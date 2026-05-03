"""DS-3.5 — parallel async sitemap-index fetches in markcrawl.robots.

Sitemap indexes (multi-tenant news sites like npr.org) point at dozens
of child sitemaps. The async parser used to fetch them sequentially,
costing 200+s on news-class crawls. The parallel version uses
asyncio.gather with a concurrency cap so all child sitemaps are
fetched concurrently."""
from __future__ import annotations

import asyncio
import time
from typing import Dict, List

from markcrawl.robots import parse_sitemap_xml_async

# ---------- Fake HTTP client ----------

class _FakeResponse:
    def __init__(self, content: bytes, content_type: str = "application/xml",
                 status: int = 200):
        self.content = content
        self.text = content.decode("utf-8", errors="replace")
        self.headers = {"content-type": content_type}
        self.is_success = 200 <= status < 300


class _FakeAsyncClient:
    """Records fetch order + per-URL latency so we can prove parallelism."""

    def __init__(self, responses: Dict[str, bytes], latency_ms: int = 50):
        self.responses = responses
        self.latency_s = latency_ms / 1000.0
        self.fetch_log: List[tuple] = []  # (url, start_time)

    async def get(self, url: str, timeout: int = 10):
        t0 = time.perf_counter()
        self.fetch_log.append((url, t0))
        await asyncio.sleep(self.latency_s)
        if url not in self.responses:
            return _FakeResponse(b"", status=404)
        return _FakeResponse(self.responses[url])


def _build_index_with_n_children(n: int, base: str = "https://example.com") -> Dict[str, bytes]:
    """Build an index XML pointing at n child sitemaps, each with 5 URLs."""
    responses: Dict[str, bytes] = {}
    children = [f"{base}/sitemap-{i}.xml" for i in range(n)]
    index_xml = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        + "\n".join(f"  <sitemap><loc>{c}</loc></sitemap>" for c in children)
        + "\n</sitemapindex>"
    )
    responses[f"{base}/sitemap.xml"] = index_xml.encode()
    for i, child in enumerate(children):
        urls = [f"{base}/section-{i}/page-{j}" for j in range(5)]
        child_xml = (
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
            + "\n".join(f"  <url><loc>{u}</loc></url>" for u in urls)
            + "\n</urlset>"
        )
        responses[child] = child_xml.encode()
    return responses


# ---------- Tests ----------

def test_index_with_one_child_returns_child_urls():
    """Sanity: single-child index still works after the parallel rewrite."""
    responses = _build_index_with_n_children(1)
    client = _FakeAsyncClient(responses, latency_ms=10)
    result = asyncio.run(parse_sitemap_xml_async(
        client, "https://example.com/sitemap.xml", timeout=10,
    ))
    assert len(result) == 5
    assert all("section-0" in u for u in result)


def test_index_with_many_children_collects_all_urls():
    """20-child index should yield 100 URLs (5 per child)."""
    responses = _build_index_with_n_children(20)
    client = _FakeAsyncClient(responses, latency_ms=5)
    result = asyncio.run(parse_sitemap_xml_async(
        client, "https://example.com/sitemap.xml", timeout=10,
    ))
    assert len(result) == 100


def test_parallel_fetch_is_faster_than_sequential():
    """20 children × 100ms latency: sequential = 2.0s, parallel ≤ 0.5s."""
    n_children = 20
    latency_ms = 100
    responses = _build_index_with_n_children(n_children)
    client = _FakeAsyncClient(responses, latency_ms=latency_ms)

    t0 = time.perf_counter()
    asyncio.run(parse_sitemap_xml_async(
        client, "https://example.com/sitemap.xml", timeout=10,
    ))
    elapsed = time.perf_counter() - t0

    sequential_lower_bound = (n_children + 1) * latency_ms / 1000.0  # 2.1s
    # Concurrency cap is 10, so 20 children take ~2 batches → ~2x latency
    # plus the index fetch. Generous upper bound.
    parallel_upper_bound = 5 * latency_ms / 1000.0  # 0.5s
    assert elapsed < parallel_upper_bound, (
        f"parallel fetch took {elapsed:.2f}s, expected < {parallel_upper_bound:.2f}s "
        f"(sequential would be ≥ {sequential_lower_bound:.2f}s)"
    )


def test_max_total_urls_cap_respected():
    """Cap at 30 should trim the result even with 20 children × 5 URLs each."""
    responses = _build_index_with_n_children(20)
    client = _FakeAsyncClient(responses, latency_ms=1)
    result = asyncio.run(parse_sitemap_xml_async(
        client, "https://example.com/sitemap.xml", timeout=10,
        max_total_urls=30,
    ))
    assert len(result) <= 30


def test_visited_dedup_prevents_cycles():
    """If two children point at each other, we shouldn't loop."""
    cyclic = {
        "https://ex.com/a.xml": (
            '<?xml version="1.0"?><sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
            '<sitemap><loc>https://ex.com/b.xml</loc></sitemap></sitemapindex>'
        ).encode(),
        "https://ex.com/b.xml": (
            '<?xml version="1.0"?><sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
            '<sitemap><loc>https://ex.com/a.xml</loc></sitemap></sitemapindex>'
        ).encode(),
    }
    client = _FakeAsyncClient(cyclic, latency_ms=1)
    # Should terminate; result is empty (no <url> entries anywhere).
    result = asyncio.run(parse_sitemap_xml_async(
        client, "https://ex.com/a.xml", timeout=10,
    ))
    assert result == []


def test_max_depth_respected():
    """Depth-2 nested index must not recurse beyond max_depth."""
    deep = {
        "https://ex.com/0.xml": (
            '<?xml version="1.0"?><sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
            '<sitemap><loc>https://ex.com/1.xml</loc></sitemap></sitemapindex>'
        ).encode(),
        "https://ex.com/1.xml": (
            '<?xml version="1.0"?><sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
            '<sitemap><loc>https://ex.com/2.xml</loc></sitemap></sitemapindex>'
        ).encode(),
        "https://ex.com/2.xml": (
            '<?xml version="1.0"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
            '<url><loc>https://ex.com/page</loc></url></urlset>'
        ).encode(),
    }
    client = _FakeAsyncClient(deep, latency_ms=1)
    # max_depth=1 means root + 1 child level allowed. /2.xml should NOT be fetched.
    result = asyncio.run(parse_sitemap_xml_async(
        client, "https://ex.com/0.xml", timeout=10, max_depth=1,
    ))
    assert "https://ex.com/page" not in result
    fetched = [u for (u, _) in client.fetch_log]
    assert "https://ex.com/2.xml" not in fetched


def test_url_filter_applied():
    """url_filter should drop entries during XML scan."""
    responses = _build_index_with_n_children(2)
    client = _FakeAsyncClient(responses, latency_ms=1)
    # Keep only section-0 URLs
    result = asyncio.run(parse_sitemap_xml_async(
        client, "https://example.com/sitemap.xml", timeout=10,
        url_filter=lambda u: "section-0" in u,
    ))
    assert all("section-0" in u for u in result)
    assert len(result) == 5

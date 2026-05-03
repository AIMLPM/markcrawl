"""Robots.txt parsing and sitemap discovery."""
from __future__ import annotations

import xml.etree.ElementTree as ET
from typing import Any, List, Optional, Tuple
from urllib import robotparser

try:
    import httpx as _httpx
    _HAS_HTTPX = True
except ImportError:
    _httpx = None  # type: ignore[assignment]
    _HAS_HTTPX = False


def parse_robots_txt(session: Any, robots_url: str) -> Tuple[robotparser.RobotFileParser, str]:
    """Fetch and parse robots.txt, returning both the parser and raw text."""
    rp = robotparser.RobotFileParser()
    try:
        response = session.get(robots_url, timeout=10)
        content = response.text if response.ok else ""
    except Exception:
        content = ""
    rp.parse(content.splitlines())
    return rp, content


def discover_sitemaps(session: Any, base: str, robots_text: Optional[str] = None) -> List[str]:
    """Find sitemap URLs declared in the site's ``robots.txt``."""
    import urllib.parse as up

    if robots_text is None:
        robots_url = up.urljoin(base, "/robots.txt")
        try:
            response = session.get(robots_url, timeout=10)
            if not response.ok:
                return []
            robots_text = response.text
        except Exception:
            return []

    sitemaps: List[str] = []
    for line in robots_text.splitlines():
        if line.lower().startswith("sitemap:"):
            sitemap_url = line.split(":", 1)[1].strip()
            if sitemap_url:
                sitemaps.append(sitemap_url)
    return sitemaps


_DEFAULT_SITEMAP_TIME_BUDGET_S = 60.0


def parse_sitemap_xml(
    session: Any,
    url: str,
    timeout: int,
    *,
    _depth: int = 0,
    _visited: Optional[set] = None,
    _deadline: Optional[float] = None,
    max_depth: int = 5,
    max_total_urls: int = 5000,
    time_budget_s: float = _DEFAULT_SITEMAP_TIME_BUDGET_S,
    url_filter: Optional[Any] = None,
) -> List[str]:
    """Recursively parse a sitemap XML and return all page URLs.

    Guards:
    * *max_depth* (default 5) bounds recursion into nested sitemap indexes.
    * *_visited* set prevents re-fetching the same sitemap (cycles).
    * *max_total_urls* (default 5000) early-exits when enough URLs have
      been collected. Critical for sites like npr.org whose sitemap index
      points to dozens of 50K-URL child sitemaps; without the cap we
      spent 245s on sitemap parsing alone for a 50-page crawl. Caller
      should pass ``max(500, max_pages * 4)`` to scale with the budget.
    * *time_budget_s* (default 60s) caps total wallclock spent in
      sitemap pre-enumeration regardless of count. Pathological retailer
      indexes (ikea: 2,113 sub-sitemaps) used to consume 200+s before
      any page got crawled, tripping zero-output watchdogs in benchmark
      harnesses (introduced in v0.10.2). Once the deadline fires, the
      function returns whatever URLs it has collected so far.
    * *url_filter*, if provided, is called for each URL; only URLs where
      the filter returns True are kept. Filtering during parse avoids
      retaining tens of thousands of out-of-scope URLs only to discard
      them at the next stage. Caller's filter should match the in-scope
      / allowed / not-excluded predicates the engine will apply anyway.
    """
    import time as _time
    if _depth > max_depth:
        return []
    if _visited is None:
        _visited = set()
    if _deadline is None:
        _deadline = _time.monotonic() + time_budget_s
    if _time.monotonic() >= _deadline:
        return []
    if url in _visited:
        return []
    _visited.add(url)

    try:
        response = session.get(url, timeout=timeout)
        if not response.ok:
            return []
        content_type = response.headers.get("content-type", "").lower()
        if not (content_type.startswith("application/xml") or response.text.strip().startswith("<")):
            return []
        root = ET.fromstring(response.content)
    except Exception:
        return []

    ns = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
    urls: List[str] = []

    def _accept(u: str) -> bool:
        return url_filter is None or url_filter(u)

    for loc in root.findall(".//sm:sitemap/sm:loc", ns):
        if len(urls) >= max_total_urls:
            break
        if _time.monotonic() >= _deadline:
            break
        child_url = (loc.text or "").strip()
        if child_url:
            child_urls = parse_sitemap_xml(
                session, child_url, timeout,
                _depth=_depth + 1, _visited=_visited, _deadline=_deadline,
                max_depth=max_depth,
                max_total_urls=max_total_urls - len(urls),
                url_filter=url_filter,
            )
            urls.extend(child_urls)

    for loc in root.findall(".//sm:url/sm:loc", ns):
        if len(urls) >= max_total_urls:
            break
        page_url = (loc.text or "").strip()
        if page_url and _accept(page_url):
            urls.append(page_url)

    if not urls:
        for loc in root.findall(".//loc"):
            if len(urls) >= max_total_urls:
                break
            page_url = (loc.text or "").strip()
            if page_url and _accept(page_url):
                urls.append(page_url)

    return list(dict.fromkeys(urls))


# ---------------------------------------------------------------------------
# Async variants
# ---------------------------------------------------------------------------

async def parse_robots_txt_async(client: Any, robots_url: str) -> Tuple[robotparser.RobotFileParser, str]:
    """Async version of :func:`parse_robots_txt`."""
    rp = robotparser.RobotFileParser()
    try:
        response = await client.get(robots_url, timeout=10)
        content = response.text if response.is_success else ""
    except Exception:
        content = ""
    rp.parse(content.splitlines())
    return rp, content


_SITEMAP_CHILD_CONCURRENCY = 10


async def parse_sitemap_xml_async(
    client: Any,
    url: str,
    timeout: int,
    *,
    _depth: int = 0,
    _visited: Optional[set] = None,
    _semaphore: Optional[Any] = None,
    _deadline: Optional[float] = None,
    max_depth: int = 5,
    max_total_urls: int = 5000,
    time_budget_s: float = _DEFAULT_SITEMAP_TIME_BUDGET_S,
    url_filter: Optional[Any] = None,
) -> List[str]:
    """Async version of :func:`parse_sitemap_xml`. Same caps semantics.

    Child-sitemap fetches inside an index are parallelized via
    asyncio.as_completed so we can short-circuit pending children once
    *max_total_urls* or *time_budget_s* fires. Multi-tenant sitemap
    indexes (npr.org, ikea with 2,113 locale shards) used to consume
    200+s before any page got crawled — the deadline fix landed in
    v0.10.2 to keep the pre-enumeration phase bounded. Concurrency is
    still capped at _SITEMAP_CHILD_CONCURRENCY so we don't hammer the
    target.
    """
    import time as _time
    if _depth > max_depth:
        return []
    if _visited is None:
        _visited = set()
    if _deadline is None:
        _deadline = _time.monotonic() + time_budget_s
    if _time.monotonic() >= _deadline:
        return []
    if _semaphore is None:
        import asyncio as _asyncio  # local import keeps top of file clean
        _semaphore = _asyncio.Semaphore(_SITEMAP_CHILD_CONCURRENCY)
    if url in _visited:
        return []
    _visited.add(url)

    try:
        response = await client.get(url, timeout=timeout)
        if not response.is_success:
            return []
        content_type = response.headers.get("content-type", "").lower()
        if not (content_type.startswith("application/xml") or response.text.strip().startswith("<")):
            return []
        root = ET.fromstring(response.content)
    except Exception:
        return []

    ns = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
    urls: List[str] = []

    def _accept(u: str) -> bool:
        return url_filter is None or url_filter(u)

    # Collect all child sitemap URLs first, then fetch in parallel.
    child_loc_urls: List[str] = []
    for loc in root.findall(".//sm:sitemap/sm:loc", ns):
        child_url = (loc.text or "").strip()
        if child_url and child_url not in _visited:
            child_loc_urls.append(child_url)

    if child_loc_urls:
        import asyncio as _asyncio

        async def _fetch_child(child_url: str) -> List[str]:
            # Skip if the budget already fired before we even started.
            if _time.monotonic() >= _deadline:
                return []
            async with _semaphore:
                if _time.monotonic() >= _deadline:
                    return []
                return await parse_sitemap_xml_async(
                    client, child_url, timeout,
                    _depth=_depth + 1, _visited=_visited,
                    _semaphore=_semaphore, _deadline=_deadline,
                    max_depth=max_depth,
                    max_total_urls=max_total_urls,
                    url_filter=url_filter,
                )

        # Fan out via as_completed so we can short-circuit once the
        # URL cap or the deadline fires; cancel pending tasks rather
        # than waiting for all 2,113 children to resolve.
        tasks = [_asyncio.create_task(_fetch_child(cu)) for cu in child_loc_urls]
        try:
            for fut in _asyncio.as_completed(tasks):
                try:
                    r = await fut
                except Exception:
                    r = []
                urls.extend(r)
                if len(urls) >= max_total_urls or _time.monotonic() >= _deadline:
                    break
        finally:
            for t in tasks:
                if not t.done():
                    t.cancel()

    for loc in root.findall(".//sm:url/sm:loc", ns):
        if len(urls) >= max_total_urls:
            break
        page_url = (loc.text or "").strip()
        if page_url and _accept(page_url):
            urls.append(page_url)

    if not urls:
        for loc in root.findall(".//loc"):
            if len(urls) >= max_total_urls:
                break
            page_url = (loc.text or "").strip()
            if page_url and _accept(page_url):
                urls.append(page_url)

    return list(dict.fromkeys(urls))[:max_total_urls]

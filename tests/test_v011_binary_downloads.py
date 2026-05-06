"""v0.11.0 — binary downloads (PDF, DOCX, etc.) referenced from crawled pages.

Covers SC-1..SC-11 from specs/binary-downloads.md plus the supporting
edge cases.  The download path is exercised through mocked HTTP for
streaming behavior (size cap, type validation, atomic rename).  An
end-to-end mocked crawl proves the discover→queue→drain→JSONL flow.
"""
from __future__ import annotations

import json
import os
import textwrap
from pathlib import Path
from unittest.mock import MagicMock, patch

from markcrawl.binaries import (
    content_type_matches,
    download_binary,
    safe_binary_filename,
    url_extension,
    url_matches_download_types,
)
from markcrawl.filters import (
    DownloadCandidate,
    exclude_legal_boilerplate,
    is_likely_paper,
    is_likely_resume,
)

# ---------- url_extension -----------------------------------------------

def test_url_extension_basic():
    assert url_extension("https://example.com/file.pdf") == ".pdf"
    assert url_extension("https://ex.com/path/to/doc.DOCX") == ".docx"


def test_url_extension_no_ext():
    assert url_extension("https://example.com/page") == ""
    assert url_extension("https://example.com/") == ""


def test_url_extension_strips_query():
    assert url_extension("https://example.com/file.pdf?download=true") == ".pdf"


def test_url_extension_rejects_too_long_or_short():
    # a "dot" in mid-path that isn't a real extension shouldn't match
    assert url_extension("https://example.com/v1.0/page") == ""


# ---------- url_matches_download_types ----------------------------------

def test_url_match_extension_match():
    assert url_matches_download_types("x.pdf", ["pdf"]) is True
    assert url_matches_download_types("x.pdf", [".pdf"]) is True
    assert url_matches_download_types("x.docx", ["pdf"]) is False


def test_url_match_no_extension():
    assert url_matches_download_types("https://ex.com/page", ["pdf"]) is False


def test_url_match_empty_types():
    assert url_matches_download_types("x.pdf", []) is False
    assert url_matches_download_types("x.pdf", None) is False  # type: ignore[arg-type]


# ---------- content_type_matches ----------------------------------------

def test_content_type_match_subtype():
    assert content_type_matches("application/pdf", ["pdf"]) is True


def test_content_type_match_full_mime():
    assert content_type_matches("application/pdf", ["application/pdf"]) is True


def test_content_type_match_with_charset_param():
    assert content_type_matches("application/pdf; charset=binary", ["pdf"]) is True


def test_content_type_mismatch():
    assert content_type_matches("text/html", ["pdf"]) is False


def test_content_type_match_mime_prefix():
    assert content_type_matches("application/pdf", ["application/"]) is True


def test_content_type_empty():
    assert content_type_matches("", ["pdf"]) is False


# ---------- safe_binary_filename ----------------------------------------

def test_safe_binary_filename_basic():
    name = safe_binary_filename("https://ex.com/folder/template.pdf")
    assert name.startswith("template__") or name.startswith("template-_")
    assert name.endswith(".pdf")
    # 12-char hash suffix
    stem = name[:-len(".pdf")]
    assert len(stem.split("__")[-1]) == 12


def test_safe_binary_filename_no_ext_uses_content_type():
    name = safe_binary_filename("https://ex.com/x", "application/pdf")
    assert name.endswith(".pdf")


def test_safe_binary_filename_no_ext_no_ct_uses_bin():
    name = safe_binary_filename("https://ex.com/x", "")
    assert name.endswith(".bin")


def test_safe_binary_filename_path_traversal_proof():
    name = safe_binary_filename("https://ex.com/../../etc/passwd")
    assert ".." not in name
    assert "/" not in name
    # only safe chars
    stem = name.rsplit(".", 1)[0]
    for ch in stem:
        assert ch.isalnum() or ch in "._-"


def test_safe_binary_filename_collision_resilience():
    """Two URLs with the same basename produce different filenames via hash."""
    a = safe_binary_filename("https://a.com/template.pdf")
    b = safe_binary_filename("https://b.com/template.pdf")
    assert a != b


# ---------- filters: DownloadCandidate ----------------------------------

def _cand(url: str, anchor: str = "", parent_url: str = "https://ex.com/",
          parent_title: str = "Home", ext: str = "") -> DownloadCandidate:
    if not ext:
        ext = url_extension(url)
    return DownloadCandidate(
        url=url, anchor_text=anchor, parent_url=parent_url,
        parent_title=parent_title, extension=ext,
    )


def test_is_likely_resume_positive_anchor():
    assert is_likely_resume(_cand("https://ex.com/file.pdf", anchor="Download CV template"))


def test_is_likely_resume_negative_anchor():
    assert not is_likely_resume(_cand("https://ex.com/file.pdf", anchor="Privacy Policy"))


def test_is_likely_resume_positive_url():
    assert is_likely_resume(_cand("https://ex.com/resume-template.pdf", anchor=""))


def test_is_likely_resume_legal_in_url_overrides():
    # Even if the URL has "resume", "privacy" elsewhere should reject
    assert not is_likely_resume(
        _cand("https://ex.com/legal/privacy-resume.pdf", anchor="")
    )


def test_is_likely_resume_empty_returns_false():
    assert not is_likely_resume(_cand("https://ex.com/", anchor=""))


def test_is_likely_paper_positive():
    assert is_likely_paper(_cand("https://ex.com/preprint.pdf", anchor="Read the paper"))


def test_is_likely_paper_negative_legal():
    assert not is_likely_paper(_cand("https://ex.com/preprint.pdf", anchor="Privacy policy"))


def test_exclude_legal_boilerplate_rejects_negative():
    assert not exclude_legal_boilerplate(_cand("https://ex.com/x.pdf", anchor="Privacy"))


def test_exclude_legal_boilerplate_permissive_for_neutral():
    # Pure negative selector — should pass through random non-legal URLs
    assert exclude_legal_boilerplate(_cand("https://ex.com/random.pdf", anchor=""))


# ---------- download_binary (sync, mocked HTTP) -------------------------

def _mock_streaming_response(status: int, content: bytes, content_type: str):
    resp = MagicMock()
    resp.status_code = status
    resp.headers = {"content-type": content_type}

    def iter_content(chunk_size=8192):
        for i in range(0, len(content), chunk_size):
            yield content[i:i + chunk_size]

    resp.iter_content = iter_content
    resp.content = content
    return resp


def test_download_binary_happy_path(tmp_path):
    """SC-1: PDF saved to <out>/downloads/, metadata returned."""
    session = MagicMock()
    session.get.return_value = _mock_streaming_response(200, b"%PDF-1.4 fake content", "application/pdf")

    result = download_binary(
        session, "https://ex.com/template.pdf",
        downloads_dir=str(tmp_path),
        timeout=10,
        max_size_bytes=10 * 1024 * 1024,
        allowed_types=["pdf"],
    )

    assert result is not None
    assert result.get("path", "").endswith(".pdf")
    assert os.path.exists(result["path"])
    assert result["size_bytes"] == len(b"%PDF-1.4 fake content")
    assert result["content_type"] == "application/pdf"


def test_download_binary_content_type_mismatch_returns_type_skipped(tmp_path):
    """SC-3: .pdf URL serving text/html → no save, type-skipped marker."""
    session = MagicMock()
    session.get.return_value = _mock_streaming_response(200, b"<html>login wall</html>", "text/html")

    result = download_binary(
        session, "https://ex.com/file.pdf",
        downloads_dir=str(tmp_path),
        timeout=10,
        max_size_bytes=1024 * 1024,
        allowed_types=["pdf"],
    )
    assert result is not None
    assert result.get("_type_skipped") is True
    # No file should have been written
    assert list(tmp_path.iterdir()) == []


def test_download_binary_size_cap_aborts_and_unlinks_partial(tmp_path):
    """SC-5: stream exceeds cap → partial file unlinked, size-skipped marker."""
    big = b"x" * 50_000  # 50 KB
    session = MagicMock()
    session.get.return_value = _mock_streaming_response(200, big, "application/pdf")

    result = download_binary(
        session, "https://ex.com/huge.pdf",
        downloads_dir=str(tmp_path),
        timeout=10,
        max_size_bytes=10_000,  # 10 KB cap
        allowed_types=["pdf"],
    )
    assert result is not None
    assert result.get("_size_skipped") is True
    # No tmp or final file should remain
    leftovers = list(tmp_path.iterdir())
    assert leftovers == [], f"unexpected files: {leftovers}"


def test_download_binary_http_error_returns_none(tmp_path):
    """4xx / 5xx → None, no file written."""
    session = MagicMock()
    session.get.return_value = _mock_streaming_response(404, b"", "text/plain")

    result = download_binary(
        session, "https://ex.com/missing.pdf",
        downloads_dir=str(tmp_path),
        timeout=10,
        max_size_bytes=1024,
        allowed_types=["pdf"],
    )
    assert result is None


def test_download_binary_connection_error_returns_none(tmp_path):
    session = MagicMock()
    session.get.side_effect = OSError("connection refused")

    result = download_binary(
        session, "https://ex.com/x.pdf",
        downloads_dir=str(tmp_path),
        timeout=10,
        max_size_bytes=1024,
        allowed_types=["pdf"],
    )
    assert result is None


# ---------- _consider_download_candidate (engine helper) ----------------

def _make_async_engine(tmp_path, **kwargs):
    from markcrawl.core import AsyncCrawlEngine
    out = tmp_path / "out"
    out.mkdir(exist_ok=True)
    defaults = dict(
        out_dir=str(out), fmt="markdown", min_words=20, delay=0, timeout=10,
        concurrency=1, include_subdomains=False, user_agent="test", proxy=None,
        show_progress=False,
    )
    defaults.update(kwargs)
    return AsyncCrawlEngine(**defaults)


def test_consider_routes_matching_url_to_queue(tmp_path):
    eng = _make_async_engine(tmp_path, download_types=["pdf"])
    claimed = eng._consider_download_candidate(
        url="https://ex.com/x.pdf", anchor_text="Download", parent_url="https://ex.com/",
        parent_title="Home", base_netloc="ex.com",
    )
    assert claimed is True
    assert len(eng._to_download) == 1


def test_consider_skips_non_matching_extension(tmp_path):
    eng = _make_async_engine(tmp_path, download_types=["pdf"])
    claimed = eng._consider_download_candidate(
        url="https://ex.com/x.docx", anchor_text="", parent_url="https://ex.com/",
        parent_title="Home", base_netloc="ex.com",
    )
    assert claimed is False
    assert len(eng._to_download) == 0


def test_consider_filter_returning_false_drops_silently(tmp_path):
    """SC-9: filter is pre-fetch — rejected URLs never get fetched.
    URL is claimed (so HTML crawler doesn't also try it) but NOT enqueued."""
    eng = _make_async_engine(
        tmp_path, download_types=["pdf"],
        download_filter=lambda c: False,
    )
    claimed = eng._consider_download_candidate(
        url="https://ex.com/x.pdf", anchor_text="x", parent_url="https://ex.com/",
        parent_title="Home", base_netloc="ex.com",
    )
    assert claimed is True  # claimed (don't HTML-crawl it)
    assert len(eng._to_download) == 0  # not enqueued


def test_consider_filter_exception_drops_silently(tmp_path):
    """A buggy filter shouldn't crash the crawl."""
    def bad(c):
        raise ValueError("oops")
    eng = _make_async_engine(tmp_path, download_types=["pdf"], download_filter=bad)
    claimed = eng._consider_download_candidate(
        url="https://ex.com/x.pdf", anchor_text="x", parent_url="https://ex.com/",
        parent_title="Home", base_netloc="ex.com",
    )
    assert claimed is True
    assert len(eng._to_download) == 0


def test_consider_dedup_existing_url(tmp_path):
    """SC-7: same URL referenced twice gets queued once."""
    eng = _make_async_engine(tmp_path, download_types=["pdf"])
    eng._consider_download_candidate(
        url="https://ex.com/x.pdf", anchor_text="a", parent_url="https://ex.com/p1",
        parent_title="P1", base_netloc="ex.com",
    )
    # Mark as already downloaded
    eng._downloaded_urls.add("https://ex.com/x.pdf")
    eng._consider_download_candidate(
        url="https://ex.com/x.pdf", anchor_text="b", parent_url="https://ex.com/p2",
        parent_title="P2", base_netloc="ex.com",
    )
    # Queue should still have just the first attempt
    assert len(eng._to_download) == 1


# ---------- API surface --------------------------------------------------

def test_crawlresult_exposes_download_fields():
    import inspect

    from markcrawl.core import CrawlResult
    fields = {f.name for f in CrawlResult.__dataclass_fields__.values()}
    assert "downloads_count" in fields
    assert "downloads_bytes" in fields
    assert "downloads_size_skipped" in fields
    assert "downloads_type_skipped" in fields
    sig = inspect.signature(CrawlResult)
    assert "downloads_count" in sig.parameters


def test_crawl_api_accepts_download_kwargs():
    import inspect

    from markcrawl.core import crawl
    sig = inspect.signature(crawl)
    for kw in ("download_types", "download_max_files", "download_max_size_mb", "download_filter"):
        assert kw in sig.parameters, f"missing kwarg: {kw}"
    assert sig.parameters["download_types"].default is None


def test_filters_module_exports():
    from markcrawl import filters
    assert hasattr(filters, "DownloadCandidate")
    assert hasattr(filters, "is_likely_resume")
    assert hasattr(filters, "is_likely_paper")
    assert hasattr(filters, "exclude_legal_boilerplate")


# ---------- End-to-end via crawl() (mocked HTTP) -------------------------

def _mock_html_resp(html: str):
    resp = MagicMock()
    resp.ok = True
    resp.status_code = 200
    resp.text = html
    resp.content = html.encode()
    resp.headers = {"content-type": "text/html; charset=utf-8"}
    return resp


def _mock_pdf_streaming_resp(content_bytes: bytes):
    resp = MagicMock()
    resp.ok = True
    resp.status_code = 200
    resp.headers = {"content-type": "application/pdf"}

    def iter_content(chunk_size=8192):
        for i in range(0, len(content_bytes), chunk_size):
            yield content_bytes[i:i + chunk_size]

    resp.iter_content = iter_content
    resp.content = content_bytes
    return resp


@patch("markcrawl.core._HAS_HTTPX", False)
@patch("markcrawl.core.fetch")
@patch("markcrawl.core.build_session")
def test_e2e_default_no_downloads_no_change(mock_build, mock_fetch, tmp_path):
    """SC-2: default behavior unchanged when download_types=None."""
    from markcrawl.core import crawl
    session = MagicMock()
    mock_build.return_value = session
    session.get.return_value = _mock_html_resp("")  # robots.txt empty

    seed_html = textwrap.dedent("""
    <html><head><title>Home</title></head>
    <body><main><p>This page has plenty of content for the min-words filter to pass cleanly here.</p>
    <a href="/template.pdf">CV template</a></main></body></html>
    """)
    by_url = {"https://example.com/": _mock_html_resp(seed_html)}
    mock_fetch.side_effect = lambda session, url, timeout: by_url.get(
        url, _mock_html_resp("")
    )

    result = crawl(
        base_url="https://example.com/",
        out_dir=str(tmp_path / "out"),
        use_sitemap=False,
        max_pages=2,
        min_words=5,
    )
    # No downloads dir created
    assert not (tmp_path / "out" / "downloads").exists()
    assert result.downloads_count == 0


@patch("markcrawl.core._HAS_HTTPX", False)
@patch("markcrawl.core.fetch")
@patch("markcrawl.core.build_session")
def test_e2e_pdf_link_downloaded_and_recorded_in_jsonl(mock_build, mock_fetch, tmp_path):
    """SC-1: PDF link is downloaded; JSONL row carries `downloads` field."""
    from markcrawl.core import crawl
    session = MagicMock()
    mock_build.return_value = session

    pdf_bytes = b"%PDF-1.4 fake-template-content " * 100  # ~3 KB

    def get_side_effect(url, timeout=None, **kwargs):
        if url.endswith("/robots.txt"):
            return _mock_html_resp("")
        if url.endswith(".pdf"):
            return _mock_pdf_streaming_resp(pdf_bytes)
        return _mock_html_resp("")

    session.get.side_effect = get_side_effect

    seed_html = textwrap.dedent("""
    <html><head><title>Home</title></head>
    <body><main>
    <p>This page has plenty of content for the min-words filter to pass cleanly here.</p>
    <a href="/cv-template.pdf">Download CV template</a>
    </main></body></html>
    """)

    def fetch_side_effect(session, url, timeout):
        if url == "https://example.com/":
            return _mock_html_resp(seed_html)
        return _mock_html_resp("")

    mock_fetch.side_effect = fetch_side_effect

    result = crawl(
        base_url="https://example.com/",
        out_dir=str(tmp_path / "out"),
        use_sitemap=False,
        max_pages=1,
        min_words=5,
        download_types=["pdf"],
    )

    # SC-1 verification
    assert result.downloads_count == 1
    downloads_dir = tmp_path / "out" / "downloads"
    assert downloads_dir.is_dir()
    pdf_files = list(downloads_dir.glob("*.pdf"))
    assert len(pdf_files) == 1

    # JSONL row carries the `downloads` field
    rows = []
    with open(result.index_file) as f:
        for line in f:
            rows.append(json.loads(line))
    assert len(rows) == 1
    assert "downloads" in rows[0]
    assert len(rows[0]["downloads"]) == 1
    assert rows[0]["downloads"][0]["url"] == "https://example.com/cv-template.pdf"


@patch("markcrawl.core._HAS_HTTPX", False)
@patch("markcrawl.core.fetch")
@patch("markcrawl.core.build_session")
def test_e2e_filter_blocks_unwanted_pdfs(mock_build, mock_fetch, tmp_path):
    """SC-10: is_likely_resume blocks Privacy Policy.pdf, allows CV template."""
    from markcrawl.core import crawl
    session = MagicMock()
    mock_build.return_value = session

    pdf_bytes = b"%PDF-1.4 some content " * 50

    def get_side_effect(url, timeout=None, **kwargs):
        if url.endswith("/robots.txt"):
            return _mock_html_resp("")
        return _mock_pdf_streaming_resp(pdf_bytes)

    session.get.side_effect = get_side_effect

    seed_html = textwrap.dedent("""
    <html><head><title>Templates</title></head>
    <body><main>
    <p>This page has plenty of content for the min-words filter to pass cleanly here.</p>
    <a href="/cv-template.pdf">Download CV template</a>
    <a href="/privacy-policy.pdf">Privacy Policy</a>
    </main></body></html>
    """)
    mock_fetch.side_effect = lambda session, url, timeout: (
        _mock_html_resp(seed_html) if url == "https://example.com/templates"
        else _mock_html_resp("")
    )

    result = crawl(
        base_url="https://example.com/templates",
        out_dir=str(tmp_path / "out"),
        use_sitemap=False,
        max_pages=1,
        min_words=5,
        download_types=["pdf"],
        download_filter=is_likely_resume,
    )

    # Only the CV template should be downloaded.
    assert result.downloads_count == 1
    pdf_files = list((tmp_path / "out" / "downloads").glob("*.pdf"))
    names = [p.name for p in pdf_files]
    # Filename stem is derived from URL basename; cv-template stem expected.
    assert any("cv-template" in n for n in names)
    assert not any("privacy" in n for n in names)


# ---------- Source-level guards (cheap regression catches) ----------------

def test_streaming_used_in_binaries_module():
    """DS-4 contract: download_binary uses stream=True (not buffered .content)."""
    src = Path(__file__).parent.parent / "markcrawl" / "binaries.py"
    text = src.read_text("utf-8")
    assert "stream=True" in text, "download_binary must use stream=True"
    assert "iter_content" in text, "download_binary must use iter_content for size cap"


def test_atomic_rename_used_in_binaries_module():
    """DS-4: atomic .tmp → final rename."""
    src = Path(__file__).parent.parent / "markcrawl" / "binaries.py"
    text = src.read_text("utf-8")
    assert "os.replace" in text, "download_binary must atomically rename via os.replace"
    assert ".tmp" in text, "tmp suffix expected during streaming"

"""v0.10.6 — opt-in robots.txt Disallow override.

The default ``respect_robots=True`` preserves the historical behavior:
robots.txt Disallow rules are honored.  Setting ``respect_robots=False``
bypasses Disallow but **still honors Crawl-delay** (politeness intact).

Caller takes responsibility for legality and ethics.  The bypass is
loud (warning logs at engine setup), audited (``CrawlResult.
robots_bypassed_count``), and never silently configurable from the
environment.
"""
from __future__ import annotations

import logging
import textwrap
from unittest.mock import MagicMock, patch


def _mock_resp(html: str, ok: bool = True, status: int = 200) -> MagicMock:
    resp = MagicMock()
    resp.ok = ok
    resp.status_code = status
    resp.text = html
    resp.content = html.encode()
    resp.headers = {"content-type": "text/html; charset=utf-8"}
    return resp


def _make_async_engine(tmp_path, *, respect_robots=True):
    from markcrawl.core import AsyncCrawlEngine
    out = tmp_path / "out"
    out.mkdir(exist_ok=True)
    return AsyncCrawlEngine(
        out_dir=str(out),
        fmt="markdown",
        min_words=20,
        delay=0,
        timeout=10,
        concurrency=1,
        include_subdomains=False,
        user_agent="test",
        proxy=None,
        show_progress=False,
        respect_robots=respect_robots,
    )


def _make_sync_engine(tmp_path, *, respect_robots=True):
    from markcrawl.core import CrawlEngine
    out = tmp_path / "out"
    out.mkdir(exist_ok=True)
    return CrawlEngine(
        out_dir=str(out),
        fmt="markdown",
        min_words=20,
        delay=0,
        timeout=10,
        concurrency=1,
        include_subdomains=False,
        user_agent="test",
        render_js=False,
        proxy=None,
        show_progress=False,
        respect_robots=respect_robots,
    )


# ---------- Engine state defaults ------------------------------------------

def test_engine_defaults_to_respecting_robots(tmp_path):
    e = _make_async_engine(tmp_path)
    assert e.respect_robots is True
    assert e._robots_bypassed_count == 0


def test_engine_can_opt_out(tmp_path):
    e = _make_async_engine(tmp_path, respect_robots=False)
    assert e.respect_robots is False
    assert e._robots_bypassed_count == 0


# ---------- allowed() behavior under both modes ----------------------------

def test_allowed_blocks_disallowed_when_respecting(tmp_path):
    """Default behavior: robots.txt Disallow rules block fetches."""
    engine = _make_async_engine(tmp_path, respect_robots=True)
    rp = MagicMock()
    rp.can_fetch.return_value = False  # disallowed
    engine._rp = rp
    assert engine.allowed("https://example.com/private/secret") is False
    assert engine._robots_bypassed_count == 0


def test_allowed_bypasses_disallowed_when_not_respecting(tmp_path):
    """Override mode: Disallowed URLs are reported allowed AND counted."""
    engine = _make_async_engine(tmp_path, respect_robots=False)
    rp = MagicMock()
    rp.can_fetch.return_value = False
    engine._rp = rp
    assert engine.allowed("https://example.com/private/secret") is True
    assert engine._robots_bypassed_count == 1
    # Multiple bypassed URLs accumulate
    assert engine.allowed("https://example.com/private/another") is True
    assert engine._robots_bypassed_count == 2


def test_allowed_does_not_count_when_url_was_actually_allowed(tmp_path):
    """Bypass count tracks ONLY URLs robots actually disallowed.

    A URL robots permits doesn't bump the counter even with override on
    — the override didn't unlock anything for that URL.
    """
    engine = _make_async_engine(tmp_path, respect_robots=False)
    rp = MagicMock()
    rp.can_fetch.return_value = True  # allowed by robots
    engine._rp = rp
    assert engine.allowed("https://example.com/public/page") is True
    assert engine._robots_bypassed_count == 0


def test_allowed_handles_can_fetch_exception(tmp_path):
    """When the parser blows up, default to allowed (the conservative
    behavior matches what we did pre-v0.10.6 — a robots failure
    shouldn't block the crawl)."""
    engine = _make_async_engine(tmp_path, respect_robots=True)
    rp = MagicMock()
    rp.can_fetch.side_effect = Exception("malformed UA pattern")
    engine._rp = rp
    assert engine.allowed("https://example.com/x") is True
    assert engine._robots_bypassed_count == 0


def test_sync_engine_has_same_bypass_behavior(tmp_path):
    """Parity check — sync engine mirrors the async one."""
    engine = _make_sync_engine(tmp_path, respect_robots=False)
    rp = MagicMock()
    rp.can_fetch.return_value = False
    engine._rp = rp
    assert engine.allowed("https://example.com/private") is True
    assert engine._robots_bypassed_count == 1


# ---------- Loud-warning behavior ------------------------------------------

@patch("markcrawl.core._HAS_HTTPX", False)
@patch("markcrawl.core.parse_robots_txt")
@patch("markcrawl.core.build_session")
def test_warning_emitted_when_bypassing(
    mock_build, mock_parse_robots, tmp_path, caplog,
):
    """Bypass mode emits a WARNING-level log at setup_robots time."""
    from markcrawl.core import CrawlEngine

    rp = MagicMock()
    rp.can_fetch.return_value = True
    mock_parse_robots.return_value = (rp, "User-agent: *\nDisallow: /\n")
    mock_build.return_value = MagicMock()

    out = tmp_path / "out"
    out.mkdir()
    engine = CrawlEngine(
        out_dir=str(out),
        fmt="markdown", min_words=20, delay=0, timeout=10, concurrency=1,
        include_subdomains=False, user_agent="test", render_js=False,
        proxy=None, show_progress=False,
        respect_robots=False,
    )

    with caplog.at_level(logging.WARNING, logger="markcrawl.core"):
        engine.setup_robots("https://example.com/")

    assert any(
        "robots.txt" in r.message and "respect_robots=False" in r.message
        for r in caplog.records
    ), "expected setup_robots to log a respect_robots=False warning"


@patch("markcrawl.core._HAS_HTTPX", False)
@patch("markcrawl.core.parse_robots_txt")
@patch("markcrawl.core.build_session")
def test_no_warning_emitted_when_respecting(
    mock_build, mock_parse_robots, tmp_path, caplog,
):
    """Default mode: no robots-bypass warning."""
    from markcrawl.core import CrawlEngine

    rp = MagicMock()
    rp.can_fetch.return_value = True
    mock_parse_robots.return_value = (rp, "")
    mock_build.return_value = MagicMock()

    out = tmp_path / "out"
    out.mkdir()
    engine = CrawlEngine(
        out_dir=str(out),
        fmt="markdown", min_words=20, delay=0, timeout=10, concurrency=1,
        include_subdomains=False, user_agent="test", render_js=False,
        proxy=None, show_progress=False,
    )

    with caplog.at_level(logging.WARNING, logger="markcrawl.core"):
        engine.setup_robots("https://example.com/")

    assert not any(
        "respect_robots=False" in r.message for r in caplog.records
    )


# ---------- Crawl-delay (politeness) is preserved --------------------------

@patch("markcrawl.core._HAS_HTTPX", False)
@patch("markcrawl.core.parse_robots_txt")
@patch("markcrawl.core.build_session")
def test_crawl_delay_honored_even_with_bypass(
    mock_build, mock_parse_robots, tmp_path,
):
    """Bypass disregards Disallow but keeps the politeness contract.

    Crawl-delay is independently parsed and applied to the throttle;
    respect_robots=False MUST NOT remove rate limits.
    """
    from markcrawl.core import CrawlEngine

    rp = MagicMock()
    rp.can_fetch.return_value = True
    mock_parse_robots.return_value = (
        rp,
        "User-agent: *\nCrawl-delay: 5\nDisallow: /\n",
    )
    mock_build.return_value = MagicMock()

    out = tmp_path / "out"
    out.mkdir()
    engine = CrawlEngine(
        out_dir=str(out),
        fmt="markdown", min_words=20, delay=0, timeout=10, concurrency=1,
        include_subdomains=False, user_agent="test", render_js=False,
        proxy=None, show_progress=False,
        respect_robots=False,
    )
    engine.setup_robots("https://example.com/")

    # Crawl-delay should have been applied to the throttle even with
    # respect_robots=False.
    assert engine._throttle.base_delay >= 5.0


# ---------- End-of-crawl bypass-count summary ------------------------------

def test_emit_summary_silent_when_respecting(tmp_path):
    """No summary noise when the default is on."""
    from markcrawl.core import _emit_robots_bypass_summary
    engine = _make_async_engine(tmp_path, respect_robots=True)
    msgs = []
    engine.progress = msgs.append
    _emit_robots_bypass_summary(engine)
    assert msgs == []


def test_emit_summary_zero_count_says_no_effect(tmp_path):
    """If bypass was requested but robots wasn't constraining, say so."""
    from markcrawl.core import _emit_robots_bypass_summary
    engine = _make_async_engine(tmp_path, respect_robots=False)
    # bypass set is empty by construction; nothing to add
    msgs = []
    engine.progress = msgs.append
    _emit_robots_bypass_summary(engine)
    out = " ".join(msgs)
    assert "had no effect" in out.lower() or "did not" in out.lower()


def test_emit_summary_non_zero_count_reports_audit(tmp_path, caplog):
    """When the bypass actually unlocked URLs, surface the count."""
    from markcrawl.core import _emit_robots_bypass_summary
    engine = _make_async_engine(tmp_path, respect_robots=False)
    engine._robots_bypassed.update(
        f"https://ex.com/private/page{i}" for i in range(17)
    )
    msgs = []
    engine.progress = msgs.append
    with caplog.at_level(logging.WARNING, logger="markcrawl.core"):
        _emit_robots_bypass_summary(engine)
    out = " ".join(msgs)
    assert "17" in out
    assert any("17" in r.message for r in caplog.records)


# ---------- Public API + CrawlResult ---------------------------------------

def test_crawl_api_accepts_respect_robots_kwarg():
    """The public crawl() signature must expose respect_robots."""
    import inspect

    from markcrawl.core import crawl
    sig = inspect.signature(crawl)
    assert "respect_robots" in sig.parameters
    assert sig.parameters["respect_robots"].default is True


def test_crawlresult_exposes_robots_fields():
    """The audit fields are part of the public contract."""
    from markcrawl.core import CrawlResult
    fields = {f.name for f in CrawlResult.__dataclass_fields__.values()}
    assert "robots_respected" in fields
    assert "robots_bypassed_count" in fields


# ---------- End-to-end ----------------------------------------------------

@patch("markcrawl.core._HAS_HTTPX", False)
@patch("markcrawl.core.fetch")
@patch("markcrawl.core.build_session")
def test_e2e_default_respects_robots(mock_build, mock_fetch, tmp_path):
    """Default crawl: robots.txt Disallow blocks the page."""
    from markcrawl.core import crawl

    session = MagicMock()
    mock_build.return_value = session

    # robots.txt disallows /private/*
    robots_resp = MagicMock()
    robots_resp.ok = True
    robots_resp.status_code = 200
    robots_resp.text = "User-agent: *\nDisallow: /private/\n"
    robots_resp.content = robots_resp.text.encode()
    robots_resp.headers = {"content-type": "text/plain"}
    session.get.return_value = robots_resp

    seed_html = textwrap.dedent("""
    <html><head><title>Home</title></head>
    <body><main>
      <p>This page has plenty of content for the min-words filter to pass cleanly.</p>
      <a href="/private/secret">private</a>
    </main></body></html>
    """)
    secret_html = textwrap.dedent("""
    <html><head><title>Secret</title></head>
    <body><main>
      <p>Highly confidential content with enough words to pass the filter for testing.</p>
    </main></body></html>
    """)
    by_url = {
        "https://example.com/": _mock_resp(seed_html),
        "https://example.com/private/secret": _mock_resp(secret_html),
    }
    mock_fetch.side_effect = lambda session, url, timeout: by_url.get(
        url, _mock_resp("notfound", ok=False, status=404)
    )

    result = crawl(
        base_url="https://example.com/",
        out_dir=str(tmp_path / "out"),
        use_sitemap=False,
        max_pages=10,
        min_words=5,
    )
    # Only the seed should be saved — /private/secret is robots-blocked.
    assert result.pages_saved == 1
    assert result.robots_respected is True
    assert result.robots_bypassed_count == 0


@patch("markcrawl.core._HAS_HTTPX", False)
@patch("markcrawl.core.fetch")
@patch("markcrawl.core.build_session")
def test_e2e_bypass_unlocks_disallowed_pages(mock_build, mock_fetch, tmp_path):
    """respect_robots=False fetches Disallowed pages and audits the count."""
    from markcrawl.core import crawl

    session = MagicMock()
    mock_build.return_value = session

    robots_resp = MagicMock()
    robots_resp.ok = True
    robots_resp.status_code = 200
    robots_resp.text = "User-agent: *\nDisallow: /private/\n"
    robots_resp.content = robots_resp.text.encode()
    robots_resp.headers = {"content-type": "text/plain"}
    session.get.return_value = robots_resp

    seed_html = textwrap.dedent("""
    <html><head><title>Home</title></head>
    <body><main>
      <p>This page has plenty of content for the min-words filter to pass cleanly.</p>
      <a href="/private/secret">private</a>
    </main></body></html>
    """)
    secret_html = textwrap.dedent("""
    <html><head><title>Secret</title></head>
    <body><main>
      <p>Unique confidential content for the secret page passing the min-words filter.</p>
    </main></body></html>
    """)
    by_url = {
        "https://example.com/": _mock_resp(seed_html),
        "https://example.com/private/secret": _mock_resp(secret_html),
    }
    mock_fetch.side_effect = lambda session, url, timeout: by_url.get(
        url, _mock_resp("notfound", ok=False, status=404)
    )

    result = crawl(
        base_url="https://example.com/",
        out_dir=str(tmp_path / "out"),
        use_sitemap=False,
        max_pages=10,
        min_words=5,
        respect_robots=False,
    )
    # Both pages should be saved now, and the bypass count should
    # reflect the URL we wouldn't have fetched otherwise.
    assert result.pages_saved == 2
    assert result.robots_respected is False
    assert result.robots_bypassed_count == 1

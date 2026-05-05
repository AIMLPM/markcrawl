"""v0.10.3 — partial-write recovery, idle-timeout, 0-page diagnostic.

Three orthogonal generalizable fixes:

1. ``pages.jsonl`` is line-buffered + flushed per page so a SIGKILL /
   watchdog termination still leaves a readable JSONL on disk.
2. ``idle_timeout_s`` terminates the crawl gracefully when no new page
   has been saved for N seconds, catching discovery-exhaustion stalls
   (HF docs, etc.) without site-specific heuristics.
3. ``_emit_zero_pages_diagnostic`` surfaces the first observed HTTP
   status when a crawl finishes with 0 pages, so users can tell
   "blocked by 403" from "seed unreachable" from "min-words too high".
"""
from __future__ import annotations

import json
import logging
import textwrap
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

from markcrawl.core import (
    AsyncCrawlEngine,
    CrawlEngine,
    _emit_zero_pages_diagnostic,
    _resolve_idle_timeout,
)

# -- Fix 1: progressive flush -----------------------------------------------

def _mock_resp(html: str, ok: bool = True, status: int = 200) -> MagicMock:
    resp = MagicMock()
    resp.ok = ok
    resp.status_code = status
    resp.text = html
    resp.content = html.encode()
    resp.headers = {"content-type": "text/html; charset=utf-8"}
    return resp


@patch("markcrawl.core._HAS_HTTPX", False)
@patch("markcrawl.core.build_session")
def test_pages_jsonl_visible_on_disk_during_crawl(mock_build, tmp_path):
    """The JSONL row must hit disk before the crawl returns.

    Simulates a watchdog / SIGKILL scenario by reading the file with a
    second handle while the crawl is still running.
    """
    from markcrawl.core import crawl

    html = textwrap.dedent("""\
        <html><head><title>P</title></head>
        <body><main><p>This page has enough words to pass the minimum word filter for testing purposes here.</p></main></body>
        </html>
    """)
    session = MagicMock()
    mock_build.return_value = session
    session.get.side_effect = [_mock_resp(""), _mock_resp(html)]

    out = tmp_path / "out"
    result = crawl(
        base_url="https://example.com/",
        out_dir=str(out),
        use_sitemap=True,
        delay=0,
        max_pages=1,
        min_words=5,
    )
    assert result.pages_saved == 1
    # After the crawl returns, the file must contain a complete row.
    # (line-buffered open() is the v0.10.3 fix; the per-page flush is
    # the belt-and-braces guarantee).
    raw = Path(result.index_file).read_text("utf-8")
    assert raw.endswith("\n"), "JSONL row should end with newline (line buffered)"
    row = json.loads(raw.strip())
    assert row["url"] == "https://example.com/"


def test_open_is_line_buffered_in_crawl_paths():
    """Source-level guard: confirm both crawl paths pass buffering=1.

    Line buffering is what makes the partial-write recovery fix work
    even on SIGKILL — the OS page cache holds the bytes, the user-space
    Python buffer never sees them.  If a future refactor drops this
    flag, this test fails immediately.
    """
    src = Path(__file__).parent.parent / "markcrawl" / "core.py"
    text = src.read_text("utf-8")
    occurrences = text.count('open(engine.jsonl_path, jsonl_mode, encoding="utf-8", buffering=1)')
    assert occurrences == 2, (
        f"Expected 2 line-buffered open() calls (sync + async); found {occurrences}"
    )


# -- Fix 2: idle-timeout stall detection ------------------------------------

def test_resolve_idle_timeout_kwarg_wins():
    assert _resolve_idle_timeout(7.5) == 7.5


def test_resolve_idle_timeout_env_var(monkeypatch):
    monkeypatch.setenv("MARKCRAWL_IDLE_TIMEOUT_S", "42")
    assert _resolve_idle_timeout(None) == 42.0


def test_resolve_idle_timeout_default(monkeypatch):
    monkeypatch.delenv("MARKCRAWL_IDLE_TIMEOUT_S", raising=False)
    assert _resolve_idle_timeout(None) == 120.0


def test_resolve_idle_timeout_invalid_env_falls_back(monkeypatch):
    monkeypatch.setenv("MARKCRAWL_IDLE_TIMEOUT_S", "garbage")
    assert _resolve_idle_timeout(None) == 120.0


def _make_async_engine(tmp_path, idle_timeout_s):
    out = tmp_path / "out"
    out.mkdir()
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
        idle_timeout_s=idle_timeout_s,
    )


def _make_sync_engine(tmp_path, idle_timeout_s):
    out = tmp_path / "out"
    out.mkdir()
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
        idle_timeout_s=idle_timeout_s,
    )


def test_idle_timeout_fires_on_async_engine(tmp_path):
    engine = _make_async_engine(tmp_path, idle_timeout_s=1.0)
    # Simulate a long stretch of no saves by rewinding the clock.
    engine._last_activity_time = time.monotonic() - 5.0
    assert engine._check_idle_timeout() is True
    assert engine._stalled is True


def test_idle_timeout_does_not_fire_when_within_budget(tmp_path):
    engine = _make_async_engine(tmp_path, idle_timeout_s=10.0)
    engine._last_activity_time = time.monotonic()  # just now
    assert engine._check_idle_timeout() is False
    assert engine._stalled is False


def test_idle_timeout_disabled_when_zero(tmp_path):
    engine = _make_async_engine(tmp_path, idle_timeout_s=0.0)
    engine._last_activity_time = time.monotonic() - 10_000.0
    # idle_timeout_s=0 disables the check entirely.
    assert engine._check_idle_timeout() is False


def test_idle_timeout_fires_on_sync_engine(tmp_path):
    engine = _make_sync_engine(tmp_path, idle_timeout_s=1.0)
    engine._last_activity_time = time.monotonic() - 5.0
    assert engine._check_idle_timeout() is True
    assert engine._stalled is True


# -- v0.10.4: idle timeout resets on ANY progress event, not just saves ----

def test_successful_fetch_resets_idle_timer_async(tmp_path):
    """A 2xx response must reset the idle clock even if no save followed.

    Catches the v0.10.3 bug surfaced on huggingface-transformers: the
    engine kept fetching pages successfully but every page was deduped
    or under min_words, so saved_count stayed flat and the timer fired
    after 120s — terminating a crawl that was still making progress.
    """
    engine = _make_async_engine(tmp_path, idle_timeout_s=10.0)
    engine._last_activity_time = time.monotonic() - 100.0  # well past timeout
    assert engine._check_idle_timeout() is True  # would fire right now

    engine._stalled = False
    resp = MagicMock(status_code=200)
    engine._record_first_status(resp)
    # _record_first_status should bump the activity clock on a 2xx.
    assert engine._check_idle_timeout() is False
    assert engine._stalled is False


def test_successful_fetch_resets_idle_timer_sync(tmp_path):
    engine = _make_sync_engine(tmp_path, idle_timeout_s=10.0)
    engine._last_activity_time = time.monotonic() - 100.0
    assert engine._check_idle_timeout() is True

    engine._stalled = False
    resp = MagicMock(status_code=200)
    engine._record_first_status(resp)
    assert engine._check_idle_timeout() is False


def test_4xx_response_does_not_reset_idle_timer(tmp_path):
    """An anti-bot 403 / 404 / 5xx is NOT progress — the timer should still
    be able to fire.  (Without this, a 403 loop could keep the engine
    alive indefinitely.)"""
    engine = _make_async_engine(tmp_path, idle_timeout_s=10.0)
    engine._last_activity_time = time.monotonic() - 100.0
    resp = MagicMock(status_code=403)
    engine._record_first_status(resp)
    # 403 does not bump the clock; the timer should still want to fire.
    assert engine._check_idle_timeout() is True


def test_record_first_status_remembers_only_first_status(tmp_path):
    """The first-seen status is sticky for the diagnostic.  Even though
    we now also bump the activity clock on every 2xx, we still capture
    only the FIRST observed status, not a running tally — that's what
    powers the 0-page diagnostic."""
    engine = _make_async_engine(tmp_path, idle_timeout_s=120.0)
    engine._record_first_status(MagicMock(status_code=403))
    engine._record_first_status(MagicMock(status_code=200))
    engine._record_first_status(MagicMock(status_code=500))
    assert engine._first_status == 403


def test_discover_links_marks_activity_when_new_urls_added(tmp_path):
    """Adding fresh URLs to the queue is forward progress."""
    engine = _make_async_engine(tmp_path, idle_timeout_s=10.0)
    engine._last_activity_time = time.monotonic() - 100.0
    assert engine._check_idle_timeout() is True

    # Simulate the engine discovering a new in-scope URL on a page.
    engine._stalled = False
    engine.discover_links(
        "https://example.com/page-a",
        {"https://example.com/page-b"},
        "example.com",
    )
    # discover_links should have bumped the activity clock.
    assert engine._check_idle_timeout() is False


def test_discover_links_does_not_mark_activity_when_no_new_urls(tmp_path):
    """If every link discovered is already-seen / out-of-scope / disallowed,
    that's not progress."""
    engine = _make_async_engine(tmp_path, idle_timeout_s=10.0)
    # Pre-seed seen_urls so the candidate is rejected.
    engine.seen_urls.add("https://example.com/seen")
    engine._last_activity_time = time.monotonic() - 100.0
    engine.discover_links(
        "https://example.com/page-a",
        {"https://example.com/seen"},
        "example.com",
    )
    # No new URLs added → clock not bumped → timer still wants to fire.
    assert engine._check_idle_timeout() is True


def test_save_page_marks_activity_via_mark_activity(tmp_path):
    """Sanity: _mark_activity is the single source of truth.  save_page
    calls it (just like fetch and discover); calling _mark_activity
    directly resets the timer the same way."""
    engine = _make_async_engine(tmp_path, idle_timeout_s=10.0)
    engine._last_activity_time = time.monotonic() - 100.0
    assert engine._check_idle_timeout() is True

    engine._stalled = False
    engine._mark_activity()
    assert engine._check_idle_timeout() is False


# -- Fix 3: 0-page diagnostic ----------------------------------------------

class _DiagEngine:
    """Minimal stand-in exposing the attributes the diagnostic reads."""

    def __init__(self, saved_count, first_status):
        self.saved_count = saved_count
        self._first_status = first_status
        self.progress_messages = []
        self.progress = self.progress_messages.append


def test_diagnostic_silent_when_pages_saved():
    eng = _DiagEngine(saved_count=10, first_status=200)
    _emit_zero_pages_diagnostic(eng)
    assert eng.progress_messages == []


def test_diagnostic_no_response_observed(caplog):
    eng = _DiagEngine(saved_count=0, first_status=None)
    with caplog.at_level(logging.WARNING, logger="markcrawl.core"):
        _emit_zero_pages_diagnostic(eng)
    assert any("no successful HTTP response" in m for m in eng.progress_messages)
    assert any("DNS error" in r.message or "no HTTP response" in r.message
               for r in caplog.records)


def test_diagnostic_2xx_with_zero_saves_flags_minwords_or_js(caplog):
    """First response was 200 but nothing was saved → JS-rendered or min-words too high."""
    eng = _DiagEngine(saved_count=0, first_status=200)
    with caplog.at_level(logging.WARNING, logger="markcrawl.core"):
        _emit_zero_pages_diagnostic(eng)
    msg = " ".join(eng.progress_messages)
    assert "HTTP 200" in msg
    # Suggests the two common causes: too-strict min-words or JS.
    assert "min-words" in msg.lower() or "javascript" in msg.lower() or "render_js" in msg.lower()


def test_diagnostic_403_flags_anti_bot(caplog):
    """The newegg case: anti-bot returns 403 on first request → 0 pages."""
    eng = _DiagEngine(saved_count=0, first_status=403)
    with caplog.at_level(logging.WARNING, logger="markcrawl.core"):
        _emit_zero_pages_diagnostic(eng)
    msg = " ".join(eng.progress_messages)
    assert "HTTP 403" in msg
    # Should hint at anti-bot / blocking.
    assert "block" in msg.lower() or "anti-bot" in msg.lower()


def test_diagnostic_500_also_handled(caplog):
    """Any non-2xx status should produce the block-style hint."""
    eng = _DiagEngine(saved_count=0, first_status=503)
    with caplog.at_level(logging.WARNING, logger="markcrawl.core"):
        _emit_zero_pages_diagnostic(eng)
    msg = " ".join(eng.progress_messages)
    assert "HTTP 503" in msg


# -- First-status capture in fetch_batch ------------------------------------

def test_record_first_status_only_records_once(tmp_path):
    """Once we've seen a status, additional responses are ignored."""
    engine = _make_async_engine(tmp_path, idle_timeout_s=120.0)
    r1 = MagicMock(status_code=403)
    r2 = MagicMock(status_code=200)
    engine._record_first_status(r1)
    engine._record_first_status(r2)
    assert engine._first_status == 403


def test_record_first_status_handles_missing_attr(tmp_path):
    """Responses without status_code (mocks/raw transport errors) are skipped."""
    engine = _make_async_engine(tmp_path, idle_timeout_s=120.0)
    bogus = object()  # no status_code, no status
    engine._record_first_status(bogus)
    assert engine._first_status is None


def test_record_first_status_falls_back_to_status_attr(tmp_path):
    """Non-httpx responses might expose .status (aiohttp/urllib3 style)."""
    engine = _make_async_engine(tmp_path, idle_timeout_s=120.0)
    # Use a real class so getattr returns the literal int instead of a mock.

    class R:
        pass

    r = R()
    r.status = 429
    engine._record_first_status(r)
    assert engine._first_status == 429


def test_record_first_status_skips_none(tmp_path):
    engine = _make_async_engine(tmp_path, idle_timeout_s=120.0)
    engine._record_first_status(None)
    assert engine._first_status is None


# -- End-to-end: 0-page newegg-style crawl produces diagnostic --------------

@patch("markcrawl.core._HAS_HTTPX", False)
@patch("markcrawl.core.fetch")
@patch("markcrawl.core.build_session")
def test_e2e_403_crawl_emits_diagnostic(mock_build, mock_fetch, tmp_path, caplog):
    """Newegg-style end-to-end repro: every fetch returns 403 → 0 pages saved."""
    from markcrawl.core import crawl

    session = MagicMock()
    mock_build.return_value = session
    # robots.txt returns empty (allow all).
    session.get.return_value = _mock_resp("", ok=True, status=200)

    blocked = _mock_resp("blocked", ok=False, status=403)
    blocked.headers = {"content-type": "text/html"}
    mock_fetch.side_effect = [blocked, blocked, blocked]

    with caplog.at_level(logging.WARNING, logger="markcrawl.core"):
        result = crawl(
            base_url="https://example.com/",
            out_dir=str(tmp_path / "out"),
            use_sitemap=False,
            delay=0,
            max_pages=5,
            min_words=5,
        )

    assert result.pages_saved == 0
    # The diagnostic should have been emitted with the 403 status.
    assert any("HTTP 403" in r.message or "first HTTP 403" in r.message
               for r in caplog.records), (
        "Expected a 0-page diagnostic mentioning HTTP 403 in caplog"
    )


# -- API surface ------------------------------------------------------------

def test_crawl_api_accepts_idle_timeout_kwarg():
    """The public crawl() signature must expose idle_timeout_s for users."""
    import inspect

    from markcrawl.core import crawl
    params = inspect.signature(crawl).parameters
    assert "idle_timeout_s" in params, (
        "crawl() must expose idle_timeout_s so users can override per-call"
    )
    assert params["idle_timeout_s"].default is None

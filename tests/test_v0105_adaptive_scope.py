"""v0.10.5 — adaptive scope broadening.

When the crawl exhausts its narrow auto-derived scope with budget
remaining, the engine attempts one-level broadening (e.g.
``/docs/concepts/*`` → ``/docs/*``) before giving up.  Guarded by:

* Scope must have been auto-derived (user-explicit ``include_paths``
  is respected as intent, never mutated).
* Site must classify as ``docs`` or ``apiref``.  Generic / ecommerce
  / blog stay narrow — we don't auto-broaden into marketing or
  product UI as if it were content.
* Broadening must not land at whole-host (``/*``).
* Capped at ``_max_broaden_events`` (default 2) per crawl.
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

from markcrawl.core import (
    AsyncCrawlEngine,
    CrawlEngine,
    _compute_broader_scope,
)

# ---------- Helpers --------------------------------------------------------

def _make_async_engine(tmp_path, *, include_paths=None, site_class="docs",
                      scope_auto_broaden=True):
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
        include_paths=include_paths,
        site_class=site_class,
        scope_auto_broaden=scope_auto_broaden,
    )


def _make_sync_engine(tmp_path, *, include_paths=None, site_class="docs",
                     scope_auto_broaden=True):
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
        include_paths=include_paths,
        site_class=site_class,
        scope_auto_broaden=scope_auto_broaden,
    )


# ---------- _compute_broader_scope ----------------------------------------

def test_compute_broader_scope_two_segment():
    """Standard case — kubernetes-style two-segment seed."""
    assert _compute_broader_scope(["/docs/concepts/*"]) == ["/docs/*"]


def test_compute_broader_scope_three_segment():
    """HF-style three-segment seed."""
    assert _compute_broader_scope(["/docs/transformers/v4/*"]) == ["/docs/transformers/*"]


def test_compute_broader_scope_refuses_whole_host():
    """A single-segment scope can't broaden — would be /*."""
    assert _compute_broader_scope(["/docs/*"]) is None
    assert _compute_broader_scope(["/book/*"]) is None


def test_compute_broader_scope_refuses_tier0_dual():
    """The Tier-0 dual pattern (``/seg`` + ``/seg/*``) can't broaden either."""
    assert _compute_broader_scope(["/learn", "/learn/*"]) is None


def test_compute_broader_scope_handles_empty():
    """No scope at all — nothing to broaden."""
    assert _compute_broader_scope([]) is None


def test_compute_broader_scope_locale_segment():
    """Locale-prefixed seed: /us/en/* → /us/*."""
    assert _compute_broader_scope(["/us/en/*"]) == ["/us/*"]


# ---------- _try_broaden_scope guardrails ---------------------------------

def test_broaden_refused_when_scope_not_auto_derived(tmp_path):
    """Explicit user include_paths must be respected."""
    engine = _make_async_engine(
        tmp_path, include_paths=["/docs/concepts/*"],
        site_class="docs", scope_auto_broaden=False,
    )
    assert engine._try_broaden_scope("example.com") is False
    assert engine.include_paths == ["/docs/concepts/*"]
    assert engine._broaden_count == 0


def test_broaden_refused_for_non_docs_site(tmp_path):
    """Generic / ecommerce / blog don't auto-broaden — too risky."""
    for klass in ("generic", "ecommerce", "blog", "wiki"):
        engine = _make_async_engine(
            tmp_path, include_paths=["/cat/X/*"],
            site_class=klass, scope_auto_broaden=True,
        )
        assert engine._try_broaden_scope("example.com") is False, (
            f"site_class={klass!r} should refuse auto-broadening"
        )


def test_broaden_allowed_for_apiref(tmp_path):
    """apiref class also gets adaptive broadening (it's docs-shaped)."""
    engine = _make_async_engine(
        tmp_path, include_paths=["/api/v1/users/*"],
        site_class="apiref", scope_auto_broaden=True,
    )
    assert engine._try_broaden_scope("api.example.com") is True
    assert engine.include_paths == ["/api/v1/*"]


def test_broaden_caps_at_max_events(tmp_path):
    """After _max_broaden_events firings, we stop broadening."""
    engine = _make_async_engine(
        tmp_path, include_paths=["/a/b/c/*"], site_class="docs",
    )
    assert engine._max_broaden_events == 2
    # First broaden: /a/b/c/* → /a/b/*
    assert engine._try_broaden_scope("ex.com") is True
    assert engine.include_paths == ["/a/b/*"]
    # Second broaden: /a/b/* → /a/*
    assert engine._try_broaden_scope("ex.com") is True
    assert engine.include_paths == ["/a/*"]
    # Third broaden: refused (cap hit, even though /a/* → /* would be
    # blocked by the whole-host guardrail anyway)
    assert engine._try_broaden_scope("ex.com") is False
    assert engine._broaden_count == 2


def test_broaden_refused_when_already_at_whole_host_boundary(tmp_path):
    """``/docs/*`` can't broaden further — would be ``/*``."""
    engine = _make_async_engine(
        tmp_path, include_paths=["/docs/*"], site_class="docs",
    )
    assert engine._try_broaden_scope("ex.com") is False
    assert engine.include_paths == ["/docs/*"]


def test_broaden_records_scope_history(tmp_path):
    """Each successful broadening appends to scope_history."""
    engine = _make_async_engine(
        tmp_path, include_paths=["/docs/concepts/*"], site_class="docs",
    )
    assert engine.scope_history == [["/docs/concepts/*"]]
    engine._try_broaden_scope("ex.com")
    assert engine.scope_history == [["/docs/concepts/*"], ["/docs/*"]]


def test_broaden_replays_filtered_urls_now_in_scope(tmp_path):
    """URLs filtered under narrow scope get requeued when scope opens."""
    engine = _make_async_engine(
        tmp_path, include_paths=["/docs/concepts/*"], site_class="docs",
    )
    # Simulate URLs that were filtered under /docs/concepts/* but are
    # in /docs/* (would pass after broadening).
    engine._filtered_by_scope.update({
        "https://ex.com/docs/tasks/install",
        "https://ex.com/docs/reference/api",
        "https://ex.com/docs/concepts/architecture",  # would already pass narrow
    })
    assert engine._try_broaden_scope("ex.com") is True
    # All three should be requeued now (broader scope /docs/* matches all).
    requeued = list(engine.to_visit)
    assert "https://ex.com/docs/tasks/install" in requeued
    assert "https://ex.com/docs/reference/api" in requeued
    # The set should be drained.
    assert len(engine._filtered_by_scope) == 0


def test_broaden_does_not_replay_seen_urls(tmp_path):
    """URLs already in seen_urls aren't requeued by replay."""
    engine = _make_async_engine(
        tmp_path, include_paths=["/docs/concepts/*"], site_class="docs",
    )
    engine.seen_urls.add("https://ex.com/docs/tasks/install")
    engine._filtered_by_scope.update({
        "https://ex.com/docs/tasks/install",  # already seen
        "https://ex.com/docs/tasks/upgrade",
    })
    engine._try_broaden_scope("ex.com")
    requeued = list(engine.to_visit)
    assert "https://ex.com/docs/tasks/install" not in requeued
    assert "https://ex.com/docs/tasks/upgrade" in requeued


def test_broaden_respects_exclude_paths_after_replay(tmp_path):
    """An exclude_paths-rejected URL stays rejected after broadening,
    even though the include_paths widening would otherwise pass it."""
    engine = _make_async_engine(
        tmp_path, include_paths=["/docs/concepts/*"], site_class="docs",
    )
    engine.exclude_paths = ["/docs/legacy/*"]
    engine._filtered_by_scope.update({
        "https://ex.com/docs/tasks/install",      # passes both filters
        "https://ex.com/docs/legacy/old-page",    # rejected by exclude_paths
    })
    engine._try_broaden_scope("ex.com")
    requeued = list(engine.to_visit)
    assert "https://ex.com/docs/tasks/install" in requeued
    assert "https://ex.com/docs/legacy/old-page" not in requeued


# ---------- Sync engine parity --------------------------------------------

def test_sync_engine_broadens_too(tmp_path):
    """Sync engine has the same broadening behavior as async."""
    engine = _make_sync_engine(
        tmp_path, include_paths=["/docs/concepts/*"], site_class="docs",
    )
    assert engine._try_broaden_scope("ex.com") is True
    assert engine.include_paths == ["/docs/*"]


# ---------- discover_links stashes filtered URLs --------------------------

def test_discover_links_stashes_filtered_urls(tmp_path):
    """Links rejected ONLY by include_paths (path_excluded) get stashed
    for potential broadening, not silently dropped."""
    engine = _make_async_engine(
        tmp_path, include_paths=["/docs/concepts/*"], site_class="docs",
    )
    # Set up internals discover_links needs
    engine.visited_for_links = set()
    engine.seen_urls = set()
    engine._seed_urls = set()
    links = {
        "https://ex.com/docs/concepts/intro",   # passes scope
        "https://ex.com/docs/tasks/install",    # rejected by include_paths
        "https://ex.com/blog/post",             # rejected by include_paths
    }
    engine.discover_links("https://ex.com/seed", links, "ex.com")
    # The two out-of-scope but in-host URLs should be stashed.
    assert "https://ex.com/docs/tasks/install" in engine._filtered_by_scope
    assert "https://ex.com/blog/post" in engine._filtered_by_scope
    # The in-scope URL went into to_visit.
    assert "https://ex.com/docs/concepts/intro" in list(engine.to_visit)


def test_discover_links_does_not_stash_when_not_auto_broaden(tmp_path):
    """Memory hygiene — when broadening is off, don't accumulate the set."""
    engine = _make_async_engine(
        tmp_path, include_paths=["/docs/concepts/*"], site_class="docs",
        scope_auto_broaden=False,
    )
    engine.visited_for_links = set()
    engine.seen_urls = set()
    engine._seed_urls = set()
    engine.discover_links(
        "https://ex.com/seed",
        {"https://ex.com/docs/tasks/install"},
        "ex.com",
    )
    assert engine._filtered_by_scope == set()


# ---------- End-to-end integration via crawl() ----------------------------

def _mock_resp(html, ok=True, status=200):
    resp = MagicMock()
    resp.ok = ok
    resp.status_code = status
    resp.text = html
    resp.content = html.encode()
    resp.headers = {"content-type": "text/html; charset=utf-8"}
    return resp


@patch("markcrawl.core._HAS_HTTPX", False)
@patch("markcrawl.core.fetch")
@patch("markcrawl.core.build_session")
def test_e2e_kubernetes_style_broadening(mock_build, mock_fetch, tmp_path):
    """Simulate the kubernetes-docs case end-to-end.

    Seed yields scope ``/docs/concepts/*``.  The seed page links to two
    sibling sections (``/docs/tasks/`` and ``/docs/reference/``) that
    only become reachable after broadening to ``/docs/*``.
    """
    from markcrawl.core import crawl

    session = MagicMock()
    mock_build.return_value = session
    session.get.return_value = _mock_resp("")  # robots.txt empty

    seed_html = """
    <html><head><title>Concepts</title></head>
    <body><main>
      <p>This page has plenty of content for the min-words filter to pass cleanly here.</p>
      <a href="/docs/concepts/intro">intro</a>
      <a href="/docs/tasks/install">install</a>
      <a href="/docs/reference/api">api</a>
    </main></body></html>
    """
    def _page(unique_marker):
        return f"""
        <html><head><title>{unique_marker}</title></head>
        <body><main>
          <p>Unique content for {unique_marker} so dedup doesn't collapse pages with enough min-words filler.</p>
        </main></body></html>
        """
    by_url = {
        "https://kubernetes.io/docs/concepts/": _mock_resp(seed_html),
        "https://kubernetes.io/docs/concepts/intro": _mock_resp(_page("intro")),
        "https://kubernetes.io/docs/tasks/install": _mock_resp(_page("install")),
        "https://kubernetes.io/docs/reference/api": _mock_resp(_page("api")),
    }
    mock_fetch.side_effect = lambda session, url, timeout: by_url.get(
        url, _mock_resp("notfound", ok=False, status=404)
    )

    result = crawl(
        base_url="https://kubernetes.io/docs/concepts/",
        out_dir=str(tmp_path / "out"),
        use_sitemap=False,
        max_pages=10,
        min_words=5,
    )

    # All four should be saved (seed + intro inside /docs/concepts/*,
    # then install + api after broadening to /docs/*).
    assert result.pages_saved == 4, (
        f"expected 4, got {result.pages_saved}; scope_history={result.scope_history}"
    )
    # The scope must have been broadened from /docs/concepts/* to /docs/*.
    assert result.scope_history == [["/docs/concepts/*"], ["/docs/*"]]


@patch("markcrawl.core._HAS_HTTPX", False)
@patch("markcrawl.core.fetch")
@patch("markcrawl.core.build_session")
def test_e2e_explicit_include_paths_not_broadened(mock_build, mock_fetch, tmp_path):
    """User-explicit include_paths is respected, never mutated."""
    from markcrawl.core import crawl

    session = MagicMock()
    mock_build.return_value = session
    session.get.return_value = _mock_resp("")

    seed_html = """
    <html><head><title>Concepts</title></head>
    <body><main>
      <p>This page has plenty of content for the min-words filter to pass cleanly here.</p>
      <a href="/docs/concepts/intro">intro</a>
      <a href="/docs/tasks/install">install</a>
    </main></body></html>
    """
    by_url = {
        "https://kubernetes.io/docs/concepts/": _mock_resp(seed_html),
        "https://kubernetes.io/docs/concepts/intro": _mock_resp(seed_html),
        "https://kubernetes.io/docs/tasks/install": _mock_resp(seed_html),
    }
    mock_fetch.side_effect = lambda session, url, timeout: by_url.get(
        url, _mock_resp("notfound", ok=False, status=404)
    )

    result = crawl(
        base_url="https://kubernetes.io/docs/concepts/",
        out_dir=str(tmp_path / "out"),
        use_sitemap=False,
        max_pages=10,
        min_words=5,
        include_paths=["/docs/concepts/*"],  # USER-EXPLICIT
    )

    # /docs/tasks/install must NOT be saved — user said /docs/concepts/* only.
    assert result.scope_history == [["/docs/concepts/*"]], (
        f"User-explicit scope must not be auto-broadened; got {result.scope_history}"
    )


# ---------- CrawlResult API ------------------------------------------------

def test_crawlresult_exposes_scope_history():
    """The new field is part of the public CrawlResult contract."""
    import inspect

    from markcrawl.core import CrawlResult
    fields = {f.name for f in CrawlResult.__dataclass_fields__.values()}
    assert "scope_history" in fields
    sig = inspect.signature(CrawlResult)
    assert "scope_history" in sig.parameters

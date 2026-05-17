"""Tests for the default aggregator-page URL filter (v0.11.1).

The filter rejects mdBook /print.html, Hugo /_print/, and similar
single-render-of-whole-tree pages during crawl-time URL filtering. These
pages have artificially high keyword density on almost any retrieval
query because they contain the entire docs tree on a single URL, so the
embedder ranks them above the dedicated chapter pages a user actually
wants.

Bench evidence motivating the filter: markcrawl returned /print.html in
49% of rust-book top-5 retrieval slots and /_print/ in 39% of
kubernetes-docs slots; all five other well-functioning competitors
return 0% on kubernetes-docs.
"""

from __future__ import annotations

import pytest

from markcrawl.core import (
    _DEFAULT_AGGREGATOR_PATH_PATTERNS,
    AsyncCrawlEngine,
    CrawlEngine,
)

# ---------- engine fixtures ----------------------------------------------

def _make_sync_engine(tmp_path, **kwargs):
    out = tmp_path / "out"
    out.mkdir(exist_ok=True)
    defaults = dict(
        out_dir=str(out), fmt="markdown", min_words=20, delay=0, timeout=10,
        concurrency=1, include_subdomains=False, user_agent="test",
        render_js=False, proxy=None, show_progress=False,
    )
    defaults.update(kwargs)
    return CrawlEngine(**defaults)


def _make_async_engine(tmp_path, **kwargs):
    out = tmp_path / "out"
    out.mkdir(exist_ok=True)
    defaults = dict(
        out_dir=str(out), fmt="markdown", min_words=20, delay=0, timeout=10,
        concurrency=1, include_subdomains=False, user_agent="test",
        proxy=None, show_progress=False,
    )
    defaults.update(kwargs)
    return AsyncCrawlEngine(**defaults)


# ---------- default patterns rejected ------------------------------------

# (URL, reason) pairs covering the observed bench failure modes.
_REJECTED_URLS = [
    ("https://doc.rust-lang.org/book/print.html", "mdBook print view"),
    ("https://example.com/print.html", "root-level print.html"),
    ("https://kubernetes.io/docs/concepts/_print/", "Hugo _print trailing slash"),
    ("https://kubernetes.io/docs/concepts/_print/index.html", "Hugo _print explicit index"),
    ("https://example.com/foo/_print", "Hugo _print bare path"),
    ("https://example.com/foo/print/index.html", "alternate single-page generator"),
]


@pytest.mark.parametrize("url, reason", _REJECTED_URLS)
def test_sync_engine_rejects_aggregator_by_default(tmp_path, url, reason):
    engine = _make_sync_engine(tmp_path)
    engine._seed_urls = set()
    assert engine.path_excluded(url), f"should reject {url} ({reason})"


@pytest.mark.parametrize("url, reason", _REJECTED_URLS)
def test_async_engine_rejects_aggregator_by_default(tmp_path, url, reason):
    engine = _make_async_engine(tmp_path)
    engine._seed_urls = set()
    assert engine.path_excluded(url), f"should reject {url} ({reason})"


# ---------- non-aggregator URLs pass through -----------------------------

_ACCEPTED_URLS = [
    "https://doc.rust-lang.org/book/ch12-02-reading-a-file.html",
    "https://kubernetes.io/docs/concepts/architecture/control-plane-node-communication/",
    "https://example.com/index.html",                # plain index.html is content, not aggregator
    "https://example.com/blueprint.html",             # 'print' substring inside a word — must not over-match
    "https://example.com/imprint/",                   # legal page; not aggregator
    "https://example.com/preprint.html",              # academic preprint; not aggregator
    "https://example.com/_printer-friendly/css.css",  # asset path containing _print as prefix-only
]


@pytest.mark.parametrize("url", _ACCEPTED_URLS)
def test_sync_engine_accepts_non_aggregator(tmp_path, url):
    engine = _make_sync_engine(tmp_path)
    engine._seed_urls = set()
    assert not engine.path_excluded(url), f"should NOT reject {url}"


# ---------- opt-out flag preserves aggregators ---------------------------

@pytest.mark.parametrize("url, reason", _REJECTED_URLS)
def test_sync_engine_include_aggregator_pages_allows_through(tmp_path, url, reason):
    engine = _make_sync_engine(tmp_path, include_aggregator_pages=True)
    engine._seed_urls = set()
    assert not engine.path_excluded(url), (
        f"with include_aggregator_pages=True, should allow {url} ({reason})"
    )


@pytest.mark.parametrize("url, reason", _REJECTED_URLS)
def test_async_engine_include_aggregator_pages_allows_through(tmp_path, url, reason):
    engine = _make_async_engine(tmp_path, include_aggregator_pages=True)
    engine._seed_urls = set()
    assert not engine.path_excluded(url), (
        f"with include_aggregator_pages=True, should allow {url} ({reason})"
    )


# ---------- composition with user-supplied filters -----------------------

def test_user_exclude_paths_still_applied(tmp_path):
    """User-supplied exclude_paths must still reject matching URLs even
    when aggregator filter is the primary default. Both sets compose."""
    engine = _make_sync_engine(tmp_path, exclude_paths=["/job/*"])
    engine._seed_urls = set()
    # User pattern rejects /job/*
    assert engine.path_excluded("https://example.com/job/listings")
    # Aggregator default still rejects /print.html
    assert engine.path_excluded("https://example.com/print.html")
    # Non-matching URL passes
    assert not engine.path_excluded("https://example.com/articles/foo")


def test_include_paths_with_aggregator_filter(tmp_path):
    """When include_paths is set, aggregator default applies first.
    A URL under include_paths but matching aggregator pattern is still
    rejected; a URL outside include_paths but not aggregator is
    rejected by the include filter, not the aggregator filter."""
    engine = _make_sync_engine(tmp_path, include_paths=["/docs/*"])
    engine._seed_urls = set()
    # Inside scope but is aggregator → rejected
    assert engine.path_excluded("https://example.com/docs/_print/index.html")
    # Inside scope, real content → allowed
    assert not engine.path_excluded("https://example.com/docs/getting-started")
    # Outside scope → rejected by include filter
    assert engine.path_excluded("https://example.com/blog/post-1")


def test_opt_out_with_user_exclude_paths(tmp_path):
    """include_aggregator_pages=True disables ONLY the aggregator defaults.
    User exclude_paths still apply."""
    engine = _make_sync_engine(
        tmp_path,
        include_aggregator_pages=True,
        exclude_paths=["/internal/*"],
    )
    engine._seed_urls = set()
    # Aggregator now allowed
    assert not engine.path_excluded("https://example.com/print.html")
    # User pattern still rejects
    assert engine.path_excluded("https://example.com/internal/secret")


# ---------- patterns constant invariants ---------------------------------

def test_default_patterns_are_a_tuple():
    """Constant must be immutable — patterns are part of the public-ish
    invariant surface and shouldn't be mutated at runtime."""
    assert isinstance(_DEFAULT_AGGREGATOR_PATH_PATTERNS, tuple)
    assert len(_DEFAULT_AGGREGATOR_PATH_PATTERNS) >= 4


def test_default_patterns_cover_observed_bench_failures():
    """Sanity check: the slam-dunk bench-observed cases must be covered."""
    import fnmatch
    for url_path, reason in [
        ("/book/print.html", "rust-book"),
        ("/docs/concepts/_print/", "kubernetes-docs trailing slash"),
        ("/docs/concepts/_print/index.html", "kubernetes-docs explicit index"),
    ]:
        assert any(
            fnmatch.fnmatch(url_path, pat)
            for pat in _DEFAULT_AGGREGATOR_PATH_PATTERNS
        ), f"no pattern matches {url_path} ({reason})"

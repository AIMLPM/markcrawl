"""Tests for path-similarity priority — BFS queue reordering by seed alignment.

The path priority is a "soft" optimization: it reorders the queue so on-section
links get crawled first, but never blocks any URL.  Worst-case is the same
as default BFS; best-case is dramatically better coverage on sub-section seeds.
"""

from __future__ import annotations

from markcrawl.core import CrawlEngine


def _make_engine(seed_path: str) -> CrawlEngine:
    """Build a minimal CrawlEngine and prime its seed_path_parts."""
    eng = CrawlEngine(
        out_dir="/tmp/_test_priority",
        fmt="markdown",
        min_words=20,
        delay=0,
        timeout=15,
        concurrency=1,
        include_subdomains=False,
        user_agent="test",
        render_js=False,
        proxy=None,
        show_progress=False,
        auto_path_priority=True,
    )
    eng._seed_path_parts = [p for p in seed_path.strip("/").split("/") if p]
    return eng


class TestPathPriority:
    def test_exact_match_scores_one(self):
        eng = _make_engine("/en-US/docs/Web/CSS")
        assert eng._path_priority("https://x.com/en-US/docs/Web/CSS/Reference/Properties/display") == 1.0

    def test_partial_prefix_scores_partial(self):
        eng = _make_engine("/en-US/docs/Web/CSS")
        # 3 of 4 segments match
        assert eng._path_priority("https://x.com/en-US/docs/Web/HTML") == 0.75

    def test_two_segment_match(self):
        eng = _make_engine("/en-US/docs/Web/CSS")
        # 2 of 4 segments
        assert abs(eng._path_priority("https://x.com/en-US/docs/Glossary/CSS") - 0.5) < 1e-9

    def test_locale_only_match(self):
        eng = _make_engine("/en-US/docs/Web/CSS")
        # 1 of 4
        assert eng._path_priority("https://x.com/en-US/blog/article") == 0.25

    def test_zero_match(self):
        eng = _make_engine("/en-US/docs/Web/CSS")
        assert eng._path_priority("https://x.com/fr/docs/Web/CSS") == 0.0

    def test_empty_seed_path_zero(self):
        eng = _make_engine("/")
        assert eng._path_priority("https://x.com/anything") == 0.0

    def test_short_seed_full_match(self):
        eng = _make_engine("/docs/transformers")
        assert eng._path_priority("https://x.com/docs/transformers/main_classes/pipelines") == 1.0
        assert eng._path_priority("https://x.com/docs/sagemaker") == 0.5

    def test_link_with_query_and_fragment(self):
        eng = _make_engine("/docs/transformers")
        assert eng._path_priority("https://x.com/docs/transformers/intro?ref=hn#section") == 1.0

    def test_link_path_shorter_than_seed(self):
        eng = _make_engine("/docs/transformers/index")
        # Link path /docs has only 1 segment matching out of 3 in seed
        assert abs(eng._path_priority("https://x.com/docs") - (1/3)) < 1e-9


class TestPriorityRespectsScopeHeuristic:
    """Priority should be a no-op when the seed isn't scopeable.
    Otherwise it can starve sibling sections via depth-first behavior."""

    def test_content_page_seed_disables_priority(self):
        """When seed is /stable/user_guide.html (scope returns None because
        derived path /stable has only 1 segment), priority should also
        return 0 for everything → falls back to BFS."""
        from markcrawl.core import CrawlEngine
        eng = CrawlEngine(
            out_dir="/tmp/_x", fmt="markdown", min_words=20, delay=0,
            timeout=15, concurrency=1, include_subdomains=False,
            user_agent="t", render_js=False, proxy=None, show_progress=False,
            auto_path_priority=True,
        )
        # Simulate setup_robots with a content-page seed
        from markcrawl.core import _auto_path_scope_from_seed
        derived = _auto_path_scope_from_seed("https://x.com/stable/user_guide.html")
        if derived:
            scope_pattern = derived[0].rstrip("*").rstrip("/")
            eng._seed_path_parts = [p for p in scope_pattern.strip("/").split("/") if p]
        # If derived is None, _seed_path_parts stays empty
        # Either way, priority should return 0 for any URL (including targets)
        assert eng._path_priority("https://x.com/stable/modules/linear_model") == 0.0

    def test_section_seed_keeps_priority_active(self):
        """Section seed (/docs/transformers/) → scope active → priority active."""
        from markcrawl.core import CrawlEngine, _auto_path_scope_from_seed
        eng = CrawlEngine(
            out_dir="/tmp/_x", fmt="markdown", min_words=20, delay=0,
            timeout=15, concurrency=1, include_subdomains=False,
            user_agent="t", render_js=False, proxy=None, show_progress=False,
            auto_path_priority=True,
        )
        derived = _auto_path_scope_from_seed("https://x.com/docs/transformers/")
        if derived:
            scope_pattern = derived[0].rstrip("*").rstrip("/")
            eng._seed_path_parts = [p for p in scope_pattern.strip("/").split("/") if p]
        # Should match for in-section URLs
        assert eng._path_priority("https://x.com/docs/transformers/pipelines") == 1.0
        # And drop for out-of-section
        assert eng._path_priority("https://x.com/blog/article") == 0.0

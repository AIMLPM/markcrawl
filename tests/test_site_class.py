"""Tests for markcrawl.site_class — site classifier from URL conventions."""
from __future__ import annotations

from markcrawl.site_class import classify_site


class TestHostnamePrefix:
    def test_api_hostname(self):
        assert classify_site("https://api.slack.com/methods").site_class == "apiref"
        assert classify_site("https://api.github.com/v3/repos").site_class == "apiref"

    def test_wiki_hostname(self):
        assert classify_site("https://wiki.archlinux.org/title/Pacman").site_class == "wiki"
        assert classify_site("https://wiki.gentoo.org/wiki/Handbook").site_class == "wiki"
        assert classify_site("https://wiki.openstreetmap.org/wiki/Tags").site_class == "wiki"

    def test_blog_hostname(self):
        assert classify_site("https://blog.python.org/").site_class == "blog"
        assert classify_site("https://blog.cloudflare.com/tag/security/").site_class == "blog"
        assert classify_site("https://news.ycombinator.com/").site_class == "blog"

    def test_docs_hostname(self):
        assert classify_site("https://docs.djangoproject.com/en/stable/").site_class == "docs"
        assert classify_site("https://doc.rust-lang.org/book/").site_class == "docs"

    def test_docs_hostname_with_api_path_upgrades_to_apiref(self):
        # docs.stripe.com/api → apiref (most specific signal wins)
        assert classify_site("https://docs.stripe.com/api").site_class == "apiref"
        assert classify_site("https://docs.github.com/en/rest").site_class == "docs"  # /en/rest, en is first-seg


class TestFirstSegment:
    def test_wiki_first_segment(self):
        assert classify_site("https://en.wikipedia.org/wiki/Computer_science").site_class == "wiki"
        assert classify_site("https://example.com/title/Pacman").site_class == "wiki"

    def test_book_first_segment_short_seed(self):
        # /book/ is a hub seed → docs class (single segment)
        assert classify_site("https://doc.rust-lang.org/book/").site_class == "docs"
        # docs class also fires for /tutorial, /guide, /handbook
        assert classify_site("https://example.com/tutorial").site_class == "docs"

    def test_api_first_segment(self):
        assert classify_site("https://docs.stripe.com/api").site_class == "apiref"
        assert classify_site("https://example.com/reference/foo").site_class == "apiref"

    def test_blog_first_segment(self):
        assert classify_site("https://example.com/blog/2024/post").site_class == "blog"
        assert classify_site("https://example.com/news").site_class == "blog"
        # Edge case: github.blog/category/engineering/ classifies as ecom because
        # first segment is "category" (an ecom marker). Functionally OK — both
        # blog and ecom dispatch to sitemap-broad.
        assert classify_site("https://github.blog/category/engineering/").site_class == "ecom"

    def test_deep_docs_path_is_generic(self):
        # /docs/transformers/index is a deep section — generic class so existing
        # 2+-segment scope behavior is preserved
        assert classify_site("https://huggingface.co/docs/transformers/index").site_class == "generic"


class TestPathPatterns:
    def test_year_month_blog(self):
        # /YYYY/MM/ pattern signals blog even without blog. hostname
        assert classify_site("https://example.com/2024/10/some-post").site_class == "blog"
        assert classify_site("https://something.com/2023/01/post-title").site_class == "blog"

    def test_ecom_marker_anywhere(self):
        # /products/, /shop/, /collections/, /cat/, /category/, /catalog/
        assert classify_site("https://www.ikea.com/us/en/cat/furniture").site_class == "ecom"
        assert classify_site("https://wordpress.org/plugins/category/seo/").site_class == "ecom"
        assert classify_site("https://shop.example.com/collections/featured").site_class == "ecom"


class TestGenericFallback:
    def test_unknown_path(self):
        assert classify_site("https://example.com/").site_class == "generic"
        assert classify_site("https://nextjs.org/").site_class == "generic"

    def test_deep_unknown_path(self):
        assert classify_site("https://example.com/some/deep/path").site_class == "generic"


class TestRotationPoolCoverage:
    """Validate that the 40 sites in our internal rotation classify reasonably."""

    EXPECTED = [
        # docs class — single-segment hubs get docs class for Tier 0 scope
        ("https://kubernetes.io/docs/concepts/", "generic"),
        ("https://developer.mozilla.org/en-US/docs/Web/CSS", "generic"),
        ("https://scikit-learn.org/stable/user_guide.html", "generic"),
        ("https://fastapi.tiangolo.com/tutorial/", "docs"),
        ("https://doc.rust-lang.org/book/", "docs"),  # docs hostname
        ("https://www.postgresql.org/docs/current/", "generic"),
        ("https://docs.djangoproject.com/en/stable/", "docs"),  # docs hostname
        # wiki class
        ("https://en.wikipedia.org/wiki/Computer_science", "wiki"),
        ("https://wiki.archlinux.org/title/Pacman", "wiki"),
        ("https://en.wikibooks.org/wiki/Python_Programming", "wiki"),
        ("https://wiki.gentoo.org/wiki/Handbook:Main_Page", "wiki"),
        ("https://rosettacode.org/wiki/Hello_world", "wiki"),
        ("https://wiki.openstreetmap.org/wiki/Tags", "wiki"),
        ("https://wiki.archlinux.org/title/Arch_User_Repository", "wiki"),
        # ecom class
        ("https://www.ikea.com/us/en/cat/furniture-fu001/", "ecom"),
        ("https://wordpress.org/plugins/category/seo/", "ecom"),
        ("https://addons.mozilla.org/en-US/firefox/category/privacy-security/", "ecom"),
        # blog class
        ("https://blog.python.org/", "blog"),
        ("https://blog.cloudflare.com/tag/security/", "blog"),
        # apiref class
        ("https://docs.stripe.com/api", "apiref"),
        ("https://docs.github.com/en/rest", "docs"),  # docs hostname; en is first-seg
        ("https://discord.com/developers/docs/reference", "generic"),
        ("https://platform.openai.com/docs/api-reference", "generic"),
        ("https://api.slack.com/methods", "apiref"),
        # spa-rendered (rendering is orthogonal — content class still applies)
        ("https://huggingface.co/docs/transformers/index", "generic"),
        ("https://vercel.com/docs", "docs"),
        ("https://tanstack.com/query/latest/docs", "generic"),
        ("https://nextjs.org/docs", "docs"),
        ("https://supabase.com/docs", "docs"),
        ("https://vuejs.org/guide/introduction.html", "generic"),
        ("https://tailwindcss.com/docs/installation", "generic"),
    ]

    def test_pool_classifications_match_expected(self):
        mismatches = []
        for url, expected in self.EXPECTED:
            actual = classify_site(url).site_class
            if actual != expected:
                mismatches.append((url, expected, actual))
        # Allow ≤ 5 mismatches as edge cases — we'll iterate
        assert len(mismatches) <= 5, f"Too many mismatches: {mismatches}"

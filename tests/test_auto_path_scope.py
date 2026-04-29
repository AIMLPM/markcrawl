"""Tests for _auto_path_scope_from_seed — derives include_paths from seed URL.

Heuristic: take the seed URL's path, drop trailing /index* if present,
return [path + '/*'] when there are >= 2 path segments. Returns None
for root or single-segment seeds (preserves whole-site crawl behavior).
"""

from __future__ import annotations

from markcrawl.core import _auto_path_scope_from_seed as derive


class TestAutoPathScope:
    def test_docs_subsection(self):
        # HF transformers: derives /docs/transformers/* (drops /index)
        assert derive("https://huggingface.co/docs/transformers/index") == ["/docs/transformers/*"]

    def test_deep_docs_path(self):
        # MDN: keeps the full /en-US/docs/Web/CSS path
        assert derive("https://developer.mozilla.org/en-US/docs/Web/CSS") == ["/en-US/docs/Web/CSS/*"]

    def test_trailing_slash_stripped(self):
        # k8s: trailing slash doesn't change the result
        assert derive("https://kubernetes.io/docs/concepts/") == ["/docs/concepts/*"]

    def test_ecommerce_deep_seed(self):
        # ikea: /us/en/cat/<X>/ — /cat/ marker triggers ecommerce path
        # (segments before marker → /us/en/* so sibling /us/en/p/<product> is reachable).
        # See TestEcommerceMarkers for the comprehensive cases.
        assert derive("https://www.ikea.com/us/en/cat/furniture-fu001/") == ["/us/en/*"]

    def test_root_url_returns_none(self):
        assert derive("https://example.com/") is None
        assert derive("https://example.com") is None

    def test_single_segment_non_docs_returns_none(self):
        # Single-segment seed without docs classification → no scope. Avoids
        # over-restricting sites like docs.stripe.com/api (queries span
        # /billing/, /connect/ etc.; locking to /api/* loses coverage).
        assert derive("https://example.com/blog") is None
        assert derive("https://docs.stripe.com/api") is None

    def test_single_segment_docs_class_scopes_to_segment(self):
        # Docs-class single-segment seeds (`/book/`, `/docs`, `/tutorial`)
        # benefit from scoping when the host bundles sibling projects (e.g.
        # doc.rust-lang.org has /book/, /std/, /reference/). Site classifier
        # gates this Tier 0 fix to docs-class only.
        assert derive("https://doc.rust-lang.org/book/") == ["/book", "/book/*"]
        assert derive("https://nextjs.org/docs") == ["/docs", "/docs/*"]
        assert derive("https://vercel.com/docs") == ["/docs", "/docs/*"]
        assert derive("https://fastapi.tiangolo.com/tutorial/") == ["/tutorial", "/tutorial/*"]

    def test_two_segments_minimum(self):
        # Exactly two segments — qualifies for scoping
        assert derive("https://example.com/a/b") == ["/a/b/*"]

    def test_index_html_dropped(self):
        # /docs/foo/index.html → /docs/foo/*
        assert derive("https://example.com/docs/foo/index.html") == ["/docs/foo/*"]
        assert derive("https://example.com/docs/foo/index.htm") == ["/docs/foo/*"]
        assert derive("https://example.com/docs/foo/index.php") == ["/docs/foo/*"]
        assert derive("https://example.com/docs/foo/index") == ["/docs/foo/*"]

    def test_not_index_suffix_preserved(self):
        # /docs/foo/intro (no /index, no extension) → /docs/foo/intro/*
        assert derive("https://example.com/docs/foo/intro") == ["/docs/foo/intro/*"]

    def test_content_filename_drops_to_parent(self):
        # /stable/user_guide.html (a content page, not /index) → /stable/*
        # Sibling pages like /stable/modules/* should be in scope.
        # Falls back to None when this leaves only 1 segment.
        assert derive("https://scikit-learn.org/stable/user_guide.html") is None
        # Deeper path: /a/b/page.html → /a/b/*
        assert derive("https://example.com/a/b/page.html") == ["/a/b/*"]
        # Other content extensions
        assert derive("https://example.com/a/b/page.php") == ["/a/b/*"]
        assert derive("https://example.com/a/b/page.aspx") == ["/a/b/*"]
        assert derive("https://example.com/a/b/page.htm") == ["/a/b/*"]

    def test_query_string_ignored(self):
        # Querystring + fragment must not affect path-derivation
        assert derive("https://example.com/docs/foo/?ref=hn#section") == ["/docs/foo/*"]

    def test_wiki_article_scopes_to_container(self):
        # /wiki/<article> — articles are siblings under /wiki/, so scope to
        # /wiki/* (catches siblings; excludes /index.php, /api.php that
        # mediawiki ships at the host root).
        assert derive("https://en.wikipedia.org/wiki/Computer_science") == ["/wiki/*"]
        assert derive("https://en.wikipedia.org/wiki/Machine_learning") == ["/wiki/*"]
        # Case-insensitive match; preserves the seed's casing for the scope
        # path so glob compares against URLs as fetched.
        assert derive("https://en.wikipedia.org/Wiki/Machine_learning") == ["/Wiki/*"]
        assert derive("https://example.com/wikipedia/Foo") == ["/wikipedia/*"]

    def test_title_article_scopes_to_container(self):
        # archlinux mediawiki uses /title/X (custom $wgArticlePath); IMDB
        # uses /title/tt1234 for movie pages. Both want sibling scope.
        assert derive("https://wiki.archlinux.org/title/Pacman") == ["/title/*"]
        assert derive("https://wiki.archlinux.org/title/Installation_guide") == ["/title/*"]
        assert derive("https://www.imdb.com/title/tt0111161") == ["/title/*"]

    def test_wiki_category_namespace_scopes_to_container(self):
        # gentoo seeds at /wiki/Category:Ports or /wiki/Handbook:Main_Page —
        # mediawiki namespaces are still under /wiki/, so /wiki/* is correct.
        assert derive("https://wiki.gentoo.org/wiki/Handbook:Main_Page") == ["/wiki/*"]
        assert derive("https://wiki.gentoo.org/wiki/Category:Ports") == ["/wiki/*"]

    def test_non_article_first_seg_is_normal(self):
        # /docs/concepts/ etc. proceed normally
        assert derive("https://example.com/docs/concepts") == ["/docs/concepts/*"]
        # /content-not-in-list/X still gets scoped
        assert derive("https://example.com/something/X") == ["/something/X/*"]


class TestEcommerceMarkers:
    """Detect /cat/, /category/, /products/, /shop/, /collections/ markers
    used as URL conventions by hundreds of ecommerce platforms.  Items are
    siblings *before* the marker, not children of it."""

    def test_ikea_style_cat_marker(self):
        # /us/en/cat/<X>/ → /us/en/* (products at /us/en/p/<slug> are siblings)
        assert derive("https://www.ikea.com/us/en/cat/furniture-fu001/") == ["/us/en/*"]
        # German variant
        assert derive("https://www.ikea.com/de/de/cat/wohnzimmer-29084/") == ["/de/de/*"]

    def test_shopify_style_products_marker(self):
        # /products/<slug> → marker at root → no scope (whole site)
        assert derive("https://example-shop.com/products/my-widget") is None
        # /collections/<X>/products/<Y> → marker at i=2 → /collections/<X>/*
        assert derive("https://shop.com/collections/spring-sale/products/x") == ["/collections/spring-sale/*"]

    def test_collections_marker(self):
        # Shopify uses /collections/ for category pages
        assert derive("https://shop.com/store/collections/featured/x") == ["/store/*"]

    def test_category_marker(self):
        # WooCommerce / Magento default
        assert derive("https://store.example.com/blog/category/news/post-1") == ["/blog/*"]
        assert derive("https://store.example.com/category/electronics") is None  # marker at root

    def test_shop_marker(self):
        # Etsy-style
        assert derive("https://example.com/store/shop/X") == ["/store/*"]

    def test_marker_case_insensitive(self):
        assert derive("https://x.com/US/EN/CAT/furniture") == ["/US/EN/*"]

    def test_no_marker_keeps_normal_scope(self):
        # /docs/concepts/ has no ecommerce marker — still scopes normally
        assert derive("https://kubernetes.io/docs/concepts/") == ["/docs/concepts/*"]
        # mdn paths similarly unaffected
        assert derive("https://developer.mozilla.org/en-US/docs/Web/CSS") == ["/en-US/docs/Web/CSS/*"]

    def test_deepest_marker_wins(self):
        # /shop/category/X has markers at i=0 (shop) and i=1 (category).
        # We use the DEEPEST marker — outer /shop/ is just a parent grouping;
        # inner /category/ is the leaf-level category index.  Scope = /shop/*.
        assert derive("https://example.com/shop/category/X") == ["/shop/*"]
        # Two markers further apart
        assert derive("https://example.com/store/products/category/X") == ["/store/products/*"]

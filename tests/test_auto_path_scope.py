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

    def test_single_segment_returns_none(self):
        # /blog → too shallow to scope; let the crawler do whole-site
        assert derive("https://example.com/blog") is None
        assert derive("https://example.com/blog/") is None

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

    def test_wiki_article_returns_none(self):
        # /wiki/<article> — articles are siblings, scope would block them
        assert derive("https://en.wikipedia.org/wiki/Computer_science") is None
        assert derive("https://en.wikipedia.org/wiki/Machine_learning") is None
        # Case-insensitive match
        assert derive("https://en.wikipedia.org/Wiki/Machine_learning") is None
        assert derive("https://example.com/wikipedia/Foo") is None

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

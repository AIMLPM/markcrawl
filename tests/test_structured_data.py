"""Structured data (JSON-LD) carried through to the caller.

A page's ``<script type="application/ld+json">`` blocks used to be parsed
and then dropped: only ``name`` / ``description`` (and FAQ pairs) were
folded into the page text.  These tests pin the new contract:

* ``markcrawl.structured`` exposes ``extract_structured_data``,
  ``find_items`` and ``job_posting_places``; none of them raise on bad
  input.
* Every crawled page carries ``PageData.structured_data`` (empty list
  when the page has no JSON-LD), filled the same way by the sync engine,
  the async engine and its process-pool extraction worker, whatever
  extractor is configured.
* ``pages.jsonl`` gains a ``structured_data`` key only when the page has
  JSON-LD, so rows for pages without it are unchanged.
"""
from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from markcrawl import PageData
from markcrawl.structured import (
    MAX_JSON_LD_BLOCK_BYTES,
    extract_structured_data,
    find_items,
    job_posting_places,
)

try:
    import httpx  # noqa: F401
    _HAS_HTTPX = True
except ImportError:  # pragma: no cover - depends on the environment
    _HAS_HTTPX = False

_skip_no_httpx = pytest.mark.skipif(not _HAS_HTTPX, reason="httpx not installed")


# ---------------------------------------------------------------------------
# Fixtures: recorded-shape HTML (no network)
# ---------------------------------------------------------------------------

# The shape a large payments company's careers page uses: one JobPosting
# in <head>, one Place, locality + country only.
JOB_POSTING = {
    "@context": "https://schema.org",
    "@type": "JobPosting",
    "title": "Backend Engineer, Payments",
    "datePosted": "2026-10-01",
    "hiringOrganization": {"@type": "Organization", "name": "Example Payments"},
    "jobLocation": {
        "@type": "Place",
        "address": {
            "@type": "PostalAddress",
            "addressLocality": "Seattle",
            "addressCountry": "US",
        },
    },
}

PLACE_SEATTLE = {
    "locality": "Seattle",
    "region": None,
    "country": "US",
    "postal_code": None,
    "address_text": None,
    "remote": False,
}

BODY_TEXT = (
    "<p>We are hiring a backend engineer to build payment systems that move "
    "money reliably for millions of businesses around the world.</p>"
)


def _page(head: str = "", body: str = BODY_TEXT, title: str = "Backend Engineer") -> str:
    return (
        f"<html><head><title>{title}</title>{head}</head>"
        f"<body><main>{body}</main></body></html>"
    )


def _ld(obj, attrs: str = 'type="application/ld+json"') -> str:
    text = obj if isinstance(obj, str) else json.dumps(obj)
    return f"<script {attrs}>{text}</script>"


JOB_HTML = _page(head=_ld(JOB_POSTING))
PLAIN_HTML = _page(body="<p>" + "A page about nothing in particular with enough words. " * 3 + "</p>")


# ---------------------------------------------------------------------------
# extract_structured_data
# ---------------------------------------------------------------------------

class TestExtractStructuredData:
    def test_job_posting_in_head(self):
        items = extract_structured_data(JOB_HTML)
        assert items == [JOB_POSTING]

    def test_block_in_body(self):
        html = _page(body=BODY_TEXT + _ld(JOB_POSTING))
        assert extract_structured_data(html) == [JOB_POSTING]

    def test_head_and_body_blocks_in_document_order(self):
        org = {"@context": "https://schema.org", "@type": "Organization", "name": "Example"}
        html = _page(head=_ld(org), body=BODY_TEXT + _ld(JOB_POSTING))
        assert extract_structured_data(html) == [org, JOB_POSTING]

    def test_no_block_returns_empty_list(self):
        assert extract_structured_data(PLAIN_HTML) == []

    def test_mention_of_mime_type_outside_a_script_is_not_a_block(self):
        html = _page(body="<p>Use application/ld+json for structured data.</p>")
        assert extract_structured_data(html) == []

    def test_other_script_types_are_ignored(self):
        html = _page(head='<script type="application/json">{"@type": "JobPosting"}</script>'
                          '<script>var x = {"@type": "JobPosting"};</script>')
        assert extract_structured_data(html) == []

    def test_array_block_yields_each_object(self):
        crumbs = {"@type": "BreadcrumbList", "itemListElement": []}
        html = _page(head=_ld([crumbs, JOB_POSTING, "not-an-object", 3]))
        assert extract_structured_data(html) == [crumbs, JOB_POSTING]

    def test_graph_container_is_flattened_and_context_carried(self):
        block = {
            "@context": "https://schema.org",
            "@graph": [
                {"@type": "WebPage", "name": "Careers"},
                {"@type": "JobPosting", "title": "Engineer"},
            ],
        }
        items = extract_structured_data(_page(head=_ld(block)))
        assert items == [
            {"@context": "https://schema.org", "@type": "WebPage", "name": "Careers"},
            {"@context": "https://schema.org", "@type": "JobPosting", "title": "Engineer"},
        ]

    def test_graph_member_keeps_its_own_context(self):
        block = {
            "@context": "https://schema.org",
            "@graph": [{"@context": "http://schema.org/", "@type": "JobPosting"}],
        }
        items = extract_structured_data(_page(head=_ld(block)))
        assert items == [{"@context": "http://schema.org/", "@type": "JobPosting"}]

    def test_typed_graph_container_is_kept_without_its_graph(self):
        block = {"@type": "WebSite", "name": "Example", "@graph": [{"@type": "JobPosting"}]}
        items = extract_structured_data(_page(head=_ld(block)))
        assert items == [{"@type": "WebSite", "name": "Example"}, {"@type": "JobPosting"}]

    def test_malformed_block_beside_a_good_one(self):
        html = _page(head=_ld("{not json at all") + _ld(JOB_POSTING) + _ld(""))
        assert extract_structured_data(html) == [JOB_POSTING]

    def test_html_comment_wrapper(self):
        html = _page(head=_ld("<!--\n" + json.dumps(JOB_POSTING) + "\n-->"))
        assert extract_structured_data(html) == [JOB_POSTING]

    @pytest.mark.parametrize("opening, closing", [
        ("<![CDATA[", "]]>"),
        ("//<![CDATA[", "//]]>"),
        ("/*<![CDATA[*/", "/*]]>*/"),
    ])
    def test_cdata_wrappers(self, opening, closing):
        html = _page(head=_ld(opening + "\n" + json.dumps(JOB_POSTING) + "\n" + closing))
        assert extract_structured_data(html) == [JOB_POSTING]

    def test_trailing_garbage_after_the_object(self):
        html = _page(head=_ld(json.dumps(JOB_POSTING) + "; // tracking snippet"))
        assert extract_structured_data(html) == [JOB_POSTING]

    def test_concatenated_objects_in_one_block(self):
        org = {"@type": "Organization", "name": "Example"}
        html = _page(head=_ld(json.dumps(org) + "\n" + json.dumps(JOB_POSTING)))
        assert extract_structured_data(html) == [org, JOB_POSTING]

    def test_raw_newline_inside_a_string_value(self):
        raw = '{"@type": "JobPosting", "description": "Line one\nLine two"}'
        items = extract_structured_data(_page(head=_ld(raw)))
        assert items == [{"@type": "JobPosting", "description": "Line one\nLine two"}]

    @pytest.mark.parametrize("attrs", [
        'type="application/ld+json; charset=utf-8"',
        'type="Application/LD+JSON"',
        "type='application/ld+json'",
        'id="jobposting" type="application/ld+json" nonce="abc"',
    ])
    def test_type_attribute_variants(self, attrs):
        html = _page(head=_ld(JOB_POSTING, attrs=attrs))
        assert extract_structured_data(html) == [JOB_POSTING]

    def test_commented_out_script_is_not_read(self):
        html = _page(head="<!-- " + _ld(JOB_POSTING) + " -->")
        assert extract_structured_data(html) == []

    def test_block_over_the_size_bound_is_skipped(self):
        big = dict(JOB_POSTING, description="x" * (MAX_JSON_LD_BLOCK_BYTES + 1))
        org = {"@type": "Organization", "name": "Example"}
        html = _page(head=_ld(big) + _ld(org))
        assert extract_structured_data(html) == [org]

    def test_size_bound_counts_utf8_bytes(self):
        # 'é' is two bytes in UTF-8: the block is under the bound in
        # characters but over it in bytes.
        payload = "é" * (MAX_JSON_LD_BLOCK_BYTES // 2)
        big = {"@type": "JobPosting", "description": payload}
        assert len(json.dumps(big, ensure_ascii=False)) < MAX_JSON_LD_BLOCK_BYTES
        html = _page(head=_ld(json.dumps(big, ensure_ascii=False)))
        assert extract_structured_data(html) == []

    def test_size_bound_is_configurable_and_can_be_disabled(self):
        big = dict(JOB_POSTING, description="x" * (MAX_JSON_LD_BLOCK_BYTES + 1))
        html = _page(head=_ld(big))
        assert extract_structured_data(html, max_block_bytes=None) == [big]
        assert extract_structured_data(JOB_HTML, max_block_bytes=10) == []

    @pytest.mark.parametrize("bad", ["", "   ", "<html", "<<<>>>", None, b"bytes", 42])
    def test_never_raises_on_junk_input(self, bad):
        assert extract_structured_data(bad) == []

    def test_never_raises_on_deep_nesting(self):
        deep = "[" * 100_000 + "]" * 100_000
        html = _page(head=_ld(deep) + _ld(JOB_POSTING))
        assert extract_structured_data(html) == [JOB_POSTING]


# ---------------------------------------------------------------------------
# find_items
# ---------------------------------------------------------------------------

class TestFindItems:
    def test_exact_type_match(self):
        items = [{"@type": "Organization"}, JOB_POSTING]
        assert find_items(items, "JobPosting") == [JOB_POSTING]

    def test_type_list_contains_name(self):
        item = {"@type": ["Thing", "JobPosting"]}
        assert find_items([item], "JobPosting") == [item]

    def test_full_and_compact_iri_forms(self):
        a = {"@type": "https://schema.org/JobPosting"}
        b = {"@type": "schema:JobPosting"}
        c = {"@type": "http://schema.org/JobPostingDraft"}
        assert find_items([a, b, c], "JobPosting") == [a, b]

    def test_no_partial_name_match(self):
        assert find_items([{"@type": "JobPostingDraft"}, {"@type": "Job"}], "JobPosting") == []

    def test_reaches_into_graph_of_raw_blocks(self):
        block = {"@context": "https://schema.org", "@graph": [{"@type": "JobPosting", "title": "A"}]}
        found = find_items([block], "JobPosting")
        assert [f["title"] for f in found] == ["A"]

    def test_accepts_a_single_object(self):
        assert find_items(JOB_POSTING, "JobPosting") == [JOB_POSTING]

    @pytest.mark.parametrize("junk", [None, [], [None, 1, "x"], [{"no": "type"}], [{"@type": 5}]])
    def test_junk_input_returns_empty(self, junk):
        assert find_items(junk, "JobPosting") == []


# ---------------------------------------------------------------------------
# job_posting_places
# ---------------------------------------------------------------------------

def _place(**kw):
    out = {"locality": None, "region": None, "country": None,
           "postal_code": None, "address_text": None, "remote": False}
    out.update(kw)
    return out


class TestJobPostingPlaces:
    def test_single_place(self):
        assert job_posting_places(JOB_POSTING) == [PLACE_SEATTLE]

    def test_several_places_and_address_shapes(self):
        posting = {
            "@type": "JobPosting",
            "jobLocation": [
                {"@type": "Place", "address": {
                    "@type": "PostalAddress", "addressLocality": " Toronto ",
                    "addressRegion": "ON", "postalCode": "M5V 2T6",
                    "addressCountry": {"@type": "Country", "name": "Canada"},
                }},
                {"@type": "Place", "address": "Dublin, Ireland"},
                {"@type": "Place", "address": [
                    {"addressLocality": "Austin", "addressRegion": {"@type": "State", "name": "TX"},
                     "postalCode": 78701, "addressCountry": "US"},
                ]},
                {"@type": "Place", "name": "Head office"},      # no address: skipped
                {"@type": "Place", "address": {"addressLocality": "  "}},  # empty: skipped
                "Somewhere",                                     # not a Place: skipped
            ],
        }
        assert job_posting_places(posting) == [
            _place(locality="Toronto", region="ON", country="Canada", postal_code="M5V 2T6"),
            _place(address_text="Dublin, Ireland"),
            _place(locality="Austin", region="TX", country="US", postal_code="78701"),
        ]

    def test_address_fields_written_on_the_place_itself(self):
        posting = {"@type": "JobPosting", "jobLocation": {
            "@type": "PostalAddress", "addressLocality": "Vancouver", "addressCountry": "CA"}}
        assert job_posting_places(posting) == [_place(locality="Vancouver", country="CA")]

    def test_telecommute_with_applicant_location_requirements(self):
        posting = {
            "@type": "JobPosting",
            "jobLocationType": "TELECOMMUTE",
            "applicantLocationRequirements": [
                {"@type": "Country", "name": "USA"},
                {"@type": "State", "name": "Ontario"},
                {"@type": "City", "name": "Berlin"},
                {"@type": "AdministrativeArea", "name": "EMEA"},
                "Anywhere in Europe",
            ],
        }
        assert job_posting_places(posting) == [
            _place(country="USA", remote=True),
            _place(region="Ontario", remote=True),
            _place(locality="Berlin", remote=True),
            _place(address_text="EMEA", remote=True),
            _place(address_text="Anywhere in Europe", remote=True),
        ]

    def test_telecommute_without_a_stated_area(self):
        posting = {"@type": "JobPosting", "jobLocationType": ["telecommute"]}
        assert job_posting_places(posting) == [_place(remote=True)]

    def test_office_plus_remote_lists_both(self):
        posting = dict(JOB_POSTING, jobLocationType="TELECOMMUTE",
                       applicantLocationRequirements={"@type": "Country", "name": "US"})
        assert job_posting_places(posting) == [PLACE_SEATTLE, _place(country="US", remote=True)]

    def test_office_only_posting_is_not_remote(self):
        posting = dict(JOB_POSTING, jobLocationType="ONSITE")
        assert job_posting_places(posting) == [PLACE_SEATTLE]

    @pytest.mark.parametrize("junk", [
        None, "JobPosting", [], {}, {"@type": "JobPosting"},
        {"jobLocation": 5}, {"jobLocation": {"address": 7}},
        {"applicantLocationRequirements": [None, 3, {"@type": "Country"}]},
    ])
    def test_junk_input_returns_empty(self, junk):
        assert job_posting_places(junk) == []

    def test_end_to_end_from_html(self):
        items = extract_structured_data(JOB_HTML)
        postings = find_items(items, "JobPosting")
        assert [job_posting_places(p) for p in postings] == [[PLACE_SEATTLE]]


# ---------------------------------------------------------------------------
# Public API surface
# ---------------------------------------------------------------------------

def test_helpers_are_exported_from_package_root():
    import markcrawl
    for name in ("extract_structured_data", "find_items", "job_posting_places"):
        assert name in markcrawl.__all__
        assert getattr(markcrawl, name) is globals()[name]


def test_pagedata_positional_construction_still_works():
    p = PageData("https://e.com/", "T", "content", "f.md")
    assert p.structured_data == []
    q = PageData("https://e.com/2", "T", "content", "g.md")
    p.structured_data.append({"@type": "X"})
    assert q.structured_data == []  # default is not shared between instances


def test_pagedata_structured_data_is_the_last_field():
    from dataclasses import fields
    assert [f.name for f in fields(PageData)] == ["url", "title", "content", "filename", "structured_data"]


# ---------------------------------------------------------------------------
# Engines: sync, async, process-pool worker
# ---------------------------------------------------------------------------

def _mock_resp(html: str, ok: bool = True, status: int = 200) -> MagicMock:
    resp = MagicMock()
    resp.ok = ok
    resp.is_success = ok
    resp.status_code = status
    resp.text = html
    resp.content = html.encode()
    resp.headers = {"content-type": "text/html; charset=utf-8"}
    return resp


LEGACY_ROW_KEYS = ["url", "title", "path", "crawled_at", "citation", "tool", "text"]


def _sync_crawl(tmp_path, pages, **kwargs):
    """Run ``crawl()`` on the sync engine against recorded HTML."""
    from markcrawl.core import crawl

    with patch("markcrawl.core._HAS_HTTPX", False), \
         patch("markcrawl.core.build_session") as mock_build, \
         patch("markcrawl.core.fetch") as mock_fetch:
        session = MagicMock()
        robots = _mock_resp("User-agent: *\nAllow: /\n")
        robots.headers = {"content-type": "text/plain"}
        session.get.return_value = robots
        mock_build.return_value = session
        mock_fetch.side_effect = lambda s, url, timeout: pages.get(
            url, _mock_resp("missing", ok=False, status=404))
        kwargs.setdefault("min_words", 5)
        return crawl(
            base_url=next(iter(pages)),
            out_dir=str(tmp_path / "out"),
            use_sitemap=False,
            max_pages=10,
            **kwargs,
        )


def _rows(result):
    with open(result.index_file, encoding="utf-8") as f:
        return [line for line in f if line.strip()]


class TestSyncEngine:
    def test_job_page_carries_structured_data(self, tmp_path):
        url = "https://jobs.example.com/listing/123"
        result = _sync_crawl(tmp_path, {url: _mock_resp(JOB_HTML)})
        assert result.pages_saved == 1
        page = result.pages[0]
        assert page.structured_data == [JOB_POSTING]
        row = json.loads(_rows(result)[0])
        assert row["structured_data"] == [JOB_POSTING]
        # The new key comes last; the legacy keys keep their order.
        assert list(row)[:-1] == LEGACY_ROW_KEYS
        assert list(row)[-1] == "structured_data"
        postings = find_items(page.structured_data, "JobPosting")
        assert job_posting_places(postings[0]) == [PLACE_SEATTLE]

    def test_page_without_json_ld_row_is_unchanged(self, tmp_path):
        url = "https://www.example.com/about"
        result = _sync_crawl(tmp_path, {url: _mock_resp(PLAIN_HTML)})
        assert result.pages_saved == 1
        assert result.pages[0].structured_data == []
        line = _rows(result)[0]
        row = json.loads(line)
        assert list(row) == LEGACY_ROW_KEYS
        # Byte for byte: the row is exactly what the legacy builder wrote.
        expected = {k: row[k] for k in LEGACY_ROW_KEYS}
        assert line == json.dumps(expected, ensure_ascii=False) + "\n"

    def test_oversized_block_is_left_out_of_the_row(self, tmp_path):
        big = dict(JOB_POSTING, description="x" * (MAX_JSON_LD_BLOCK_BYTES + 1))
        url = "https://jobs.example.com/listing/9"
        result = _sync_crawl(tmp_path, {url: _mock_resp(_page(head=_ld(big)))})
        assert result.pages[0].structured_data == []
        assert "structured_data" not in json.loads(_rows(result)[0])

    @pytest.mark.parametrize("fmt, extractor", [
        ("markdown", "default"),
        ("markdown", "trafilatura"),
        ("markdown", "ensemble"),
        ("markdown", "readerlm"),
        ("text", "default"),
    ])
    def test_every_extractor_carries_structured_data(self, tmp_path, fmt, extractor):
        url = "https://jobs.example.com/listing/123"
        # Never load a model in tests: if transformers is installed the
        # ReaderLM extractor must fall back to the default pipeline.
        with patch("markcrawl.extract_content._get_readerlm_tokenizer", side_effect=RuntimeError("no model")), \
             patch("markcrawl.extract_content._get_readerlm_model", side_effect=RuntimeError("no model")):
            result = _sync_crawl(tmp_path, {url: _mock_resp(JOB_HTML)}, fmt=fmt, extractor=extractor)
        assert result.pages[0].structured_data == [JOB_POSTING]
        assert json.loads(_rows(result)[0])["structured_data"] == [JOB_POSTING]

    def test_custom_content_extractor_carries_structured_data(self, tmp_path):
        url = "https://jobs.example.com/listing/123"
        result = _sync_crawl(
            tmp_path, {url: _mock_resp(JOB_HTML)},
            content_extractor=lambda html: ("Custom", "custom extracted text with enough words here"),
        )
        assert result.pages[0].title == "Custom"
        assert result.pages[0].structured_data == [JOB_POSTING]


class TestProcessPoolWorker:
    @pytest.mark.parametrize("fmt, extractor", [
        ("markdown", "default"), ("markdown", "trafilatura"),
        ("markdown", "ensemble"), ("text", "default"),
    ])
    def test_worker_returns_structured_data(self, fmt, extractor):
        from markcrawl.core import _extract_content_worker
        result = _extract_content_worker(JOB_HTML, "https://jobs.example.com/1", fmt, extractor)
        title, content, links, structured = result
        assert title == "Backend Engineer"
        assert "backend engineer" in content.lower()
        assert structured == [JOB_POSTING]

    def test_worker_without_json_ld(self):
        from markcrawl.core import _extract_content_worker
        *_, structured = _extract_content_worker(PLAIN_HTML, "https://e.com/", "markdown", "default")
        assert structured == []


@_skip_no_httpx
class TestAsyncEngine:
    def _engine(self, tmp_path, **kw):
        from markcrawl.core import AsyncCrawlEngine
        out = tmp_path / "out"
        out.mkdir(exist_ok=True)
        return AsyncCrawlEngine(
            out_dir=str(out), fmt="markdown", min_words=5, delay=0, timeout=10,
            concurrency=1, include_subdomains=False, user_agent="test",
            proxy=None, show_progress=False, **kw,
        )

    def test_process_response_carries_structured_data(self, tmp_path):
        engine = self._engine(tmp_path)
        page = engine.process_response("https://jobs.example.com/1", _mock_resp(JOB_HTML))
        assert page["structured_data"] == [JOB_POSTING]

    def test_extract_response_with_custom_extractor(self, tmp_path):
        import asyncio
        engine = self._engine(tmp_path, content_extractor=lambda html: ("C", "custom words enough here"))
        try:
            result = asyncio.run(engine._extract_response("https://jobs.example.com/1", _mock_resp(JOB_HTML)))
        finally:
            asyncio.run(engine.close())
        assert result[3] == [JOB_POSTING]

    @pytest.mark.parametrize("concurrency", [1, 2])
    def test_crawl_parity_with_sync_engine(self, tmp_path, concurrency):
        """Async crawl (inline and process-pool extraction) writes the same
        PageData.structured_data and JSONL rows as the sync engine."""
        import httpx

        from markcrawl.core import crawl

        # Seed at the root so the derived path scope admits both pages.
        job_url = "https://jobs.example.com/"
        plain_url = "https://jobs.example.com/about"
        job_html = JOB_HTML.replace("</main>", f'<a href="{plain_url}">About</a></main>')
        pages = {job_url: _mock_resp(job_html), plain_url: _mock_resp(PLAIN_HTML)}

        async def mock_get(url, timeout=None):
            url = str(url)
            if url.endswith("/robots.txt"):
                resp = _mock_resp("User-agent: *\nAllow: /\n")
                resp.headers = {"content-type": "text/plain"}
                return resp
            return pages.get(url, _mock_resp("missing", ok=False, status=404))

        async def mock_aclose():
            pass

        client = MagicMock(spec=httpx.AsyncClient)
        client.get = mock_get
        client.aclose = mock_aclose

        with patch("markcrawl.core.build_async_session", return_value=client):
            async_result = crawl(
                base_url=job_url, out_dir=str(tmp_path / "async"), use_sitemap=False,
                delay=0, max_pages=10, min_words=5, concurrency=concurrency,
            )
        sync_result = _sync_crawl(tmp_path, {job_url: _mock_resp(job_html), plain_url: _mock_resp(PLAIN_HTML)})

        def by_url(result):
            return {p.url: p.structured_data for p in result.pages}

        assert async_result.pages_saved == sync_result.pages_saved == 2
        assert by_url(async_result) == by_url(sync_result) == {job_url: [JOB_POSTING], plain_url: []}

        def rows_by_url(result):
            out = {}
            for line in _rows(result):
                row = json.loads(line)
                out[row["url"]] = {k: v for k, v in row.items() if k != "crawled_at"}
            return out

        assert rows_by_url(async_result) == rows_by_url(sync_result)
        assert "structured_data" not in rows_by_url(async_result)[plain_url]


def test_readme_example_shape():
    """The README snippet runs against a crawled page record."""
    page = PageData("https://jobs.example.com/1", "T", "c", "f.md", structured_data=[JOB_POSTING])
    lines = []
    for posting in find_items(page.structured_data, "JobPosting"):
        for place in job_posting_places(posting):
            lines.append((posting.get("title"), place["locality"], place["country"], place["remote"]))
    assert lines == [("Backend Engineer, Payments", "Seattle", "US", False)]


def test_text_output_unchanged_by_structured_data(tmp_path):
    """Carrying the blocks through does not change the extracted text."""
    from markcrawl.extract_content import html_to_markdown
    url = "https://jobs.example.com/listing/123"
    _, md_with, _ = html_to_markdown(JOB_HTML, base_url=url)
    result = _sync_crawl(tmp_path, {url: _mock_resp(JOB_HTML)})
    assert result.pages[0].content == md_with


def test_size_bound_is_documented():
    assert MAX_JSON_LD_BLOCK_BYTES == 128 * 1024
    assert "MAX_JSON_LD_BLOCK_BYTES" in (extract_structured_data.__doc__ or "")


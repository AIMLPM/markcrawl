"""robots.txt handling per RFC 9309 (the Robots Exclusion Protocol).

Pins three behaviour changes against the ``urllib.robotparser`` based
handling that came before:

1. Fetch outcome (RFC 9309 section 2.3.1).  A robots.txt that is
   *unreachable* (5xx, 429, timeout, connection error) means complete
   disallow: nothing is fetched while ``respect_robots=True``, one warning
   is logged, and ``CrawlResult.robots_status == "unreachable"``.  An
   *unavailable* file (4xx) still means "no rules".  A parser exception on
   a URL now means "not allowed" instead of "allowed".
2. Group selection (section 2.2.1).  The crawler's product token (default
   ``MarkCrawl``, derived from the User-Agent) is matched
   case-insensitively against ``User-agent:`` lines; matching groups are
   combined; ``*`` is the fallback.  The default UA starts with
   ``Mozilla``, which the stdlib parser used as the token, so a site that
   wrote ``User-agent: MarkCrawl`` was not obeyed.
3. Path matching (sections 2.2.2 and 2.2.3).  ``*`` and ``$`` wildcards,
   longest match wins, ``Allow`` wins a tie, percent-encoding normalised,
   ``/robots.txt`` implicitly allowed.  Crawl-delay is read from the same
   selected group.

All HTTP is mocked; nothing touches the network.
"""
from __future__ import annotations

import asyncio
import logging
import textwrap
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
import requests

from markcrawl.fetch import DEFAULT_UA
from markcrawl.robots import (
    DEFAULT_ROBOTS_PRODUCT_TOKEN,
    ROBOTS_OK,
    ROBOTS_UNAVAILABLE,
    ROBOTS_UNREACHABLE,
    RobotsRules,
    parse_crawl_delay,
    parse_robots_txt,
    parse_robots_txt_async,
    product_token_from_user_agent,
)
from markcrawl.throttle import AdaptiveThrottle

try:
    import httpx
    _HAS_HTTPX = True
except ImportError:  # pragma: no cover - depends on the environment
    httpx = None
    _HAS_HTTPX = False

_skip_no_httpx = pytest.mark.skipif(not _HAS_HTTPX, reason="httpx not installed")

SITE = "https://www.example.com"


def _allowed(robots: str, agent: str, path: str) -> bool:
    return RobotsRules(textwrap.dedent(robots)).can_fetch(agent, SITE + path)


# ---------------------------------------------------------------------------
# RFC 9309 section 5: the specification's own examples
# ---------------------------------------------------------------------------

RFC_SIMPLE_EXAMPLE = """\
User-Agent: *
Disallow: *.gif$
Disallow: /example/
Allow: /publications/

User-Agent: foobot
Disallow:/
Allow:/example/page.html
Allow:/example/allowed.gif

User-Agent: barbot
User-Agent: bazbot
Disallow: /example/page.html

User-Agent: quxbot

EOF
"""


class TestRfcSimpleExample:
    """RFC 9309 section 5.1."""

    @pytest.mark.parametrize("path, expected", [
        ("/publications/", True),
        ("/publications/paper.html", True),
        ("/example/", False),
        ("/example/page.html", False),
        ("/images/logo.gif", False),
        ("/logo.gif?v=2", True),             # "$" anchors the end: not a .gif path
        ("/publications/figure.gif", True),  # longest match: Allow /publications/ (14) > *.gif$ (6)
        ("/index.html", True),
    ])
    def test_other_agents_use_the_star_group(self, path, expected):
        assert _allowed(RFC_SIMPLE_EXAMPLE, "OtherBot", path) is expected

    @pytest.mark.parametrize("path, expected", [
        ("/example/page.html", True),
        ("/example/allowed.gif", True),
        ("/", False),
        ("/publications/", False),
        ("/example/other.html", False),
    ])
    def test_foobot(self, path, expected):
        assert _allowed(RFC_SIMPLE_EXAMPLE, "foobot", path) is expected

    @pytest.mark.parametrize("agent", ["barbot", "bazbot", "BazBot"])
    @pytest.mark.parametrize("path, expected", [
        ("/example/page.html", False),
        ("/example/other.html", True),
        ("/logo.gif", True),
    ])
    def test_barbot_and_bazbot_share_one_group(self, agent, path, expected):
        assert _allowed(RFC_SIMPLE_EXAMPLE, agent, path) is expected

    @pytest.mark.parametrize("path", ["/", "/example/page.html", "/logo.gif"])
    def test_quxbot_empty_group_allows_everything(self, path):
        assert _allowed(RFC_SIMPLE_EXAMPLE, "quxbot", path) is True


class TestRfcLongestMatchExample:
    """RFC 9309 section 5.2."""

    ROBOTS = """\
    User-Agent: foobot
    Allow: /example/page/
    Disallow: /example/page/disallowed.gif
    """

    @pytest.mark.parametrize("path, expected", [
        ("/example/page/", True),
        ("/example/page/index.html", True),
        ("/example/page/disallowed.gif", False),
    ])
    def test_most_specific_rule_wins(self, path, expected):
        assert _allowed(self.ROBOTS, "foobot", path) is expected


# ---------------------------------------------------------------------------
# Group selection by product token (section 2.2.1)
# ---------------------------------------------------------------------------

class TestGroupSelection:
    def test_markcrawl_group_is_obeyed_with_the_default_user_agent(self):
        robots = "User-agent: MarkCrawl\nDisallow: /\n"
        assert _allowed(robots, DEFAULT_UA, "/") is False
        assert _allowed(robots, DEFAULT_UA, "/any/page") is False

    @pytest.mark.parametrize("line", ["User-agent: markcrawl", "USER-AGENT: MARKCRAWL", "user-agent:MarkCrawl/1.0"])
    def test_product_token_match_is_case_insensitive_and_ignores_version(self, line):
        assert _allowed(line + "\nDisallow: /private\n", DEFAULT_UA, "/private/x") is False

    def test_named_group_replaces_the_star_group(self):
        robots = "User-agent: *\nDisallow: /\n\nUser-agent: MarkCrawl\nAllow: /\n"
        assert _allowed(robots, DEFAULT_UA, "/page") is True
        assert _allowed(robots, "OtherBot", "/page") is False

    def test_mozilla_group_no_longer_applies_to_markcrawl(self):
        # The stdlib parser took "Mozilla" (the UA's first word) as the token.
        robots = "User-agent: Mozilla\nDisallow: /\n"
        assert _allowed(robots, DEFAULT_UA, "/page") is True

    def test_token_must_match_exactly_not_as_a_substring(self):
        robots = "User-agent: Mark\nDisallow: /\n\nUser-agent: MarkCrawlerX\nDisallow: /\n"
        assert _allowed(robots, DEFAULT_UA, "/page") is True

    def test_groups_for_the_same_agent_are_combined(self):
        robots = """\
        user-agent: ExampleBot
        disallow: /foo
        disallow: /bar

        user-agent: ExampleBot
        disallow: /baz
        """
        for path in ("/foo", "/bar", "/baz"):
            assert _allowed(robots, "ExampleBot", path) is False
        assert _allowed(robots, "ExampleBot", "/qux") is True

    def test_blank_lines_and_comments_do_not_split_a_group(self):
        robots = "User-agent: a\n\n# comment\nUser-agent: MarkCrawl\n\nDisallow: /x # trailing comment\n"
        assert _allowed(robots, DEFAULT_UA, "/x") is False
        assert _allowed(robots, "a", "/x") is False

    def test_no_matching_group_and_no_star_means_no_rules(self):
        assert _allowed("User-agent: OtherBot\nDisallow: /\n", DEFAULT_UA, "/x") is True

    def test_rules_before_any_user_agent_are_ignored(self):
        assert _allowed("Disallow: /\nUser-agent: *\nDisallow: /private\n", DEFAULT_UA, "/x") is True

    def test_empty_disallow_allows_everything(self):
        assert _allowed("User-agent: *\nDisallow:\n", DEFAULT_UA, "/anything") is True

    def test_unknown_lines_bom_and_crlf_are_tolerated(self):
        robots = "\ufeffUser-agent: *\r\nHost: example.com\r\nnot a directive\r\nDisallow: /private\r\n"
        assert _allowed(robots, DEFAULT_UA, "/private/x") is False
        assert _allowed(robots, DEFAULT_UA, "/public") is True

    def test_robots_txt_itself_is_always_allowed(self):
        assert _allowed("User-agent: *\nDisallow: /\n", DEFAULT_UA, "/robots.txt") is True


class TestProductToken:
    @pytest.mark.parametrize("ua, token", [
        (DEFAULT_UA, "MarkCrawl"),
        ("Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)", "Googlebot"),
        ("MyBot/2.1 (+https://example.org/bot)", "MyBot"),
        ("test", "test"),
        ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0 Safari/537.36", "MarkCrawl"),
        ("", "MarkCrawl"),
        (None, "MarkCrawl"),
    ])
    def test_derived_from_user_agent(self, ua, token):
        assert product_token_from_user_agent(ua) == token

    def test_default_token(self):
        assert DEFAULT_ROBOTS_PRODUCT_TOKEN == "MarkCrawl"


# ---------------------------------------------------------------------------
# Path matching (sections 2.2.2 and 2.2.3)
# ---------------------------------------------------------------------------

class TestPathMatching:
    @pytest.mark.parametrize("pattern, path, matched", [
        ("/fish", "/fish", True),
        ("/fish", "/fish.html", True),
        ("/fish", "/fish/salmon.html", True),
        ("/fish", "/Fish.asp", False),               # case-sensitive
        ("/fish", "/catfish", False),
        ("/fish*", "/fishheads/yummy.html", True),
        ("/fish/", "/fish", False),
        ("/*.php", "/folder/filename.php?parameters", True),
        ("/*.php$", "/filename.php", True),
        ("/*.php$", "/filename.php?parameters", False),
        ("/*.php$", "/filename.php5", False),
        ("/fish*.php", "/fishheads/catfish.php?parameters", True),
        ("/fish*.php", "/Fish.PHP", False),
        ("/this/path/exactly$", "/this/path/exactly", True),
        ("/this/path/exactly$", "/this/path/exactly/more", False),
        ("/this/*/exactly", "/this/a/b/exactly", True),
        ("/*?", "/page?q=1", True),
        ("/*?", "/page", False),
        ("/private*/secret", "/private-area/x/secret", True),
        ("/a**b", "/a-x-b", True),
    ])
    def test_wildcards(self, pattern, path, matched):
        robots = f"User-agent: *\nDisallow: {pattern}\n"
        assert _allowed(robots, DEFAULT_UA, path) is (not matched)

    def test_longest_match_allow_beats_shorter_disallow(self):
        robots = "User-agent: *\nDisallow: /folder/\nAllow: /folder/page\n"
        assert _allowed(robots, DEFAULT_UA, "/folder/page") is True
        assert _allowed(robots, DEFAULT_UA, "/folder/other") is False

    def test_longest_match_disallow_beats_shorter_allow(self):
        robots = "User-agent: *\nAllow: /folder/\nDisallow: /folder/private\n"
        assert _allowed(robots, DEFAULT_UA, "/folder/private/x") is False
        assert _allowed(robots, DEFAULT_UA, "/folder/public") is True

    def test_allow_wins_a_tie(self):
        robots = "User-agent: *\nDisallow: /page\nAllow: /page\n"
        assert _allowed(robots, DEFAULT_UA, "/page") is True

    def test_rule_order_does_not_matter(self):
        a = "User-agent: *\nAllow: /p/q\nDisallow: /p\n"
        b = "User-agent: *\nDisallow: /p\nAllow: /p/q\n"
        for robots in (a, b):
            assert _allowed(robots, DEFAULT_UA, "/p/q/r") is True
            assert _allowed(robots, DEFAULT_UA, "/p/x") is False

    def test_dollar_root_only(self):
        robots = "User-agent: *\nAllow: /$\nDisallow: /\n"
        assert _allowed(robots, DEFAULT_UA, "/") is True
        assert _allowed(robots, DEFAULT_UA, "/page") is False

    def test_query_string_is_part_of_the_path(self):
        robots = "User-agent: *\nDisallow: /search?q=\n"
        assert _allowed(robots, DEFAULT_UA, "/search?q=shoes") is False
        assert _allowed(robots, DEFAULT_UA, "/search") is True

    @pytest.mark.parametrize("rule, path", [
        ("/foo/bar/%E3%83%84", "/foo/bar/ツ"),      # UTF-8 in the URL
        ("/foo/bar/%E3%83%84", "/foo/bar/%e3%83%84"),   # lowercase hex in the URL
        ("/foo/bar/ツ", "/foo/bar/%E3%83%84"),      # UTF-8 in the rule
        ("/foo/bar/baz", "/foo/bar/%62%61%7A"),          # encoded unreserved chars
        ("/foo/bar/%62%61%7A", "/foo/bar/baz"),
        ("/path/file-with-a-%2A.html", "/path/file-with-a-*.html"),  # literal "*"
        ("/path/foo-%24", "/path/foo-$"),                # literal "$"
    ])
    def test_percent_encoding_is_normalised(self, rule, path):
        assert _allowed(f"User-agent: *\nDisallow: {rule}\n", DEFAULT_UA, path) is False

    def test_encoded_reserved_character_is_not_decoded(self):
        # %2F is an encoded "/", which is reserved: it must not match "/".
        assert _allowed("User-agent: *\nDisallow: /a/b\n", DEFAULT_UA, "/a%2Fb") is True


# ---------------------------------------------------------------------------
# Crawl-delay comes from the same selected group
# ---------------------------------------------------------------------------

class TestCrawlDelay:
    ROBOTS = (
        "User-agent: MarkCrawl\nDisallow: /x\nCrawl-delay: 7\n\n"
        "User-agent: *\nCrawl-delay: 1\n"
    )

    def test_delay_from_the_markcrawl_group(self):
        assert parse_crawl_delay(self.ROBOTS, DEFAULT_UA) == 7.0
        assert AdaptiveThrottle.parse_crawl_delay(self.ROBOTS, DEFAULT_UA) == 7.0
        assert RobotsRules(self.ROBOTS).crawl_delay(DEFAULT_UA) == 7.0

    def test_other_agents_get_the_star_delay(self):
        assert parse_crawl_delay(self.ROBOTS, "OtherBot") == 1.0
        assert parse_crawl_delay(self.ROBOTS, "*") == 1.0

    def test_named_group_without_a_delay_does_not_borrow_the_star_one(self):
        robots = "User-agent: MarkCrawl\nDisallow: /x\n\nUser-agent: *\nCrawl-delay: 9\n"
        assert parse_crawl_delay(robots, DEFAULT_UA) is None

    @pytest.mark.parametrize("value", ["-1", "nan", "inf", "soon"])
    def test_unusable_values_are_ignored(self, value):
        assert parse_crawl_delay(f"User-agent: *\nCrawl-delay: {value}\n", DEFAULT_UA) is None


# ---------------------------------------------------------------------------
# Fetch outcome (section 2.3.1)
# ---------------------------------------------------------------------------

def _robots_resp(status: int, text: str = "") -> MagicMock:
    resp = MagicMock()
    resp.status_code = status
    resp.ok = status < 400
    resp.is_success = 200 <= status < 300
    resp.text = text
    resp.content = text.encode()
    resp.headers = {"content-type": "text/plain"}
    return resp


ROBOTS_URL = SITE + "/robots.txt"


class TestFetchOutcome:
    @pytest.mark.parametrize("status", [500, 502, 503, 504, 429])
    def test_server_error_is_unreachable_and_disallows_everything(self, status):
        session = MagicMock()
        session.get.return_value = _robots_resp(status, "User-agent: *\nAllow: /\n")
        rp, text = parse_robots_txt(session, ROBOTS_URL)
        assert rp.status == ROBOTS_UNREACHABLE
        assert str(status) in rp.reason
        assert text == ""
        assert rp.can_fetch(DEFAULT_UA, SITE + "/") is False
        assert rp.can_fetch(DEFAULT_UA, SITE + "/any/page") is False

    @pytest.mark.parametrize("exc", [
        requests.ConnectionError("connection refused"),
        requests.Timeout("timed out"),
        OSError("network down"),
    ])
    def test_network_error_is_unreachable(self, exc):
        session = MagicMock()
        session.get.side_effect = exc
        rp, text = parse_robots_txt(session, ROBOTS_URL)
        assert rp.status == ROBOTS_UNREACHABLE
        assert type(exc).__name__ in rp.reason
        assert text == ""
        assert rp.can_fetch(DEFAULT_UA, SITE + "/") is False

    @pytest.mark.parametrize("status", [400, 401, 403, 404, 410])
    def test_client_error_is_unavailable_and_allows_everything(self, status):
        session = MagicMock()
        session.get.return_value = _robots_resp(status, "User-agent: *\nDisallow: /\n")
        rp, text = parse_robots_txt(session, ROBOTS_URL)
        assert rp.status == ROBOTS_UNAVAILABLE
        assert text == ""
        assert rp.can_fetch(DEFAULT_UA, SITE + "/any/page") is True

    def test_success_parses_the_rules(self):
        session = MagicMock()
        session.get.return_value = _robots_resp(200, "User-agent: *\nDisallow: /private\n")
        rp, text = parse_robots_txt(session, ROBOTS_URL)
        assert rp.status == ROBOTS_OK
        assert text == "User-agent: *\nDisallow: /private\n"
        assert rp.can_fetch(DEFAULT_UA, SITE + "/private/x") is False
        assert rp.can_fetch(DEFAULT_UA, SITE + "/public") is True

    def test_response_without_ok_attribute_is_read(self):
        """An httpx-style response has ``is_success`` but no ``ok``; its
        rules used to be dropped (AttributeError -> empty file)."""
        resp = SimpleNamespace(status_code=200, is_success=True,
                               text="User-agent: *\nDisallow: /private\n")
        session = MagicMock()
        session.get.return_value = resp
        rp, _ = parse_robots_txt(session, ROBOTS_URL)
        assert rp.status == ROBOTS_OK
        assert rp.can_fetch(DEFAULT_UA, SITE + "/private/x") is False

    @_skip_no_httpx
    def test_real_httpx_response_on_the_sync_path(self):
        url = ROBOTS_URL
        resp = httpx.Response(200, text="User-agent: MarkCrawl\nDisallow: /\n",
                              request=httpx.Request("GET", url))
        session = MagicMock()
        session.get.return_value = resp
        rp, _ = parse_robots_txt(session, url)
        assert rp.can_fetch(DEFAULT_UA, SITE + "/page") is False

    def test_site_maps_are_listed(self):
        rules = RobotsRules("Sitemap: https://www.example.com/sitemap.xml\nUser-agent: *\nDisallow:\n")
        assert rules.site_maps() == ["https://www.example.com/sitemap.xml"]
        assert RobotsRules("").site_maps() is None


class TestFetchOutcomeAsync:
    def _client(self, resp=None, exc=None):
        async def get(url, timeout=None):
            if exc is not None:
                raise exc
            return resp
        return SimpleNamespace(get=get)

    @pytest.mark.parametrize("status, expected_status, allowed", [
        (500, ROBOTS_UNREACHABLE, False),
        (503, ROBOTS_UNREACHABLE, False),
        (429, ROBOTS_UNREACHABLE, False),
        (404, ROBOTS_UNAVAILABLE, True),
        (403, ROBOTS_UNAVAILABLE, True),
        (200, ROBOTS_OK, True),
    ])
    def test_status_parity_with_sync(self, status, expected_status, allowed):
        resp = SimpleNamespace(status_code=status, is_success=200 <= status < 300,
                               text="User-agent: *\nDisallow: /private\n")
        rp, _ = asyncio.run(parse_robots_txt_async(self._client(resp), ROBOTS_URL))
        assert rp.status == expected_status
        assert rp.can_fetch(DEFAULT_UA, SITE + "/public") is allowed

    def test_network_error_is_unreachable(self):
        rp, text = asyncio.run(parse_robots_txt_async(self._client(exc=OSError("down")), ROBOTS_URL))
        assert rp.status == ROBOTS_UNREACHABLE
        assert text == ""
        assert rp.can_fetch(DEFAULT_UA, SITE + "/") is False

    def test_markcrawl_group_obeyed(self):
        resp = SimpleNamespace(status_code=200, is_success=True, text="User-agent: MarkCrawl\nDisallow: /\n")
        rp, _ = asyncio.run(parse_robots_txt_async(self._client(resp), ROBOTS_URL))
        assert rp.can_fetch(DEFAULT_UA, SITE + "/page") is False


# ---------------------------------------------------------------------------
# Engines
# ---------------------------------------------------------------------------

def _engine_kwargs(tmp_path, **kw):
    out = tmp_path / "out"
    out.mkdir(exist_ok=True)
    base = dict(
        out_dir=str(out), fmt="markdown", min_words=5, delay=0, timeout=10,
        concurrency=1, include_subdomains=False, user_agent=None,
        proxy=None, show_progress=False,
    )
    base.update(kw)
    return base


@pytest.mark.parametrize("engine_name", ["CrawlEngine", "AsyncCrawlEngine"])
class TestEngineAllowed:
    def _engine(self, engine_name, tmp_path, **kw):
        import markcrawl.core as core
        if engine_name == "AsyncCrawlEngine" and not _HAS_HTTPX:
            pytest.skip("httpx not installed")
        extra = {"render_js": False} if engine_name == "CrawlEngine" else {}
        return getattr(core, engine_name)(**_engine_kwargs(tmp_path, **extra, **kw))

    def test_parser_exception_means_not_allowed(self, engine_name, tmp_path):
        engine = self._engine(engine_name, tmp_path)
        engine._rp = MagicMock()
        engine._rp.can_fetch.side_effect = Exception("malformed rule")
        assert engine.allowed("https://example.com/x") is False
        assert engine._robots_bypassed_count == 0

    def test_parser_exception_with_respect_robots_false_is_unchanged(self, engine_name, tmp_path):
        engine = self._engine(engine_name, tmp_path, respect_robots=False)
        engine._rp = MagicMock()
        engine._rp.can_fetch.side_effect = Exception("malformed rule")
        assert engine.allowed("https://example.com/x") is True
        assert engine._robots_bypassed_count == 0

    def test_default_product_token(self, engine_name, tmp_path):
        engine = self._engine(engine_name, tmp_path)
        assert engine.robots_product_token == "MarkCrawl"
        engine._rp = RobotsRules("User-agent: MarkCrawl\nDisallow: /\n")
        assert engine.allowed("https://example.com/page") is False

    def test_product_token_derived_from_custom_user_agent(self, engine_name, tmp_path):
        engine = self._engine(engine_name, tmp_path, user_agent="AcmeBot/3.0 (+https://acme.example)")
        assert engine.robots_product_token == "AcmeBot"
        engine._rp = RobotsRules("User-agent: AcmeBot\nDisallow: /\n")
        assert engine.allowed("https://example.com/page") is False

    def test_explicit_product_token(self, engine_name, tmp_path):
        engine = self._engine(engine_name, tmp_path, robots_product_token="CustomBot")
        assert engine.robots_product_token == "CustomBot"
        engine._rp = RobotsRules("User-agent: CustomBot\nDisallow: /\n")
        assert engine.allowed("https://example.com/page") is False


@patch("markcrawl.core._HAS_HTTPX", False)
@patch("markcrawl.core.build_session")
def test_sync_setup_robots_reads_crawl_delay_from_the_selected_group(mock_build, tmp_path):
    from markcrawl.core import CrawlEngine
    session = MagicMock()
    session.get.return_value = _robots_resp(
        200, "User-agent: *\nCrawl-delay: 1\n\nUser-agent: MarkCrawl\nCrawl-delay: 3\n")
    mock_build.return_value = session
    engine = CrawlEngine(**_engine_kwargs(tmp_path, render_js=False, user_agent=DEFAULT_UA))
    engine.setup_robots("https://example.com/")
    assert engine.throttle.base_delay == 3.0
    assert engine.robots_status == ROBOTS_OK


# ---------------------------------------------------------------------------
# End to end: crawl() on the sync and async engines
# ---------------------------------------------------------------------------

PAGE_HTML = textwrap.dedent("""
<html><head><title>Home</title></head>
<body><main>
  <p>This page has plenty of words so the minimum word filter passes cleanly.</p>
  <a href="/about">about</a>
</main></body></html>
""")
ABOUT_HTML = textwrap.dedent("""
<html><head><title>About</title></head>
<body><main>
  <p>About this site: a second page with a different set of enough words.</p>
</main></body></html>
""")


def _page_resp(html: str) -> MagicMock:
    resp = _robots_resp(200, html)
    resp.headers = {"content-type": "text/html; charset=utf-8"}
    return resp


PAGES = {"https://example.com/": PAGE_HTML, "https://example.com/about": ABOUT_HTML}


def _run_sync(tmp_path, robots, **kwargs):
    """``robots`` is a response, or an exception raised by session.get."""
    from markcrawl.core import crawl

    fetched = []

    def fake_fetch(session, url, timeout):
        fetched.append(url)
        html = PAGES.get(url)
        return _page_resp(html) if html else _robots_resp(404)

    session = MagicMock()
    if isinstance(robots, BaseException):
        session.get.side_effect = robots
    else:
        session.get.return_value = robots
    with patch("markcrawl.core._HAS_HTTPX", False), \
         patch("markcrawl.core.build_session", return_value=session), \
         patch("markcrawl.core.fetch", side_effect=fake_fetch):
        kwargs.setdefault("min_words", 5)
        result = crawl(
            base_url="https://example.com/", out_dir=str(tmp_path / "out"),
            max_pages=10, **kwargs,
        )
    other_gets = [c.args[0] for c in session.get.call_args_list if not c.args[0].endswith("/robots.txt")]
    return result, fetched + other_gets


def _run_async(tmp_path, robots, **kwargs):
    from markcrawl.core import crawl

    fetched = []

    async def get(url, timeout=None):
        url = str(url)
        if url.endswith("/robots.txt"):
            if isinstance(robots, BaseException):
                raise robots
            return robots
        fetched.append(url)
        html = PAGES.get(url)
        return _page_resp(html) if html else _robots_resp(404)

    async def aclose():
        pass

    client = MagicMock(spec=httpx.AsyncClient)
    client.get = get
    client.aclose = aclose
    with patch("markcrawl.core.build_async_session", return_value=client):
        kwargs.setdefault("min_words", 5)
        result = crawl(
            base_url="https://example.com/", out_dir=str(tmp_path / "out"),
            max_pages=10, **kwargs,
        )
    return result, fetched


ENGINES = [
    pytest.param(_run_sync, id="sync"),
    pytest.param(_run_async, id="async", marks=_skip_no_httpx),
]


@pytest.mark.parametrize("run", ENGINES)
class TestCrawlEndToEnd:
    @pytest.mark.parametrize("robots", [
        _robots_resp(500), _robots_resp(503), _robots_resp(429),
        requests.ConnectionError("refused"), OSError("timed out"),
    ], ids=["500", "503", "429", "connection-error", "timeout"])
    def test_unreachable_robots_fetches_nothing(self, run, robots, tmp_path, caplog, capsys):
        with caplog.at_level(logging.WARNING, logger="markcrawl"):
            result, fetched = run(tmp_path, robots, show_progress=True)
        assert fetched == []
        assert result.pages_saved == 0
        assert result.robots_status == ROBOTS_UNREACHABLE
        assert result.robots_respected is True
        warnings = [r for r in caplog.records if "robots.txt" in r.getMessage() and "unreachable" in r.getMessage()]
        assert len(warnings) == 1
        out = capsys.readouterr().out
        assert "unreachable" in out
        assert "no successful HTTP response" not in out
        # An empty index, like any 0-page crawl, not a missing or stale one.
        with open(result.index_file, encoding="utf-8") as f:
            assert f.read() == ""

    @pytest.mark.parametrize("status", [404, 403, 410])
    def test_unavailable_robots_allows_the_crawl(self, run, status, tmp_path):
        result, fetched = run(tmp_path, _robots_resp(status))
        assert result.robots_status == ROBOTS_UNAVAILABLE
        assert result.pages_saved == 2
        assert set(fetched) == set(PAGES)

    def test_markcrawl_group_disallow_all_is_obeyed(self, run, tmp_path):
        robots = _robots_resp(200, "User-agent: *\nAllow: /\n\nUser-agent: MarkCrawl\nDisallow: /\n")
        result, fetched = run(tmp_path, robots)
        assert result.robots_status == ROBOTS_OK
        assert result.pages_saved == 0
        assert fetched == []

    def test_star_rules_still_apply(self, run, tmp_path):
        result, fetched = run(tmp_path, _robots_resp(200, "User-agent: *\nDisallow: /about$\n"))
        assert [p.url for p in result.pages] == ["https://example.com/"]
        assert "https://example.com/about" not in fetched

    def test_robots_product_token_kwarg(self, run, tmp_path):
        robots = _robots_resp(200, "User-agent: CustomBot\nDisallow: /\n")
        result, _ = run(tmp_path, robots)
        assert result.pages_saved == 2
        result, fetched = run(tmp_path, robots, robots_product_token="CustomBot")
        assert result.pages_saved == 0
        assert fetched == []

    def test_respect_robots_false_is_unchanged_when_unreachable(self, run, tmp_path, caplog):
        with caplog.at_level(logging.WARNING, logger="markcrawl"):
            result, fetched = run(tmp_path, _robots_resp(500), respect_robots=False)
        assert result.pages_saved == 2
        assert result.robots_respected is False
        assert result.robots_bypassed_count == 0
        assert result.robots_status == ROBOTS_UNREACHABLE
        assert not any("unreachable" in r.getMessage() for r in caplog.records)

    def test_resume_state_survives_an_unreachable_robots(self, run, tmp_path):
        import os

        from markcrawl.state import STATE_FILENAME, load_state, save_state
        out = tmp_path / "out"
        out.mkdir()
        state_path = str(out / STATE_FILENAME)
        save_state(state_path, {"https://example.com/"}, set(),
                   ["https://example.com/about"], 1, ["https://example.com/"], set())
        result, fetched = run(tmp_path, _robots_resp(503), resume=True)
        assert fetched == []
        assert result.pages_saved == 0
        assert os.path.isfile(state_path)
        assert list(load_state(state_path)["to_visit"]) == ["https://example.com/about"]


def test_crawl_api_exposes_robots_product_token():
    import inspect

    from markcrawl.core import crawl
    sig = inspect.signature(crawl)
    assert sig.parameters["robots_product_token"].default is None


def test_crawlresult_exposes_robots_status():
    from markcrawl.core import CrawlResult
    result = CrawlResult(pages_saved=0, output_dir="o", index_file="i", pages=[])
    assert result.robots_status is None

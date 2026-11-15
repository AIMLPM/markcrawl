"""Robots.txt parsing (RFC 9309) and sitemap discovery."""
from __future__ import annotations

import logging
import math
import re
import urllib.parse as up
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

try:
    import httpx as _httpx
    _HAS_HTTPX = True
except ImportError:
    _httpx = None  # type: ignore[assignment]
    _HAS_HTTPX = False

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# RFC 9309 robots.txt rules
# ---------------------------------------------------------------------------

#: robots.txt was fetched (2xx) and its rules apply.
ROBOTS_OK = "ok"
#: robots.txt is unavailable (4xx): there are no rules, everything is allowed
#: (RFC 9309 section 2.3.1.3).
ROBOTS_UNAVAILABLE = "unavailable"
#: robots.txt is unreachable (5xx, 429, timeout or connection error): the
#: site must be treated as fully disallowed (RFC 9309 section 2.3.1.4).
ROBOTS_UNREACHABLE = "unreachable"

#: Product token MarkCrawl matches against ``User-agent:`` lines.
DEFAULT_ROBOTS_PRODUCT_TOKEN = "MarkCrawl"

_TOKEN = re.compile(r"[A-Za-z_-]+")
_COMPATIBLE = re.compile(r"\(\s*compatible\s*;\s*([A-Za-z_-]+)", re.IGNORECASE)
_PERCENT = re.compile(r"%([0-9A-Fa-f]{2})")
_UNRESERVED = frozenset("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-._~")
_PRINTABLE_ASCII = "".join(chr(c) for c in range(0x21, 0x7F))


def product_token_from_user_agent(user_agent: Optional[str]) -> str:
    """Return the robots.txt product token for a User-Agent string.

    A bot that announces itself the usual way (``Mozilla/5.0 (compatible;
    MarkCrawl/0.1; +url)``) gets the name after ``compatible;``.  Otherwise
    the UA's first product name is used (``AcmeBot/3.0`` -> ``AcmeBot``),
    unless it is ``Mozilla`` (a browser-style UA), in which case the
    crawler is still MarkCrawl: :data:`DEFAULT_ROBOTS_PRODUCT_TOKEN`.
    """
    if not isinstance(user_agent, str) or not user_agent.strip():
        return DEFAULT_ROBOTS_PRODUCT_TOKEN
    m = _COMPATIBLE.search(user_agent)
    if m:
        return m.group(1)
    m = _TOKEN.match(user_agent.strip())
    if m and m.group(0).lower() != "mozilla":
        return m.group(0)
    return DEFAULT_ROBOTS_PRODUCT_TOKEN


def _match_token(useragent: str) -> str:
    """The lowercase token a ``can_fetch`` / ``crawl_delay`` caller is matched by."""
    if isinstance(useragent, str) and useragent.strip() == "*":
        return "*"
    return product_token_from_user_agent(useragent).lower()


def _normalize(path: str) -> str:
    """Percent-encoding normalisation (RFC 9309 section 2.2.2): decode
    encoded unreserved characters, upper-case the remaining escapes, and
    encode non-ASCII, space and control characters as UTF-8."""
    def _escape(m: "re.Match[str]") -> str:
        char = chr(int(m.group(1), 16))
        return char if char in _UNRESERVED else "%" + m.group(1).upper()
    return up.quote(_PERCENT.sub(_escape, path), safe=_PRINTABLE_ASCII)


def _url_path(url: str) -> str:
    """The part of *url* rules are matched against: path plus query, with a
    literal ``*`` or ``$`` encoded so only the rule's own act as wildcards."""
    parts = up.urlsplit(url)
    path = parts.path or "/"
    if parts.query:
        path += "?" + parts.query
    return _normalize(path).replace("*", "%2A").replace("$", "%24")


def _matches(path: str, pattern: str) -> bool:
    """Does *pattern* (with ``*`` and a trailing ``$``) match the start of
    *path*?  Linear in ``len(path) * len(pattern)``; no backtracking."""
    if "*" not in pattern and not pattern.endswith("$"):
        return path.startswith(pattern)
    end = len(path)
    positions = [0]
    for i, char in enumerate(pattern):
        if char == "$" and i == len(pattern) - 1:
            return positions[-1] == end
        if char == "*":
            positions = list(range(positions[0], end + 1))
        else:
            positions = [p + 1 for p in positions if p < end and path[p] == char]
            if not positions:
                return False
    return True


@dataclass
class _Group:
    agents: List[str] = field(default_factory=list)
    rules: List[Tuple[bool, str]] = field(default_factory=list)  # (is_allow, pattern)
    crawl_delay: Optional[float] = None


def _parse_delay(value: str) -> Optional[float]:
    try:
        delay = float(value)
    except ValueError:
        return None
    return delay if math.isfinite(delay) and delay >= 0 else None


class RobotsRules:
    """A robots.txt file matched per RFC 9309.

    Groups are selected by product token (case-insensitive; matching groups
    are combined; ``*`` is the fallback).  Within the group the longest
    matching ``Allow`` / ``Disallow`` path wins, ``Allow`` wins a tie, ``*``
    and a trailing ``$`` are wildcards, and percent-encoding is normalised.
    ``/robots.txt`` is always allowed.  ``Crawl-delay`` is read from the
    same selected group.

    ``can_fetch(useragent, url)`` has the call shape of
    :meth:`urllib.robotparser.RobotFileParser.can_fetch`; *useragent* may be
    a full User-Agent string or a product token.

    *status* records how the file was obtained (:data:`ROBOTS_OK`,
    :data:`ROBOTS_UNAVAILABLE`, :data:`ROBOTS_UNREACHABLE`); an unreachable
    file disallows everything.
    """

    def __init__(self, text: str = "", status: str = ROBOTS_OK, reason: str = ""):
        self.status = status
        self.reason = reason
        self._groups: List[_Group] = []
        self._sitemaps: List[str] = []
        self._selected: Dict[str, Tuple[List[Tuple[bool, str]], Optional[float]]] = {}
        if status == ROBOTS_OK and isinstance(text, str):
            self._parse(text)

    def _parse(self, text: str) -> None:
        group: Optional[_Group] = None
        in_agent_lines = False
        loose_delay: Optional[float] = None  # Crawl-delay before any User-agent
        for raw in text.lstrip("\ufeff").splitlines():
            line = raw.split("#", 1)[0].strip()
            key, sep, value = line.partition(":")
            if not sep:
                continue
            key, value = key.strip().lower(), value.strip()
            if key == "user-agent":
                if group is None or not in_agent_lines:
                    group = _Group()
                    self._groups.append(group)
                m = _TOKEN.match(value)
                group.agents.append("*" if value == "*" else (m.group(0).lower() if m else ""))
                in_agent_lines = True
            elif key in ("allow", "disallow", "crawl-delay"):
                in_agent_lines = False
                if key == "crawl-delay":
                    delay = _parse_delay(value)
                    if group is None:
                        loose_delay = delay if loose_delay is None else loose_delay
                    elif group.crawl_delay is None:
                        group.crawl_delay = delay
                elif group is not None and value:
                    group.rules.append((key == "allow", _normalize(value)))
            elif key == "sitemap" and value:
                self._sitemaps.append(value)
        if loose_delay is not None:
            # Kept from the pre-RFC parser: a Crawl-delay above every
            # User-agent line applies to "*".
            self._groups.insert(0, _Group(agents=["*"], crawl_delay=loose_delay))

    def _select(self, useragent: str) -> Tuple[List[Tuple[bool, str]], Optional[float]]:
        token = _match_token(useragent)
        if token not in self._selected:
            groups = [g for g in self._groups if token in g.agents]
            if not groups:
                groups = [g for g in self._groups if "*" in g.agents]
            rules = [rule for g in groups for rule in g.rules]
            delay = next((g.crawl_delay for g in groups if g.crawl_delay is not None), None)
            self._selected[token] = (rules, delay)
        return self._selected[token]

    def can_fetch(self, useragent: str, url: str) -> bool:
        path = _url_path(url)
        if path == "/robots.txt":
            return True
        if self.status == ROBOTS_UNREACHABLE:
            return False
        best_allow = best_disallow = -1
        for is_allow, pattern in self._select(useragent)[0]:
            if _matches(path, pattern):
                if is_allow:
                    best_allow = max(best_allow, len(pattern))
                else:
                    best_disallow = max(best_disallow, len(pattern))
        return best_disallow <= best_allow

    def crawl_delay(self, useragent: str) -> Optional[float]:
        return self._select(useragent)[1]

    def site_maps(self) -> Optional[List[str]]:
        return list(self._sitemaps) or None


def parse_crawl_delay(robots_text: str, user_agent: str = "*") -> Optional[float]:
    """Crawl-delay for *user_agent* from the group RFC 9309 selects for it."""
    if not isinstance(robots_text, str):
        return None
    return RobotsRules(robots_text).crawl_delay(user_agent)


def _classify_response(response: Any) -> Tuple[str, str]:
    """Map a robots.txt response to (status, reason) per RFC 9309 2.3.1."""
    code = getattr(response, "status_code", None)
    if isinstance(code, int) and not isinstance(code, bool):
        if 200 <= code < 300:
            return ROBOTS_OK, f"HTTP {code}"
        if code == 429 or code >= 500:
            return ROBOTS_UNREACHABLE, f"HTTP {code}"
        return ROBOTS_UNAVAILABLE, f"HTTP {code}"
    # No numeric status (a duck-typed response): trust its success flag.
    success = getattr(response, "is_success", None)
    if success is None:
        success = getattr(response, "ok", False)
    return (ROBOTS_OK, "") if success else (ROBOTS_UNREACHABLE, "request failed")


def _rules_from_response(response: Any, robots_url: str) -> Tuple[RobotsRules, str]:
    status, reason = _classify_response(response)
    text = getattr(response, "text", "") if status == ROBOTS_OK else ""
    if not isinstance(text, str):
        text = ""
    logger.debug("robots.txt %s: %s (%s)", robots_url, status, reason)
    return RobotsRules(text, status=status, reason=reason), text


def _unreachable(robots_url: str, exc: BaseException) -> Tuple[RobotsRules, str]:
    reason = f"{type(exc).__name__}: {exc}" if str(exc) else type(exc).__name__
    logger.debug("robots.txt %s unreachable: %s", robots_url, reason)
    return RobotsRules(status=ROBOTS_UNREACHABLE, reason=reason), ""


def parse_robots_txt(session: Any, robots_url: str) -> Tuple[RobotsRules, str]:
    """Fetch robots.txt and return ``(rules, raw_text)``.

    ``rules.status`` follows RFC 9309 section 2.3.1: 2xx is parsed; 4xx is
    *unavailable* (no rules, everything allowed); 5xx, 429 and network
    errors are *unreachable* (everything disallowed).  *raw_text* is the
    body for a 2xx and ``""`` otherwise.
    """
    try:
        response = session.get(robots_url, timeout=10)
    except Exception as exc:
        return _unreachable(robots_url, exc)
    return _rules_from_response(response, robots_url)


def discover_sitemaps(session: Any, base: str, robots_text: Optional[str] = None) -> List[str]:
    """Find sitemap URLs declared in the site's ``robots.txt``."""
    import urllib.parse as up

    if robots_text is None:
        robots_url = up.urljoin(base, "/robots.txt")
        try:
            response = session.get(robots_url, timeout=10)
            if not response.ok:
                return []
            robots_text = response.text
        except Exception:
            return []

    sitemaps: List[str] = []
    for line in robots_text.splitlines():
        if line.lower().startswith("sitemap:"):
            sitemap_url = line.split(":", 1)[1].strip()
            if sitemap_url:
                sitemaps.append(sitemap_url)
    return sitemaps


_DEFAULT_SITEMAP_TIME_BUDGET_S = 60.0


def parse_sitemap_xml(
    session: Any,
    url: str,
    timeout: int,
    *,
    _depth: int = 0,
    _visited: Optional[set] = None,
    _deadline: Optional[float] = None,
    max_depth: int = 5,
    max_total_urls: int = 5000,
    time_budget_s: float = _DEFAULT_SITEMAP_TIME_BUDGET_S,
    url_filter: Optional[Any] = None,
) -> List[str]:
    """Recursively parse a sitemap XML and return all page URLs.

    Guards:
    * *max_depth* (default 5) bounds recursion into nested sitemap indexes.
    * *_visited* set prevents re-fetching the same sitemap (cycles).
    * *max_total_urls* (default 5000) early-exits when enough URLs have
      been collected. Critical for sites like npr.org whose sitemap index
      points to dozens of 50K-URL child sitemaps; without the cap we
      spent 245s on sitemap parsing alone for a 50-page crawl. Caller
      should pass ``max(500, max_pages * 4)`` to scale with the budget.
    * *time_budget_s* (default 60s) caps total wallclock spent in
      sitemap pre-enumeration regardless of count. Pathological retailer
      indexes (ikea: 2,113 sub-sitemaps) used to consume 200+s before
      any page got crawled, tripping zero-output watchdogs in benchmark
      harnesses (introduced in v0.10.2). Once the deadline fires, the
      function returns whatever URLs it has collected so far.
    * *url_filter*, if provided, is called for each URL; only URLs where
      the filter returns True are kept. Filtering during parse avoids
      retaining tens of thousands of out-of-scope URLs only to discard
      them at the next stage. Caller's filter should match the in-scope
      / allowed / not-excluded predicates the engine will apply anyway.
    """
    import time as _time
    if _depth > max_depth:
        return []
    if _visited is None:
        _visited = set()
    if _deadline is None:
        _deadline = _time.monotonic() + time_budget_s
    if _time.monotonic() >= _deadline:
        return []
    if url in _visited:
        return []
    _visited.add(url)

    try:
        response = session.get(url, timeout=timeout)
        if not response.ok:
            return []
        content_type = response.headers.get("content-type", "").lower()
        if not (content_type.startswith("application/xml") or response.text.strip().startswith("<")):
            return []
        root = ET.fromstring(response.content)
    except Exception:
        return []

    ns = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
    urls: List[str] = []

    def _accept(u: str) -> bool:
        return url_filter is None or url_filter(u)

    for loc in root.findall(".//sm:sitemap/sm:loc", ns):
        if len(urls) >= max_total_urls:
            break
        if _time.monotonic() >= _deadline:
            break
        child_url = (loc.text or "").strip()
        if child_url:
            child_urls = parse_sitemap_xml(
                session, child_url, timeout,
                _depth=_depth + 1, _visited=_visited, _deadline=_deadline,
                max_depth=max_depth,
                max_total_urls=max_total_urls - len(urls),
                url_filter=url_filter,
            )
            urls.extend(child_urls)

    for loc in root.findall(".//sm:url/sm:loc", ns):
        if len(urls) >= max_total_urls:
            break
        page_url = (loc.text or "").strip()
        if page_url and _accept(page_url):
            urls.append(page_url)

    if not urls:
        for loc in root.findall(".//loc"):
            if len(urls) >= max_total_urls:
                break
            page_url = (loc.text or "").strip()
            if page_url and _accept(page_url):
                urls.append(page_url)

    return list(dict.fromkeys(urls))


# ---------------------------------------------------------------------------
# Async variants
# ---------------------------------------------------------------------------

async def parse_robots_txt_async(client: Any, robots_url: str) -> Tuple[RobotsRules, str]:
    """Async version of :func:`parse_robots_txt` (same status rules)."""
    try:
        response = await client.get(robots_url, timeout=10)
    except Exception as exc:
        return _unreachable(robots_url, exc)
    return _rules_from_response(response, robots_url)


_SITEMAP_CHILD_CONCURRENCY = 10


async def parse_sitemap_xml_async(
    client: Any,
    url: str,
    timeout: int,
    *,
    _depth: int = 0,
    _visited: Optional[set] = None,
    _semaphore: Optional[Any] = None,
    _deadline: Optional[float] = None,
    max_depth: int = 5,
    max_total_urls: int = 5000,
    time_budget_s: float = _DEFAULT_SITEMAP_TIME_BUDGET_S,
    url_filter: Optional[Any] = None,
) -> List[str]:
    """Async version of :func:`parse_sitemap_xml`. Same caps semantics.

    Child-sitemap fetches inside an index are parallelized via
    asyncio.as_completed so we can short-circuit pending children once
    *max_total_urls* or *time_budget_s* fires. Multi-tenant sitemap
    indexes (npr.org, ikea with 2,113 locale shards) used to consume
    200+s before any page got crawled — the deadline fix landed in
    v0.10.2 to keep the pre-enumeration phase bounded. Concurrency is
    still capped at _SITEMAP_CHILD_CONCURRENCY so we don't hammer the
    target.
    """
    import time as _time
    if _depth > max_depth:
        return []
    if _visited is None:
        _visited = set()
    if _deadline is None:
        _deadline = _time.monotonic() + time_budget_s
    if _time.monotonic() >= _deadline:
        return []
    if _semaphore is None:
        import asyncio as _asyncio  # local import keeps top of file clean
        _semaphore = _asyncio.Semaphore(_SITEMAP_CHILD_CONCURRENCY)
    if url in _visited:
        return []
    _visited.add(url)

    try:
        response = await client.get(url, timeout=timeout)
        if not response.is_success:
            return []
        content_type = response.headers.get("content-type", "").lower()
        if not (content_type.startswith("application/xml") or response.text.strip().startswith("<")):
            return []
        root = ET.fromstring(response.content)
    except Exception:
        return []

    ns = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
    urls: List[str] = []

    def _accept(u: str) -> bool:
        return url_filter is None or url_filter(u)

    # Collect all child sitemap URLs first, then fetch in parallel.
    child_loc_urls: List[str] = []
    for loc in root.findall(".//sm:sitemap/sm:loc", ns):
        child_url = (loc.text or "").strip()
        if child_url and child_url not in _visited:
            child_loc_urls.append(child_url)

    if child_loc_urls:
        import asyncio as _asyncio

        async def _fetch_child(child_url: str) -> List[str]:
            # Skip if the budget already fired before we even started.
            if _time.monotonic() >= _deadline:
                return []
            async with _semaphore:
                if _time.monotonic() >= _deadline:
                    return []
                return await parse_sitemap_xml_async(
                    client, child_url, timeout,
                    _depth=_depth + 1, _visited=_visited,
                    _semaphore=_semaphore, _deadline=_deadline,
                    max_depth=max_depth,
                    max_total_urls=max_total_urls,
                    url_filter=url_filter,
                )

        # Fan out via as_completed so we can short-circuit once the
        # URL cap or the deadline fires; cancel pending tasks rather
        # than waiting for all 2,113 children to resolve.
        tasks = [_asyncio.create_task(_fetch_child(cu)) for cu in child_loc_urls]
        try:
            for fut in _asyncio.as_completed(tasks):
                try:
                    r = await fut
                except Exception:
                    r = []
                urls.extend(r)
                if len(urls) >= max_total_urls or _time.monotonic() >= _deadline:
                    break
        finally:
            for t in tasks:
                if not t.done():
                    t.cancel()

    for loc in root.findall(".//sm:url/sm:loc", ns):
        if len(urls) >= max_total_urls:
            break
        page_url = (loc.text or "").strip()
        if page_url and _accept(page_url):
            urls.append(page_url)

    if not urls:
        for loc in root.findall(".//loc"):
            if len(urls) >= max_total_urls:
                break
            page_url = (loc.text or "").strip()
            if page_url and _accept(page_url):
                urls.append(page_url)

    return list(dict.fromkeys(urls))[:max_total_urls]

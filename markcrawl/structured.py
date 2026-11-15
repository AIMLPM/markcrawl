"""Schema.org structured data (JSON-LD) found on a page.

Many pages describe themselves in ``<script type="application/ld+json">``
blocks: a job posting's places, a product's price, an article's author.
:func:`extract_structured_data` returns those blocks as plain dicts, and
the crawler stores the same list on every :class:`~markcrawl.PageData`
(``structured_data``) and in the page's ``pages.jsonl`` row.

The helpers only read what a block states.  They never raise on malformed
input and never fill a field the block does not give.
"""
from __future__ import annotations

import json
import logging
import re
from typing import Any, Iterable, List, Optional

from bs4 import BeautifulSoup, SoupStrainer

from .utils import HTML_PARSER

logger = logging.getLogger(__name__)

#: A ``<script type="application/ld+json">`` whose text is larger than this
#: (in UTF-8 bytes) is skipped.  Real JobPosting, Product and Article
#: blocks are a few KB; the bound keeps catalogue dumps (multi-MB
#: ItemList blocks repeated on every page of a shop) out of the crawl
#: result and the JSONL index.
MAX_JSON_LD_BLOCK_BYTES = 128 * 1024

_LD_JSON_HINT = re.compile(r"application/ld\+json", re.IGNORECASE)
# An opening HTML comment or CDATA marker (``<!--``, ``<![CDATA[``,
# ``//<![CDATA[``, ``/*<![CDATA[*/``).  The closing marker needs no rule:
# it is trailing garbage after the last value, which the parser stops at.
_LEADING_WRAPPER = re.compile(r"^\s*(?:<!--|(?:/\*\s*|//\s*)?<!\[CDATA\[(?:\s*\*/)?)")
_DECODER = json.JSONDecoder(strict=False)  # tolerate raw newlines inside strings
_MAX_DEPTH = 32


def _is_json_ld_type(value: Optional[str]) -> bool:
    return bool(value) and value.split(";", 1)[0].strip().lower() == "application/ld+json"


def _parse_block(text: str) -> List[Any]:
    """Parse one script's text into JSON values, tolerating real-page noise:
    HTML comment and CDATA wrappers, several values in one block, and
    trailing garbage after the last value."""
    text = _LEADING_WRAPPER.sub("", text, count=1).strip()
    values: List[Any] = []
    pos = 0
    while pos < len(text):
        try:
            value, end = _DECODER.raw_decode(text, pos)
        except (ValueError, RecursionError):
            break
        values.append(value)
        pos = end
        while pos < len(text) and text[pos] in " \t\r\n;,":
            pos += 1
    return values


def _flatten(value: Any, out: List[dict], context: Any = None, depth: int = 0) -> None:
    """Append every object in *value* to *out*: array elements in turn, and
    the members of an ``@graph`` container (each given the container's
    ``@context`` when it has none of its own)."""
    if depth > _MAX_DEPTH:
        return
    if isinstance(value, list):
        for element in value:
            _flatten(element, out, context, depth + 1)
        return
    if not isinstance(value, dict):
        return
    graph = value.get("@graph")
    if not isinstance(graph, (list, dict)):
        out.append(value)
        return
    context = value.get("@context", context)
    container = {k: v for k, v in value.items() if k != "@graph"}
    if "@type" in container:
        out.append(container)
    for member in graph if isinstance(graph, list) else [graph]:
        if isinstance(member, dict) and context is not None and "@context" not in member:
            member = {"@context": context, **member}
        _flatten(member, out, context, depth + 1)


def _structured_data_from_soup(soup: Any, max_block_bytes: Optional[int]) -> List[dict]:
    items: List[dict] = []
    for script in soup.find_all("script", type=_is_json_ld_type):
        text = script.string or ""
        if max_block_bytes is not None and len(text.encode("utf-8", "replace")) > max_block_bytes:
            logger.debug("Skipping JSON-LD block of %d chars (over %d bytes)", len(text), max_block_bytes)
            continue
        for value in _parse_block(text):
            _flatten(value, items)
    return items


def extract_structured_data(
    html: str,
    max_block_bytes: Optional[int] = MAX_JSON_LD_BLOCK_BYTES,
) -> List[dict]:
    """Return the JSON-LD objects in *html*, in document order (head and body).

    Each ``<script type="application/ld+json">`` block may hold one object,
    an array of objects, or an ``@graph`` container; arrays and ``@graph``
    members are returned as separate items.  HTML comment and CDATA
    wrappers, raw newlines inside strings and trailing garbage are
    tolerated; a block that still does not parse is skipped.  A block
    larger than *max_block_bytes* (default ``MAX_JSON_LD_BLOCK_BYTES``,
    128 KiB of UTF-8) is skipped; pass ``None`` to keep every block.

    Never raises: bad input returns ``[]``.
    """
    try:
        if not isinstance(html, str) or not _LD_JSON_HINT.search(html):
            return []
        soup = BeautifulSoup(html, HTML_PARSER, parse_only=SoupStrainer("script"))
        return _structured_data_from_soup(soup, max_block_bytes)
    except Exception:  # never let a hostile page break a crawl
        logger.debug("JSON-LD extraction failed", exc_info=True)
        return []


def _has_type(item: dict, type_name: str) -> bool:
    types = item.get("@type")
    for t in types if isinstance(types, list) else [types]:
        if isinstance(t, str) and (
            t == type_name or t.endswith("/" + type_name) or t.endswith(":" + type_name)
        ):
            return True
    return False


def find_items(items: Iterable[dict], type_name: str) -> List[dict]:
    """Return the items whose ``@type`` is *type_name* (or a list containing
    it).  ``@graph`` containers are searched too, and full or compact IRIs
    (``https://schema.org/JobPosting``, ``schema:JobPosting``) match."""
    flat: List[dict] = []
    try:
        _flatten(items if isinstance(items, dict) else list(items or []), flat)
    except TypeError:
        return []
    return [item for item in flat if _has_type(item, type_name)]


# ---------------------------------------------------------------------------
# JobPosting places
# ---------------------------------------------------------------------------

_ADDRESS_KEYS = ("addressLocality", "addressRegion", "addressCountry", "postalCode")
_AREA_FIELD = {"Country": "country", "State": "region", "City": "locality"}


def _as_list(value: Any) -> List[Any]:
    return value if isinstance(value, list) else ([] if value is None else [value])


def _text(value: Any) -> Optional[str]:
    if isinstance(value, dict):
        value = value.get("name")
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        value = str(value)
    return (value.strip() or None) if isinstance(value, str) else None


def _place(remote: bool, **fields: Optional[str]) -> Optional[dict]:
    if not any(fields.values()) and not remote:
        return None
    place = dict.fromkeys(("locality", "region", "country", "postal_code", "address_text"))
    place.update(fields)
    place["remote"] = remote
    return place


def _address_place(address: Any) -> Optional[dict]:
    if isinstance(address, str):
        return _place(False, address_text=_text(address))
    if not isinstance(address, dict):
        return None
    return _place(
        False,
        locality=_text(address.get("addressLocality")),
        region=_text(address.get("addressRegion")),
        country=_text(address.get("addressCountry")),
        postal_code=_text(address.get("postalCode")),
    )


def job_posting_places(item: dict) -> List[dict]:
    """Return the places a schema.org ``JobPosting`` states, as plain dicts:
    ``{locality, region, country, postal_code, address_text, remote}``.

    * Each ``jobLocation`` address gives one place with ``remote=False``.
      A plain-text address is kept whole in ``address_text``, not split.
    * Each ``applicantLocationRequirements`` area (where a remote worker may
      be) gives one place with ``remote=True``: a Country fills ``country``,
      a State ``region``, a City ``locality``, anything else ``address_text``.
    * ``jobLocationType: TELECOMMUTE`` with no stated area adds one
      ``remote=True`` place with every other field ``None``.

    Fields the block does not state are ``None``; nothing is inferred.
    """
    if not isinstance(item, dict):
        return []
    places: List[Optional[dict]] = []
    for location in _as_list(item.get("jobLocation")):
        if not isinstance(location, dict):
            continue
        address = location.get("address")
        if address is None and any(k in location for k in _ADDRESS_KEYS):
            address = location  # address fields written on the Place itself
        places.extend(_address_place(a) for a in _as_list(address))
    for area in _as_list(item.get("applicantLocationRequirements")):
        name = _text(area) if isinstance(area, (str, dict)) else None
        if not name:
            continue
        area_type = area.get("@type") if isinstance(area, dict) else None
        field = _AREA_FIELD.get(area_type, "address_text") if isinstance(area_type, str) else "address_text"
        places.append(_place(True, **{field: name}))
    result = [p for p in places if p]
    telecommute = any(
        isinstance(t, str) and t.strip().upper() == "TELECOMMUTE"
        for t in _as_list(item.get("jobLocationType"))
    )
    if telecommute and not any(p["remote"] for p in result):
        result.append(_place(True))
    return result

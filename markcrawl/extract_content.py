"""Content extraction — HTML to Markdown/text conversion and DOM cleaning."""
from __future__ import annotations

import re
import urllib.parse as up
from typing import Callable, List, Optional, Set, Tuple

from bs4 import BeautifulSoup

from .urls import norm_url
from .utils import HTML_PARSER as _PARSER

try:
    from markdownify import markdownify as md_convert
except Exception:
    md_convert = None

EXCLUDE_TAGS = {"script", "style", "noscript", "template", "svg", "canvas"}
STRUCTURE_TAGS = {"nav", "header", "footer", "aside"}


def clean_dom_for_content(soup: BeautifulSoup) -> None:
    for tag in soup.find_all(EXCLUDE_TAGS):
        tag.decompose()
    for tag in soup.find_all(STRUCTURE_TAGS):
        tag.decompose()
    for el in soup.select(
        '[role="navigation"], [aria-hidden="true"], .sr-only, .visually-hidden, .cookie, .Cookie, .cookie-banner, .consent'
    ):
        try:
            el.decompose()
        except Exception:
            pass


def compact_blank_lines(text: str, max_blank_streak: int = 2) -> str:
    lines = [line.rstrip() for line in text.splitlines()]
    output: List[str] = []
    blank_streak = 0
    for line in lines:
        if line.strip():
            blank_streak = 0
            output.append(line)
        else:
            blank_streak += 1
            if blank_streak <= max_blank_streak:
                output.append("")
    return "\n".join(output).strip()


def _extract_links_from_soup(soup: BeautifulSoup, base_url: Optional[str]) -> Set[str]:
    """Extract normalised links from an already-parsed soup (no re-parse needed)."""
    if base_url is None:
        return set()
    links: Set[str] = set()
    for anchor in soup.find_all("a", href=True):
        href = anchor["href"].strip()
        absolute_url = up.urljoin(base_url, href)
        links.add(norm_url(absolute_url))
    return links


def html_to_markdown(html: str, base_url: Optional[str] = None) -> Tuple[str, str, Set[str]]:
    """Convert raw HTML to cleaned Markdown text.

    Returns ``(title, markdown, links)`` where *links* is the set of
    normalised ``<a href>`` URLs found in the document.  Extracting links
    during the same parse avoids a second BeautifulSoup pass.
    """
    soup = BeautifulSoup(html, _PARSER)
    links = _extract_links_from_soup(soup, base_url)
    clean_dom_for_content(soup)
    title = (soup.title.string or "").strip() if soup.title else ""
    main = soup.find("main") or soup.find(attrs={"role": "main"}) or soup.body or soup
    html_fragment = str(main)

    if md_convert:
        markdown = md_convert(
            html_fragment,
            heading_style="ATX",
            strip=["img"],
            wrap=False,
            bullets="*",
            escape_asterisks=False,
            escape_underscores=False,
            code_language=False,
        )
    else:
        markdown = BeautifulSoup(html_fragment, _PARSER).get_text("\n")

    return title, compact_blank_lines(markdown), links


def html_to_text(html: str, base_url: Optional[str] = None) -> Tuple[str, str, Set[str]]:
    """Convert raw HTML to cleaned plain text.

    Returns ``(title, text, links)``.
    """
    soup = BeautifulSoup(html, _PARSER)
    links = _extract_links_from_soup(soup, base_url)
    clean_dom_for_content(soup)
    title = (soup.title.string or "").strip() if soup.title else ""
    text = soup.get_text(separator="\n")
    lines = [re.sub(r"\s+", " ", line).strip() for line in text.splitlines()]
    lines = [line for line in lines if line]

    deduped: List[str] = []
    previous: Optional[str] = None
    for line in lines:
        if line != previous:
            deduped.append(line)
        previous = line
    return title, "\n".join(deduped).strip(), links


def default_progress(enabled: bool) -> Callable[[str], None]:
    def emit(message: str) -> None:
        if enabled:
            print(message)
    return emit

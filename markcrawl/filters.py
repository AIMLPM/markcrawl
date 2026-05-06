"""Reusable best-effort filters for the ``download_filter`` callback.

Used with :func:`markcrawl.crawl` when ``download_types`` is set, to
filter out files that match the requested type but aren't what the
caller actually wants — e.g. a `.pdf` link that points to a privacy
policy when the caller is harvesting resume templates.

The crawler provides hooks; domain-specific classification ("is this
*actually* a resume?") remains the caller's responsibility.  These
helpers are starting points, not classifiers.  Test against your real
corpus before relying on them.

Filters are pure functions of :class:`DownloadCandidate` and run
**pre-fetch** — rejected URLs are never fetched, so anchor text is the
highest-leverage signal.

Example::

    from markcrawl import crawl
    from markcrawl.filters import is_likely_resume

    result = crawl(
        base_url="https://example.com/templates",
        out_dir="out/",
        download_types=["pdf", "docx"],
        download_filter=is_likely_resume,
    )

To compose with your own logic::

    def my_filter(c):
        return is_likely_resume(c) and "spam" not in c.url

    crawl(..., download_filter=my_filter)
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DownloadCandidate:
    """Pre-fetch context passed to ``download_filter`` callbacks.

    Attributes:
        url: Absolute URL of the candidate binary.
        anchor_text: Text inside the ``<a>`` tag that linked here, or
            ``""`` if the URL came from a sitemap or a bare-href link.
            Empty anchor is common; filters must handle it.
        parent_url: URL of the page that linked to this candidate (or
            the seed/base URL for sitemap-discovered candidates).
        parent_title: Title of the parent page, or ``"<sitemap>"`` for
            sitemap-discovered candidates.
        extension: Lowercase file extension extracted from the URL,
            including the leading dot (e.g. ``".pdf"``).  May be empty
            if the URL has no extension; in that case the candidate
            matched on a MIME-prefix configured via ``download_types``.
    """
    url: str
    anchor_text: str
    parent_url: str
    parent_title: str
    extension: str


# --- Internal helpers ------------------------------------------------------

# Words that, if present in URL or anchor text, strongly suggest the
# candidate is legal/marketing/admin boilerplate rather than content
# the user wants to ingest.  Used as a negative selector across all
# starter filters.
_LEGAL_BOILERPLATE_TERMS = frozenset({
    "privacy", "terms", "policy", "policies", "legal",
    "investor", "shareholder", "annual-report", "sec-filing",
    "cookie", "gdpr", "ccpa", "disclaimer", "compliance",
    "press-release", "presskit", "media-kit",
})

# Resume/CV positive signals.  Multilingual variants kept conservative
# to avoid false positives (e.g. "lebenslauf" — German for CV — is
# included; "currículum" — Spanish — relies on common ASCII spelling).
_RESUME_TERMS = frozenset({
    "resume", "resumes",
    "cv", "cvs",
    "curriculum", "curriculum-vitae",
    "lebenslauf",
    "vita",
    "template", "templates", "sample", "samples",
    "example", "examples",
    "starter", "boilerplate-resume",
})

# Academic paper / research positive signals.
_PAPER_TERMS = frozenset({
    "paper", "papers", "preprint", "preprints",
    "research", "study", "studies",
    "abstract", "manuscript",
    "publication", "publications",
    "article", "articles",
    "whitepaper", "white-paper",
    "thesis", "dissertation",
})


def _normalize_terms(text: str) -> set:
    """Lowercase and split a string on common separators for term matching."""
    if not text:
        return set()
    lowered = text.lower()
    # Split on whitespace, hyphen, underscore, slash, dot, query/fragment markers.
    for sep in ("/", "-", "_", "?", "&", "=", "#", ".", " ", "\t", "\n"):
        lowered = lowered.replace(sep, " ")
    return {t for t in lowered.split() if t}


def _candidate_terms(c: DownloadCandidate) -> set:
    """Aggregate normalized terms from URL + anchor text."""
    return _normalize_terms(c.url) | _normalize_terms(c.anchor_text)


# --- Public filters --------------------------------------------------------

def is_likely_resume(c: DownloadCandidate) -> bool:
    """Best-effort filter for resume / CV templates.

    Returns True when the candidate's URL or anchor text contains
    resume/CV positive signals AND does not contain legal-boilerplate
    negative signals.  When anchor text is empty (sitemap-discovered,
    bare-href links), falls back to URL-only matching.

    Not a classifier — multilingual edge cases, unusual filename
    conventions, and heavily-stylized hosting URLs may produce false
    negatives.  Compose with your own predicates for production use.
    """
    terms = _candidate_terms(c)
    if not terms:
        return False
    if terms & _LEGAL_BOILERPLATE_TERMS:
        return False
    return bool(terms & _RESUME_TERMS)


def is_likely_paper(c: DownloadCandidate) -> bool:
    """Best-effort filter for academic papers / research articles.

    Returns True when URL or anchor text contains paper/research
    positive signals AND does not contain legal-boilerplate signals.

    Subject to the same caveats as :func:`is_likely_resume`.
    """
    terms = _candidate_terms(c)
    if not terms:
        return False
    if terms & _LEGAL_BOILERPLATE_TERMS:
        return False
    return bool(terms & _PAPER_TERMS)


def exclude_legal_boilerplate(c: DownloadCandidate) -> bool:
    """Pure negative selector — returns True when the candidate is
    NOT obvious legal/marketing boilerplate.

    Designed to compose with positive filters via boolean ``and``::

        download_filter = lambda c: my_positive(c) and exclude_legal_boilerplate(c)

    On its own this filter is permissive — it returns True for almost
    everything that isn't a privacy policy or investor-relations doc.
    """
    terms = _candidate_terms(c)
    return not (terms & _LEGAL_BOILERPLATE_TERMS)

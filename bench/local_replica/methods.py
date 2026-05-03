"""DS-5: Candidate render_js detection methods + cascade.

Each method is a pure function: given a SiteProfile-like dict (the scan
signals captured per site in labeled_sites.json), return whether to
promote `render_js=True`. The autoresearch sweep (DS-6) scores each
method on the labeled dataset.

Methods:
  M1  static-is-spa     -- current heuristic, is_spa=True triggers promote
  M2  seed-word-thresh  -- class-gated seed_word_count < threshold
  M3  trip-wire         -- 5-page yield check (placeholder; needs crawl loop hook)
  M4  empty-extract     -- post-Playwright terminal check (placeholder)
  M5  ratio-signal      -- HTML-size / visible-text ratio (post-fetch signal)
  M6  cascade           -- M1 -> M2 -> (gate signals for M3/M4)

Each function returns a dict:
  {"promote": bool, "rule": str, "signal": str, "cost_seconds": float}

For the sweep, "trip-wire" rules need crawl-time data; methods.py
returns "promote=None" for those when only scan signals are available,
and the sweep aggregates them after a small probe crawl.
"""
from __future__ import annotations

from typing import Dict, Optional

# Class-gated thresholds: classes where a thin seed page is a strong
# render_js signal. Wiki/blog/ecom seeds are often genuinely thin
# (category indexes), so they are excluded -- promoting them to
# Playwright would be a false positive.
SEED_WORD_THRESHOLDS: Dict[str, int] = {
    "apiref":  100,    # API doc landing pages should have intro prose
    "docs":    150,    # docs landing has overview text
    "spa":     100,    # SPA shells return very little
    "generic": 50,     # be conservative on unknown
}


def m1_static_is_spa(scan: Dict) -> Dict:
    """Current heuristic: trust js_detect.is_spa flag."""
    is_spa = scan.get("is_spa")
    if is_spa is True:
        return {"promote": True, "rule": "M1", "signal": "is_spa=True",
                "cost_seconds": 0.0}
    return {"promote": False, "rule": "M1", "signal": f"is_spa={is_spa}",
            "cost_seconds": 0.0}


def m2_seed_word_thresh(scan: Dict) -> Dict:
    """Class-gated: thin seed in apiref/docs/spa/generic implies JS shell."""
    cls = scan.get("url_class", "generic")
    swc = scan.get("seed_word_count", -1)
    threshold = SEED_WORD_THRESHOLDS.get(cls)
    if threshold is None:
        return {"promote": False, "rule": "M2",
                "signal": f"class={cls} not gated",
                "cost_seconds": 0.0}
    if swc < 0:
        return {"promote": False, "rule": "M2",
                "signal": f"seed_word_count unknown",
                "cost_seconds": 0.0}
    if swc < threshold:
        return {"promote": True, "rule": "M2",
                "signal": f"class={cls} seed_word_count={swc}<{threshold}",
                "cost_seconds": 0.0}
    return {"promote": False, "rule": "M2",
            "signal": f"class={cls} seed_word_count={swc}>={threshold}",
            "cost_seconds": 0.0}


def m3_trip_wire(scan: Dict, first_n_pages: Optional[list] = None,
                 n_required: int = 4, n_total: int = 5,
                 word_threshold: int = 50) -> Dict:
    """N-of-M trip-wire: after crawling first 5 pages, if 4+ have <50 words, promote.

    Requires `first_n_pages` (list of dicts with `text` field) supplied by
    the caller. When unavailable (pure scan), returns promote=None.
    """
    if first_n_pages is None:
        return {"promote": None, "rule": "M3",
                "signal": "no crawl data; deferred",
                "cost_seconds": 2.5}  # estimated 5 fetches
    if len(first_n_pages) < n_total:
        return {"promote": None, "rule": "M3",
                "signal": f"only {len(first_n_pages)} pages crawled",
                "cost_seconds": 2.5}
    thin = sum(1 for p in first_n_pages
               if len((p.get("text") or "").split()) < word_threshold)
    if thin >= n_required:
        return {"promote": True, "rule": "M3",
                "signal": f"{thin}/{n_total} pages thin (<{word_threshold} words)",
                "cost_seconds": 2.5}
    return {"promote": False, "rule": "M3",
            "signal": f"{thin}/{n_total} pages thin (<{word_threshold} words)",
            "cost_seconds": 2.5}


def m4_empty_extract(rendered_pages: Optional[list] = None,
                     n_check: int = 5,
                     word_threshold: int = 20) -> Dict:
    """Terminal check: even after Playwright, are pages empty?

    Catches mui.com-style cases where render_js=True still extracts 0-byte
    markdown. Used to STOP cycling, not to promote (we already promoted to
    get here). Returns promote=False if the rendered crawl is also empty
    (signals "give up").
    """
    if rendered_pages is None:
        return {"promote": None, "rule": "M4",
                "signal": "no rendered crawl data",
                "cost_seconds": 0.0}
    sample = rendered_pages[:n_check]
    if not sample:
        return {"promote": False, "rule": "M4",
                "signal": "no pages after render",
                "cost_seconds": 0.0}
    thin = sum(1 for p in sample
               if len((p.get("text") or "").split()) < word_threshold)
    if thin >= n_check:
        return {"promote": False, "rule": "M4",
                "signal": f"all {n_check} rendered pages thin -- give up",
                "cost_seconds": 0.0}
    return {"promote": True, "rule": "M4",
            "signal": f"{n_check - thin}/{n_check} rendered pages have content",
            "cost_seconds": 0.0}


def m5_ratio_signal(scan: Dict, html_bytes: int = 0,
                    visible_text_bytes: int = 0) -> Dict:
    """Heuristic: large HTML response with tiny visible text = JS-shelled.

    Requires html/text byte counts captured during the seed fetch. When
    unavailable (current scan doesn't capture this), returns promote=None.
    """
    if html_bytes == 0 or visible_text_bytes == 0:
        return {"promote": None, "rule": "M5",
                "signal": "no html/text byte counts",
                "cost_seconds": 0.0}
    ratio = html_bytes / max(visible_text_bytes, 1)
    if ratio > 50:  # 50:1 HTML-to-text is heavy JS shell
        return {"promote": True, "rule": "M5",
                "signal": f"html/text ratio={ratio:.1f}>50",
                "cost_seconds": 0.0}
    return {"promote": False, "rule": "M5",
            "signal": f"html/text ratio={ratio:.1f}<=50",
            "cost_seconds": 0.0}


def m6_cascade(scan: Dict, first_n_pages: Optional[list] = None,
               rendered_pages: Optional[list] = None,
               html_bytes: int = 0, visible_text_bytes: int = 0,
               user_render_js: Optional[bool] = None) -> Dict:
    """Cascade: priority-order short-circuit.

    Order:
      0. user-set render_js -> respect
      1. M1 (is_spa=True) -> promote
      2. M2 (class-gated seed_word_count) -> promote
      3. M5 (HTML/text ratio if available) -> promote
      4. M3 (trip-wire after 5 pages) -> promote/keep
      5. M4 (post-Playwright terminal check) -> stop cycling

    Returns the first rule that fired. Cascade speed cost is the sum of
    cheap rules (M1, M2, M5 = 0s) until either a promote fires or M3
    requires the trip-wire crawl.
    """
    cost = 0.0

    # Rule 0: user authority
    if user_render_js is not None:
        return {"promote": user_render_js, "rule": "M6/user",
                "signal": f"user_render_js={user_render_js}",
                "cost_seconds": cost}

    # Rule 1: is_spa
    r = m1_static_is_spa(scan)
    if r["promote"]:
        return {"promote": True, "rule": "M6/M1",
                "signal": r["signal"], "cost_seconds": cost}

    # Rule 2: seed word count
    r = m2_seed_word_thresh(scan)
    if r["promote"]:
        return {"promote": True, "rule": "M6/M2",
                "signal": r["signal"], "cost_seconds": cost}

    # Rule 5: ratio (if available)
    if html_bytes > 0:
        r = m5_ratio_signal(scan, html_bytes, visible_text_bytes)
        if r["promote"]:
            return {"promote": True, "rule": "M6/M5",
                    "signal": r["signal"], "cost_seconds": cost}

    # Rule 3: trip-wire
    if first_n_pages is not None:
        r = m3_trip_wire(scan, first_n_pages)
        cost += r.get("cost_seconds", 0.0)
        if r["promote"] is True:
            return {"promote": True, "rule": "M6/M3",
                    "signal": r["signal"], "cost_seconds": cost}
        if r["promote"] is False:
            return {"promote": False, "rule": "M6/M3",
                    "signal": r["signal"], "cost_seconds": cost}

    # Default: don't promote
    return {"promote": False, "rule": "M6/default",
            "signal": "no cascade rule fired", "cost_seconds": cost}


# Method registry for the sweep
METHODS = {
    "M1-is-spa":      m1_static_is_spa,
    "M2-seed-words":  m2_seed_word_thresh,
    "M3-trip-wire":   m3_trip_wire,
    "M5-ratio":       m5_ratio_signal,
    "M6-cascade":     m6_cascade,
}

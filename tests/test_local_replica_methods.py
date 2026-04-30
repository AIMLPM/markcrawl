"""Unit tests for bench/local_replica/methods.py — DS-5 cascade rules."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "bench" / "local_replica"))

from methods import (  # noqa: E402
    m1_static_is_spa, m2_seed_word_thresh, m3_trip_wire,
    m4_empty_extract, m5_ratio_signal, m6_cascade,
)


# ---- M1: is_spa --------------------------------------------------------

def test_m1_promotes_when_is_spa_true():
    r = m1_static_is_spa({"is_spa": True})
    assert r["promote"] is True
    assert r["rule"] == "M1"


def test_m1_skips_when_is_spa_false():
    r = m1_static_is_spa({"is_spa": False})
    assert r["promote"] is False


def test_m1_skips_when_is_spa_none():
    r = m1_static_is_spa({"is_spa": None})
    assert r["promote"] is False


# ---- M2: seed word threshold (class-gated) -----------------------------

def test_m2_promotes_apiref_thin_seed():
    r = m2_seed_word_thresh({"url_class": "apiref", "seed_word_count": 50})
    assert r["promote"] is True


def test_m2_skips_apiref_rich_seed():
    r = m2_seed_word_thresh({"url_class": "apiref", "seed_word_count": 500})
    assert r["promote"] is False


def test_m2_skips_wiki_thin_seed():
    """Wiki is NOT in the gated set — thin wiki seeds are normal (category indexes)."""
    r = m2_seed_word_thresh({"url_class": "wiki", "seed_word_count": 30})
    assert r["promote"] is False


def test_m2_skips_blog_thin_seed():
    r = m2_seed_word_thresh({"url_class": "blog", "seed_word_count": 20})
    assert r["promote"] is False


def test_m2_skips_when_seed_word_count_unknown():
    r = m2_seed_word_thresh({"url_class": "apiref", "seed_word_count": -1})
    assert r["promote"] is False


def test_m2_promotes_docs_thin_seed():
    r = m2_seed_word_thresh({"url_class": "docs", "seed_word_count": 100})
    assert r["promote"] is True


def test_m2_promotes_spa_thin_seed():
    r = m2_seed_word_thresh({"url_class": "spa", "seed_word_count": 50})
    assert r["promote"] is True


# ---- M3: trip-wire (N-of-M) -------------------------------------------

def test_m3_returns_none_when_no_pages():
    r = m3_trip_wire({"url_class": "apiref"})
    assert r["promote"] is None


def test_m3_promotes_when_4_of_5_thin():
    pages = [{"text": ""}, {"text": ""}, {"text": ""}, {"text": ""},
             {"text": "lots of words " * 20}]
    r = m3_trip_wire({}, first_n_pages=pages)
    assert r["promote"] is True


def test_m3_skips_when_only_2_of_5_thin():
    pages = [{"text": ""}, {"text": ""}] + \
            [{"text": "lots of words " * 20}] * 3
    r = m3_trip_wire({}, first_n_pages=pages)
    assert r["promote"] is False


def test_m3_returns_none_with_fewer_than_5_pages():
    pages = [{"text": ""}, {"text": ""}]
    r = m3_trip_wire({}, first_n_pages=pages)
    assert r["promote"] is None


# ---- M4: empty-extraction terminal check -------------------------------

def test_m4_keeps_when_rendered_pages_have_content():
    pages = [{"text": "real content " * 10}] * 5
    r = m4_empty_extract(rendered_pages=pages)
    assert r["promote"] is True


def test_m4_gives_up_when_all_rendered_pages_empty():
    pages = [{"text": ""}] * 5
    r = m4_empty_extract(rendered_pages=pages)
    assert r["promote"] is False


def test_m4_returns_none_when_no_data():
    r = m4_empty_extract()
    assert r["promote"] is None


# ---- M5: ratio signal --------------------------------------------------

def test_m5_promotes_high_html_text_ratio():
    r = m5_ratio_signal({}, html_bytes=100_000, visible_text_bytes=500)
    assert r["promote"] is True


def test_m5_skips_low_ratio():
    r = m5_ratio_signal({}, html_bytes=10_000, visible_text_bytes=2_000)
    assert r["promote"] is False


def test_m5_returns_none_when_bytes_unknown():
    r = m5_ratio_signal({}, html_bytes=0, visible_text_bytes=0)
    assert r["promote"] is None


# ---- M6: cascade composition -------------------------------------------

def test_m6_user_authority_overrides_all():
    """user-set render_js wins over every other signal."""
    scan = {"is_spa": True, "url_class": "apiref", "seed_word_count": 0}
    r = m6_cascade(scan, user_render_js=False)
    assert r["promote"] is False
    assert r["rule"] == "M6/user"


def test_m6_m1_fires_first():
    scan = {"is_spa": True, "url_class": "apiref", "seed_word_count": 500}
    r = m6_cascade(scan)
    assert r["promote"] is True
    assert r["rule"] == "M6/M1"


def test_m6_falls_through_to_m2():
    scan = {"is_spa": False, "url_class": "apiref", "seed_word_count": 50}
    r = m6_cascade(scan)
    assert r["promote"] is True
    assert r["rule"] == "M6/M2"


def test_m6_falls_through_to_m5_when_ratio_signal_available():
    scan = {"is_spa": False, "url_class": "wiki", "seed_word_count": 500}
    r = m6_cascade(scan, html_bytes=100_000, visible_text_bytes=500)
    assert r["promote"] is True
    assert r["rule"] == "M6/M5"


def test_m6_uses_trip_wire_when_pages_provided():
    scan = {"is_spa": False, "url_class": "wiki", "seed_word_count": 500}
    pages = [{"text": ""}] * 5
    r = m6_cascade(scan, first_n_pages=pages)
    assert r["promote"] is True
    assert r["rule"] == "M6/M3"


def test_m6_default_no_promote():
    """Nothing fires => default is not to promote."""
    scan = {"is_spa": False, "url_class": "wiki", "seed_word_count": 500}
    r = m6_cascade(scan)
    assert r["promote"] is False
    assert r["rule"] == "M6/default"


def test_m6_short_circuits_on_first_match():
    """If M1 fires, M2 should not be evaluated -- the rule attribution should be M6/M1."""
    scan = {"is_spa": True, "url_class": "apiref", "seed_word_count": 50}
    r = m6_cascade(scan)
    assert r["rule"] == "M6/M1"  # not M6/M2 even though M2 would also fire


def test_m6_zero_cost_on_pure_scan_signals():
    """Scan-only cascade (no trip-wire, no user input) should report zero seconds."""
    scan = {"is_spa": True, "url_class": "apiref"}
    r = m6_cascade(scan)
    assert r["cost_seconds"] == 0.0

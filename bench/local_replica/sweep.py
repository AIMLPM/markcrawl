"""DS-6: Autoresearch sweep — score each detection method on labeled_sites.json.

For each method (M1..M5 + M6 cascade):
  - run prediction over every labeled site
  - compare to ground-truth label (`needs_render_js` vs `static_ok`)
  - compute precision / recall / balanced accuracy / FP rate / FN rate
  - tally cost_seconds per positive

Outputs:
  bench/local_replica/sweep_results.json    -- raw per-site predictions + per-method metrics
  bench/local_replica/SWEEP_REPORT.md       -- human-readable winner + per-method confusion

Usage:
    .venv/bin/python bench/local_replica/sweep.py \\
        --labeled bench/local_replica/labeled_sites.json \\
        --output bench/local_replica/sweep_results.json
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Dict, List, Optional

REPLICA = Path(__file__).resolve().parent
sys.path.insert(0, str(REPLICA))
from methods import METHODS, m6_cascade  # noqa: E402


def truth_label(rec: Dict) -> Optional[bool]:
    """Convert ground-truth label to bool. Indeterminate -> None (excluded)."""
    if rec.get("label") == "needs_render_js":
        return True
    if rec.get("label") == "static_ok":
        return False
    return None


def predict_for_method(method_name: str, rec: Dict) -> Dict:
    """Run a method on a site record and return its decision."""
    fn = METHODS[method_name]
    scan = rec.get("scan", {})
    if method_name == "M3-trip-wire":
        # Need first 5 pages of static crawl. We don't store per-page text in
        # labeled_sites.json (would be huge), so re-load from runs dir.
        return _trip_wire_via_disk(rec)
    if method_name == "M5-ratio":
        # No html_bytes captured currently — return None (deferred).
        return fn(scan)
    if method_name == "M6-cascade":
        # Cascade: include trip-wire pages if available
        first5 = _load_first_pages(rec, n=5)
        return m6_cascade(scan, first_n_pages=first5)
    return fn(scan)


def _load_first_pages(rec: Dict, n: int = 5) -> Optional[List[Dict]]:
    """Read the first N pages from the static crawl jsonl on disk."""
    slug = rec.get("slug")
    if not slug:
        return None
    p = REPLICA / "runs" / "ds4-static" / slug / "pages.jsonl"
    if not p.is_file():
        return None
    pages = []
    with p.open() as f:
        for i, line in enumerate(f):
            if i >= n:
                break
            try:
                pages.append(json.loads(line))
            except Exception:
                pass
    return pages or None


def _trip_wire_via_disk(rec: Dict) -> Dict:
    pages = _load_first_pages(rec, n=5)
    from methods import m3_trip_wire
    return m3_trip_wire(rec.get("scan", {}), first_n_pages=pages)


def confusion(predictions: List[bool], truth: List[bool]) -> Dict:
    tp = fp = tn = fn = 0
    for pred, t in zip(predictions, truth):
        if pred is True and t is True:
            tp += 1
        elif pred is True and t is False:
            fp += 1
        elif pred is False and t is True:
            fn += 1
        elif pred is False and t is False:
            tn += 1
    return {"tp": tp, "fp": fp, "tn": tn, "fn": fn,
            "precision": tp / (tp + fp) if (tp + fp) else 0.0,
            "recall":    tp / (tp + fn) if (tp + fn) else 0.0,
            "fp_rate":   fp / (fp + tn) if (fp + tn) else 0.0,
            "fn_rate":   fn / (tp + fn) if (tp + fn) else 0.0,
            "balanced_accuracy": 0.5 * (
                (tp / (tp + fn) if (tp + fn) else 0.0) +
                (tn / (fp + tn) if (fp + tn) else 0.0)),
            "n": tp + fp + tn + fn}


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--labeled", required=True)
    p.add_argument("--output", required=True)
    args = p.parse_args()

    data = json.loads(Path(args.labeled).read_text())
    sites = data["sites"]
    print(f"Loaded {len(sites)} sites from {args.labeled}")
    print(f"Label distribution: {data.get('label_distribution', {})}\n")

    # Filter to sites with definite labels
    labeled = [s for s in sites if truth_label(s) is not None]
    print(f"Scoring on {len(labeled)} sites (excluding indeterminate)\n")

    method_names = list(METHODS.keys())
    per_method: Dict[str, Dict] = {}
    per_site_predictions: Dict[str, Dict] = {}

    for method in method_names:
        preds: List[Optional[bool]] = []
        truths: List[bool] = []
        cost_total = 0.0
        for rec in labeled:
            t = truth_label(rec)
            res = predict_for_method(method, rec)
            promote = res.get("promote")
            preds.append(promote)
            truths.append(t)
            cost_total += res.get("cost_seconds", 0.0) or 0.0
            per_site_predictions.setdefault(rec["slug"], {})[method] = {
                "promote": promote, "rule": res.get("rule"),
                "signal": res.get("signal"), "truth": t,
            }

        # Filter sites where method returned None (deferred). Only score definite predictions.
        defined = [(p, t) for p, t in zip(preds, truths) if p is not None]
        if not defined:
            per_method[method] = {"error": "no definite predictions",
                                  "n_undefined": len(preds)}
            continue
        defined_preds, defined_truths = zip(*defined)
        cm = confusion(list(defined_preds), list(defined_truths))
        cm["n_undefined"] = sum(1 for p in preds if p is None)
        cm["mean_cost_seconds_per_site"] = cost_total / len(labeled)
        per_method[method] = cm

    # Identify winner: highest balanced_accuracy with FP rate <= 10%, breaking ties by recall
    def score(cm: Dict) -> tuple:
        if "balanced_accuracy" not in cm:
            return (-1, 0)
        if cm["fp_rate"] > 0.10:
            return (-0.5, cm["balanced_accuracy"])  # penalized but ranked
        return (cm["balanced_accuracy"], cm["recall"])

    ranked = sorted(per_method.items(), key=lambda kv: score(kv[1]), reverse=True)

    out = {
        "n_labeled": len(labeled),
        "label_distribution": data.get("label_distribution"),
        "per_method": per_method,
        "ranking": [name for name, _ in ranked],
        "per_site_predictions": per_site_predictions,
    }
    Path(args.output).write_text(json.dumps(out, indent=2))

    # Print summary
    print(f"{'method':18s}  {'bal_acc':>8s}  {'precision':>9s}  {'recall':>7s}  "
          f"{'fp_rate':>8s}  {'cost(s)':>7s}  notes")
    print("-" * 90)
    for name in [m for m, _ in ranked]:
        cm = per_method[name]
        if "error" in cm:
            print(f"  {name:18s}  -- {cm['error']} (undef={cm['n_undefined']})")
            continue
        notes = ""
        if cm["fp_rate"] > 0.10:
            notes = "❌ FP>10%"
        elif cm["balanced_accuracy"] >= 0.85:
            notes = "✅ meets SC-4"
        print(f"  {name:18s}  {cm['balanced_accuracy']:>8.3f}  {cm['precision']:>9.3f}  "
              f"{cm['recall']:>7.3f}  {cm['fp_rate']:>8.3f}  "
              f"{cm['mean_cost_seconds_per_site']:>7.2f}  {notes}")

    print()
    print(f"Saved -> {args.output}")
    winner = ranked[0][0] if ranked else "(none)"
    print(f"Winner: {winner}")


if __name__ == "__main__":
    main()

"""Aggregate 3-trial runs into median/min/max summaries and compare.

Reads summary.json + per-site report.json from N labelled trials per
build, computes per-metric trial statistics, and emits a side-by-side
comparison vs another build's trial set.

Usage:
    python multitrial_compare.py \\
        --baseline-trials v098-baseline-trial1,v098-baseline-trial2,v098-baseline-trial3 \\
        --baseline-base /tmp/markcrawl-v098-baseline/bench/local_replica/runs \\
        --candidate-trials v099-rc1-trial1,v099-rc1-trial2,v099-rc1-trial3 \\
        --candidate-base bench/local_replica/runs \\
        --out v099_release_report_multitrial.md

The "median" stat is reported as the headline; min/max bracket the
run-to-run noise floor. A delta is meaningful only if the candidate
median is outside the baseline (min, max) range.
"""
from __future__ import annotations

import argparse
import json
import statistics
from pathlib import Path
from typing import List


def load_trials(labels: list[str], base: Path) -> list[dict]:
    out = []
    for label in labels:
        s = base / label / "summary.json"
        if not s.is_file():
            print(f"WARN: missing summary.json for {label} at {s}")
            continue
        out.append(json.loads(s.read_text()))
    return out


def per_site_trials(labels: list[str], base: Path) -> dict[str, list[dict]]:
    """Return {site_name: [trial_report_dict, ...]}."""
    out: dict[str, list[dict]] = {}
    for label in labels:
        run_dir = base / label
        if not run_dir.is_dir():
            continue
        for site_dir in run_dir.iterdir():
            rpt = site_dir / "report.json"
            if not rpt.is_file():
                continue
            d = json.loads(rpt.read_text())
            name = d.get("name", site_dir.name)
            out.setdefault(name, []).append(d)
    return out


def stat3(vals: list[float]) -> tuple[float, float, float]:
    if not vals:
        return (0.0, 0.0, 0.0)
    return (min(vals), statistics.median(vals), max(vals))


def fmt_triple(t: tuple[float, float, float], prec: int = 3) -> str:
    lo, med, hi = t
    return f"{med:.{prec}f}  ({lo:.{prec}f}–{hi:.{prec}f})"


def overlap(a: tuple[float, float, float], b: tuple[float, float, float]) -> bool:
    """Do trial ranges overlap? If yes, delta is within noise."""
    a_lo, _, a_hi = a
    b_lo, _, b_hi = b
    return not (a_hi < b_lo or b_hi < a_lo)


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--baseline-trials", required=True, help="Comma-separated baseline labels")
    p.add_argument("--baseline-base", required=True, help="Path to runs/ for baseline")
    p.add_argument("--candidate-trials", required=True, help="Comma-separated candidate labels")
    p.add_argument("--candidate-base", required=True, help="Path to runs/ for candidate")
    p.add_argument("--out", help="Markdown output path")
    args = p.parse_args()

    base_labels = [x.strip() for x in args.baseline_trials.split(",") if x.strip()]
    cand_labels = [x.strip() for x in args.candidate_trials.split(",") if x.strip()]

    base_summaries = load_trials(base_labels, Path(args.baseline_base))
    cand_summaries = load_trials(cand_labels, Path(args.candidate_base))
    base_per_site = per_site_trials(base_labels, Path(args.baseline_base))
    cand_per_site = per_site_trials(cand_labels, Path(args.candidate_base))

    out_lines: list[str] = []

    def emit(s: str = "") -> None:
        out_lines.append(s)
        print(s)

    emit(f"# Multi-trial comparison")
    emit()
    emit(f"- Baseline: `{args.baseline_trials}` ({len(base_summaries)} trials)")
    emit(f"- Candidate: `{args.candidate_trials}` ({len(cand_summaries)} trials)")
    emit()
    emit("Stats reported as `median (min–max)`. **A delta is significant** only when the candidate median lies outside the baseline (min, max) range, i.e. the trials don't overlap.")
    emit()

    # ----- Aggregate -----
    emit("## Aggregate")
    emit()
    emit("| metric | baseline | candidate | delta (medians) | trials overlap? |")
    emit("|---|---|---|---|---|")
    for key, label, prec in [
        ("pages_per_sec_crawl_only", "speed (p/s, crawl-only)", 3),
        ("pages_per_sec_ex_npr", "speed (p/s, ex-NPR)", 3),
        ("pages_per_sec_end_to_end", "speed (p/s, end-to-end)", 3),
        ("mrr_mean", "MRR mean", 4),
        ("mrr_median", "MRR median (per-run)", 4),
        ("n_pages_total", "pages crawled", 0),
        ("wallclock_total_sec", "wallclock total (s)", 1),
    ]:
        bvals = [s.get(key, 0) for s in base_summaries]
        cvals = [s.get(key, 0) for s in cand_summaries]
        bt = stat3([float(x) for x in bvals])
        ct = stat3([float(x) for x in cvals])
        d = ct[1] - bt[1]
        ov = overlap(bt, ct)
        sig = "OVERLAP — within noise" if ov else "**SIGNIFICANT**"
        emit(f"| {label} | {fmt_triple(bt, prec)} | {fmt_triple(ct, prec)} | {d:+.{prec}f} | {sig} |")

    # ----- Full-report dimensions -----
    if (base_summaries and "full_report" in base_summaries[0]
        and cand_summaries and "full_report" in cand_summaries[0]):
        emit()
        emit("## 4 leadership dimensions (SC-6)")
        emit()
        emit("| dimension | baseline | candidate | delta (medians) | trials overlap? |")
        emit("|---|---|---|---|---|")
        for key, label, prec in [
            ("content_signal_pct", "content_signal_pct", 2),
            ("cost_at_scale_50M_dollars", "cost_at_scale_50M ($)", 2),
            ("pipeline_timing_1k_pages_sec", "pipeline_timing_1k (s)", 2),
        ]:
            bvals = [s["full_report"].get(key, 0) for s in base_summaries]
            cvals = [s["full_report"].get(key, 0) for s in cand_summaries]
            bt = stat3([float(x) for x in bvals])
            ct = stat3([float(x) for x in cvals])
            d = ct[1] - bt[1]
            ov = overlap(bt, ct)
            sig = "OVERLAP" if ov else "**SIGNIFICANT**"
            emit(f"| {label} | {fmt_triple(bt, prec)} | {fmt_triple(ct, prec)} | {d:+.{prec}f} | {sig} |")

    # ----- Per-site MRR -----
    emit()
    emit("## Per-site MRR (median across trials)")
    emit()
    emit("| site | baseline | candidate | delta | overlap? |")
    emit("|---|---|---|---|---|")
    all_sites = sorted(set(base_per_site) | set(cand_per_site))
    sig_count = 0
    sc3_violations = []
    for s in all_sites:
        bvals = [r.get("mrr", 0.0) for r in base_per_site.get(s, [])]
        cvals = [r.get("mrr", 0.0) for r in cand_per_site.get(s, [])]
        bt = stat3(bvals)
        ct = stat3(cvals)
        d = ct[1] - bt[1]
        ov = overlap(bt, ct)
        sig = "" if ov else " **SIGNIF**"
        if not ov and d < -0.10:
            sc3_violations.append((s, bt, ct, d))
            sig += " — ❌ SC-3 (real)"
        elif not ov and d < 0:
            sig += " — minor regress"
        elif not ov and d > 0:
            sig += " — improved"
            sig_count += 1
        emit(f"| {s} | {fmt_triple(bt, 3)} | {fmt_triple(ct, 3)} | {d:+.3f} | {sig} |")

    # ----- Per-site speed -----
    emit()
    emit("## Per-site speed (p/s, median across trials)")
    emit()
    emit("| site | baseline | candidate | delta |")
    emit("|---|---|---|---|")
    for s in all_sites:
        bvals = []
        for r in base_per_site.get(s, []):
            w = r.get("wallclock", 0)
            p = r.get("pages", 0)
            if w > 0:
                bvals.append(p / w)
        cvals = []
        for r in cand_per_site.get(s, []):
            w = r.get("wallclock", 0)
            p = r.get("pages", 0)
            if w > 0:
                cvals.append(p / w)
        bt = stat3(bvals)
        ct = stat3(cvals)
        d = ct[1] - bt[1]
        emit(f"| {s} | {fmt_triple(bt, 2)} | {fmt_triple(ct, 2)} | {d:+.2f} |")

    # ----- Verdict -----
    emit()
    emit("## Verdict")
    emit()
    if sc3_violations:
        emit(f"### ❌ {len(sc3_violations)} real SC-3 violations (non-overlapping trials, regression > 0.10):")
        for s, bt, ct, d in sc3_violations:
            emit(f"  - **{s}**: baseline {fmt_triple(bt, 3)}, candidate {fmt_triple(ct, 3)}, delta {d:+.3f}")
    else:
        emit("### ✅ No real SC-3 violations (no per-site MRR regression > 0.10 with non-overlapping trials)")

    if args.out:
        Path(args.out).write_text("\n".join(out_lines) + "\n")
        print(f"\nWritten to {args.out}")


if __name__ == "__main__":
    main()

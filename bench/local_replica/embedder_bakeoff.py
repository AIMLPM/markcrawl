"""DS-B1 — embedder bake-off orchestrator.

Runs the 11-site canonical pool five times against five embedders,
reusing the cached pages.jsonl from runs/v099-rc1-trial1 so only the
embed-and-score step varies. Aggregates MRR + cost_at_scale + per-cat
into bench/local_replica/embedder_bakeoff.json.

Usage:
    .venv/bin/python bench/local_replica/embedder_bakeoff.py
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path

REPLICA = Path(__file__).resolve().parent
ROOT = Path(__file__).resolve().parents[2]
RUNS = REPLICA / "runs"
SRC_RUN = RUNS / "v099-rc1-trial1"

EMBEDDERS = [
    # (slug, full_spec, kind, notes)
    ("3small", "text-embedding-3-small", "openai", "current default"),
    ("3large", "text-embedding-3-large", "openai", "OpenAI premium"),
    ("bge-large", "BAAI/bge-large-en-v1.5", "local", "BGE family"),
    ("mxbai-large", "mixedbread-ai/mxbai-embed-large-v1", "local", "Mixedbread"),
    ("nomic-text", "nomic-ai/nomic-embed-text-v1.5", "local", "Nomic w/ task prefix"),
]

SITES = [
    "huggingface-transformers", "ikea", "kubernetes-docs", "mdn-css",
    "newegg", "npr-news", "postgres-docs", "react-dev", "rust-book",
    "smittenkitchen", "stripe-docs",
]


def setup_symlinks(label: str) -> None:
    """Mirror SRC_RUN/<site>/pages.jsonl into RUNS/<label>/<site>/."""
    for site in SITES:
        d = RUNS / label / site
        d.mkdir(parents=True, exist_ok=True)
        link = d / "pages.jsonl"
        target = SRC_RUN / site / "pages.jsonl"
        if not target.is_file():
            print(f"[warn] missing source pages.jsonl for {site}", file=sys.stderr)
            continue
        if link.is_symlink() or link.exists():
            link.unlink()
        link.symlink_to(target)


def run_one(slug: str, spec: str) -> dict:
    label = f"v010-emb-{slug}"
    print(f"\n=== {slug} ({spec}) → label={label} ===")
    setup_symlinks(label)

    cmd = [
        ".venv/bin/python", "-u", str(REPLICA / "run.py"),
        "--label", label,
        "--reuse-crawl",
        "--embedder", spec,
        "--full-report",
    ]
    # Skip HF Hub metadata calls for cached models — they intermittently
    # hang behind CloudFront edge nodes and gate the bake-off behind
    # network latency. Pre-downloaded models work entirely offline.
    env = {**os.environ, "HF_HUB_OFFLINE": "1", "TRANSFORMERS_OFFLINE": "1"}
    t0 = time.perf_counter()
    proc = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, env=env)
    elapsed = time.perf_counter() - t0
    if proc.returncode != 0:
        print(f"[error] {slug} run failed (exit {proc.returncode})")
        print(proc.stdout[-2000:])
        print("STDERR:", proc.stderr[-2000:])
        return {"error": f"exit {proc.returncode}", "elapsed_sec": round(elapsed, 1)}

    summary_path = RUNS / label / "summary.json"
    summary = json.loads(summary_path.read_text())
    cost = summary.get("full_report", {}).get("cost_at_scale_50M_dollars")
    out = {
        "spec": spec,
        "label": label,
        "elapsed_sec": round(elapsed, 1),
        "mrr_mean": summary["mrr_mean"],
        "mrr_median": summary["mrr_median"],
        "by_category": summary["by_category"],
        "n_chunks_total": sum(
            json.loads((RUNS / label / s / "report.json").read_text()).get("n_chunks", 0)
            for s in SITES
            if (RUNS / label / s / "report.json").is_file()
        ),
        "cost_at_scale_50M_dollars": cost,
    }
    print(f"  → MRR mean {summary['mrr_mean']}  median {summary['mrr_median']}  "
          f"cost ${cost}  in {elapsed:.0f}s")
    return out


def main() -> None:
    if not SRC_RUN.is_dir():
        sys.exit(f"missing source run-dir: {SRC_RUN}")

    results: dict[str, dict] = {}
    for slug, spec, kind, notes in EMBEDDERS:
        results[slug] = {**run_one(slug, spec), "kind": kind, "notes": notes}

    out_path = REPLICA / "embedder_bakeoff.json"
    out_path.write_text(json.dumps(results, indent=2))
    print(f"\n=== Bake-off complete: {out_path} ===\n")

    # Quick comparison print.
    print(f"{'embedder':<14} {'mrr_mean':>9} {'cost($)':>9} {'time(s)':>8}")
    for slug, info in results.items():
        cost = info.get("cost_at_scale_50M_dollars", "?")
        elapsed = info.get("elapsed_sec", 0)
        mrr = info.get("mrr_mean", 0.0)
        print(f"{slug:<14} {mrr:>9.4f} {cost:>9} {elapsed:>8.0f}")


if __name__ == "__main__":
    main()

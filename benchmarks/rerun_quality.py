#!/usr/bin/env python3
"""Re-run quality scoring against an existing benchmark run directory.

Reads the pages.jsonl files already on disk (no crawling), applies the
quality scorer, and overwrites QUALITY_COMPARISON.md.

For colly+md: if a _url_map.json exists in the run directory it uses exact
URLs; otherwise it attempts to patch URLs from _urls.txt before scoring.

Usage:
    python benchmarks/rerun_quality.py                          # latest run
    python benchmarks/rerun_quality.py --run run_20260405_221158
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

BENCH_DIR = Path(__file__).parent
REPO_ROOT = BENCH_DIR.parent
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(BENCH_DIR))

from quality_scorer import (
    PageQuality,
    generate_quality_report,
    score_consensus,
    score_density,
    score_signals,
)

TOOLS = ["markcrawl", "crawl4ai", "scrapy+md", "crawlee", "colly+md", "playwright", "firecrawl"]
SITES = ["quotes-toscrape", "books-toscrape", "fastapi-docs", "python-docs"]


def _patch_colly_urls(run_dir: Path, site: str) -> dict[str, str]:
    """Return safe_name → original_url map for colly, built from _url_map.json
    or _urls.txt if the map wasn't written by an older run."""
    colly_site_dir = run_dir / "colly+md" / site

    # Prefer the pre-built map (new runs)
    map_path = colly_site_dir / "_url_map.json"
    if map_path.exists():
        with open(map_path) as f:
            return json.load(f)

    # Fallback: reconstruct from _urls.txt written alongside the run
    urls_path = colly_site_dir / "_urls.txt"
    if urls_path.exists():
        url_map: dict[str, str] = {}
        for line in urls_path.read_text().splitlines():
            u = line.strip()
            if u:
                safe = u.replace("://", "_").replace("/", "_")[:80]
                url_map[safe] = u
        return url_map

    return {}


def _fix_colly_jsonl(run_dir: Path, site: str) -> None:
    """Rewrite colly+md pages.jsonl with correct URLs in-place."""
    jsonl_path = run_dir / "colly+md" / site / "pages.jsonl"
    if not jsonl_path.exists():
        return

    url_map = _patch_colly_urls(run_dir, site)
    if not url_map:
        return

    lines = jsonl_path.read_text(encoding="utf-8").splitlines()
    fixed_lines = []
    changed = 0
    for line in lines:
        line = line.strip()
        if not line:
            continue
        page = json.loads(line)
        current_url = page.get("url", "")
        # Derive the safe_name from the current (possibly reconstructed) URL
        # by reversing the reconstruction: replace / → _ after the scheme
        # Try each key in url_map whose value best matches
        fixed_url = current_url
        for safe, original in url_map.items():
            # Match by safe_name pattern applied to original URL
            candidate_safe = original.replace("://", "_").replace("/", "_")[:80]
            if candidate_safe == safe:
                # Check if current reconstructed URL loosely matches original
                if current_url.replace("/", "_").rstrip("_") in original.replace("/", "_"):
                    fixed_url = original
                    break
                # Direct safe → original match by stem
                current_safe = current_url.replace("://", "_").replace("/", "_")[:80]
                if current_safe == safe:
                    fixed_url = original
                    break
        if fixed_url != current_url:
            page["url"] = fixed_url
            changed += 1
        fixed_lines.append(json.dumps(page, ensure_ascii=False))

    if changed:
        jsonl_path.write_text("\n".join(fixed_lines) + "\n", encoding="utf-8")
        print(f"  colly+md / {site}: fixed {changed} URLs in pages.jsonl")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", default=None, help="Run directory name under benchmarks/runs/")
    parser.add_argument(
        "--output", default=str(BENCH_DIR / "QUALITY_COMPARISON.md"),
        help="Output path for quality report",
    )
    args = parser.parse_args()

    runs_dir = BENCH_DIR / "runs"
    if args.run:
        run_dir = runs_dir / args.run
    else:
        # Use latest run
        run_dirs = sorted(runs_dir.iterdir()) if runs_dir.exists() else []
        if not run_dirs:
            sys.exit("No run directories found under benchmarks/runs/")
        run_dir = run_dirs[-1]

    print(f"Scoring quality from: {run_dir.name}")

    # Fix colly URLs in existing jsonl files before scoring
    for site in SITES:
        _fix_colly_jsonl(run_dir, site)

    quality_results: dict[str, dict[str, list]] = {}

    for site in SITES:
        quality_results[site] = {}
        tool_outputs_by_url: dict[str, dict[str, str]] = {}

        for tool in TOOLS:
            jsonl_path = run_dir / tool / site / "pages.jsonl"
            if not jsonl_path.exists():
                continue
            with open(jsonl_path, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    page = json.loads(line)
                    url = page.get("url", "").rstrip("/")
                    text = page.get("text", "")
                    if url and text:
                        tool_outputs_by_url.setdefault(url, {})[tool] = text

        for tool in TOOLS:
            pages = []
            for url, outputs in tool_outputs_by_url.items():
                if tool not in outputs:
                    continue
                markdown = outputs[tool]
                signal = score_signals(markdown)
                density = score_density(markdown)
                consensus = score_consensus(markdown, outputs, tool)
                pages.append(PageQuality(url=url, tool=tool, signal=signal,
                                         density=density, consensus=consensus))
            quality_results[site][tool] = pages

        total_pages = sum(len(p) for p in quality_results[site].values())
        available = [t for t in TOOLS if quality_results[site].get(t)]
        print(f"  {site}: scored {total_pages} pages across {len(available)} tools")

    report = generate_quality_report(quality_results, TOOLS)
    Path(args.output).write_text(report, encoding="utf-8")
    print(f"\nQuality report written to: {args.output}")


if __name__ == "__main__":
    main()

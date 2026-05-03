"""DS-2: Profile speed regression at the feature level.

Runs the same site (or small site set) under different auto_* feature
toggles to isolate which features cost p/s. Output is a table comparing
each configuration's pages/sec, MRR, and total wallclock.

Configurations to test (each is a single-axis change vs the current
default):
  baseline-defaults   -- current crawl() defaults (auto_path_scope=True,
                         auto_path_priority=True, use_sitemap=True,
                         auto_scan=False)
  no-auto-scope       -- auto_path_scope=False
  no-auto-priority    -- auto_path_priority=False
  no-sitemap          -- use_sitemap=False
  bare                -- all auto_* off (auto_path_scope=False,
                         auto_path_priority=False, use_sitemap=False)
  with-auto-scan      -- auto_scan=True (current v0.9.8 dispatch path)

The site under test is npr-news by default — it's the catastrophic case
revealed in DS-1 (0.33 p/s, 449s for 150 pages). Profiling on this site
isolates whichever feature combination is producing the 6× slowdown.

Usage:
    .venv/bin/python bench/local_replica/profile_features.py --sites npr-news,mdn-css,rust-book
    .venv/bin/python bench/local_replica/profile_features.py --sites npr-news --max-pages 50
"""
from __future__ import annotations

import argparse
import json
import logging
import shutil
import sys
import time
from pathlib import Path
from typing import Dict, List

import yaml

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from markcrawl.core import crawl  # noqa: E402

REPLICA = Path(__file__).resolve().parent
RUNS = REPLICA / "runs"
CANONICAL = REPLICA / "sites_v1.2_canonical.yaml"

logging.basicConfig(level=logging.WARNING, format="%(levelname)s: %(message)s")


CONFIGS = [
    ("baseline-defaults", dict(auto_path_scope=True, auto_path_priority=True,
                               use_sitemap=True, auto_scan=False)),
    ("no-auto-scope",     dict(auto_path_scope=False, auto_path_priority=True,
                               use_sitemap=True, auto_scan=False)),
    ("no-auto-priority",  dict(auto_path_scope=True, auto_path_priority=False,
                               use_sitemap=True, auto_scan=False)),
    ("no-sitemap",        dict(auto_path_scope=True, auto_path_priority=True,
                               use_sitemap=False, auto_scan=False)),
    ("bare",              dict(auto_path_scope=False, auto_path_priority=False,
                               use_sitemap=False, auto_scan=False)),
    ("with-auto-scan",    dict(auto_path_scope=True, auto_path_priority=True,
                               use_sitemap=True, auto_scan=True)),
]


def load_canonical() -> List[dict]:
    raw = yaml.safe_load(CANONICAL.open())["sites"]
    return [{"name": s["name"], "url": s["url"], "category": s.get("category", "?"),
             "max_pages": int(s.get("max_pages", 200)),
             "render_js": bool(s.get("render_js", False))}
            for s in raw if s.get("has_queries", True)]


def crawl_one(site: dict, out_dir: Path, kw: Dict, max_pages: int) -> Dict:
    if out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    t0 = time.perf_counter()
    try:
        result = crawl(
            base_url=site["url"], out_dir=str(out_dir), fmt="markdown",
            max_pages=max_pages, delay=0.0, timeout=20,
            show_progress=False, min_words=5,
            render_js=site["render_js"], **kw,
        )
        wall = time.perf_counter() - t0
        return {"pages": result.pages_saved, "wall": round(wall, 2),
                "pps": round(result.pages_saved / wall, 3) if wall > 0 else 0.0,
                "error": None}
    except Exception as exc:
        return {"pages": 0, "wall": round(time.perf_counter() - t0, 2),
                "pps": 0.0, "error": repr(exc)[:200]}


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--sites", required=True, help="Comma-separated names from canonical pool")
    p.add_argument("--max-pages", type=int, default=None,
                   help="Override site max_pages (useful for fast iteration)")
    p.add_argument("--output", default=str(REPLICA / "profile_features.json"))
    p.add_argument("--configs", help="Comma-separated subset of config names")
    args = p.parse_args()

    site_pool = {s["name"]: s for s in load_canonical()}
    site_names = args.sites.split(",")
    targets = [site_pool[n] for n in site_names if n in site_pool]
    if not targets:
        raise SystemExit(f"none of {site_names} in canonical pool")

    if args.configs:
        wanted = set(args.configs.split(","))
        configs = [(n, kw) for n, kw in CONFIGS if n in wanted]
    else:
        configs = CONFIGS

    print(f"Profiling {len(targets)} sites × {len(configs)} configs "
          f"= {len(targets)*len(configs)} crawls", flush=True)

    results = []
    for site in targets:
        cap = args.max_pages or site["max_pages"]
        for cfg_name, kw in configs:
            out = RUNS / "profile" / cfg_name / site["name"]
            r = crawl_one(site, out, kw, cap)
            r["site"] = site["name"]
            r["category"] = site["category"]
            r["config"] = cfg_name
            r["max_pages"] = cap
            results.append(r)
            err = f" ERR={r['error']}" if r["error"] else ""
            print(f"  [{site['name']:15s}] {cfg_name:18s} "
                  f"pages={r['pages']:4d} wall={r['wall']:6.1f}s "
                  f"= {r['pps']:6.2f} p/s{err}", flush=True)

    # Save full + write summary table
    Path(args.output).write_text(json.dumps(results, indent=2))
    print(f"\nFull results -> {args.output}")
    print()

    # Per-site, per-config table
    for site in targets:
        print(f"=== {site['name']} (cat={site['category']}, max={args.max_pages or site['max_pages']}) ===")
        site_rows = [r for r in results if r["site"] == site["name"]]
        baseline = next((r for r in site_rows if r["config"] == "baseline-defaults"), None)
        for r in site_rows:
            delta = ""
            if baseline and r["config"] != "baseline-defaults" and r["pps"] > 0 and baseline["pps"] > 0:
                d = r["pps"] - baseline["pps"]
                delta = f"  Δ={d:+.2f} p/s"
            print(f"  {r['config']:18s}  {r['pps']:6.2f} p/s ({r['pages']} pages, {r['wall']}s){delta}")
        print()

    # Aggregate per-config
    print("=== Aggregate (mean p/s across sites) ===")
    cfg_means: Dict[str, List[float]] = {}
    for r in results:
        cfg_means.setdefault(r["config"], []).append(r["pps"])
    for cfg, ms in cfg_means.items():
        print(f"  {cfg:18s}  mean={sum(ms)/len(ms):.2f} p/s  per-site=[{', '.join(f'{m:.1f}' for m in ms)}]")


if __name__ == "__main__":
    main()

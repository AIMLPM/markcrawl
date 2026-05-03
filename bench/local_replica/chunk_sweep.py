"""Track D — autoresearch-style chunk-shape sweep.

Pattern adapted from karpathy/autoresearch (fixed metric, TSV log,
resumable on existing TSV, simplicity criterion baked into how we
report results).

What this does
--------------
1. Reads cached pages.jsonl from one or more replica run-dirs (no
   re-crawl).
2. For each chunking config in the sweep grid, re-chunks every page,
   embeds chunks, scores MRR per query, aggregates per site.
3. Appends one TSV row per (config, run-dir, site) plus one summary
   row per (config, run-dir) per the autoresearch format.
4. Skips configs whose summary row already exists in the TSV — so a
   reboot mid-sweep just resumes.

What this DOES NOT do
---------------------
- Re-crawl. Crawls are expensive (hours); the sweep operates on
  already-saved JSONL. The cache key is `(run_dir, site)`.
- Re-embed across configs. Each config gets fresh embeddings — chunk
  text changes with the config, so embeddings can't be shared.
- Cross-encoder rerank. That's Track A. Track D measures pure-chunk
  effects.

Usage
-----
::

    python bench/local_replica/chunk_sweep.py \\
        --runs bench/local_replica/runs/v099-rc1-trial3 \\
        --grid phase1_size \\
        --embedder st-mini \\
        --tsv bench/local_replica/chunk_sweep_results.tsv

Embedder choices
----------------
- ``st-mini``: sentence-transformers/all-MiniLM-L6-v2 (CPU, free, fast).
- ``st-bge``: BAAI/bge-large-en-v1.5 (CPU, free, slower, stronger).
- ``openai-3-small``: text-embedding-3-small (API, $).

Grid choices
------------
- ``phase1_size``: pure size sweep at overlap=0.
- ``phase2_overlap``: the size winner at varied overlap_pct.
- ``phase3_strategy``: the (size, overlap) winner with alternate flags.
- ``phase4_validate``: the top-3 configs across multiple cached runs.
- ``custom``: pass --configs PATH for a JSON list of explicit configs.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import logging
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from markcrawl.chunker import chunk_markdown  # noqa: E402

REPLICA = Path(__file__).resolve().parent
QUERIES = REPLICA / "queries"

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
log = logging.getLogger("chunk_sweep")


# ---------------------------------------------------------------------------
# Config dataclass
# ---------------------------------------------------------------------------

@dataclass
class ChunkConfig:
    """One point in the sweep grid."""
    max_words: int = 400
    min_words: int = 0
    section_overlap_words: int = 0
    overlap_words: int = 50  # legacy word-fallback overlap
    adaptive: bool = False
    auto_extract_title: bool = False
    prepend_first_paragraph: bool = False
    strip_markdown_links: bool = False
    label: str = "default"

    def cid(self) -> str:
        """Short stable id for the config (8 hex chars of hash)."""
        d = asdict(self)
        d.pop("label", None)
        s = json.dumps(d, sort_keys=True)
        return hashlib.sha1(s.encode()).hexdigest()[:8]

    def to_kwargs(self) -> Dict[str, Any]:
        return {
            "max_words": self.max_words,
            "min_words": self.min_words,
            "section_overlap_words": self.section_overlap_words,
            "overlap_words": self.overlap_words,
            "adaptive": self.adaptive,
            "auto_extract_title": self.auto_extract_title,
            "prepend_first_paragraph": self.prepend_first_paragraph,
            "strip_markdown_links": self.strip_markdown_links,
        }


# ---------------------------------------------------------------------------
# Sweep grids
# ---------------------------------------------------------------------------

def grid_phase1_size() -> List[ChunkConfig]:
    """Phase 1: size sweep at overlap=0, no extras."""
    out: List[ChunkConfig] = []
    # Baseline (matches v0.9.9 production): max=400, min=0, overlap=0
    out.append(ChunkConfig(max_words=400, min_words=0, label="baseline-v099"))
    # Pure size variation: target each (max, min) so chunks land in a band
    for max_w, min_w in [
        (200, 100),  # small
        (250, 150),
        (300, 200),  # crawlee/playwright/colly band
        (400, 250),
        (500, 350),
        (600, 400),  # bigger
    ]:
        out.append(ChunkConfig(
            max_words=max_w, min_words=min_w,
            label=f"size-max{max_w}-min{min_w}",
        ))
    return out


def grid_phase2_overlap(best_max: int, best_min: int) -> List[ChunkConfig]:
    """Phase 2: overlap sweep at the size winner from phase 1."""
    out: List[ChunkConfig] = []
    for ov in [0, 20, 40, 60, 80, 100, 150]:
        out.append(ChunkConfig(
            max_words=best_max, min_words=best_min,
            section_overlap_words=ov,
            label=f"ovl-max{best_max}-min{best_min}-ov{ov}",
        ))
    return out


def grid_phase3_strategy(best_max: int, best_min: int, best_ov: int) -> List[ChunkConfig]:
    """Phase 3: alternate strategies on top of (size, overlap) winner."""
    base = dict(max_words=best_max, min_words=best_min, section_overlap_words=best_ov)
    out: List[ChunkConfig] = [
        ChunkConfig(**base, label="strat-base"),
        ChunkConfig(**base, prepend_first_paragraph=True,
                    label="strat-prepend-1para"),
        ChunkConfig(**base, strip_markdown_links=True,
                    label="strat-strip-links"),
        ChunkConfig(**base, prepend_first_paragraph=True,
                    strip_markdown_links=True,
                    label="strat-prepend-strip"),
        ChunkConfig(**base, auto_extract_title=True,
                    label="strat-auto-title"),
        ChunkConfig(**base, adaptive=True,
                    label="strat-adaptive"),
    ]
    return out


GRID_BUILDERS = {
    "phase1_size": grid_phase1_size,
}


# ---------------------------------------------------------------------------
# Site / page loading
# ---------------------------------------------------------------------------

def load_pages(run_dir: Path, site: str) -> List[dict]:
    jsonl = run_dir / site / "pages.jsonl"
    if not jsonl.is_file():
        return []
    return [json.loads(line) for line in jsonl.open() if line.strip()]


def list_sites(run_dir: Path) -> List[str]:
    out = []
    for d in run_dir.iterdir():
        if d.is_dir() and (d / "pages.jsonl").is_file():
            out.append(d.name)
    return sorted(out)


def chunkify(pages: List[dict], cfg: ChunkConfig) -> List[Dict[str, str]]:
    """Apply config's chunk_markdown over all pages. Returns list of
    {url, text} chunk dicts."""
    out: List[Dict[str, str]] = []
    kwargs = cfg.to_kwargs()
    for p in pages:
        md = p.get("text") or p.get("markdown") or ""
        if not md:
            continue
        url = p.get("url", "")
        for ch in chunk_markdown(md, **kwargs):
            out.append({"url": url, "text": ch.text})
    return out


# ---------------------------------------------------------------------------
# Embedder backends
# ---------------------------------------------------------------------------

class _STMini:
    name = "st-mini"
    model_name = "sentence-transformers/all-MiniLM-L6-v2"
    _model = None

    def encode(self, texts: List[str]) -> List[List[float]]:
        from sentence_transformers import SentenceTransformer
        if _STMini._model is None:
            _STMini._model = SentenceTransformer(self.model_name)
        embs = _STMini._model.encode(
            texts, normalize_embeddings=True, show_progress_bar=False,
            convert_to_numpy=True, batch_size=64,
        )
        return embs.tolist()


class _STBge:
    name = "st-bge"
    model_name = "BAAI/bge-large-en-v1.5"
    _model = None

    def encode(self, texts: List[str]) -> List[List[float]]:
        from sentence_transformers import SentenceTransformer
        if _STBge._model is None:
            _STBge._model = SentenceTransformer(self.model_name)
        embs = _STBge._model.encode(
            texts, normalize_embeddings=True, show_progress_bar=False,
            convert_to_numpy=True, batch_size=32,
        )
        return embs.tolist()


class _OpenAI:
    name = "openai-3-small"
    model_name = "text-embedding-3-small"
    _client = None

    def __init__(self):
        if _OpenAI._client is None:
            import os
            api_key = os.environ.get("OPENAI_API_KEY")
            if not api_key:
                env_path = ROOT / ".env"
                if env_path.is_file():
                    for line in env_path.read_text().splitlines():
                        if line.startswith("OPENAI_API_KEY="):
                            api_key = line.split("=", 1)[1].strip().strip('"').strip("'")
                            break
            if not api_key:
                raise SystemExit("OPENAI_API_KEY missing")
            from openai import OpenAI
            _OpenAI._client = OpenAI(api_key=api_key)

    def encode(self, texts: List[str]) -> List[List[float]]:
        out: List[List[float]] = []
        for i in range(0, len(texts), 96):
            batch = texts[i:i + 96]
            resp = _OpenAI._client.embeddings.create(model=self.model_name, input=batch)
            out.extend([d.embedding for d in resp.data])
        return out


def get_embedder(name: str):
    if name == "st-mini":
        return _STMini()
    if name == "st-bge":
        return _STBge()
    if name == "openai-3-small":
        return _OpenAI()
    raise SystemExit(f"unknown embedder: {name}")


# ---------------------------------------------------------------------------
# MRR scoring
# ---------------------------------------------------------------------------

def cosine(a: List[float], b: List[float]) -> float:
    # Embeddings are pre-normalized for st-* and post-normalized via OpenAI
    # docs (their 3-small returns unit vectors). Dot product = cosine.
    return sum(x * y for x, y in zip(a, b))


def mrr_for_site(site: str, chunks: List[Dict[str, str]], chunk_embs: List[List[float]],
                 query_embs: Dict[str, List[float]], queries: List[dict],
                 K: int = 20) -> Dict[str, Any]:
    """Compute MRR + per-category breakdown for one site.

    Returns a dict with 'mrr_mean', 'rrs' (list per query), and
    'per_category' ({cat: mean_rr}).
    """
    if not chunks or not queries or not chunk_embs:
        return {"mrr_mean": 0.0, "rrs": [], "per_category": {}}
    rrs: List[float] = []
    cat_rrs: Dict[str, List[float]] = {}
    for q in queries:
        q_emb = query_embs.get(q["query"])
        if q_emb is None:
            continue
        scored = [
            (cosine(q_emb, ch_emb), ch.get("url", ""), idx)
            for idx, (ch, ch_emb) in enumerate(zip(chunks, chunk_embs))
        ]
        scored.sort(key=lambda t: t[0], reverse=True)
        rr = 0.0
        url_match = q.get("url_match") or q.get("expected_url_contains") or ""
        if not url_match:
            rrs.append(0.0)
            continue
        for rank, (_score, url, _idx) in enumerate(scored[:K], start=1):
            if url_match in url:
                rr = 1.0 / rank
                break
        rrs.append(rr)
        cat = q.get("category", "uncategorized")
        cat_rrs.setdefault(cat, []).append(rr)
    mrr_mean = sum(rrs) / len(rrs) if rrs else 0.0
    per_cat = {c: round(sum(v) / len(v), 4) for c, v in cat_rrs.items()}
    return {
        "mrr_mean": round(mrr_mean, 4),
        "rrs": rrs,
        "per_category": per_cat,
        "n_queries": len(rrs),
    }


def load_queries(site: str) -> List[dict]:
    f = QUERIES / f"{site}.json"
    if not f.is_file():
        return []
    return json.loads(f.read_text())


# ---------------------------------------------------------------------------
# TSV append + resume check
# ---------------------------------------------------------------------------

TSV_COLS = [
    "config_id", "label", "run_dir", "embedder",
    "max_words", "min_words", "section_overlap_words", "overlap_words",
    "adaptive", "auto_extract_title", "prepend_first_paragraph", "strip_markdown_links",
    "n_sites", "n_pages_total", "n_chunks_total", "avg_words_per_chunk",
    "mrr_mean", "mrr_median",
    "per_site_mrr_json",
    "elapsed_sec", "status", "description",
]


def ensure_tsv(tsv: Path) -> None:
    if not tsv.is_file():
        with tsv.open("w") as f:
            w = csv.writer(f, delimiter="\t")
            w.writerow(TSV_COLS)


def existing_keys(tsv: Path) -> set:
    """Return set of (config_id, run_dir, embedder) tuples already logged."""
    keys = set()
    if not tsv.is_file():
        return keys
    with tsv.open() as f:
        r = csv.DictReader(f, delimiter="\t")
        for row in r:
            if row.get("status") in ("completed", "skipped"):
                keys.add((row["config_id"], row["run_dir"], row["embedder"]))
    return keys


def append_row(tsv: Path, row: Dict[str, Any]) -> None:
    with tsv.open("a") as f:
        w = csv.writer(f, delimiter="\t")
        w.writerow([row.get(c, "") for c in TSV_COLS])


# ---------------------------------------------------------------------------
# Main sweep loop
# ---------------------------------------------------------------------------

def run_one(cfg: ChunkConfig, run_dir: Path, embedder, sites: List[str],
            tsv: Path) -> Dict[str, Any]:
    """Run one config across all sites, append a single summary row."""
    t0 = time.perf_counter()
    log.info("[%s] cfg=%s embedder=%s run=%s",
             cfg.cid(), cfg.label, embedder.name, run_dir.name)

    # Pre-embed all queries once across all sites (each query is independent
    # of chunking strategy, so embeddings are stable across configs).
    all_queries: Dict[str, dict] = {}  # site -> queries
    all_query_texts: List[str] = []
    for site in sites:
        qs = load_queries(site)
        all_queries[site] = qs
        all_query_texts.extend([q["query"] for q in qs])
    query_emb_map: Dict[str, List[float]] = {}
    if all_query_texts:
        unique_qs = list(dict.fromkeys(all_query_texts))
        log.info("    embedding %d unique queries", len(unique_qs))
        q_embs = embedder.encode(unique_qs)
        for q, e in zip(unique_qs, q_embs):
            query_emb_map[q] = e

    per_site_mrr: Dict[str, float] = {}
    per_site_meta: Dict[str, Dict[str, int]] = {}
    per_site_categories: Dict[str, Dict[str, float]] = {}
    n_pages_total = 0
    n_chunks_total = 0
    total_words = 0

    for site in sites:
        pages = load_pages(run_dir, site)
        if not pages:
            per_site_mrr[site] = 0.0
            per_site_meta[site] = {"pages": 0, "chunks": 0, "avg_words": 0}
            continue
        chunks = chunkify(pages, cfg)
        if not chunks:
            per_site_mrr[site] = 0.0
            per_site_meta[site] = {"pages": len(pages), "chunks": 0, "avg_words": 0}
            continue
        ch_texts = [c["text"] for c in chunks]
        log.info("    [%s] embedding %d chunks", site, len(ch_texts))
        ch_embs = embedder.encode(ch_texts)
        result = mrr_for_site(site, chunks, ch_embs, query_emb_map,
                              all_queries.get(site, []))
        per_site_mrr[site] = result["mrr_mean"]
        per_site_categories[site] = result["per_category"]
        words = sum(len(t.split()) for t in ch_texts)
        per_site_meta[site] = {
            "pages": len(pages),
            "chunks": len(chunks),
            "avg_words": round(words / len(chunks), 1) if chunks else 0,
            "n_queries": result["n_queries"],
        }
        n_pages_total += len(pages)
        n_chunks_total += len(chunks)
        total_words += words

    # Include sites that had chunks (excludes failed crawls)
    valid_mrrs = [v for s, v in per_site_mrr.items()
                  if per_site_meta.get(s, {}).get("chunks", 0) > 0]
    mrr_mean = round(sum(valid_mrrs) / len(valid_mrrs), 4) if valid_mrrs else 0.0
    sorted_m = sorted(valid_mrrs)
    mrr_med = round(sorted_m[len(sorted_m) // 2], 4) if sorted_m else 0.0

    # Cross-site per-category aggregation
    all_cat_rrs: Dict[str, List[float]] = {}
    for site, cats in per_site_categories.items():
        for cat, m in cats.items():
            all_cat_rrs.setdefault(cat, []).append(m)
    per_category_global = {c: round(sum(v) / len(v), 4)
                           for c, v in all_cat_rrs.items()}

    elapsed = round(time.perf_counter() - t0, 1)
    avg_words = round(total_words / n_chunks_total, 1) if n_chunks_total else 0
    row = {
        "config_id": cfg.cid(),
        "label": cfg.label,
        "run_dir": run_dir.name,
        "embedder": embedder.name,
        "max_words": cfg.max_words,
        "min_words": cfg.min_words,
        "section_overlap_words": cfg.section_overlap_words,
        "overlap_words": cfg.overlap_words,
        "adaptive": cfg.adaptive,
        "auto_extract_title": cfg.auto_extract_title,
        "prepend_first_paragraph": cfg.prepend_first_paragraph,
        "strip_markdown_links": cfg.strip_markdown_links,
        "n_sites": len(sites),
        "n_pages_total": n_pages_total,
        "n_chunks_total": n_chunks_total,
        "avg_words_per_chunk": avg_words,
        "mrr_mean": mrr_mean,
        "mrr_median": mrr_med,
        "per_site_mrr_json": json.dumps({
            "mrr": per_site_mrr,
            "meta": per_site_meta,
            "per_category": per_category_global,
            "per_site_per_category": per_site_categories,
        }, separators=(",", ":")),
        "elapsed_sec": elapsed,
        "status": "completed",
        "description": cfg.label,
    }
    append_row(tsv, row)
    log.info("[%s] DONE  MRR=%.4f (median %.4f)  chunks=%d avg=%d words  %.1fs",
             cfg.cid(), mrr_mean, mrr_med, n_chunks_total, avg_words, elapsed)
    return row


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--runs", required=True, nargs="+",
                   help="Path(s) to replica run directories whose pages.jsonl to use.")
    p.add_argument("--grid", required=True, choices=list(GRID_BUILDERS) + ["custom"],
                   help="Sweep grid name, or 'custom' with --configs.")
    p.add_argument("--configs", help="Path to JSON list of explicit ChunkConfig dicts (custom grid).")
    p.add_argument("--embedder", default="st-mini",
                   choices=["st-mini", "st-bge", "openai-3-small"])
    p.add_argument("--tsv", default="bench/local_replica/chunk_sweep_results.tsv")
    p.add_argument("--sites", help="Comma-separated subset; default all sites in run-dir.")
    args = p.parse_args()

    tsv = Path(args.tsv)
    ensure_tsv(tsv)
    skip_keys = existing_keys(tsv)
    log.info("resuming: %d completed (config_id, run_dir, embedder) keys in TSV",
             len(skip_keys))

    # Build configs
    if args.grid == "custom":
        if not args.configs:
            raise SystemExit("--configs required for --grid custom")
        cfg_dicts = json.loads(Path(args.configs).read_text())
        configs = [ChunkConfig(**d) for d in cfg_dicts]
    else:
        configs = GRID_BUILDERS[args.grid]()
    log.info("grid '%s' -> %d configs", args.grid, len(configs))

    embedder = get_embedder(args.embedder)
    log.info("embedder: %s (%s)", embedder.name, getattr(embedder, "model_name", "?"))

    # Loop
    for run_dir_str in args.runs:
        run_dir = Path(run_dir_str)
        if not run_dir.is_dir():
            log.warning("skipping missing run-dir: %s", run_dir)
            continue
        sites = list_sites(run_dir)
        if args.sites:
            wanted = set(args.sites.split(","))
            sites = [s for s in sites if s in wanted]
        log.info("run_dir=%s, sites=%d", run_dir.name, len(sites))
        for cfg in configs:
            key = (cfg.cid(), run_dir.name, embedder.name)
            if key in skip_keys:
                log.info("[%s] SKIP (already logged)", cfg.cid())
                continue
            try:
                run_one(cfg, run_dir, embedder, sites, tsv)
                # Re-read skip set so we don't double-run if multiple --runs
                skip_keys.add(key)
            except Exception as exc:
                log.exception("config %s failed: %s", cfg.cid(), exc)
                # Append a status=error row so we know
                append_row(tsv, {
                    "config_id": cfg.cid(), "label": cfg.label,
                    "run_dir": run_dir.name, "embedder": embedder.name,
                    "status": "error", "description": f"{exc!r}"[:200],
                })

    log.info("sweep complete")


if __name__ == "__main__":
    main()

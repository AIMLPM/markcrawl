# Recipe: RAG retrieval recipes by site category

> **Status:** preliminary, based on internal measurements across 10 sites
> spanning 6 categories. Numbers below are MRR (Mean Reciprocal Rank)
> on 8-query test sets per site, with 200-page crawls.

MarkCrawl produces clean Markdown — but how you *retrieve* from that
Markdown matters too.  We measured several retrieval-side knobs across
site categories and found that **no single retrieval recipe is optimal
for all sites**.  Per-category dispatch beats uniform settings by up
to **+0.06 MRR** on a strong embedder, and far more if you mix
embedders.

This recipe gives starting points by site category and shows how to
implement a category-dispatching retrieval layer over MarkCrawl
output.

## Recommended starting points

| Site category | Embedder | Hybrid α (vector vs BM25) | Rerank | Notes |
|---|---|---|---|---|
| **docs — heavy API names** (e.g. kubernetes) | `text-embedding-3-small` | 0.5–0.7 | off | Pure vector 0.906 → α=0.7 hybrid 0.938; BM25 helps for short technical noun phrases |
| **docs — prose-like** (e.g. mdn) | `text-embedding-3-small` | 1.0 | off | α=1.0 ties any blend; prose-style queries are well-served by pure vector |
| **spa — JS-rendered** (e.g. huggingface) | `BAAI/bge-small-en-v1.5` | 1.0 | off | bge-small beats `text-embedding-3-small` by +0.17 MRR on hf-transformers; do NOT add BM25 (drops MRR by half) |
| **ecom** (e.g. ikea, plugin catalogs) | `text-embedding-3-small` | 1.0 (no BM25) | off | BM25 collapses MRR (0.125 → 0.016 on ikea); brand/product noun lexical noise |
| **wiki** | `text-embedding-3-small` | 1.0 | off | Weakest category in our pool (avg MRR 0.30); crawl coverage is the limiter, not retrieval |
| **blog** | `text-embedding-3-small` | 1.0 | off | Rotating-content variance; queries about *recent* posts tend to miss |
| **apiref** | `text-embedding-3-small` | 1.0 | off | Bimodal — well-curated docs (stripe-style 0.75) score high, deep-nested API ref (twilio-style 0.25) need bigger crawl budgets |

**The α-sweet-spot depends on the embedder.**  Weaker embedders
(`all-MiniLM-L6-v2`) benefit from BM25 augmentation because their
vectors miss exact-match signal.  Strong embedders (`text-embedding-3-small`)
already capture that — adding BM25 dilutes the signal and regresses
on most categories.  When in doubt with a strong embedder: α=1.0.

**General defaults if you don't know the category:**

- Embedder: `text-embedding-3-small` (or `BAAI/bge-small-en-v1.5` for free)
- α = 1.0 (pure vector)
- No cross-encoder rerank pass

## Why per-category, not per-site?

Per-site rules don't generalize — when a site changes URL structure
or moves to a new framework, the rules silently break.  Categories
capture the **content-shape** properties that drive retrieval choices:

- Docs have many short technical noun phrases (API names, classes) →
  BM25 lift exists
- Ecom has lots of repeated brand/product nouns → BM25 finds the
  wrong items because lexical signal is everywhere
- SPAs (JS-rendered) often have shorter chunks and noisier headings →
  smaller embedders trained on concise queries do better

Category mapping for a new site is a one-line decision when you
ingest it; URL-pattern rules are a maintenance liability.

## Cross-encoder reranking is not a free win

We do **not** recommend any cross-encoder reranker as a uniform pass:

| Reranker | k=50 | k=20 |
|---|---|---|
| `cross-encoder/ms-marco-MiniLM-L-6-v2` | k8s −0.149 | not measured |
| `BAAI/bge-reranker-base` (doc-tuned) | k8s −0.128 | k8s −0.095, hf +0.080 |

Reranking helped **only on the JS-rendered/SPA category** (HF) in our
data.  For docs and ecom, all rerank passes regressed — the extra
inference cost gave you a worse ranking than the embedder produced.

If you want to use a reranker anyway, prefer `bge-reranker-base` over
`ms-marco-MiniLM`, keep `k=20` (rerank only the top-20 candidates),
and dispatch by category — apply rerank only on SPA-category sites.

## Implementation: category-dispatching retrieval

```python
"""Category-aware retrieval over a MarkCrawl-built index.

Each site is tagged with a category at ingest time.  At query time,
this loads the right embedder and alpha for the site's category.
Self-contained example — depends only on `openai`, `sentence-transformers`,
and `rank-bm25` (or your favorite BM25 library).
"""
import math
from typing import Literal

from openai import OpenAI
from rank_bm25 import BM25Okapi
from sentence_transformers import SentenceTransformer

Category = Literal["docs", "spa", "ecom", "wiki", "blog", "apiref"]

# Per-category retrieval recipes — tune to your own corpus!
RECIPES: dict[Category, dict] = {
    # If your docs are heavy on API names, drop alpha to 0.5–0.7 to add BM25
    "docs":    {"embedder": "openai-3-small", "alpha": 1.0, "rerank": False},
    "spa":     {"embedder": "bge-small",      "alpha": 1.0, "rerank": False},
    "ecom":    {"embedder": "openai-3-small", "alpha": 1.0, "rerank": False},
    "wiki":    {"embedder": "openai-3-small", "alpha": 1.0, "rerank": False},
    "blog":    {"embedder": "openai-3-small", "alpha": 1.0, "rerank": False},
    "apiref":  {"embedder": "openai-3-small", "alpha": 1.0, "rerank": False},
}


def embed(name: str, texts: list[str], is_query: bool) -> list[list[float]]:
    if name == "openai-3-small":
        client = OpenAI()
        resp = client.embeddings.create(model="text-embedding-3-small",
                                         input=texts)
        return [d.embedding for d in resp.data]
    if name == "bge-small":
        st = SentenceTransformer("BAAI/bge-small-en-v1.5")
        # bge expects an instruction prefix on queries (not on passages)
        prefix = ("Represent this sentence for searching relevant passages: "
                  if is_query else "")
        out = st.encode([prefix + t for t in texts], normalize_embeddings=True)
        return out.tolist()
    raise ValueError(f"Unknown embedder: {name}")


def cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(x * x for x in b))
    return dot / (na * nb) if na and nb else 0.0


def normalize(xs: list[float]) -> list[float]:
    if not xs:
        return xs
    lo, hi = min(xs), max(xs)
    if hi - lo < 1e-12:
        return [0.0] * len(xs)
    return [(x - lo) / (hi - lo) for x in xs]


def retrieve(query: str, category: Category,
             chunks: list[dict], chunk_vecs: dict,
             top_k: int = 10) -> list[tuple[dict, float]]:
    """`chunk_vecs` is {embedder_name: [vec, vec, ...]} — pre-compute once
    per embedder you serve, then re-use across queries."""
    recipe = RECIPES[category]
    q_vec = embed(recipe["embedder"], [query], is_query=True)[0]
    c_vecs = chunk_vecs[recipe["embedder"]]

    vec_scores = [cosine(q_vec, cv) for cv in c_vecs]

    if recipe["alpha"] < 1.0:
        bm25 = BM25Okapi([c["text"].lower().split() for c in chunks])
        bm25_scores = list(bm25.get_scores(query.lower().split()))
        v_norm = normalize(vec_scores)
        b_norm = normalize(bm25_scores)
        a = recipe["alpha"]
        blended = [a * v + (1 - a) * b for v, b in zip(v_norm, b_norm)]
    else:
        blended = vec_scores

    ranked = sorted(range(len(chunks)), key=lambda i: -blended[i])[:top_k]
    return [(chunks[i], blended[i]) for i in ranked]


# Usage:
#
#   chunks = load_chunks_for_site("kubernetes-docs")  # your storage
#   pre_vecs = {
#       "openai-3-small": embed("openai-3-small",
#                               [c["text"] for c in chunks], is_query=False),
#       # also pre-compute bge-small if you serve SPA-category sites
#   }
#   results = retrieve("How do pods autoscale?", "docs", chunks, pre_vecs)
```

## Caveats

- Pre-computing two embedder spaces (one per category you serve)
  doubles storage; skip if you only have one category.
- These numbers came from a single-run measurement.  Single-run MRR
  on long-tail catalog sites (ikea-style) has ~±0.25 variance because
  a 200-page random sample of thousands of products won't hit the
  same specific items each run.  Average across multiple runs for
  decisions.
- Don't trust generic recipes blindly: spend an evening measuring
  what works on **your** category mix with **your** queries.

## Measuring on your own corpus

The simplest harness — given a list of sites, queries, and ground-truth
URL substrings — is ~80 lines of Python.  The skeleton:

```python
# 1. crawl with markcrawl → list of chunks per site
# 2. embed all chunks once (use multiple embedders if you want to dispatch)
# 3. for each query: embed, score against chunks, find rank of correct URL
# 4. average reciprocal-rank → MRR; report per-site, per-category

import json
from markcrawl import crawl
# ... load sites + queries from a YAML/JSON file ...
for site in sites:
    crawl(site["base_url"], out_dir=f"runs/{site['slug']}", max_pages=200)
    # ... chunk, embed, score against site["queries"] ...
```

Spend an afternoon building the harness once; reuse it forever.

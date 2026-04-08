# RAG Cost at Scale

<!-- style: v2, 2026-04-08 -->

Switching to markcrawl saves 21-66% on RAG infrastructure costs depending on which tool you're replacing. At mid-size scale (100K pages, 1K queries/day), that's $960-$2,960 saved per year. Solo developers with an AI subscription can run the entire pipeline at $0 marginal cost for up to ~13,000 pages.

## What drives RAG costs

Crawler choice affects two independent cost drivers in a RAG pipeline. They scale with different things, which is why this report separates them:

- **Storage costs** scale with **corpus size** (number of pages). Every page you crawl gets split into chunks, each chunk gets embedded, and the embeddings live in a hosted vector database. A crawler that produces more chunks per page costs more to store -- linearly. You pay this once per crawl (plus re-indexing).

- **Query costs** scale with **query volume** (queries per day). Every user query retrieves the top-K most relevant chunks and sends them as context to an LLM. Noisier chunks mean you need a higher K to find the same signal, which means more input tokens per query. You pay this on every query, forever.

Both cost drivers favor the crawler that produces the fewest, cleanest chunks. Markcrawl produces 25-108% fewer chunks than competing tools (see [chunk data](#source-data)) and the highest answer quality among tools that completed all 8 benchmark sites (see [ANSWER_QUALITY.md](ANSWER_QUALITY.md)).

**How to read the tables below.** Every dollar amount is an annual cost. Storage tables assume [OpenAI text-embedding-3-small](https://openai.com/pricing) at $0.02/1M tokens for embedding and $0.10/1K vectors/month for vector DB hosting (a mid-range across [Pinecone](https://www.pinecone.io/pricing/), [Qdrant](https://qdrant.tech/pricing/), [Weaviate](https://weaviate.io/pricing) -- see [full pricing sources](#storage-cost-formula)). Query tables assume [Claude Sonnet](https://www.anthropic.com/pricing) at $3.00/1M input tokens. All formulas are in the [Methodology](#methodology) section so you can replicate with your own pricing.

## Summary

Total annual cost by scenario, all 8 tools ranked by total cost ascending. This is the table most readers need.

| Tool | 1K pages, 100 q/day | 100K pages, 1K q/day | 1M pages, 10K q/day | vs markcrawl (mid) |
|---|---|---|---|---|
| **markcrawl** | **$341** | **$4,505** | **$45,055** | **--** |
| scrapy+md | $409 | $5,464 | $54,640 | +21.3% |
| firecrawl | $443 | $5,835 | $58,347 | +29.5% |
| crawl4ai | $513 | $6,960 | $69,596 | +54.5% |
| crawl4ai-raw | $513 | $6,961 | $69,608 | +54.5% |
| colly+md | $516 | $7,213 | $72,129 | +60.1% |
| playwright | $517 | $7,320 | $73,202 | +62.5% |
| crawlee | $518 | $7,467 | $74,673 | +65.7% |

> Firecrawl's K is estimated at 13, based on its chunk ratio (12.97 chunks/page, 1.28x markcrawl). Firecrawl scored 4.04/5 on answer quality (70 queries on 6 sites) vs markcrawl's 3.91/5 (92 queries on 8 sites) -- these scores are not directly comparable due to different query sets. Firecrawl is architecturally a SaaS product -- even self-hosted, it requires 4+ services (API, worker, Redis, Playwright) with no library mode. The self-hosted setup failed on 2 of 8 benchmark sites (react-dev, stripe-docs). See [SPEED_COMPARISON.md](SPEED_COMPARISON.md) and [ANSWER_QUALITY.md](ANSWER_QUALITY.md) for details.

## What this means

**For the developer picking a crawler:** markcrawl is the cheapest tool at every scale, but the gap depends on what you're comparing against. vs scrapy+md (the closest competitor), it's a 21% savings -- meaningful but not transformative. vs playwright or crawlee, it's 63-66% -- a significant budget line item at scale. Firecrawl is now the third-cheapest tool (29.5% more than markcrawl) thanks to improved page coverage that reduced its chunk ratio.

**For the engineering manager estimating budgets:** at 100K pages and 1K queries/day, markcrawl costs ~$4,500/yr in embedding + LLM infrastructure. The next cheapest tool (scrapy+md) costs ~$5,500/yr. That $960 gap is real but modest. The gap widens at scale: at 1M pages it's $9,600/yr vs scrapy+md and $28,100/yr vs playwright. The savings scale linearly -- 10x more pages = 10x more savings.

**For the senior engineer checking the model:** these projections assume a fixed K (retrieval depth) per tool, estimated from chunk ratios. The actual relationship between K and quality is non-linear, so treat these as directional estimates, not precise forecasts. The [methodology section](#estimating-k-per-tool) documents the assumptions and their limitations.

**An honest caveat:** crawler choice is not the largest cost lever in a RAG pipeline. Choosing Claude Haiku ($0.80/1M tokens) over Claude Sonnet ($3.00/1M tokens) saves 73% on query costs regardless of crawler. Optimizing chunk size and retrieval strategy often matters more than which tool fetched the HTML. Markcrawl's advantage is that it gives you the cleanest starting material, so your other optimizations compound on a better foundation.

---

## Storage Costs (scale with pages)

Every page gets chunked, embedded, and stored in a vector database. More chunks per page = higher cost. All figures use [OpenAI text-embedding-3-small](https://openai.com/pricing) at $0.02/1M tokens + $0.10/1K vectors/month for DB hosting (see [full formula](#storage-cost-formula)).

Sorted by cost ascending (markcrawl produces the fewest chunks per page):

| Pages | markcrawl | scrapy+md | firecrawl | crawl4ai | crawl4ai-raw | colly+md | playwright | crawlee |
|---|---|---|---|---|---|---|---|---|
| 100 | $1 | $2 | $2 | $2 | $2 | $2 | $2 | $3 |
| 1,000 | $12 | $15 | $16 | $20 | $20 | $23 | $24 | $25 |
| 10,000 | $122 | $152 | $156 | $203 | $203 | $229 | $239 | $254 |
| 100,000 | $1,220 | $1,522 | $1,564 | $2,032 | $2,033 | $2,285 | $2,393 | $2,540 |
| 1,000,000 | $12,205 | $15,220 | $15,642 | $20,321 | $20,333 | $22,854 | $23,927 | $25,398 |

At 1M pages, markcrawl saves **$3,015/yr vs scrapy+md** and **$13,193/yr vs crawlee** on storage alone.

---

## Query Costs (scale with query volume)

Every query retrieves top-K chunks and sends them to an LLM as context. Markcrawl's cleaner chunks produce the best answers at K=10. Tools with noisier output need a higher K to compensate, which means more tokens (and cost) per query.

### Estimated retrieval depth per tool

All figures use [Claude Sonnet](https://www.anthropic.com/pricing) at $3.00/1M input tokens. K is estimated from each tool's chunk ratio relative to markcrawl (see [methodology](#estimating-k-per-tool)).

| Tool | Quality at K=10 | Estimated K to match | Tokens/query |
|---|---|---|---|
| **markcrawl** | **3.91 (baseline)** | **10** | **3,000** |
| scrapy+md | 3.86 (-1.3%) | ~12 | 3,600 |
| firecrawl | 4.04 (+3.3%) | ~13 | 3,900 |
| crawl4ai-raw | 3.84 (-1.8%) | ~15 | 4,500 |
| colly+md | 3.83 (-2.0%) | ~15 | 4,500 |
| crawl4ai | 3.82 (-2.3%) | ~15 | 4,500 |
| crawlee | 3.80 (-2.8%) | ~15 | 4,500 |
| playwright | 3.74 (-4.3%) | ~15 | 4,500 |

### Annual LLM query cost

| Queries/day | markcrawl | scrapy+md | firecrawl | crawl4ai | crawl4ai-raw | colly+md | playwright | crawlee |
|---|---|---|---|---|---|---|---|---|
| 100 | $328 | $394 | $427 | $493 | $493 | $493 | $493 | $493 |
| 1,000 | $3,285 | $3,942 | $4,270 | $4,928 | $4,928 | $4,928 | $4,928 | $4,928 |
| 10,000 | $32,850 | $39,420 | $42,705 | $49,275 | $49,275 | $49,275 | $49,275 | $49,275 |
| 100,000 | $328,500 | $394,200 | $427,050 | $492,750 | $492,750 | $492,750 | $492,750 | $492,750 |

Query costs dwarf storage costs at every scale. At 1K queries/day, the LLM bill is 2-3x the storage bill. This is why the K estimate matters -- even a small increase in retrieval depth compounds across millions of queries.

---

## Named Scenarios

Three scenarios so you can find your own situation. Each breaks out storage and query costs separately, because they scale with different things and you may be able to reduce one independently.

### Scenario A: Small app (1K pages, 100 queries/day)

A side project or internal tool. Storage is negligible; query costs dominate.

| Tool | Storage/yr | Queries/yr | Total/yr | vs markcrawl |
|---|---|---|---|---|
| **markcrawl** | **$12** | **$328** | **$341** | **--** |
| scrapy+md | $15 | $394 | $409 | +$69 (+20.2%) |
| firecrawl | $16 | $427 | $443 | +$102 (+29.9%) |
| crawl4ai | $20 | $493 | $513 | +$172 (+50.6%) |
| crawl4ai-raw | $20 | $493 | $513 | +$172 (+50.6%) |
| colly+md | $23 | $493 | $516 | +$175 (+51.3%) |
| playwright | $24 | $493 | $517 | +$176 (+51.6%) |
| crawlee | $25 | $493 | $518 | +$177 (+52.1%) |

### Scenario B: Mid-size product (100K pages, 1K queries/day)

A production RAG product. Both storage and query costs are meaningful.

| Tool | Storage/yr | Queries/yr | Total/yr | vs markcrawl |
|---|---|---|---|---|
| **markcrawl** | **$1,220** | **$3,285** | **$4,505** | **--** |
| scrapy+md | $1,522 | $3,942 | $5,464 | +$960 (+21.3%) |
| firecrawl | $1,564 | $4,270 | $5,835 | +$1,330 (+29.5%) |
| crawl4ai | $2,032 | $4,928 | $6,960 | +$2,455 (+54.5%) |
| crawl4ai-raw | $2,033 | $4,928 | $6,961 | +$2,456 (+54.5%) |
| colly+md | $2,285 | $4,928 | $7,213 | +$2,708 (+60.1%) |
| playwright | $2,393 | $4,928 | $7,320 | +$2,815 (+62.5%) |
| crawlee | $2,540 | $4,928 | $7,467 | +$2,963 (+65.7%) |

### Scenario C: Large-scale RAG (1M pages, 10K queries/day)

Enterprise scale. Both storage and query savings are substantial.

| Tool | Storage/yr | Queries/yr | Total/yr | vs markcrawl |
|---|---|---|---|---|
| **markcrawl** | **$12,205** | **$32,850** | **$45,055** | **--** |
| scrapy+md | $15,220 | $39,420 | $54,640 | +$9,585 (+21.3%) |
| firecrawl | $15,642 | $42,705 | $58,347 | +$13,292 (+29.5%) |
| crawl4ai | $20,321 | $49,275 | $69,596 | +$24,541 (+54.5%) |
| crawl4ai-raw | $20,333 | $49,275 | $69,608 | +$24,553 (+54.5%) |
| colly+md | $22,854 | $49,275 | $72,129 | +$27,074 (+60.1%) |
| playwright | $23,927 | $49,275 | $73,202 | +$28,147 (+62.5%) |
| crawlee | $25,398 | $49,275 | $74,673 | +$29,619 (+65.7%) |

---

## Head-to-Head: markcrawl vs scrapy+md

Scrapy+md is markcrawl's closest competitor on both chunk efficiency and answer quality. If you're deciding between these two, here's the full picture across every scale.

### Storage comparison

All figures use the same pricing assumptions as above (see [storage formula](#storage-cost-formula)).

| Pages | MC chunks | Scrapy chunks | MC storage/yr | Scrapy storage/yr | Savings |
|---|---|---|---|---|---|
| 100 | 1,012 | 1,262 | $1 | $2 | $0.30 |
| 1,000 | 10,120 | 12,620 | $12 | $15 | $3 |
| 10,000 | 101,200 | 126,200 | $122 | $152 | $30 |
| 100,000 | 1,012,000 | 1,262,000 | $1,220 | $1,522 | $302 |
| 1,000,000 | 10,120,000 | 12,620,000 | $12,205 | $15,220 | $3,015 |

### Query comparison

| Queries/day | MC queries/yr | Scrapy queries/yr | Savings |
|---|---|---|---|
| 100 | $328 | $394 | $66 |
| 1,000 | $3,285 | $3,942 | $657 |
| 10,000 | $32,850 | $39,420 | $6,570 |

The margin vs scrapy+md is roughly **21% savings** across all scales. But markcrawl leads on both dimensions: 24.7% fewer chunks and 1.3% higher answer quality (see [ANSWER_QUALITY.md](ANSWER_QUALITY.md)).

---

## Solo Developer Costs

Most solo developers don't pay per-token -- they have a flat-rate AI subscription. With the right stack, a solo dev can run a full RAG pipeline at **$0 marginal cost** for up to ~13,000 pages. The only variable cost is vector database hosting, and free tiers are generous enough to cover most documentation sites.

The [API-priced scenarios above](#named-scenarios) model enterprise workloads. This section covers a different reality: a developer with Claude Code Max ($200/mo), ChatGPT Plus ($20/mo), or similar, who wants to build a RAG app without additional API bills. The crawler choice still matters -- markcrawl's lower chunk count means more pages fit in the same free-tier storage.

### What changes with a subscription

| Cost item | API pricing | With subscription | How |
|---|---|---|---|
| Embeddings | ~$0.50-0.75/run | **$0** | Use local [`sentence-transformers`](https://huggingface.co/docs/sentence-transformers) instead of OpenAI API |
| LLM answer scoring | ~$0.15-0.25/run | **$0** | Route through Claude Code / ChatGPT |
| LLM queries at runtime | $3.00/1M input tokens | **$0** | Within subscription limits |
| Vector database | $0-25/mo | **$0-25/mo** | Free tiers cover most solo projects |

The only hard cost is vector database hosting -- and free tiers cover a surprising number of pages.

### How many pages fit in free tiers

Storage per chunk uses this formula:

```
raw_bytes    = dimensions x 4 bytes            (1536-dim -> 6,144 bytes)
metadata     = ~2 KB per chunk                  (text, source URL, chunk index)
with_indexes = raw_bytes x ~2                   (pgvector HNSW index overhead)
total        = (6,144 + 2,048) x 2 = 16 KB     per chunk with indexes

max_chunks   = free_storage_bytes / 16,384
max_pages    = max_chunks / chunks_per_page     (10.1 for markcrawl)
```

Using markcrawl (10.1 chunks/page, the most efficient). Sorted by max pages descending:

| Service | Type | Free storage | Max chunks | Max pages | Notes |
|---|---|---|---|---|---|
| **Zilliz** | Vector-only | 5 GB | ~327,000 | **~32,400** | Most free storage |
| **Qdrant** | Vector-only | 4 GB disk | ~262,000 | **~25,900** | 0.5 vCPU, 1 GB RAM |
| **Pinecone** | Vector-only | 2 GB | ~131,000 | **~13,000** | 1M reads/mo included |
| **Supabase** | DB + vectors | 500 MB | ~32,000 | **~3,200** | Pauses after 7 days inactivity |
| **Neon** | DB + vectors | 500 MB | ~32,000 | **~3,200** | No pause, 100 compute-hrs/mo |
| **Railway** | DB + vectors | $5/mo credits | ~2,000+ | **~2,000** | Typical actual cost ~$0.55/mo |

Crawler choice matters here: a noisier tool like crawlee (21.1 chunks/page) roughly halves these numbers -- ~1,520 pages on Supabase Free instead of ~3,200. This is the same chunk efficiency gap from the [main comparison](#summary), but now it translates directly into free-tier capacity.

For context, 3,200 pages covers most documentation sites entirely (FastAPI docs: 275 pages, Python stdlib: 500 pages, Stripe docs: 500 pages). A solo dev building a RAG app over 1-3 documentation sites fits comfortably in a free tier.

### Database + vector storage (full-stack)

These services provide a SQL database, auth, storage, AND vector search -- everything you need for a RAG app backend. No separate vector service needed. Sorted by cheapest paid tier ascending:

| Service | Free tier | Cheapest paid | Per-query cost? | Best for |
|---|---|---|---|---|
| **[Railway](https://railway.app/pricing)** | $5/mo in credits | ~$0.55/mo actual | No | Simple deploy-anything platform |
| **[Neon](https://neon.tech/pricing)** | 500 MB, no pause | Usage-based (~$1-5/mo) | No | Serverless Postgres, DB branching for dev/staging |
| **[PlanetScale](https://planetscale.com/pricing)** | Dev tier | $5/mo | Yes ($1/B reads) | MySQL-native teams, native vector columns |
| **[CockroachDB](https://www.cockroachlabs.com/pricing/)** | $15/mo in credits | Usage-based | Yes (request units) | Multi-region, distributed SQL |
| **[Supabase](https://supabase.com/pricing)** | 500 MB, pauses after 7d | $25/mo (8 GB, ~52K pages) | No | Full-stack apps (auth, storage, realtime, edge functions) |

### Vector-only services (embedding storage + search)

These only store and query embeddings -- no SQL, no auth, no file storage. Use these when you already have a separate database and just need fast vector search. Sorted by cheapest paid tier ascending:

| Service | Free tier | Cheapest paid | Per-query cost? | Best for |
|---|---|---|---|---|
| **[Weaviate](https://weaviate.io/pricing)** | 14-day trial only | $45/mo | Indirect | GraphQL API, module ecosystem |
| **[Pinecone](https://www.pinecone.io/pricing/)** | 2 GB, 1M reads/mo | $50/mo | Yes ($16/M reads) | Simplest API, widest RAG adoption |
| **[Turbopuffer](https://turbopuffer.com/pricing)** | None | $64/mo | Yes (~$4/M queries) | Extreme scale (used by Cursor for 100B+ vectors) |
| **[Qdrant](https://qdrant.tech/pricing/)** | 0.5 vCPU, 4 GB disk | ~$150/mo | No | Self-host friendly, no per-query fees |
| **[Chroma](https://www.trychroma.com/pricing)** | $5 in credits | $250/mo | Yes ($0.0075/TiB queried) | Python-native, local-first development |
| **[Zilliz](https://zilliz.com/pricing)** | 5 GB | Serverless ($4/M compute units) | Yes | Most free storage, Milvus ecosystem |

### Solo dev named scenarios

Three scenarios matching different project sizes. The key insight: for most solo projects, the entire RAG pipeline is free beyond your existing AI subscription. The breakpoint is vector DB storage, and crawler efficiency determines where you hit it.

**Scenario: Side project (1 documentation site, <500 pages)**

| Item | Cost |
|---|---|
| Crawler | $0 (markcrawl, open source) |
| Embeddings | $0 (local sentence-transformers) |
| Vector DB | $0 (Supabase Free or Neon Free) |
| LLM queries | $0 (within Claude Code / ChatGPT subscription) |
| **Total** | **$0/mo** (beyond your existing AI subscription) |

**Scenario: Serious side project (3-5 sites, ~2,000 pages)**

| Item | Cost |
|---|---|
| Crawler | $0 |
| Embeddings | $0 (local) |
| Vector DB | $0 (fits in Supabase Free / Neon Free / Pinecone Free) |
| LLM queries | $0 (within subscription) |
| **Total** | **$0/mo** |

**Scenario: Production app (10+ sites, ~10,000 pages)**

| Item | Cost |
|---|---|
| Crawler | $0 |
| Embeddings | $0 (local) or ~$0.06 one-time (OpenAI API) |
| Vector DB | $25/mo (Supabase Pro) or $0 (Pinecone Free covers ~13,000 pages) |
| LLM queries | $0 (within subscription) or $10-30/mo (API at 1K queries/day) |
| **Total** | **$0-25/mo** |

**What this means in practice:** if you're already paying for an AI subscription and building a RAG app over documentation sites, you likely won't pay anything extra. The marginal cost of adding markcrawl to your stack is $0. The only question is whether your corpus fits in a free-tier vector DB -- and with markcrawl's 10.1 chunks/page, you get roughly 2x the capacity of noisier crawlers like crawlee before you need to upgrade. See [ANSWER_QUALITY.md](ANSWER_QUALITY.md) for whether that quality difference matters for your use case.

---

## Methodology

### Source data

All numbers derive from our benchmark of **92 queries across 8 sites** using 8 crawler tools. Full results in [ANSWER_QUALITY.md](ANSWER_QUALITY.md) and [RETRIEVAL_COMPARISON.md](RETRIEVAL_COMPARISON.md). See [METHODOLOGY.md](METHODOLOGY.md) for the complete test setup.

Measured values for all tools (sorted by chunks/page ascending):

| Tool | Total chunks | Pages | Chunks/page | Answer quality (/5) |
|---|---|---|---|---|
| **markcrawl** | **2,126** | **210** | **10.12** | **3.91** |
| scrapy+md | 2,574 | 204 | 12.62 | 3.86 |
| firecrawl | 14,000 | 1,079 | 12.97 | 4.04 |
| crawl4ai | 3,539 | 210 | 16.85 | 3.82 |
| crawl4ai-raw | 3,540 | 210 | 16.86 | 3.84 |
| colly+md | 3,884 | 205 | 18.95 | 3.83 |
| playwright | 4,167 | 210 | 19.84 | 3.74 |
| crawlee | 4,422 | 210 | 21.06 | 3.80 |

All tools crawled the same ~210 pages across 8 sites. Firecrawl crawled 6 of 8 sites (1,079 pages) -- it has higher total chunks due to more pages, but a comparable chunks/page ratio. Firecrawl's answer quality (4.04/5) is based on 70 queries across 6 sites, while other tools were scored on 92 queries across 8 sites -- see [ANSWER_QUALITY.md](ANSWER_QUALITY.md) for why these scores are not directly comparable. Chunks were created with the same chunker (300-word max, 50-word overlap). Quality was scored by a GPT-4o-mini judge on correctness, relevance, completeness, and usefulness (1-5 each), averaged to an overall score.

### Chunk count formula

```
chunks = pages x chunks_per_page

where chunks_per_page is measured per-tool (see table above)
```

### Storage cost formula

Storage = embedding (one-time) + vector DB hosting (ongoing).

**Embedding:**
```
embedding_cost = chunks x tokens_per_chunk x price_per_token

where:
  tokens_per_chunk = 300          (measured average across benchmark)
  price_per_token  = $0.02 / 1M  (OpenAI text-embedding-3-small, April 2026)
```

**Vector database:**
```
annual_storage = (chunks / 1,000) x cost_per_1K_vectors_per_month x 12

where:
  cost_per_1K_vectors_per_month = $0.10
```

**Embedding pricing source:** [OpenAI pricing](https://openai.com/pricing)
- `text-embedding-3-small`: $0.02 per 1M tokens
- `text-embedding-3-large`: $0.13 per 1M tokens (6.5x more, same formula applies)

**Vector DB pricing source** ($0.10/1K/month is a mid-range across providers):

| Provider | Plan | Approximate cost | Source |
|---|---|---|---|
| Pinecone | Serverless (s1) | ~$0.08-0.12/1K vectors/mo | [pinecone.io/pricing](https://www.pinecone.io/pricing/) |
| Pinecone | Standard (p1) | ~$0.096/1K vectors/mo | [pinecone.io/pricing](https://www.pinecone.io/pricing/) |
| Qdrant | Cloud | ~$0.085/GB/mo (~$0.05-0.10/1K) | [qdrant.tech/pricing](https://qdrant.tech/pricing/) |
| Weaviate | Cloud | ~$0.095/1K vectors/mo | [weaviate.io/pricing](https://weaviate.io/pricing) |

Vector size: 1536 dimensions (text-embedding-3-small) x 4 bytes = 6,144 bytes/vector, plus ~2 KB metadata per chunk. Self-hosted is cheaper but requires ops overhead.

### Query cost formula

```
annual_query_cost = K x tokens_per_chunk x queries_per_day x 365 x price_per_token

where:
  K                 = estimated retrieval depth to match markcrawl quality (see below)
  tokens_per_chunk  = 300
  price_per_token   = $3.00 / 1M  (Claude Sonnet input, April 2026)
```

**LLM pricing source:** [Anthropic pricing](https://www.anthropic.com/pricing)
- Claude Sonnet: $3.00 per 1M input tokens
- Claude Opus: $15.00 per 1M input tokens (5x multiplier)
- Claude Haiku: $0.80 per 1M input tokens

### Estimating K per tool

Markcrawl scores 3.91/5 with K=10. Each tool's K is scaled proportionally to its chunk ratio: `K = round(10 x (tool_chunks_per_page / markcrawl_chunks_per_page))`, capped at 15. This reflects needing more chunks to find the same signal in noisier output.

**Limitations of this model:** the actual relationship between K and quality is non-linear. Increasing K has diminishing returns -- you get more context but also more noise. Some quality gap may persist regardless of K, because the issue isn't just retrieving more chunks but retrieving *cleaner* chunks. Treat these projections as directional, not precise.

### Retrieval degradation at scale (not modeled)

The quality gaps measured at 150 pages likely grow at larger corpus sizes. More chunks in the vector index means more "distractor" vectors competing for top-K retrieval slots. Research on dense retrieval shows precision degrades approximately with log(N).

```
At 1M pages:
  markcrawl:  log2(10.1M) = 23.3 difficulty factor
  scrapy+md:  log2(12.6M) = 23.6  (+1.3% harder)
  firecrawl:  log2(13.0M) = 23.6  (+1.5% harder)
  crawl4ai:   log2(16.9M) = 24.0  (+3.0% harder)
  crawlee:    log2(21.1M) = 24.3  (+4.5% harder)
  playwright: log2(19.8M) = 24.2  (+3.9% harder)
```

This effect is not captured in our benchmark (which tests ~210 pages) but would widen quality gaps at production scale.

---

## What this analysis does NOT include

- **Crawl compute**: markcrawl is the third-fastest tool (see [SPEED_COMPARISON.md](SPEED_COMPARISON.md)), saving server time vs Playwright-based tools, but hard to dollarize without knowing infrastructure.
- **Re-indexing costs**: pages change and need re-embedding; the chunk ratio applies to every re-index cycle.
- **Output token costs**: only input tokens are modeled. Output costs are roughly equal across tools since answer length is similar.
- **Retrieval compute**: vector similarity search scales with index size. Smaller indexes are faster to query (relevant at >10M vectors).
- **Human cost of bad answers**: quality gaps mean some queries produce noticeably worse answers. At 1K queries/day, even a 1% gap is 10 degraded answers daily.

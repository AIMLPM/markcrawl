# Production RAG Retrieval: Research for Benchmark Design

> Research compiled April 2026. Focused on 2024-2025 findings relevant to benchmarking
> a web crawler's output quality for RAG use cases.

---

## Table of Contents

1. [How Many Chunks Do Production Systems Retrieve?](#1-how-many-chunks-do-production-systems-retrieve)
2. [Retrieval Evaluation Metrics](#2-retrieval-evaluation-metrics)
3. [Reranking in Production RAG](#3-reranking-in-production-rag)
4. [RAG Pipeline Architectures](#4-rag-pipeline-architectures)
5. [Chunk Quality vs Quantity](#5-chunk-quality-vs-quantity)
6. [Standard RAG Benchmarks](#6-standard-rag-benchmarks)
7. [Embedding Models in Production](#7-embedding-models-in-production)
8. [Chunk Size and Overlap](#8-chunk-size-and-overlap)
9. [Implications for Web Crawler Benchmarking](#9-implications-for-web-crawler-benchmarking)

---

## 1. How Many Chunks Do Production Systems Retrieve?

### Framework Defaults

| Framework   | Default top-k | Notes |
|-------------|---------------|-------|
| LlamaIndex  | 5             | `similarity_top_k=5` in default query engine [3] |
| LangChain   | 4             | Default `k=4` in vector store retrievers |

These defaults are starting points. Production systems almost always tune this value.

### Anthropic's Contextual Retrieval Benchmark (2024)

Anthropic's Contextual Retrieval research [1] is the most rigorous public study on top-k values for RAG:

- **Initial retrieval**: Top 150 chunks (broad recall stage)
- **After reranking**: Top 20 chunks passed to the LLM
- **Testing variations**: Tested 5, 10, and 20 chunks; **20 was most effective**
- Passing top-20 chunks to the model proved more effective than using fewer chunks [1]

### Production Patterns

| Stage | Typical K | Purpose |
|-------|-----------|---------|
| Initial embedding retrieval | 20-150 | Maximize recall; fast bi-encoder search [1] |
| After reranking | 3-20 | Maximize precision; slow cross-encoder scoring [4] |
| Passed to LLM | 3-20 | Context window budget vs. answer quality [1] |

**Key insight**: Production systems do NOT use top-1 or top-3 from raw embedding search. They retrieve broadly (high K) and narrow down via reranking [1] [4].

---

## 2. Retrieval Evaluation Metrics

### Metric Definitions

**Recall@K** -- What fraction of all relevant documents appear in the top-K results? [6]
```
Recall@K = (relevant items in top-K) / (total relevant items)
```
Common K values: 1, 3, 5, 10, 20. Higher K gives higher recall but measures a looser bar.

**Precision@K** -- What fraction of the top-K results are relevant? [6]
```
Precision@K = (relevant items in top-K) / K
```

**MRR (Mean Reciprocal Rank)** -- Average of 1/rank of the first relevant result across queries [6].
```
MRR = (1/N) * sum(1 / rank_i)
```
Useful when you care about the *first* relevant hit (e.g., single-answer questions).

**MAP (Mean Average Precision)** -- Mean of average precision across queries. Rewards systems that rank *all* relevant items higher. Best for multi-document relevance [6].

**NDCG@K (Normalized Discounted Cumulative Gain)** -- Accounts for both relevance *and* position, with logarithmic discount for lower-ranked items. Values relevance grades (not just binary relevant/not-relevant) [6].
```
DCG@K = sum(relevance_i / log2(i + 1))
NDCG@K = DCG@K / ideal_DCG@K
```

### Which Metrics Matter Most for RAG?

| Metric | RAG Relevance | When to Use |
|--------|---------------|-------------|
| **Recall@K** | **Critical** | If the relevant chunk isn't retrieved, the LLM can't answer. This is the floor [16]. |
| **NDCG@K** | High | Correlates most strongly with end-to-end RAG quality. Target NDCG@10 > 0.8 [18]. |
| **MRR** | Medium | Matters for single-answer factoid questions. Less relevant for synthesis tasks [6]. |
| **MAP** | Medium | Good for evaluating multi-document retrieval scenarios [6]. |
| **Precision@K** | Lower | Less critical because LLMs can filter noise; recall matters more than precision for retrieval [16]. |

### Important Caveat (2025 Research)

Recent research [8] shows that classical IR metrics like NDCG, MAP, and MRR fail to adequately predict RAG performance because they assume monotonically decreasing document utility with rank position. New approaches like **eRAG** score each document based on the quality of the LLM's response when receiving only that document as context, showing better correlation with end-to-end RAG performance [8].

**Practical finding**: Improving retrieval recall from 80% to 95% may only improve answer quality by 5-10% if the generation model poorly utilizes the retrieved context [8].

### Recommendation for Crawler Benchmarking

For a web crawler benchmark, **Recall@K** is the right primary metric because:
- It directly measures "did the retrieval system find the right content?" [16]
- It's simple, interpretable, and doesn't require relevance grading
- The crawler's job is to produce content that *can be found* -- downstream reranking handles precision [4]

Measure at multiple K values: **Recall@1, Recall@5, Recall@10, Recall@20**.

---

## 3. Reranking in Production RAG

### Two-Stage Retrieval is Standard

Nearly all production RAG systems in 2024-2025 use a two-stage pipeline [4]:

```
Query --> Bi-encoder retrieval (top-20 to top-150) --> Cross-encoder reranking (top-3 to top-20) --> LLM
```

### Why Two Stages?

- **Bi-encoders** (embedding models): Fast (~1ms per query), but lower precision. Pre-compute document embeddings offline [4].
- **Cross-encoders** (rerankers): Slow (~10ms per pair), but much higher precision. Score each query-document pair jointly [4].

You can't run cross-encoders against millions of documents. You *need* the fast first stage.

### Performance Impact

- Reranking improves retrieval precision by **30-50%** in production systems [15]
- Databricks research shows reranking can improve retrieval quality by **up to 48%** [15]
- Anthropic found reranking reduced retrieval failure by **67%** when combined with contextual retrieval [1]

### Popular Reranking Models (2024-2025)

| Model | Parameters | Notes |
|-------|-----------|-------|
| Cohere Rerank v3 | Proprietary | Most widely used commercial reranker [4] |
| BAAI/bge-reranker-v2-m3 | 278M | Best open-weight reranker for English + multilingual |
| cross-encoder/ms-marco-MiniLM-L-6-v2 | 22M | Lightweight, widely used open-source [4] |
| Jina Reranker v2 | 137M | Good balance of speed and quality |

### Latency Budget

- Reranking 50 documents: ~1.5 seconds [15]
- Reranking 100 documents: should be < 300ms with optimized models
- If reranking exceeds 500ms, reduce the candidate set size

### Implications for Crawler Benchmarking

Since production systems use reranking [4], the initial retrieval stage's job is **recall, not precision**. A crawler benchmark should therefore:
- Evaluate at **higher K values** (K=10, K=20) to match what rerankers receive
- Not penalize noisy results heavily -- rerankers handle that
- Focus on whether the *correct* chunk is *somewhere* in the top-K

---

## 4. RAG Pipeline Architectures

### The Three Paradigms

#### Naive RAG (2023) [13]
```
Query --> Embed --> Vector Search (top-k) --> Concatenate with query --> LLM --> Response
```
- Fixed retriever (BM25 or single embedding model)
- No query transformation, no reranking
- Suffers from low precision and fragmented context

#### Advanced RAG (2024) [13] [14]
```
Query --> Query Rewriting/Expansion --> Hybrid Search (vector + BM25) --> Reranking --> LLM --> Response
```
- Pre-retrieval: query rewriting, HyDE, multi-query expansion (3-5 reformulations)
- Retrieval: hybrid search combining dense vectors + sparse BM25
- Post-retrieval: cross-encoder reranking, context compression
- This is the standard for "production RAG" in 2025

#### Modular/Agentic RAG (2025) [13]
```
Query --> Router/Planner --> [Retriever | Web Search | SQL | Graph DB] --> Evaluator --> LLM --> Response
                                                                              |
                                                                              v
                                                                    (iterate if low confidence)
```
- Components are swappable modules
- AI agent decides retrieval strategy dynamically
- Iterative refinement: re-retrieve if initial results are insufficient
- Multi-agent architectures for complex queries

### What Most Production Systems Actually Use

The majority of production systems in 2025 are **Advanced RAG** -- hybrid search with reranking [14]. Modular/agentic RAG is growing but still limited to sophisticated teams. Naive RAG persists in prototypes and demos [13].

### Implications for Crawler Benchmarking

A crawler benchmark should assume the **Advanced RAG** architecture as the target consumer:
- Content will be chunked and embedded
- Both semantic (vector) and keyword (BM25) retrieval will be used [14]
- Reranking will follow initial retrieval [4]
- The crawler's output quality affects every stage: better markdown means better chunks, better embeddings, and better keyword matching

---

## 5. Chunk Quality vs Quantity

### Quality Defines the Ceiling

> "The quality of your text chunking doesn't just set a baseline for your RAG system's performance; it defines the upper limit." [11]

This finding from multiple 2024-2025 studies is the single most important insight for crawler benchmarking.

### Key Research Findings

**Adaptive chunking vs. fixed-size (2025)** [12]:
- Adaptive chunking aligned to logical topic boundaries: **87% accuracy**
- Fixed-size baseline: **13% accuracy**
- This 74-point gap shows that chunk boundary quality is transformative

**Semantic chunking impact** [11]:
- Up to **9% recall improvement** over naive fixed-size splitting
- The wrong strategy creates a **9% recall gap** between best and worst approaches

**Vectara NAACL 2025 study** [11]:
- Fixed-size chunking consistently outperformed semantic chunking on realistic document sets
- Suggests that simple approaches work well when the *input content is clean*

### The Garbage In, Garbage Out Problem

When source content is noisy (navigation elements, ads, boilerplate) [11]:
- Chunks contain irrelevant text mixed with useful content
- Embeddings become less accurate (noisy signal)
- Keyword search matches on irrelevant terms
- Reranking can partially compensate, but fundamentally "you can't retrieve what isn't there"

When source content is clean:
- Even simple fixed-size chunking produces good results [11]
- Embeddings capture semantic meaning accurately
- Keyword search matches on substantive terms only
- The entire pipeline performs better

### Implications for Crawler Benchmarking

This is the strongest argument for benchmarking crawler output quality:
1. **Clean content from crawlers --> better chunks --> better embeddings --> better retrieval** [11]
2. No amount of sophisticated RAG engineering compensates for garbage input
3. The crawler is the *first* quality gate in the pipeline
4. A crawler that strips boilerplate, preserves structure, and outputs clean markdown directly improves every downstream stage

---

## 6. Standard RAG Benchmarks

### Retrieval-Focused Benchmarks

**BEIR (Benchmarking-IR)** [18]
- 17 datasets spanning diverse text retrieval tasks
- The standard for evaluating embedding models in IR
- Domains: bio-medical, finance, scientific, web search, etc.
- Primary metric: NDCG@10

**MTEB (Massive Text Embedding Benchmark)** [9]
- 58 datasets, 112 languages, 8 embedding tasks
- Hosted on Hugging Face; incorporates BEIR
- Tasks: retrieval, classification, clustering, reranking, etc.
- The leaderboard for comparing embedding models

### RAG-Specific Benchmarks

**RAGAS (Retrieval Augmented Generation Assessment)** [5]
- Framework for reference-free RAG evaluation
- Four core metrics:
  - **Faithfulness**: Is the response factually consistent with retrieved context? (0-1)
  - **Answer Relevancy**: Is the response relevant to the original query? (0-1)
  - **Context Precision**: Are retrieved documents useful for answering? (0-1)
  - **Context Recall**: Do retrieved documents cover all relevant aspects? (0-1)
- Does not require ground-truth human annotations
- Uses LLM-as-judge to compute metrics

**CRAG (Comprehensive RAG Benchmark) -- KDD Cup 2024** [16]
- Evaluates RAG across diverse domains and question types
- Three tasks with varying access to external sources
- Tests real-world complexity: web pages, knowledge graphs

**RAGBench (2024)** [7]
- Explainable benchmark for RAG systems
- Provides diagnostic information about failure modes

### Other Notable Benchmarks
- LegalBench-RAG: domain-specific legal retrieval
- T2-RAGBench: temporal reasoning in RAG
- WixQA: real production question-answering

### Implications for Crawler Benchmarking

Our crawler benchmark is distinct from these: we're not evaluating the embedding model or the LLM. We're evaluating **content quality at the ingestion stage**. The closest analogy is measuring how the crawler's output affects **Context Recall** [5] -- does the crawled content, once chunked and embedded, allow the retrieval system to find the right information?

---

## 7. Embedding Models in Production

### Current Landscape (2025-2026)

#### Proprietary

| Model | MTEB Score | Cost (per 1M tokens) | Dimensions | Notes |
|-------|-----------|----------------------|------------|-------|
| Cohere embed-v4 | 65.2 | ~$0.10 | 1024 | Top MTEB; multilingual + multimodal [9] |
| OpenAI text-embedding-3-large | 64.6 | $0.13 | 3072 (variable) | Variable dimensions; can truncate to 256 [10] |
| OpenAI text-embedding-3-small | 62.3 | $0.02 | 1536 | Best cost/performance ratio [10] |
| Voyage AI voyage-3 | ~64 | $0.06 | 1024 | Strong on code and technical content [9] |

#### Open-Source

| Model | MTEB Score | Parameters | Notes |
|-------|-----------|-----------|-------|
| BGE-M3 | 63.0 | 568M | Dense + sparse + multi-vector; MIT license [9] |
| Nomic Embed v1.5 | ~62 | 137M | Fast; good for real-time systems [9] |
| E5-Mistral-7B | ~63 | 7B | LLM-based; high quality but slow |
| all-MiniLM-L6-v2 | ~56 | 22M | Fast baseline for prototyping [10] |

### Practical Recommendations

- **Startup/MVP**: all-MiniLM-L6-v2 (free, fast) [10]
- **Production, quality matters**: Cohere embed-v4 or OpenAI text-embedding-3-large [9]
- **Production, budget matters**: BGE-M3 self-hosted [9]
- **Multilingual**: Cohere embed-v4 or BGE-M3
- **Privacy-critical**: BGE-M3 (MIT license, self-hosted)

### Implications for Crawler Benchmarking

For a crawler benchmark, the choice of embedding model is a **confound** -- we want to measure crawler quality, not embedding model quality. Options:
1. **Use a single standard model** (e.g., OpenAI text-embedding-3-small) for consistency
2. **Test across multiple models** to show crawler quality holds regardless of embedding model
3. **Use the most common production model** for relevance (OpenAI embeddings are dominant) [10]

Our current benchmark uses OpenAI text-embedding-3-small, which is a reasonable default: cheap, widely used, and adequate for measuring relative differences between crawlers.

---

## 8. Chunk Size and Overlap

### Benchmark-Validated Defaults

The current consensus from 2024-2025 benchmarks [2] [11]:

| Parameter | Recommended Default | Range |
|-----------|-------------------|-------|
| Chunk size | **512 tokens** | 256-1024 tokens depending on query type |
| Overlap | **10-20% of chunk size** (50-100 tokens) | Minimum 10%; 15% optimal in FinanceBench [11] |

### NVIDIA 2024 Benchmark Results

Tested 7 chunking strategies across 5 datasets [2]:

| Strategy | Average Accuracy | Std Dev | Notes |
|----------|-----------------|---------|-------|
| **Page-level** | **0.648** | **0.107** | Most consistent across datasets |
| Token-based (512) | 0.645 | 0.12 | Near-equivalent to page-level |
| Token-based (1024) | 0.640 | 0.13 | Better for analytical queries |
| Token-based (256) | 0.620 | 0.15 | Better for factoid queries |
| Token-based (128) | 0.603 | 0.18 | Too fragmented |

### Query-Type Sensitivity

| Query Type | Optimal Chunk Size | Why |
|------------|-------------------|-----|
| Factoid (single fact) | 256-512 tokens | Smaller = more precise signal [2] |
| Analytical (reasoning) | 1024+ tokens | Needs surrounding context [2] |
| Multi-hop (connecting ideas) | Page-level or 1024 | Needs broader context [2] |

### Overlap Matters

- Skipping overlap is the third most common chunking mistake [11]
- Even 10% overlap recovers context lost at chunk boundaries
- 15% overlap performed best on FinanceBench with 1024-token chunks [11]

### Anthropic's Contextual Retrieval Parameters

- Chunk size: **800 tokens** [1]
- Context window prepended to each chunk: **50-100 tokens** (generated by LLM) [1]
- This "contextual chunk" approach reduced retrieval failure by 49-67% [1]

### Implications for Crawler Benchmarking

Our benchmark should use **standard chunking parameters** so results generalize:
- **512 tokens with 10-20% overlap** as the default [2]
- Recursive character splitting (preserves paragraphs and sentences)
- Test at multiple chunk sizes if feasible (256, 512, 1024) to show robustness

The key question for a crawler benchmark: does cleaner crawler output produce better chunks *regardless* of chunk size? If yes, that's a strong signal that crawler quality matters.

---

## 9. Implications for Web Crawler Benchmarking

### The Core Argument

A web crawler sits at the very beginning of the RAG pipeline:

```
Web Page --> Crawler --> Markdown --> Chunker --> Embedder --> Vector DB --> Retriever --> Reranker --> LLM
```

Every downstream component depends on what the crawler produces. Research shows:
1. Chunk quality defines the **ceiling** of RAG performance [11]
2. Clean content makes even simple chunking strategies effective [11]
3. No amount of reranking compensates for missing content (can't retrieve what wasn't crawled) [4]

### Recommended Benchmark Design

Based on this research, a web crawler retrieval benchmark should:

#### Metrics
- **Primary**: Recall@K at K=5, K=10, K=20 [6] [16]
- **Secondary**: MRR (for single-answer queries), NDCG@10 (for graded relevance if available) [18]
- Recall@K is the right choice because the crawler's job is to ensure relevant content *can be found*, not to rank it

#### K Values
- **K=5**: Matches the "what if there's no reranker?" scenario (framework defaults) [3]
- **K=10**: Matches the "modest reranking" scenario
- **K=20**: Matches Anthropic's recommended pipeline (retrieve 150, rerank to 20) [1]
- Reporting at multiple K values shows how sensitive results are to the retrieval budget

#### Chunking Parameters
- **Default**: 512 tokens, 10-20% overlap, recursive character splitting [2]
- This matches the most widely validated configuration
- Consider testing at 256 and 1024 tokens as sensitivity analysis

#### Embedding Model
- Use a single standard model for consistency (OpenAI text-embedding-3-small is reasonable) [10]
- The goal is to measure *relative* differences between crawlers, not absolute retrieval quality

#### What to Measure
1. **Content completeness**: Does the crawled markdown contain the information needed to answer test queries?
2. **Retrieval success**: Once chunked and embedded, can the relevant chunks be found? [16]
3. **Boilerplate impact**: Does navigation/footer/ad content degrade retrieval by polluting chunks? [11]
4. **Structure preservation**: Do headings, lists, and code blocks survive crawling and aid retrieval?

#### Comparison to Existing Benchmarks

| Benchmark | Measures | Our Benchmark Measures |
|-----------|----------|----------------------|
| BEIR/MTEB [9] [18] | Embedding model quality | Crawler output quality |
| RAGAS [5] | End-to-end RAG pipeline | Content quality at ingestion |
| CRAG [16] | RAG system across domains | Crawler across website types |

Our benchmark fills a gap: no existing benchmark measures how the **content extraction step** (crawling) affects downstream retrieval quality.

### Design Decisions Summary

| Decision | Recommendation | Rationale |
|----------|---------------|-----------|
| Primary metric | Recall@K | Matches retrieval stage's job (recall, not precision) [4] [16] |
| K values | 5, 10, 20 | Covers no-reranker to full-pipeline scenarios [1] [3] |
| Chunk size | 512 tokens | Benchmark-validated default; most common in production [2] |
| Overlap | 50-100 tokens (10-20%) | Consensus from NVIDIA and FinanceBench studies [2] [11] |
| Embedding model | OpenAI text-embedding-3-small | Widely used, affordable, adequate for relative comparison [10] |
| Query types | Mix of factoid + analytical | Different chunk sizes favor different query types [2] |

---

## References

[1] Anthropic, 2024. Contextual Retrieval. Anthropic Research Blog. Available at: https://www.anthropic.com/news/contextual-retrieval [Accessed April 6, 2026].

[2] NVIDIA, 2024. Finding the Best Chunking Strategy for Accurate AI Responses. NVIDIA Developer Blog. Available at: https://developer.nvidia.com/blog/finding-the-best-chunking-strategy-for-accurate-ai-responses/ [Accessed April 6, 2026].

[3] LlamaIndex, 2025. Building Performant RAG for Production. LlamaIndex Documentation. Available at: https://developers.llamaindex.ai/python/framework/optimizing/production_rag/ [Accessed April 6, 2026].

[4] Pinecone, 2024. Rerankers and Two-Stage Retrieval. Pinecone Learning Center. Available at: https://www.pinecone.io/learn/series/rag/rerankers/ [Accessed April 6, 2026].

[5] RAGAS, 2025. Available Metrics. RAGAS Documentation. Available at: https://docs.ragas.io/en/stable/concepts/metrics/available_metrics/ [Accessed April 6, 2026].

[6] Weaviate, 2024. Retrieval Evaluation Metrics. Weaviate Blog. Available at: https://weaviate.io/blog/retrieval-evaluation-metrics [Accessed April 6, 2026].

[7] Fröbe, M. et al., 2024. RAGBench: Explainable Benchmark for Retrieval-Augmented Generation Systems. arXiv preprint. Available at: https://arxiv.org/abs/2407.11005 [Accessed April 6, 2026].

[8] Salemi, A. and Zamani, H., 2025. Redefining Retrieval Evaluation Metrics in the Era of LLMs. arXiv preprint. Available at: https://arxiv.org/html/2510.21440v1 [Accessed April 6, 2026].

[9] Ailog, 2025. Best Embedding Models 2025: Complete Comparison Guide. Ailog Blog. Available at: https://app.ailog.fr/en/blog/guides/choosing-embedding-models [Accessed April 6, 2026].

[10] PremAI, 2026. Best Embedding Models for RAG 2026: Ranked by MTEB Score, Cost, and Self-Hosting. PremAI Blog. Available at: https://blog.premai.io/best-embedding-models-for-rag-2026-ranked-by-mteb-score-cost-and-self-hosting/ [Accessed April 6, 2026].

[11] Firecrawl, 2025. Best Chunking Strategies for RAG 2025. Firecrawl Blog. Available at: https://www.firecrawl.dev/blog/best-chunking-strategies-rag [Accessed April 6, 2026].

[12] LangCopilot, 2025. Document Chunking for RAG: A Practical Guide. LangCopilot Blog. Available at: https://langcopilot.com/posts/2025-10-11-document-chunking-for-rag-practical-guide [Accessed April 6, 2026].

[13] MarkTechPost, 2024. Evolution of RAGs: Naive RAG, Advanced RAG, and Modular RAG Architectures. MarkTechPost. Available at: https://www.marktechpost.com/2024/04/01/evolution-of-rags-naive-rag-advanced-rag-and-modular-rag-architectures/ [Accessed April 6, 2026].

[14] Orq.ai, 2025. RAG Architecture Explained 2025. Orq.ai Blog. Available at: https://orq.ai/blog/rag-architecture [Accessed April 6, 2026].

[15] Ailog, 2025. Cross-Encoder Reranking Improves RAG Accuracy by 40%. Ailog Blog. Available at: https://app.ailog.fr/en/blog/news/reranking-cross-encoders-study [Accessed April 6, 2026].

[16] GetMaxim, 2025. Complete Guide to RAG Evaluation: Metrics, Methods, and Best Practices for 2025. GetMaxim Articles. Available at: https://www.getmaxim.ai/articles/complete-guide-to-rag-evaluation-metrics-methods-and-best-practices-for-2025/ [Accessed April 6, 2026].

[17] Label Your Data, 2026. RAG Evaluation. Label Your Data Articles. Available at: https://labelyourdata.com/articles/llm-fine-tuning/rag-evaluation [Accessed April 6, 2026].

[18] NVIDIA, 2025. Evaluating Retriever for Enterprise-Grade RAG. NVIDIA Developer Blog. Available at: https://developer.nvidia.com/blog/evaluating-retriever-for-enterprise-grade-rag/ [Accessed April 6, 2026].

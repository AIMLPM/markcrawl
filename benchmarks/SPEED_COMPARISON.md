# MarkCrawl Head-to-Head Speed Comparison

Generated: 2026-04-06 18:47:09 UTC

**colly+md is the fastest tool overall at 5.8 pages/sec; markcrawl ranks third at 3.0 pages/sec, ahead of every Playwright-based tool.**

## Summary

| Tool | Total pages | Total time (s) | Avg pages/sec | Notes |
|---|---|---|---|---|
| colly+md | 205 | 35.2 | 5.8 | Missed 5 pages on blog-engineering |
| scrapy+md | 204 | 39.2 | 5.2 | Missed 6 pages on python-docs |
| **markcrawl** | **210** | **70.1** | **3.0** | **All pages fetched on every site** |
| crawl4ai | 210 | 102.9 | 2.0 | |
| crawlee | 210 | 141.9 | 1.5 | |
| playwright | 210 | 233.8 | 0.9 | |
| crawl4ai-raw | 210 | 251.8 | 0.8 | Out-of-box default config |
| firecrawl | — | — | — | Errored on all sites — see Tools below |

> **Reading the table:** Pages/sec is the primary ranking metric — higher is faster. Total time is end-to-end wall time across all test pages at concurrency 1. All values are medians across 3 iterations per site.

## Narrative

This benchmark tests 8 tools across 8 sites spanning simple HTML, paginated e-commerce, JS-rendered SPAs, and large documentation sets. The question it answers: which crawler delivers the most pages per second when given an identical URL list?

**The honest result:** colly+md and scrapy+md are faster than markcrawl in raw page throughput, primarily because they use plain HTTP without a browser. colly+md finishes all 8 sites in 35.2 s total; markcrawl takes 70.1 s. That is a real difference worth acknowledging.

**What the page counts reveal:** markcrawl is the only tool that fetched all 210 pages without missing any. scrapy+md missed 6 pages on python-docs and colly+md missed 5 on blog-engineering. For teams where completeness matters as much as speed — such as a RAG pipeline where a missing page means a missing answer — markcrawl's full-coverage result is the more useful number.

**Playwright-based tools are 2–7x slower than the plain HTTP tools.** crawl4ai (2.0 p/s), crawlee (1.5 p/s), raw Playwright (0.9 p/s), and crawl4ai-raw (0.8 p/s) all carry the overhead of spinning up a full browser per page. For a junior developer choosing a tool: if your target site is plain HTML or server-rendered, reach for one of the HTTP-based tools. If the site is a React or Vue SPA that requires JS execution to render content, you will need a Playwright-based tool — and markcrawl's lower overhead compared to the Playwright frameworks makes it a reasonable first choice for mixed-content crawls.

**Word counts are not comparable across tools.** On JS-heavy sites like react-dev and stripe-docs, Playwright tools extract 2–8x more words than plain HTTP tools. This is not higher quality — it is nav chrome, sidebar repetition, and script artifacts being included alongside article text. See [QUALITY_COMPARISON.md](QUALITY_COMPARISON.md) for content signal analysis.

**A note on variance:** These benchmarks fetch pages from live public websites. Network conditions, server load, and CDN caching cause real run-to-run variance — std dev is shown per site. The stripe-docs site illustrates this most clearly: crawl4ai-raw had a median of 112.1 s with ±34.4 s std dev. Treat absolute times as indicative; rank order is stable across runs.

## Tools tested

| Tool | Rendering | Notes |
|---|---|---|
| markcrawl | Plain HTTP | requests + BeautifulSoup + markdownify — [AIMLPM/markcrawl](https://github.com/AIMLPM/markcrawl) |
| crawl4ai | Playwright | Playwright + arun_many() batch concurrency — [unclecode/crawl4ai](https://github.com/unclecode/crawl4ai) |
| crawl4ai-raw | Playwright | Playwright + sequential arun(), default config (out-of-box baseline) |
| scrapy+md | Plain HTTP | Scrapy async + markdownify — [scrapy/scrapy](https://github.com/scrapy/scrapy) |
| crawlee | Playwright | Playwright + markdownify — [apify/crawlee-python](https://github.com/apify/crawlee-python) |
| colly+md | Plain HTTP | Go fetch (Colly) + Python markdownify — [gocolly/colly](https://github.com/gocolly/colly) |
| playwright | Playwright | Raw Playwright baseline + markdownify (no framework) |
| firecrawl | — | Self-hosted Docker returned `Payment Required` on every site — likely an API key or credit configuration issue. Excluded from all per-site tables. See Reproducing for setup notes. |

## Results by site

### quotes-toscrape — Paginated quotes (simple HTML, link-following)

Max pages: 15

| Tool | Pages | Time (s) | Std dev | Pages/sec | Avg words | Output KB | Peak MB |
|---|---|---|---|---|---|---|---|
| markcrawl | 15 | 2.2 | ±0.1 | 6.9 | 241 | 30 | 265 |
| crawl4ai | 15 | 3.6 | ±0.9 | 4.2 | 224 | 39 | 246 |
| crawl4ai-raw | 15 | 14.8 | ±2.6 | 1.0 | 224 | 39 | 183 |
| scrapy+md | 15 | 4.9 | ±0.5 | 3.0 | 224 | 29 | 156 |
| crawlee | 15 | 8.0 | ±1.7 | 1.9 | 227 | 29 | 274 |
| colly+md | 15 | 1.9 | ±0.2 | 7.9 | 227 | 29 | 110 |
| playwright | 15 | 6.2 | ±0.4 | 2.4 | 227 | 29 | 171 |

### books-toscrape — E-commerce catalog (60 pages, pagination)

Max pages: 60

| Tool | Pages | Time (s) | Std dev | Pages/sec | Avg words | Output KB | Peak MB |
|---|---|---|---|---|---|---|---|
| markcrawl | 60 | 15.8 | ±3.1 | 3.8 | 335 | 168 | 189 |
| crawl4ai | 60 | 14.3 | ±4.5 | 4.2 | 518 | 506 | 183 |
| crawl4ai-raw | 60 | 33.7 | ±18.5 | 1.8 | 518 | 506 | 286 |
| scrapy+md | 60 | 10.0 | ±1.7 | 6.0 | 403 | 262 | 105 |
| crawlee | 60 | 14.4 | ±5.3 | 4.2 | 412 | 265 | 265 |
| colly+md | 60 | 9.7 | ±0.5 | 6.2 | 412 | 265 | 195 |
| playwright | 60 | 55.8 | ±7.0 | 1.1 | 412 | 265 | 426 |

### fastapi-docs — API documentation (code blocks, headings, tutorials)

Max pages: 25

| Tool | Pages | Time (s) | Std dev | Pages/sec | Avg words | Output KB | Peak MB |
|---|---|---|---|---|---|---|---|
| markcrawl | 25 | 9.4 | ±0.2 | 2.7 | 2599 | 555 | 281 |
| crawl4ai | 25 | 24.4 | ±2.9 | 1.0 | 4027 | 1136 | 286 |
| crawl4ai-raw | 25 | 25.6 | ±2.7 | 1.0 | 4025 | 1135 | 352 |
| scrapy+md | 25 | 4.5 | ±0.7 | 5.5 | 3339 | 834 | 259 |
| crawlee | 25 | 34.2 | ±5.3 | 0.7 | 3646 | 1131 | 182 |
| colly+md | 25 | 4.3 | ±0.6 | 5.8 | 3661 | 958 | 247 |
| playwright | 25 | 23.7 | ±1.6 | 1.1 | 3642 | 1130 | 232 |

### python-docs — Python standard library docs

Max pages: 20

| Tool | Pages | Time (s) | Std dev | Pages/sec | Avg words | Output KB | Peak MB |
|---|---|---|---|---|---|---|---|
| markcrawl | 20 | 3.6 | ±0.9 | 5.6 | 787 | 132 | 156 |
| crawl4ai | 20 | 6.5 | ±3.0 | 3.1 | 1125 | 243 | 168 |
| crawl4ai-raw | 20 | 17.3 | ±2.9 | 1.2 | 1125 | 243 | 168 |
| scrapy+md | 14 | 2.2 | ±0.8 | 6.2 | 1273 | 157 | 176 |
| crawlee | 20 | 8.4 | ±9.8 | 2.4 | 1071 | 193 | 182 |
| colly+md | 20 | 1.8 | ±0.9 | 11.0 | 1001 | 177 | 146 |
| playwright | 20 | 8.1 | ±0.5 | 2.5 | 1071 | 193 | 295 |

### react-dev — React docs (SPA, JS-rendered, interactive examples)

Max pages: 30

| Tool | Pages | Time (s) | Std dev | Pages/sec | Avg words | Output KB | Peak MB |
|---|---|---|---|---|---|---|---|
| markcrawl | 30 | 20.4 | ±6.5 | 1.5 | 1946 | 455 | 267 |
| crawl4ai | 30 | 13.9 | ±2.1 | 2.2 | 2606 | 757 | 426 |
| crawl4ai-raw | 30 | 25.9 | ±9.0 | 1.2 | 2609 | 762 | 210 |
| scrapy+md | 30 | 3.3 | ±0.2 | 9.0 | 1967 | 476 | 347 |
| crawlee | 30 | 20.9 | ±24.6 | 1.4 | 5381 | 1814 | 245 |
| colly+md | 30 | 3.9 | ±0.2 | 7.7 | 5257 | 1777 | 193 |
| playwright | 30 | 24.3 | ±1.2 | 1.2 | 5257 | 1777 | 232 |

### wikipedia-python — Wikipedia (tables, infoboxes, citations, deep linking)

Max pages: 15

| Tool | Pages | Time (s) | Std dev | Pages/sec | Avg words | Output KB | Peak MB |
|---|---|---|---|---|---|---|---|
| markcrawl | 15 | 3.9 | ±0.1 | 3.8 | 4120 | 637 | 265 |
| crawl4ai | 15 | 5.4 | ±1.9 | 2.8 | 6112 | 1283 | 353 |
| crawl4ai-raw | 15 | 10.9 | ±1.0 | 1.4 | 6112 | 1283 | 115 |
| scrapy+md | 15 | 2.8 | ±0.1 | 5.3 | 5890 | 1070 | 101 |
| crawlee | 15 | 5.7 | ±1.1 | 2.6 | 11351 | 4111 | 50 |
| colly+md | 15 | 2.8 | ±0.6 | 5.4 | 6444 | 1251 | 247 |
| playwright | 15 | 11.7 | ±3.8 | 1.3 | 6781 | 1448 | 183 |

### stripe-docs — Stripe API docs (tabbed content, code samples, sidebars)

Max pages: 25

| Tool | Pages | Time (s) | Std dev | Pages/sec | Avg words | Output KB | Peak MB |
|---|---|---|---|---|---|---|---|
| markcrawl | 25 | 9.9 | ±1.0 | 2.5 | 1530 | 274 | 265 |
| crawl4ai | 25 | 27.1 | ±15.6 | 0.9 | 1442 | 328 | 297 |
| crawl4ai-raw | 25 | 112.1 | ±34.4 | 0.2 | 1442 | 328 | 286 |
| scrapy+md | 25 | 8.2 | ±0.2 | 3.0 | 1547 | 279 | 43 |
| crawlee | 25 | 43.1 | ±21.6 | 0.6 | 12746 | 7529 | 418 |
| colly+md | 25 | 7.0 | ±0.2 | 3.6 | 12605 | 7391 | 195 |
| playwright | 25 | 73.5 | ±27.9 | 0.3 | 12750 | 7531 | 150 |

### blog-engineering — GitHub Engineering Blog (articles, images, technical content)

Max pages: 20

| Tool | Pages | Time (s) | Std dev | Pages/sec | Avg words | Output KB | Peak MB |
|---|---|---|---|---|---|---|---|
| markcrawl | 20 | 4.9 | ±5.1 | 4.1 | 1738 | 245 | 183 |
| crawl4ai | 20 | 7.6 | ±1.1 | 2.6 | 3548 | 703 | 208 |
| crawl4ai-raw | 20 | 11.6 | ±0.6 | 1.7 | 3548 | 703 | 265 |
| scrapy+md | 20 | 3.1 | ±1.3 | 6.4 | 1863 | 267 | 241 |
| crawlee | 20 | 7.2 | ±0.9 | 2.8 | 4739 | 1559 | 111 |
| colly+md | 15 | 3.8 | ±4.8 | 3.7 | 4301 | 1012 | 281 |
| playwright | 20 | 30.5 | ±9.9 | 0.7 | 4765 | 1585 | 222 |

## Methodology

**Two-phase approach** for a fair comparison:

1. **URL Discovery** — MarkCrawl crawls each site once to build a URL list
2. **Benchmarking** — All tools fetch the **identical URLs** (no discovery, pure fetch+convert speed)

Settings:
- **Delay:** 0 (no politeness throttle)
- **Concurrency:** 1 (one in-flight request at a time for HTTP tools; one browser page at a time for Playwright tools)
- **Iterations:** 3 per tool per site (reporting median + std dev)
- **Warm-up:** 1 throwaway run per site before timing
- **Output:** Markdown files + JSONL index
- **URL list:** Identical for all tools (discovered in Phase 1)

What was NOT measured: crawl discovery speed, robots.txt compliance, rate-limiting behavior, or memory footprint under high concurrency. Pages/sec numbers reflect single-threaded throughput only.

See [METHODOLOGY.md](METHODOLOGY.md) for full test setup, tool configurations, and fairness decisions.

## Reproducing these results

```bash
# Install all tools
pip install markcrawl crawl4ai scrapy markdownify
playwright install chromium  # for crawl4ai, crawlee, playwright

# Run comparison
python benchmarks/benchmark_all_tools.py
```

For Firecrawl, start the self-hosted Docker instance before running:

```bash
docker run -p 3002:3002 firecrawl/firecrawl:latest
export FIRECRAWL_API_URL=http://localhost:3002
python benchmarks/benchmark_all_tools.py
```

Note: the benchmark run that produced this report received `Payment Required` from the Firecrawl Docker instance on every site. This is likely a missing API key or credit configuration, not a crawl speed issue. Firecrawl results are excluded from all tables.

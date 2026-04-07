# MarkCrawl Head-to-Head Comparison

Generated: 2026-04-06 18:47:09 UTC

## Methodology

**Two-phase approach** for a fair comparison:

1. **URL Discovery** — MarkCrawl crawls each site once to build a URL list
2. **Benchmarking** — All tools fetch the **identical URLs** (no discovery, pure fetch+convert speed)

Settings:
- **Delay:** 0 (no politeness throttle)
- **Concurrency:** 1
- **Iterations:** 3 per tool per site (reporting median + std dev)
- **Warm-up:** 1 throwaway run per site before timing
- **Output:** Markdown files + JSONL index
- **URL list:** Identical for all tools (discovered in Phase 1)

See [METHODOLOGY.md](METHODOLOGY.md) for full methodology.

## Tools tested

| Tool | Available | Notes |
|---|---|---|
| markcrawl | Yes | requests + BeautifulSoup + markdownify — [AIMLPM/markcrawl](https://github.com/AIMLPM/markcrawl) |
| crawl4ai | Yes | Playwright + arun_many() batch concurrency — [unclecode/crawl4ai](https://github.com/unclecode/crawl4ai) |
| crawl4ai-raw | Yes | Playwright + sequential arun(), default config (out-of-box baseline) |
| scrapy+md | Yes | Scrapy async + markdownify — [scrapy/scrapy](https://github.com/scrapy/scrapy) |
| crawlee | Yes | Playwright + markdownify — [apify/crawlee-python](https://github.com/apify/crawlee-python) |
| colly+md | Yes | Go fetch (Colly) + Python markdownify — [gocolly/colly](https://github.com/gocolly/colly) |
| playwright | Yes | Raw Playwright baseline + markdownify (no framework) |
| firecrawl | Yes | Self-hosted Docker — [firecrawl/firecrawl](https://github.com/firecrawl/firecrawl) |

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
| firecrawl | — | — | — | — | — | — | error: Payment Required: Failed to start crawl. Insuffici |

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
| firecrawl | — | — | — | — | — | — | error: Payment Required: Failed to start crawl. Insuffici |

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
| firecrawl | — | — | — | — | — | — | error: Payment Required: Failed to start crawl. Insuffici |

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
| firecrawl | — | — | — | — | — | — | error: Payment Required: Failed to start crawl. Insuffici |

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
| firecrawl | — | — | — | — | — | — | error: Payment Required: Failed to start crawl. Insuffici |

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
| firecrawl | — | — | — | — | — | — | error: Payment Required: Failed to start crawl. Insuffici |

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
| firecrawl | — | — | — | — | — | — | error: Payment Required: Failed to start crawl. Insuffici |

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
| firecrawl | — | — | — | — | — | — | error: Payment Required: Failed to start crawl. Insuffici |

## Overall summary

| Tool | Total pages | Total time (s) | Avg pages/sec | Notes |
|---|---|---|---|---|
| markcrawl | 210 | 70.1 | 3.0 |
| crawl4ai | 210 | 102.9 | 2.0 |
| crawl4ai-raw | 210 | 251.8 | 0.8 |
| scrapy+md | 204 | 39.2 | 5.2 |
| crawlee | 210 | 141.9 | 1.5 |
| colly+md | 205 | 35.2 | 5.8 |
| playwright | 210 | 233.8 | 0.9 |
| firecrawl | — | — | — | *all sites errored* |

> **Note on variance:** These benchmarks fetch pages from live public websites.
> Network conditions, server load, and CDN caching can cause significant
> run-to-run variance (std dev shown per site). For the most reliable comparison,
> run multiple iterations and compare medians.

## Reproducing these results

```bash
# Install all tools
pip install markcrawl crawl4ai scrapy markdownify
playwright install chromium  # for crawl4ai

# Run comparison
python benchmarks/benchmark_all_tools.py
```

For FireCrawl, also run:
```bash
docker run -p 3002:3002 firecrawl/firecrawl:latest
export FIRECRAWL_API_URL=http://localhost:3002
python benchmarks/benchmark_all_tools.py
```

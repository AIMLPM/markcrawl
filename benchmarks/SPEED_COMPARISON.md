# MarkCrawl Head-to-Head Comparison

Generated: 2026-04-06 14:56:12 UTC

## Methodology

**Two-phase approach** for a fair comparison:

1. **URL Discovery** — MarkCrawl crawls each site once to build a URL list
2. **Benchmarking** — All tools fetch the **identical URLs** (no discovery, pure fetch+convert speed)

Settings:
- **Delay:** 0 (no politeness throttle)
- **Concurrency:** 5
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
| markcrawl | 15 | 2.4 | ±0.1 | 6.4 | 204 | 26 | 181 |
| crawl4ai | 15 | 2.7 | ±0.4 | 5.5 | 188 | 33 | 97 |
| crawl4ai-raw | 15 | 6.2 | ±0.2 | 2.4 | 188 | 33 | 213 |
| scrapy+md | 15 | 2.9 | ±0.0 | 5.1 | 188 | 24 | 158 |
| crawlee | 15 | 4.6 | ±2.3 | 3.3 | 191 | 25 | 27 |
| colly+md | 15 | 2.1 | ±0.0 | 7.2 | 191 | 25 | 48 |
| playwright | 15 | 5.1 | ±0.0 | 3.0 | 191 | 25 | 147 |
| firecrawl | 15 | 23.3 | ±5.6 | 0.6 | 83 | 18 | 158 |

### books-toscrape — E-commerce catalog (60 pages, pagination)

Max pages: 60

| Tool | Pages | Time (s) | Std dev | Pages/sec | Avg words | Output KB | Peak MB |
|---|---|---|---|---|---|---|---|
| markcrawl | 60 | 9.0 | ±0.2 | 6.6 | 333 | 168 | 134 |
| crawl4ai | 60 | 7.4 | ±0.3 | 8.2 | 511 | 502 | 163 |
| crawl4ai-raw | 60 | 23.0 | ±0.8 | 2.6 | 511 | 502 | 83 |
| scrapy+md | 60 | 8.4 | ±0.3 | 7.2 | 400 | 260 | 30 |
| crawlee | 60 | 15.5 | ±0.6 | 3.9 | 408 | 262 | 28 |
| colly+md | 60 | 7.3 | ±0.1 | 8.3 | 408 | 263 | 127 |
| playwright | 60 | 59.7 | ±3.7 | 1.0 | 408 | 262 | 128 |
| firecrawl | 60 | 38.0 | ±40.6 | 1.6 | 505 | 306 | 49 |

### fastapi-docs — API documentation (code blocks, headings, tutorials)

Max pages: 25

| Tool | Pages | Time (s) | Std dev | Pages/sec | Avg words | Output KB | Peak MB |
|---|---|---|---|---|---|---|---|
| markcrawl | 25 | 5.8 | ±0.1 | 4.3 | 2487 | 602 | 238 |
| crawl4ai | 25 | 19.5 | ±3.2 | 1.3 | 3991 | 1252 | 254 |
| crawl4ai-raw | 25 | 21.4 | ±0.8 | 1.2 | 3989 | 1252 | 161 |
| scrapy+md | 25 | 3.7 | ±0.2 | 6.7 | 3258 | 903 | 38 |
| crawlee | 25 | 17.6 | ±0.7 | 1.4 | 3580 | 1230 | 33 |
| colly+md | 25 | 3.8 | ±0.6 | 6.6 | 3581 | 1027 | 200 |
| playwright | 25 | 16.6 | ±0.5 | 1.5 | 3563 | 1228 | 199 |
| firecrawl | 25 | 30.3 | ±8.5 | 0.8 | 1795 | 439 | 52 |

### python-docs — Python standard library docs

Max pages: 20

| Tool | Pages | Time (s) | Std dev | Pages/sec | Avg words | Output KB | Peak MB |
|---|---|---|---|---|---|---|---|
| markcrawl | 20 | 2.8 | ±0.1 | 7.2 | 2349 | 584 | 205 |
| crawl4ai | 20 | 3.8 | ±0.1 | 5.3 | 2709 | 870 | 276 |
| crawl4ai-raw | 20 | 8.1 | ±0.4 | 2.5 | 2709 | 870 | 158 |
| scrapy+md | 16 | 2.2 | ±0.1 | 7.1 | 3112 | 616 | 40 |
| crawlee | 20 | 4.1 | ±0.1 | 4.8 | 2654 | 650 | 36 |
| colly+md | 20 | 1.6 | ±0.5 | 12.3 | 2571 | 631 | 197 |
| playwright | 20 | 7.4 | ±0.1 | 2.7 | 2654 | 650 | 169 |
| firecrawl | 20 | 30.5 | ±22.9 | 0.7 | 7709 | 1477 | 68 |

## Overall summary

| Tool | Total pages | Total time (s) | Avg pages/sec | Notes |
|---|---|---|---|---|
| markcrawl | 120 | 20.0 | 6.0 |
| crawl4ai | 120 | 33.4 | 3.6 |
| crawl4ai-raw | 120 | 58.7 | 2.0 |
| scrapy+md | 116 | 17.3 | 6.7 |
| crawlee | 120 | 41.8 | 2.9 |
| colly+md | 120 | 14.8 | 8.1 |
| playwright | 120 | 88.7 | 1.4 |
| firecrawl | 120 | 122.1 | 1.0 |

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

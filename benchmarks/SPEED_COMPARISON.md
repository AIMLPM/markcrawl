# MarkCrawl Head-to-Head Comparison

Generated: 2026-04-05 13:43:36 UTC

## Methodology

**Two-phase approach** for a fair comparison:

1. **URL Discovery** — MarkCrawl crawls each site once to build a URL list
2. **Benchmarking** — All tools fetch the **identical URLs** (no discovery, pure fetch+convert speed)

Settings:
- **Delay:** 0 (no politeness throttle)
- **Concurrency:** 1 (sequential, single-thread comparison)
- **Iterations:** 3 per tool per site (reporting median + std dev)
- **Warm-up:** 1 throwaway run per site before timing
- **Output:** Markdown files + JSONL index
- **URL list:** Identical for all tools (discovered in Phase 1)

See [METHODOLOGY.md](METHODOLOGY.md) for full methodology.

## Tools tested

| Tool | Available | Notes |
|---|---|---|
| markcrawl | Yes | requests + BeautifulSoup + markdownify — [AIMLPM/markcrawl](https://github.com/AIMLPM/markcrawl) |
| crawl4ai | Yes | Playwright + built-in extraction — [unclecode/crawl4ai](https://github.com/unclecode/crawl4ai) |
| scrapy+md | Yes | Scrapy async + markdownify — [scrapy/scrapy](https://github.com/scrapy/scrapy) |
| crawlee | Yes | Playwright + markdownify — [apify/crawlee-python](https://github.com/apify/crawlee-python) |
| colly+md | Yes | Go fetch (Colly) + Python markdownify — [gocolly/colly](https://github.com/gocolly/colly) |
| playwright | Yes | Raw Playwright baseline + markdownify (no framework) |
| firecrawl | Not installed | Self-hosted Docker — [firecrawl/firecrawl](https://github.com/firecrawl/firecrawl) |

## Results by site

### quotes-toscrape — Paginated quotes (simple HTML, link-following)

Max pages: 15

| Tool | Pages | Time (s) | Std dev | Pages/sec | Avg words | Output KB | Peak MB |
|---|---|---|---|---|---|---|---|
| markcrawl | 15 | 2.2 | ±0.2 | 6.8 | 217 | 29 | 195 |
| crawl4ai | 15 | 5.7 | ±0.0 | 2.6 | 201 | 38 | 167 |
| scrapy+md | 15 | 2.6 | ±0.0 | 5.8 | 201 | 27 | 148 |
| crawlee | — | — | — | — | — | — | error: No module named 'browserforge' |
| colly+md | 15 | 1.9 | ±0.1 | 7.9 | 204 | 28 | 90 |
| playwright | 15 | 20.4 | ±0.3 | 0.7 | 204 | 28 | 49 |

### books-toscrape — E-commerce catalog (60 pages, pagination)

Max pages: 60

| Tool | Pages | Time (s) | Std dev | Pages/sec | Avg words | Output KB | Peak MB |
|---|---|---|---|---|---|---|---|
| markcrawl | 60 | 7.6 | ±0.5 | 7.9 | 319 | 163 | 131 |
| crawl4ai | 60 | 21.2 | ±0.1 | 2.8 | 504 | 500 | 145 |
| scrapy+md | 60 | 8.0 | ±0.8 | 7.5 | 389 | 257 | 58 |
| crawlee | — | — | — | — | — | — | error: No module named 'browserforge' |
| colly+md | 60 | 6.6 | ±0.2 | 9.1 | 397 | 260 | 126 |
| playwright | 60 | 85.3 | ±1.0 | 0.7 | 397 | 260 | 121 |

### fastapi-docs — API documentation (code blocks, headings, tutorials)

Max pages: 25

| Tool | Pages | Time (s) | Std dev | Pages/sec | Avg words | Output KB | Peak MB |
|---|---|---|---|---|---|---|---|
| markcrawl | 25 | 4.5 | ±0.0 | 5.5 | 3578 | 971 | 232 |
| crawl4ai | 25 | 19.9 | ±0.3 | 1.3 | 5222 | 1718 | 161 |
| scrapy+md | 25 | 3.3 | ±0.4 | 7.5 | 4473 | 1295 | 48 |
| crawlee | — | — | — | — | — | — | error: No module named 'browserforge' |
| colly+md | 25 | 3.3 | ±0.2 | 7.6 | 4795 | 1419 | 244 |
| playwright | 0 | 378.4 | ±0.2 | 0.0 | 0 | 0 | 42 |

### python-docs — Python standard library docs

Max pages: 20

| Tool | Pages | Time (s) | Std dev | Pages/sec | Avg words | Output KB | Peak MB |
|---|---|---|---|---|---|---|---|
| markcrawl | 20 | 2.0 | ±0.0 | 10.0 | 2327 | 596 | 196 |
| crawl4ai | 20 | 7.4 | ±0.1 | 2.7 | 2699 | 880 | 152 |
| scrapy+md | 15 | 2.1 | ±0.0 | 7.1 | 3304 | 629 | 50 |
| crawlee | — | — | — | — | — | — | error: No module named 'browserforge' |
| colly+md | 20 | 1.3 | ±0.0 | 15.3 | 2571 | 646 | 249 |
| playwright | 20 | 16.6 | ±0.0 | 1.2 | 2646 | 663 | 155 |

## Overall summary

| Tool | Total pages | Total time (s) | Avg pages/sec |
|---|---|---|---|
| markcrawl | 120 | 16.4 | 7.3 |
| crawl4ai | 120 | 54.2 | 2.2 |
| scrapy+md | 115 | 16.1 | 7.1 |
| crawlee | 0 | 0.0 | 0.0 |
| colly+md | 120 | 13.1 | 9.1 |
| playwright | 95 | 500.6 | 0.2 |

## Reproducing these results

```bash
# Install all tools
pip install markcrawl crawl4ai scrapy markdownify
playwright install chromium  # for crawl4ai

# Run comparison
python benchmarks/run_comparison.py
```

For FireCrawl, also run:
```bash
docker run -p 3002:3002 firecrawl/firecrawl:latest
export FIRECRAWL_API_URL=http://localhost:3002
python benchmarks/run_comparison.py
```

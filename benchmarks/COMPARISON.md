# MarkCrawl Head-to-Head Comparison

Generated: 2026-04-05 03:52:03 UTC

## Methodology

Each tool crawled the same sites with equivalent settings:
- **Delay:** 0 (no politeness throttle)
- **Concurrency:** 1 (sequential, single-thread comparison)
- **Iterations:** 3 per tool per site (reporting median + std dev)
- **Warm-up:** 1 throwaway run per site before timing
- **Output:** Markdown files + JSONL index

See [COMPARISON_PLAN.md](COMPARISON_PLAN.md) for full methodology.

## Tools tested

| Tool | Available | Notes |
|---|---|---|
| markcrawl | Yes | requests + BeautifulSoup + markdownify |
| crawl4ai | Yes | Playwright (headless Chromium) + built-in extraction |
| scrapy+md | Yes | Scrapy async framework + markdownify pipeline |
| firecrawl | Not installed | Self-hosted Docker (set FIRECRAWL_API_URL) |

## Results by site

### quotes-toscrape — Paginated quotes (simple HTML, link-following)

Max pages: 15

| Tool | Pages | Time (s) | Std dev | Pages/sec | Avg words | Output KB | Peak MB |
|---|---|---|---|---|---|---|---|
| markcrawl | 15 | 2.9 | ±0.4 | 5.2 | 269 | 34 | 111 |
| crawl4ai | 15 | 5.6 | ±0.1 | 2.7 | 226 | 38 | 136 |
| scrapy+md | 14 | 2.9 | ±0.2 | 4.9 | 141 | 18 | 131 |

### books-toscrape — E-commerce catalog (60 pages, pagination)

Max pages: 60

| Tool | Pages | Time (s) | Std dev | Pages/sec | Avg words | Output KB | Peak MB |
|---|---|---|---|---|---|---|---|
| markcrawl | 60 | 7.8 | ±0.3 | 7.7 | 314 | 160 | 116 |
| crawl4ai | 60 | 21.1 | ±0.4 | 2.8 | 504 | 534 | 136 |
| scrapy+md | 59 | 7.7 | ±0.2 | 7.7 | 481 | 212 | 38 |

### fastapi-docs — API documentation (code blocks, headings, tutorials)

Max pages: 25

| Tool | Pages | Time (s) | Std dev | Pages/sec | Avg words | Output KB | Peak MB |
|---|---|---|---|---|---|---|---|
| markcrawl | 25 | 3.7 | ±1.3 | 6.8 | 965 | 209 | 144 |
| crawl4ai | 25 | 20.6 | ±0.4 | 1.2 | 5410 | 1839 | 226 |
| scrapy+md | 21 | 3.8 | ±0.2 | 5.7 | 2717 | 652 | 40 |

### python-docs — Python standard library docs

Max pages: 20

| Tool | Pages | Time (s) | Std dev | Pages/sec | Avg words | Output KB | Peak MB |
|---|---|---|---|---|---|---|---|
| markcrawl | 20 | 2.0 | ±0.1 | 9.9 | 1640 | 327 | 153 |
| crawl4ai | 20 | 8.0 | ±0.6 | 2.5 | 4900 | 940 | 181 |
| scrapy+md | 19 | 2.4 | ±0.2 | 8.0 | 3875 | 645 | 41 |

## Overall summary

| Tool | Total pages | Total time (s) | Avg pages/sec |
|---|---|---|---|
| markcrawl | 120 | 16.4 | 7.3 |
| crawl4ai | 120 | 55.3 | 2.2 |
| scrapy+md | 113 | 16.8 | 6.7 |

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

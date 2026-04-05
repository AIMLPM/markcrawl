# MarkCrawl Benchmark Results

Generated: 2026-04-05 02:23:27 UTC

## What this measures

Each benchmark runs the **full MarkCrawl pipeline** end-to-end:

```
1. Discover URLs     — fetch robots.txt, parse sitemap or follow links
2. Fetch pages       — HTTP GET each URL (adaptive throttle, delay=0 base)
3. Clean HTML        — strip <nav>, <footer>, <script>, <style>, cookie banners
4. Convert to Markdown — transform cleaned HTML via markdownify
5. Write .md files   — one file per page with citation header
6. Write JSONL index — append url, title, crawled_at, citation, text per page
```

**Pages/second** includes all six steps — network fetch is typically the
bottleneck, not HTML parsing or Markdown conversion. Benchmarks run with
`delay=0` (adaptive throttle only). MarkCrawl automatically backs off
if the server is slow or returns 429 rate-limit responses.

Source: [`benchmarks/run_benchmarks.py`](run_benchmarks.py)

## Summary

- **Sites tested:** 7
- **Total pages crawled:** 213
- **Total time:** 32.2s
- **Overall pages/second:** 6.61

## Performance

### Small (1-5 pages) — 7 pages in 1.4s (4.8 p/s), 19 KB output

| Site | Description | Pages | Time (s) | Pages/sec | Avg words | Output KB |
|---|---|---|---|---|---|---|
| httpbin | Simple HTTP test service (minimal HTML, 1-2 pages) | 2 | 0.7 | 3.02 | 37 | 2 |
| scrapethissite | Scraping practice site (structured data tables) | 5 | 0.8 | 6.39 | 204 | 17 |

### Medium (15-30 pages) — 46 pages in 7.6s (6.1 p/s), 1117 KB output

| Site | Description | Pages | Time (s) | Pages/sec | Avg words | Output KB |
|---|---|---|---|---|---|---|
| fastapi-docs | FastAPI framework docs (API docs with code examples, tutorials) | 25 | 4.8 | 5.23 | 1740 | 1018 |
| python-docs | Python standard library index + module pages | 6 | 0.5 | 12.27 | 190 | 24 |
| quotes-toscrape | Paginated quotes (tests link-following across 10+ pages) | 15 | 2.3 | 6.47 | 201 | 74 |

### Large (50-100 pages) — 160 pages in 23.2s (6.9 p/s), 869 KB output

| Site | Description | Pages | Time (s) | Pages/sec | Avg words | Output KB |
|---|---|---|---|---|---|---|
| books-toscrape | E-commerce catalog (50+ product pages, pagination, categories) | 60 | 8.2 | 7.30 | 288 | 501 |
| quotes-toscrape-large | Paginated quotes (100 page deep crawl, link-following stress test) | 100 | 15.0 | 6.68 | 178 | 367 |


## Extraction Quality

| Site | Junk detected | Title rate | Citation rate | JSONL complete |
|---|---|---|---|---|
| httpbin | 0 | 50% | 100% | 100% |
| scrapethissite | 0 | 100% | 100% | 100% |
| fastapi-docs | 0 | 100% | 100% | 100% |
| python-docs | 0 | 100% | 100% | 100% |
| quotes-toscrape | 0 | 100% | 100% | 100% |
| books-toscrape | 0 | 100% | 100% | 100% |
| quotes-toscrape-large | 0 | 100% | 100% | 100% |

## Quality Scores

| Metric | Score | Target | Status |
|---|---|---|---|
| Title extraction rate | 93% | >90% | PASS |
| Citation completeness | 100% | 100% | PASS |
| JSONL field completeness | 100% | 100% | PASS |
| Junk in output | 0 matches | 0 | PASS |
| Min pages crawled | all met | all sites | PASS |

## What these metrics mean

- **Pages/sec**: Crawl throughput (higher is better). Affected by network, server response time, and `--delay`.
- **Avg words/page**: Average extracted content size. Very low values may indicate extraction issues.
- **Junk detected**: Count of navigation, footer, script, or cookie text found in extracted Markdown. Should be 0.
- **Title rate**: Percentage of pages where a `<title>` was successfully extracted.
- **Citation rate**: Percentage of JSONL rows with a complete citation string.
- **JSONL complete**: Percentage of JSONL rows with all required fields (url, title, path, crawled_at, citation, tool, text).

## Reproducing these results

```bash
pip install markcrawl
python benchmarks/run_benchmarks.py
```

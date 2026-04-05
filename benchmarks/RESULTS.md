# MarkCrawl Benchmark Results

Generated: 2026-04-05 02:12:45 UTC

## What this measures

Each benchmark runs the **full MarkCrawl pipeline** end-to-end:

```
1. Discover URLs     — fetch robots.txt, parse sitemap or follow links
2. Fetch pages       — HTTP GET each URL (delay=0.3s between requests)
3. Clean HTML        — strip <nav>, <footer>, <script>, <style>, cookie banners
4. Convert to Markdown — transform cleaned HTML via markdownify
5. Write .md files   — one file per page with citation header
6. Write JSONL index — append url, title, crawled_at, citation, text per page
```

**Pages/second** includes all six steps — network fetch is typically the
bottleneck, not HTML parsing or Markdown conversion. The `delay=0.3s`
politeness setting means the theoretical maximum is ~3.3 pages/sec in
sequential mode.

Source: [`benchmarks/run_benchmarks.py`](run_benchmarks.py)

## Summary

- **Sites tested:** 7
- **Total pages crawled:** 213
- **Total time:** 105.5s
- **Overall pages/second:** 2.02

## Performance

### Small (1-5 pages) — 7 pages in 3.6s (1.9 p/s), 19 KB output

| Site | Description | Pages | Time (s) | Pages/sec | Avg words | Output KB |
|---|---|---|---|---|---|---|
| httpbin | Simple HTTP test service (minimal HTML, 1-2 pages) | 2 | 1.2 | 1.61 | 37 | 2 |
| scrapethissite | Scraping practice site (structured data tables) | 5 | 2.4 | 2.12 | 204 | 17 |

### Medium (15-30 pages) — 46 pages in 22.0s (2.1 p/s), 787 KB output

| Site | Description | Pages | Time (s) | Pages/sec | Avg words | Output KB |
|---|---|---|---|---|---|---|
| fastapi-docs | FastAPI framework docs (API docs with code examples, tutorials) | 25 | 11.9 | 2.10 | 1082 | 687 |
| python-docs | Python standard library index + module pages | 6 | 2.8 | 2.18 | 190 | 24 |
| quotes-toscrape | Paginated quotes (tests link-following across 10+ pages) | 15 | 7.3 | 2.04 | 217 | 76 |

### Large (50-100 pages) — 160 pages in 79.9s (2.0 p/s), 848 KB output

| Site | Description | Pages | Time (s) | Pages/sec | Avg words | Output KB |
|---|---|---|---|---|---|---|
| books-toscrape | E-commerce catalog (50+ product pages, pagination, categories) | 60 | 31.0 | 1.93 | 298 | 499 |
| quotes-toscrape-large | Paginated quotes (100 page deep crawl, link-following stress test) | 100 | 48.9 | 2.04 | 160 | 349 |


## Extraction Quality

| Site | Junk detected | Title rate | Citation rate | JSONL complete |
|---|---|---|---|---|
| httpbin | 0 | 50% | 100% | 50% |
| scrapethissite | 0 | 100% | 100% | 100% |
| fastapi-docs | 6 | 100% | 100% | 100% |
| python-docs | 0 | 100% | 100% | 100% |
| quotes-toscrape | 0 | 100% | 100% | 100% |
| books-toscrape | 0 | 100% | 100% | 100% |
| quotes-toscrape-large | 0 | 100% | 100% | 100% |

## Quality Scores

| Metric | Score | Target | Status |
|---|---|---|---|
| Title extraction rate | 93% | >90% | PASS |
| Citation completeness | 100% | 100% | PASS |
| JSONL field completeness | 93% | 100% | NEEDS WORK |
| Junk in output | 6 matches | 0 | NEEDS WORK |
| Min pages crawled | some failed | all sites | NEEDS WORK |

## Junk Detection Details

### fastapi-docs
- <script: 6 match(es)


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

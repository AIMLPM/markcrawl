# MarkCrawl Benchmark Results

Generated: 2026-04-05 01:40:27 UTC

## Summary

- **Sites tested:** 5
- **Total pages crawled:** 20
- **Total time:** 15.2s
- **Overall pages/second:** 1.32

## Performance

| Site | Pages | Time (s) | Pages/sec | Avg words/page |
|---|---|---|---|---|
| httpbin | 2 | 1.6 | 1.28 | 37 |
| python-docs | 3 | 1.8 | 1.65 | 190 |
| scrapethissite | 5 | 4.3 | 1.17 | 681 |
| quotes-toscrape | 5 | 3.4 | 1.48 | 375 |
| books-toscrape | 5 | 4.1 | 1.21 | 363 |

## Extraction Quality

| Site | Junk detected | Title rate | Citation rate | JSONL complete |
|---|---|---|---|---|
| httpbin | 0 | 50% | 100% | 50% |
| python-docs | 0 | 100% | 100% | 100% |
| scrapethissite | 1 | 100% | 100% | 100% |
| quotes-toscrape | 0 | 100% | 100% | 100% |
| books-toscrape | 0 | 100% | 100% | 100% |

## Quality Scores

| Metric | Score | Target | Status |
|---|---|---|---|
| Title extraction rate | 90% | >90% | NEEDS WORK |
| Citation completeness | 100% | 100% | PASS |
| JSONL field completeness | 90% | 100% | NEEDS WORK |
| Junk in output | 1 matches | 0 | NEEDS WORK |
| Min pages crawled | all met | all sites | PASS |

## Junk Detection Details

### scrapethissite
- cookie: 1 match(es)


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

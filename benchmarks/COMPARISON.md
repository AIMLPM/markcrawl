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

## Analysis: why these numbers look the way they do

### Crawl4AI is 3x slower — this is expected and real

Crawl4AI launches a headless Chromium browser for every page. On static HTML sites (which all our test sites are), this is pure overhead — the browser renders JavaScript that doesn't exist, serializes a DOM that `requests.get()` already fetches in milliseconds. This gap would narrow or reverse on JavaScript-heavy SPAs where browser rendering is actually necessary.

**This finding is grounded.** The browser vs. HTTP-client performance difference is well-documented and architectural, not an artifact of our benchmark.

### MarkCrawl vs Scrapy: too close to call

MarkCrawl measured 7.3 pages/sec vs Scrapy's 6.7 pages/sec — a 9% difference. This gap is **not statistically significant** given the variance in our measurements. Before drawing conclusions, consider:

1. **Scrapy's framework overhead.** Scrapy's architecture includes spider instantiation, a middleware chain, signal dispatching, and an item pipeline — all of which add per-request overhead that a direct `requests.get()` call doesn't have. This could account for a small speed difference on short crawls, but would amortize on longer ones.

2. **Page count difference.** MarkCrawl found 120 pages vs Scrapy's 113. Our hybrid mode (sitemap + link-following) discovered more URLs. More pages in the same time category could inflate our pages/sec if the additional pages were small or fast to fetch.

3. **Network variance.** Standard deviations ranged from ±0.0 to ±1.3s across runs. At these margins, a single slow DNS lookup or server hiccup could flip which tool appears faster.

4. **Our Scrapy wrapper may be suboptimal.** We wrote a subprocess-based spider with `markdownify` in the parse callback. A Scrapy expert would likely structure this differently — using item pipelines, enabling async DNS, or tuning Twisted reactor settings. Our wrapper represents "a developer who reads the Scrapy docs and writes a quick spider," not peak Scrapy performance.

**How to validate these hypotheses:**

- **Framework overhead (#1):** Profile both tools with `cProfile` on the same site. Measure time spent in HTTP fetch vs. HTML parsing vs. Markdown conversion vs. framework overhead. If Scrapy spends >10% of time in middleware/signals, the hypothesis holds.
- **Page count effect (#2):** Re-run both tools with identical URL lists (not discovery) — feed the same 60 URLs to both and compare pure processing speed.
- **Network variance (#3):** Run 10+ iterations instead of 3 and check if confidence intervals overlap. If the 95% CI for both tools includes the other's median, the difference is noise.
- **Scrapy wrapper quality (#4):** Ask a Scrapy maintainer or experienced user to write their own spider for this benchmark and compare. Alternatively, benchmark Scrapy with its recommended async settings (`CONCURRENT_REQUESTS=1, REACTOR_THREADPOOL_MAXSIZE=20, DNS_RESOLVER='scrapy.resolver.CachingThreadedResolver'`).

**Our honest conclusion:** MarkCrawl and Scrapy are in the same performance tier (~7 pages/sec sequential) for static sites. The difference is within measurement noise. MarkCrawl's advantage is not speed — it's that you get equivalent throughput with `pip install markcrawl && markcrawl --base URL` instead of writing a spider class, configuring pipelines, and adding Markdown conversion.

### What we claim vs. what we don't

**Grounded claims:**
- "3x faster than browser-based crawlers (Crawl4AI) on static HTML sites"
- "Competitive with Scrapy on throughput, with one-command simplicity"
- "Best page coverage with hybrid sitemap + link-following (120 pages vs Scrapy's 113)"

**Claims we do NOT make:**
- "Fastest Python web crawler" — Scrapy at high concurrency with async would be significantly faster
- "Faster than Scrapy" — the 9% margin is within noise and our Scrapy wrapper may be suboptimal
- "Better extraction quality" — Crawl4AI extracted more words per page (5410 vs 965 on FastAPI docs), which could mean richer content or more boilerplate — manual quality review is needed to determine which

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

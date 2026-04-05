# Head-to-Head Benchmark Plan: MarkCrawl vs Other Crawlers

## Goal

Compare MarkCrawl against FireCrawl, Crawl4AI, and Scrapy on the same sites with equivalent settings, measuring what matters for the "crawl a documentation site for RAG" use case.

## The fairness problem

These tools don't do the same things:

| Feature | MarkCrawl | FireCrawl | Crawl4AI | Scrapy |
|---|---|---|---|---|
| Output format | Markdown + JSONL | Markdown + JSON | Markdown + JSON | Raw HTML (custom pipelines) |
| JS rendering | Optional (Playwright) | Always (headless Chrome) | Always (Playwright) | Optional (plugin) |
| LLM extraction | Built-in | Via API | Built-in | None |
| Deployment | Local CLI | SaaS API or self-hosted | Local Python | Local Python |
| Default delay | 0 (adaptive) | API rate limit | 0 | 0 |

**What's comparable:** Fetch HTML → extract clean Markdown → write to disk. All four can do this.

**What's NOT comparable:** FireCrawl's SaaS latency (network round-trip to their API), Crawl4AI's always-on browser (heavier but handles JS), Scrapy's raw HTML output (no Markdown conversion by default).

## Proposed approach

### What we measure

| Metric | How | Why it matters |
|---|---|---|
| **Pages/second** | Total pages / total wall-clock time | Raw throughput — the headline number |
| **Time to first page** | Time from command start to first output file | Startup overhead matters for small crawls |
| **Markdown quality** | Manual review of 5 pages per site | Does the output look right? Code blocks, headings, lists preserved? |
| **Content accuracy** | Word count of extracted text vs known content | Are we getting the main content or missing sections? |
| **Junk ratio** | Nav/footer/script text in output | How clean is the extraction? |
| **Output size** | Total bytes of Markdown files | Efficient extraction = smaller, cleaner files |
| **Memory usage** | Peak RSS during crawl | Relevant for large crawls |

### What we do NOT measure

- LLM extraction speed (only MarkCrawl and Crawl4AI have this — not apples to apples)
- Supabase upload (unique to MarkCrawl)
- SaaS API response time for FireCrawl (depends on their server load, not the tool)
- Anti-bot bypass capability (none of these tools are designed for this)

### Test sites

Same sites as our current benchmarks, plus one JS-rendered site for the `--render-js` comparison:

| Site | Pages | Why |
|---|---|---|
| http://quotes.toscrape.com | 15 | Simple paginated site — baseline |
| http://books.toscrape.com | 60 | Larger e-commerce catalog |
| https://fastapi.tiangolo.com | 25 | Real API documentation with code blocks |
| https://docs.python.org/3/library/ | 20 | Well-structured standard library docs |
| http://quotes.toscrape.com/js/ | 15 | **JS-rendered version** — same content, requires browser |

### Settings for each tool

All tools run with equivalent settings to isolate processing speed:

```
Delay:        0 (no politeness throttle)
Concurrency:  1 (sequential, to compare single-thread performance)
JS rendering: OFF for static sites, ON for the JS site
Timeout:      15s per request
Max pages:    as listed per site
Output:       Markdown (or closest equivalent)
```

We also run a **concurrency test** at concurrency=5 on the 60-page site to compare parallel performance.

### How to run each tool

**MarkCrawl:**
```bash
markcrawl --base URL --out ./results/markcrawl/SITE --delay 0 --max-pages N --format markdown
```

**Crawl4AI:**
```bash
# Python script using crawl4ai library
from crawl4ai import AsyncWebCrawler
async with AsyncWebCrawler() as crawler:
    result = await crawler.arun(url=URL)
    # Write result.markdown to file
```

**FireCrawl (self-hosted):**
```bash
# Using firecrawl-py SDK against local instance
from firecrawl import FirecrawlApp
app = FirecrawlApp(api_url="http://localhost:3002")
result = app.crawl_url(URL, params={"limit": N, "scrapeOptions": {"formats": ["markdown"]}})
```

**Scrapy:**
```bash
# Custom spider that saves response.text (raw HTML)
# Then pipe through markdownify for fair comparison
scrapy crawl docs_spider -a url=URL -a max_pages=N
```

Note: Scrapy doesn't produce Markdown natively. For a fair comparison, we'll add a `markdownify` pipeline item so the Markdown conversion cost is included.

### Report format

```markdown
## Results: quotes.toscrape.com (15 pages)

| Tool | Time (s) | Pages/sec | Avg words | Junk | Output KB |
|---|---|---|---|---|---|
| MarkCrawl | 2.3 | 6.5 | 176 | 0 | 76 |
| Crawl4AI | X.X | X.X | XXX | X | XX |
| FireCrawl | X.X | X.X | XXX | X | XX |
| Scrapy+md | X.X | X.X | XXX | X | XX |

### Sample output comparison

[Side-by-side Markdown output from each tool for the same page]
```

## What we expect to find

Based on architecture:

- **MarkCrawl should be fastest on static sites** — it uses `requests` (lightweight) while Crawl4AI and FireCrawl spin up headless browsers. Less overhead = faster for HTML-only pages.
- **Crawl4AI should win on JS-rendered sites** — it's built around Playwright and optimized for browser-rendered content.
- **Scrapy should have highest raw throughput** — it's async with minimal per-page overhead, but adding Markdown conversion will slow it down.
- **FireCrawl self-hosted will be slowest** — it runs a full Node.js server + browser per page.
- **Markdown quality should be similar** — all tools use similar HTML-to-Markdown libraries.
- **Junk detection is where MarkCrawl should differentiate** — our `clean_dom_for_content` strips more boilerplate than raw markdownify.

## What we're honest about

If another tool is faster, we say so. The comparison should be factual, not promotional. MarkCrawl's value proposition isn't "fastest crawler" — it's "simplest end-to-end pipeline for the crawl-to-RAG use case."

## Dependencies to install

```bash
# MarkCrawl (already installed)
pip install markcrawl

# Crawl4AI
pip install crawl4ai
playwright install chromium

# FireCrawl (self-hosted via Docker)
docker run -p 3002:3002 firecrawl/firecrawl:latest

# Scrapy + markdownify
pip install scrapy markdownify
```

## Open questions before running

1. **Should we benchmark FireCrawl's SaaS API or self-hosted?** SaaS adds network latency that isn't the tool's fault. Self-hosted is fairer but requires Docker setup.

2. **Should we run multiple iterations?** Network variance can be significant. Running 3x and taking the median would be more rigorous but 3x the time.

3. **Should we include a "time to install" metric?** MarkCrawl's `pip install markcrawl` vs Crawl4AI's `pip install + playwright install` vs FireCrawl's Docker setup. This matters for developer experience but isn't a performance metric.

4. **What about Crawl4AI's built-in LLM features?** They have structured extraction too. Should we compare extraction quality, or just crawl+Markdown?

5. **Should we publish results in the README or as a separate doc?** README could link to a `benchmarks/COMPARISON.md` with full results.

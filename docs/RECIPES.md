# MarkCrawl Recipes

Runnable examples for common crawl + extract + RAG tasks.  All commands use
the public `markcrawl` CLI installed by `pip install markcrawl`.  See
[../README.md](../README.md) for installation and core concepts.

## Table of contents

- [Single-page scrapes](#single-page-scrapes)
  - [Scrape a single page](#scrape-a-single-page)
  - [Scrape a single JS-rendered page](#scrape-a-single-js-rendered-page)
- [Crawling a whole site](#crawling-a-whole-site)
  - [Crawl a docs site](#crawl-a-docs-site)
  - [Crawl a subsection without sitemap wandering](#crawl-a-subsection-without-sitemap-wandering)
  - [Back up a blog before it shuts down](#back-up-a-blog-before-it-shuts-down)
  - [Resume an interrupted crawl](#resume-an-interrupted-crawl)
- [Filtering URLs](#filtering-urls)
  - [Skip junk pages](#skip-junk-pages)
  - [Crawl only specific sections](#crawl-only-specific-sections)
  - [Preview URLs before committing to a long crawl](#preview-urls-before-committing-to-a-long-crawl)
  - [Safe crawl of a job board](#safe-crawl-of-a-job-board)
  - [Smart-sample a large site](#smart-sample-a-large-site)
- [Extraction and dedup](#extraction-and-dedup)
  - [Choose an extraction backend](#choose-an-extraction-backend)
  - [Crawl high-value pages first](#crawl-high-value-pages-first)
  - [Skip pages you've already crawled](#skip-pages-youve-already-crawled)
- [Binary downloads and assets](#binary-downloads-and-assets)
  - [Download images alongside content](#download-images-alongside-content)
  - [Selectively download referenced binaries (PDF, DOCX)](#selectively-download-referenced-binaries-pdf-docx)
  - [Capture page screenshots](#capture-page-screenshots)
- [Multi-site workflows](#multi-site-workflows)
  - [Discover seed URLs and fan out across sites](#discover-seed-urls-and-fan-out-across-sites)
- [End-to-end use cases](#end-to-end-use-cases)
  - [Competitive analysis (crawl 3 competitors, extract pricing)](#competitive-analysis-crawl-3-competitors-extract-pricing)
  - [Docs site → RAG chatbot](#docs-site--rag-chatbot)
  - [API docs → code generation prompt](#api-docs--code-generation-prompt)

---

## Single-page scrapes

### Scrape a single page

```bash
markcrawl --base https://example.com/pricing --no-sitemap --max-pages 1
```

### Scrape a single JS-rendered page

For React, Vue, YouTube, and similar JS-rendered pages:

```bash
markcrawl --base "https://www.youtube.com/@channel/videos" \
  --no-sitemap --max-pages 1 --render-js
# → outputs one .md file with video titles, view counts, and dates
```

For infinite-scroll pages like YouTube, this captures the first ~28 videos from the initial render.

---

## Crawling a whole site

### Crawl a docs site

```bash
markcrawl --base https://docs.example.com --max-pages 500 --concurrency 5 --show-progress
```

### Crawl a subsection without sitemap wandering

Large sites (YouTube, GitHub, etc.) have sitemaps with thousands of unrelated pages.  Use `--no-sitemap` to crawl only from your target URL:

```bash
markcrawl --base https://docs.example.com/guides \
  --no-sitemap --max-pages 50 --show-progress
```

### Back up a blog before it shuts down

```bash
markcrawl --base https://engineering.example.com/blog \
  --no-sitemap --max-pages 1000 --concurrency 5 --out ./blog-archive --show-progress
# → every post saved as clean Markdown with citations and access dates
```

### Resume an interrupted crawl

```bash
markcrawl --base https://docs.example.com --out ./docs --resume --show-progress
```

---

## Filtering URLs

### Skip junk pages

Exclude job listings, login walls, SEO spam:

```bash
markcrawl --base https://example.com \
  --exclude-path "/job/*" --exclude-path "/careers/*" --exclude-path "/login" \
  --max-pages 500 --out ./output --show-progress
```

### Crawl only specific sections

Blog + pricing, ignore everything else:

```bash
markcrawl --base https://example.com \
  --include-path "/blog/*" --include-path "/pricing" \
  --max-pages 200 --out ./output --show-progress
```

### Preview URLs before committing to a long crawl

```bash
markcrawl --base https://example.com --dry-run
# → prints every URL that would be crawled (from sitemap), then exits
# Pipe to wc -l to get a count, or grep to check for junk patterns
markcrawl --base https://example.com --dry-run | wc -l
markcrawl --base https://example.com --dry-run | grep "/job/"
```

### Safe crawl of a job board

Dry-run first, then exclude:

```bash
# Step 1: see what you'd get
markcrawl --base https://tealhq.com --dry-run | head -50
# Step 2: exclude the job listings, crawl just the content pages
markcrawl --base https://tealhq.com \
  --exclude-path "/job/*" --exclude-path "/resume-examples/*" \
  --max-pages 200 --out ./tealhq --show-progress
```

### Smart-sample a large site

For e-commerce, job boards, real estate — sample N pages per templated cluster instead of crawling thousands:

```bash
# Preview the pattern clusters first
markcrawl --base https://bigsite.com --dry-run --smart-sample --show-progress
# Crawl with sampling — 5 pages per templated cluster instead of thousands
markcrawl --base https://bigsite.com --out ./bigsite \
  --smart-sample --sample-size 5 --sample-threshold 20 --show-progress
```

---

## Extraction and dedup

### Choose an extraction backend

```bash
# Default (BS4 + markdownify) — fastest, good for most sites
markcrawl --base https://docs.example.com --out ./output --show-progress

# Ensemble — runs default + trafilatura, picks best per page
markcrawl --base https://docs.example.com --out ./output --extractor ensemble --show-progress

# ReaderLM-v2 — ML-based extraction (uses the bundled torch + transformers stack since v0.10.1)
markcrawl --base https://docs.example.com --out ./output --extractor readerlm --show-progress
```

### Crawl high-value pages first

Link prioritization scores discovered links by predicted content value:

```bash
markcrawl --base https://docs.example.com --out ./docs \
  --prioritize-links --max-pages 100 --show-progress
# Prioritizes content-rich pages (guides, docs) over low-value ones (legal, login)
```

### Skip pages you've already crawled

Cross-crawl dedup — only fetches new or changed pages:

```bash
# First crawl
markcrawl --base https://docs.example.com --out ./docs --show-progress
# Later — only fetches new/changed pages
markcrawl --base https://docs.example.com --out ./docs --cross-dedup --show-progress
```

---

## Binary downloads and assets

### Download images alongside content

Photography blogs, product pages:

```bash
# Crawl a photography blog and save images from the content area
markcrawl --base https://photography-blog.example.com --out ./photos \
  --download-images --max-pages 50 --show-progress
# Output:
#   ./photos/assets/mountain-abc123.jpg
#   ./photos/assets/sunset-def456.png
#   ./photos/post-1__a1b2c3.md  ← Markdown with ![alt](assets/filename.ext) refs
#   ./photos/pages.jsonl         ← index includes "images" array per page

# Adjust minimum image size to skip thumbnails (default: 5000 bytes)
markcrawl --base https://example.com/gallery --out ./gallery \
  --download-images --min-image-size 20000 --show-progress
```

### Selectively download referenced binaries (PDF, DOCX)

*New in v0.11.0.*  Stream-download referenced files with size + content-type guards and a pre-fetch filter callback:

```python
# Crawl an aggregator site and harvest only the resume templates
# (skips privacy policies, ToS, marketing PDFs by anchor + URL signal).
from markcrawl import crawl
from markcrawl.filters import is_likely_resume

result = crawl(
    base_url="https://example.com/templates",
    out_dir="./resumes",
    download_types=["pdf", "docx"],         # opt-in; default None = no downloads
    download_filter=is_likely_resume,       # pre-fetch — rejected URLs never fetched
    download_max_files=200,                 # cap per crawl
    download_max_size_mb=25,                # per-file cap (streaming)
)
print(f"Saved {result.downloads_count} files, {result.downloads_bytes/1e6:.1f} MB")
# Output:
#   ./resumes/downloads/cv-template-1__a1b2c3.pdf
#   ./resumes/downloads/cover-letter-2__d4e5f6.docx
#   ./resumes/pages.jsonl       ← each page's row gets "downloads": [{url, path, ...}]
```

Filters are pure functions of `DownloadCandidate(url, anchor_text, parent_url, parent_title, extension)` — compose your own with the bundled starters:

```python
from markcrawl.filters import is_likely_resume, exclude_legal_boilerplate

# Combine a positive selector with the negative one:
def my_filter(c):
    return is_likely_resume(c) and exclude_legal_boilerplate(c) and "spam" not in c.url

crawl(..., download_types=["pdf"], download_filter=my_filter)
```

Bundled filters (`markcrawl.filters`): `is_likely_resume`, `is_likely_paper`, `exclude_legal_boilerplate`.  Best-effort heuristics, not classifiers — test against your real corpus before relying on them.

### Capture page screenshots

Dashboards, data visualisations, JS-rendered charts:

```bash
# Full-page screenshot of every crawled page (auto-enables --render-js)
markcrawl --base https://steamcharts.com/top --out ./dash \
  --screenshot --max-pages 5 --show-progress
# Output:
#   ./dash/screenshots/top-abc123def456.png   ← 1920-wide full-page PNG
#   ./dash/pages.jsonl                        ← each row gets "screenshot": "screenshots/..."

# Crop to just the dashboard region, JPEG for smaller files, longer wait for slow charts
markcrawl --base https://example.com/dashboards --out ./dash \
  --screenshot --screenshot-selector ".dashboard-main" \
  --screenshot-format jpeg --screenshot-wait-ms 3000 --show-progress
```

The screenshot path loads with `wait_until="load"` and then pauses `--screenshot-wait-ms` (default 1500 ms) before capturing, so canvas/SVG charts have time to render.  (`networkidle` is deliberately avoided — many real sites never idle due to analytics pings.)  Failures are recorded in the JSONL row as `screenshot_error` rather than aborting the crawl.

---

## Multi-site workflows

### Discover seed URLs and fan out across sites

Use a bundled curated seed pack, then crawl every site:

```bash
# Use a bundled curated seed pack, then crawl every site with screenshots
markcrawl discover --pack game-dashboards | \
  markcrawl --seed-file - --out ./dashboards \
    --screenshot --max-pages-per-site 5 --show-progress

# List available packs
markcrawl discover --list-packs
```

Output is organised per-site: `./dashboards/<netloc>/pages.jsonl` plus `screenshots/` under each.  See the full recipe (including a YouTube frame-extraction path using `yt-dlp` + `ffmpeg`) at [recipes/game-dashboards.md](recipes/game-dashboards.md).

---

## End-to-end use cases

### Competitive analysis (crawl 3 competitors, extract pricing)

```bash
markcrawl --base https://competitor-one.com/pricing --no-sitemap --max-pages 1 --out ./comp1
markcrawl --base https://competitor-two.com/pricing --no-sitemap --max-pages 1 --out ./comp2
markcrawl --base https://competitor-three.com/pricing --no-sitemap --max-pages 1 --out ./comp3
markcrawl-extract \
  --jsonl ./comp1/pages.jsonl ./comp2/pages.jsonl ./comp3/pages.jsonl \
  --fields pricing_tiers features free_trial --show-progress
# → extracted.jsonl with structured pricing data across all three
```

### Docs site → RAG chatbot

Full pipeline: crawl, embed, query — **$0 in API charges** thanks to the local embedder default since v0.10.1:

```bash
pip install markcrawl markcrawl[upload]            # base install bundles the local embedder
markcrawl --base https://docs.example.com --out ./docs --max-pages 500 --concurrency 5 --show-progress
markcrawl-upload --jsonl ./docs/pages.jsonl --show-progress
# → pages chunked + embedded locally with mxbai-embed-large-v1, uploaded to Supabase/pgvector
# Wire your chatbot to query the vector table — see docs/SUPABASE.md
```

To use OpenAI embeddings instead (e.g. for parity with an existing index), set `MARKCRAWL_EMBEDDER=text-embedding-3-small` or pass `embedding_model=...` to `upload(...)` / `markcrawl-upload`.

### API docs → code generation prompt

```bash
markcrawl --base https://api.example.com/docs --out ./api-docs --max-pages 200 --show-progress
# Feed the output to an LLM:
# "Using the API documentation in ./api-docs/pages.jsonl, generate a
#  typed Python client with methods for each endpoint."
```

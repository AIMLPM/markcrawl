# MarkCrawl by iD8 🕷️📝
### Turn any webpage or website into clean Markdown for LLM pipelines — in one command.

[![CI](https://github.com/AIMLPM/markcrawl/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/AIMLPM/markcrawl/actions/workflows/ci.yml)
![PyPI Version](https://img.shields.io/pypi/v/markcrawl)
![License](https://img.shields.io/github/license/AIMLPM/markcrawl)
[![markcrawl MCP server](https://glama.ai/mcp/servers/AIMLPM/markcrawl/badges/score.svg)](https://glama.ai/mcp/servers/AIMLPM/markcrawl)

> **Latest:** v0.11.1 (2026-05-12) — default aggregator URL filter. See [What's New](#whats-new) below.

```bash
pip install markcrawl
markcrawl --base https://docs.example.com --out ./output --show-progress
```

MarkCrawl is a crawl-and-structure engine. It fetches one page or crawls an entire website, strips navigation/scripts/boilerplate, and writes clean Markdown files with a structured JSONL index. Every page includes a citation with the access date. No API keys needed.

Everything else — LLM extraction, Supabase upload, MCP server, LangChain tools — is optional and installed separately.

> **Want a hosted API instead of running locally?** [Join the waitlist](https://github.com/AIMLPM/markcrawl/issues/13) — we're gauging interest.

**LLM agents:** Load [docs/LLM_PROMPT.md](docs/LLM_PROMPT.md) as a system prompt to generate correct MarkCrawl commands automatically.

## What's New

Install or upgrade with pip:

```bash
pip install --upgrade markcrawl
pip show markcrawl | grep Version       # confirm the installed version
markcrawl --help | head -1              # confirm the binary on $PATH is the upgraded one
```

If `markcrawl --help` is missing flags you expect (e.g. `--screenshot`, `--seed-file`, `--smart-sample`, `--download-images`), your local install is stale. Run `pip install --upgrade markcrawl` against the same Python that owns the `markcrawl` binary on your `PATH` — `head -1 $(which markcrawl)` shows the right interpreter. PyPI is always the source of truth; see [CHANGELOG.md](CHANGELOG.md) for the full release history.

**v0.11 highlights** ([changelog](CHANGELOG.md#0111--2026-05-12)):

- **Aggregator URL filter** (default, v0.11.1) — rejects mdBook `/print.html` and Hugo `/_print/` pages during crawl-time URL filtering. These bundle the entire docs tree on a single URL and otherwise dominate retrieval rankings on cosine similarity (markcrawl was returning them in 49% of rust-book and 39% of kubernetes-docs top-5 retrieval slots before the fix; competitors return 0%). Opt out via `include_aggregator_pages=True` / `--include-aggregators`.
- **Binary downloads** (v0.11.0) — new `download_types=["pdf", "docx"]` kwarg streams referenced files to `<out_dir>/downloads/` with size + content-type guards. Pre-fetch `download_filter` callback receives URL + anchor text + parent-page context; reject candidates before any HTTP bytes transfer.
- **Local embedder is the default** since v0.10.1 — `pip install markcrawl` ships the full ML stack (torch + transformers + sentence-transformers). Zero API key required for embedding. Override with `MARKCRAWL_EMBEDDER=text-embedding-3-small` or the `embedding_model` kwarg if you want OpenAI back.
- **Tenacity-backed HTTP retry** — full-jitter exponential backoff (2 s → 30 s, 5 attempts) that honors the server's `Retry-After` header on 429s.

> **Where markcrawl stands on the public benchmark, honestly.** The independent [llm-crawler-benchmarks v1.4 leaderboard](https://github.com/AIMLPM/llm-crawler-benchmarks/blob/main/docs/V14_RELEASE_NOTES.md) measures 7 web crawlers on how well their output supports RAG. Markcrawl ranks **1st on cost** ($4,505/yr at 100,000-page scale) but **7th of 7 on answer quality** (3.77/5) and retrieval accuracy (MRR 0.341 vs leaders at 0.76). We're actively working to close that gap on three fronts:
>
> 1. **v0.11.1 (just shipped)** filters out `/print.html` and `/_print/` "whole-book-on-one-page" URLs that were stealing 39–49% of markcrawl's top-5 retrieval slots on documentation sites. Competitors already filter these. Expected MRR improvement: **+0.02 to +0.04** on docs-heavy sites (formal measurement pending the next benchmark cycle).
> 2. **Upcoming releases** improve how markcrawl chooses *which* pages to crawl within its budget — markcrawl's deliberately-narrower crawl strategy (which keeps cost low and signal-to-noise high) is also the main cause of the retrieval gap.
> 3. **The benchmark itself is being improved** — v1.4's test questions were sampled from one specific crawler's output, which structurally penalizes any crawler whose discovery strategy differs from that anchor. The benchmark is being updated so each site's test questions come from the site's own sitemap, independent of any crawler. We expect this fix alone to surface **~5–10%** of markcrawl's current "misses" as actually correct answers at different URLs — work shown in our [audit notes](https://github.com/AIMLPM/llm-crawler-benchmarks/blob/main/docs/V14_RELEASE_NOTES.md).
>
> **Goal for the next benchmark cycle:** move from 7th to mid-pack on retrieval (+0.10 to +0.20 MRR) and answer quality, while keeping the cost-efficiency lead. Honest, measured progress — we publish the numbers either way.

## Quickstart (2 minutes)

```bash
pip install markcrawl
markcrawl --base https://quotes.toscrape.com --out ./demo --max-pages 5 --show-progress
```

Your `./demo` folder now contains:

```text
demo/
├── index__a4f3b2c1d0.md    ← clean Markdown of the page
├── page-2__b7e2d1f0a3.md
├── ...
└── pages.jsonl              ← structured index (one JSON line per page)
```

Each line in `pages.jsonl`:

```json
{
  "url": "https://quotes.toscrape.com/",
  "title": "Quotes to Scrape",
  "crawled_at": "2026-04-04T12:30:00Z",
  "citation": "Quotes to Scrape. quotes.toscrape.com. Available at: https://quotes.toscrape.com/ [Accessed April 04, 2026].",
  "tool": "markcrawl",
  "text": "# Quotes to Scrape\n\n> "The world as we have created it is a process of our thinking..." — Albert Einstein\n\nTags: change, deep-thoughts, thinking, world..."
}
```

**Schema** — every page in `pages.jsonl` has these fields:

| Field | Type | Description |
|---|---|---|
| `url` | string | Original URL fetched. |
| `title` | string | Page title from `<title>` (or first H1 if missing). |
| `crawled_at` | string (ISO 8601) | UTC timestamp of when the page was fetched. |
| `citation` | string | Pre-formatted academic-style citation including access date. |
| `tool` | string | Always `"markcrawl"`. Helps when merging output from multiple crawlers. |
| `text` | string | Clean Markdown content (nav/footer/scripts stripped). |
| `downloads` | array (optional) | Present when `download_types` is set; one entry per saved binary: `{url, path, size_bytes, content_type}`. |
| `images` | array (optional) | Present when `--download-images` is set; lists saved image paths. |
| `screenshot` | string (optional) | Present when `--screenshot` is set; relative path to the PNG/JPEG capture. |

## Common Recipes

Runnable examples for the most common patterns:

- **Single-page scrapes** — including JS-rendered pages (React, Vue, YouTube)
- **Whole-site crawls** — docs, blogs, subsections; resume interrupted runs
- **URL filtering** — `--exclude-path`, `--include-path`, `--dry-run`, smart sampling
- **Extraction backends** — BS4 (default), trafilatura, ensemble, ReaderLM-v2
- **Binary downloads** — images, PDFs (with pre-fetch filter callbacks), DOCX
- **Screenshots** — full-page or cropped, PNG or JPEG
- **End-to-end use cases** — competitive analysis, RAG chatbot, API-docs → code-gen

Full recipes with copy-paste commands and expected outputs: **[docs/RECIPES.md](docs/RECIPES.md)**.

<details>
<summary>How it compares to other crawlers</summary>

Different tools make different tradeoffs. This table summarizes the main differences:

| | MarkCrawl | FireCrawl | Crawl4AI | Scrapy |
|---|---|---|---|---|
| License | MIT | AGPL-3.0 | Apache-2.0 | BSD-3 |
| Install | `pip install markcrawl` | SaaS or self-host | pip + Playwright | pip + framework |
| Output | Markdown + JSONL | Markdown + JSON | Markdown | Custom pipelines |
| JS rendering | Optional (`--render-js`) | Built-in | Built-in | Plugin |
| LLM extraction | Optional add-on | Via API | Built-in | None |
| Best for | Single-site crawl → Markdown | Hosted scraping API | AI-native crawling | Large-scale distributed |

Each tool has strengths: FireCrawl excels as a hosted API, Crawl4AI has deep browser automation, and Scrapy handles massive distributed workloads. MarkCrawl focuses on simple local crawls that produce LLM-ready Markdown.

### Benchmark results (6 tools, May 2026)

**Speed:** scrapy+md is fastest (5.0 pages/sec), markcrawl at 2.7. Playwright-based tools average 1.4-2.1 pages/sec.

**Output cleanliness:** markcrawl has the lowest nav pollution (53 words vs 500+ for others) — less junk in your embeddings.

**RAG answer quality:** markcrawl scores 3.77/5 on answer quality with the fewest chunks (27,193 total, 2.2x fewer than the most), keeping embedding costs low.

| Tool | Chunks/page | Answer Quality (/5) | Annual cost (100K pages, 1K queries/day) |
|---|---|---|---|
| **markcrawl** | **18.7** | **3.77** | **$4,505** |
| scrapy+md | 31.7 | 3.68 | $5,464 |
| crawl4ai | 16.8 | 4.72 | $6,960 |
| colly+md | 40.6 | 4.36 | $7,213 |
| playwright | 39.0 | 4.48 | $7,320 |
| crawlee | 40.5 | 4.68 | $7,467 |

Full benchmark data: [docs/BENCHMARKS.md](docs/BENCHMARKS.md) | Methodology: [llm-crawler-benchmarks](https://github.com/AIMLPM/llm-crawler-benchmarks)
</details>

## Installation

```bash
pip install markcrawl                # Core crawler + chunker + local embedder
                                     # (no API keys required for embedding)
```

Optional add-ons (tasks beyond the crawl-and-embed core):

```bash
pip install markcrawl[js]            # + JavaScript rendering (Playwright)
pip install markcrawl[extract]       # + LLM extraction (OpenAI, Claude, Gemini, Grok)
pip install markcrawl[upload]        # + Supabase upload integration
pip install markcrawl[mcp]           # + MCP server for AI agents
pip install markcrawl[langchain]     # + LangChain tool wrappers
pip install markcrawl[all]           # Everything
```

For Playwright, also run `playwright install chromium` after installing.

**Lean install** (skip the local-embedder dep stack — you'll need an `OPENAI_API_KEY` and pass `embedding_model="text-embedding-3-small"` for any embedding work):

```bash
pip install --no-deps markcrawl beautifulsoup4 lxml markdownify requests certifi tenacity
```

<details>
<summary>Install from source (for development)</summary>

```bash
git clone https://github.com/AIMLPM/markcrawl.git
cd markcrawl
python -m venv .venv
source .venv/bin/activate
pip install -e ".[all]"
```
</details>

## Crawling

```bash
markcrawl --base https://www.example.com --out ./output --show-progress
```

Add flags as needed:

```bash
markcrawl \
  --base https://www.example.com \
  --out ./output \
  --include-subdomains \        # crawl sub.example.com too
  --render-js \                 # render JavaScript (React, Vue, etc.)
  --concurrency 5 \             # fetch 5 pages in parallel
  --proxy http://proxy:8080 \   # route through a proxy
  --max-pages 200 \             # stop after 200 pages
  --format markdown \           # or "text" for plain text
  --show-progress
```

Resume an interrupted crawl:

```bash
markcrawl --base https://www.example.com --out ./output --resume --show-progress
```

### Output

Each page becomes a `.md` file with a citation header:

```markdown
# Getting Started

> URL: https://docs.example.com/getting-started
> Crawled: April 04, 2026
> Citation: Getting Started. docs.example.com. Available at: https://docs.example.com/getting-started [Accessed April 04, 2026].

Welcome to the platform. This guide walks you through installation...
```

Navigation, footer, cookie banners, and scripts are stripped. Only the main content remains.

<details>
<summary>All crawler CLI arguments</summary>

| Argument | Description |
|---|---|
| `--base` | Base site URL to crawl |
| `--out` | Output directory |
| `--format` | `markdown` or `text` (default: `markdown`) |
| `--show-progress` | Print progress and crawl events |
| `--render-js` | Render JavaScript with Playwright before extracting |
| `--concurrency` | Pages to fetch in parallel (default: `1`) |
| `--proxy` | HTTP/HTTPS proxy URL |
| `--resume` | Resume from saved state |
| `--include-subdomains` | Include subdomains under the base domain |
| `--max-pages` | Max pages to save; `0` = unlimited (default: `500`) |
| `--delay` | Minimum delay between requests in seconds (default: `0`, adaptive throttle adjusts automatically) |
| `--timeout` | Per-request timeout in seconds (default: `15`) |
| `--min-words` | Skip pages with fewer words (default: `20`) |
| `--user-agent` | Override the default user agent |
| `--use-sitemap` / `--no-sitemap` | Enable/disable sitemap discovery. Use `--no-sitemap` when you want to scrape a specific page or subsection — without it, large sites (YouTube, GitHub) may discover thousands of unrelated pages via their sitemap |
| `--exclude-path` | Glob pattern to exclude URL paths (e.g. `'/job/*'`). Can be repeated |
| `--include-path` | Glob pattern to include URL paths (e.g. `'/blog/*'`). Only matching paths are crawled. Can be repeated |
| `--dry-run` | Discover URLs (via sitemap/links) and print them without fetching content |
| `--smart-sample` | Auto-detect templated URL patterns and sample from large clusters instead of crawling every page |
| `--sample-size` | Pages to sample per templated cluster (default: `5`, used with `--smart-sample`) |
| `--sample-threshold` | Clusters larger than this are sampled (default: `20`, used with `--smart-sample`) |
| `--auto-resume` | Automatically resume if saved state exists, otherwise start fresh |
| `--cross-dedup` | Skip pages already seen in previous crawls to the same output directory |
| `--prioritize-links` | Score discovered links by predicted content yield — crawl high-value pages first |
| `--extractor` | Content extraction backend: `default`, `trafilatura`, `ensemble`, or `readerlm` |
| `--download-images` | Download images from the content area to `assets/` and use local paths in Markdown |
| `--min-image-size` | Minimum image file size in bytes to keep (default: `5000`). Smaller images are skipped |
| `--i18n-filter` | Skip URLs under locale path segments (`/fr/`, `/de-DE/`, `/zh-Hans/`, ...) — generic, no per-domain config |
| `--title-at-top` | Prepend `# {title}` to the `text` field of every JSONL row when not already present — top-MRR RAG recipe |
</details>

## Optional: structured extraction

If you need structured data (not just text), the extraction add-on uses an LLM to pull specific fields from each page.

```bash
pip install markcrawl[extract]

markcrawl-extract \
  --jsonl ./output/pages.jsonl \
  --fields company_name pricing features \
  --show-progress
```

Auto-discover fields across multiple crawled sites:

```bash
markcrawl-extract \
  --jsonl ./comp1/pages.jsonl ./comp2/pages.jsonl ./comp3/pages.jsonl \
  --auto-fields \
  --context "competitor pricing analysis" \
  --show-progress
```

Supports OpenAI, Anthropic (Claude), Google Gemini, and xAI (Grok) via `--provider`.

<details>
<summary>Extraction details</summary>

### Provider and model selection

```bash
markcrawl-extract --jsonl ... --fields pricing --provider openai         # default
markcrawl-extract --jsonl ... --fields pricing --provider anthropic      # Claude
markcrawl-extract --jsonl ... --fields pricing --provider gemini         # Gemini
markcrawl-extract --jsonl ... --fields pricing --provider grok           # Grok
markcrawl-extract --jsonl ... --fields pricing --model gpt-4o           # override model
```

| Provider | API key env var | Default model |
|---|---|---|
| OpenAI | `OPENAI_API_KEY` | `gpt-4o-mini` |
| Anthropic | `ANTHROPIC_API_KEY` | `claude-sonnet-4-20250514` |
| Google Gemini | `GEMINI_API_KEY` | `gemini-2.0-flash` |
| xAI (Grok) | `XAI_API_KEY` | `grok-3-mini-fast` |

### All extraction CLI arguments

| Argument | Description |
|---|---|
| `--jsonl` | Path(s) to `pages.jsonl` — pass multiple for cross-site analysis |
| `--fields` | Field names to extract (space-separated) |
| `--auto-fields` | Auto-discover fields by sampling pages |
| `--context` | Describe your goal for auto-discovery |
| `--sample-size` | Pages to sample for auto-discovery (default: `3`) |
| `--provider` | `openai`, `anthropic`, `gemini`, or `grok` |
| `--model` | Override the default model |
| `--output` | Output path (default: `extracted.jsonl`) |
| `--delay` | Delay between LLM calls in seconds (default: `0.25`) |
| `--show-progress` | Print progress |

### Output format

Extracted rows include LLM attribution:

```json
{
  "url": "https://competitor.com/pricing",
  "citation": "Pricing. competitor.com. Available at: ... [Accessed April 04, 2026].",
  "pricing_tiers": "Starter ($29/mo), Pro ($99/mo), Enterprise (contact sales)",
  "extracted_by": "gpt-4o-mini (openai)",
  "extraction_note": "Field values were extracted by an LLM and may be interpreted, not verbatim."
}
```
</details>

## Optional: Supabase vector search (RAG)

Chunk pages, generate embeddings, and upload to Supabase with pgvector:

```bash
pip install markcrawl[upload]

markcrawl --base https://docs.example.com --out ./output --show-progress
markcrawl-upload --jsonl ./output/pages.jsonl --show-progress
```

Requires `SUPABASE_URL`, `SUPABASE_KEY`, and `OPENAI_API_KEY`. See **[docs/SUPABASE.md](docs/SUPABASE.md)** for table setup, query examples, and recommendations.

## Optional: agent integrations

MarkCrawl includes integrations for AI agents. Each is an optional add-on.

<details>
<summary>MCP Server (Claude Desktop, Cursor, Windsurf)</summary>

```bash
pip install markcrawl[mcp]
```

```json
{
  "mcpServers": {
    "markcrawl": {
      "command": "python",
      "args": ["-m", "markcrawl.mcp_server"]
    }
  }
}
```

Tools: `crawl_site`, `list_pages`, `read_page`, `search_pages`, `extract_data`
</details>

<details>
<summary>LangChain Tool</summary>

```bash
pip install markcrawl[langchain]
```

```python
from markcrawl.langchain import all_tools
from langchain_openai import ChatOpenAI
from langchain.agents import initialize_agent, AgentType

agent = initialize_agent(tools=all_tools, llm=ChatOpenAI(model="gpt-4o-mini"),
                         agent=AgentType.STRUCTURED_CHAT_ZERO_SHOT_REACT_DESCRIPTION)
agent.run("Crawl docs.example.com and summarize their auth guide")
```
</details>

<details>
<summary>OpenClaw Skill (WhatsApp, Telegram, Slack)</summary>

```bash
npx clawhub install markcrawl-skill
```

See [AIMLPM/markcrawl-clawhub-skill](https://github.com/AIMLPM/markcrawl-clawhub-skill).
</details>

<details>
<summary>LLM assistant prompt</summary>

Copy the system prompt from **[docs/LLM_PROMPT.md](docs/LLM_PROMPT.md)** into any LLM to get an assistant that generates correct MarkCrawl commands.
</details>

## When NOT to use MarkCrawl

- **Sites behind login/auth** — no cookie or session support
- **Aggressive bot protection** (Cloudflare, Akamai) — no anti-bot evasion
- **Millions of pages** — designed for hundreds to low thousands; use Scrapy for scale
- **PDF content** — HTML only (PDF support is on the roadmap)
- **JavaScript SPAs** — add `markcrawl[js]` and use `--render-js` for React/Vue/Angular
- **Infinite-scroll pages** — `--render-js` renders the initial page load but does not scroll; you'll get the first screenful of content (e.g., ~28 of 82 YouTube videos). For complete listings, combine with the platform's API or RSS feed (e.g., YouTube's `/feeds/videos.xml?channel_id=...`)

## Architecture

MarkCrawl is a web crawler. The optional layers (extraction, upload, agents) are separate add-ons that work with the crawler's output.

```text
CORE (free, no API keys)              OPTIONAL ADD-ONS
┌──────────────────────────┐
│ 1. Discover URLs         │          markcrawl[extract]  — LLM field extraction
│    (sitemap or links)    │          markcrawl[upload]   — Supabase/pgvector RAG
│ 2. Fetch & clean HTML    │          markcrawl[js]       — Playwright JS rendering
│ 3. Write Markdown + JSONL│          markcrawl[mcp]      — MCP server for agents
│    + auto-citation       │          markcrawl[langchain] — LangChain tools
└──────────────────────────┘
```

For internals, see **[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)**.

## Extending MarkCrawl

```python
from markcrawl import crawl

result = crawl("https://example.com", out_dir="./output")
print(f"Saved {result.pages_saved} pages")
```

```python
# Process output in your own pipeline
import json
with open(result.index_file) as f:
    for line in f:
        page = json.loads(line)
        your_db.insert(page)  # Pinecone, Weaviate, Elasticsearch, etc.
```

```python
# Use individual components
from markcrawl import chunk_text
from markcrawl.extract import LLMClient, extract_fields
```

See **[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)** for the full module map and extensibility guide.

## Cost

The core crawler is free. Two optional features have API costs:

| Feature | Cost | When |
|---|---|---|
| Structured extraction | ~$0.01-0.03 per page | `markcrawl-extract` |
| Supabase upload | ~$0.0001 per page | `markcrawl-upload` |

## Setting up API keys

Only needed for extraction and upload. The core crawler requires no keys.

```bash
# .env — in your working directory
OPENAI_API_KEY="sk-..."           # extraction (--provider openai) + upload
ANTHROPIC_API_KEY="sk-ant-..."    # extraction (--provider anthropic)
GEMINI_API_KEY="AI..."            # extraction (--provider gemini)
XAI_API_KEY="xai-..."             # extraction (--provider grok)
SUPABASE_URL="https://..."        # upload
SUPABASE_KEY="eyJ..."             # upload (service-role key)
```

```bash
source .env
```

<details>
<summary>Project structure</summary>

```text
.
├── README.md
├── LICENSE
├── PRIVACY.md
├── SECURITY.md
├── CONTRIBUTING.md
├── CODE_OF_CONDUCT.md
├── Dockerfile
├── Makefile
├── glama.json
├── pyproject.toml
├── requirements.txt
├── .github/
│   ├── pull_request_template.md
│   └── workflows/
│       ├── ci.yml
│       └── publish.yml
├── docs/
│   ├── ARCHITECTURE.md
│   ├── LLM_PROMPT.md
│   ├── MCP_SUBMISSION.md
│   ├── RAG_RETRIEVAL_RESEARCH.md
│   └── SUPABASE.md
├── tests/
│   ├── __init__.py
│   ├── test_chunker.py
│   ├── test_core.py
│   ├── test_extract.py
│   └── test_upload.py
└── markcrawl/
    ├── __init__.py
    ├── cli.py
    ├── core.py               # orchestrator
    ├── fetch.py              # HTTP/Playwright fetching
    ├── robots.py             # robots.txt parsing
    ├── throttle.py           # adaptive rate limiting
    ├── state.py              # crawl state & resume
    ├── urls.py               # URL normalization & filtering
    ├── extract_content.py    # HTML → Markdown conversion
    ├── dedup.py              # cross-crawl deduplication
    ├── link_scorer.py        # link prioritization
    ├── chunker.py
    ├── exceptions.py
    ├── utils.py
    ├── extract.py            # LLM field extraction
    ├── extract_cli.py
    ├── upload.py
    ├── upload_cli.py
    ├── langchain.py
    └── mcp_server.py
```
</details>

## Roadmap

- [ ] Canonical URL support
- [ ] PDF support
- [ ] Authenticated crawling
- [ ] Multi-provider embeddings

<details>
<summary>Shipped features</summary>

- `pip install markcrawl` on PyPI
- 200 automated tests + GitHub Actions CI (Python 3.10-3.13) + ruff linting
- Markdown and plain text output with auto-citation
- Sitemap-first crawling with robots.txt compliance
- Text chunking with configurable overlap + semantic chunking
- Supabase/pgvector upload for RAG
- JavaScript rendering via Playwright
- Concurrent fetching and proxy support
- Resume interrupted crawls + auto-resume
- LLM extraction (OpenAI, Claude, Gemini, Grok) with auto-field discovery
- MCP server, LangChain tools, OpenClaw skill
- Image alt text preservation
- Python API (`result.pages`)
- Page-type extraction and content-region heuristics
- Multiple extraction backends (default, trafilatura, ensemble, ReaderLM-v2)
- Cross-crawl deduplication (`--cross-dedup`)
- Link prioritization by predicted content yield (`--prioritize-links`)
- Smart sampling of templated URL clusters (`--smart-sample`)
- URL path filtering (`--include-path`, `--exclude-path`) and dry-run preview
</details>

## Project info

- **Contributing** — see [CONTRIBUTING.md](CONTRIBUTING.md). If you used an LLM to generate code, include the prompt in your PR.
- **Security** — see [SECURITY.md](SECURITY.md) for the disclosure policy.
- **Privacy** — MarkCrawl runs locally. No telemetry, no analytics, no data sent anywhere. See [PRIVACY.md](PRIVACY.md).
- **License** — MIT.  See [LICENSE](LICENSE).

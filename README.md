# Website Crawler for AI / RAG Ingestion

A lightweight Python website crawler that extracts clean Markdown or plain text from websites for AI ingestion, RAG pipelines, search indexing, and documentation archiving.

This project starts with a sitemap when available, respects `robots.txt`, keeps crawling in-scope, and writes both page files and a `pages.jsonl` index for downstream processing.

## Why this exists

A lot of crawlers are either too heavyweight for small ingestion jobs or too focused on broad web scraping. This project is intentionally simple:

- crawl a single site or subdomain set
- extract readable content instead of raw HTML
- produce output that is easy to load into embeddings, vector stores, or search pipelines
- stay understandable and hackable for contributors

## Features

- Sitemap-first crawling
- `robots.txt` checks
- Optional subdomain support
- Markdown or plain text output
- Progress logging with a single CLI flag
- Retry and backoff support for transient errors
- Safe filenames with URL hashing
- JSONL index for ingestion workflows
- Basic content cleanup for nav / footer / utility elements

## Project structure

```text
.
├── README.md
├── LICENSE
├── .gitignore
├── requirements.txt
├── CONTRIBUTING.md
├── CODE_OF_CONDUCT.md
├── SECURITY.md
└── webcrawler/
    ├── __init__.py
    ├── cli.py
    └── core.py
```

## Installation

### Option 1: Run locally

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Option 2: Install as a local package

```bash
pip install -e .
```

## Usage

### Basic crawl

```bash
python -m webcrawler.cli \
  --base https://www.WEBSITE-TO-CRAWL.com/ \
  --out ./output \
  --format markdown
```

### Show progress output

```bash
python -m webcrawler.cli \
  --base https://www.WEBSITE-TO-CRAWL.com/ \
  --out ./output \
  --format markdown \
  --show-progress
```

### Include subdomains

```bash
python -m webcrawler.cli \
  --base https://www.WEBSITE-TO-CRAWL.com/ \
  --out ./output \
  --include-subdomains
```

### Plain text output

```bash
python -m webcrawler.cli \
  --base https://www.WEBSITE-TO-CRAWL.com/ \
  --out ./output \
  --format text
```

## CLI arguments

| Argument | Description |
|---|---|
| `--base` | Base site URL to crawl |
| `--out` | Output directory |
| `--use-sitemap` | Use sitemap(s) when available |
| `--delay` | Delay between requests in seconds |
| `--timeout` | Per-request timeout in seconds |
| `--max-pages` | Maximum number of pages to save; `0` means unlimited |
| `--include-subdomains` | Include subdomains under the base domain |
| `--format` | `markdown` or `text` |
| `--show-progress` | Print progress and crawl events |
| `--min-words` | Skip pages with very little content |
| `--user-agent` | Override the default user agent |

## Output

For each page, the crawler writes:

1. a `.md` or `.txt` file with extracted content
2. a `pages.jsonl` index row for downstream ingestion

Example JSONL row:

```json
{
  "url": "https://www.WEBSITE-TO-CRAWL.com/page",
  "title": "Page Title",
  "path": "page__abc123def0.md",
  "text": "Extracted content..."
}
```

Example output tree:

```text
output/
├── index__6dcd4ce23d.md
├── about__9c1185a5c5.md
├── docs-getting-started__0cc175b9c0.md
└── pages.jsonl
```

## Good fit for

- RAG ingestion
- knowledge base extraction
- internal site archiving
- documentation indexing
- competitor or market research on public pages

## Not currently designed for

- authenticated crawling
- JavaScript-heavy sites that require browser rendering
- PDF extraction
- highly parallel distributed crawling
- anti-bot evasion

## Open-source roadmap

- [ ] Package publishing
- [ ] Automated tests
- [ ] GitHub Actions CI
- [ ] Canonical URL support
- [ ] Duplicate-content detection
- [ ] Optional chunking for embeddings
- [ ] PDF support
- [ ] Browser-rendered page mode

## Legal and ethical use

Use this tool responsibly.

- Respect `robots.txt`, site terms, and rate limits.
- Only crawl content you are authorized to access.
- Do not use this project to evade access controls or scrape private content.
- You are responsible for complying with the target site's policies and applicable laws.

## Contributing

Please read [CONTRIBUTING.md](CONTRIBUTING.md) before opening a pull request.

## Security

If you discover a security issue, please follow the instructions in [SECURITY.md](SECURITY.md).

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE).

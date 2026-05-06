---
spec_version: 2
name: Binary downloads (PDF, DOCX, etc.) referenced from crawled pages
status: confidence-reviewed
size: M
date: 2026-05-06
branch: feat/v0.11.0-binary-downloads
depends_on: []
affected_code:
  - markcrawl/binaries.py:NEW
  - markcrawl/filters.py:NEW           # DownloadCandidate + reusable starter filters
  - markcrawl/core.py:30-50           # imports + new module-level constants area
  - markcrawl/core.py:324-360         # CrawlResult dataclass (extend with download fields)
  - markcrawl/core.py:375-470         # CrawlEngine.__init__ (add download kwargs + state)
  - markcrawl/core.py:863-905         # CrawlEngine.discover_links (route binary links)
  - markcrawl/core.py:1126-1170       # CrawlEngine.run (drain download queue per batch)
  - markcrawl/core.py:1218-1310       # AsyncCrawlEngine.__init__ (parity)
  - markcrawl/core.py:1603-1645       # AsyncCrawlEngine.discover_links (parity)
  - markcrawl/core.py:1774-1820       # AsyncCrawlEngine.run (parity)
  - markcrawl/core.py:1978-2180       # public crawl() signature + plumbing
  - markcrawl/core.py:2186-2400       # _crawl_sync signature + engine instantiation
  - markcrawl/core.py:2448-2700       # _crawl_async signature + engine instantiation
  - markcrawl/__init__.py:1-30        # re-export DOWNLOADS_DIR if useful
  - tests/test_v011_binary_downloads.py:NEW
  - bench/local_replica/release_smoke.py:NEW-CASE
  - CHANGELOG.md
  - pyproject.toml:7
  - README.md:NEW-SECTION
constitution_reviewed: false
---

# Binary downloads (PDF, DOCX, etc.) referenced from crawled pages

## Problem Statement

Markcrawl converts HTML to Markdown but silently drops every link to a non-HTML resource (PDF, DOCX, LaTeX, etc.). Many useful crawls reference such files — resume-template aggregators link to `.pdf` and `.docx` downloads, documentation sites link to whitepapers and reference cards, government / academic sites link to forms and papers. Today users who need those binaries must run a second pipeline (manual `curl` of the URLs collected from `pages.jsonl`), which doubles the operational surface and re-implements robots-handling, retry, dedup, and path-safety. CareerGraph is the first external user surfacing this need (resume templates from ATS aggregator sites); the shape applies broadly to any "crawl + selectively download referenced files" use case.

**Out of scope:** (1) format-specific text extraction from binaries — converting PDF/DOCX → Markdown is a separate problem with mature libraries (pypdf, python-docx, mammoth, pandoc) and would either be a sister `markcrawl-docs` package or a v0.12 follow-up. (2) Crawling *inside* downloaded binaries (following links in PDF text). (3) Image downloads — already handled by the existing `download_images=True` path; this spec is for non-image binaries only.

## Solution Summary

Add a `download_types` kwarg to `crawl()` that accepts a list of file extensions or MIME prefixes. When set, links matching the criteria are routed during link discovery to a separate download queue (sibling to the HTML crawl queue), then streamed to disk by a new `download_binary` helper that mirrors the existing `images.download_image` shape but adds streaming, size caps, and per-MIME validation. Downloaded files land in `<out_dir>/downloads/`, and each crawled page's JSONL row gains a `downloads` field listing the binaries discovered on that page (URL, local path, size, MIME type). All existing safety nets (`respect_robots`, `idle_timeout_s`, retry, dedup) apply uniformly to downloads. The default `download_types=None` preserves current behavior for every existing user.

A second new module `markcrawl/filters.py` ships a `DownloadCandidate` dataclass and three reusable best-effort filters (`is_likely_resume`, `is_likely_paper`, `exclude_legal_boilerplate`) for the common "I want PDFs, but not random privacy policies" case. The crawl-time `download_filter` callback is `Callable[[DownloadCandidate], bool]`, receiving URL + anchor text + parent-page metadata so callers can pre-filter at discovery time without ever fetching unwanted files. Markcrawl provides hooks; domain-specific classification ("is this actually a resume?") remains the caller's responsibility — these helpers are starting points, not classifiers. The filter's pre-fetch contract eliminates 90%+ of unwanted PDFs (privacy policies, ToS, marketing whitepapers) before any HTTP byte is transferred.

## Success Criteria

- **SC-1** — **Given** a crawl seed page that links to one PDF and `download_types=["pdf"]`, **When** the crawl runs, **Then** exactly one file with a `.pdf` extension is saved under `<out_dir>/downloads/`, the seed page's JSONL row contains a `downloads` list with one entry, and that entry's `path` matches the saved file.
- **SC-2** — **Given** `download_types=None` (the default), **When** any crawl runs against any site, **Then** no `<out_dir>/downloads/` directory is created and no JSONL row contains a `downloads` field — i.e., zero behavior change vs v0.10.6 for callers who don't set the new flag.
- **SC-3** — **Given** a link whose URL ends in `.pdf` but whose actual response `content-type` is `text/html` (e.g., a 302 to a login wall), **When** `download_types=["pdf"]` is set, **Then** no file is saved, the URL is logged at debug level as `content-type mismatch`, and the JSONL row's `downloads` list omits this URL.
- **SC-4** — **Given** `download_max_files=N` and a crawl that would discover M > N matching binary links, **When** the crawl runs, **Then** exactly N files are saved (not throttled, not retried) and the engine emits one info-level log noting the cap was reached.
- **SC-5** — **Given** `download_max_size_mb=K` and a binary whose stream exceeds K MB, **When** download begins and the cumulative byte count crosses K MB, **Then** the download is aborted, any partial bytes written to disk are removed, and the URL is recorded in `CrawlResult.downloads_size_skipped: List[str]`.
- **SC-6** — **Given** `respect_robots=True` (default) and a robots.txt that disallows the binary URL, **When** the crawl encounters that link, **Then** the binary is not fetched, the existing robots-disallowed log line fires, and `CrawlResult.robots_bypassed_count` does NOT increment. **Given** `respect_robots=False` and the same scenario, **Then** the binary IS fetched and the URL appears in the bypass count exactly once.
- **SC-7** — **Given** the same binary URL referenced from two distinct crawled pages, **When** the crawl runs, **Then** the file is downloaded exactly once, both JSONL rows include a `downloads` entry pointing at the same local path, and `CrawlResult.downloads_count == 1`.
- **SC-8** — **Given** any binary URL, **When** the saved filename is generated, **Then** the path lives strictly inside `<out_dir>/downloads/` (no `..` traversal, no absolute paths, no characters outside `[a-zA-Z0-9._-]`), and a 12-character hash suffix is appended to disambiguate URLs that produce identical basenames.
- **SC-9** — **Given** `download_filter` returning `False` for a `DownloadCandidate` whose URL would otherwise match `download_types`, **When** discovery encounters that URL, **Then** the URL is NOT added to `_to_download`, NOT fetched, and the JSONL row's `downloads` list omits it. The decision happens **pre-fetch** — zero HTTP bytes are transferred for filtered URLs.
- **SC-10** — **Given** `markcrawl.filters.is_likely_resume` is passed as `download_filter` on a page that links to both `cv-template.pdf` (positive anchor "Download CV template") and `privacy-policy.pdf` (negative anchor "Privacy Policy"), **When** the crawl runs with `download_types=["pdf"]`, **Then** `cv-template.pdf` is downloaded and `privacy-policy.pdf` is NOT downloaded. (Validates the starter filter's positive AND negative signal handling end to end.)
- **SC-11** — **Given** a sitemap.xml that lists a `.pdf` URL among regular HTML URLs, **When** the crawl runs with `download_types=["pdf"]`, **Then** the PDF is routed to the download queue (not the HTML crawl queue), and the existing HTML URLs are unaffected. (Closes the sitemap-route fix gap from spec-review G3.)

## Flow

```
crawl(base_url, download_types=["pdf","docx"],
      download_max_files=200, download_max_size_mb=25, ...)
  │
  ▼
discover_links (per crawled page)
  │
  ├─► HTML link & in-scope ────► to_visit (existing path)
  │
  ├─► matches download_types ──► _to_download (NEW queue)
  │                              │
  │                              ▼
  │                       parallel: download_binary(url)
  │                              │
  │                              ├── HEAD OR streaming GET
  │                              ├── verify content-type
  │                              ├── stream with size cap
  │                              ├── if cap exceeded → unlink partial, record in size_skipped
  │                              ├── else write to <out_dir>/downloads/<safe-name>
  │                              └── record metadata
  │                              │
  │                              ▼
  │                       (url, path, size, content_type) → page's downloads list
  │
  └─► out-of-scope or matches neither ──► dropped (existing behavior)

After crawl loop exits:
  _emit_download_summary(engine)  →  "[info] downloaded N files (X.X MB total)
                                      across Y pages; M skipped on size, K on
                                      content-type mismatch"
  CrawlResult populated with downloads_count, downloads_bytes,
  downloads_size_skipped, downloads_type_skipped
```

## Detailed Steps

### DS-1: Module skeleton — `markcrawl/binaries.py`

- [ ] **Status**
  - What: Create new module mirroring `markcrawl/images.py:1-122` shape but tailored for arbitrary binary downloads. Define `DOWNLOADS_DIR = "downloads"`, helpers `safe_binary_filename(url, content_type) -> str`, `match_download_type(url, content_type, types) -> bool`, and the core `download_binary(session, url, downloads_dir, timeout, max_size_bytes, allowed_types) -> Optional[Dict]` returning `{path, size_bytes, content_type}` on success or `None`. Use **streaming** (`session.get(..., stream=True)` or `httpx`'s `iter_bytes()`) — never read full response into memory.
  - Actor: Claude Code (implementer)
  - Input: requests/httpx session, URL, downloads dir, caps, allowed types
  - Output: Dict on success / None on failure / sentinel on size-skip
  - Evidence: _pending_
  - Test: _pending_
  - On failure: bubble exception to caller; caller logs and continues. Partial files MUST be unlinked before returning None (no orphan `.pdf.tmp` left on disk).

### DS-1b: `markcrawl/filters.py` — DownloadCandidate + 3 starter filters

- [ ] **Status**
  - What: New module exposing:
    - `@dataclass DownloadCandidate(url: str, anchor_text: str, parent_url: str, parent_title: str, extension: str)` — passed to user filters at discovery time
    - `is_likely_resume(c: DownloadCandidate) -> bool` — positive signals: "resume", "cv", "curriculum", "template", "sample" in anchor or URL; negative signals: "privacy", "terms", "policy", "legal", "investor"
    - `is_likely_paper(c: DownloadCandidate) -> bool` — positive: "paper", "preprint", "research", "study", "abstract"; negative: same legal/marketing terms
    - `exclude_legal_boilerplate(c: DownloadCandidate) -> bool` — pure negative selector returning True when URL/anchor looks like legal boilerplate; intended to compose with positive filters via `lambda c: positive(c) and exclude_legal_boilerplate(c)`
  - Actor: Claude Code
  - Input: `DownloadCandidate` instance
  - Output: bool (True = include, False = filter out)
  - Evidence: _pending_
  - Test: _pending_
  - On failure: filters are pure functions; no failure mode beyond invalid input. Document that callers can compose: `download_filter=lambda c: is_likely_resume(c) and "spam" not in c.url`.

### DS-2: Engine state — both `CrawlEngine` and `AsyncCrawlEngine` `__init__`

- [ ] **Status**
  - What: Add kwargs `download_types: Optional[List[str]] = None`, `download_max_files: int = 200`, `download_max_size_mb: int = 25`, `download_filter: Optional[Callable[[DownloadCandidate], bool]] = None`. Initialize state: `self._to_download: Deque[Tuple[str, DownloadCandidate]] = deque()` (URL + cached candidate for parent-page rebinding), `self._downloaded_urls: Set[str] = set()`, `self._download_records: List[Dict] = []`, `self._page_downloads: Dict[str, List[Dict]] = {}` (page-URL → list of download records), `self._downloads_size_skipped: List[str] = []`, `self._downloads_type_skipped: List[str] = []`. Skip all of this if `download_types is None`.
  - Actor: Claude Code
  - Input: __init__ kwargs
  - Output: Engine instance with download state
  - Evidence: _pending_
  - Test: _pending_
  - On failure: invalid `download_types` (not a list of strings) → `ValueError` raised at construction. No silent acceptance.

### DS-3: Link routing — `discover_links` in both engines (sync `core.py:863-905`, async `core.py:1603-1645`)

- [ ] **Status**
  - What: Don't break the existing `Set[str]` link-extraction contract. Instead add a sibling public function `extract_link_pairs(html, base_url) -> Set[Tuple[str, str]]` in `markcrawl/extract_content.py` that returns `(anchor_text, url)` tuples. The engine calls it conditionally — only when `self._download_types is not None` — to get anchor text for the download-routing path. The existing `_extract_links_from_soup` and the 3-tuple return shape of `html_to_markdown` etc. stay unchanged (zero risk to the HTML-crawl path). When download routing fires: build a `DownloadCandidate(url, anchor_text, parent_url, parent_title, extension)`, call `self._download_filter(candidate)` if set; if it returns False (or if not allowed by robots), skip silently; otherwise enqueue `(url, candidate)` into `_to_download`. Same-eTLD+1 scope rule: respect existing `include_subdomains` flag (downloads obey same scope rules as HTML, no new flag).
  - Actor: Claude Code
  - Input: crawled page + extracted (anchor, url) pairs
  - Output: links partitioned into HTML queue / download queue / filtered / dropped
  - Evidence: _pending_
  - Test: _pending_
  - On failure: ambiguous link (matches download type AND looks like HTML page e.g. `/docs/foo.html` listed in download_types?) → log warning and prefer HTML path. Default to NOT downloading on ambiguity. Filter raises exception → log warning, treat as filter-rejected (defensive: a buggy filter shouldn't crash the crawl).

### DS-3b: Sitemap-route fix — symmetry with link discovery

- [ ] **Status**
  - What: At the two sitemap-load sites in core.py — sync at the loop near `engine.seeds`/`target_queue.append(u)` (around line 2360-2367) and async at the parallel spot (around line 2580-2585) — when `self._download_types is not None`, partition the sitemap URLs by extension match before the `target_queue.append(u)` loop. Matching URLs go to `_to_download` (with synthesized `DownloadCandidate(url, anchor_text="", parent_url=base_url, parent_title="<sitemap>", extension=...)` since sitemap entries don't carry anchor text). Non-matching URLs follow the existing path. Closes Gap G3 from the spec self-review.
  - Actor: Claude Code
  - Input: sitemap-load URL list
  - Output: HTML URLs to to_visit; binary URLs to _to_download
  - Evidence: _pending_
  - Test: _pending_
  - On failure: same as DS-3 — ambiguous → prefer HTML.

### DS-4: Streaming download with size cap — `binaries.download_binary`

- [ ] **Status**
  - What: Open response with streaming. Validate `content-type` against `allowed_types` BEFORE writing any bytes (skip with `_downloads_type_skipped.append(url)` if mismatch). Write to a `.tmp` path while accumulating bytes; on every chunk check cumulative size; if size exceeds `max_size_bytes`, abort, `os.unlink(tmp_path)`, append URL to size-skipped, return None. On success rename `.tmp` → final path atomically.
  - Actor: Claude Code
  - Input: HTTP session, URL, target dir, caps, allowed types
  - Output: Dict with `{path, size_bytes, content_type}` or None
  - Evidence: _pending_
  - Test: _pending_
  - On failure: connection errors / timeouts → log debug, return None, ensure no partial file left. Disk write errors → log warning, unlink partial, return None. **No silent partial files.**

### DS-5: Run-loop integration — drain `_to_download` queue

- [ ] **Status**
  - What: In `CrawlEngine.run` (sync, `core.py:1126-1170`) and `AsyncCrawlEngine.run` (`core.py:1774-1820`), after each batch of HTML fetches and BEFORE the idle-timeout / scope-broaden checks, drain pending downloads up to `download_max_files - len(_downloaded_urls)`. Sync engine uses ThreadPoolExecutor; async engine uses asyncio.gather with a download semaphore (separate from the HTML semaphore so downloads don't starve HTML fetches). Each successful download appends to `_download_records` AND to the appropriate `_page_downloads[parent_page_url]` list.
  - Actor: Claude Code
  - Input: pending download queue + budget remaining
  - Output: files saved + records populated
  - Evidence: _pending_
  - Test: _pending_
  - On failure: max_files cap reached → drain remaining queue (mark size_skipped/type_skipped where applicable) and emit the `[info] download cap reached` log exactly once. Do not raise.

### DS-6: JSONL row enrichment — `build_jsonl_row` in both engines

- [ ] **Status**
  - What: Add an optional `downloads` field to the JSONL row. When `self._page_downloads.get(url)` is non-empty, include it as a list of `{url, path, size_bytes, content_type}` dicts. When empty or unset, omit the field entirely (don't emit `"downloads": []` — keeps backward compat with downstream parsers).
  - Actor: Claude Code
  - Input: page data + accumulated download records
  - Output: JSONL line with `downloads` field when applicable
  - Evidence: _pending_
  - Test: _pending_
  - On failure: serialization error (path contains non-UTF-8 byte — shouldn't happen given safe_binary_filename, but defensively) → log warning, omit the row's `downloads` field rather than crashing the line.

### DS-7: End-of-crawl summary — `_emit_download_summary`

- [ ] **Status**
  - What: New helper sibling to `_emit_zero_pages_diagnostic` and `_emit_robots_bypass_summary`. Fires only when `download_types is not None`. Reports: total files saved, total bytes, count of size-skipped, count of type-skipped, and count of pages whose JSONL row has a `downloads` field. Format mirrors existing summaries — `[info]` progress line + WARNING-level log when significant skips occurred.
  - Actor: Claude Code
  - Input: engine state at end of crawl
  - Output: progress line + log entry
  - Evidence: _pending_
  - Test: _pending_
  - On failure: no failure modes (pure read of state).

### DS-8: Public API plumbing — `crawl()`, `_crawl_sync`, `_crawl_async`

- [ ] **Status**
  - What: Add the four new kwargs to `crawl()` (`core.py:1978-2180`), thread through `_crawl_sync` (`core.py:2186-2400`) and `_crawl_async` (`core.py:2448-2700`) signatures, pass to engine constructors. Mirror the v0.10.5 / v0.10.6 plumbing pattern exactly (each kwarg appears at four levels: `crawl()` signature → `_crawl_*` signature → engine `__init__` signature → engine state).
  - Actor: Claude Code
  - Input: kwargs from caller
  - Output: engine constructed with download state
  - Evidence: _pending_
  - Test: _pending_
  - On failure: kwarg mis-spelling → Python's TypeError on unknown kwarg, fail-fast. No silent kwarg-swallowing.

### DS-9: CrawlResult fields

- [ ] **Status**
  - What: Add to `CrawlResult` (`core.py:324-360`): `downloads_count: int = 0`, `downloads_bytes: int = 0`, `downloads_size_skipped: List[str] = field(default_factory=list)`, `downloads_type_skipped: List[str] = field(default_factory=list)`. Populate at both return sites (`_crawl_sync` end, `_crawl_async` end) from engine state.
  - Actor: Claude Code
  - Input: engine state at crawl end
  - Output: CrawlResult with populated download fields
  - Evidence: _pending_
  - Test: _pending_
  - On failure: never (additive fields with defaults, no breaking change).

### DS-10: Unit tests — `tests/test_v011_binary_downloads.py`

- [ ] **Status**
  - What: New test file ~25 tests covering each SC + every `On failure` path. Mirror the structure of `tests/test_v0103_resilience.py` and `tests/test_v0106_respect_robots.py`. Mock HTTP responses with controllable content-type / size / status. Include an end-to-end test using `@patch("markcrawl.core.fetch")` that proves a discovered PDF link gets saved to disk and recorded in JSONL.
  - Actor: Claude Code
  - Input: pytest framework + mocks
  - Output: green test suite
  - Evidence: _pending_
  - Test: _pending_
  - On failure: any test failing → fix the implementation, not the test. Tests are the spec made executable.

### DS-11: Smoke harness — DEFERRED to v0.11.1

- [x] **Status** — DEFERRED
  - What: Live-network ATS-template smoke is deferred. Stable target URLs are hard to lock in advance (ATS aggregator structure changes, WAF behavior varies). The e2e mocked-HTTP test in DS-10 covers the regression surface for v0.11.0; a live smoke is release-confidence sugar, not a release blocker. Will add in v0.11.1 once a stable target is identified.
  - Actor: Claude Code
  - Input: n/a (deferred)
  - Output: n/a
  - Evidence: deferred — see DS-10 mocked e2e for regression coverage
  - Test: DS-10 covers
  - On failure: n/a

### DS-12: Documentation + version bump

- [ ] **Status**
  - What: Bump `pyproject.toml:7` to `version = "0.11.0"`. Add CHANGELOG entry. Update README.md with a new "Selectively download referenced binaries" section showing the canonical CareerGraph use case (`download_types=["pdf","docx"]` on an ATS aggregator URL).
  - Actor: Claude Code
  - Input: existing changelog + readme
  - Output: docs reflecting v0.11.0 capability
  - Evidence: _pending_
  - Test: _pending_
  - On failure: stale README example → caught by the smoke harness reproducing the example. README examples must run without modification (lift directly from a working test).

## Edge Cases

- **`.pdf` URL serves `text/html`** (login wall, soft-404, marketing splash). DS-4 catches this via content-type check before writing bytes; URL goes to `downloads_type_skipped`.
- **Binary larger than `max_size_mb`**. DS-4 streams + checks per chunk; partial file unlinked; URL goes to `downloads_size_skipped`. We do NOT fetch a HEAD-only request first because many servers return wrong/missing `Content-Length` headers; the streaming check is authoritative.
- **Same binary URL referenced by N pages**. DS-2 dedups via `_downloaded_urls`; first occurrence triggers download; subsequent occurrences just append the existing record to that page's `_page_downloads[parent_url]`.
- **Cross-subdomain binary**: `jobs.example.com/listing` links to `cdn.example.com/template.pdf`. CONFIGURABLE per Open Question 1 — proposed default: same-eTLD+1 by default, follow `include_subdomains` flag.
- **robots.txt disallows the binary URL** with `respect_robots=True`. The existing `allowed()` check applies uniformly. With `respect_robots=False`, the bypass count increments exactly once per unique URL (DS-2 hooks into the same `_robots_bypassed` set as v0.10.6).
- **Disk full / write error mid-download**. DS-4's `On failure` unlinks any partial; engine continues with remaining downloads. Final `_emit_download_summary` reports the partial completion accurately.
- **`download_types=["pdf"]` AND `download_filter` is set**. Filter runs AFTER extension match — extension narrows the candidate set, filter further refines. Filter callable receives the full URL, returns bool.
- **Content-type with charset suffix** (`application/pdf; charset=binary`). DS-1's `match_download_type` strips parameters before comparing, mirroring how `images.py:71-77` does it for `image/`.
- **Filename collision** — two URLs produce the same `safe_binary_filename` stub. DS-1's hash suffix (12 chars from sha1) makes collision astronomically improbable; if it ever occurs, the second download overwrites — explicit, no defensive renaming chain.
- **Crawl interrupted mid-download** (Ctrl+C, watchdog, OS kill). The `.tmp` rename pattern means partial files have a `.tmp` suffix and won't be confused with completed files on resume; resume should re-attempt the URL.
- **Anchor text contradicts URL**: link text says "Privacy Policy" but URL ends `.pdf` and points at a marketing brochure. With `download_filter=is_likely_resume`, the anchor signal wins (rejected). This is the desired behavior — anchor is the strongest available signal.
- **No anchor text** (e.g., a bare `<a href="x.pdf"></a>` or sitemap entry). `DownloadCandidate.anchor_text` is `""`. Filters must handle empty anchor gracefully — `is_likely_resume` falls back to URL-only matching, which is the v0.10.x same-as-today behavior.
- **Filter raises an exception** (caller bug). Engine logs warning, treats as filter-rejected (skip the URL), continues. Don't let a buggy user filter crash an otherwise-fine crawl.
- **Sitemap entry is a binary URL** (e.g., academic site sitemap lists `paper.pdf` directly). DS-3b routes it to `_to_download` instead of `to_visit`. JSONL row: parent_url is the seed/base URL; parent_title is "<sitemap>".
- **Same eTLD+1, different protocol** (`http://example.com/x.pdf` linked from `https://example.com/page`). Mirrors existing same_scope behavior — protocol is preserved by URL normalization.

## Artifacts / Output

```
out_dir/
├── pages.jsonl          (existing — now with optional `downloads` field per row)
├── <safe-name>.md       (existing — one per crawled HTML page)
├── assets/              (existing — image downloads, when download_images=True)
└── downloads/           (NEW — binary downloads, when download_types is set)
    ├── cv-template-1__abc123def456.pdf
    ├── cover-letter-2__789abc012345.docx
    └── ...
```

| # | Artifact | Description | Consumed by |
|---|----------|-------------|-------------|
| 1 | `out_dir/downloads/<file>` | Saved binary | downstream pipeline (CareerGraph, RAG indexer, etc.) |
| 2 | `pages.jsonl` `downloads` field | Per-page list of binary records | pages.jsonl reader / batch ETL |
| 3 | `CrawlResult.downloads_count` etc. | Aggregate audit fields | calling code, tests, smoke harness |
| 4 | `[info]` progress lines | End-of-crawl summary | operator visibility |

## Data / State Changes

| Entity | Operation | Fields affected | Notes |
|--------|-----------|-----------------|-------|
| `<out_dir>/downloads/` directory | Create on first download | n/a | Created lazily; not present when no downloads |
| `pages.jsonl` row | Append `downloads` field | `downloads: List[Dict]` | Optional — omitted when no downloads on that page |
| Engine state | Mutate in-memory only | several `_download_*` fields | Not persisted across runs (resume support: Open Question 2) |

## Technical Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Match by extension OR content-type? | **Both, sequentially** — extension as a cheap pre-filter to avoid even fetching obviously-irrelevant URLs; content-type as the authoritative check before writing bytes | Cheapest correct version. Mirrors `images.py:71-77` precedent. |
| Stream download or read full body? | **Stream** with per-chunk size accumulation | Default 25 MB cap means a single 100 MB malicious response could OOM a small worker if we read all bytes. Streaming is mandatory. |
| Same-host scope for downloads? | **Default same-eTLD+1; respect existing `include_subdomains` flag** | Matches existing crawl scope rules. Don't invent a new flag — if the user trusts subdomains for crawling, they trust them for downloading. (Closes Open Question 1.) |
| Where do downloads happen — during crawl or post-crawl? | **During crawl, parallel** | Post-crawl would block the JSONL final flush and double the wallclock for users who care about both. Parallel matches `download_images` precedent. |
| Separate semaphore for downloads vs HTML? | **Yes** | Without it, slow downloads starve HTML fetching and inflate idle-timeout false positives. |
| Default cap (max_files=200, max_size=25MB)? | Conservative defaults that handle "resume aggregator" use case and stop short of "ingest a whole file server" | 200 × 25MB = 5GB worst case is fine for a one-shot crawl, problematic if cron'd hourly — caller can opt down for higher cadence. |
| Do we re-rewrite Markdown content to point at local paths (like images do)? | **No** | Image rewriting makes sense because images render inline in Markdown. PDFs/DOCX don't render inline; the link text in the rendered Markdown should keep pointing at the original URL (citation), with the local path recorded only in the JSONL `downloads` field. |
| robots.txt + downloads | Honor uniformly; respect_robots=False bypasses for downloads same as for HTML | One flag, one mental model. |
| Filename safety | sha1[:12] suffix on extracted basename, restricted to `[a-zA-Z0-9._-]`, extension preserved from URL when present (else from content-type, else `.bin`) | Mirrors `safe_image_filename` (`images.py:19-34`). Path-traversal-proof. |
| Filter signature | **`Callable[[DownloadCandidate], bool]`**, not `Callable[[str], bool]`. Candidate carries URL + anchor text + parent-page URL/title + extension. | Anchor text is the highest-leverage pre-fetch signal ("Privacy Policy" vs "Download CV template"). URL alone is not enough to filter signal from noise on real sites. Pre-fetch contract: filter runs at discovery time before any HTTP byte is transferred. |
| Sitemap-discovered binary URLs | Routed to download queue same as link-discovered binaries | Symmetry: sitemap is just structured link discovery. Without this, "why didn't my PDFs download? oh, they're in the sitemap" is a confusing surprise. (Closes spec-review G3.) |
| Resume support for partial downloads | **Clean and re-fetch on resume**; HTTP Range deferred to v0.11.1 if requested | YAGNI. Re-fetch is correct, simple, and 90%+ of users want it. Range support adds significant edge-case surface (server-changed-mid-resume, 200-instead-of-206) for a marginal use case. (Closes Open Question 2.) |
| Launch validation gate | Tag v0.11.0 on green internal verification (tests + smoke). CareerGraph reports issues against v0.11.x patches. | Same posture as every release in the v0.10.x campaign. CareerGraph's option B (50-line script) means they're not blocked on us, so no need to hold the tag. (Closes Open Question 3.) |
| Ship pre-built filters in `markcrawl.filters`? | **Yes — `is_likely_resume`, `is_likely_paper`, `exclude_legal_boilerplate`** | Every user with the same use case shouldn't re-implement obvious patterns. Markcrawl provides hooks AND sensible starting points. Document explicit contract: best-effort heuristics, not classifiers. |

## Cost / Performance

| Operation | Provider | Paid via | Estimated cost |
|-----------|----------|----------|---------------|
| Binary HTTP fetch | Target server | bandwidth | ~25 MB × N files; user's network |
| Disk write | Local filesystem | disk space | up to `max_files × max_size_mb` MB; default 5 GB ceiling |
| No LLM / API calls | n/a | n/a | $0 |

Latency impact on crawl wallclock: each download adds the file's transfer time to the parallel pool. With concurrency=8 and the existing async semaphore, a typical "10 PDFs, 1 MB each" download adds ~3-8 seconds to the crawl. A "200 PDFs, 25 MB each" worst case adds ~10-20 minutes. The `idle_timeout_s` watchdog (v0.10.4) keeps progress events flowing during long downloads via the per-chunk write callback bumping `_last_activity_time`.

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Tool used to bulk-pirate copyrighted content | Medium | High (reputational, legal) | Conservative defaults; same robots-respect path as v0.10.6; CHANGELOG entry explicitly notes user responsibility. Don't ship a CLI flag (`--download-types`) without documentation matching the `respect_robots=False` warning posture. |
| Malicious server feeds enormous file | Low | Medium (disk fill / OOM) | Streaming + size cap is mandatory in DS-4. Tested via SC-5 / DS-4's `On failure`. |
| Slow downloads block crawl progress, idle_timeout fires | Low | Low (graceful exit) | Per-chunk write triggers `_mark_activity()`; v0.10.4 already covers this. |
| Filename collisions overwrite real files | Very Low | Medium (data loss) | sha1[:12] suffix → 1-in-2^48 collision odds per pair. Acceptable. |
| `.tmp` files orphaned on crash | Low | Low (disk debris) | Atomic rename on success; explicit unlink on failure. Resume scan could clean up `*.tmp` (Open Question 2). |
| Cross-host download surprises user | Medium | Low (expected files in unexpected directories) | Default same-eTLD+1; emit info log when first cross-subdomain download fires. |
| Smoke harness depends on third-party site that changes | High | Low (smoke flap, not build break) | Treat ATS template smoke as BLOCKED-tolerant per existing v0.10.5 convention. Don't gate releases on it. |

## Evidence

| ID | Claim | Files | Build | Test Suite | Test File(s) | Result |
|----|-------|-------|-------|------------|--------------|--------|
| V-1 | SC-1 | _pending_ | _pending_ | pytest | _pending_ | _pending_ |
| V-2 | SC-2 | _pending_ | _pending_ | pytest | _pending_ | _pending_ |
| V-3 | SC-3 | _pending_ | _pending_ | pytest | _pending_ | _pending_ |
| V-4 | SC-4 | _pending_ | _pending_ | pytest | _pending_ | _pending_ |
| V-5 | SC-5 | _pending_ | _pending_ | pytest | _pending_ | _pending_ |
| V-6 | SC-6 | _pending_ | _pending_ | pytest | _pending_ | _pending_ |
| V-7 | SC-7 | _pending_ | _pending_ | pytest | _pending_ | _pending_ |
| V-8 | SC-8 | _pending_ | _pending_ | pytest | _pending_ | _pending_ |
| V-9 | DS-1 (binaries.py module) | _pending_ | _pending_ | pytest | _pending_ | _pending_ |
| V-10 | DS-4 (streaming + size cap correctness) | _pending_ | _pending_ | pytest | _pending_ | _pending_ |
| V-11 | DS-5 (run-loop drain ordering) | _pending_ | _pending_ | pytest | _pending_ | _pending_ |
| V-12 | DS-7 (end-of-crawl summary) | _pending_ | _pending_ | pytest | _pending_ | _pending_ |
| V-13 | DS-9 (CrawlResult fields) | _pending_ | _pending_ | pytest | _pending_ | _pending_ |
| V-14 | DS-10 (unit-test green) | _pending_ | _pending_ | pytest | _pending_ | _pending_ |
| V-15 | DS-11 (smoke harness — DEFERRED, see DS-10 e2e for coverage) | n/a | n/a | n/a | n/a | DEFERRED |
| V-16 | SC-9 (filter is pre-fetch — zero bytes for rejected URLs) | _pending_ | _pending_ | pytest | _pending_ | _pending_ |
| V-17 | SC-10 (is_likely_resume positive + negative signal e2e) | _pending_ | _pending_ | pytest | _pending_ | _pending_ |
| V-18 | SC-11 (sitemap binary URLs route to download queue) | _pending_ | _pending_ | pytest | _pending_ | _pending_ |
| V-19 | DS-1b (filters.py module: 3 starter filters + DownloadCandidate) | _pending_ | _pending_ | pytest | _pending_ | _pending_ |
| V-20 | DS-3b (sitemap-route fix) | _pending_ | _pending_ | pytest | _pending_ | _pending_ |

## Open Questions

All resolved during spec review (see Technical Decisions for full text):

1. ~~**Cross-host download default**~~ → **RESOLVED**: respect existing `include_subdomains` flag.
2. ~~**Resume support for downloads**~~ → **RESOLVED**: clean and re-fetch on resume; HTTP Range deferred to v0.11.1.
3. ~~**Launch validation**~~ → **RESOLVED**: tag on green internal verification; CareerGraph reports against patches.

(No remaining blockers. Implementation can begin once `/confidenceBoost` gate passes.)

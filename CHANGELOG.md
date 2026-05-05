# Changelog

All notable changes to MarkCrawl are documented in this file. The format
follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and this
project follows [SemVer](https://semver.org/) once it reaches 1.0.

## [0.10.5] - 2026-05-04

### Added
- **Adaptive scope broadening.** When a crawl exhausts its narrow
  auto-derived scope (e.g. `/docs/concepts/*` from a kubernetes seed)
  with budget remaining, the engine now attempts one-level broadening
  (`/docs/concepts/*` → `/docs/*`) before giving up. URLs filtered
  under the previous scope are stashed and replayed through the
  broader scope. Triggers only when:
  - Scope was auto-derived (user-explicit `include_paths` is
    respected as intent and never mutated).
  - The current scope's leftmost segment is in `_DOCS_HUB_MARKERS`
    (`docs`, `book`, `learn`, `tutorial`, `guide`, `reference`,
    `manual`, `handbook`, `api`, etc.) **or** the seed classifies as
    `docs`/`apiref` by hostname.
  - One-level broadening doesn't land at whole-host (`/*`).
  - Cap of `_DEFAULT_MAX_BROADEN_EVENTS = 2` per crawl.
- **`CrawlResult.scope_history: List[List[str]]`** — sequence of
  scope patterns the crawl traversed. Empty if no scope was set;
  one entry per scope state. Auditable.

### Empirical proof (real network, 2026-05-04)
| Site | v0.10.4 | v0.10.5 | Delta |
|---|---|---|---|
| kubernetes-docs (max=400) | 195/400 | **400/400** | **+105%** |
| rust-book (max=150) | 111 | 111 | unchanged (single-segment guardrail) |
| postgres-docs (max=80) | 80 | 80 | unchanged |

The kubernetes seed `https://kubernetes.io/docs/concepts/` exhausts
its narrow scope at 195 pages; v0.10.5 broadens to `/docs/*`, replays
~200 stashed URLs from `/docs/tasks/`, `/docs/reference/`,
`/docs/setup/`, etc., and fills the full 400 budget — all in 28 s.

Rust-book is **deliberately unchanged**: its Tier 0 single-segment
scope `/book/*` cannot broaden short of whole-host, which the
guardrail blocks. We don't auto-pull `/std/`, `/cargo/`, `/nomicon/`
even though crawl4ai-raw does — those are different publications,
and our scope honors the seed's intent.

### Fixed
- The run loops in `CrawlEngine` and `AsyncCrawlEngine` now attempt
  scope broadening at *both* exit paths (queue empty AND every URL
  in the queue filtered out), not just one.

### Migration
No breaking changes. Behavior preserved exactly when the user passes
`include_paths` explicitly. For default crawls on docs sites,
expect more pages and the same (or better) signal-to-noise — the
broadening guardrail is intentionally tight (docs hub markers only,
no whole-host fallback).

549 tests passing (was 528 on v0.10.4; +21 in
`tests/test_v0105_adaptive_scope.py`).

## [0.10.4] - 2026-05-04

### Fixed
- **Idle timeout now resets on any meaningful progress.** v0.10.3 reset
  the `idle_timeout_s` clock only on `save_page`, which mis-fired on
  bursty crawls where the engine was successfully fetching pages but
  most were being deduped or under `min_words` (e.g.
  huggingface-transformers: ~21 pages saved before the 120 s timer
  fired, vs ~200 reachable). The reset signal is now widened — a
  successful HTTP 2xx response, OR a save, OR a `discover_links` call
  that adds at least one new URL to the queue all bump the activity
  clock. Net effect: the timer now functions as a true deadlock
  detector, not a save-rate guard. Sites that legitimately produce
  pages slowly continue to run; truly idle engines still get killed
  cleanly.

### Added
- `CrawlResult.first_status: Optional[int]` — first observable HTTP
  status. Lets callers distinguish engine bugs from external
  WAF/anti-bot blocks without scraping logs.
- `CrawlResult.stalled: bool` — True when the run was terminated by
  the idle-timeout watchdog rather than running out of work.
- `bench/local_replica/release_smoke.py` — pre-release coverage
  harness. Runs ``crawl()`` against ~4 real sites with per-site
  baselines, treats first_status≥400 + 0 pages as `BLOCKED` (skip,
  not fail). Catches stall-detection regressions, coverage
  regressions, and anti-bot diagnostic regressions in 5-10 min vs
  the 8-hour public benchmark.

### Internal
- Engine field renamed `_last_save_time` → `_last_activity_time`.
- New `_mark_activity()` helper on both `CrawlEngine` and
  `AsyncCrawlEngine` — single source of truth for the timer reset.
- 4xx / 5xx responses do **not** reset the clock (anti-bot loops can
  still be detected).

### Tests
528 passing (was 521 on v0.10.3). New tests in
`tests/test_v0103_resilience.py` cover all five reset paths (2xx,
4xx, 5xx, save, new-link discovery) and the no-op cases.

### Migration
No breaking changes. Public API surface (`idle_timeout_s` kwarg, env
var, default of 120 s) unchanged. Users who set
`MARKCRAWL_IDLE_TIMEOUT_S=300` to work around the v0.10.3 mis-fire can
now drop that override — 120 s is correct again.

## [0.10.3] - 2026-05-04

Three generalizable resilience fixes surfaced by the `llm-crawler-benchmarks`
v1.3 cycle. None are site-specific — each applies to any site exhibiting
the symptom.

### Fixed
- **Partial-write recovery (`pages.jsonl` is now line-buffered).** Both
  `_crawl_sync` and `_crawl_async` open the JSONL with `buffering=1`,
  and `save_page` flushes after every row. A SIGKILL / external
  watchdog termination now leaves a complete, readable JSONL on disk
  instead of an empty file. Previously, rows were buffered in
  user-space Python and lost on subprocess kill.
- **Discovery-exhaustion stall detection (`idle_timeout_s`).** Crawls
  where reachable pages < `max_pages` (e.g. HF docs with ~200
  reachable, max_pages=300) used to spin indefinitely on duplicate /
  out-of-scope link-discovery without producing new saves. The engine
  now tracks `_last_save_time` and terminates gracefully when no new
  page has been saved for `idle_timeout_s` seconds (default 120 s,
  overridable per call or via the `MARKCRAWL_IDLE_TIMEOUT_S` env var;
  set to 0 to disable). Generalizes to any site whose link graph
  yields lots of duplicates relative to fresh content.
- **0-page diagnostic logging.** When a crawl finishes with
  `pages_saved == 0`, the engine surfaces the first observed HTTP
  status so users can distinguish "blocked by 403" (anti-bot) from
  "200 but no extractable content" (JS-rendered or `min_words` too
  high) from "no response at all" (DNS error / unreachable seed).
  Catches the newegg-style anti-bot case generically.

### Added
- `idle_timeout_s` kwarg on the public `crawl()` API plus both
  `CrawlEngine` and `AsyncCrawlEngine` constructors. `None` →
  fall through to the env var, then to `DEFAULT_IDLE_TIMEOUT_S = 120.0`.
- `MARKCRAWL_IDLE_TIMEOUT_S` env var.
- 21 new tests in `tests/test_v0103_resilience.py` covering all three
  fixes (line-buffer guard, idle-timeout firing & disable semantics,
  diagnostic for 200/403/503/no-response, end-to-end 0-page repro).

### Migration
- No breaking changes. Default `idle_timeout_s=120` is generous and
  fires only on genuine stalls; for users intentionally running
  long-blocked crawls (e.g. waiting on a slow render), pass
  `idle_timeout_s=0` or set the env var to `0`.

521 tests passing (was 500 on v0.10.2; +21 for the resilience suite).

## [0.10.2] - 2026-05-03

### Fixed
- **Sitemap pre-enumeration deadline.** Recursive `parse_sitemap_xml`
  / `parse_sitemap_xml_async` (`markcrawl.robots`) and the call sites
  in `markcrawl.core` now share a 60 s wallclock budget for the whole
  sitemap-discovery phase. Retailer-style sitemap-indexes that fan out
  into thousands of locale shards (ikea: 2,113) used to consume 200+ s
  before any page got crawled, tripping the zero-output watchdog in
  benchmark harnesses (`llm-crawler-benchmarks` heartbeat fires at
  120 s with 0 pages saved). Once the deadline fires, the parser
  returns whatever URLs it has collected so far and the crawl
  proceeds normally. Async path uses `asyncio.as_completed` so
  pending child-sitemap tasks are cancelled rather than awaited.
- New `time_budget_s` kwarg on both `parse_sitemap_xml` variants
  (default 60.0) and a 2-test addition in `tests/test_sitemap_parallel.py`
  covering the short-circuit and the no-op default.

### Verified locally
| Site                     | v0.10.1                    | v0.10.2                     |
|--------------------------|----------------------------|-----------------------------|
| ikea                     | 0 pages (heartbeat fired)  | 30 pages saved in 49.7 s    |
| huggingface-transformers | regression on benchmark CI | 30 pages saved in 36.2 s    |

498 tests passing (now 500 with the new sitemap-deadline tests).

## [0.10.1] - 2026-05-03

### Changed
- **Local embedder is now the default.** The full ML stack
  (`torch`, `transformers`, `sentence-transformers`, `sentencepiece`)
  ships in the base `pip install markcrawl` so `chunk_semantic` and
  the bake-off-winning `mixedbread-ai/mxbai-embed-large-v1` embedder
  work out of the box — **zero API cost** for embedding at any scale
  (replaces the previous OpenAI 3-small default at $4,505/yr per 100K
  pages).
- **`markcrawl[ml]` is kept as a no-op alias** for backward compat.
  Existing `pip install markcrawl[ml]` invocations continue to work
  identically.
- **`markcrawl.upload.upload(...)`** picks the embedder via
  `markcrawl.embedder.make_default_embedder()`. Override with
  `embedder=<Embedder>`, `embedding_model="text-embedding-3-small"`
  (or any spec `make_embedder` accepts), or the
  `MARKCRAWL_EMBEDDER` env var. Lean install: `pip install --no-deps
  markcrawl beautifulsoup4 lxml markdownify requests certifi tenacity`
  (factory falls back to OpenAI 3-small).

### Added
- **`markcrawl.embedder.make_default_embedder()`** — returns mxbai
  when sentence-transformers is importable, else OpenAI 3-small.
- **`DEFAULT_EMBEDDER_SPEC = "mixedbread-ai/mxbai-embed-large-v1"`** —
  single source of truth for the production default.

### Migration
- No code changes required for callers using `upload(...)` with
  default kwargs — they automatically pick up the local embedder
  and stop incurring OpenAI charges. To stay on OpenAI, pass
  `embedding_model="text-embedding-3-small"`.

## [0.10.0] - 2026-05-01

### Added
- **Tenacity-backed HTTP retry policy** in the new module `markcrawl.retry`.
  Full-jitter exponential backoff: 5 attempts, 2 s starting delay, 30 s cap.
  Honors the server's `Retry-After` header on 429 responses (clamped to the
  30 s ceiling). Emits one structured INFO log line per retry — `[retry]
  attempt=N status_code=… url=… sleep=Xs elapsed=Ys detail=…`. Applied
  uniformly to both the `httpx` (`_fetch_httpx`, `fetch_async`) and
  `requests` (`_fetch_requests`) code paths so both transports follow the
  same policy.
- **`tests/test_retry.py`** — 36 new unit tests covering header parsing,
  retryable-status detection, the wait strategy, end-to-end retry behavior,
  and policy-constant invariants.
- **CI source-vs-published parity check** at
  `.github/workflows/cli-flag-parity.yml`. Triggers on push to `main` and on
  every `v*` tag. Installs the local source as a wheel, captures `markcrawl
  --help`, force-reinstalls the latest published wheel, captures `--help`
  again, and diffs. Hard-fails on any mismatch when the source version is
  already on PyPI; soft-warns when source is ahead (expected pre-release
  window). Catches the source-vs-PyPI divergence class that produced bug
  fe6f3c39.
- **`tenacity>=8.0,<10.0`** declared in `pyproject.toml` and
  `requirements.txt` install requirements.

### Changed
- **`markcrawl/throttle.py` no longer reacts to 429 responses.** Rate-limit
  backoff is now owned exclusively by the retry layer. `AdaptiveThrottle`
  continues to manage inter-request pacing (response-time proportional and
  `robots.txt` Crawl-delay floor) — both layers now compose cleanly without
  double-waiting. The previous uncapped doubling-from-1 s branch in
  `throttle.update()` (lines 46–50 in 0.9.x) was removed; an explicit
  early-return on 429 keeps the response-time signal clean. Tests updated:
  `tests/test_core.py::test_update_throttle_429_is_ignored` and
  `test_update_throttle_429_does_not_disturb_pacing` codify the new contract.
- **`markcrawl/fetch.py::_build_requests_session` no longer mounts a
  `urllib3.util.Retry` adapter.** Transport-level retry was conflicting with
  the new request-level retry layer; consolidating to the tenacity layer
  removes the double-retry surface and the silent transport-level
  no-jitter behavior.
- **`fetch_async` rewritten** to use `tenacity.AsyncRetrying` via
  `markcrawl.retry.with_retry_async` for a single source of truth on the
  retry policy across sync and async paths.

### Documentation
- **README.md** — new "Installation / Upgrading" section near the top with
  `pip install --upgrade` guidance, an explanation of the stale-install
  failure mode, and `head -1 $(which markcrawl)` as the canonical
  diagnostic for "which Python owns my binary".
- **specs/v3-landscape/** — three design docs from the v3 landscape stage
  (`root-cause-diagnosis.md`, `backoff-strategy-design.md`, `fix-plan.md`)
  document the bug investigation, library comparison, and operator runbook.

### Migration notes for downstream consumers
- No CLI-flag changes — every flag in 0.9.x remains in 0.10.0 with identical
  semantics. The retry behavior change is internal and transparent.
- Anyone subclassing `AdaptiveThrottle` and overriding `update()` should be
  aware that `_backoff_count` is now permanently 0 (kept as a public
  attribute for backward compatibility).
- Library consumers calling `markcrawl.fetch.fetch()` directly will see the
  same return contract: a response object on success / exhausted-soft-fail,
  or `None` when the underlying transport raises a transient error five
  times in a row.

### MRR + cost (Track D + Track B from the speed-recovery campaign, merged into v0.10.0)
- **`chunk_markdown` defaults flipped** to the Track D winner: `min_words=250`,
  `section_overlap_words=40`, `strip_markdown_links=True`. Multi-trial validated
  +14% MRR on `all-MiniLM-L6-v2` (6 trials, all positive) and +15% on OpenAI
  3-small (3 trials, all positive). Halves chunks/page (20.3 → 10.49 in the
  local replica), so the index is also smaller.
- **`markcrawl.embedder`** ships an `Embedder` ABC + `OpenAIEmbedder` +
  `LocalSentenceTransformerEmbedder` (with model-specific instruction
  prefixes for asymmetric retrieval). `make_embedder("…")` accepts string
  specs that route to the right backend. The bake-off across 4 embedders
  on the canonical 11-site pool found `mixedbread-ai/mxbai-embed-large-v1`
  the Pareto winner ($0/yr cost, MRR within ±0.020 of OpenAI 3-small).
- **`markcrawl.retrieval.CrossEncoderReranker`** ships as opt-in
  infrastructure (off by default — failed the +0.030 MRR bar on this
  distribution; lift was concentrated on tutorial-class sites only).

### Local-replica benchmark (11-site canonical pool, Track-D chunks, mxbai embedder)
| Metric                  | v0.9.9-rc1   | v0.10.0       | Δ                |
|-------------------------|-------------:|--------------:|-----------------:|
| Mean MRR                | 0.3461       | **0.3859**    | **+0.040 (+11.5%)** |
| Cost at 50 M pages      | $10,152      | **$0**        | **−$10,152/yr**  |
| Chunks per page         | 20.3         | 10.49         | −48% (smaller index) |

## [0.9.3] - 2026-04-26

Last release before the v3 retry overhaul. See git log for the 0.5.0 → 0.9.3
release history (multi-site discovery, screenshot pipeline, image download,
smart-sample, dry-run, etc.).

[0.10.5]: https://github.com/AIMLPM/markcrawl/releases/tag/v0.10.5
[0.10.4]: https://github.com/AIMLPM/markcrawl/releases/tag/v0.10.4
[0.10.3]: https://github.com/AIMLPM/markcrawl/releases/tag/v0.10.3
[0.10.2]: https://github.com/AIMLPM/markcrawl/releases/tag/v0.10.2
[0.10.1]: https://github.com/AIMLPM/markcrawl/releases/tag/v0.10.1
[0.10.0]: https://github.com/AIMLPM/markcrawl/releases/tag/v0.10.0
[0.9.3]: https://github.com/AIMLPM/markcrawl/releases/tag/v0.9.3

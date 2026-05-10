# Six releases in 72 hours: a v0.10.x → v0.11.0 postmortem

> **TL;DR.** Between 2026-05-03 and 2026-05-06, markcrawl shipped six releases in response to a public benchmark surfacing real-world failure modes, plus one external-user feature request. Each release fixed a generalizable bug or added a generalizable capability with empirical proof. This is the engineering log of that window — what broke, what we shipped, what we learned, and what we deliberately did not ship.

This document is part postmortem, part case study, part argument for how RAG ingestion tooling should evolve in response to evidence rather than vibes.

## The setting

A separate repo, `llm-crawler-benchmarks`, runs an end-to-end pipeline that crawls 11 sites with seven different crawlers, embeds the chunks, runs a fixed query set against each tool's index, and produces an MRR / cost / coverage leaderboard. The bench is independent of markcrawl — same fairness contract for every tool: identical embedder, identical chunker, identical retrieval index. It's the closest thing the RAG-ingestion space has to an objective benchmark.

The v1.3 cycle of that bench produced two failures we had to engage with:

1. **`huggingface-transformers` (max_pages=300)** — markcrawl saved 0 pages on one pass and 21 pages on another, while other crawlers saved 200–300.
2. **`newegg` (max_pages=200)** — markcrawl saved 0 pages with no diagnostic explaining why.

The user-facing complaint distilled to: **"why is markcrawl returning 0 pages without telling me anything?"** That single question forced six successive product fixes, each of which generalizes well past the surface symptom.

---

## v0.10.2 — the sitemap that ate the budget

**Trigger.** `markcrawl/ikea` returned 0 pages, heartbeat stalled at 120 s.

**Diagnosis.** ikea's `sitemap.xml` is a sitemap-*index* pointing at 2,113 locale-specific child sitemaps. The recursive `parse_sitemap_xml` was unbounded — it walked all 2,113 children before any page got crawled. The 120 s zero-output watchdog in the benchmark wrapper killed the process before discovery finished.

**Fix.** A 60 s wallclock budget shared across all sitemap fetches in the discovery phase. New `time_budget_s` kwarg on `parse_sitemap_xml{,_async}`. Async path switched from `asyncio.gather` to `asyncio.as_completed` so pending children get cancelled when the deadline fires.

**Empirical proof.** ikea: 0 → 30 pages saved in 49.7 s (max_pages=30 local test).

**Generalizable lesson.** When discovery is unbounded, give it a wallclock cap. "Eventually we'll be done" is a failure mode dressed as correctness.

---

## v0.10.3 — three resilience fixes from one symptom

**Trigger.** v0.10.2 fixed ikea, but `huggingface-transformers` still failed differently: the crawl ran for 180+ seconds saving pages, then the wrapper killed it, and **`pages.jsonl` on disk was 0 bytes** — even though 200 individual `.md` files were already written. Separately, `newegg` returned 0 pages with no diagnostic.

**Diagnosis (three orthogonal bugs surfaced from the same evidence):**

1. **Partial-write recovery was broken.** `pages.jsonl` was opened with default Python buffering — flushes were every 10 pages. SIGKILL between flushes lost everything in the user-space buffer.
2. **No idle-timeout in the engine itself.** When a crawl was bursty (HF docs links to thousands of internal anchors and translations), the engine kept popping URLs from the queue but rarely produced new saves. Watchdogs killed the run, but the engine had no graceful self-exit.
3. **No diagnostic when `pages_saved == 0`.** newegg returned 0 pages because the first request got a 403 anti-bot response. Markcrawl logged debug info that never reached users.

**Fixes.**
- Open `pages.jsonl` with `buffering=1` (line-buffered). Flush every row, not every 10. SIGKILL now preserves all already-written rows in the OS page cache.
- Engine tracks `_last_save_time`; terminates gracefully when `idle_timeout_s` (default 120 s) elapses with no new saves. Configurable per-call and via `MARKCRAWL_IDLE_TIMEOUT_S` env var.
- New `_emit_zero_pages_diagnostic` that captures the first observed HTTP status and emits a class-aware warning: 4xx/5xx → likely anti-bot block; 200 → likely `min_words` too high or JS-rendered; no response → DNS/unreachable.

**Empirical proof.** ikea unchanged at 200/200. Newegg now logs `Crawl saved 0 pages; first HTTP 403 (likely anti-bot block).` HF still partial — see v0.10.4.

**Generalizable lesson.** One observable failure ("0-byte JSONL") often hides three independent bugs. Diagnostic logging is product-grade work, not chrome.

---

## v0.10.4 — the idle-timer was wrong

**Trigger.** The v0.10.3 idle-timeout fired, but on `huggingface-transformers` it killed the crawl after **21 pages** instead of waiting for the bursty discovery pattern to complete.

**Diagnosis.** v0.10.3 reset the timer only on `save_page`. On HF docs the engine was successfully *fetching* hundreds of pages but most got deduped or under-`min_words` — so `saved_count` stayed flat for stretches longer than 120 s, and the timer mis-fired. Every fetch was forward progress; the timer didn't see it.

**Fix.** Widen the reset signal. The timer now resets on **any meaningful progress event**: a save, OR a successful HTTP 2xx response, OR a `discover_links` call that adds at least one new URL to the queue. 4xx / 5xx still don't reset (anti-bot loops still get caught).

**Empirical proof.** Fresh local HF run, max_pages=200: **21 → 174 pages** (8× lift). The bench confirmed this on a non-rate-limited IP.

**Generalizable lesson.** When you build a deadlock detector, "save" is the *visible* event but "any progress" is the *correct* event. The first version of an instinctive timer is usually wrong; the second resets on a richer signal.

---

## v0.10.5 — the scope was too narrow

**Trigger.** `kubernetes-docs` (max_pages=400) saved 195 pages and stopped. The other tools saved 400.

**Diagnosis.** Markcrawl's `_auto_path_scope_from_seed` derives an `include_paths` pattern from the seed URL. For `kubernetes.io/docs/concepts/`, it scoped the crawl to `/docs/concepts/*` — exactly the seed sub-section, blocking sibling sections like `/docs/tasks/`, `/docs/reference/`, `/docs/setup/`. The 195 pages it found were genuinely all of `/docs/concepts/*`. The remaining 205 were sibling-section pages we filtered out by design.

**Then the harder question.** Are we wrong to be scoping narrowly? Looking at what `crawl4ai-raw` (the leader on coverage) actually saved on each site — extracted from cached benchmark output:

| Site | Their saves | In `/docs/*` | Outside docs |
|---|---|---|---|
| kubernetes-docs | 400 | 378 (94%) | 22 (blog/careers/legal) |
| **HF transformers** | 300 | **3 (1%)** | **297 — `/u/<user>/<model>` cards, `/new-space`, `/chat/...`** |
| react-dev | 500 | 140 in `/learn/*` | 360 (`/reference/*` is docs-relevant; `/blog/*` `/community/*` are not) |
| rust-book | 200 | 113 | 87 (separate Rust books, not "The Rust Book") |

The headline finding: **on HuggingFace, crawl4ai-raw's 300 pages were 99% Hub product UI, not transformers documentation.** Their "100% coverage" includes harvesting model card pages, user profiles, and chat UI. Markcrawl was right to exclude them.

**Fix.** Adaptive scope broadening. When the engine exhausts its narrow scope with budget remaining, it attempts one-level broadening (`/docs/concepts/*` → `/docs/*`) and replays previously filtered URLs through the new scope. Strict guardrails: only when scope was auto-derived (user-explicit `include_paths` is respected); only when the leftmost segment is a known docs-hub marker (`docs`, `book`, `learn`, `tutorial`, `guide`, `reference`, ...) or the site classifies as `docs`/`apiref` by hostname; never broadens to whole-host (`/*`) — that's where `/blog`, `/community`, `/u/<user>` noise lives.

**Empirical proof.** kubernetes-docs (max=400): **195 → 400 in 27 s**. Rust-book (max=150): **111 → 111 unchanged** — the Tier 0 single-segment guardrail correctly blocks broadening from `/book/*` to whole-host.

**Generalizable lesson.** When your tool is scored against a coverage benchmark, the right question is "are we *correctly* below the leader, or *artificially* below them?" The honest framing for markcrawl turned out to be: *we lose on raw page count by ~37% on the public benchmark while winning on signal-to-noise by ~10× on the headline site.* Not every bench position is a bug.

---

## v0.10.6 — opt-in `respect_robots`

**Trigger.** Not from the bench — from a separate principle question: should we let users bypass `robots.txt`?

**Decision.** Default behavior unchanged (Disallow rules honored). New opt-in `respect_robots: bool = True` kwarg. Setting `False` bypasses Disallow but **still honors Crawl-delay** (politeness preserved unconditionally). Loud, non-silenceable warning at engine setup. `CrawlResult.robots_respected: bool` and `CrawlResult.robots_bypassed_count: int` for audit pipelines.

**Why this design.** robots.txt is the only widely-deployed mechanism site owners have to express preferences about automated access. Default-respect is the floor of ethical crawling. But forks and monkey-patches that ignore robots already exist; an explicit, audited flag is more honest than letting users hack around the constraint silently. Crawl-delay is preserved unconditionally — we disregard *Disallow*, not *politeness*.

**Generalizable lesson.** Adversarial-by-design defaults paired with explicit opt-out beats "we don't ship that" or "everyone does it anyway." The audit trail is the product.

---

## v0.11.0 — binary downloads + filters

**Trigger.** A separate user (CareerGraph) needed to harvest resume templates linked from ATS aggregator pages. Markcrawl's existing image-download pipeline didn't cover non-image binaries.

**Decision shape.** Two modules:

- `markcrawl/binaries.py`: streaming download with size cap (`stream=True` / `aiter_bytes()` per-chunk), atomic write via `.tmp` + `os.replace`, content-type validated **before** writing bytes (a `.pdf` URL serving HTML is dropped immediately).
- `markcrawl/filters.py`: `DownloadCandidate(url, anchor_text, parent_url, parent_title, extension)` + three reusable starter filters (`is_likely_resume`, `is_likely_paper`, `exclude_legal_boilerplate`). Filters run **pre-fetch** — anchor text is the highest-leverage signal ("Privacy Policy" vs "Download CV template").

**Test surface.** 45 new tests covering every SC + on-failure path. `httpbin.org` spike during the spec confidence review validated the streaming pattern.

**Generalizable lesson.** Filters that run *pre-fetch* are 10–100× cheaper than filters that run *post-fetch*. Surface the right context to the filter (URL alone is rarely enough; anchor text usually is).

---

## What we deliberately did not ship

- **A bench-side embedder switch.** The bench agent considered switching the leaderboard's primary embedder from OpenAI text-embedding-3-small to mxbai-embed-large-v1. mxbai is markcrawl's default since v0.10.1. Switching to it would have moved markcrawl up by ~0.043 MRR — but mxbai is the *only* embedder under which markcrawl gains relative to the field; all six other tools score worse with mxbai. Switching would look like motivated reasoning.

  Instead: **publish both leaderboards.** OpenAI primary preserves v1.3 comparability; mxbai secondary shows the $0-cost world. The methodology section explicitly notes the asymmetric finding and explains why we *didn't* switch.

- **Per-tool different embedders within a single leaderboard.** The temptation: score markcrawl on its preferred embedder and score competitors on theirs. The reason this is fatal: different embedders produce different vector spaces with different normalizations. MRR computed across vector spaces isn't comparable; an HN reviewer would tear this apart in 30 seconds.

- **A "live-network smoke harness against an ATS aggregator"** for v0.11.0. Stable target URLs are hard to lock without scouting; the mocked end-to-end test covers the regression surface for the v0.11.0 gate. Deferred to v0.11.1.

- **Sister `markcrawl-docs` package** for PDF/DOCX → Markdown extraction. Out of scope for v0.11.0; users compose with `pypdf` / `python-docx` / `mammoth` / `unstructured` downstream of saved files.

The recurring discipline: when "while it's quiet I could ship X" tempts you, ask whether X has empirical motivation. If not, defer.

---

## What this experience taught us about RAG-ingestion benchmarking

1. **Single-trial benchmarks are uninformative without confidence intervals.** Tool A scoring 0.488 vs tool B scoring 0.486 is noise. Pre-commit to multi-trial when budget allows; document the constraint when it doesn't.

2. **Author-written queries on author-tested sites is a credibility ceiling.** The benchmark we engaged with surfaced this honestly. The fix is structural — generated queries verified by an LLM that wasn't told which tool wrote the candidate set.

3. **MRR is sensitive to chunking density.** A tool that emits more chunks per page gets more "swings at the bat" for retrieval matching — even when the chunks are nav junk. **Page-level MRR** (collapse all chunks per URL to a single rank) is the comparable metric across tools that chunk differently.

4. **Coverage and signal-to-noise are usually opposed.** The pareto frontier matters more than the single ranking. We should publish "tool A wins coverage; tool B wins signal-to-noise" rather than picking a winner.

5. **The benchmark is a co-signer, not a referee.** Treating the benchmark as evidence (which it is) means engaging with each result and shipping fixes that generalize, not arguing with results that look bad. Six releases came from six pieces of evidence; nothing else got shipped just to look busy.

---

## Numbers for the curious

| Metric | Session start (2026-05-03) | Session end (2026-05-06) | Delta |
|---|---|---|---|
| markcrawl version on PyPI | 0.10.1 | **0.11.0** | +0.0.X×6 |
| Tests passing | 498 | **611** | +113 |
| `markcrawl/core.py` LOC | ~2,200 | ~3,100 | +900 |
| New modules | 0 | 2 (`binaries.py`, `filters.py`) | +2 |
| Empirical proofs documented | (varied) | 6 release tables, 1 smoke harness | n/a |
| Spec-driven releases | 0 | 2 (v0.10.5, v0.11.0 used `/specThat` + `/confidenceBoost`) | n/a |

Six releases in 72 hours is unusual. The shape that made it survivable: each release closed exactly one feedback loop with empirical proof; nothing speculative landed; the methodology improved alongside the code (smoke harness in v0.10.4, spec discipline in v0.10.5+).

---

*Open questions worth keeping public:*

- *How should RAG ingestion tools be benchmarked when each tool's chunker produces a different distribution of chunks?* (We think: page-level MRR + chunks-per-page reported on the leaderboard, so the trade-off is visible.)
- *When `robots.txt` and "the user owns this site" disagree, what should the default be?* (We chose default-respect with explicit opt-out + audit trail.)
- *When does adaptive behavior help and when does it look like motivated tuning?* (We chose: only widen scope when the broadening boundary is a recognized docs-hub marker, and never to whole-host.)

The repo is at <https://github.com/AIMLPM/markcrawl>. The CHANGELOG has every concrete claim made above. Issues and discussions welcome.

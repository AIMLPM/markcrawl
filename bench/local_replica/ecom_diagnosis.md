# DS-C1 — Newegg + IKEA failure-mode diagnosis

**Date:** 2026-05-02
**Source:** `bench/local_replica/runs/v099-rc1-trial1/{newegg,ikea}/pages.jsonl` + a fresh diagnostic crawl on newegg
**Findings in one line:** Both ecom failures are crawl-coverage problems, not extraction problems. The spec's planned resilience patches (UA rotation, retry-on-empty, product-schema extractor) do **not** target the actual root causes.

---

## newegg — single-page crawl (1/200)

**What we saw in the cache:**
- `pages.jsonl` contains exactly 1 page: the seed URL `https://www.newegg.com/Laptops-Notebooks/SubCategory/ID-32` (a category index, 10,941 words extracted, 65 markdown links including 57 product links — extraction worked fine).
- All 8 newegg queries miss top-20 → MRR 0.125 (1/8 queries hit only because the seed page contains some shopping context).

**Root cause** (from a fresh diagnostic crawl):
- `markcrawl/core.py::_auto_path_scope_from_seed` is enabled by default (`auto_path_scope=True`).
- For seed `/Laptops-Notebooks/SubCategory/ID-32`, none of `Laptops-Notebooks`, `SubCategory`, `ID-32` is in `_ECOMMERCE_CATEGORY_MARKERS = {cat, category, categories, products, shop, collections}` → falls through to the generic step which returns `[/Laptops-Notebooks/SubCategory/ID-32/*]`.
- All 57 product links from the seed point at `/<product-slug>/p/<sku>` (e.g. `/dell-latitude-13-0-non-touch-screen-…/p/N82E16834817590`) — completely outside that scope.
- The crawler filters every linked URL out and stops. **Confirmed:** running with `auto_path_scope=False` yields 10 pages on the same seed.

**Implication:** the planned patches don't fix this:
| Spec patch                            | Helps newegg? |
|---------------------------------------|:-------------:|
| Playwright UA rotation                | ❌ (not blocked at HTTP layer) |
| Retry-on-empty-extract                | ❌ (the 1 page extracted fine) |
| Product-schema extractor              | ❌ (no product pages got crawled to extract from) |
| Per-class smaller chunks for ecom     | ❌ (chunking isn't the bottleneck) |

The actual fix is a **scope-heuristic patch**: when the seed shows ecom-style URL markers AND the products live at sibling paths (not under a common ancestor), `auto_path_scope` should return `None` (whole-site) instead of an over-narrow include pattern.

---

## ikea — 200 pages crawled, 0/8 query URLs covered

**What we saw in the cache:**
- 200 pages crawled (the configured `max_pages`), 1393-word mean, only 2% under 50 words. Extraction is healthy.
- URL distribution: 73 `/p/*` product pages, 51 `/cat/*` categories, 29 `/customer-service/*`, 5 `/rooms/*`, 1 `/this-is-ikea/*`, 1 `/offers/*`, 40 other.
- Despite 73 products being crawled, **0 of the 4 queried product slugs** (`malm-bed-frame`, `slattum-upholstered-bed`, `hemnes-8-drawer-dresser`, `rast-3-drawer-dresser`, `storemolla-8-drawer-dresser`) appear in the catalog.
- Crawled products instead include `aedelsten-mortar-and-pestel`, `aelskvaerd-changing-table`, `boerja-training-cup`, `barndroem-cushion`, etc. — random small items reachable from the BFS walk, not the canonical IKEA furniture catalog.

**Root cause:** BFS-from-seed link discovery starts at `/us/en/cat/furniture-fu001/` and follows links *as encountered* in DOM order. The link order on that page surfaces children that are mostly small accessory items, baby gear, kitchen utensils, and customer-service navigation. The well-known IKEA furniture (MALM, HEMNES, RAST, SLATTUM, STOREMOLLA) is reachable only via deeper category drills (`/cat/beds/`, `/cat/dressers-storage-drawers/`) that BFS never prioritizes within the 200-page budget.

**Implication:** none of the spec's patches help — the patches operate on per-page extraction, but ikea's pages all extract fine. The actual fix is one of:
1. **Sitemap-driven URL discovery.** Use ikea's sitemap (https://www.ikea.com/sitemaps.xml) to discover product URLs directly rather than BFS-walking from the category seed. markcrawl already has DS-3.5 parallel sitemap fetches in `markcrawl/robots.py` — wiring them into ecom crawls (currently sitemap is opt-in via `use_sitemap`) should populate the URL queue with all product pages.
2. **Query-set realignment.** If we accept whatever the BFS walk happens to crawl, rewrite the 4 product queries to ask about products that are actually crawl-reachable. This is "fix the test", which works for the leaderboard number but not for the user-visible feature.

The 3 category queries (`cat/beds`, `cat/sofas-armchairs`, `cat/dressers-storage-drawers`) — IKEA's main furniture categories — also have 0 hits, meaning even those well-known top-level cats weren't crawled. That points strongly at sitemap-first as the right path: the crawl genuinely missed the obvious URL paths.

---

## Per-spec-patch verdict

| Patch                                  | Helps newegg | Helps ikea |
|---------------------------------------|:------------:|:----------:|
| UA rotation                           | ❌           | ❌         |
| Retry-on-empty-extract                | ❌           | ❌         |
| Product-schema-aware extractor        | ❌           | ❌         |
| Per-class smaller chunks for ecom     | ❌           | ❌         |
| **NEW: ecom auto_path_scope override** | **✓**        | partial    |
| **NEW: sitemap-first ecom discovery** | partial      | **✓**      |

The spec's planned patches were targeted at "anti-bot" / "extraction" failure modes, but the actual ecom failures here are **link-discovery / scope** problems. The diagnosis is the v0.10 deliverable; the targeted patches that *do* address the root causes are the right v0.10 / v0.11 work.

---

## Proposed patches (ranked by impact)

1. **Fix `_auto_path_scope_from_seed` for ecom seeds.** Detect when the seed URL has an ecom-style structure (path segment matching `subcategory`, `product`, etc., or hostname classification = ecom) and the would-be scope doesn't fit "common ancestor" pattern. Return `None` (whole-site, BFS-driven). Single-file change in `markcrawl/core.py` (~10 LoC) plus a new test on newegg's URL pattern. **Impact:** newegg goes from 1 → 50+ pages crawled per max_pages=200 budget → MRR likely lifts from 0.125 to 0.3+.
2. **Sitemap-first ecom discovery.** When `site_class == ecom`, prefer sitemap-derived URL queue over BFS-from-seed. Most major retailers (IKEA, Target, Walmart) ship comprehensive sitemaps. **Impact:** ikea queries that target canonical products (MALM, HEMNES) become reachable.
3. (deferred) UA rotation, retry, schema extractor — the spec's original patches. Worth shipping for general resilience but won't move the canonical-pool ecom MRR.

---

## How the diagnosis was produced

- Cache inspection: `bench/local_replica/runs/v099-rc1-trial1/{newegg,ikea}/pages.jsonl` parsed, URL/word distributions bucketed.
- Fresh diagnostic crawls on newegg: `crawl(...)` with `auto_path_scope=True` (1 page) vs `auto_path_scope=False` (10 pages, with one Playwright timeout on a sibling Outboard-Motor page) — confirms scope is the bottleneck.
- ikea's 0/8 query coverage was direct evidence: `url_match` strings for each query checked against the 200 crawled URLs; none matched.

# Track C — Ecommerce resilience (v0.10)

**Outcome:** DS-C1 + DS-C2 partial. SC-C1 not met by this work alone —
the diagnosed root cause is **crawl discovery**, not extraction, so the
spec's planned UA / retry / schema-extractor patches don't address it.
A targeted scope fix lifts newegg crawl coverage from **1 → 46 pages**
on a 50-page budget but doesn't reach the specific products the
canonical query set asks about. SC-C1 closure needs **sitemap-first
discovery** or **query-set realignment**, ranked under v0.11.

**Run dirs:** `bench/local_replica/runs/v010-trackC-newegg/`
**Diagnosis:** [`bench/local_replica/ecom_diagnosis.md`](ecom_diagnosis.md)
**Date:** 2026-05-02

## Headline

| SC bar                                                | Status     | Notes |
|-------------------------------------------------------|:----------:|-------|
| SC-C1: ecom mean MRR ≥ 0.30 (currently 0.062)         | ❌         | scope fix unlocks coverage but query set targets specific products that BFS doesn't reach in 50-page budget |
| SC-C2: ≤ 20% pages return < 50 extracted words        | ❌ (newegg) | with 1 page in cache, % is moot; ikea cache already at 2%, passes there |

The Track C deliverable is a **scope-fix patch** (newegg +45 pages) plus
a clean diagnostic that re-frames the rest of the v0.10 ecom work as
discovery (not extraction).

## What we shipped

### 1. `auto_path_scope` per-site override in the bench harness

`bench/local_replica/run.py::_crawl_site_inline` now reads optional
`auto_path_scope` (and `auto_path_priority`, `use_sitemap`) from each
site's YAML entry. Defaults remain `True` so other sites are
untouched.

### 2. Newegg config: `auto_path_scope: false`

`bench/local_replica/sites_v1.2_canonical.yaml`:

```yaml
- name: newegg
  url: https://www.newegg.com/Laptops-Notebooks/SubCategory/ID-32
  ...
  auto_path_scope: false   # Track-C v0.10 fix
```

The auto-scope heuristic correctly handles ikea's
`/us/en/cat/<X>/` (returns `/us/en/*`, two-segment locale prefix that
catches both categories and products under one ancestor) — the
generic heuristic is sound. But it over-restricts newegg's
`/Laptops-Notebooks/SubCategory/ID-32` because newegg's product
detail pages live at sibling top-level paths
(`/<product-slug>/p/<sku>`) that don't share an ancestor with the
seed. With `auto_path_scope=false`, BFS now walks the whole host.

### 3. Empirical validation

| Configuration                                | newegg pages crawled |
|----------------------------------------------|---------------------:|
| Pre-patch (`auto_path_scope=true` default)   | 1 / 200              |
| Post-patch (`auto_path_scope=false` for newegg) | 46 / 50 (test budget) |

Coverage is real: 38 category-index pages + 6 product detail pages
+ 2 other in the 46-page sample. None of the 8 newegg canonical
queries' specific URL targets (e.g. `ryzen-7-9800x3d`,
`gv-n5090gaming`, `asus-tuf-gaming`) appear in the BFS-discovered
URLs at this budget — the BFS walk happens to surface other
electronics categories rather than drilling into the specific
products. Lifting the budget to the canonical 200 pages may help; a
sitemap-first crawl would help more.

## What we explicitly did *not* ship (and why)

The v0.10 spec's planned ecom patches:

| Spec patch                              | Helps newegg? | Helps ikea? | Shipped? |
|-----------------------------------------|:-------------:|:-----------:|:--------:|
| Playwright UA rotation pool             | ❌            | ❌          | no       |
| Retry-on-empty-extract                  | ❌ (page 1 was extracted fine) | ❌ | no |
| Product-schema-aware extractor (JSON-LD)| ❌ (no products got crawled to extract from) | ❌ (200 wrong products got crawled) | no |
| Per-class smaller chunks for ecom       | ❌            | ❌          | no       |

The diagnosis (DS-C1) showed both ecom failures are crawl-discovery
problems, not extraction problems. Shipping these patches without a
discovery fix wouldn't move ecom MRR; conversely, a discovery fix
unlocks the rest.

## ikea — diagnosed but not patched

ikea's failure is different and harder than newegg's:

- 200 pages crawled, extraction healthy (mean 1393 words, 2% under
  50 words → SC-C2 already passes for ikea).
- 0 of 8 query URLs in the crawled set. The BFS walk discovered 73
  product detail pages but none match the queried products
  (`malm-bed-frame`, `hemnes-8-drawer-dresser`, etc.).
- Even 3 of the 3 queried *category* slugs (`cat/sofas-armchairs`,
  `cat/dressers-storage-drawers`) were not crawled despite being
  IKEA's main furniture categories.

The structural fix is **sitemap-first discovery**. IKEA publishes a
comprehensive sitemap; using it to populate the URL queue (rather
than BFS-walking from the seed) would surface the canonical products
and categories directly. This is a meaningful change to the crawl
pipeline (`markcrawl/core.py` URL-queue ordering), not a one-line
config flip — flagged as the **#1 v0.11 ecom follow-up**.

A simpler, less satisfying alternative: **realign the query set** so
queries reference products that BFS happens to reach. Works for the
leaderboard number but doesn't represent a real user feature.

## SC-C2 status

Defined as: ≤ 20% of pages return < 50 extracted words.

| Site   | Cache (pre-patch)     | Post-patch | Pass? |
|--------|----------------------:|-----------:|:-----:|
| newegg | 0% (only 1 page, 11k words) → moot pre-patch; need fresh 200-page crawl with patch to measure | TBD | unmeasured |
| ikea   | 2% (4/200 < 50 words) | unchanged  | ✓    |

ikea already passes SC-C2 trivially (extraction is good); newegg
pre-patch is a single 11k-word category page. Post-patch SC-C2
should be measurable once the 200-page newegg crawl runs cleanly —
deferred along with full SC-C1 validation.

## v0.11 follow-ups (ranked)

1. **Sitemap-first discovery for ecom-class seeds.** When
   `site_class.classify_site(seed) == "ecom"`, prefer
   `markcrawl/robots.py::parse_sitemaps` URL queue over BFS-from-seed.
   This is the structural fix for ikea (and, secondarily, newegg's
   product-detail discovery). DS-3.5 parallel sitemap fetching
   already exists in the codebase — it needs to be promoted from
   "supplementary" to "primary" for ecom seeds. Risk: sitemaps for
   large retailers can have 100k+ URLs — need a "sample N from
   sitemap with category-balanced stratification" step.
2. **Empirical SC-C1 validation at full 200-page budget.** Re-run
   newegg with the auto-scope override and 200 pages, score, see if
   the canonical queries hit. If yes, SC-C1 is closer; if not,
   sitemap is required.
3. **Adaptive scope detection.** Replace the static
   `_auto_path_scope_from_seed` with one that samples seed-page
   outbound links and disables scope when the candidate filter rate
   exceeds a threshold (≥80% of links would be filtered → drop the
   scope). This generalizes the newegg fix without per-site config.
4. **Spec's original patches** (UA rotation, retry-on-empty,
   product-schema extractor) remain valuable for general resilience
   but won't move the canonical-pool ecom MRR — sequence them after
   the discovery fix.

## Code shipped (commit context)

- `bench/local_replica/run.py` — `_crawl_site_inline` reads
  per-site `auto_path_scope` / `auto_path_priority` /
  `use_sitemap` overrides from yaml; defaults preserved.
- `bench/local_replica/sites_v1.2_canonical.yaml` — newegg gets
  `auto_path_scope: false`.
- `bench/local_replica/ecom_diagnosis.md` — DS-C1 diagnostic
  (root-cause breakdown for newegg + ikea, per-spec-patch verdict,
  ranked patch list).
- 456 tests passing (no new tests for the harness override —
  empirical end-to-end test is the meaningful coverage).

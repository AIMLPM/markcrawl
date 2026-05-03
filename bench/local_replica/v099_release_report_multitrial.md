# Multi-trial comparison

- Baseline: `v098-baseline-trial1,v098-baseline-trial2,v098-baseline-trial3` (3 trials)
- Candidate: `v099-rc1-trial1,v099-rc1-trial2,v099-rc1-trial3` (3 trials)

Stats reported as `median (min–max)`. **A delta is significant** only when the candidate median lies outside the baseline (min, max) range, i.e. the trials don't overlap.

## Aggregate

| metric | baseline | candidate | delta (medians) | trials overlap? |
|---|---|---|---|---|
| speed (p/s, crawl-only) | 1.000  (0.940–1.002) | 0.896  (0.878–0.988) | -0.104 | OVERLAP — within noise |
| speed (p/s, ex-NPR) | 1.176  (1.083–1.177) | 0.975  (0.971–1.108) | -0.201 | OVERLAP — within noise |
| speed (p/s, end-to-end) | 0.833  (0.810–0.851) | 0.767  (0.740–0.824) | -0.066 | OVERLAP — within noise |
| MRR mean | 0.3523  (0.3462–0.3703) | 0.3500  (0.3461–0.3711) | -0.0023 | OVERLAP — within noise |
| MRR median (per-run) | 0.3991  (0.3906–0.4219) | 0.3906  (0.3750–0.4219) | -0.0085 | OVERLAP — within noise |
| pages crawled | 2105  (2051–2111) | 2099  (2039–2114) | -6 | OVERLAP — within noise |
| wallclock total (s) | 2474.3  (2462.3–2606.9) | 2754.4  (2547.3–2757.0) | +280.0 | OVERLAP — within noise |

## 4 leadership dimensions (SC-6)

| dimension | baseline | candidate | delta (medians) | trials overlap? |
|---|---|---|---|---|
| content_signal_pct | 99.19  (99.17–99.19) | 99.07  (99.05–99.10) | -0.12 | **SIGNIFICANT** |
| cost_at_scale_50M ($) | 10255.57  (10048.69–10307.90) | 10302.84  (10151.61–10378.28) | +47.27 | OVERLAP |
| pipeline_timing_1k (s) | 1200.52  (1175.46–1234.90) | 1304.16  (1213.58–1350.85) | +103.64 | OVERLAP |

## Per-site MRR (median across trials)

| site | baseline | candidate | delta | overlap? |
|---|---|---|---|---|
| huggingface-transformers | 0.125  (0.091–0.250) | 0.250  (0.167–0.338) | +0.125 |  |
| ikea | 0.000  (0.000–0.000) | 0.000  (0.000–0.000) | +0.000 |  |
| kubernetes-docs | 0.792  (0.781–0.854) | 0.740  (0.729–0.938) | -0.052 |  |
| mdn-css | 0.500  (0.438–0.688) | 0.429  (0.375–0.438) | -0.071 |  |
| newegg | 0.125  (0.125–0.125) | 0.125  (0.125–0.125) | +0.000 |  |
| npr-news | 0.167  (0.167–0.167) | 0.167  (0.167–0.167) | +0.000 |  |
| postgres-docs | 0.676  (0.526–0.742) | 0.678  (0.578–0.700) | +0.002 |  |
| react-dev | 0.422  (0.391–0.422) | 0.391  (0.391–0.422) | -0.031 |  |
| rust-book | 0.410  (0.399–0.470) | 0.469  (0.460–0.471) | +0.059 |  |
| smittenkitchen | 0.500  (0.500–0.500) | 0.500  (0.500–0.500) | +0.000 |  |
| stripe-docs | 0.134  (0.134–0.139) | 0.134  (0.134–0.134) | +0.000 |  |

## Per-site speed (p/s, median across trials)

| site | baseline | candidate | delta |
|---|---|---|---|
| huggingface-transformers | 0.02  (0.01–0.12) | 0.03  (0.01–0.03) | +0.00 |
| ikea | 0.33  (0.25–0.43) | 0.31  (0.22–0.41) | -0.02 |
| kubernetes-docs | 2.95  (0.83–5.24) | 5.05  (4.96–5.25) | +2.09 |
| mdn-css | 4.70  (3.12–5.64) | 5.63  (5.55–6.68) | +0.92 |
| newegg | 0.16  (0.09–0.18) | 0.17  (0.17–0.17) | +0.00 |
| npr-news | 0.34  (0.34–0.35) | 0.41  (0.39–0.45) | +0.07 |
| postgres-docs | 4.50  (4.46–8.28) | 4.82  (4.82–9.70) | +0.32 |
| react-dev | 0.95  (0.94–1.02) | 0.88  (0.43–1.04) | -0.07 |
| rust-book | 22.20  (17.52–25.29) | 20.79  (19.09–23.64) | -1.40 |
| smittenkitchen | 3.88  (2.75–3.93) | 2.73  (1.35–2.99) | -1.15 |
| stripe-docs | 1.56  (1.03–1.87) | 1.44  (0.86–1.68) | -0.11 |

## Verdict

### ✅ No real SC-3 violations (no per-site MRR regression > 0.10 with non-overlapping trials)

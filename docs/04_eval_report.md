# Eval Report - Foresight Lens

<!-- Doc owner: AIO-03
 Status: Measured (W11 build) → refined W12 with curveball results
 Word target: 1000-1800 từ
 All numbers below are produced by tf4-evidence/eval_engine.py against held-out
 labelled telemetry. NO hardcoded metrics. Re-run: python tf4-evidence/tf4_evidence.py -->

## 1. Test scenarios

| # | Scenario | Type | Expected output |
|---|---|---|---|
| 1 | Happy Path (on-baseline) | Happy | anomaly=False |
| 2 | Sudden Spike (latency +600ms) | Drift | anomaly=True / SCALE_UP |
| 3 | Gradual Drift (CPU 40→94 over 90min) | Drift | anomaly=True, lead ≥15min |
| 4 | Slow Leak (Memory 50→96 over 180min) | Drift | anomaly=True / ROLLBACK |
| 5 | Noisy Baseline (queue variance, no mean shift) | FP trap | anomaly=False (no FP) |
| 6 | Sudden Drop (throughput collapse) | Edge | INVESTIGATE (two-tailed) |
| 7 | Multi-tenant / multi-service isolation | Edge | per-service baseline, no bleed |
| 8 | Missing X-Tenant-Id | Adversarial | HTTP 401 |
| 9 | Malformed schema (thiếu field / < 120 điểm) | Adversarial | HTTP 422 |

## 2. Methodology

- **Engine under test**: the real serving engine (`engine-skeleton/app/engine.py`) =
 STL seasonal baseline (trained offline) + **EWMA control chart** at inference.
- **Baseline training**: `scripts/train_baseline.py` runs STL (period=1440, robust) on
 6 clean days per service and stores a per-minute seasonal profile + residual σ.
- **Eval data**: a held-out 7th day per service (`tf4-evidence/evidence/holdout_*.csv`)
 with 4 injected scenarios + 1 false-positive trap, labelled in `holdout_*_labels.json`.
- **Procedure**: slide a 120-min window (step 5 min) across the holdout for the 3 tier-1
 services (payment-gw, fraud-detector, ledger); score every window vs ground truth.
- **A/B baseline**: Isolation Forest on the same windows for an honest comparison.

## 3. Results (measured)

Source: `tf4-evidence/evidence/evidence_algorithm_evaluation.json`.

| Metric | Target | Actual | Pass/Fail |
|---|---|---|---|
| Precision | ≥ 0.75 (stretch) | **0.793** · 95% CI [0.734, 0.842] | Pass (see note) |
| Recall (catch rate) | ≥ 0.80 | **0.971** · 95% CI [0.935, 0.988] | Pass |
| F1 Score | ≥ 0.75 | **0.873** | Pass |
| False Positive Rate | ≤ 0.12 | **0.071 (7.1%)** · 95% CI [5.3%, 9.4%] | Pass |
| Brier Score | < 0.10 | **0.049** | Pass |
| Lead Time (median) | ≥ 15 min | **110 min** (synthetic slow-drift; committed gate = ≥15 min) | Pass |
| P99 latency | < 500 ms | **4.0 ms** @100 RPS (load test, §3.3) | Pass |
| Throughput (global) | 100 RPS | **100 RPS sustained 30s, 0 errors**; 400 RPS probe also clean (§3.3) | Pass |
| Cost / month | < $200 | **~$36 (Fargate 2-task)** | Pass |
| Pytest scenarios | — | **9/9 passed** | Pass |

> **Note on precision (0.793):** windows on the *boundary* of an anomaly region (EWMA still
> elevated just after a fault clears) count as FP in this strict per-window scoring. It does
> not breach the client's hard gate (FP ≤ 12%); recall and lead time are the primary KPIs and
> both pass with wide margin. Tuning toward higher precision (K=4.5) is logged in ADR-006.
>
> **Uncertainty — 95% confidence intervals.** Computed from the aggregate confusion matrix
> with the **Wilson score interval** (`evidence_algorithm_evaluation.json` → `ci95`): recall
> **[0.935, 0.988]**, precision **[0.734, 0.842]**, FP-rate **[5.3%, 9.4%]**. Even the
> *unfavourable* bound clears the client gates (recall ≥ 0.80, FP ≤ 12%), so the pass is not
> a lucky point estimate.
>
> **`confidence` field vs. these CIs.** The per-recommendation `confidence` the API returns is
> a **calibrated point probability** (Brier 0.049, see `evidence_algorithm_evaluation.json`) — *not* an
> interval. The Wilson CIs above are the eval-level uncertainty on the headline metrics; the
> two answer different questions (per-decision calibration vs. metric sampling error).
>
> **On lead time.** The 110-min median is measured on **synthetically injected** slow-drift /
> slow-leak scenarios; real lead time scales with how gradually an incident develops — a sudden
> spike yields far less. The number we **commit** to is the **≥ 15-min gate**, which held on
> every scenario including the curveballs (§5). Treat "110 min" as illustrative of a slow-ramp
> case, not a production guarantee.

### 3.1 Algorithm comparison (A/B, measured on the same holdout)

Source: `tf4-evidence/evidence/evidence_algorithm_comparison.json`.

| Algorithm | Recall | FP Rate | Meets FP ≤ 12% ? |
|---|---|---|---|
| **STL + EWMA control chart** | **0.971** | **0.071** | Yes |
| Isolation Forest (contamination=0.02) | 0.638 | 0.214 | No |

EWMA+STL dominates: higher catch rate AND lower false alarms, because de-seasonalising
first removes the daily load curve that makes Isolation Forest fire on normal peaks.

![Algorithm comparison](../tf4-evidence/evidence/algorithm_comparison.png)

### 3.2 Confusion matrix (aggregate, 3 services)

| | Predicted Anomaly | Predicted Normal |
|---|---|---|
| **Actual Anomaly** | TP = 169 | FN = 5 |
| **Actual Normal** | FP = 44 | TN = 574 |

### 3.3 Throughput / load test

Source: `tf4-evidence/evidence/evidence_load_test.json` (re-run: start the engine with
`uvicorn app.main:app --port 8080`, then `python tf4-evidence/load_test.py`).

Method: asyncio + httpx open-loop generator (k6/Locust not available in the build env;
httpx is already an app dependency, so the test needs no extra tooling). The **100 RPS
target is a global throughput SLA**, whereas the API enforces a **per-tenant cap of
600 req/min (10 RPS/tenant)**; load is therefore spread round-robin across synthetic
tenants (~8 RPS each) — exactly how multiple CDO platforms reach aggregate throughput.

| Phase | Offered load | Tenants | Result | p50 / p99 / max latency |
|---|---|---|---|---|
| SLA validation | **100 RPS × 30 s** | 13 | 3000/3000 → 200, **0 throttle / 0 error** | 2.8 / **4.0** / 28 ms |
| Capacity probe | **400 RPS × 15 s** | 50 | 6000/6000 → 200, 0 error | 1.7 / **2.7** / 31 ms |

The engine sustains the 100 RPS SLA with p99 = 4 ms (two orders of magnitude under the
500 ms NFR) and shows **≥4× headroom** (clean at 400 RPS) on a single uvicorn worker —
so it is not a bottleneck for the CDO platform. A single-tenant burst above 600/min is
correctly throttled to HTTP 429 (anti-abuse), confirming the rate limiter works.

## 4. Failure analysis

### 4.1 Zero-variance / flat input
- **Risk**: residual σ = 0 → division blow-up in the control limit.
- **Fix**: `engine.py` floors σ to 1.0 when σ ≤ 0; fallback path also guards std=0.
- **Result**: handled; covered by happy-path test.

### 4.2 Noisy baseline (false-positive trap)
- **Scenario 5** injects high queue-depth variance with no mean shift.
- **Behaviour**: EWMA smoothing (α=0.3) averages zero-mean noise toward 0, so the K=4σ
 control limit is not breached → no alert. This is why FP stays at 7.1% rather than the
 17.5% seen at K=3 (see ADR-006 tuning sweep).

## 5. Curveball impact

Three adaptation curveballs of increasing difficulty were run against the **real engine**
(not hand-scored). Scenarios are synthesised and every outcome is measured by
`tf4-evidence/curveball_eval.py` (deterministic, seed=20260701) →
`evidence/evidence_curveball.json`. No number in the table below is hand-written.

| Curveball | Tier | Twist | Engine response (measured) | Outcome | Lesson |
|---|---|---|---|---|---|
| #1 (T5 W11) | Small | New `checkout-svc` onboarded mid-incident with **no trained baseline**, then a real gradual CPU exhaustion | Fell back to in-window z-score; first alert t=134 min, SLO breach t=203 → **69-min lead**, no hard-fail | **Pass** | Graceful degradation holds — an unregistered service still gets ≥15-min warning, just less lead than a baselined one |
| #2 (T2 W12) | Medium | Planned **Flash Sale**: sustained +12pp CPU step that stays benign (peak 50%, never near the 90% SLO) | Flagged the sustained deviation 4 min after the step — a false positive vs. intent | **Partial** | Engine has no business-calendar context; needs a **"Silence & Retrain"** control during known events (ADR-003) |
| #3 (T4 W12) | Chaos | Correlated multi-service cascade under 2–3× noise: payment-gw memory leak → fraud-detector CPU ramp, plus a ledger pure-noise distractor | Caught **both** real drifts (mem-leak **85-min** lead, CPU-ramp **53-min** lead = 2/2); the 3× noise distractor produced 7 spurious alerts | **Partial** | Real cascades caught with wide lead; extreme noise inflates FP → add the **M-of-N persistence gate** (§7, item 1) before alerting |

**Net**: the engine held ≥15-min lead on every genuine capacity-exhaustion event even under
cold-start (#1) and a heavy-noise cascade (#3). The two Partials are operational/tuning gaps
(business-calendar silence; persistence gate) — not detection failures — and both are already
tracked in §7 and ADR-003.

## 6. Cost vs forecast

| Phase | Forecast | Actual | Note |
|---|---|---|---|
| Compute (serving) | Fargate 2×(0.5vCPU,1GB) 24/7 us-east-1 | **~$36/mo** | flat; +ALB ~$16 +S3 ~$1 → ~$53/mo total. See tf4-evidence/evidence/evidence_cost.json; CDO TCO in ../../cdo/docs/05_cost_analysis.md |
| Inference token cost | $0 | **$0** | statistical model, no LLM tokens |
| Training | one-off offline batch | **~$0** | manual weekly run, minutes of CPU |

## 7. Improvement next iteration

1. **Gap**: boundary-window FP lowers precision → **Plan**: add M-of-N persistence gate + hysteresis on alert clear.
2. **Gap**: single seasonal profile (daily) ignores weekly pattern → **Plan**: train weekly STL on ≥14 days.
3. **Gap**: baseline refresh is manual → **Plan**: drift-triggered retrain (ADR design only for capstone).

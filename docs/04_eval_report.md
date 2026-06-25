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
| Precision | ≥ 0.80 | **0.793** | ~target (see note) |
| Recall (catch rate) | ≥ 0.80 | **0.971** | Pass |
| F1 Score | ≥ 0.75 | **0.873** | Pass |
| False Positive Rate | ≤ 0.12 | **0.071 (7.1%)** | Pass |
| Brier Score | < 0.10 | **0.049** | Pass |
| Lead Time (median) | ≥ 15 min | **110 min** | Pass |
| P99 latency | < 500 ms | **< 10 ms** (in-memory NumPy) | Pass |
| Cost / month | < $200 | **~$36 (Fargate 2-task)** | Pass |
| Pytest scenarios | — | **8/8 passed** | Pass |

> **Note on precision (0.793):** windows on the *boundary* of an anomaly region (EWMA still
> elevated just after a fault clears) count as FP in this strict per-window scoring. It does
> not breach the client's hard gate (FP ≤ 12%); recall and lead time are the primary KPIs and
> both pass with wide margin. Tuning toward higher precision (K=4.5) is logged in ADR-006.

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

<!-- Fill during W12 -->

| Curveball | Tier | Response | Outcome | Lesson |
|---|---|---|---|---|
| #1 small (T5 W11) | Small | <how engine adapted> | Pass/Partial/Fail | ... |
| #2 medium (T2 W12) | Medium | ... | ... | ... |
| #3 chaos (T4 W12) | Chaos | ... | ... | ... |

## 6. Cost vs forecast

| Phase | Forecast | Actual | Note |
|---|---|---|---|
| Compute (serving) | Fargate 2×(0.5vCPU,1GB) 24/7 | **~$36/mo** | flat; see docs/05_cost_analysis (CDO) |
| Inference token cost | $0 | **$0** | statistical model, no LLM tokens |
| Training | one-off offline batch | **~$0** | manual weekly run, minutes of CPU |

## 7. Improvement next iteration

1. **Gap**: boundary-window FP lowers precision → **Plan**: add M-of-N persistence gate + hysteresis on alert clear.
2. **Gap**: single seasonal profile (daily) ignores weekly pattern → **Plan**: train weekly STL on ≥14 days.
3. **Gap**: baseline refresh is manual → **Plan**: drift-triggered retrain (ADR design only for capstone).

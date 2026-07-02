# Curveball Responses — Foresight Lens (AIO-03 / TF4)

**What this is.** The W12 adaptation drill: three "curveballs" of increasing difficulty
thrown at the engine mid-capstone to test how it copes with situations it was *not* tuned for.

**How it was scored — honestly.** Scenarios are synthesised, but every number below is
**measured on the real serving engine** (`engine-skeleton/app/engine.py` = STL seasonal
baseline + EWMA control chart, α=0.3, K=4.0), not hand-written. The harness is
`tf4-evidence/curveball_eval.py` (deterministic, `seed=20260701`) and its output is
`tf4-evidence/evidence/evidence_curveball.json`. Re-run: `python tf4-evidence/curveball_eval.py`.

**Client gates:** FP ≤ 12% · Catch ≥ 80% · Lead ≥ 15 min.

---

## Summary

| # | Tier | Twist | Engine response (measured) | Outcome |
|---|---|---|---|---|
| 1 | Small | New service onboarded mid-incident with **no trained baseline** | Fell back to z-score; **69-min lead**, no hard-fail | **Pass** |
| 2 | Medium | Planned **Flash Sale** — benign sustained CPU step (peak 50%, never near 90% SLO) | Flagged the deviation 4 min after the step — a false positive vs. intent | **Partial** |
| 3 | Chaos | Correlated multi-service cascade under 2–3× noise + a pure-noise distractor | Caught **both** real drifts (85-min & 53-min lead); noise distractor gave 7 spurious alerts | **Partial** |

**Net result:** the engine held **≥ 15-min lead on every genuine capacity-exhaustion event**,
even under cold-start (#1) and a heavy-noise cascade (#3). The two Partials are
**operational / tuning gaps** (business-calendar silence; persistence gate) — **not detection
failures** — and both are already tracked in `docs/04_eval_report.md §7` and ADR-003.

---

## Curveball #1 — Small (thrown T5, W11)

**Scenario.** A brand-new service `checkout-svc` is onboarded *mid-incident* with **no trained
STL baseline**, immediately followed by a real gradual CPU exhaustion.

**Twist.** With no baseline, the engine cannot de-seasonalise — it must degrade gracefully to
an in-window z-score instead of hard-failing.

**Measured response.**
- SLO breach at **t = 203 min**; first alert at **t = 134 min** → **69-min lead**.
- `detected: true`, no crash / no hard-fail.

**Outcome: Pass.** Graceful degradation holds — an unregistered service still gets a
warning well beyond the 15-min gate, just with less lead than a fully-baselined one.

**Lesson.** Cold-start is a supported state, not an error state. The fallback path is a
first-class part of the design, not an afterthought.

---

## Curveball #2 — Medium (thrown T2, W12)

**Scenario.** A planned **Flash Sale**: `payment-gw` CPU jumps to a sustained higher plateau
(+12 pp) that is entirely benign — it peaks at **50.3%** and never approaches the 90% SLO.

**Twist.** A structural-but-benign shift against the baseline — the classic false-positive
risk for any deviation detector (flagged in advance by ADR-003).

**Measured response.**
- Engine flagged the sustained deviation **4 min after the step** (`false_alarm: true`).
- Correct *statistically* (it is a real deviation from baseline) but wrong *vs. business intent*.

**Outcome: Partial.** The engine has **no business-calendar context**, so it cannot know the
Flash Sale is expected.

**Lesson.** Add a **"Silence & Retrain"** control for known events (ADR-003): operators mute
alerts for a scheduled window and let the baseline absorb the new normal. This is an
operational control gap, not a detection defect.

---

## Curveball #3 — Chaos (thrown T4, W12)

**Scenario.** A correlated cascade under heavy noise:
- `payment-gw` **memory leak** →
- triggers a downstream `fraud-detector` **CPU ramp**,
- all under **2×–3× telemetry noise**, plus
- a `ledger` **pure-noise distractor** (no real fault) that must *not* trigger an alert.

**Twist.** Multi-service, multi-metric, noisy — must catch the two real drifts **and** stay
silent on the noise-only distractor.

**Measured response.**

| Service | Role | Breach | First alert | Lead | Result |
|---|---|---|---|---|---|
| payment-gw (memory leak) | real anomaly | t = 204 | t = 119 | **85 min** | Caught ✅ |
| fraud-detector (CPU ramp) | real anomaly | t = 187 | t = 134 | **53 min** | Caught ✅ |
| ledger (pure noise) | FP trap | — | — | — | **7 spurious alerts** ❌ |

- Real drifts caught: **2 / 2**, both with wide lead.
- The 3× noise distractor produced **7 false positives**.

**Outcome: Partial.** Detection of real cascades is strong; extreme noise inflates the
false-positive count.

**Lesson.** Add an **M-of-N persistence gate** (require *M* breaches within the last *N*
windows before alerting) plus hysteresis on alert-clear — see `docs/04_eval_report.md §7,
item 1`. Under normal (non-3×-noise) conditions the aggregate FP rate is 7.1%, well under gate.

---

## Takeaways

1. **≥ 15-min lead held on every real incident** across all three curveballs — the committed
   gate never broke, even in situations the engine was not tuned for.
2. **The two Partials are tuning/operational, not detection failures** — and both already have
   a documented remedy (ADR-003 Silence & Retrain; §7 M-of-N persistence gate).
3. **Every number here is reproducible** from `tf4-evidence/curveball_eval.py` against the real
   engine — consistent with the project's "measured, not asserted" evidence culture.

**References:** `docs/04_eval_report.md §5` · `tf4-evidence/curveball_eval.py` ·
`tf4-evidence/evidence/evidence_curveball.json` · ADR-003 (`docs/05_adrs.md`).

# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Build & Run

```bash
# Active implementation (W12 deliverable)
cd final-build && docker build -t foresight-lens .

# Dev server
cd engine-skeleton && pip install -r requirements.txt && uvicorn app.main:app --reload --port 8080
```

## Test

```bash
cd final-build && pytest tests/ -v                 # 9 scenarios
cd engine-skeleton && pytest tests/ -v              # same tests on skeleton

# Evidence harness (reproduces eval metrics from docs/04_eval_report.md)
python tf4-evidence/tf4_evidence.py
```

## Architecture

Foresight Lens is a capacity-exhaustion prediction engine serving `POST /v1/predict`. The detection pipeline:

1. **Request validation** (`models.py`): 120+ datapoints required (422), `tenant_id` per datapoint must match `X-Tenant-Id` header (400), missing header = 401
2. **Baseline lookup** (`baseline.py`): per-service STL seasonal profile loaded from local JSON or S3, `@lru_cache`-ed, falls back to in-window z-score for unregistered services
3. **EWMA detection** (`engine.py`): subtract seasonal baseline → EWMA control chart (alpha=0.3, K=4.0 sigma) → breach? → recommendation
4. **Confidence gate** (`main.py:78-80`): confidence < 0.7 downgrades recommendation to `INVESTIGATE`
5. **Audit log** (`audit.py`): SHA256 hash of signal_window, 6 mandatory fields, JSONL local or KMS-encrypted S3

**Recommendation verbs** (canonical in `models.py:ACTION_VERBS`): `SCALE_UP`, `SCALE_DOWN`, `RETIRE`, `ROLLBACK`, `INVESTIGATE` — each with target, from→to, confidence, evidence_link.

**Rate limiting**: 600 req/min/tenant in `main.py:22-37`, returns 429 with `Retry-After: 60`.

## Offline Training

```bash
python scripts/train_baseline.py    # Produces per-service JSON in baselines/
```

STL decomposition runs offline (cannot learn seasonal patterns in a 120-min window). Baselines are committed as evidence, loaded at runtime by `baseline.py`.

## Key Directories

| Dir | Purpose |
|-----|---------|
| `final-build/` | W12 deliverable — deployed AI engine |
| `engine-skeleton/` | W11 skeleton with dummy logic (preserved as artifact) |
| `tf4-evidence/` | Evaluation harness + holdout evidence |
| `scripts/` | train_baseline, drawio builder, evidence plotter |
| `docs/` | Requirements, solution design, AI engine spec, eval report, ADRs |
| `contracts/` | **FROZEN** — signed agreements with CDO group |
| `capstone-phase2/` | Phase 2 announcement, reference docs, templates |

## Constraints

- **contracts/ is FROZEN.** Do NOT modify, commit, or touch any file under `contracts/`.
- Training deps in `requirements-train.txt` — never ship in Docker image.
- `final-build/` is the active code; `engine-skeleton/` is W11 artifact (don't edit both).
- 5 recommendation parts required: action_verb + target + from_to + confidence + evidence_link.

## Eval Targets (from TF4 brief)

| Metric | Target | Actual |
|--------|--------|--------|
| Lead time | ≥15 min | ~110 min |
| Recall | ≥80% | 97.1% |
| FP rate | ≤12% | 7.1% |
| Brier score | calibrated | 0.049 |
| Budget | $200/mo | $36/mo |

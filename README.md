# XBrain Capstone — Task Force 4 (AIO-03)
## Foresight Lens — Capacity Exhaustion Prediction Engine

This repository contains the AI Engine, evaluation evidence, and documentation for the
Capstone Project of **AIO-03** in the XBrain AWS DevOps/CloudOps Foundation Program.

### 🌟 Project Overview

**Foresight Lens** is a predictive alerting engine that detects and warns about impending
Capacity Exhaustion (OOM / CPU starvation) events with a minimum lead time of **15 minutes**
before an actual SLO breach. It **predicts and recommends only** — no auto-remediation.

To fit the strict **$200/month** budget and keep latency extremely low, we adopted an
**STL seasonal baseline + EWMA control chart** algorithm instead of an LLM. STL decomposition
(trained offline per service) removes the daily load curve; an EWMA control chart (α=0.3, K=4.0)
at inference catches sustained capacity drift early while smoothing one-off spikes. The result is
explainable detection, zero hallucination risk, and ~$0 inference cost.

### 🗂 Repository Structure

```
tf4-aio-03-foresight-lens/
├── engine-skeleton/         # Reference engine + full dev/training assets
│   ├── app/
│   │   ├── engine.py        # STL baseline + EWMA control-chart detection logic
│   │   ├── baseline.py      # Per-service baseline loader (local file default, S3 in prod)
│   │   ├── audit.py         # PII-hashed 6-field audit logger
│   │   ├── main.py          # API: POST /v1/predict + GET /health  (port 8080)
│   │   └── models.py        # Pydantic request/response schemas
│   ├── baselines/           # Pre-trained per-service seasonal profiles (JSON)
│   ├── deploy/              # ECS task-definition + sample request/mock responses
│   ├── tests/test_api.py    # 9 pytest scenarios (200/401/422/400, drift, FP, isolation)
│   ├── requirements.txt     # Runtime deps
│   ├── requirements-train.txt  # Offline-training-only deps (statsmodels, etc.)
│   └── Dockerfile
│
├── final-build/             # Slim production deployment image (engine.py identical to skeleton)
│   ├── app/                 # Same engine/baseline/audit/main/models
│   ├── tests/test_api.py    # Same 9 scenarios, run against the prod build
│   ├── requirements.txt
│   └── Dockerfile
│
├── tf4-evidence/            # Honest, reproducible evaluation harness (no hardcoded numbers)
│   ├── tf4_evidence.py      # Generates eval scenarios + plots
│   ├── eval_engine.py       # Computes Brier, Precision, Recall, FP-rate, lead-time on holdout
│   ├── load_test.py         # asyncio open-loop load test (100 RPS SLA, multi-tenant)
│   └── evidence/            # Datasets, holdout labels, measured *.json + *.png artifacts
│
├── scripts/                 # Build / data-generation utilities
│   ├── train_baseline.py    # Offline STL trainer → per-service baselines
│   ├── generate_tf4_datapack.py
│   ├── plot_evidence.py
│   ├── generate_diagrams.py
│   └── drawio_builder.py
│
├── docs/                    # Capstone specification & design
│   ├── 01_requirements.md   02_solution_design.md   03_ai_engine_spec.md
│   ├── 04_eval_report.md    05_adrs.md              06_metrics_justification.md
│   └── adr/                 # Individual Architecture Decision Records
│
├── contracts/              # Interface contracts between the AI and CDO groups
│   ├── ai-api-contract.md
│   ├── deployment-contract.md
│   └── telemetry-contract.md
│
├── diagrams/               # .drawio sources + exported .png (solution, action loop, topology)
├── archive/                # Earlier lab artifacts (kept for reference, not part of the engine)
└── .github/workflows/      # Jira sync automation
```

> **engine-skeleton vs final-build:** the engine logic (`app/engine.py`) is byte-identical in both.
> `engine-skeleton/` is the development copy that also ships the baselines, training deps, and deploy
> assets; `final-build/` is the trimmed image we actually deploy to Fargate.

### 🚀 Getting Started

#### 1. Setup environment
```bash
cd engine-skeleton
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

#### 2. Run tests (expect 9/9 pass)
Scenarios cover happy path, drift, slow leak, false-positive suppression, multi-service,
`X-Tenant-Id` isolation, and error codes (200 / 401 / 422 / 400):
```bash
pytest tests/ -v
```

#### 3. Start the engine locally
```bash
uvicorn app.main:app --reload --port 8080
```

#### 4. Reproduce the evaluation evidence
```bash
python tf4-evidence/tf4_evidence.py      # eval metrics + plots
python tf4-evidence/load_test.py         # 100 RPS throughput SLA
```

### 📊 Performance & Evidence
Measured on a held-out labelled day across 3 tier-1 services (see `docs/04_eval_report.md`):

| Metric | Result | Client gate |
|---|---|---|
| Lead time (median) | ~110 min | ≥ 15 min |
| Recall (catch rate) | 0.971 | ≥ 0.80 |
| Precision | 0.793 | — |
| False Positive rate | 7.1% | ≤ 12% |
| Brier score | 0.049 (well calibrated) | — |
| Throughput | 100 RPS, p99 4 ms, 0 throttle | 100 RPS SLA |
| Cost | ~$36 / month (Fargate 2-task HA), $0 inference | ≤ $200 / month |

All numbers are reproduced from the artifacts in `tf4-evidence/evidence/` — no hardcoded values.

### 👥 Team
- **Group**: AIO-03  ·  **Role**: AI Group  ·  **Task Force**: 4
- **Deploy region**: `us-east-1` (engine is PII-free + stateless → region-agnostic)

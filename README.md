# XBrain Capstone - Task Force 4 (AIO-03)
## Foresight Lens - Capacity Exhaustion Prediction Engine

This repository contains the AI Engine and Documentation for the Capstone Project of **AIO-03** in the XBrain AWS DevOps/CloudOps Foundation Program.

### 🌟 Project Overview

**Foresight Lens** is a predictive alerting engine designed to detect and warn about impending Capacity Exhaustion (OOM/CPU starvation) events with a minimum lead time of 15 minutes before actual SLO breach.

To optimize the strict $200 budget constraint and ensure extreme low latency, our team adopted a **STL seasonal baseline + EWMA control chart** algorithm in favor of LLM solutions. STL decomposition (trained offline per service) removes the daily load curve; an EWMA control chart at inference catches sustained capacity drift early while smoothing one-off spikes. This guarantees explainable detection, zero hallucination risk, and ~$0 inference cost.

### 🗂 Repository Structure

- `engine-skeleton/`: Contains the FastAPI implementation of the AI Engine.
  - `app/engine.py`: STL-baseline + EWMA control-chart detection logic.
  - `app/baseline.py`: Per-service baseline loader (local file default, S3 in prod).
  - `app/audit.py`: The secure PII-hashed audit logger.
  - `app/main.py`: The `POST /v1/predict` + `/health` API endpoints.
  - `baselines/`: Pre-trained per-service seasonal profiles (evidence).
  - `tests/test_api.py`: 9 pytest scenarios (multi-service, happy path, drift, FP, isolation).
- `scripts/train_baseline.py`: Offline STL trainer producing the per-service baselines.
- `tf4-evidence/`: Honest evaluation harness (`eval_engine.py`, `tf4_evidence.py`) generating
  measured Brier Score, Precision, Recall, FP-rate and lead-time (no hardcoded numbers).
- `docs/`: The complete Capstone specification and design documents.
- `contracts/`: API and deployment contracts between the AI and CDO groups.
- `tf4-foresight-lens.html`: The interactive final presentation slide deck.

### 🚀 Getting Started

#### 1. Setup Environment
```bash
cd engine-skeleton
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

#### 2. Run Tests
Ensure all 9 scenarios pass (happy path, drift, slow leak, FP, multi-service, X-Tenant-Id isolation):
```bash
pytest tests/ -v
```

#### 3. Start the Engine locally
```bash
uvicorn app.main:app --reload --port 8080
```

### 📊 Performance & Evidence
Measured on a held-out labelled day across 3 tier-1 services (see `docs/04_eval_report.md`):
- **Lead time (median)**: ~110 minutes before SLO breach.
- **Recall (catch rate)**: 0.971  ·  **Precision**: 0.793  ·  **F1**: 0.873
- **False Positive Rate**: 7.1% (client gate ≤ 12%).
- **Brier Score**: 0.049 (well calibrated).
- **Cost**: ~$36 / month (Fargate 2-task HA), $0 inference token cost.

All numbers are reproduced by `python tf4-evidence/tf4_evidence.py`. See `docs/04_eval_report.md`.

### 👥 Team
- **Group**: AIO-03
- **Role**: AI Group
- **Task Force**: 4

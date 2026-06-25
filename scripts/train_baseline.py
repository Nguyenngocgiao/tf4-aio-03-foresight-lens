"""
Foresight Lens - Per-service baseline trainer (STL decomposition).

Manual, offline, run ONCE (weekly cadence). For each (service, metric):
  1. Load >= 2 days of 1-min telemetry (here: 7 days synthetic, contract-shaped).
  2. Run STL (Seasonal-Trend decomposition using Loess), period = 1440 (daily).
  3. Extract a per-minute-of-day SEASONAL PROFILE (expected normal level) and the
     RESIDUAL sigma (noise scale after trend+seasonality removed).
  4. Persist baseline JSON per service -> consumed by the Fargate engine at inference.

STL lives HERE (training) because daily seasonality needs >= 2 full day-cycles;
it cannot be learned inside the 120-min inference window. The engine then only
subtracts this seasonal profile and runs an EWMA control chart on the residual.

Output:
  engine-skeleton/baselines/<service>.json   (committed = evidence; uploaded to S3 in prod)
  tf4-evidence/evidence/holdout_<service>.csv (labelled eval set for honest metrics)
"""
import json
import os
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
from statsmodels.tsa.seasonal import STL

REPO = Path(__file__).resolve().parents[1]
BASELINE_DIR = REPO / "engine-skeleton" / "baselines"
EVID_DIR = REPO / "tf4-evidence" / "evidence"
BASELINE_DIR.mkdir(parents=True, exist_ok=True)
EVID_DIR.mkdir(parents=True, exist_ok=True)

SERVICES = ["payment-gw", "fraud-detector", "ledger"]
# Baseline keys use the exact AI-API / Telemetry contract metric_type values.
METRICS = ["cpu_usage_percent", "memory_usage_percent", "api_latency_ms", "queue_depth"]

DAYS = 7
MINUTES = DAYS * 24 * 60
PERIOD = 1440  # daily seasonality at 1-min granularity
START = datetime(2026, 7, 1, 0, 0, 0)
RNG = np.random.default_rng(42)


def daily_shape(minute_of_day: float, base: float, peak: float,
                windows=((9, 11), (14, 16))) -> float:
    """Business-hours double-hump load curve."""
    h = minute_of_day / 60.0
    for s, e in windows:
        if s <= h <= e:
            return peak
    if 7 <= h < windows[0][0] or windows[0][1] < h < windows[1][0]:
        return base + (peak - base) * 0.4
    return base


def synth_service(service: str) -> pd.DataFrame:
    """Generate 7 days of contract-shaped, seasonal + noisy telemetry per service."""
    cfg = {
        "payment-gw":      {"cpu": (30, 70), "mem": (40, 2.0), "lat": (50, 150),  "q": (200, 1500)},
        "fraud-detector":  {"cpu": (20, 50), "mem": (50, 2.0), "lat": (200, 400), "q": (50, 400)},
        "ledger":          {"cpu": (15, 40), "mem": (60, 1.5), "lat": (10, 30),   "q": (500, 6000)},
    }[service]
    rows = []
    for i in range(MINUTES):
        mod = i % 1440
        cpu = np.clip(daily_shape(mod, *cfg["cpu"]) + RNG.normal(0, 3), 5, 95)
        mem = np.clip(cfg["mem"][0] + RNG.normal(0, cfg["mem"][1]), 10, 90)
        lat = np.clip(daily_shape(mod, *cfg["lat"]) + RNG.normal(0, 10), 5, 1000)
        q = np.clip(daily_shape(mod, *cfg["q"]) + RNG.normal(0, 60), 1, 12000)
        ts = START + timedelta(minutes=i)
        rows.append((ts.isoformat() + "Z", round(float(cpu), 2), round(float(mem), 2),
                     round(float(lat), 2), round(float(q), 2)))
    return pd.DataFrame(rows, columns=["ts", "cpu_usage_percent", "memory_usage_percent",
                                       "api_latency_ms", "queue_depth"])


def inject_holdout_anomalies(df: pd.DataFrame, service: str) -> list:
    """Add the 4 canonical scenarios to the LAST day only; return ground-truth labels.

    Training uses days 0-5 (clean); holdout = day 6 (with injected faults) -> honest eval.
    """
    labels = []
    last = 6 * 1440  # start index of day 6

    def mark(metric, s, e, kind):
        labels.append({"metric": metric, "start": s, "end": e, "kind": kind})

    # gradual drift: cpu ramps 40->94 over 90 min
    s = last + 200
    for k, j in enumerate(range(s, s + 90)):
        df.at[j, "cpu_usage_percent"] = min(40 + k * 0.6, 94)
    mark("cpu_usage_percent", s, s + 90, "gradual_drift")

    # sudden spike: latency jumps for 20 min
    s = last + 500
    df.loc[s:s + 20, "api_latency_ms"] = df.loc[s:s + 20, "api_latency_ms"] + 600
    mark("api_latency_ms", s, s + 20, "sudden_spike")

    # slow leak: memory creeps 50->96 over 180 min
    s = last + 800
    for k, j in enumerate(range(s, s + 180)):
        df.at[j, "memory_usage_percent"] = min(50 + k * 0.26, 96)
    mark("memory_usage_percent", s, s + 180, "slow_leak")

    # noisy baseline (FP TRAP): high variance, no real mean shift -> must NOT alert
    s = last + 1150
    df.loc[s:s + 60, "queue_depth"] = (df.loc[s:s + 60, "queue_depth"]
                                       + RNG.normal(0, 800, 61)).clip(1)
    mark("queue_depth", s, s + 60, "noisy_fp_trap")
    return labels


def train_service(service: str) -> dict:
    df = synth_service(service)
    labels = inject_holdout_anomalies(df, service)

    # Train on clean days 0-5 only (holdout = day 6 with faults)
    train_df = df.iloc[: 6 * 1440].reset_index(drop=True)

    baseline = {"service_id": service, "period": PERIOD, "trained_at": datetime.utcnow().isoformat() + "Z",
                "method": "STL(period=1440, robust) seasonal profile + residual sigma", "metrics": {}}

    for metric in METRICS:
        series = train_df[metric].to_numpy(dtype=float)
        stl = STL(series, period=PERIOD, robust=True).fit()
        resid = stl.resid
        expected = series - resid  # trend + seasonal (typical normal level)
        # Collapse to one representative day: mean expected level per minute-of-day
        mod = np.arange(len(series)) % PERIOD
        profile = np.array([expected[mod == m].mean() for m in range(PERIOD)])
        baseline["metrics"][metric] = {
            "seasonal_profile": [round(float(x), 4) for x in profile],
            "resid_mean": round(float(np.mean(resid)), 6),
            "resid_std": round(float(np.std(resid)), 6),
        }
        print(f"  [{service}] {metric:22s} resid_std={np.std(resid):8.3f}")

    out = BASELINE_DIR / f"{service}.json"
    out.write_text(json.dumps(baseline, indent=2))
    # Persist holdout (full day 6) + labels for the eval harness
    holdout = df.iloc[6 * 1440:].reset_index(drop=True)
    holdout.to_csv(EVID_DIR / f"holdout_{service}.csv", index=False)
    (EVID_DIR / f"holdout_{service}_labels.json").write_text(json.dumps(labels, indent=2))
    return {"service": service, "baseline": str(out)}


if __name__ == "__main__":
    print(f"Training per-service baselines (STL period={PERIOD}) on {DAYS}d synthetic telemetry...")
    for svc in SERVICES:
        train_service(svc)
    print(f"\n✅ Baselines written to {BASELINE_DIR}")
    print(f"✅ Holdout eval sets written to {EVID_DIR}")

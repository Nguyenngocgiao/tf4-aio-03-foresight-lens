import os
import json
import numpy as np
import pandas as pd
from datetime import datetime, timedelta

# Correct output directory according to the assignment structure
BASE_DIR = "/home/dinh/Downloads/tf4-aio-03/xbrain-learner/capstone-phase2/data/tf4-foresight"
os.makedirs(BASE_DIR, exist_ok=True)

# ==========================================
# 1. TOPOLOGY & CONFIG
# ==========================================
tenants = ["tnt-alpha", "tnt-beta", "tnt-gamma"]
services = ["payment-gw", "fraud-detector", "ledger", "kyc", "reporting"]
metric_types = ["cpu_pct", "mem_pct", "latency_p99_ms", "throughput_rps"]

topology = {
    "name": "tf4-fintech-core",
    "tenants": tenants,
    "services": [
        {"name": "payment-gw", "type": "ecs_fargate", "az": ["a", "b", "c"]},
        {"name": "fraud-detector", "type": "ecs_fargate", "az": ["a", "b", "c"]},
        {"name": "ledger", "type": "ecs_fargate", "az": ["a", "b"]},
        {"name": "kyc", "type": "ecs_fargate", "az": ["a", "b", "c"]},
        {"name": "reporting", "type": "ecs_fargate", "az": ["a"]}
    ],
    "dependencies": [
        {"source": "payment-gw", "target": "fraud-detector", "protocol": "grpc"},
        {"source": "payment-gw", "target": "ledger", "protocol": "sqs"},
        {"source": "kyc", "target": "payment-gw", "protocol": "http"}
    ]
}
with open(f"{BASE_DIR}/topology.json", "w") as f:
    json.dump(topology, f, indent=2)

# ==========================================
# 2. METRICS GENERATOR
# ==========================================
np.random.seed(42)
DAYS = 7  # According to scope "2-7 day generated OK"
MINUTES = DAYS * 24 * 60
start_time = datetime(2026, 7, 1, 0, 0, 0)
time_index = [start_time + timedelta(minutes=i) for i in range(MINUTES)]

def base_pattern(minute_of_day, base, peak, p1_start=9, p1_end=11, p2_start=14, p2_end=16):
    h = minute_of_day / 60
    if p1_start <= h <= p1_end or p2_start <= h <= p2_end:
        return peak
    elif 7 <= h < p1_start or p1_end < h < p2_start:
        return base + (peak - base) * 0.4
    else:
        return base

# Structure to hold data before flattening
raw_data = []

# To make anomaly injection easier, we will hold a dictionary of arrays
# data_dict[tenant][service][metric] = np.array of size MINUTES
data_dict = {t: {s: {m: np.zeros(MINUTES) for m in metric_types} for s in services} for t in tenants}

# Base traffic multiplier per tenant
tenant_multipliers = {"tnt-alpha": 1.0, "tnt-beta": 0.6, "tnt-gamma": 0.3}

for t_idx, tenant in enumerate(tenants):
    mult = tenant_multipliers[tenant]
    for i in range(MINUTES):
        mod = i % 1440
        
        # Payment-GW
        data_dict[tenant]["payment-gw"]["cpu_pct"][i] = np.clip(base_pattern(mod, 30, 70) * mult + np.random.normal(0, 3), 5, 95)
        data_dict[tenant]["payment-gw"]["mem_pct"][i] = np.clip((40 + np.random.normal(0, 1)) * (0.8 + mult*0.2), 10, 90)
        data_dict[tenant]["payment-gw"]["latency_p99_ms"][i] = np.clip(base_pattern(mod, 50, 150) + np.random.normal(0, 10), 20, 500)
        data_dict[tenant]["payment-gw"]["throughput_rps"][i] = np.clip(base_pattern(mod, 500, 2500) * mult + np.random.normal(0, 50), 10, 5000)

        # Fraud-Detector
        data_dict[tenant]["fraud-detector"]["cpu_pct"][i] = np.clip(base_pattern(mod, 20, 50) * mult + np.random.normal(0, 2), 5, 95)
        data_dict[tenant]["fraud-detector"]["mem_pct"][i] = np.clip(50 + np.random.normal(0, 2), 10, 95)
        data_dict[tenant]["fraud-detector"]["latency_p99_ms"][i] = np.clip(base_pattern(mod, 200, 400) + np.random.normal(0, 15), 50, 1000)
        data_dict[tenant]["fraud-detector"]["throughput_rps"][i] = data_dict[tenant]["payment-gw"]["throughput_rps"][i] * 0.9

        # Ledger
        data_dict[tenant]["ledger"]["cpu_pct"][i] = np.clip(base_pattern(mod, 15, 40) * mult + np.random.normal(0, 2), 5, 95)
        data_dict[tenant]["ledger"]["mem_pct"][i] = np.clip(60 + np.random.normal(0, 1), 10, 95)
        data_dict[tenant]["ledger"]["latency_p99_ms"][i] = np.clip(base_pattern(mod, 10, 30) + np.random.normal(0, 2), 5, 100)
        data_dict[tenant]["ledger"]["throughput_rps"][i] = data_dict[tenant]["payment-gw"]["throughput_rps"][i] * 0.8
        
        # KYC
        data_dict[tenant]["kyc"]["cpu_pct"][i] = np.clip(base_pattern(mod, 20, 60, p1_start=8, p1_end=12, p2_start=13, p2_end=15) * mult + np.random.normal(0, 3), 5, 95)
        data_dict[tenant]["kyc"]["mem_pct"][i] = np.clip(45 + np.random.normal(0, 1.5), 10, 95)
        data_dict[tenant]["kyc"]["latency_p99_ms"][i] = np.clip(base_pattern(mod, 100, 300) + np.random.normal(0, 15), 50, 1000)
        data_dict[tenant]["kyc"]["throughput_rps"][i] = np.clip(base_pattern(mod, 50, 200) * mult + np.random.normal(0, 10), 5, 500)
        
        # Reporting
        data_dict[tenant]["reporting"]["cpu_pct"][i] = np.clip(base_pattern(mod, 10, 80, p1_start=22, p1_end=23, p2_start=23.5, p2_end=24) * mult + np.random.normal(0, 4), 5, 95)
        data_dict[tenant]["reporting"]["mem_pct"][i] = np.clip(30 + np.random.normal(0, 1), 10, 95)
        data_dict[tenant]["reporting"]["latency_p99_ms"][i] = np.clip(base_pattern(mod, 500, 2000) + np.random.normal(0, 50), 100, 5000)
        data_dict[tenant]["reporting"]["throughput_rps"][i] = np.clip(base_pattern(mod, 5, 50) * mult + np.random.normal(0, 2), 1, 100)


# ==========================================
# 3. TEST SCENARIOS (INJECTED)
# ==========================================
labels = []
deploy_logs = []

def inject_anomaly(start_min, duration, tenant, service, metric, value_func, desc, is_fp=False):
    end_min = start_min + duration
    for j in range(start_min, end_min):
        if j < MINUTES:
            data_dict[tenant][service][metric][j] = value_func(data_dict[tenant][service][metric][j], j - start_min)
    
    labels.append({
        "start_time": time_index[start_min].isoformat() + "Z",
        "end_time": time_index[min(end_min, MINUTES-1)].isoformat() + "Z",
        "tenant_id": tenant,
        "service": service,
        "metric": metric,
        "description": desc,
        "is_false_positive_trap": is_fp
    })

# S1: Sudden CPU Spike (Payment, tnt-alpha)
inject_anomaly(1*1440 + 600, 15, "tnt-alpha", "payment-gw", "cpu_pct", lambda v, t: 95 + np.random.normal(0, 1), "DDoS Spike", False)

# S2: Gradual Memory Leak (Fraud, tnt-beta)
inject_anomaly(2*1440 + 300, 300, "tnt-beta", "fraud-detector", "mem_pct", lambda v, t: min(v + (t * 0.15), 99), "Memory Leak to OOM", False)

# S3: Step Change Latency (Payment, tnt-gamma)
inject_anomaly(3*1440 + 800, 120, "tnt-gamma", "payment-gw", "latency_p99_ms", lambda v, t: v + 300, "Bad Deployment N+1 Query", False)
deploy_logs.append({"ts": time_index[3*1440 + 795].isoformat() + "Z", "service": "payment-gw", "msg": "Deploy v2.1.4"})

# S4: FP Trap - Auto-scaling (Payment, tnt-alpha)
inject_anomaly(4*1440 + 600, 5, "tnt-alpha", "payment-gw", "cpu_pct", lambda v, t: 85, "Traffic surge, auto-scaled successfully", True)

# S5: FP Trap - Load Test (Payment, tnt-beta)
inject_anomaly(5*1440 + 120, 60, "tnt-beta", "payment-gw", "latency_p99_ms", lambda v, t: v + 150, "Scheduled Load Test (Chaos Eng)", True)

# S6: Very Slow CPU Drift (Ledger, tnt-alpha)
inject_anomaly(6*1440, 720, "tnt-alpha", "ledger", "cpu_pct", lambda v, t: min(v + (t * 0.05), 98), "Slow zombie process leak", False)

# S7: Silent Drop (Payment CPU drops to 0, means dead) (tnt-beta)
inject_anomaly(4*1440 + 500, 30, "tnt-beta", "payment-gw", "cpu_pct", lambda v, t: 0, "Service Crash (Silent)", False)

# S8: FP Trap - Noisy Baseline (Payment Latency highly volatile but no actual mean shift) (tnt-gamma)
inject_anomaly(5*1440 + 800, 60, "tnt-gamma", "payment-gw", "latency_p99_ms", lambda v, t: max(v + np.random.normal(0, 150), 10), "Noisy baseline (High Variance)", True)

# ==========================================
# 4. FLATTEN AND EXPORT
# ==========================================

print(f"Flattening data to Contract format (Long schema)...")
records = []
for t in tenants:
    for s in services:
        for m in metric_types:
            series = data_dict[t][s][m]
            for i in range(MINUTES):
                records.append({
                    "timestamp": time_index[i].isoformat() + "Z",
                    "tenant_id": t,
                    "service_id": s,
                    "metric_type": m,
                    "value": round(float(series[i]), 2)
                })

print(f"Converting to DataFrame ({len(records)} rows)...")
df = pd.DataFrame(records)

# Save to a single CSV or partition by day. For 7 days * 3 tenants * 5 services * 4 metrics * 1440 min = 604,800 rows
# We will save it as a single CSV for simplicity
csv_path = f"{BASE_DIR}/telemetry_data.csv"
print(f"Saving to {csv_path}...")
df.to_csv(csv_path, index=False)

with open(f"{BASE_DIR}/alerts_ground_truth.json", "w") as f:
    json.dump(labels, f, indent=2)

with open(f"{BASE_DIR}/deploy_log.json", "w") as f:
    json.dump(deploy_logs, f, indent=2)

readme = """# TF4 Foresight Lens - Data Pack (Contract Compliant)

This dataset is generated according to the Telemetry Contract for TF4.

## Schema (Long Format)
- `timestamp`: ISO8601 string
- `tenant_id`: Multi-tenant isolation identifier (e.g. tnt-alpha)
- `service_id`: Microservice name
- `metric_type`: Metric dimension (e.g., cpu_pct, latency_p99_ms)
- `value`: Float measurement

## Included Scenarios
Ground truth anomalies and False Positive (FP) traps are listed in `alerts_ground_truth.json`.
"""
with open(f"{BASE_DIR}/README.md", "w") as f:
    f.write(readme)

print(f"✅ Data-pack created successfully at: {BASE_DIR}")
print("Included: telemetry_data.csv, topology.json, alerts_ground_truth.json, deploy_log.json, README.md")

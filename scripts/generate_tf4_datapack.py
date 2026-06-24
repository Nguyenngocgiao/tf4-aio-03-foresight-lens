import os
import json
import numpy as np
import pandas as pd
from datetime import datetime, timedelta

BASE_DIR = "/home/dinh/Downloads/tf4-aio-03/data-pack"
os.makedirs(f"{BASE_DIR}/metrics", exist_ok=True)
os.makedirs(f"{BASE_DIR}/logs", exist_ok=True)

# ==========================================
# 1. TOPOLOGY
# ==========================================
topology = {
    "name": "tf4-fintech-core",
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
        {"source": "payment-gw", "target": "payment-db", "protocol": "tcp", "type": "rds_postgres"},
        {"source": "payment-gw", "target": "payment-cache", "protocol": "tcp", "type": "elasticache_redis"},
        {"source": "fraud-detector", "target": "fraud-db", "protocol": "http", "type": "dynamodb"},
        {"source": "kyc", "target": "payment-gw", "protocol": "http"}
    ]
}
with open(f"{BASE_DIR}/topology.json", "w") as f:
    json.dump(topology, f, indent=2)

# ==========================================
# 2. METRICS GENERATOR
# ==========================================
np.random.seed(42)
DAYS = 10
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

# Normal baseline
metrics = {}
services = ["payment-gw", "fraud-detector", "ledger", "kyc", "reporting"]
metric_types = ["cpu_pct", "mem_pct", "latency_p99_ms", "throughput_rps"]

for svc in services:
    for m in metric_types:
        metrics[f"{svc}_{m}"] = np.zeros(MINUTES)

# Infrastructure metrics
metrics["ledger_queue_depth"] = np.zeros(MINUTES) # SQS
metrics["payment-db_connection_pool_pct"] = np.zeros(MINUTES) # RDS Postgres
metrics["payment-cache_hit_rate_pct"] = np.zeros(MINUTES) # Redis
metrics["fraud-db_consumed_rcu"] = np.zeros(MINUTES) # DynamoDB

metrics["payment-gw_error_rate"] = np.zeros(MINUTES)
metrics["fraud-detector_error_rate"] = np.zeros(MINUTES)

for i in range(MINUTES):
    mod = i % 1440
    
    # Payment-GW
    metrics["payment-gw_cpu_pct"][i] = np.clip(base_pattern(mod, 30, 70) + np.random.normal(0, 3), 5, 95)
    metrics["payment-gw_mem_pct"][i] = np.clip(base_pattern(mod, 40, 50) + np.random.normal(0, 1), 10, 90)
    metrics["payment-gw_latency_p99_ms"][i] = np.clip(base_pattern(mod, 50, 150) + np.random.normal(0, 10), 20, 500)
    metrics["payment-gw_throughput_rps"][i] = np.clip(base_pattern(mod, 500, 2500) + np.random.normal(0, 50), 100, 5000)
    metrics["payment-gw_error_rate"][i] = np.clip(np.random.normal(0.001, 0.001), 0, 0.05)

    # Fraud-Detector
    metrics["fraud-detector_cpu_pct"][i] = np.clip(base_pattern(mod, 20, 50) + np.random.normal(0, 2), 5, 95)
    metrics["fraud-detector_mem_pct"][i] = np.clip(50 + np.random.normal(0, 2), 10, 95)
    metrics["fraud-detector_latency_p99_ms"][i] = np.clip(base_pattern(mod, 200, 400) + np.random.normal(0, 15), 50, 1000)
    metrics["fraud-detector_throughput_rps"][i] = metrics["payment-gw_throughput_rps"][i] * 0.9 # 90% traffic goes to fraud
    metrics["fraud-detector_error_rate"][i] = np.clip(np.random.normal(0.001, 0.001), 0, 0.05)

    # Ledger
    metrics["ledger_cpu_pct"][i] = np.clip(base_pattern(mod, 15, 40) + np.random.normal(0, 2), 5, 95)
    metrics["ledger_mem_pct"][i] = np.clip(60 + np.random.normal(0, 1), 10, 95)
    metrics["ledger_latency_p99_ms"][i] = np.clip(base_pattern(mod, 10, 30) + np.random.normal(0, 2), 5, 100)
    metrics["ledger_throughput_rps"][i] = metrics["payment-gw_throughput_rps"][i] * 0.8
    
    # KYC (Morning peak)
    metrics["kyc_cpu_pct"][i] = np.clip(base_pattern(mod, 20, 60, p1_start=8, p1_end=12, p2_start=13, p2_end=15) + np.random.normal(0, 3), 5, 95)
    metrics["kyc_mem_pct"][i] = np.clip(45 + np.random.normal(0, 1.5), 10, 95)
    metrics["kyc_latency_p99_ms"][i] = np.clip(base_pattern(mod, 100, 300) + np.random.normal(0, 15), 50, 1000)
    metrics["kyc_throughput_rps"][i] = np.clip(base_pattern(mod, 50, 200) + np.random.normal(0, 10), 10, 500)
    
    # Reporting (End of day batch)
    metrics["reporting_cpu_pct"][i] = np.clip(base_pattern(mod, 10, 80, p1_start=22, p1_end=23, p2_start=23.5, p2_end=24) + np.random.normal(0, 4), 5, 95)
    metrics["reporting_mem_pct"][i] = np.clip(30 + np.random.normal(0, 1), 10, 95)
    metrics["reporting_latency_p99_ms"][i] = np.clip(base_pattern(mod, 500, 2000) + np.random.normal(0, 50), 100, 5000)
    metrics["reporting_throughput_rps"][i] = np.clip(base_pattern(mod, 5, 50) + np.random.normal(0, 2), 1, 100)

    # Ledger Queue (Batch at 1 AM)
    q = np.random.exponential(50)
    if 60 <= mod <= 90: # 1:00 AM - 1:30 AM
        q += 5000 + np.random.normal(0, 500)
    metrics["ledger_queue_depth"][i] = np.clip(q, 0, 20000)

    # Payment DB & Cache
    metrics["payment-db_connection_pool_pct"][i] = np.clip(base_pattern(mod, 20, 60) + np.random.normal(0, 2), 5, 100)
    metrics["payment-cache_hit_rate_pct"][i] = np.clip(95 + np.random.normal(0, 1), 0, 100)

    # Fraud DB (DynamoDB)
    metrics["fraud-db_consumed_rcu"][i] = metrics["fraud-detector_throughput_rps"][i] * np.clip(np.random.normal(1.2, 0.1), 1, 3)

# ==========================================
# 3. 10 TEST SCENARIOS (Injected)
# ==========================================
labels = []
deploy_logs = []

def inject_anomaly(start_min, duration, series_name, value_func, desc, is_fp=False):
    end_min = start_min + duration
    for j in range(start_min, end_min):
        metrics[series_name][j] = value_func(metrics[series_name][j], j - start_min)
    
    labels.append({
        "start_time": time_index[start_min].isoformat() + "Z",
        "end_time": time_index[end_min].isoformat() + "Z",
        "service": series_name.split("_")[0],
        "metric": series_name,
        "description": desc,
        "is_false_positive_trap": is_fp
    })

# S1: Sudden CPU Spike (Payment)
inject_anomaly(1*1440 + 600, 15, "payment-gw_cpu_pct", lambda v, t: 95 + np.random.normal(0, 1), "DDoS Spike", False)

# S2: Gradual Memory Leak (Fraud)
inject_anomaly(2*1440 + 300, 300, "fraud-detector_mem_pct", lambda v, t: v + (t * 0.15), "Memory Leak to OOM", False)

# S3: Step Change Latency (Payment)
inject_anomaly(3*1440 + 800, 120, "payment-gw_latency_p99_ms", lambda v, t: v + 300, "Bad Deployment N+1 Query", False)
deploy_logs.append({"ts": time_index[3*1440 + 795].isoformat() + "Z", "service": "payment-gw", "msg": "Deploy v2.1.4"})

# S4: FP Trap - Auto-scaling (Payment)
inject_anomaly(4*1440 + 600, 5, "payment-gw_cpu_pct", lambda v, t: 85, "Traffic surge, auto-scaled successfully", True)

# S5: Queue Backlog (Ledger)
inject_anomaly(5*1440 + 700, 60, "ledger_queue_depth", lambda v, t: v + 15000 + np.random.normal(0, 1000), "SQS Worker Down", False)

# S6: FP Trap - Load Test (Payment)
inject_anomaly(6*1440 + 120, 60, "payment-gw_latency_p99_ms", lambda v, t: v + 150, "Scheduled Load Test (Chaos Eng)", True)

# S7: Very Slow CPU Drift (Payment)
inject_anomaly(7*1440, 720, "payment-gw_cpu_pct", lambda v, t: v + (t * 0.05), "Slow zombie process leak", False)

# S8: FP Trap - Expected Batch (Ledger)
inject_anomaly(8*1440 + 1300, 120, "ledger_queue_depth", lambda v, t: v + 8000, "Expected End-of-month Sync", True)

# S9: Silent Drop (Payment CPU drops to 0, means dead)
inject_anomaly(9*1440 + 500, 30, "payment-gw_cpu_pct", lambda v, t: 0, "Service Crash (Silent)", False)

# S10: FP Trap - Noisy Baseline (Payment Latency highly volatile but no actual mean shift)
inject_anomaly(9*1440 + 800, 60, "payment-gw_latency_p99_ms", lambda v, t: v + np.random.normal(0, 150), "Noisy baseline (Flash Sale / High Variance)", True)

# S11: Metric Freeze (Fraud Mem stays perfectly flat, agent stuck)
inject_anomaly(9*1440 + 1000, 120, "fraud-detector_mem_pct", lambda v, t: 60.0, "Datadog Agent Freeze (Stale Metric)", False)

# S12: Cache stampede / Connection Pool Exhaustion
inject_anomaly(5*1440 + 200, 30, "payment-cache_hit_rate_pct", lambda v, t: 30 + np.random.normal(0, 5), "Redis Eviction/Crash", False)
inject_anomaly(5*1440 + 205, 25, "payment-db_connection_pool_pct", lambda v, t: 99.5, "RDS Connection Pool Exhausted due to Cache Miss", False)

# ==========================================
# 4. EXPORT FILES
# ==========================================
with open(f"{BASE_DIR}/alerts_ground_truth.json", "w") as f:
    json.dump(labels, f, indent=2)

with open(f"{BASE_DIR}/deploy_log.json", "w") as f:
    json.dump(deploy_logs, f, indent=2)

for metric_key, series in metrics.items():
    df = pd.DataFrame({
        "timestamp": [t.isoformat() + "Z" for t in time_index],
        "value": np.round(series, 2)
    })
    df.to_csv(f"{BASE_DIR}/metrics/{metric_key}.csv", index=False)

# Generator source code
with open(__file__, "r") as src, open(f"{BASE_DIR}/_generator.py", "w") as dst:
    dst.write(src.read())

readme = """# TF4 Foresight Lens - Data Pack (Evaluation Ground Truth)

This data-pack provides the **10 Test Scenarios** required for the final evaluation of the TF4 Anomaly Detection Engine (Rolling 3-Sigma).

## Structure
- `metrics/*.csv`: 1-minute resolution telemetry for PaymentGW, FraudDetector, and Ledger.
- `alerts_ground_truth.json`: The hidden labels. Contains both True Anomalies and False Positive Traps.
- `deploy_log.json`: Contextual events that correlate with some metrics.
- `topology.json`: The microservice graph.

## The 11 Scenarios (Blind Test for the AI Engine)
1. **DDoS Spike** (Payment CPU) - [Sudden Spike]
2. **Memory Leak** (Fraud Mem) - [Slow Leak]
3. **Bad Deploy N+1** (Payment Latency)
4. **FP Trap: Auto-scaling** (Payment CPU)
5. **Worker Down** (Ledger Queue)
6. **FP Trap: Load Test** (Payment Latency)
7. **Zombie Process** (Payment CPU Drift) - [Gradual Drift]
8. **FP Trap: Expected Batch** (Ledger Queue)
9. **Service Crash** (Payment CPU silent drop)
10. **FP Trap: Noisy Baseline** (Payment Latency highly volatile) - [Noisy Baseline]
11. **Agent Freeze** (Fraud Mem stale metric)

**Goal:** The TF4 engine must trigger alerts for the actual anomalies, and **MUST REMAIN SILENT** for scenarios 4, 6, 8, and 10 to pass the `FP <= 12%` requirement.
"""
with open(f"{BASE_DIR}/README.md", "w") as f:
    f.write(readme)

print(f"✅ Data-pack created successfully at: {BASE_DIR}")
print("Included: metrics (*.csv), topology.json, alerts_ground_truth.json, README.md")

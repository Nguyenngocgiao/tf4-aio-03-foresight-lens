import os
import json
import numpy as np
import pandas as pd
from datetime import datetime, timedelta

# Correct output directory according to the assignment structure
BASE_DIR = "/home/dinh/TF4-AIO-03-foresight-lens-final/xbrain-learner/capstone-phase2/data/tf4-foresight"
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

def generate_ou_series(minutes, base_func, theta, sigma, min_val, max_val, dt=1.0):
    """
    Generate time series using the Ornstein-Uhlenbeck (Vasicek) model 
    via Euler-Maruyama method.
    dx = theta * (mu - x) * dt + sigma * sqrt(dt) * dW
    """
    series = np.zeros(minutes)
    x = base_func(0)
    for i in range(minutes):
        mu = base_func(i % 1440)
        # Euler step
        x = x + theta * (mu - x) * dt + sigma * np.sqrt(dt) * np.random.normal()
        
        # Soft reflection boundary to prevent flatlining (variance = 0) at extreme values
        if x < min_val:
            x = min_val + np.abs(x - min_val)
        elif x > max_val:
            x = max_val - np.abs(x - max_val)
            
        series[i] = x
    return series

# Structure to hold data before flattening
raw_data = []

# To make anomaly injection easier, we will hold a dictionary of arrays
# data_dict[tenant][service][metric] = np.array of size MINUTES
data_dict = {t: {s: {m: np.zeros(MINUTES) for m in metric_types} for s in services} for t in tenants}

# Base traffic multiplier per tenant
tenant_multipliers = {"tnt-alpha": 1.0, "tnt-beta": 0.6, "tnt-gamma": 0.3}

for t_idx, tenant in enumerate(tenants):
    mult = tenant_multipliers[tenant]
    
    # Payment-GW
    data_dict[tenant]["payment-gw"]["cpu_pct"] = generate_ou_series(MINUTES, lambda m: base_pattern(m, 30, 70) * mult, theta=0.1, sigma=2.0, min_val=5.0, max_val=95.0)
    data_dict[tenant]["payment-gw"]["mem_pct"] = generate_ou_series(MINUTES, lambda m: 40 * (0.8 + mult*0.2), theta=0.05, sigma=1.0, min_val=10.0, max_val=90.0)
    data_dict[tenant]["payment-gw"]["latency_p99_ms"] = generate_ou_series(MINUTES, lambda m: base_pattern(m, 50, 150), theta=0.2, sigma=10.0, min_val=20.0, max_val=500.0)
    data_dict[tenant]["payment-gw"]["throughput_rps"] = generate_ou_series(MINUTES, lambda m: base_pattern(m, 500, 2500) * mult, theta=0.3, sigma=50.0, min_val=10.0, max_val=5000.0)

    # Fraud-Detector
    data_dict[tenant]["fraud-detector"]["cpu_pct"] = generate_ou_series(MINUTES, lambda m: base_pattern(m, 20, 50) * mult, theta=0.1, sigma=1.5, min_val=5.0, max_val=95.0)
    data_dict[tenant]["fraud-detector"]["mem_pct"] = generate_ou_series(MINUTES, lambda m: 50, theta=0.05, sigma=1.5, min_val=10.0, max_val=95.0)
    data_dict[tenant]["fraud-detector"]["latency_p99_ms"] = generate_ou_series(MINUTES, lambda m: base_pattern(m, 200, 400), theta=0.2, sigma=15.0, min_val=50.0, max_val=1000.0)
    data_dict[tenant]["fraud-detector"]["throughput_rps"] = data_dict[tenant]["payment-gw"]["throughput_rps"] * 0.9

    # Ledger
    data_dict[tenant]["ledger"]["cpu_pct"] = generate_ou_series(MINUTES, lambda m: base_pattern(m, 15, 40) * mult, theta=0.1, sigma=1.5, min_val=5.0, max_val=95.0)
    data_dict[tenant]["ledger"]["mem_pct"] = generate_ou_series(MINUTES, lambda m: 60, theta=0.05, sigma=1.0, min_val=10.0, max_val=95.0)
    data_dict[tenant]["ledger"]["latency_p99_ms"] = generate_ou_series(MINUTES, lambda m: base_pattern(m, 10, 30), theta=0.2, sigma=2.0, min_val=5.0, max_val=100.0)
    data_dict[tenant]["ledger"]["throughput_rps"] = data_dict[tenant]["payment-gw"]["throughput_rps"] * 0.8
    
    # KYC
    data_dict[tenant]["kyc"]["cpu_pct"] = generate_ou_series(MINUTES, lambda m: base_pattern(m, 20, 60, p1_start=8, p1_end=12, p2_start=13, p2_end=15) * mult, theta=0.1, sigma=2.5, min_val=5.0, max_val=95.0)
    data_dict[tenant]["kyc"]["mem_pct"] = generate_ou_series(MINUTES, lambda m: 45, theta=0.05, sigma=1.2, min_val=10.0, max_val=95.0)
    data_dict[tenant]["kyc"]["latency_p99_ms"] = generate_ou_series(MINUTES, lambda m: base_pattern(m, 100, 300), theta=0.2, sigma=15.0, min_val=50.0, max_val=1000.0)
    data_dict[tenant]["kyc"]["throughput_rps"] = generate_ou_series(MINUTES, lambda m: base_pattern(m, 50, 200) * mult, theta=0.3, sigma=10.0, min_val=5.0, max_val=500.0)
    
    # Reporting
    data_dict[tenant]["reporting"]["cpu_pct"] = generate_ou_series(MINUTES, lambda m: base_pattern(m, 10, 80, p1_start=22, p1_end=23, p2_start=23.5, p2_end=24) * mult, theta=0.1, sigma=3.0, min_val=5.0, max_val=95.0)
    data_dict[tenant]["reporting"]["mem_pct"] = generate_ou_series(MINUTES, lambda m: 30, theta=0.05, sigma=1.0, min_val=10.0, max_val=95.0)
    data_dict[tenant]["reporting"]["latency_p99_ms"] = generate_ou_series(MINUTES, lambda m: base_pattern(m, 500, 2000), theta=0.2, sigma=40.0, min_val=100.0, max_val=5000.0)
    data_dict[tenant]["reporting"]["throughput_rps"] = generate_ou_series(MINUTES, lambda m: base_pattern(m, 5, 50) * mult, theta=0.3, sigma=2.0, min_val=1.0, max_val=100.0)


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

np.random.seed(123)

# Inject 100 REAL anomalies and 100 FALSE POSITIVE traps randomly
for i in range(200):
    t = np.random.choice(tenants)
    s = np.random.choice(services)
    m = np.random.choice(metric_types)
    
    # Random start time (leave first day for clean baseline)
    start_min = np.random.randint(1440, MINUTES - 1440)
    
    is_fp = i >= 100  # First 100 are real, next 100 are traps
    
    if not is_fp:
        # REAL ANOMALIES
        anomaly_type = np.random.choice(["spike", "leak", "drop"])
        if anomaly_type == "spike":
            inject_anomaly(start_min, np.random.randint(15, 60), t, s, m, lambda v, time: v * np.random.uniform(2.5, 4.0), f"Real Spike ({m})", False)
        elif anomaly_type == "leak":
            inject_anomaly(start_min, np.random.randint(120, 300), t, s, m, lambda v, time: v + (time * np.random.uniform(0.1, 0.5)), f"Gradual Leak ({m})", False)
        else: # drop
            inject_anomaly(start_min, np.random.randint(20, 60), t, s, m, lambda v, time: v * 0.1, f"Silent Drop ({m})", False)
            if s == "payment-gw":
                deploy_logs.append({"ts": time_index[start_min - 5].isoformat() + "Z", "service": s, "msg": f"Deploy v{np.random.randint(1,4)}.{np.random.randint(0,9)}.0"})
    else:
        # FALSE POSITIVE TRAPS (Noise, tiny blips)
        trap_type = np.random.choice(["noise", "micro_spike"])
        if trap_type == "noise":
            # High variance but mean remains same
            inject_anomaly(start_min, np.random.randint(30, 90), t, s, m, lambda v, time: v + np.random.normal(0, abs(v) * 0.5 + 0.1), f"Noisy Baseline ({m})", True)
        else:
            # Huge spike but only lasts 1-2 minutes (should be ignored by 3-consecutive-point rule)
            inject_anomaly(start_min, np.random.randint(1, 3), t, s, m, lambda v, time: v * 5.0, f"Micro Spike ({m})", True)


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
                record = {
                    "timestamp": time_index[i].isoformat() + "Z",
                    "tenant_id": t,
                    "service_id": s,
                    "metric_type": m,
                    "value": round(float(series[i]), 2)
                }
                
                # Inject PII in ~5% of records to test "schema whitelist, reject ingest" requirement
                if np.random.rand() < 0.05:
                    pii_types = [
                        {"customer_email": f"user{np.random.randint(1000, 9999)}@gmail.com"},
                        {"card_number": f"4242-4242-4242-{np.random.randint(1000, 9999)}"},
                        {"ssn": f"{np.random.randint(100, 999)}-{np.random.randint(10, 99)}-{np.random.randint(1000, 9999)}"}
                    ]
                    record["metadata"] = json.dumps(np.random.choice(pii_types))
                
                records.append(record)

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

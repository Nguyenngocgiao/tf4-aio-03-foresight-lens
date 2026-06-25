import json
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from pathlib import Path

# Paths
BASE_DIR = Path("/home/dinh/TF4-AIO-03-foresight-lens-final")
DATA_DIR = BASE_DIR / "xbrain-learner/capstone-phase2/data/tf4-foresight"
OUT_DIR = BASE_DIR / "tf4-evidence/evidence"
OUT_DIR.mkdir(parents=True, exist_ok=True)

# 1. Visualize Model Comparison
print("Plotting model comparison metrics...")
with open(OUT_DIR / "evidence_algorithm_evaluation.json", "r") as f:
    eval_data = json.load(f)

results = eval_data["results"]
models = ["ewma_stl", "iforest", "oc_svm", "lof", "llm"]
labels = ["3-Sigma (EWMA)", "Isolation Forest", "One-Class SVM", "LOF", "LLM (GenAI)"]
recalls = [results[m]["recall"] * 100 for m in models]
fprs = [results[m]["fp_rate"] * 100 for m in models]

x = np.arange(len(labels))
width = 0.35

fig, ax = plt.subplots(figsize=(10, 6))
rects1 = ax.bar(x - width/2, recalls, width, label='Catch Rate (TP) %', color='green')
rects2 = ax.bar(x + width/2, fprs, width, label='False Positive Rate %', color='red')

ax.set_ylabel('Percentage (%)')
ax.set_title('Algorithm Evaluation: Catch Rate vs False Positive Rate')
ax.set_xticks(x)
ax.set_xticklabels(labels)
ax.legend()
ax.axhline(y=80, color='g', linestyle='--', alpha=0.5, label='Target Catch (80%)')
ax.axhline(y=12, color='r', linestyle='--', alpha=0.5, label='Target FP Limit (12%)')

# Attach a text label above each bar
for rect in rects1:
    height = rect.get_height()
    ax.annotate(f'{height:.0f}%', xy=(rect.get_x() + rect.get_width() / 2, height),
                xytext=(0, 3), textcoords="offset points", ha='center', va='bottom')
for rect in rects2:
    height = rect.get_height()
    ax.annotate(f'{height:.0f}%', xy=(rect.get_x() + rect.get_width() / 2, height),
                xytext=(0, 3), textcoords="offset points", ha='center', va='bottom')

plt.tight_layout()
plt.savefig(OUT_DIR / "metrics_comparison.png")
plt.close()

# 2. Visualize the EWMA on a specific time series scenario
print("Plotting EWMA visualization on telemetry data...")
df = pd.read_csv(DATA_DIR / "telemetry_data.csv")
df['timestamp'] = pd.to_datetime(df['timestamp'])

with open(DATA_DIR / "alerts_ground_truth.json", "r") as f:
    ground_truth = json.load(f)

# Pick a specific scenario: Memory Leak for tnt-beta
gt_leak = None
for gt in ground_truth:
    if gt["service"] == "fraud-detector" and gt["metric"] == "mem_pct" and not gt["is_false_positive_trap"]:
        gt_leak = gt
        break

if gt_leak:
    tenant = gt_leak["tenant_id"]
    service = gt_leak["service"]
    metric = gt_leak["metric"]
    start_time = pd.to_datetime(gt_leak["start_time"])
    end_time = pd.to_datetime(gt_leak["end_time"])

    # 4 hours window
    buffer_start = start_time - pd.Timedelta(hours=3)
    mask = (df["tenant_id"] == tenant) & (df["service_id"] == service) & (df["metric_type"] == metric) & (df["timestamp"] >= buffer_start) & (df["timestamp"] <= end_time + pd.Timedelta(minutes=30))
    sub_df = df[mask].sort_values("timestamp")

    if len(sub_df) > 0:
        series = sub_df["value"].values
        timestamps = sub_df["timestamp"].values
        
        # Calculate EWMA
        alpha = 0.1
        ewma = np.zeros_like(series)
        ewma[0] = series[0]
        for i in range(1, len(series)):
            ewma[i] = alpha * series[i] + (1 - alpha) * ewma[i-1]
            
        residuals = series - ewma
        upper_bound = np.zeros_like(series)
        lower_bound = np.zeros_like(series)
        anomalies = []
        
        window = 60
        sigma = 3.0
        consecutive = 0
        
        for i in range(len(series)):
            if i < window:
                upper_bound[i] = ewma[i]
                lower_bound[i] = ewma[i]
                continue
                
            baseline = residuals[i-window:i]
            std = np.std(baseline)
            if std < 1e-5: std = 1.0
            
            upper = ewma[i] + sigma * std
            lower = ewma[i] - sigma * std
            upper_bound[i] = upper
            lower_bound[i] = lower
            
            if series[i] > upper or series[i] < lower:
                consecutive += 1
            else:
                consecutive = 0
                
            if consecutive >= 3:
                anomalies.append((timestamps[i], series[i]))

        plt.figure(figsize=(14, 7))
        plt.plot(timestamps, series, label='Raw Telemetry', color='blue', alpha=0.6)
        plt.plot(timestamps, ewma, label='EWMA Baseline', color='black', linewidth=1.5)
        
        # We only plot bounds after window
        plt.fill_between(timestamps[window:], lower_bound[window:], upper_bound[window:], color='orange', alpha=0.2, label='3-Sigma Bound')
        
        # Plot Anomalies
        if anomalies:
            ax, ay = zip(*anomalies)
            plt.scatter(ax, ay, color='red', label='EWMA Alert (3 consec.)', zorder=5, marker='x')

        plt.axvspan(start_time, end_time, color='red', alpha=0.1, label='Ground Truth Leak Window')

        plt.title(f"EWMA Detection on {tenant} | {service} | {metric}")
        plt.xlabel("Time")
        plt.ylabel("Value (%)")
        plt.legend()
        plt.grid(True, alpha=0.3)
        plt.tight_layout()
        plt.savefig(OUT_DIR / "scenario_ewma_visualized.png")
        plt.close()

print("Done! Visualizations saved.")

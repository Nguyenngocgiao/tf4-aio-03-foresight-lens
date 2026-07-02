import json
from pathlib import Path
import numpy as np

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

REPO = Path(__file__).resolve().parents[1]
BASELINE_DIR = REPO / "engine-skeleton" / "baselines"
EVID_DIR = REPO / "tf4-evidence" / "evidence"

SERVICES = ["payment-gw", "fraud-detector", "ledger"]
METRICS = ["cpu_usage_percent", "memory_usage_percent", "api_latency_ms", "queue_depth"]

COLORS = {
    "api_latency_ms": "#D81B60",
    "queue_depth": "#ED7100",
    "cpu_usage_percent": "#1E88E5",
    "memory_usage_percent": "#F9A825",
}

def plot_service_profile(service):
    base_file = BASELINE_DIR / f"{service}.json"
    if not base_file.exists():
        return
    
    data = json.loads(base_file.read_text())
    metrics_data = data.get("metrics", {})
    
    fig, axes = plt.subplots(4, 1, figsize=(10, 8), sharex=True)
    fig.suptitle(f"Expected Daily Seasonal Profile - {service.upper()}", fontsize=14)
    
    x = np.arange(1440) / 60.0  # Hours of the day
    
    for i, metric in enumerate(METRICS):
        if metric in metrics_data:
            profile = metrics_data[metric]["seasonal_profile"]
            ax = axes[i]
            ax.plot(x, profile, color=COLORS.get(metric, "#888"), lw=2, label=metric)
            ax.set_ylabel(metric.replace("_", "\n"), fontsize=9)
            ax.grid(axis="y", alpha=0.3)
            ax.legend(loc="upper right", fontsize=8)
            
    axes[-1].set_xlabel("Hour of Day (0-24)")
    axes[-1].set_xticks(np.arange(0, 25, 2))
    
    fig.tight_layout()
    out_path = EVID_DIR / f"service_{service}_profile.png"
    fig.savefig(out_path, dpi=110)
    plt.close(fig)
    print(f"Saved {out_path.name}")

def plot_cpu_comparison():
    fig, ax = plt.subplots(figsize=(10, 4))
    
    x = np.arange(1440) / 60.0
    svc_colors = {"payment-gw": "#1E88E5", "fraud-detector": "#D81B60", "ledger": "#F9A825"}
    
    for service in SERVICES:
        base_file = BASELINE_DIR / f"{service}.json"
        if base_file.exists():
            data = json.loads(base_file.read_text())
            if "cpu_usage_percent" in data["metrics"]:
                profile = data["metrics"]["cpu_usage_percent"]["seasonal_profile"]
                ax.plot(x, profile, lw=2, label=service, color=svc_colors.get(service))
                
    ax.set_title("CPU Usage Profile Comparison Across Services", fontsize=12)
    ax.set_xlabel("Hour of Day (0-24)")
    ax.set_ylabel("CPU Usage (%)")
    ax.set_xticks(np.arange(0, 25, 2))
    ax.grid(axis="y", alpha=0.3)
    ax.legend(title="Service")
    
    fig.tight_layout()
    out_path = EVID_DIR / "service_comparison_cpu.png"
    fig.savefig(out_path, dpi=110)
    plt.close(fig)
    print(f"Saved {out_path.name}")

def main():
    print("Generating updated profile charts...")
    for svc in SERVICES:
        plot_service_profile(svc)
    plot_cpu_comparison()
    print("Done!")

if __name__ == "__main__":
    main()

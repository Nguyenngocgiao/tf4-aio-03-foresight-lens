"""Regenerate the metric-priority evidence charts from the IN-REPO evidence JSON.

Repo-relative + reproducible (no hardcoded machine paths, no fabricated models).
Reads tf4-evidence/evidence/evidence_metric_priority.json (canonical metric_type
names) and writes:
  - metric_priority_chart.png       (average detection rank per metric)
  - metric_priority_multi_root.png  (detection lag per metric across 4 root causes)

Run:  python scripts/plot_evidence.py

Note: the algorithm A/B chart (algorithm_comparison.png) is produced separately by
tf4-evidence/tf4_evidence.py (measured EWMA+STL vs Isolation Forest) and is not
touched here.
"""
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

REPO = Path(__file__).resolve().parents[1]
EVID = REPO / "tf4-evidence" / "evidence"
DRIFT_ONSET_MIN = 720  # injections start at ~t=12h; detection_times are absolute minutes

# stable colour per metric; api_latency_ms highlighted as the first-to-detect signal
COLORS = {
    "api_latency_ms": "#D81B60",
    "queue_depth": "#ED7100",
    "cpu_usage_percent": "#1E88E5",
    "memory_usage_percent": "#F9A825",
}


def load():
    return json.loads((EVID / "evidence_metric_priority.json").read_text())


def chart_average_rank(data):
    avg = data["average_rank"]
    metrics = sorted(avg, key=avg.get)  # best (lowest rank) first
    vals = [avg[m] for m in metrics]
    fig, ax = plt.subplots(figsize=(11.5, 4.5))
    y = np.arange(len(metrics))[::-1]  # best on top
    ax.barh(y, vals, color=[COLORS.get(m, "#888") for m in metrics], height=0.6)
    for yi, v in zip(y, vals):
        ax.annotate(f"{v:.2f}", (v, yi), xytext=(4, 0), textcoords="offset points",
                    va="center", fontsize=10, fontweight="bold")
    ax.set_yticks(y)
    ax.set_yticklabels(metrics)
    ax.set_xlabel("Average detection rank across 4 root causes (1 = detects first)")
    ax.set_xlim(0, max(vals) + 0.6)
    ax.set_title("Metric Priority — average detection order\n"
                 f"Final order: {'  >  '.join(data['final_rank'])}", fontsize=12)
    ax.grid(axis="x", alpha=0.3)
    fig.tight_layout()
    fig.savefig(EVID / "metric_priority_chart.png", dpi=110)
    plt.close(fig)


def chart_multi_root(data):
    roots = data["root_causes"]
    metrics = data["final_rank"]  # consistent legend order
    labels = [rc["root_cause"] for rc in roots]
    x = np.arange(len(roots))
    n = len(metrics)
    w = 0.8 / n
    fig, ax = plt.subplots(figsize=(11, 5.5))
    for i, m in enumerate(metrics):
        lags = [rc["detection_times"][m] - DRIFT_ONSET_MIN for rc in roots]
        ax.bar(x + (i - (n - 1) / 2) * w, lags, w, label=m, color=COLORS.get(m, "#888"))
    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=10)
    ax.set_ylabel(f"Detection lag (min after drift onset ~t={DRIFT_ONSET_MIN})")
    ax.set_title("Metric Priority — detection lag per metric across 4 root causes\n"
                 "api_latency_ms is first-to-detect in 4/4", fontsize=12)
    ax.legend(title="metric_type", fontsize=9)
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    fig.savefig(EVID / "metric_priority_multi_root.png", dpi=110)
    plt.close(fig)


def main():
    data = load()
    chart_average_rank(data)
    chart_multi_root(data)
    print("Wrote metric_priority_chart.png + metric_priority_multi_root.png")
    print("final_rank:", " > ".join(data["final_rank"]))


if __name__ == "__main__":
    main()

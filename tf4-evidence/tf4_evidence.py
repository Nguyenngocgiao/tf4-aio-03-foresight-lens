"""TF4 evidence orchestrator (honest, repo-relative).

Single source of truth for evaluation is eval_engine.py, which scores the REAL
serving engine (STL baseline + EWMA control chart) on a held-out labelled day.
This script:
  1. runs that harness -> evidence_algorithm_evaluation.json (measured, not hardcoded),
  2. runs an Isolation Forest baseline on the same holdout windows for an honest A/B,
  3. writes evidence_algorithm_comparison.json + algorithm_comparison.png.

There are NO hardcoded confusion-matrix values anywhere; every number comes from a run.
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parents[1]
EVID = REPO / "tf4-evidence" / "evidence"
sys.path.insert(0, str(REPO / "tf4-evidence"))
sys.path.insert(0, str(REPO / "engine-skeleton"))

import eval_engine as ev  # noqa: E402

METRICS = ev.METRICS
WINDOW, STEP = ev.WINDOW, ev.STEP


def isolation_forest_scores():
    """Honest A/B: Isolation Forest on the same holdout windows (FP / recall)."""
    from sklearn.ensemble import IsolationForest
    cm = {"tp": 0, "fp": 0, "fn": 0, "tn": 0}
    for svc in ev.SERVICES:
        df = pd.read_csv(EVID / f"holdout_{svc}.csv")
        labels = json.loads((EVID / f"holdout_{svc}_labels.json").read_text())
        X = df[METRICS].to_numpy(dtype=float)
        for end in range(WINDOW, len(df), STEP):
            win = X[end - WINDOW:end]
            clf = IsolationForest(contamination=0.02, random_state=42).fit(win[:-15])
            alert = bool((clf.predict(win[-5:]) == -1).any())
            is_true, _ = ev.true_region_at(end - 1, labels)
            key = ("tp" if alert else "fn") if is_true else ("fp" if alert else "tn")
            cm[key] += 1
    tp, fp, fn, tn = cm["tp"], cm["fp"], cm["fn"], cm["tn"]
    return {
        "confusion_matrix": cm,
        "recall": round(tp / (tp + fn), 3) if tp + fn else 0.0,
        "fp_rate": round(fp / (fp + tn), 3) if fp + tn else 0.0,
    }


def main():
    print("Running engine eval (STL + EWMA)...")
    engine = ev.evaluate()
    print("Running Isolation Forest baseline...")
    iforest = isolation_forest_scores()

    comparison = {
        "ewma_stl": {"recall": engine["recall"], "fp_rate": engine["fp_rate"],
                     "f1": engine["f1"], "lead_time_min": engine["lead_time_min"]},
        "iforest": iforest,
        "requirements": "FP <= 12%, Catch >= 80%",
    }
    (EVID / "evidence_algorithm_comparison.json").write_text(json.dumps(comparison, indent=2))
    print(json.dumps(comparison, indent=2))

    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        algos = ["EWMA+STL", "IsolationForest"]
        fp = [engine["fp_rate"] * 100, iforest["fp_rate"] * 100]
        rc = [engine["recall"] * 100, iforest["recall"] * 100]
        x = np.arange(len(algos))
        fig, ax = plt.subplots(figsize=(7, 4))
        ax.bar(x - 0.2, fp, 0.4, label="FP rate %")
        ax.bar(x + 0.2, rc, 0.4, label="Recall %")
        ax.axhline(12, ls="--", color="r", lw=1, label="FP limit 12%")
        ax.set_xticks(x); ax.set_xticklabels(algos); ax.legend()
        ax.set_title("Foresight Lens — measured algorithm comparison (holdout)")
        fig.tight_layout(); fig.savefig(EVID / "algorithm_comparison.png", dpi=110)
        print("Saved algorithm_comparison.png")
    except Exception as e:
        print(f"(plot skipped: {e})")


if __name__ == "__main__":
    main()

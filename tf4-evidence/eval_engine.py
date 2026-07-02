"""Honest evaluation of the Foresight Lens engine on held-out, labelled telemetry.

Slides a 120-min window across the holdout day for each of the 3 tier-1 services,
calls the REAL engine (STL baseline + EWMA control chart), and scores every window
against ground-truth anomaly regions (including a noisy false-positive trap).

Outputs measured precision / recall / F1 / FP-rate / lead-time + a confusion matrix
to tf4-evidence/evidence/evidence_algorithm_evaluation.json. No hardcoded numbers.
"""
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "engine-skeleton"))
from app.engine import AnomalyDetector  # noqa: E402

EVID = REPO / "tf4-evidence" / "evidence"
SERVICES = ["payment-gw", "fraud-detector", "ledger"]
METRICS = ["cpu_usage_percent", "memory_usage_percent", "api_latency_ms", "queue_depth"]
WINDOW = 120
STEP = 5
BREACH_LEVEL = {"cpu_usage_percent": 90, "memory_usage_percent": 90, "api_latency_ms": 600, "queue_depth": 9999}

detector = AnomalyDetector()


def row_to_signals(df_win: pd.DataFrame, service: str):
    sigs = []
    for _, r in df_win.iterrows():
        ts = pd.Timestamp(r["ts"].replace("Z", ""))
        for m in METRICS:
            sigs.append(SimpleNamespace(ts=ts.to_pydatetime(), service_id=service,
                                        metric_type=m, value=float(r[m])))
    return sigs


def true_region_at(idx, labels):
    """Return (is_true_anomaly, is_fp_trap) for a window whose last point is at row idx.

    Label `start`/`end` are absolute minute indices into the full 7-day dataset;
    the holdout CSV is day 7 (rows 0..1439), so shift labels by 6*1440 to map them
    onto holdout row indices. The 3 services intentionally share ONE label file:
    anomalies are injected at the same day-relative minutes in every service
    (controlled experiment), while the underlying per-service baselines differ.
    """
    is_true = is_fp = False
    for lb in labels:
        # 6*1440 = shift from absolute 7-day minute coords to the day-7 holdout row.
        if lb["start"] - 6 * 1440 <= idx <= lb["end"] - 6 * 1440:
            if lb["kind"] == "noisy_fp_trap":
                is_fp = True
            else:
                is_true = True
    return is_true, is_fp


def evaluate():
    cm = {"tp": 0, "fp": 0, "fn": 0, "tn": 0}
    lead_times = []
    per_service = {}
    brier_pairs = []  # (predicted_prob, outcome) for calibration
    for svc in SERVICES:
        df = pd.read_csv(EVID / f"holdout_{svc}.csv")
        labels = json.loads((EVID / f"holdout_{svc}_labels.json").read_text())
        s_cm = {"tp": 0, "fp": 0, "fn": 0, "tn": 0}
        first_alert_min = {}
        for end in range(WINDOW, len(df), STEP):
            win = df.iloc[end - WINDOW:end]
            anomaly, sev, rec, reason, conf = detector.detect_drift("tnt-eval", row_to_signals(win, svc))
            is_true, is_fp = true_region_at(end - 1, labels)
            # calibration: predicted prob of anomaly = confidence if alert else (1-confidence)
            pred_prob = conf if anomaly else round(1.0 - conf, 3)
            brier_pairs.append((pred_prob, 1 if is_true else 0))
            if is_true:
                if anomaly:
                    s_cm["tp"] += 1
                else:
                    s_cm["fn"] += 1
            else:
                if anomaly:
                    s_cm["fp"] += 1
                else:
                    s_cm["tn"] += 1
            # capture first alert per labelled region for lead-time
            if anomaly:
                for lb in labels:
                    lo, hi = lb["start"] - 6 * 1440, lb["end"] - 6 * 1440
                    if lb["kind"] in ("slow_leak", "gradual_drift") and lo <= end - 1 <= hi:
                        first_alert_min.setdefault(lb["kind"], end - 1)
        # lead time = breach point - first alert, for the slow-leak region
        for lb in labels:
            if lb["kind"] in first_alert_min:
                lo = lb["start"] - 6 * 1440
                metric = lb["metric"]
                seg = df[metric].to_numpy()[lo:lb["end"] - 6 * 1440]
                breach_idx = next((lo + k for k, v in enumerate(seg) if v >= BREACH_LEVEL[metric]), lb["end"] - 6 * 1440)
                lead = breach_idx - first_alert_min[lb["kind"]]
                if lead > 0:
                    lead_times.append(lead)
        per_service[svc] = s_cm
        for k in cm:
            cm[k] += s_cm[k]

    tp, fp, fn, tn = cm["tp"], cm["fp"], cm["fn"], cm["tn"]
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    fp_rate = fp / (fp + tn) if fp + tn else 0.0

    def wilson_ci(x, n, z=1.96):
        """95% Wilson score interval for a proportion x/n (better than normal approx at edges)."""
        if n == 0:
            return [None, None]
        p = x / n
        d = 1 + z * z / n
        centre = (p + z * z / (2 * n)) / d
        half = z * ((p * (1 - p) / n + z * z / (4 * n * n)) ** 0.5) / d
        return [round(centre - half, 3), round(centre + half, 3)]
    brier = float(np.mean([(p - o) ** 2 for p, o in brier_pairs])) if brier_pairs else None
    # Brier skill vs. climatology: a raw Brier score is only meaningful against the
    # "always predict the base rate" forecast, whose Brier equals p*(1-p) at prevalence p.
    base_rate = (tp + fn) / (tp + fp + fn + tn)
    brier_climatology = base_rate * (1 - base_rate)
    brier_skill = 1 - brier / brier_climatology if brier is not None and brier_climatology else None
    from app.engine import EWMA_ALPHA, SIGMA_K
    out = {
        "method": f"STL(period=1440) seasonal baseline + EWMA(alpha={EWMA_ALPHA}) control chart, K={SIGMA_K}",
        "requirements": "FP <= 12%, Catch >= 80%, Lead >= 15min",
        "eval_setup": f"{len(SERVICES)} services, holdout day, {WINDOW}-min sliding window step {STEP}",
        "confusion_matrix": cm,
        "precision": round(precision, 3),
        "recall": round(recall, 3),
        "f1": round(f1, 3),
        "fp_rate": round(fp_rate, 3),
        "ci95": {
            "recall": wilson_ci(tp, tp + fn),
            "precision": wilson_ci(tp, tp + fp),
            "fp_rate": wilson_ci(fp, fp + tn),
        },
        "ci95_method": "Wilson score interval, 95% (z=1.96), from the aggregate confusion matrix",
        "brier_score": round(brier, 4) if brier is not None else None,
        "brier_baseline": {
            "base_rate": round(base_rate, 4),
            "brier_climatology": round(brier_climatology, 4),
            "brier_skill_score": round(brier_skill, 4) if brier_skill is not None else None,
        },
        "lead_time_min": int(np.median(lead_times)) if lead_times else None,
        "lead_time_samples": lead_times,
        "per_service": per_service,
    }
    (EVID / "evidence_algorithm_evaluation.json").write_text(json.dumps(out, indent=2))
    print(json.dumps(out, indent=2))
    return out


if __name__ == "__main__":
    evaluate()

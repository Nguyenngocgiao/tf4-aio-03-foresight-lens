import numpy as np
from typing import List, Tuple
from .models import SignalDatapoint

class AnomalyDetector:
    def __init__(self):
        # In a real scenario, baselines would be loaded from a DB per tenant/service.
        pass

    def generate_recommendation(self, metric: str, tenant_id: str, baseline_info: str = "") -> Tuple[dict, str, float]:
        """Returns (Recommendation dict, reasoning, confidence)"""
        confidence = 0.85
        if metric == "cpu_usage_percent":
            rec = {"action_verb": "SCALE_UP", "target": f"{tenant_id} ECS Service", "from_to": "Current -> +2 Tasks", "evidence_link": f"https://dashboard.internal/metrics/{tenant_id}/cpu", "confidence": confidence}
            return rec, f"CPU drift detected{baseline_info}. Scale ECS Service for {tenant_id}.", confidence
        elif metric == "queue_depth":
            rec = {"action_verb": "SCALE_UP", "target": f"{tenant_id} SQS Workers", "from_to": "Current -> +5 Workers", "evidence_link": f"https://dashboard.internal/metrics/{tenant_id}/queue", "confidence": confidence}
            return rec, f"Queue backlog detected{baseline_info}. Increase worker concurrency for {tenant_id}.", confidence
        elif metric == "memory_usage_percent":
            rec = {"action_verb": "ROLLBACK", "target": f"{tenant_id} Deployment", "from_to": "v_latest -> v_previous", "evidence_link": f"https://dashboard.internal/metrics/{tenant_id}/mem", "confidence": confidence}
            return rec, f"Memory leak detected for {tenant_id}{baseline_info}. Consider rollback.", confidence
        elif metric in ["active_connections", "db_connection_pool_pct", "cache_hit_rate_pct"]:
            rec = {"action_verb": "INVESTIGATE", "target": f"{tenant_id} Database/Cache", "from_to": "N/A", "evidence_link": f"https://dashboard.internal/metrics/{tenant_id}/db", "confidence": confidence}
            return rec, f"Database or cache saturation detected for {tenant_id}{baseline_info}.", confidence
        else:
            rec = {"action_verb": "INVESTIGATE", "target": f"{tenant_id}", "from_to": "N/A", "evidence_link": f"https://dashboard.internal/metrics/{tenant_id}", "confidence": confidence}
            return rec, f"Anomalous metric {metric} detected for {tenant_id}{baseline_info}.", confidence

    def detect_drift(self, tenant_id: str, signals: List[SignalDatapoint]) -> Tuple[bool, float, dict, str, float]:
        """
        Runs ewma_stl logic on the signals.
        Returns: (anomaly_bool, severity, suggested_action, reasoning, confidence)
        """
        if not signals:
            return False, 0.0, None, "No signals provided", 1.0

        # Group by signal_name
        signal_dict = {}
        for s in signals:
            if s.signal_name not in signal_dict:
                signal_dict[s.signal_name] = []
            signal_dict[s.signal_name].append(s.value)

        for metric, values in signal_dict.items():
            if len(values) < 3:
                continue # Not enough data to calculate std
            
            baseline_vals = values[:-1]
            last_val = values[-1]
            
            mean_val = np.mean(baseline_vals)
            std_val = np.std(baseline_vals)
            
            if std_val == 0:
                std_val = 1.0 # default small std to allow catching spikes when baseline is perfectly flat

            # Two-tailed: catch both spike UP and drop DOWN
            if last_val > mean_val + 3 * std_val:
                severity = min((last_val - mean_val) / (10 * std_val), 1.0)
                baseline_info = f" (Value {last_val:.2f} > Threshold {mean_val + 3 * std_val:.2f})"
                action, reasoning, confidence = self.generate_recommendation(metric, tenant_id, baseline_info)
                return True, round(float(severity), 2), action, reasoning, confidence
            elif last_val < mean_val - 3 * std_val:
                severity = min((mean_val - last_val) / (10 * std_val), 1.0)
                action = {"action_verb": "INVESTIGATE", "target": f"{tenant_id}", "from_to": "N/A", "evidence_link": f"https://dashboard.internal/metrics/{tenant_id}", "confidence": 0.80}
                reasoning = f"Sudden drop in {metric} for {tenant_id} (Value {last_val:.2f} < Threshold {mean_val - 3 * std_val:.2f}). Possible service degradation or outage."
                confidence = 0.80
                return True, round(float(severity), 2), action, reasoning, confidence

        return False, 0.0, None, "No anomaly detected within ewma_stl thresholds.", 0.95

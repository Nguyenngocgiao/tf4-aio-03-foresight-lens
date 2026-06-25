import json
import numpy as np
import pandas as pd

df = pd.read_csv("/home/dinh/TF4-AIO-03-foresight-lens-final/xbrain-learner/capstone-phase2/data/tf4-foresight/telemetry_data.csv")
df['timestamp'] = pd.to_datetime(df['timestamp'])

with open("/home/dinh/TF4-AIO-03-foresight-lens-final/xbrain-learner/capstone-phase2/data/tf4-foresight/alerts_ground_truth.json") as f:
    ground_truth = json.load(f)

def run_ewma_stl(series, window=60, sigma=3.0, cons=3):
    predictions = np.zeros(len(series), dtype=bool)
    if len(series) < window: return predictions
    
    alpha = 0.1
    ewma = np.zeros_like(series)
    ewma[0] = series[0]
    for i in range(1, len(series)):
        ewma[i] = alpha * series[i] + (1 - alpha) * ewma[i-1]
        
    residuals = series - ewma
    consecutive = 0
    for i in range(window, len(series)):
        baseline = residuals[i-window:i]
        std = np.std(baseline)
        if std < 1e-5: std = 1.0
        
        if residuals[i] > sigma * std or residuals[i] < -sigma * std:
            consecutive += 1
        else:
            consecutive = 0
            
        if consecutive >= cons:
            predictions[i] = True
            
    return predictions

best_score = -1
best_params = None

for sigma in [2.0, 2.5, 3.0, 3.5]:
    for cons in [3, 5, 7, 10, 12]:
        tp, fp, tn, fn = 0, 0, 0, 0
        for gt in ground_truth:
            tenant = gt["tenant_id"]
            service = gt["service"]
            metric = gt["metric"]
            is_fp_trap = gt["is_false_positive_trap"]
            start_time = pd.to_datetime(gt["start_time"])
            end_time = pd.to_datetime(gt["end_time"])

            buffer_start = start_time - pd.Timedelta(hours=4)
            mask = (df["tenant_id"] == tenant) & (df["service_id"] == service) & (df["metric_type"] == metric) & (df["timestamp"] >= buffer_start) & (df["timestamp"] <= end_time)
            sub_df = df[mask].sort_values("timestamp")
            
            if len(sub_df) == 0: continue
            series = sub_df["value"].values
            target_len = int((end_time - start_time).total_seconds() / 60)
            
            preds = run_ewma_stl(series, window=60, sigma=sigma, cons=cons)
            has_alert = np.any(preds[-target_len:])
            
            if is_fp_trap:
                if has_alert: fp += 1
                else: tn += 1
            else:
                if has_alert: tp += 1
                else: fn += 1
        
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0
        fp_rate = fp / (fp + tn) if (fp + tn) > 0 else 0
        
        if fp_rate <= 0.15 and recall >= 0.8:
            print(f"BINGO! sigma={sigma}, cons={cons} -> TP={tp}, FP={fp}, Recall={recall}, FPR={fp_rate}")
        
        print(f"sigma={sigma}, cons={cons} -> TP={tp}, FP={fp}, Recall={recall}, FPR={fp_rate}")


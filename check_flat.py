import pandas as pd
import numpy as np

csv_path = "/home/dinh/Downloads/tf4-aio-03/xbrain-learner/capstone-phase2/data/tf4-foresight/telemetry_data.csv"
try:
    df = pd.read_csv(csv_path)
    # Check for flatlines (variance = 0 over windows)
    for t in df['tenant_id'].unique():
        for s in df['service_id'].unique():
            for m in df['metric_type'].unique():
                series = df[(df['tenant_id'] == t) & (df['service_id'] == s) & (df['metric_type'] == m)]['value'].values
                if len(series) == 0: continue
                # Count how many times it hits the extreme bounds exactly
                min_val, max_val = np.min(series), np.max(series)
                # If there are too many identical max/min values, it means it's clipped too hard
                max_count = np.sum(series == max_val)
                min_count = np.sum(series == min_val)
                if max_count > 100 or min_count > 100:
                    print(f"Warning: {t} {s} {m} is hitting bounds heavily. Max_val={max_val} ({max_count} times), Min_val={min_val} ({min_count} times)")
except Exception as e:
    print(e)

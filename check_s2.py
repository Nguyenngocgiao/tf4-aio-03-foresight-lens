import pandas as pd
import numpy as np

csv_path = "/home/dinh/Downloads/tf4-aio-03/xbrain-learner/capstone-phase2/data/tf4-foresight/telemetry_data.csv"
try:
    df = pd.read_csv(csv_path)
    series = df[(df['tenant_id'] == 'tnt-beta') & (df['service_id'] == 'fraud-detector') & (df['metric_type'] == 'mem_pct')]['value'].values
    start_idx = 2*1440 + 300
    print("Pre-anomaly S2 values (last 5):", series[start_idx-5:start_idx])
    print("Anomaly S2 values (first 5):", series[start_idx:start_idx+5])
    print("Anomaly S2 values (last 5):", series[start_idx+300-5:start_idx+300])
    print("Post-anomaly S2 values (first 5):", series[start_idx+300:start_idx+305])
except Exception as e:
    print(e)

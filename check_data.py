import pandas as pd
import numpy as np

csv_path = "/home/dinh/Downloads/tf4-aio-03/xbrain-learner/capstone-phase2/data/tf4-foresight/telemetry_data.csv"
df = pd.DataFrame()
try:
    df = pd.read_csv(csv_path)
    print("Columns:", df.columns)
    
    # Check for constant values or strange patterns
    series = df[(df['tenant_id'] == 'tnt-alpha') & (df['service_id'] == 'payment-gw') & (df['metric_type'] == 'cpu_pct')]['value'].values
    print("Payment-GW CPU Alpha: Mean=", np.mean(series), "Std=", np.std(series), "Min=", np.min(series), "Max=", np.max(series))
    
    # Check autocorrelation
    s = pd.Series(series)
    print("Autocorrelation lag 1:", s.autocorr(1))
    print("Autocorrelation lag 10:", s.autocorr(10))
    
    # Check an anomaly region (S1: 1*1440 + 600, 15 min)
    start_idx = 1440 + 600
    print("Anomaly S1 values:", series[start_idx:start_idx+15])
    print("Post-anomaly S1 values:", series[start_idx+15:start_idx+30])

except Exception as e:
    print(e)


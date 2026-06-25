import json
import requests
from datetime import datetime, timedelta

signals = []
start_ts = datetime.utcnow() - timedelta(minutes=120)
for i in range(120):
    ts = (start_ts + timedelta(minutes=i)).isoformat() + "Z"
    signals.append({
        "ts": ts,
        "tenant_id": "tenant-cdo-demo",
        "service_id": "payment-gw",
        "metric_type": "api_latency_ms",
        "value": 1200
    })

payload = {
    "signal_window": signals,
    "context": {
        "deployment_version": "v2.3.1",
        "time_range": {
            "start_ts": start_ts.isoformat() + "Z",
            "end_ts": datetime.utcnow().isoformat() + "Z"
        }
    }
}

headers = {
    "Content-Type": "application/json",
    "X-Tenant-Id": "tenant-cdo-demo"
}

resp = requests.post("http://3.88.41.31/v1/predict", json=payload, headers=headers)
print("Status:", resp.status_code)
print(resp.json())

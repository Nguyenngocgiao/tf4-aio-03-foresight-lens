from fastapi.testclient import TestClient
from app.main import app
from datetime import datetime, timedelta

client = TestClient(app)

def generate_baseline(metric_name, start_val, count=120):
    base_ts = datetime(2026, 6, 25, 9, 0, 0)
    return [{"ts": (base_ts + timedelta(minutes=i)).isoformat() + "Z", "service_id": "payment-gw", "signal_name": metric_name, "value": start_val + (i % 3 - 1)} for i in range(count)]

def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"

def test_detect_dummy_skeleton():
    payload = {
        "signal_window": generate_baseline("cpu_usage_percent", 50, 120),
        "context": {
            "deployment_version": "v1",
            "time_range": {"start_ts": "2026-06-25T09:00:00Z", "end_ts": "2026-06-25T10:00:00Z"}
        }
    }
    headers = {"X-Tenant-Id": "tnt-1", "Authorization": "SigV4"}
    response = client.post("/v1/predict", json=payload, headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["anomaly"] is True
    assert data["recommendation"]["action_verb"] == "SCALE_UP"
    assert data["reasoning"] == "skeleton response"

def test_missing_tenant_id():
    payload = {
        "signal_window": generate_baseline("cpu_usage_percent", 50, 120),
        "context": {
            "deployment_version": "v1",
            "time_range": {"start_ts": "2026-06-25T09:00:00Z", "end_ts": "2026-06-25T10:00:00Z"}
        }
    }
    response = client.post("/v1/predict", json=payload, headers={"Authorization": "SigV4"})
    assert response.status_code == 401

def test_less_than_120_points_fails():
    payload = {
        "signal_window": generate_baseline("cpu_usage_percent", 50, 119),
        "context": {
            "deployment_version": "v1",
            "time_range": {"start_ts": "2026-06-25T09:00:00Z", "end_ts": "2026-06-25T10:00:00Z"}
        }
    }
    headers = {"X-Tenant-Id": "tnt-1", "Authorization": "SigV4"}
    response = client.post("/v1/predict", json=payload, headers=headers)
    assert response.status_code == 400

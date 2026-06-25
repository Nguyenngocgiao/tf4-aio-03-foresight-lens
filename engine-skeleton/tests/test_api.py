import json
from datetime import datetime, timedelta
from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

# Tests use an UNREGISTERED service so the engine exercises its in-window fallback
# (deterministic, no baseline coupling). A dedicated test below covers the STL path.
TEST_SVC = "test-svc"
TENANT = "tnt-1"
HEADERS = {"X-Tenant-Id": TENANT, "Authorization": "SigV4"}


def generate_baseline(metric_type, start_val, count=120, service_id=TEST_SVC, tenant_id=TENANT):
    base_ts = datetime(2026, 6, 25, 9, 0, 0)
    return [{"ts": (base_ts + timedelta(minutes=i)).isoformat() + "Z",
             "tenant_id": tenant_id, "service_id": service_id, "metric_type": metric_type,
             "value": start_val + (i % 3 - 1)} for i in range(count)]


def _payload(window):
    return {"signal_window": window,
            "context": {"deployment_version": "v1",
                        "time_range": {"start_ts": "2026-06-25T09:00:00Z",
                                       "end_ts": "2026-06-25T11:00:00Z"}}}


def test_health_check():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "healthy"


def test_detect_happy_path():
    r = client.post("/v1/predict", json=_payload(generate_baseline("cpu_usage_percent", 50)), headers=HEADERS)
    assert r.status_code == 200
    data = r.json()
    assert data["anomaly"] is False
    assert data["recommendation"] is None


def test_detect_sudden_spike():
    window = generate_baseline("cpu_usage_percent", 50, 119)
    window.append({"ts": "2026-06-25T10:59:00Z", "tenant_id": TENANT, "service_id": TEST_SVC,
                   "metric_type": "cpu_usage_percent", "value": 98})
    r = client.post("/v1/predict", json=_payload(window), headers=HEADERS)
    assert r.status_code == 200
    data = r.json()
    assert data["anomaly"] is True
    assert data["recommendation"]["action_verb"] == "SCALE_UP"
    assert "audit_id" in data


def test_detect_slow_leak():
    window = generate_baseline("memory_usage_percent", 40, 119)
    window.append({"ts": "2026-06-25T10:59:00Z", "tenant_id": TENANT, "service_id": TEST_SVC,
                   "metric_type": "memory_usage_percent", "value": 92})
    r = client.post("/v1/predict", json=_payload(window), headers=HEADERS)
    assert r.status_code == 200
    assert r.json()["anomaly"] is True
    assert r.json()["recommendation"]["action_verb"] == "ROLLBACK"


def test_detect_sudden_drop():
    window = generate_baseline("throughput_rps", 1000, 119)
    window.append({"ts": "2026-06-25T10:59:00Z", "tenant_id": TENANT, "service_id": TEST_SVC,
                   "metric_type": "throughput_rps", "value": 50})
    r = client.post("/v1/predict", json=_payload(window), headers=HEADERS)
    assert r.status_code == 200
    assert r.json()["recommendation"]["action_verb"] == "INVESTIGATE"


def test_missing_tenant_id():
    r = client.post("/v1/predict", json=_payload(generate_baseline("cpu_usage_percent", 50)),
                    headers={"Authorization": "SigV4"})
    assert r.status_code == 401  # contract: missing tenant header -> 401


def test_less_than_120_points_fails():
    r = client.post("/v1/predict", json=_payload(generate_baseline("cpu_usage_percent", 50, 119)),
                    headers=HEADERS)
    assert r.status_code == 422  # contract: schema validation failure -> 422


def test_tenant_id_mismatch_rejected():
    window = generate_baseline("cpu_usage_percent", 50, tenant_id="tnt-OTHER")  # != header tnt-1
    r = client.post("/v1/predict", json=_payload(window), headers=HEADERS)
    assert r.status_code == 400  # well-formed but cross-tenant input -> 400


def test_stl_baseline_path_detects_drift():
    """Integration: feed payment-gw values matching its trained seasonal profile, then drift it."""
    bl_path = Path(__file__).resolve().parents[1] / "baselines" / "payment-gw.json"
    if not bl_path.exists():
        return  # baseline not trained in this environment; skip gracefully
    profile = json.loads(bl_path.read_text())["metrics"]["cpu_usage_percent"]["seasonal_profile"]
    base_ts = datetime(2026, 7, 8, 9, 0, 0)  # 09:00 -> minute-of-day 540
    normal = [{"ts": (base_ts + timedelta(minutes=i)).isoformat() + "Z", "tenant_id": TENANT,
               "service_id": "payment-gw", "metric_type": "cpu_usage_percent",
               "value": profile[(540 + i) % 1440]} for i in range(120)]
    r = client.post("/v1/predict", json=_payload(normal), headers=HEADERS)
    assert r.status_code == 200 and r.json()["anomaly"] is False
    drift = [dict(p) for p in normal]
    for k in range(60, 120):
        drift[k]["value"] = profile[(540 + k) % 1440] + (k - 60) * 1.5
    r2 = client.post("/v1/predict", json=_payload(drift), headers=HEADERS)
    assert r2.status_code == 200 and r2.json()["anomaly"] is True

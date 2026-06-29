"""
Load test for the Foresight Lens AI Engine /v1/predict endpoint.

Validates the success criterion in docs/01_requirements.md §3:
  - Throughput: 100 Requests/sec (engine must not be CDO's bottleneck)
  - NFR (docs §6): p99 latency < 500 ms

Tooling note: the capstone brief suggests k6/Locust, but neither is available in
this environment. This runner uses asyncio + httpx (httpx is already an app
dependency, so no extra tooling) and is fully reproducible:

  # 1. start the engine (from final-build/):
  uvicorn app.main:app --host 127.0.0.1 --port 8080
  # 2. run the load test:
  python tf4-evidence/load_test.py --url http://127.0.0.1:8080 --rps 100 --duration 30

IMPORTANT - global vs per-tenant: the 100 RPS target is a GLOBAL throughput SLA, while
the API enforces a per-tenant rate limit of 600 req/min (= 10 RPS/tenant, see
ai-api-contract.md). Driving 100 RPS through a single tenant would (correctly) be
throttled to 429. So load is spread round-robin across enough synthetic tenants that
each stays well under the per-tenant cap (~8 RPS/tenant), which is exactly how the
real CDO platforms (multiple tenants) reach aggregate throughput.

Two phases, both OPEN-LOOP (requests dispatched on a fixed schedule regardless of
response latency, so measured RPS reflects offered load and p99 reflects behaviour
under that sustained rate):
  Phase 1 (SLA validation): fixed target RPS (default 100) for `duration` seconds.
  Phase 2 (capacity probe): higher target RPS (default 400) to show headroom >> 100.

Writes a machine-readable result to tf4-evidence/evidence/evidence_load_test.json
in the same evidence-based style as the other eval artifacts (no hardcoded numbers).
"""
import argparse
import asyncio
import json
import os
import statistics
import time
from datetime import datetime, timedelta, timezone

import httpx

# Unregistered service -> engine uses its deterministic in-window fallback (no baseline
# coupling), exactly like the pytest suite. Keeps the load test self-contained.
SERVICE = "loadtest-svc"
WINDOW_SIZE = 120          # minimum required by the schema (>= 120 datapoints)
RPS_PER_TENANT = 8         # stay safely under the 10 RPS (600/min) per-tenant cap


def build_payload(tenant: str) -> bytes:
    """One valid request body: 120 continuous 1-minute datapoints, tenant matches header."""
    start = datetime.now(timezone.utc) - timedelta(minutes=WINDOW_SIZE)
    signal_window = []
    for i in range(WINDOW_SIZE):
        ts = start + timedelta(minutes=i)
        # mild sinusoidal-ish baseline so the engine does real EWMA work, not a flat line
        value = 50.0 + 10.0 * ((i % 30) / 30.0)
        signal_window.append({
            "ts": ts.isoformat(),
            "tenant_id": tenant,
            "service_id": SERVICE,
            "metric_type": "cpu_usage_percent",
            "value": round(value, 3),
        })
    body = {
        "signal_window": signal_window,
        "context": {
            "deployment_version": "loadtest-v1",
            "time_range": {
                "start_ts": signal_window[0]["ts"],
                "end_ts": signal_window[-1]["ts"],
            },
        },
    }
    return json.dumps(body).encode()


def build_tenants(rps: int):
    """Enough tenants that each stays under ~8 RPS; returns [(tenant, payload_bytes, headers)]."""
    n = max(1, -(-rps // RPS_PER_TENANT))  # ceil
    out = []
    for i in range(n):
        t = f"tnt-loadtest-{i:03d}"
        out.append((t, build_payload(t),
                    {"X-Tenant-Id": t, "Content-Type": "application/json"}))
    return out


def pct(values, p):
    if not values:
        return None
    k = (len(values) - 1) * (p / 100.0)
    lo = int(k)
    hi = min(lo + 1, len(values) - 1)
    return values[lo] + (values[hi] - values[lo]) * (k - lo)


async def open_loop(client, url, tenants, rps, duration, phase):
    """Dispatch requests on a fixed schedule (offered load = rps), round-robin tenants."""
    latencies = []
    statuses = {}
    errors = 0
    interval = 1.0 / rps
    tasks = []

    async def one_call(payload_bytes, headers):
        nonlocal errors
        t0 = time.perf_counter()
        try:
            r = await client.post(url, content=payload_bytes, headers=headers)
            latencies.append((time.perf_counter() - t0) * 1000.0)
            statuses[r.status_code] = statuses.get(r.status_code, 0) + 1
        except Exception:
            errors += 1

    start = time.perf_counter()
    next_fire = start
    n = 0
    while time.perf_counter() - start < duration:
        now = time.perf_counter()
        if now >= next_fire:
            _, payload_bytes, headers = tenants[n % len(tenants)]
            tasks.append(asyncio.create_task(one_call(payload_bytes, headers)))
            n += 1
            next_fire += interval
        else:
            await asyncio.sleep(min(next_fire - now, 0.001))
    wall = time.perf_counter() - start
    if tasks:
        await asyncio.gather(*tasks)

    latencies.sort()
    ok = statuses.get(200, 0)
    return {
        "phase": phase,
        "target_rps": rps,
        "tenants": len(tenants),
        "rps_per_tenant": round(rps / len(tenants), 1),
        "duration_s": round(wall, 2),
        "requests_sent": n,
        "responses_2xx": ok,
        "status_breakdown": statuses,
        "transport_errors": errors,
        "achieved_rps": round(ok / wall, 1) if wall else 0,
        "success_rate": round(ok / n, 4) if n else 0,
        "latency_ms": {
            "p50": round(pct(latencies, 50), 2) if latencies else None,
            "p95": round(pct(latencies, 95), 2) if latencies else None,
            "p99": round(pct(latencies, 99), 2) if latencies else None,
            "max": round(latencies[-1], 2) if latencies else None,
        },
    }


async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default="http://127.0.0.1:8080")
    ap.add_argument("--rps", type=int, default=100)
    ap.add_argument("--duration", type=int, default=30)
    ap.add_argument("--probe-rps", type=int, default=400)
    ap.add_argument("--probe-duration", type=int, default=15)
    ap.add_argument("--out", default=os.path.join(os.path.dirname(__file__),
                                                  "evidence", "evidence_load_test.json"))
    args = ap.parse_args()

    endpoint = args.url.rstrip("/") + "/v1/predict"
    sla_tenants = build_tenants(args.rps)
    probe_tenants = build_tenants(args.probe_rps)

    limits = httpx.Limits(max_connections=400, max_keepalive_connections=400)
    async with httpx.AsyncClient(timeout=10.0, limits=limits) as client:
        # sanity check
        _, pb, hd = sla_tenants[0]
        r = await client.post(endpoint, content=pb, headers=hd)
        if r.status_code != 200:
            raise SystemExit(f"sanity request failed: {r.status_code} {r.text[:300]}")

        print(f"[phase 1] open-loop {args.rps} rps for {args.duration}s "
              f"across {len(sla_tenants)} tenants ...")
        sla = await open_loop(client, endpoint, sla_tenants, args.rps,
                              args.duration, "open_loop_sla_100rps")
        print(json.dumps(sla, indent=2))

        print(f"[phase 2] open-loop capacity probe {args.probe_rps} rps for "
              f"{args.probe_duration}s across {len(probe_tenants)} tenants ...")
        cap = await open_loop(client, endpoint, probe_tenants, args.probe_rps,
                              args.probe_duration, "open_loop_capacity_probe")
        print(json.dumps(cap, indent=2))

    gates = {
        "throughput_100rps": sla["achieved_rps"] >= 100,
        "p99_under_500ms": (sla["latency_ms"]["p99"] is not None
                            and sla["latency_ms"]["p99"] < 500),
        "no_throttle_at_sla": sla["status_breakdown"].get(429, 0) == 0,
        "no_errors_at_sla": sla["transport_errors"] == 0 and sla["success_rate"] >= 0.99,
    }
    result = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "endpoint": endpoint,
        "engine": "EWMA + STL control chart (in-window fallback path)",
        "method": "asyncio + httpx open-loop, single uvicorn worker on localhost; "
                  "load spread across synthetic tenants to respect the 600/min per-tenant cap",
        "sla_target": {"throughput_rps": 100, "p99_latency_ms": 500,
                       "per_tenant_cap_rpm": 600},
        "phase1_sla": sla,
        "phase2_capacity_probe": cap,
        "gates_pass": gates,
        "overall_pass": all(gates.values()),
    }
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w") as f:
        json.dump(result, f, indent=2)
    print(f"\nGates: {gates}\nOverall pass: {result['overall_pass']}\nWrote {args.out}")


if __name__ == "__main__":
    asyncio.run(main())

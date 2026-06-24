# TF4 Foresight Lens - Data Pack (Contract Compliant)

This dataset is generated according to the Telemetry Contract for TF4.

## Schema (Long Format)
- `timestamp`: ISO8601 string
- `tenant_id`: Multi-tenant isolation identifier (e.g. tnt-alpha)
- `service_id`: Microservice name
- `metric_type`: Metric dimension (e.g., cpu_pct, latency_p99_ms)
- `value`: Float measurement

## Included Scenarios
Ground truth anomalies and False Positive (FP) traps are listed in `alerts_ground_truth.json`.

# Telemetry Contract - Task force 4

<!-- Owner: AIO-03
     Signed by: AI Lead + CDO Leads × 2-3 + Reviewer panel
     Date signed: 2026-06-25 (W11 T5)
     🔒 FREEZE - no change without formal change request -->

## Mục đích

Định nghĩa **signals nào CDO emit từ infra** → AI engine consume để dự đoán Capacity Exhaustion. Là handshake giữa platform layer (CDO) và intelligence layer (AI).

## Versioning

- **Current version**: `v1.0`
- **Evolution**: backward-compatible additions only. Breaking change → new contract version + migration window

---

## Signals required

> List signals AI engine cần để analyze. Hệ thống Foresight Lens sử dụng mảng dữ liệu (Rolling Window) để phát hiện bất thường dựa trên 3-Sigma.

### Signal 1: `cpu_usage_percent`

| Attribute | Value |
|---|---|
| **Type** | gauge |
| **Labels** | service, region, tenant_id (mandatory) |
| **Unit** | percentage (0-100) |
| **Frequency** | 1 phút |
| **Emit point** | CloudWatch Metrics / Prometheus → CDO Ingestion → AI API |
| **Retention** | 7 ngày hot |
| **Used for** | Phát hiện xu hướng tăng đột biến CPU |

### Signal 2: `memory_usage_percent`

| Attribute | Value |
|---|---|
| **Type** | gauge |
| **Labels** | service, region, tenant_id (mandatory) |
| **Unit** | percentage (0-100) |
| **Frequency** | 1 phút |
| **Emit point** | CloudWatch Metrics / Prometheus → CDO Ingestion → AI API |
| **Retention** | 7 ngày hot |
| **Used for** | Dự đoán Memory Leak dẫn tới OOM (Out Of Memory) |

### Signal 3: `active_connections`

| Attribute | Value |
|---|---|
| **Type** | gauge |
| **Labels** | service, region, tenant_id (mandatory) |
| **Unit** | count |
| **Frequency** | 1 phút |
| **Emit point** | ALB / Nginx metrics |
| **Used for** | Correlate giữa traffic spike và resource exhaustion |

### Signal 4: `db_connection_pool_pct`

| Attribute | Value |
|---|---|
| **Type** | gauge |
| **Labels** | service, db_type (e.g. postgres, mysql), region, tenant_id |
| **Unit** | percentage (0-100) |
| **Frequency** | 1 phút |
| **Emit point** | RDS CloudWatch Metrics → CDO Ingestion → AI API |
| **Retention** | 7 ngày hot |
| **Used for** | Phát hiện cạn kiệt Connection Pool của Database do slow queries hoặc Cache Stampede |

### Signal 5: `queue_depth`

| Attribute | Value |
|---|---|
| **Type** | gauge |
| **Labels** | service, queue_name, region, tenant_id |
| **Unit** | count |
| **Frequency** | 1 phút |
| **Emit point** | SQS CloudWatch Metrics → CDO Ingestion → AI API |
| **Retention** | 7 ngày hot |
| **Used for** | Đo lường mức độ nghẽn cổ chai (backlog) của worker consuming message (ví dụ Ledger worker) |

### Signal 6: `cache_hit_rate_pct`

| Attribute | Value |
|---|---|
| **Type** | gauge |
| **Labels** | service, cache_type (e.g. redis), region, tenant_id |
| **Unit** | percentage (0-100) |
| **Frequency** | 1 phút |
| **Emit point** | ElastiCache CloudWatch Metrics → CDO Ingestion → AI API |
| **Retention** | 7 ngày hot |
| **Used for** | Phát hiện Cache Miss Spike dẫn đến quá tải trực tiếp xuống RDS |

---

## Cross-cutting requirements

Mọi signal phải comply:
- **Tenant scoping**: mọi signal payload **bắt buộc** có `tenant_id` field - AI engine không accept signal thiếu tenant_id.
- **Time precision**: timestamp RFC3339 UTC, millisecond precision.
- **Schema validation**: AI ingestion layer (Pydantic) validate schema; reject malformed.
- **PII**: KHÔNG được chứa PII (email / phone / name) trong signal value hoặc labels.

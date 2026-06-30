# Pitch Cá Nhân — Thịnh Nguyễn Công

**Vai trò**: Platform Contracts Lead (Telemetry & Deployment)  
**Nhóm**: AIO-03 — Foresight Lens  
**Giai đoạn**: Capstone Phase 2 (W11–W12)

---

## 1. Nhiệm vụ đảm nhận

| Nhiệm vụ | Deliverable | Trạng thái |
|---|---|---|
| [Contracts] Draft Telemetry & Deployment Contracts | `contracts/telemetry-contract.md` + `contracts/deployment-contract.md` | Hoàn thành & Đã đóng băng |

---

## 2. Artifacts đã thực hiện

### `contracts/telemetry-contract.md` — CDO phải gửi gì

Telemetry contract định nghĩa data interface từ CDO đến AI engine: những signal nào là bắt buộc, schema mỗi signal phải theo, tần suất gửi, và các compliance rule.

**7 signals với specification đầy đủ:**

| Signal | Dùng để |
|---|---|
| `cpu_usage_percent` | Phát hiện capacity exhaustion qua CPU drift |
| `memory_usage_percent` | Dự báo OOM do memory leak |
| `active_connections` | Correlation với traffic spike |
| `db_connection_pool_pct` | Connection pool exhaustion |
| `queue_depth` | Worker backlog / queue overflow |
| `cache_hit_rate_pct` | Cache miss spike → RDS overload |
| `api_latency_ms` | Leading indicator (latency tăng 15–30 phút trước khi SLO breach) |

Mỗi signal tôi spec đầy đủ: gauge type, mandatory label fields, unit, tần suất 1 phút, emit point (CloudWatch Metrics / ALB / SQS / ElastiCache), retention (7 ngày hot + 83 ngày cold = tổng 90 ngày), emit SLA (p99 < 60s), volume SLA (50,000 events/giây peak — trần thiết kế cho Black Friday), và cost estimate (~$3.5/tháng cho demo scope).

**Note làm rõ volume SLA 50k/s:** Tôi viết phần giải thích chi tiết phân biệt giữa trần pipeline capacity (50k/s, cho Black Friday với ~3M time-series) và actual demo scope (vài chục events/giây, 3 service × 4 signal × 1 phút/lần). Note này ngăn nhầm lẫn trong CDO integration khi team ban đầu nghĩ họ cần emit 50,000 events/giây cho demo.

**Baseline coverage footnote** — ghi rõ AI engine train baseline cho 4 signal chính (`cpu_usage_percent`, `memory_usage_percent`, `api_latency_ms`, `queue_depth`) và fall back sang in-window z-score cho 3 signal còn lại. CDO team biết chính xác signal nào có trained baseline và signal nào dùng fallback.

**Cross-cutting requirements:**
- Tenant scoping — mọi signal payload bắt buộc có `tenant_id`. Engine reject signal thiếu trường này
- Time precision — RFC3339 UTC, millisecond precision
- Data Alignment & Imputation — CDO phải forward-fill hoặc zero-fill gap trước khi gửi. Engine trả HTTP 400 khi phát hiện gap. Đây là operationalization của open question resolution trong `docs/01_requirements.md`
- PII denylist — mở rộng cho domain payment/fraud/ledger (PCI-DSS/SOC2): `email`, `phone`, `name`, `transaction_id`, `account_id`, `card_pan`, `user_id`. CDO ingestion layer phải strip/redact trước khi đẩy sang AI API

### `contracts/deployment-contract.md` — CDO host engine như thế nào

Deployment contract định nghĩa AI engine được deploy trên CDO infrastructure theo cách nào. Vì CDO tự host AI engine trên platform của mình, tài liệu này là blueprint CDO team dùng để viết IaC.

**Compute specification:**
- ECS Fargate, `tf-4-aiops-cluster`, `foresight-lens-engine`
- 0.5 vCPU / 1024 MB mỗi task
- Lý do: EWMA là O(N) in-memory trên 120 float — computation cực nhẹ. 1GB RAM đủ cho 4 Uvicorn worker ở ~150MB mỗi cái

**FinOps & Cost Circuit Breaker:**
- AWS Budgets alert khi đạt 80% ($160)
- Lambda-triggered scale-to-zero khi đạt 100% ($200) — `Desired_Count = 0`
- Tôi ghi rõ đây là hard requirement với priority cao hơn SLA 99.5% availability. Khi circuit breaker trigger, CDO fallback sang rule-based alerting. Cost đo thực ~$36/tháng nên breaker gần như không bao giờ kích hoạt — đây là van an toàn, không phải operating mode thông thường

**Scaling policy:**
- Min 2, Max 4 task
- Autoscale trigger: CPU 70%, 80 RPS/task
- Scale-up cooldown 60s, scale-down cooldown 300s (lên nhanh, xuống chậm)

**Secrets management:**
- 5 env var được định nghĩa: `AWS_REGION`, `BASELINE_BACKEND`, `BASELINE_S3_BUCKET`, `BASELINE_S3_PREFIX`, `AUDIT_BACKEND/S3_BUCKET/KMS_KEY_ID`
- Note rõ: không cần Bedrock API key — statistical model, $0 token cost

**Storage & State:**
- Per-service STL baseline lưu trên S3 (mã hóa KMS)
- Engine stateless — mỗi request fetch baseline từ cache hay S3, không có database
- Baseline refresh thủ công: upload file JSON baseline mới lên S3 hàng tuần

**Networking:**
- Private subnet, internal ALB only, `tf-4-ai-engine-sg`
- Ingress: SG-to-SG từ CDO platforms chỉ trong cùng task force
- Egress: VPC Endpoint hoặc NAT đến AWS services (không có public internet egress)

**Baseline lifecycle:**
- Version prefix trên S3 (`baselines/v2/`)
- Giữ ít nhất 2 version gần nhất để rollback
- Promotion gate: recall >= 80%, FP <= 12% trên holdout trước khi swap
- Fail gate → giữ baseline cũ

**Canary rollout strategy:** 10% → 50% → 100%, 5 phút mỗi bước  
**Abort criteria:** error > 1%, P99 > 800ms, anomaly prediction error > 15%  
**Rollback:** AWS CodeDeploy, target RTO < 60 giây

---

## 3. Quyết định chính và lý do

### CDO tự host engine, không phải AI team host central endpoint

Deployment contract chỉ định mỗi CDO platform tự host một instance AI engine của riêng họ. AI team không chạy một central endpoint.

Lý do: Central endpoint tạo hard dependency — nếu AI team infrastructure sập, cả ba CDO platform mất monitoring. CDO tự host thì failure được isolate: engine của CDO-1 sập không ảnh hưởng CDO-2 hay CDO-3. Topology mạng cũng đơn giản hơn — không có cross-account API call, chỉ in-VPC call đến endpoint của chính CDO.

Đánh đổi: Ba CDO team cần maintain ba engine deployment riêng. Operational overhead tăng. Được giảm thiểu bởi việc deploy runbook (`engine-skeleton/deploy/README.md`) là một document mà cả ba CDO follow giống nhau.

### Circuit breaker $200 là hard requirement override SLA

Tôi ghi rõ ràng circuit breaker (scale-to-zero khi $200) là hard requirement với priority cao hơn SLA 99.5% availability.

Lý do: Constraint $200 của khách hàng là tuyệt đối — "tuyệt đối không vượt $200". Nếu ghi nó là soft target có thể override để maintain SLA, một CDO team có thể disable breaker để tránh downtime khi cost spike. Priority ordering tường minh (cost constraint > SLA) đảm bảo breaker không thể bị coi là negotiable.

Note trong tài liệu cũng làm rõ tại sao điều này an toàn: với ~$36/tháng actual cost, breaker gần như không bao giờ trigger. Đây là last-resort safety valve, không phải operating mode thông thường.

### 50,000 events/giây là design ceiling, không phải demo requirement

Tôi viết volume SLA là "50,000 events/giây peak (design ceiling)" với note giải thích rõ sự khác biệt giữa trần thiết kế pipeline và actual demo scope.

Lý do: Không có làm rõ này, CDO team xây Kinesis/Timestream ingestion pipeline sẽ hoặc over-provision (nghĩ cần 50k/s cho demo) hoặc under-provision (nghĩ nó chỉ cho show). Note cung cấp thông tin cần thiết để sizing infrastructure đúng: vài chục events/giây cho demo; hướng đến 50k/s là trần năng lực cho Black Friday simulation.

### Mở rộng PII denylist cho domain payment/fraud/ledger

Tôi mở rộng denylist PII chung (`email`, `phone`, `name`) thêm financial identifiers domain-specific (`transaction_id`, `account_id`, `card_pan`, `user_id`) và ghi rõ PCI-DSS/SOC2 là compliance driver.

Lý do: Ba CDO service là payment, fraud detection, và ledger — tất cả đều dưới PCI-DSS/SOC2. Generic PII rule chưa đủ: metric label `account_id: ACC-12345` là PII trong financial context dù "account_id" không nằm trong denylist PII phổ thông. Mở rộng denylist với domain-specific field giúp CDO ingestion team biết chính xác key nào cần strip trước khi data qua AI layer.

---

## 4. Đánh đổi và nhìn lại

Những gì đã làm tốt: Circuit breaker design với priority ordering và "fail-open" rationale không tạo ra tranh luận trong review. Lý luận đầy đủ để CDO team hiểu intent ngay. Baseline lifecycle section cho CDO procedure vận hành rõ ràng cho baseline update mà không cần AI team tham gia. Failure modes table là reference thực tế mà CDO team có thể đưa vào runbook của họ.

Những gì cần làm khác: Telemetry contract chỉ định ~$3.5/tháng cost mỗi signal cho demo scope nhưng không cho công thức hay source để scale estimate này lên production cardinality. Tôi sẽ thêm note: "ở 50k/s, cost scale theo $X/tháng cho Timestream ingest tại $Y/GB."

Cross-cutting requirement về Data Alignment ghi CDO phải imputation trước khi gửi nhưng không spec method nào nên dùng cho từng signal. Với `memory_usage_percent`, forward-fill là hợp lý (memory không drop về 0 khi mạng bị ngắt); với `queue_depth`, zero-fill có thể chính xác hơn. Imputation guidance theo từng signal sẽ giảm guesswork cho CDO.

---

## 5. Tự đánh giá

Cả hai hợp đồng hoàn thành, đã đóng băng, và nhất quán nội bộ. Telemetry contract phù hợp với 4 signal chính dùng trong trained baselines (`train_baseline.py`). Deployment contract phù hợp với Fargate config trong `engine-skeleton/deploy/task-definition.json` và scaling parameters trong `docs/03_ai_engine_spec.md`. Circuit breaker math nhất quán với ~$36/tháng actual measurement trong `docs/04_eval_report.md`.

Bằng chứng mạnh nhất: cả hai hợp đồng được review và ký vào 2026-06-25. Không có amendment nào kể từ đó — freeze đã được tuân thủ. 7 telemetry signal và deployment parameter được implement đúng như spec. Không có CDO team nào phải request contract change trong W11–W12.

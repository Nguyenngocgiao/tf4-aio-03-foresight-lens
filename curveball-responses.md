# Curveball Responses — Foresight Lens (TF4-AIO-03)

<!-- Doc owner: AIO-03
     Status: live W12 — append một block mỗi lần curveball inject
     Cadence inject: #1 W11 T5 (25/06) · #2 W12 T2 (29/06 16h) · #3 W12 T4 (01/07 14h)
     Format mỗi response: Problem · Impact · Response · Lesson -->

Ba lần inject scope-change mô phỏng client change-request thật. Nguyên tắc xuyên suốt khi
xử lý: **không panic, không cãi, không miss deadline** — đọc lại 3 contracts đã FREEZE, phân
loại breaking vs non-breaking, rồi adapt bằng config/versioning thay vì re-design.

| # | Tier | Khi nào | Scenario | Outcome |
|---|------|---------|----------|---------|
| 1 | Small | W11 T5, 15p | Region migration `ap-southeast-1` → `us-east-1` | **Pass** — config-only, không đụng schema |
| 2 | Medium | W12 T2, 30p | Đổi đơn vị metric `api_latency_ms` → `api_latency_us` (×1000), no-downtime | **Pass** — additive v1.1 + dual-emit |
| 3 | Chaos | W12 T4, 60p | Primary region `us-east-1` sập 30 phút | **Pass** — fail-open giữ monitoring, RTO < 60s |

---

## Curveball #1 — Region migration `ap-southeast-1` → `us-east-1`

**Problem.** Cuối buổi approve T5 W11, Client thông báo platform sẽ chuyển region vận hành từ
`ap-southeast-1` (Singapore) sang `us-east-1` (N. Virginia) vì lý do data-residency + cost. Câu
hỏi: AI Engine và 3 contracts vừa ký phải sửa gì, có phá FREEZE không?

**Impact.**
- **Engine: zero code change.** Engine đã thiết kế *region-agnostic* — region đọc từ env var
  `AWS_REGION`, baseline đọc từ `BASELINE_S3_BUCKET`/`BASELINE_S3_PREFIX` (Deployment Contract §Secrets).
  Không có region hard-code trong logic.
- **Tài nguyên regional phải dựng lại ở `us-east-1`:** S3 bucket chứa per-service baseline; KMS key
  mã hóa audit (KMS key bound theo region → key mới, re-encrypt at rest); VPC endpoint (S3/CloudWatch),
  internal ALB, private subnet, security group.
- **Baseline KHÔNG cần retrain.** Seasonal profile STL học theo *time-of-day UTC* (chu kỳ ngày), không
  phụ thuộc địa lý; cùng tập user fintech → đường cong tải không đổi. Chỉ cần **copy** file baseline JSON
  sang bucket mới (S3 cross-region copy).
- **Contracts: không breaking.** `region` trong Telemetry Contract là một *label value*, không phải field
  schema → đổi `ap-southeast-1`→`us-east-1` là thay giá trị, không đổi interface. AI API Contract: URL
  vốn đã per-CDO internal domain, schema/endpoint không đổi. Theo versioning policy, đây là **non-breaking**
  → **không cần change request, không re-sign** → FREEZE không bị phá.

**Response.**
1. Xác nhận engine region-agnostic; re-point `AWS_REGION`, `BASELINE_S3_BUCKET`, `AUDIT_S3_BUCKET`,
   `AUDIT_KMS_KEY_ID` sang tài nguyên `us-east-1`. Không sửa 1 dòng code.
2. Tạo KMS key mới ở `us-east-1`; S3 cross-region copy baseline JSON; giữ ≥2 version để rollback.
3. CDO re-apply Terraform ở region mới (VPC + private subnet + internal ALB + SG + VPC endpoint).
   Deploy engine bằng **canary 10→50→100%**; drain region cũ sau khi 100% healthy.
4. Ghi **ADR-007 (Region migration)** — append-only — log lý do region-agnostic giúp đây là config change
   chứ không phải re-design. DR design (single-region per scope) cập nhật primary = `us-east-1`.

**Lesson.** Tách region ra env var + engine **stateless** + baseline lưu **S3** biến một việc nghe "to"
(đổi region) thành *config + IaC re-apply*. Vì interface (schema, endpoint) không đổi nên versioning policy
phân loại non-breaking → không động tới FREEZE. Đúng giá trị của quyết định "engine region-agnostic" trong
Deployment Contract.

---

## Curveball #2 — Đổi đơn vị metric `api_latency_ms` → `api_latency_us` (no-downtime)

**Problem.** 16h T2 W12, platform team đổi đơn vị metric latency từ mili-giây sang micro-giây
(`api_latency_ms` → `api_latency_us`) — giá trị nhân **×1000**. Telemetry Contract đang **FREEZE v1.0**.
Yêu cầu: migrate **không downtime**, không phá baseline đã train trên `ms`, không phá contract.

**Impact.**
- **Đây là breaking change về *semantics*, dù shape schema y hệt.** `metric_type` vẫn là string, `value`
  vẫn là float — nhưng phân phối số nhân 1000×. Baseline (seasonal profile + residual σ) train trên `ms`
  sẽ thấy mọi điểm `us` vượt baseline ~1000× → **EWMA control limit breach toàn bộ** → false-positive storm.
- Nếu CDO âm thầm đổi value dưới cùng tên `api_latency_ms` → **silent corruption** nguy hiểm nhất: schema
  pass validation, baseline sai, alert rác.
- Theo versioning: breaking → **new contract version + migration window** (Telemetry Contract §Versioning).

**Response (zero-downtime).**
1. **Raise change request** đúng quy trình (raise trong task force → bump version). Bump Telemetry Contract
   **v1.0 → v1.1 dạng additive**: thêm metric_type **mới** `api_latency_us`, **không** mutate `api_latency_ms`.
2. **Dual-emit window:** CDO emit **đồng thời** cả `api_latency_ms` (cũ) + `api_latency_us` (mới). Engine vẫn
   score trên baseline `ms` cũ → **không gián đoạn, không FP spike** trong lúc chuyển.
3. **Unit-normalization tại ingestion (Pydantic boundary):** map các unit-variant về canonical unit
   (`*_us ÷ 1000 → ms`) trước khi so baseline → baseline cũ vẫn dùng được ngay, không cần chờ.
4. **Train baseline mới** cho `api_latency_us` offline (`scripts/train_baseline.py`) trên data dual-emit;
   chỉ **promote khi pass holdout gate** (recall ≥80%, FP ≤12% — Deployment Contract promotion gate).
5. **Cutover:** sau khi baseline mới pass gate → flip canonical; dừng emit `api_latency_ms` sau **migration
   window 30 ngày**. Giữ baseline cũ ≥2 version để rollback.
6. **Fail-safe:** baseline mới fail gate → giữ bản cũ; fallback z-score in-window vốn *unit-agnostic* (đo độ
   lệch tương đối) nên không vỡ dù cutover lỗi. Roll engine change bằng canary 10→50→100%.

**Lesson.** Đổi đơn vị là breaking change *ngữ nghĩa* dù schema không đổi — bắt được trước khi nó âm thầm
phá baseline. Kỷ luật **frozen-contract + versioning** (additive v1.1, dual-emit, migration window) cho phép
migrate **0 downtime**. Engine **stateless** + baseline **offline** + **promotion gate** làm việc swap an toàn
và reversible. Log **ADR-008 (unit normalization)**.

---

## Curveball #3 — Chaos: primary region `us-east-1` sập 30 phút

**Problem.** 14h T4 W12, region chính `us-east-1` mất 30 phút (regional outage). Serving endpoint, S3
baseline, audit S3/KMS, CloudWatch đều unreachable. Monitoring sống sót thế nào và engine recover ra sao?

**Impact.**
- Deploy **single-region** (multi-region chỉ design-only theo scope). Engine ở `us-east-1` chết → cả **3 CDO**
  (payment / fraud / ledger) nhận `503`/timeout trên `/v1/predict`.
- Không mitigation: 3 platform mất predictive capacity đúng 30 phút — thời điểm outage dễ cascade nhất.
- In-memory baseline cache (TTL 5 phút) stale nhanh; S3 baseline tạm unreachable.

**Response (fail-open + design-only failover).**
1. **Fail-open là contractual và đã build:** khi `503`/timeout, **mọi CDO bắt buộc** fallback sang rule-based
   static-threshold alert (Deployment Contract §Failure modes; Solution Design Q1). **Monitoring KHÔNG đứt** —
   chỉ *degrade* từ predictive → reactive (ngưỡng cứng RAM>90%, CPU>90%, pool>95%). Mất tạm lead-time, không
   mất coverage.
2. **Engine resilience:** stateless + S3-backed → **không mất state**. Region trở lại → ECS Fargate task
   restart (health check `/health`), fetch baseline từ S3, resume. **RTO < 60s**. Không cần retrain (S3 durable,
   versioned).
3. **Audit integrity:** trong outage engine không serve (fail-open) → không có audit gap cho served call; CDO
   fallback alert log phía CDO. Khôi phục xong audit resume, hash-chain nguyên vẹn.
4. **Multi-region failover (DESIGN-ONLY, trình bày thiết kế):** warm-standby `ap-southeast-1` — baseline S3
   Cross-Region Replication, engine image ECR replicate, Route53 health-check failover sang internal ALB phụ.
   RTO target ~5 phút. Không build (out of scope) nhưng **đã thiết kế** — tái dùng đúng tính *region-agnostic*
   ở Curveball #1: failover = re-point config y hệt.
5. **Confidence gate dưới chaos:** ngưỡng `<0.7 → INVESTIGATE` giúp giai đoạn recovery nhiễu, tín hiệu yếu hạ
   xuống INVESTIGATE thay vì spam `SCALE_UP` trên transient hậu-outage.
6. **Cost guard độc lập:** scale-to-zero circuit breaker không bị ảnh hưởng; outage không phát sinh cost.

**Chaos drill (demo thật):** kill engine task / chặn S3 → CDO fallback bắn static alert (không gap monitoring)
→ restart task → baseline reload từ S3 → predictive resume; đo RTO ghi vào eval report §5.

**Lesson.** **Fail-open** là quyết định an toàn quan trọng nhất: regional outage chỉ *degrade* Foresight Lens
từ predictive → reactive, **không bao giờ làm SRE mù**. Stateless + S3 baseline durable biến recovery thành
*restart*, không phải *rebuild*. Thiết kế region-agnostic (Curveball #1) chính là thứ làm multi-region failover
(design-only) đứng dậy rẻ về sau. Log **ADR-009** (chaos-drill RTO evidence + warm-standby failover design).

---

> **Reconcile evidence:** ba block trên khớp với bảng "Curveball impact" ở `docs/04_eval_report.md §5`.
> Nếu wording curveball mentor inject khác giả định, cập nhật phần **Problem** tương ứng, phần Response/Lesson
> giữ nguyên hướng (config-over-redesign · additive versioning · fail-open).

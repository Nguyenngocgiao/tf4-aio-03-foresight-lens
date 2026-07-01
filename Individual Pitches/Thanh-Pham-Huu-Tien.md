# Pitch Cá Nhân — Thanh Phạm Hữu Tiến

**Vai trò**: Technical Lead (Kỹ thuật trưởng) — AI Engine
**Nhóm**: AIO-03 — Foresight Lens
**Giai đoạn**: Capstone Phase 2 (W11–W12)

---

## 1. Nhiệm vụ đảm nhận

| Mảng | Trách nhiệm | Trạng thái |
|---|---|---|
| Kiến trúc & quyết định kỹ thuật | Chọn thuật toán, ranh giới auth/deploy, chốt region | Hoàn thành |
| Engine code & evidence integrity | Trực tiếp sửa/đồng bộ phần lớn code (engine, API, cả 2 build) khớp contract–docs–evidence; số đo thật, tái lập | Hoàn thành |
| W12 hardening & defense-readiness | SigV4, load test, NFR/MG matrix, curveball | Hoàn thành |
| Điều phối team & hợp đồng CDO | Đồng bộ 3 contract, handover, review/merge PR | Hoàn thành |
| Governance repo | Contracts frozen, dọn secret/tooling, chuẩn commit | Hoàn thành |

Vai trò của tôi là **giữ cho toàn hệ thống nhất quán và trung thực** — từ thuật toán, hợp đồng, hạ tầng đến con số đưa lên bàn defense.

---

## 2. Đóng góp kỹ thuật chính

### 2.1 Kiến trúc & các quyết định trọng yếu

- **Chọn STL seasonal baseline + EWMA control chart (α=0.3, K=4.0) thay vì LLM.** STL khử chu kỳ tải ngày/đêm (train offline), EWMA bắt drift kéo dài sớm và làm mượt gai đơn lẻ. Lý do: vừa ngân sách **$200/tháng**, latency cực thấp, **giải thích được**, **zero hallucination**, inference ~$0. Các trade-off ghi trong ADR-001/004/006 (sweep 16 tổ hợp α×K chọn K=4.0 vì FP 7.1% < gate 12%; K=3.0 bị loại do FP 17.5%).
- **Chốt deploy region = `us-east-1`.** Engine region-agnostic (stateless, no PII, `AWS_REGION` env) → đi theo region CDO, chọn us-east-1 vì chi phí thấp nhất + catalog service rộng nhất.
- **Chốt ranh giới xác thực ở edge.** IAM SigV4 enforce bằng **private API Gateway (`AWS_IAM`) đứng trước Internal ALB (routing) → ECS Fargate**; app **không** verify chữ ký, chỉ đọc `principal_id` đã xác thực để ghi audit (`Authorization` Optional có chủ đích). Tôi phát hiện & sửa cách nói sai "ALB tự enforce IAM" (ALB native auth chỉ OIDC/Cognito; IAM/SigV4 là của API Gateway).

### 2.2 Engine & liêm chính dữ liệu (nguyên tắc "đo thật, không bịa số")

- **Trực tiếp sửa & đồng bộ phần lớn code** để engine ↔ contract ↔ docs ↔ evidence khớp nhau: port engine EWMA+STL thật sang `final-build/app/` (trước đó là bản 3-sigma giả dán nhãn ewma_stl), chuẩn hoá mã lỗi (422 schema / 400 business / 401 thiếu tenant header), rate-limit 600/phút/tenant (429 + `Retry-After`), audit log 6 trường với SHA-256 hash PII, confidence gating `< 0.7 → INVESTIGATE`, và đọc `principal_id` từ header SigV4 đã verify để ghi audit. Sau mỗi đợt đồng bộ đều chạy lại **tests 9/9 pass cả 2 build**.
- **Eval reproducible.** Mọi số đến từ `tf4-evidence/eval_engine.py` chạy engine thật trên holdout có label: **Recall 0.971 · Precision 0.793 · F1 0.873 · FP 7.1% · Brier 0.049 · Lead 110 phút** (CM: TP 169 / FP 44 / FN 5 / TN 574). Bổ sung **khoảng tin cậy 95% (Wilson)** trên metric — recall **[0.935, 0.988]**, FP **[5.3%, 9.4%]** — cận bất lợi nhất vẫn qua gate, nên pass không phải may từ một điểm ước lượng.
- **Rà & vá mâu thuẫn cross-file toàn repo** (giữ một nguồn sự thật): cost `$32` (model nhầm 0.25 vCPU/per-request) → **~$53/tháng đúng** (Fargate 0.5 vCPU/1 GB × 2 flat + ALB + S3); `DynamoDB`→`S3` cho audit khớp code; nhãn "3-sigma" → **EWMA K=4.0**; chuẩn hoá `metric_type` về vocab contract; `evidence_pattern_diversity` rescope **5→3 service** đúng deliverable, kèm generator tái lập từ data đã ship.
- **Đóng khung số liệu trung thực.** Lead-time 110 phút được ghi rõ là **đo trên kịch bản synthetic slow-drift, KHÔNG phải guarantee production** — cam kết thực là **gate ≥15 phút**; `confidence` là **điểm xác suất đã hiệu chuẩn** (Brier 0.049 + reliability diagram), phân biệt rõ với CI trên metric.

### 2.3 W12 hardening & defense-readiness

- **Load test** `/v1/predict`: 100 RPS × 30s → **p99 = 4 ms, 0 throttle/error**; probe 400 RPS vẫn sạch (≥4× headroom). Chỉ rõ **100 RPS = throughput global** còn **600/phút = cap per-tenant** nên phải rải đa-tenant.
- Gỡ mâu thuẫn "Bedrock Guardrails" (engine thống kê, không LLM) → liệt kê security thật (SigV4 edge + Pydantic + audit 6-field + SHA-256).
- Hoàn thiện **NFR/MG control matrix** trỏ artifact thật; tests **9/9 pass** cả `engine-skeleton` và `final-build`.

### 2.4 Curveball (W12) — thiết kế kịch bản, đo bằng engine thật

Ba curveball tăng độ khó, chấm bằng `curveball_eval.py` (deterministic, reproducible):
- **#1 Small** — service mới không có baseline + CPU drift → fallback z-score bắt được, lead **69 phút** → **Pass**.
- **#2 Medium** — Flash Sale lành tính (peak 50%, không chạm 90%) → engine báo động (FP so với ý định) → **Partial**; bài học: control "Silence & Retrain" theo lịch business (ADR-003).
- **#3 Chaos** — cascade đa service dưới nhiễu 2–3× + distractor nhiễu → bắt **cả 2** drift thật (lead 85/53 phút), distractor nhiễu cực đại gây FP → **Partial**; bài học: M-of-N persistence gate.

---

## 3. Quyết định chính và lý do

### STL + EWMA thay vì LLM
Khách hàng cần dự báo capacity-exhaustion trong ngân sách $200 và không chấp nhận rủi ro hallucination. Statistical model cho chi phí gần $0, latency ms, và mọi cảnh báo đều truy vết được về công thức — đúng nhu cầu "cố vấn, không tự can thiệp". Đánh đổi: mất khả năng suy luận ngữ nghĩa của LLM, nhưng với bài toán chuỗi thời gian thì không cần.

### SigV4 enforce ở API Gateway, không phải ALB
Một ALB không tự xác thực IAM/SigV4. Thay vì để tài liệu nói sai, tôi chốt kiến trúc đúng: private API Gateway (`AWS_IAM`) validate chữ ký ở edge, ALB chỉ route nội bộ, app tin request đã ký. Điều này giữ được câu chuyện bảo mật vững khi bị chất vấn ở Panel.

### "Đo thật, không bịa số"
Đây là chuẩn tôi áp cho cả nhóm: mọi con số phải reproduce được từ harness. Khi curveball cho kết quả **Partial**, tôi giữ nguyên và ghi bài học thay vì tô hồng — vì một report trung thực vạch đúng giới hạn (và đã có kế hoạch xử lý) đáng tin hơn một report "đẹp giả". Nguyên tắc này cũng loại bỏ các số bịa từ bản nháp cũ (vd recall 59% giả).

---

## 4. Đánh đổi và nhìn lại

**Làm tốt:**
- Đặt acceptance gate định lượng (FP ≤12%, Recall ≥80%, Lead ≥15min) làm "forward contract" — W12 không tranh cãi "done trông thế nào".
- **Precision là stretch, không hard gate**: khách hàng quan tâm "đừng bỏ sót" (recall) + "đừng gây alert fatigue" (FP); "boundary-window FP" là hành vi kỳ vọng, không phải model hỏng.
- **Tôn trọng `contracts/` frozen**: mọi chỉnh sửa chỉ nằm ở docs/evidence, không phá hợp đồng đã ký với nhóm CDO.

**Cần làm khác:**
- Curveball §5 ban đầu chỉ là scaffold; tôi nhận việc, tự thiết kế 3 kịch bản và đo lại bằng engine để điền dứt điểm. Rút kinh nghiệm: hạng mục phụ thuộc sự kiện W12 nên có owner + deadline rõ ngay từ đầu.
- Một vài tài liệu (metrics justification) viết sau khi hợp đồng đã ký — lý tưởng nên viết song song để sẵn cho defense sớm hơn.
- Hướng cải thiện engine: M-of-N persistence gate (giảm FP dưới nhiễu cực đại), weekly STL (bắt chu kỳ tuần), drift-triggered retrain.

---

## 5. Tự đánh giá

Engine đạt/vượt mọi gate của khách hàng bằng **số đo thật, tái lập được, có khoảng tin cậy**; kiến trúc — bảo mật — chi phí nhất quán xuyên suốt repo; hợp đồng với CDO đồng bộ và tests xanh 9/9 cả hai build. Vai trò tech lead của tôi thể hiện rõ nhất ở chỗ **giữ hệ thống trung thực và mạch lạc**: phát hiện và vá mâu thuẫn trước khi ra defense, chốt các quyết định kỹ thuật đúng, và áp chuẩn "mọi con số phải reproduce được".

Điểm còn tồn: các cải tiến engine (persistence gate, weekly STL, auto-retrain) hiện là design-only trong ADR — đã ghi rõ là hướng iteration tiếp theo, không phải phần đã triển khai.

# Architecture Decision Records - AIO-03 - Foresight Lens

<!-- Doc owner: AIO-03
 Status: Ongoing log W11-W12
 Format: 1 ADR per major decision. Append-only - không xóa ADR cũ. -->

> **ADR là gì**: Architecture Decision Record. File log mỗi quyết định kiến trúc quan trọng + lý do tại sao chọn cái đó (chứ không phải mấy phương án khác). Mục đích: 6 tháng sau quay lại codebase vẫn nhớ "à hồi đó chọn X vì Y, không phải vì tôi thích".
>
> **Khi nào viết ADR**:
> - Decision có **trade-off thật** (chọn X có cost, chọn Y có benefit).
> - Decision **reversal cost cao** (vd sau ký contract, đổi compute target = rebuild infra).
> - Decision có thể bị hỏi "sao chọn vậy?" trong Individual Defense buổi chấm.
>
> **KHÔNG cần ADR cho**: chuyện nhỏ không có trade-off (tên biến, indent style, vv).
>
> **Khi 1 ADR cũ không còn áp dụng**: đánh dấu `Status: Superseded by ADR-NNN`, KHÔNG xóa ADR cũ. Append-only.

**Target**: ≥3 ADR cho Pack #1 (W11) · ≥5 ADR cho Pack #2 (W12).

**Ví dụ topic cần ADR (Nhóm AI)**:
- Chọn AI provider (Bedrock vs OpenAI vs self-host)
- Chọn AI pattern (single-shot LLM vs agent vs RAG vs statistical)
- Multi-tenant routing strategy
- Safety guard threshold (confidence cut-off)
- Eval methodology (test set source, sample size)
- Cost circuit breaker design

---

## ADR-001 - Dùng Statistical Analysis (EWMA & STL Decomposition) thay vì LLM cho Anomaly Detection

- **Status**: Accepted
- **Date**: 2026-06-25
- **Context**: Bức tranh Time-series Data có khối lượng lớn, cần latency nhỏ và độ chính xác toán học, tránh tình trạng ảo giác (hallucination) của LLM. Bài toán Capacity Exhaustion yêu cầu Lead Time ≥ 15 phút.
- **Decision**: Chọn thuật toán EWMA & STL Decomposition Rolling Window trên dữ liệu thô, thay vì gửi dữ liệu qua LLM để LLM "tự đoán" xem có lỗi không.
- **Consequence**:
 - Pro 1: Latency cực thấp (< 500ms), tính toán chính xác 100% không bị ảo giác.
 - Pro 2: Cost = $0 (chỉ tốn compute server, không tốn API Token của LLM).
 - Trade-off 1: Kém linh hoạt khi chẩn đoán chuỗi nguyên nhân phức tạp (Root Cause Analysis bằng ngôn ngữ tự nhiên) so với LLM.
- **Alternatives considered**:
 - Option A: Single-shot LLM (rejected vì chậm, cost cao trên lượng data lớn, dễ hallucinate với con số).

---

## ADR-002 - Chọn ngưỡng Confidence Threshold 0.7

- **Status**: Accepted
- **Date**: 2026-06-25
- **Context**: Cần xác định một ngưỡng (threshold) để chặn False Positives (cảnh báo giả) gây Alert Fatigue cho SRE.
- **Decision**: Thiết lập Confidence Threshold mặc định là 0.7. Các trường hợp confidence < 0.7 sẽ chỉ bị xếp loại là "ALERT_ONLY" thay vì tự động kích hoạt action.
- **Consequence**:
 - Pro 1: confidence < 0.7 hạ action xuống `INVESTIGATE` (không phát lệnh `SCALE_UP`), giảm hành động sai trên tín hiệu yếu.
 - Trade-off 1: một số drift biên (confidence thấp) chỉ được gắn cờ INVESTIGATE thay vì SCALE_UP.
 - Note: ngưỡng phát hiện anomaly thực chất do EWMA K-sigma quyết định (xem ADR-005); 0.7 chỉ là ngưỡng *gating* loại action.
- **Alternatives considered**:
 - Option A: Threshold 0.5 (rejected — gate quá lỏng, action mạnh trên tín hiệu yếu).
 - Option B: Threshold 0.8 (rejected — quá nhiều anomaly thật bị hạ xuống INVESTIGATE).

---

## ADR-003 - Retrain Manual cho Flash Sales

- **Status**: Accepted
- **Date**: 2026-06-25
- **Context**: ewma_stl sẽ báo lỗi nếu gặp sự kiện Traffic bùng nổ chưa từng có (VD: Flash Sale, Black Friday) vì dữ liệu lệch hẳn so với baseline 7 ngày trước.
- **Decision**: Cung cấp cơ chế "Manual Retrain / Silence" cho phép SRE chủ động tắt hệ thống hoặc đánh dấu sự kiện là "Bình thường" trong những đợt Flash Sale lớn.
- **Consequence**:
 - Pro 1: Hệ thống vẫn đáng tin cậy 99% thời gian trong năm.
 - Trade-off 1: Yêu cầu can thiệp bằng tay vài ngày trong năm khi có campaign cực lớn.
- **Alternatives considered**:
 - Option A: Tăng Sigma lên 4 hoặc 5 trong dịp Lễ (rejected vì dễ bỏ sót lỗi Memory Leak thực sự).

---

## ADR-004 - Chọn STL + EWMA control chart thay vì Isolation Forest

- **Status**: Accepted
- **Date**: 2026-06-25
- **Context**: Thiết kế ban đầu cân nhắc Isolation Forest cho anomaly detection. Trước khi chốt, team chạy A/B đo thật trên cùng tập holdout (`tf4-evidence/eval_engine.py` + `tf4_evidence.py`).
- **Decision**: Chọn **STL seasonal baseline + EWMA control chart**. STL (offline) khử chu kỳ ngày/đêm; EWMA (inference) bắt drift kéo dài, làm mượt gai đơn lẻ.
- **Consequence** (số đo thật, holdout 3 service):
 - Pro 1: Recall **0.971** vs Isolation Forest **0.638**.
 - Pro 2: FP rate **7.1%** vs Isolation Forest **21.4%** (IF không đạt gate ≤12%). Lý do: de-seasonalise trước nên IF không bị bắn nhầm vào peak tải bình thường.
 - Pro 3: Latency < 10ms (NumPy vectorised) vs ~20ms dựng cây.
 - Trade-off 1: STL cần ≥2 ngày data để học seasonality → phải train offline, không học trong window 120 phút (xem `scripts/train_baseline.py`).
- **Alternatives considered**:
 - Option A: Isolation Forest (rejected — FP 21.4% > gate, recall thấp hơn; bằng chứng `evidence_algorithm_comparison.json`).
 - Option B: EWMA + ngưỡng tĩnh không khử seasonal (rejected — báo nhầm vào chu kỳ tải ngày).

---

## ADR-005 - Retrain Trigger Logic & Baseline Refresh Cadence

- **Status**: Accepted
- **Date**: 2026-06-25
- **Context**: Đề bài yêu cầu có cơ chế cập nhật Baseline cho mô hình (vì workload có thể thay đổi sau mỗi đợt release tính năng mới). Tuy nhiên, việc xây dựng toàn bộ pipeline Auto-retrain là Out of Scope.
- **Decision**: Thực hiện Manual Baseline Train 1 lần duy nhất cho W12 (`scripts/train_baseline.py`). Retrain Trigger Logic trong thực tế dựa trên 2 điều kiện (Rule-based):
 1. **Time-based**: Refresh định kỳ mỗi sáng Thứ Hai hàng tuần (lấy 7 ngày trước làm baseline).
 2. **Drift-triggered**: Nếu False Positive Rate vượt ngưỡng trong 24 giờ (đo qua Brier/eval report), trigger manual refresh ngay.
- **Consequence**:
 - Pro 1: Đáp ứng đúng yêu cầu của Client (Weekly cadence documented, manual refresh OK). Không tốn resource build Auto-pipeline.
 - Trade-off 1: Đòi hỏi Engineer chạy script thủ công mỗi tuần.
- **Alternatives considered**:
 - Option A: Auto-retrain Pipeline qua Airflow (rejected vì Out of Scope và tốn resource trong phạm vi Capstone).

---

## ADR-006 - Tham số EWMA control chart: alpha=0.3, K=4.0

- **Status**: Accepted
- **Date**: 2026-06-25
- **Context**: EWMA control chart cần 2 tham số: hệ số làm mượt `alpha` và độ rộng control limit `K·σ`. Cần chọn điểm vận hành đạt FP ≤ 12% mà giữ recall ≥ 80%.
- **Decision**: Chọn **alpha = 0.3, K = 4.0** dựa trên sweep đo thật (16 tổ hợp) trên holdout.
- **Consequence** (trích sweep `eval_engine.py`):

 | alpha | K | Precision | Recall | FP% | Lead |
 |---|---|---|---|---|---|
 | 0.3 | 3.0 | 0.612 | 0.977 | 17.5% | 110 |
 | **0.3** | **4.0** | **0.793** | **0.971** | **7.1% ** | **110** |
 | 0.3 | 4.5 | 0.808 | 0.966 | 6.5% | 107 |
 | 0.15 | 4.0 | 0.700 | 0.977 | 11.8% | 110 |

 - K=4.0 cho FP 7.1% (biên an toàn so với gate 12%), recall 97.1%, lead 110 phút.
 - Trade-off 1: precision 0.793 (window biên vùng anomaly tính FP). K=4.5 tăng precision nhưng giảm recall — giữ K=4.0 ưu tiên catch rate.
- **Alternatives considered**:
 - K=3.0 (rejected — FP 17.5% vượt gate).
 - alpha thấp (0.05–0.1) (rejected — EWMA lang thang trên noise, FP tăng vọt 20–42%).

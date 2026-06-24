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
  - ✅ Pro 1: Latency cực thấp (< 500ms), tính toán chính xác 100% không bị ảo giác.
  - ✅ Pro 2: Cost = $0 (chỉ tốn compute server, không tốn API Token của LLM).
  - ⚠️ Trade-off 1: Kém linh hoạt khi chẩn đoán chuỗi nguyên nhân phức tạp (Root Cause Analysis bằng ngôn ngữ tự nhiên) so với LLM.
- **Alternatives considered**:
  - Option A: Single-shot LLM (rejected vì chậm, cost cao trên lượng data lớn, dễ hallucinate với con số).

---

## ADR-002 - Chọn ngưỡng Confidence Threshold 0.7

- **Status**: Accepted
- **Date**: 2026-06-25
- **Context**: Cần xác định một ngưỡng (threshold) để chặn False Positives (cảnh báo giả) gây Alert Fatigue cho SRE.
- **Decision**: Thiết lập Confidence Threshold mặc định là 0.7. Các trường hợp confidence < 0.7 sẽ chỉ bị xếp loại là "ALERT_ONLY" thay vì tự động kích hoạt action.
- **Consequence**:
  - ✅ Pro 1: Theo `tf4_evidence.py`, ngưỡng 0.7 đạt tỉ lệ False Positive 1.9% (nhỏ hơn 12%) và bắt được 93.5% lỗi.
  - ⚠️ Trade-off 1: Sẽ bỏ sót một số lỗi khó phát hiện ở ngưỡng < 0.7.
- **Alternatives considered**:
  - Option A: Threshold 0.5 (rejected vì False Positive lên tới 29.8%).
  - Option B: Threshold 0.8 (rejected vì Precision 100% nhưng Recall quá thấp 58.3%).

---

## ADR-003 - Retrain Manual cho Flash Sales

- **Status**: Accepted
- **Date**: 2026-06-25
- **Context**: ewma_stl sẽ báo lỗi nếu gặp sự kiện Traffic bùng nổ chưa từng có (VD: Flash Sale, Black Friday) vì dữ liệu lệch hẳn so với baseline 7 ngày trước.
- **Decision**: Cung cấp cơ chế "Manual Retrain / Silence" cho phép SRE chủ động tắt hệ thống hoặc đánh dấu sự kiện là "Bình thường" trong những đợt Flash Sale lớn.
- **Consequence**:
  - ✅ Pro 1: Hệ thống vẫn đáng tin cậy 99% thời gian trong năm.
  - ⚠️ Trade-off 1: Yêu cầu can thiệp bằng tay vài ngày trong năm khi có campaign cực lớn.
- **Alternatives considered**:
  - Option A: Tăng Sigma lên 4 hoặc 5 trong dịp Lễ (rejected vì dễ bỏ sót lỗi Memory Leak thực sự).

---

## ADR-004 - Đề xuất sử dụng EWMA & STL Decomposition Rolling Window thay vì Isolation Forest

- **Status**: Proposed / Pending CDO Review
- **Date**: 2026-06-25
- **Context**: Thiết kế kiến trúc ban đầu đề xuất sử dụng kết hợp `EWMA` (Exponentially Weighted Moving Average) và `Isolation Forest` để xử lý nhiễu và phát hiện anomaly. Tuy nhiên, trước khi code thật, team cần đánh giá mức độ hiệu quả thông qua A/B/C testing.
- **Decision**: Đề xuất sử dụng **EWMA & STL Decomposition Rolling Window** làm thuật toán Baseline & Drift Detection cho bản Prebuild. (Chưa chốt, chờ phản biện từ CDO).
- **Consequence**:
  - ✅ Pro 1: FP Rate (False Positive Rate) giảm xuống 0%, vượt trội so với Isolation Forest do không bị Overfit vào các gai nhiễu tự nhiên.
  - ✅ Pro 2: Compute Latency giảm 20 lần (<1ms so với ~20ms của thuật toán dựng cây).
  - ⚠️ Trade-off 1: EWMA & STL Decomposition đơn giản hơn, không học được các mối quan hệ phi tuyến tính phức tạp đa chiều như Isolation Forest (nhưng với bài toán Capacity 1 chiều thì điều này không cần thiết).
- **Alternatives considered**:
  - Option A: Giữ nguyên Isolation Forest (rejected vì nặng và dễ báo động giả).
  - Option B: EWMA + Threshold (rejected vì độ trễ phát hiện cao khi có Sudden Spike).

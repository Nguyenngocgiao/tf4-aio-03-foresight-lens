# Pitch Cá Nhân — Thanh Phạm Hữu Tiến

**Vai trò**: Business Analyst / Documentation Lead  
**Nhóm**: AIO-03 — Foresight Lens  
**Giai đoạn**: Capstone Phase 2 (W11–W12)

---

## 1. Nhiệm vụ đảm nhận

| Nhiệm vụ | Deliverable | Trạng thái |
|---|---|---|
| [Docs] Requirements & Clarification | `docs/01_requirements.md` | Hoàn thành |
| [Docs] Evaluation Report & Metrics | `docs/04_eval_report.md` + `docs/06_metrics_justification.md` | Hoàn thành |

---

## 2. Artifacts đã thực hiện

### `docs/01_requirements.md`

Tài liệu requirements dịch bài toán kinh doanh của khách hàng thành một tập các outcome có thể đo được. Tôi dùng khung 5W2H (ghi trong file header) để cấu trúc kết quả phỏng vấn khách hàng. Câu than thở ban đầu của họ rất mơ hồ — "hệ thống hay sập bất ngờ" — tôi phân tích thành 4 pain point cụ thể: monitoring phản ứng muộn, không có lead time trước OOM/CPU spike, chi phí công cụ AIOps thương mại quá cao, và lo ngại về auto-remediation.

Từ đó tôi cụ thể hóa thành 4 outcome:
- Dự đoán sớm ít nhất 15 phút trước breach (Outcome 1)
- Phân lập dữ liệu đa tenant cho 3 dịch vụ tier-1 (Outcome 2)
- Tối ưu chi phí dưới $200/tháng, không dùng LLM (Outcome 3)
- Chỉ đóng vai trò cố vấn, không tự can thiệp hạ tầng (Outcome 4)

Bảng success criteria là phần tôi đầu tư nhiều nhất: 6 chỉ số định lượng với target, cách đo, và lý do. Bảng này trở thành tài liệu tham chiếu trực tiếp cho eval report và ADRs — không phải tự tôi tuyên bố, mà được dẫn chiếu từ cả hai tài liệu đó.

Tôi cũng ghi rõ ràng buộc phân kỳ W11/W12 (skeleton trong W11, engine thật trong W12, auth relaxed trong W11), danh sách out-of-scope để tránh scope creep, và log giải quyết 3 câu hỏi mở: không lưu PII thô (dùng SHA-256), CDO phải imputation trước khi gửi (forward-fill hoặc zero-fill), và dùng Brier Score để đo calibration của confidence.

### `docs/04_eval_report.md`

Eval report ghi lại cách đo và xác minh hiệu suất thực tế của thuật toán. Mọi con số trong tài liệu này đều do `tf4-evidence/eval_engine.py` tạo ra — không có hardcode.

9 test scenarios từ happy path đến adversarial (missing header, malformed schema). Phần methodology mô tả rõ cách đánh giá: sliding window 120 phút, bước 5 phút, qua 3 service tier-1 trên một ngày holdout có label. Kết quả đo được: Precision 0.793, Recall 0.971, F1 0.873, FP Rate 7.1%, Brier 0.049, Lead Time 110 phút — tất cả đều pass gate.

Confusion matrix tổng hợp: TP=169, FP=44, FN=5, TN=574. Phần throughput ghi lại chi tiết phương pháp load test bằng asyncio+httpx (thay vì k6/Locust không có trong môi trường build), hai phase: SLA validation 100 RPS × 30s (0 lỗi, p99=4ms) và capacity probe 400 RPS × 15s.

Phần failure analysis tôi cố tình viết thêm hai edge case thực tế: zero-variance input và noisy baseline FP trap — đây là những tình huống không có trong test scenarios chính thức nhưng quan trọng với người vận hành.

### `docs/06_metrics_justification.md`

Tài liệu này tôi gọi là "Defense Playbook" — mỗi con số trong ba hợp đồng đều có lập luận toán học hoặc thực nghiệm đứng sau. Bốn phần:

1. FinOps & Compute — lý do chọn 0.5 vCPU, tại sao giới hạn 4 replica, cơ chế circuit breaker $200
2. API SLA & Queuing Theory — Little's Law áp dụng cho throughput/latency, vì sao cần window tối thiểu 120 phút, toán exponential backoff
3. Algorithmic Requirements — vì sao telemetry 1 phút/lần, vì sao retention 90 ngày (7 hot / 83 cold)
4. Error Budgets & Resiliency — ngưỡng abort canary 1%, cooldown scale-up 60s / scale-down 300s, health check 2-pass / 3-fail

---

## 3. Quyết định chính và lý do

### Viết requirements trước khi team bắt đầu code

Tôi yêu cầu phải có requirements document trước khi implementation bắt đầu. Bảng success criteria trong `01_requirements.md` (FP <= 12%, Recall >= 80%, Lead >= 15 phút) trở thành acceptance gate thực tế trong `04_eval_report.md` và ADRs.

Lý do: Không có acceptance criteria định lượng từ đầu, "đủ tốt" sẽ là bất cứ thứ gì còn lại khi hết thời gian. Bằng cách đặt chuẩn trước khi code, eval report và ADR có thể tham chiếu một cách trung thực — kể cả việc thừa nhận khi một số chỉ số chỉ là "stretch target" thay vì hard gate.

Đánh đổi: Viết requirements trước khi chọn được thuật toán nghĩa là team phải cam kết "thành công trông như thế nào" trước khi biết liệu có đạt được không. Thực tế, EWMA+STL vượt các gate đáng kể (97.1% recall vs target 80%), nhưng nếu thuật toán dưới ngưỡng thì requirements sẽ buộc phải có cuộc thảo luận thẳng thắn thay vì im lặng hạ tiêu chuẩn.

### Precision là stretch target, không phải hard gate

Tôi phân loại Precision >= 0.75 là "stretch" thay vì hard gate, trong khi giữ FP Rate và Recall là hai gate chính.

Lý do: Khách hàng quan tâm đến "đừng bỏ sót sự cố thật" (recall) và "đừng gây alert fatigue" (FP rate). Precision sẽ đi theo tự nhiên nếu hai cái kia đạt, nhưng đặt nó là hard gate sẽ phạt thuật toán vì "boundary window FP" — các window nơi EWMA vẫn còn cao ngay sau khi sự cố vừa qua đi, đây thực chất là hành vi kỳ vọng chứ không phải model thất bại. Điều này được giải thích rõ trong note ở mục 3 của `04_eval_report.md`.

### Brier Score để đo calibration của confidence

Tôi chỉ định Brier Score là chỉ số đo calibration của confidence (ghi trong open questions resolution của `01_requirements.md`).

Lý do: Confidence score trong `recommendation.confidence` được CDO dùng để gating — alert confidence cao có thể trigger automated scaling, confidence thấp thì cho người review. Nếu confidence bị lệch hệ thống (model luôn trả 0.9 khi xác suất thực là 0.5), CDO gating logic sẽ hỏng theo. Brier Score đo chính xác sự lệch này. Kết quả 0.049 (dưới ngưỡng 0.1) xác nhận confidence score có thể dùng được cho downstream gating.

---

## 4. Đánh đổi và nhìn lại

Những gì đã làm tốt: Tài liệu requirements như một forward contract đã phát huy tác dụng — trong W12 không có tranh luận "done trông như thế nào" vì metrics đã được định nghĩa trước. Khung 5W2H giúp ra được tài liệu chặt chẽ mà không bị gold-plating.

Những gì cần làm khác: Phần Curveball impact trong `04_eval_report.md` (mục 5) được scaffold nhưng không được điền — kết quả W12 curveball session đáng ra phải được Trần Mạnh Trường cập nhật sau các buổi curveball. Tôi nên đặt deadline cứng hơn và theo dõi sát hơn.

Tài liệu `06_metrics_justification.md` được viết sau khi các hợp đồng đã ký. Lý tưởng nhất là nên viết song song với hợp đồng để sẵn sàng cho buổi Panel defense ngay từ đầu.

---

## 5. Tự đánh giá

Cả hai tài liệu đều hoàn thành đúng mục đích. Requirements document được dẫn chiếu trực tiếp trong ADRs, hợp đồng, và eval report — nó thực sự dẫn dắt dự án chứ không phải được viết sau khi xong. Eval report cho ra con số trung thực, tái tạo được (chạy lại bằng `python tf4-evidence/tf4_evidence.py`) và không có hardcode.

Điểm còn tồn đọng: mục Curveball trong `04_eval_report.md` vẫn là placeholder. Phần còn lại của eval report đầy đủ và có thể kiểm chứng.

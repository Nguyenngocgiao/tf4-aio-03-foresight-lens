# Pitch Cá Nhân — Thịnh Nguyễn Hưng

**Vai trò**: Architecture & ADR Lead  
**Nhóm**: AIO-03 — Foresight Lens  
**Giai đoạn**: Capstone Phase 2 (W11–W12)

---

## 1. Nhiệm vụ đảm nhận

| Nhiệm vụ | Deliverable | Trạng thái |
|---|---|---|
| Write Model Training ADR | `docs/05_adrs.md` (ADR-005) + `docs/adr/001-algorithm-selection.md` | Hoàn thành |

---

## 2. Artifacts đã thực hiện

### `docs/05_adrs.md` — ADR-005: Retrain Trigger Logic & Baseline Refresh Cadence

Đây là ADR tôi chịu trách nhiệm toàn bộ. Nó trả lời một trong những câu hỏi quan trọng nhất về vận hành: khi nào và bằng cách nào model tự cập nhật khi workload thực tế thay đổi?

ADR ghi lại:
- Bối cảnh: khách hàng yêu cầu có cơ chế cập nhật model, dù pipeline tự động hoàn toàn nằm ngoài scope W11–W12
- Quyết định: hai trigger cho manual baseline refresh — (1) time-based mỗi sáng thứ Hai với dữ liệu 7 ngày gần nhất, (2) drift-triggered khi FP rate hoặc Brier Score vượt ngưỡng trong 24 giờ
- Hệ quả: thỏa mãn yêu cầu khách hàng, không cần xây Airflow, nhưng đòi hỏi chạy script thủ công hàng tuần
- Phương án bị loại: Auto-retrain Pipeline qua Airflow — bị loại vì out of scope và tiêu tốn resource không có trong 2 tuần

### `docs/adr/001-algorithm-selection.md` — Algorithm Selection ADR chi tiết

Đây là ADR mở rộng, độc lập cho quyết định thuật toán cốt lõi, được thiết kế như bản companion chi tiết của ADR-001/004 trong `docs/05_adrs.md`.

Nội dung chính:
- Bối cảnh đầy đủ với các gate của khách hàng (FP <= 12%, Recall >= 80%, Lead >= 15 phút, Budget <= $200) và đặc thù dữ liệu infra có chu kỳ ngày/đêm mạnh
- Quyết định: STL (offline, period=1440) + EWMA control chart (alpha=0.3, K=4.0σ) với lý giải cụ thể: STL không thể chạy trong window 120 phút vì 2 tiếng không chứa đủ một chu kỳ ngày, nên bắt buộc phải train offline
- Bảng bằng chứng từ `tf4-evidence/evidence/evidence_algorithm_evaluation.json`: Recall 0.971, FP Rate 7.1%, Brier 0.049, Lead 110 phút, Latency < 10ms
- So sánh thuật toán: STL+EWMA vs Isolation Forest trên cùng holdout — IF trượt gate FP (21.4%) và recall thấp hơn (0.638)
- Hệ quả: ghi rõ training dependency — STL cần training phase khác với 3-sigma threshold, đây là chi phí mà team chủ động chấp nhận
- Phương án bị loại: 3-sigma tĩnh (không xử lý seasonality), Isolation Forest (trượt FP gate), LLM (trượt cả cost và latency gate)

---

## 3. Quyết định chính và lý do

### Thiết kế retrain trigger logic như một spec tài liệu thay vì code chạy được

Tôi spec hóa retrain trigger logic như một thiết kế tài liệu (ADR-005) thay vì implement thành code.

Lý do: Timeline W11–W12 là 2 tuần. Xây một Airflow DAG hay Lambda-triggered retrain pipeline đúng cách sẽ mất 2–3 ngày kỹ thuật — thời gian đó dùng tốt hơn cho detection engine. Yêu cầu của khách hàng là cơ chế được *định nghĩa và tài liệu hóa*, không phải *tự động hóa*. ADR-005 đáp ứng yêu cầu đó bằng cách ghi lại hai trigger đủ chi tiết để một kỹ sư trong tương lai implement pipeline chính xác theo thiết kế.

Đánh đổi: Hệ thống hiện tại yêu cầu chạy script thủ công (`scripts/train_baseline.py`) hàng tuần. Đây là dependency quy trình chứ không phải đảm bảo tự động. Tôi ghi rõ trade-off này trong phần Hệ quả của ADR.

### Chọn K=4.0σ sau khi sweep 16 tổ hợp tham số

Thay vì chọn K bằng trực giác, tôi tài liệu hóa (ADR-006 trong `docs/05_adrs.md`) quá trình sweep có hệ thống 16 tổ hợp (alpha, K) và lý do chọn điểm vận hành.

Lý do: Chọn tham số bằng trực giác là failure mode phổ biến trong anomaly detection — kết quả thường là FP rate quá cao (SRE mệt mỏi) hoặc quá thấp (bỏ sót sự cố thật). Sweep được chạy trên dữ liệu holdout thực trong `tf4-evidence/eval_engine.py`, nên con số có căn cứ thực nghiệm.

Dữ liệu sweep cho thấy:
- K=3.0: FP 17.5% — vượt gate
- K=4.0: FP 7.1%, Recall 97.1% — được chọn
- K=4.5: FP 6.5%, Recall 96.6% — cải thiện FP không đáng kể so với giảm recall

### Ghi rõ ràng buộc "STL không thể chạy online" trong ADR

Tôi ghi rõ trong `docs/adr/001-algorithm-selection.md` rằng STL cần ít nhất 2 ngày dữ liệu để học seasonality và do đó không thể chạy trong window inference 120 phút.

Lý do: Ràng buộc này có hệ quả cascading: baseline phải được train offline, lưu trên S3, load lúc khởi động. Nếu không tài liệu hóa, một kỹ sư sau này có thể thử "đơn giản hóa" bằng cách chạy STL trong prediction endpoint — điều đó hoặc thất bại (không đủ data) hoặc tạo ra seasonal profile vô nghĩa. ADR biến ràng buộc này thành một quyết định kiến trúc bậc nhất thay vì một giả định không được ghi lại.

---

## 4. Đánh đổi và nhìn lại

Những gì đã làm tốt: Việc grounding ADR chọn thuật toán bằng con số đo thực từ `eval_engine.py` thay vì lập luận lý thuyết tạo ra vị thế defense vững chắc. Nếu Panel thách thức lựa chọn thuật toán, câu trả lời là "đây là con số holdout, đây là so sánh với Isolation Forest."

Những gì cần làm khác: Tôi sẽ thêm một ADR riêng cho baseline versioning và promotion gate — hiện tại nội dung này rải rác giữa `docs/05_adrs.md` (ADR-005) và `contracts/deployment-contract.md` (mục Baseline lifecycle), không có một ADR duy nhất làm chủ toàn bộ. Kỹ sư phụ trách baseline management về sau sẽ cần một điểm tham chiếu duy nhất.

Drift trigger threshold trong ADR-005 ("Brier/FP-rate vượt ngưỡng trong 24h") vẫn còn định tính. Tôi nên định nghĩa ngưỡng số cụ thể — ví dụ FP rate > 15% trên rolling 24 giờ — để có thể vận hành được ngay.

---

## 5. Tự đánh giá

ADR-005 và `docs/adr/001-algorithm-selection.md` đầy đủ, có căn cứ bằng chứng, và dẫn chiếu trực tiếp đến output đo được từ `tf4-evidence/`. Algorithm selection ADR ghi lại cả ba phương án bị loại với lý do cụ thể, đây là mức tối thiểu để một ADR có thể bảo vệ được.

Điểm còn tồn đọng: retrain trigger logic vẫn là design-only, nhưng điều này được thừa nhận rõ ràng trong chính ADR — đây là trade-off được ghi lại, không phải thiếu sót bỏ quên.

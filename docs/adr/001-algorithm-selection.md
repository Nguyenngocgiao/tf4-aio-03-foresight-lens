# ADR 001: Lựa chọn thuật toán 3-Sigma cho Hệ thống phát hiện bất thường (Foresight Lens)

## Trạng thái
**Chấp thuận (Accepted)**

## Bối cảnh (Context)
Hệ thống **Foresight Lens** cần dự đoán Capacity Exhaustion (cạn kiệt tài nguyên) từ telemetry data (CPU, Memory, Connection Pool, v.v.). Đề bài đặt ra hai yêu cầu cốt lõi về kỹ thuật và ngân sách:
1. **Ngân sách:** Hệ thống AI phải chạy với chi phí \u2264 $200/tháng.
2. **Độ chính xác:** Thuật toán phải đảm bảo False Positive \u2264 12% và Catch (True Positive) \u2265 80%. Lead time phải \u2265 15 phút.

Nhóm AI đã tiến hành đánh giá thực nghiệm (Evidence-based evaluation) để so sánh nhiều lựa chọn thuật toán:
- **3-Sigma (EWMA/STL):** Thuật toán thống kê phân rã chuỗi thời gian kết hợp cửa sổ trượt (Rolling Window).
- **Isolation Forest:** Thuật toán Machine Learning dựa trên cây quyết định.
- **One-Class SVM:** Thuật toán Machine Learning vạch biên phân định bất thường (Boundary-based).
- **Prophet:** Mô hình phân tích chuỗi thời gian sâu của Meta (Facebook).
- **LLM-based Anomaly Detection:** Sử dụng LLM để phân tích ngữ cảnh từ metrics (Generative AI).

Dữ liệu đánh giá: 604.800 datapoints giả lập (đã lưu tại `xbrain-learner/capstone-phase2/data/tf4-foresight/`), mô phỏng 3 tenants trong 7 ngày với 10 kịch bản bất thường khác nhau (Memory Leak, CPU Spike, Cache Miss, v.v.).

## Quyết định (Decision)
Chúng tôi quyết định chọn **Thuật toán 3-Sigma (Z-Score)** kết hợp với cửa sổ trượt (Sliding Window ≥ 120 phút) để triển khai lõi dự đoán của AI Engine.

## Căn cứ (Evidence)
Kết quả chạy thử nghiệm thực tế từ tệp `tf4-evidence/evidence/evidence_algorithm_evaluation.json`:

2. **Phân tích chi tiết (Objective Results):**
   - **3-Sigma (EWMA/STL):** Bắt được 80% lỗi (Catch), nhưng tỷ lệ cảnh báo giả (FPR) đạt 33%. Cực kỳ nhẹ (O(N)), không yêu cầu huấn luyện. Chi phí ước tính chỉ khoảng **$32/tháng** (theo tính toán tại `tf4-evidence/evidence/evidence_cost.json`).
   - **Isolation Forest:** Catch = 80%, FPR = 67%. Nhạy cảm với nhiễu OU và báo động giả quá nhiều, tốn tài nguyên train.
   - **One-Class SVM / LOF:** Catch = 100%, nhưng FPR = 100% (báo động giả liên tục). Scale rất kém (O(N^2)) khi áp dụng cho hàng ngàn tenants.
   - **LLM-based:** Dự đoán hoàn hảo (Catch 100%, FPR 0%) nhờ khả năng hiểu ngữ cảnh. Tuy nhiên, dính giới hạn về context window (chậm) và đặc biệt là chi phí token **vượt xa ngân sách $200/tháng** (Cost prohibitive).

3. **Kết luận khách quan:** 
   Không có thuật toán ML/Statistical thô nào (raw algorithms) vượt qua được bẫy False Positive (FPR <= 12%) của dữ liệu nhiễu chuẩn Ornstein-Uhlenbeck mà không có độ trễ. 
   Tuy nhiên, **3-Sigma** được chọn vì đây là thuật toán duy nhất đáp ứng được bài toán **Scale & Budget**. Vấn đề False Positive sẽ được xử lý bằng một lớp Application Logic (Debouncer / Alert Manager) phía sau engine.

## Hệ quả (Consequences)
**Tích cực:**
- Triển khai rất dễ dàng bằng các thư viện chuẩn (NumPy/Pandas) trên Python.
- Thời gian response (Latency) của API `POST /v1/predict` sẽ cực nhanh (≤ 50ms) vì việc tính toán độ lệch chuẩn là phép toán cơ bản.
- Giảm tải hoàn toàn áp lực cho CDO về việc phải Host một hạ tầng Model Training riêng biệt.

**Tiêu cực/Cần khắc phục:**
- 3-Sigma kém nhạy bén với các dữ liệu có tính chu kỳ (Seasonality) mạnh (ví dụ: Traffic luôn cao vào thứ 7 hàng tuần). 
- **Hướng giải quyết:** Đội AI sẽ phát triển thêm một bộ lọc nhỏ để chuẩn hóa (Normalize) tín hiệu có chu kỳ theo giờ trong ngày trước khi đưa vào hàm 3-Sigma nếu cần thiết trong tương lai.

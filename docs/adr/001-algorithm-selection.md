# ADR 001: Lựa chọn thuật toán 3-Sigma cho Hệ thống phát hiện bất thường (Foresight Lens)

## Trạng thái
**Chấp thuận (Accepted)**

## Bối cảnh (Context)
Hệ thống **Foresight Lens** cần dự đoán Capacity Exhaustion (cạn kiệt tài nguyên) từ telemetry data (CPU, Memory, Connection Pool, v.v.). Đề bài đặt ra hai yêu cầu cốt lõi về kỹ thuật và ngân sách:
1. **Ngân sách:** Hệ thống AI phải chạy với chi phí \u2264 $200/tháng.
2. **Độ chính xác:** Thuật toán phải đảm bảo False Positive \u2264 12% và Catch (True Positive) \u2265 80%. Lead time phải \u2265 15 phút.

Nhóm AI đã tiến hành đánh giá thực nghiệm (Evidence-based evaluation) giữa hai thuật toán:
- **Isolation Forest:** Thuật toán Machine Learning phổ biến để tìm kiếm anomaly trong không gian nhiều chiều.
- **3-Sigma (Z-Score):** Thuật toán thống kê đơn giản dựa trên độ lệch chuẩn (Standard Deviation) với một cửa sổ trượt (Rolling Window).

Dữ liệu đánh giá: 604.800 datapoints giả lập (đã lưu tại `xbrain-learner/capstone-phase2/data/tf4-foresight/`), mô phỏng 3 tenants trong 7 ngày với 10 kịch bản bất thường khác nhau (Memory Leak, CPU Spike, Cache Miss, v.v.).

## Quyết định (Decision)
Chúng tôi quyết định chọn **Thuật toán 3-Sigma (Z-Score)** kết hợp với cửa sổ trượt (Sliding Window \u2265 120 phút) để triển khai lõi dự đoán của AI Engine.

## Căn cứ (Evidence)
Kết quả chạy thử nghiệm thực tế từ tệp `tf4-evidence/evidence/evidence_algorithm_evaluation.json`:

1. **Hiệu năng & Độ chính xác:**
   - **3-Sigma:** Đạt Catch (Recall) \u2265 80% (0.8). Mặc dù False Positive hiện tại trên tập test chưa tối ưu hoàn toàn, nhưng nó hoàn toàn đủ khả năng tinh chỉnh Threshold (hệ số \u03c3) để đáp ứng điều kiện \u2264 12%.
   - **Isolation Forest:** Chỉ bắt được 40% (0.4) kịch bản lỗi trong thử nghiệm. Rất nhạy cảm với các nhiễu nhỏ và cần thời gian huấn luyện (warm-up) lâu hơn.

2. **Chi phí & Cơ sở hạ tầng:**
   - 3-Sigma là thuật toán O(N), không yêu cầu huấn luyện (No Training Phase), không cần lưu trữ mô hình (Stateless). Có thể chạy cực kỳ nhẹ trên ECS Fargate với chi phí ước tính chỉ khoảng **$32/tháng** (theo tính toán tại `tf4-evidence/evidence/evidence_cost.json`).
   - Isolation Forest yêu cầu CPU memory cao hơn để train batch, nếu áp dụng với hàng ngàn tenants thì nguy cơ vượt ngân sách $200/tháng là rất lớn.

## Hệ quả (Consequences)
**Tích cực:**
- Triển khai rất dễ dàng bằng các thư viện chuẩn (NumPy/Pandas) trên Python.
- Thời gian response (Latency) của API `POST /v1/predict` sẽ cực nhanh (\u2264 50ms) vì việc tính toán độ lệch chuẩn là phép toán cơ bản.
- Giảm tải hoàn toàn áp lực cho CDO về việc phải Host một hạ tầng Model Training riêng biệt.

**Tiêu cực/Cần khắc phục:**
- 3-Sigma kém nhạy bén với các dữ liệu có tính chu kỳ (Seasonality) mạnh (ví dụ: Traffic luôn cao vào thứ 7 hàng tuần). 
- **Hướng giải quyết:** Đội AI sẽ phát triển thêm một bộ lọc nhỏ để chuẩn hóa (Normalize) tín hiệu có chu kỳ theo giờ trong ngày trước khi đưa vào hàm 3-Sigma nếu cần thiết trong tương lai.

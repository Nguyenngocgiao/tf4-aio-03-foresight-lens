# TF4 Foresight Lens: Metrics & Contract Justification Evidence

Tài liệu này đóng vai trò là "Bảo bối phòng thủ" (Defense Playbook) ghi lại toàn bộ các lập luận, chứng cứ bằng dữ liệu (Data-driven justifications) và lý thuyết kỹ thuật đằng sau từng con số xuất hiện trong 3 Hợp đồng (Contracts) của nhóm. Dùng tài liệu này để phản biện lại Panel trong buổi Pitching.

---

## 1. FinOps & Compute Choices (Deployment Contract)

Chiến lược thiết kế: "Reverse Engineering từ Ngân sách" (Thiết kế ngược từ budget $200 của khách hàng).

| Con số (Metric) | Nằm ở Contract | Giải thích & Biện luận (Justification) |
| :--- | :--- | :--- |
| **0.5 vCPU / 1GB RAM** | Deployment | Thuật toán Thống kê (EWMA) cực kỳ nhẹ, xử lý In-memory các mảng 120 phần tử. 1GB RAM là dư sức cho 4 workers của Uvicorn (~150MB/worker) mà không sợ OOM. |
| **Max 4 Replicas** | Deployment | 4 Tasks Fargate cấu hình trên chạy 24/7 tiêu tốn tối đa ~$60/tháng. Việc giới hạn trần này đảm bảo AI Engine chừa lại >$130/tháng không gian ngân sách cho CDO chạy Pipeline Ingestion & Database, giữ tổng dự án an toàn dưới mốc $200. *(Tham khảo: [AWS Fargate Pricing](https://aws.amazon.com/fargate/pricing/))* |
| **$200 Circuit Breaker (Scale về 0)** | Deployment | Đáp ứng Hard Requirement của đề bài ("Tuyệt đối không vượt $200"). Khi chạm $200, AWS Lambda sẽ ép desired_count = 0. Chấp nhận hệ thống AI sập (Fail-open) để CDO fallback về Rule-based, bảo vệ an toàn túi tiền của Client. |
| **$3.5/tháng (Telemetry Storage)** | Telemetry | Việc chọn Amazon Timestream hoặc Managed Prometheus thay vì raw S3 giúp CDO query chuỗi thời gian (time-series) cực nhanh với chi phí nén siêu rẻ ($3.5/tháng), tuân thủ đúng yêu cầu kiến trúc của đề TF4. *(Tham khảo: [Amazon Timestream Pricing](https://aws.amazon.com/timestream/pricing/))* |

---

## 2. API SLA & Queuing Theory (AI API Contract)

Chiến lược thiết kế: Ứng dụng "Định luật Little" (Little's Law) và SRE Capacity Planning.

### 2.1 Yêu cầu đầu vào (Mentor's KPI)
- **Độ chính xác:** Tỷ lệ bắt lỗi (Catch/Recall) $\ge 80\%$.
- **Báo động giả (False Positive Rate - FPR):** $\le 12\%$.
- **Ngân sách:** $\le \$200$/tháng.

### 2.2 Kết quả Đánh giá Khách quan (Objective Evaluation)
Dữ liệu thử nghiệm (đo thật, nguồn `tf4-evidence/evidence/`): holdout 1 ngày/service trên 3 service tier-1 (payment-gw, fraud-detector, ledger), trượt window 120 phút (step 5 phút) → ~790 window được chấm điểm, gồm 4 scenario inject (gradual drift / sudden spike / slow leak / sudden drop) + 1 FP trap (noisy baseline). A/B đối chứng với Isolation Forest trên cùng tập.

| Thuật toán | Chi phí/Tháng | Catch (Recall) | Báo động giả (FP Rate) | Độ trễ (Latency) | Đạt gate? |
|---|---|---|---|---|---|
| **EWMA + STL** | **~$36** | **0.971** | **7.1%** | **<10ms** | **Đạt** |
| Isolation Forest | ~$150 | 0.638 | 21.4% | ~20ms | Không (FP > 12%) |
| LLM (Bedrock) | ~$10,000 | — | — | ~2000ms | Không (cost phá $200, latency giây) |

> Số EWMA+STL / Isolation Forest trích từ `evidence_algorithm_comparison.json` + `evidence_algorithm_evaluation.json` (re-run: `python tf4-evidence/tf4_evidence.py`). Hàng LLM chỉ minh hoạ lý do loại (cost + latency), không chạy thật.

### 2.3 Vì sao chọn EWMA + STL
EWMA + STL đạt **cả hai gate cùng lúc**: **Recall 0.971** (gate ≥ 0.80) và **FP Rate 7.1%** (gate $\le 12\%$), trong khi Isolation Forest trượt gate FP (21.4%) và recall thấp hơn (0.638).

**Lý do cốt lõi:**
1. **Khử seasonal trước (chìa khoá FP thấp):** STL tách chu kỳ ngày/đêm offline nên EWMA không bắn nhầm vào peak tải bình thường — đó là lý do FP chỉ **7.1%** so với **21.4%** của Isolation Forest (IF coi peak tải ban ngày là bất thường).
2. **Tránh Alert Fatigue:** FP thấp → SRE không bị "Boy who cried wolf", mỗi cảnh báo phát ra đều đáng tin.
3. **Chi phí & latency:** thuật toán $O(N)$ in-memory, ~$36/tháng (Fargate 2-task HA) và <10ms/call, $0 token cost — an toàn dưới ngân sách $200 và SLA p99 < 500ms.

> **Precision 0.793:** đạt mục tiêu stretch (≥ 0.75, xem `01_requirements.md` §3); thấp hơn 0.80 vì window ở **biên** vùng anomaly (EWMA còn cao ngay sau khi sự cố vừa hết) bị tính FP trong cách chấm per-window nghiêm ngặt. Không ảnh hưởng gate chính (FP ≤ 12%, recall ≥ 80%). Trade-off K=4.0 vs K=4.5 xem `05_adrs.md` ADR-006.

| Con số (Metric) | Nằm ở Contract | Giải thích & Biện luận (Justification) |
| :--- | :--- | :--- |
| **P99 Latency < 500ms** | AI API | Thời gian tính toán thuần túy (CPU time) của EWMA cho 120 điểm dữ liệu là < 10ms. Con số 500ms cung cấp vùng đệm (buffer) cực kỳ rộng rãi cho network round-trip và database I/O, đảm bảo SLA 99.5% luôn pass. *(Tham khảo: [Little's Law - Wikipedia](https://en.wikipedia.org/wiki/Little%27s_law))* |
| **Throughput 100 RPS** | AI API | Là giới hạn cứng để bảo vệ Engine. Giả sử 500ms latency, 4 Replicas có thể xử lý thoải mái 100 RPS đồng thời mà không nghẽn cổ chai (bottleneck) Thread Pool. |
| **Limit 600 req/phút/tenant** | AI API | Tránh hiện tượng một Tenant đơn lẻ (ví dụ Payment bị spike) hút cạn tài nguyên của 2 Tenants còn lại (Noisy Neighbor problem). |
| **Scale trigger: 80 RPS/task** | Deployment | Kích hoạt Autoscale ở ngưỡng an toàn 80% công suất (100 RPS max), cho phép thời gian khởi động (Cold start) task mới kịp hoàn thành trước khi hệ thống thực sự chạm 100% capacity. |
| **Backoff 1s -> 2s -> 4s** | AI API | Áp dụng Exponential Backoff khi dính mã lỗi 429 (Rate Limit) để chặn đứng hiện tượng "Thundering Herd" (Đàn trâu giẫm đạp) – khi các service CDO điên cuồng retry làm DDoS ngược lại AI Engine. |

---

## 3. Algorithmic Requirements (Telemetry & API Contract)

Chiến lược thiết kế: Khử nhiễu tín hiệu (Signal Processing Smoothing).

| Con số (Metric) | Nằm ở Contract | Giải thích & Biện luận (Justification) |
| :--- | :--- | :--- |
| **Window Size: ≥ 120 phút** | AI API | Yêu cầu khắt khe nhất của đề bài là Lead time phát hiện trước 15 phút. 120 phút dữ liệu quá khứ (tương đương 120 data points) là kích thước mẫu (Sample size) TỐI THIỂU để đường trung bình động (Moving Average) đủ ổn định, phân biệt được "Nhiễu nhất thời" (Noisy Spike) và "Cạn kiệt từ từ" (Gradual Drift). Ít hơn 120 phút, False Positive rate sẽ vọt quá 12%. *(Tham khảo: [Exponential Moving Average - Wikipedia](https://en.wikipedia.org/wiki/Moving_average#Exponential_moving_average))* |
| **Tần suất: 1 phút/lần** | Telemetry | 1 phút/lần đủ độ chi tiết (granularity) để detect sớm (15 phút) mà vẫn tiết kiệm cực lớn chi phí lưu trữ (Storage cost) so với việc gửi per-second (1 giây/lần). |
| **Lưu trữ 90 ngày (7 hot/83 cold)** | Telemetry | Lưu 90 ngày phục vụ việc Manual Retrain Baseline (theo chu kỳ tuần). 7 ngày đầu để ở Hot Tier cho API query nhanh, 83 ngày còn lại tống vào Cold Tier (Glacier) để tiết kiệm triệt để chi phí FinOps. |

---

## 4. Error Budgets & Resiliency (Deployment Contract)

Chiến lược thiết kế: Quản trị Rủi ro và Ngân sách lỗi (SRE Error Budgets Allocation).

| Con số (Metric) | Nằm ở Contract | Giải thích & Biện luận (Justification) |
| :--- | :--- | :--- |
| **Abort Canary nếu Error > 1%** | Deployment | SLA hệ thống cam kết Availability 99.5% (tức Error Budget = 0.5%). Nếu bản deploy mới ném ra > 1% lỗi, nó đang thâm hụt gấp đôi giới hạn cho phép. Rollback ngay lập tức ở mốc 1% là điểm cắt lỗ toán học. *(Tham khảo: [Google SRE Error Budget Policy](https://sre.google/workbook/error-budget-policy/))* |
| **Abort Canary nếu P99 > 800ms** | Deployment | SLA là 500ms. Mốc 800ms (vượt 60%) cho thấy bản deploy mới chứa thuật toán quá nặng (hoặc memory leak/thread lock), phải rollback trước khi gây timeout dây chuyền cho CDO platform. |
| **Scale-up 60s / Scale-down 300s** | Deployment | Áp dụng pattern kinh điển "Fast scale-up, Slow scale-down". Tăng task ngay lập tức (60s) để cứu traffic, nhưng phải đợi 5 phút (300s) mới được thu hồi task nhằm tránh hiện tượng "Thrashing" (Hệ thống liên tục đập đi xây lại khi traffic dao động nhẹ). *(Tham khảo: [AWS Auto Scaling Cooldowns](https://docs.aws.amazon.com/autoscaling/ec2/userguide/Cooldown.html))* |
| **Health Check: 2 Pass / 3 Fail** | Deployment | Bắt buộc 3 lần lỗi liên tiếp (90s) mới mark Unhealthy để bỏ qua các lỗi mạng (network jitter) thoáng qua. Cần 2 lần pass (60s) liên tiếp để chứng minh service đã thực sự ổn định hoàn toàn trước khi mở traffic trở lại. |

---
*Tài liệu này là Evidence được sinh ra dựa trên đối chiếu chéo giữa Requirements, Design constraints và Mathematical Modeling của Task Force 4.*

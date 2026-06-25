# Requirements - Foresight Lens

<!-- Doc owner: AIO-03 Lead
     Status: Final (W11 T6 Pack #1)
     Word target: 800-1500 từ
     BA methodology: dùng 5W2H làm khung khi interview Client T2 W11 -->

## 1. Khách hàng nói

> "Hệ thống của chúng tôi thường xuyên gặp tình trạng cạn kiệt tài nguyên (Capacity Exhaustion) một cách đột ngột. Khi monitor báo đỏ thì hệ thống đã sập rồi. Chúng tôi cần một giải pháp có khả năng dự đoán sớm sự cố trước khi nó xảy ra để SRE kịp thời can thiệp. Tuy nhiên, chúng tôi không muốn hệ thống tự động can thiệp (auto-remediation) vì sợ rủi ro, và ngân sách duy trì hàng tháng phải cực kỳ tối ưu, không được vượt quá $200."

### 1.1 Vấn đề cốt lõi (Pain points)
- Hệ thống bị sập do không dự báo được Resource Exhaustion (Memory leak dẫn đến OOM, hoặc CPU Spike).
- Công cụ monitor hiện tại chỉ mang tính chất phản ứng (Reactive), chỉ báo động khi sự cố ĐÃ xảy ra (vd: CPU đạt 99%).
- Chi phí bảo trì cho các công cụ AIOps trên thị trường quá đắt đỏ và cồng kềnh, không phù hợp với quy mô hiện tại.
- Sự thiếu tin tưởng vào khả năng "tự động hành động" (Auto-remediation) của AI do sợ hệ thống tự tắt nhầm các server đang chạy tốt.

### 1.2 Ràng buộc bàn giao dự án (Capstone Phased Delivery Constraints)
> **Ràng buộc đặc thù cho Phase 2 (Tuần 11 & 12)**:
> Do tính chất làm việc song song (Parallel execution) giữa team AI và team CDO (Cloud/DevOps), việc tích hợp phải được chia làm 2 giai đoạn:
> - **W11 (Mock Integration)**: Team AI **BẮT BUỘC** phải bàn giao một Endpoint "Skeleton" (giàn giáo) với Dummy Logic trả về JSON tĩnh đúng Schema vào ngày T5 W11. Trong giai đoạn này, Authentication (IAM SigV4) được nới lỏng (Optional) để CDO dễ dàng test luồng.
> - **W12 (Final Build)**: Team AI sẽ thay thế Skeleton bằng thuật toán AI/Thống kê thực tế. Lúc này, mọi quy định về IAM Auth, Validation, và Logic đều được siết chặt. Hợp đồng API (API Contract) giữ nguyên xuyên suốt để CDO không phải sửa code.

## 2. Outcomes mong muốn

Dựa trên pain points của khách hàng, dự án Foresight Lens hướng tới 4 mục tiêu chính:

- **Outcome 1 (Core)**: Dự đoán sớm sự cố cạn kiệt tài nguyên (Memory/CPU, Connection Pool) với độ trễ (Lead Time) tối thiểu 15 phút trước khi hệ thống thực sự vi phạm SLO (Service Level Objective). Việc dự báo sớm giúp đội SRE có đủ thời gian để mở rộng hạ tầng (Scale-up) hoặc tái khởi động dịch vụ (Rolling restart).
- **Outcome 2 (Security & Isolation)**: Đảm bảo phân lập dữ liệu rõ ràng (Multi-tenant) cho ít nhất 3 dịch vụ Tier-1 cốt lõi của công ty (Payment Gateway, Fraud Detection, Ledger). Không có bất kỳ dữ liệu nào của tenant này bị rò rỉ sang tenant khác trong quá trình phân tích.
- **Outcome 3 (FinOps)**: Tối ưu hóa chi phí vận hành ở mức thấp nhất có thể. Không sử dụng các mô hình ngôn ngữ lớn (LLM) vì phí gọi API (token cost) sẽ nhanh chóng phá vỡ ngân sách $200/tháng. Ưu tiên các giải pháp tính toán nội bộ (In-house statistical modeling).
- **Outcome 4 (Actionable Insights)**: Đóng vai trò là một "Cố vấn" (Predict + Recommend), cung cấp cảnh báo kèm hành động đề xuất (Action Verb, Target, Confidence, Evidence Link) qua API. Khách hàng muốn quyền sinh sát (quyết định scale hay không) hoàn toàn nằm trong tay hệ thống logic của CDO.

## 3. Success criteria (measurable)

Việc đánh giá sự thành công của dự án sẽ dựa trên các con số định lượng cụ thể:

| Metric | Target | How to measure | Rationale |
|---|---|---|---|
| **Lead Time** | ≥ 15 phút trước SLO breach | So sánh thời điểm AI phát ra Alert đầu tiên với thời điểm hệ thống OOM / Throttling trong môi trường test. | SRE cần ít nhất 5 phút để đọc alert, 5 phút để approve, và 5 phút để container mới spin up. |
| **Recall (Catch Rate)** | ≥ 80% | Tỉ lệ True Positive / (True Positive + False Negative) đo trên 4 test scenarios. | Đảm bảo hệ thống bắt được ít nhất 80% các trường hợp drift/exhaustion trước khi xảy ra. |
| **False Positive Rate (FPR)** | ≤ 12% | Tỉ lệ báo động giả (False Positive) trên tổng số dự đoán. | Hạn chế Alert Fatigue (mệt mỏi vì cảnh báo giả) cho đội ngũ trực ban (On-call engineers). |
| **Operating Cost** | < $200/tháng | Đo lường bằng AWS Cost Explorer (chỉ tính chi phí cho AI Engine API). | Ràng buộc tài chính khắt khe từ ban Giám đốc. Cần giải pháp Lean & Mean. |
| **Throughput** | 100 Requests/sec | Chạy Load test (k6/Locust) vào endpoint `/v1/predict`. | AI Engine phải chịu tải đủ tốt để không trở thành điểm nghẽn (bottleneck) của CDO. |

## 4. Constraints

Các ràng buộc hệ thống buộc nhóm AI phải đưa ra các quyết định kiến trúc sáng tạo:

- **Budget constraint**: Tuyệt đối không vượt quá $200/tháng cho toàn bộ giải pháp AI. Điều này cấm cửa việc gọi API tới OpenAI GPT-4 hay Anthropic Claude cho mỗi dòng log.
- **Timeline constraint**: Dự án triển khai trong vỏn vẹn 2 tuần (W11-W12), code freeze vào 18h tối Thứ Tư (W12). Không có thời gian để train các mô hình Deep Learning phức tạp (LSTM, Autoencoder).
- **Tooling constraint**: Chỉ sử dụng AWS Ecosystem. Ngôn ngữ phát triển là Python (sử dụng FastAPI cho tốc độ và Pydantic cho validation).
- **Resiliency constraint (Fail-open)**: AI Engine không được phép làm chết hệ thống chính. Nếu AI Engine sập (HTTP 5xx), CDO phải tự fallback về Rule-based alerting cũ.

## 5. Out of scope

Để đảm bảo dự án đi đúng hướng và không bị lan man (scope creep), các hạng mục sau chính thức bị loại bỏ khỏi W11-W12:

- ❌ **Tự động phục hồi (Auto-remediation)**: Engine chỉ cung cấp Recommendation (gợi ý `SCALE_UP` hoặc `INVESTIGATE`). Việc trigger API thay đổi hạ tầng là trách nhiệm của team CDO.
- ❌ **LLM-based Root Cause Analysis (RCA)**: Không sử dụng GenAI để đọc và tóm tắt log ngôn ngữ tự nhiên. Phân tích nguyên nhân gốc rễ (RCA) bằng LLM là quá đắt đỏ và tiềm ẩn rủi ro Hallucination (AI bịa ra nguyên nhân ảo).
- ❌ **Cross-region failover (DR)**: Thiết kế chỉ dừng ở mức Single-region (ap-southeast-1). Disaster Recovery (DR) sang region khác chỉ nằm trên tài liệu (Design-only).
- ❌ **Custom Model Training Pipeline**: Không xây dựng hệ thống CI/CD để tự động retrain mô hình ML. Việc update baseline sẽ làm thủ công bằng script.

## 6. Non-functional requirements (NFRs)

- **Performance (SLO platform)**: Thời gian phản hồi của AI API (p99 latency) phải < 500ms. Độ sẵn sàng (Availability) ≥ 99.5%.
- **Multi-tenant scale**: Thiết kế phải hỗ trợ độc lập dữ liệu cho ít nhất 3 tenant/service (Payment, Fraud, Ledger) thông qua chung một endpoint.
- **Security & Data Privacy**: 
  - Cách ly context 100% bằng header `X-Tenant-Id`.
  - Mọi request dẫn tới quyết định cảnh báo đều phải được Audit Log đầy đủ (≥ 6 trường) để phục vụ tra cứu sau này.
  - Tuyệt đối không lưu raw PII (Personally Identifiable Information). Toàn bộ payload đầu vào phải được Hashing (SHA-256) trước khi lưu log.
- **FinOps Target**: Tiêu tốn < $5/tenant/month cho toàn bộ tính toán nội bộ.

## 7. Open questions & Resolutions

- [x] **Q1: Có được phép lưu trữ raw data của tín hiệu đo lường vào log không?** 
  - *Resolved: Không. Bắt buộc dùng Hashing (SHA-256) cho input data để tránh lộ dữ liệu nhạy cảm qua log.*
- [x] **Q2: Nếu tín hiệu telemetry gửi lên bị đứt quãng (do rớt mạng) thì xử lý thế nào?** 
  - *Resolved: AI Engine sẽ yêu cầu CDO phải tiền xử lý (Imputation) bằng phương pháp Forward-fill hoặc Zero-fill. Nếu phát hiện mảng dữ liệu bị thủng, AI Engine sẽ văng lỗi `HTTP 400 Bad Request` ngay lập tức.*
- [x] **Q3: Bằng chứng về độ tin cậy của thuật toán được cung cấp bằng cách nào?**
  - *Resolved: Sẽ sử dụng Brier Score để đo lường mức độ hiệu chuẩn (Calibration) của Model Confidence, lưu trữ trực tiếp vào `evidence_algorithm_evaluation.json`.*


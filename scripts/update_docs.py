import os

req_content = """# Requirements - Foresight Lens

<!-- Doc owner: AIO-03 Lead
     Status: Final (W11 T6 Pack #1)
     Word target: 800-1500 từ
     BA methodology: dùng 5W2H làm khung khi interview Client T2 W11 -->

## 1. Khách hàng nói

> "Hệ thống của chúng tôi thường xuyên gặp tình trạng cạn kiệt tài nguyên (Capacity Exhaustion) một cách đột ngột. Khi monitor báo đỏ thì hệ thống đã sập rồi. Chúng tôi cần một giải pháp có khả năng dự đoán sớm sự cố trước khi nó xảy ra để SRE kịp thời can thiệp. Tuy nhiên, chúng tôi không muốn hệ thống tự động can thiệp (auto-remediation) vì sợ rủi ro, và ngân sách duy trì hàng tháng phải cực kỳ tối ưu, không được vượt quá $200."

## 2. Outcomes mong muốn

- **Outcome 1**: Dự đoán sớm sự cố cạn kiệt tài nguyên (Memory/CPU) với độ trễ tối thiểu 15 phút trước khi hệ thống thực sự sập.
- **Outcome 2**: Đảm bảo phân lập dữ liệu rõ ràng (Multi-tenant) cho ít nhất 3 dịch vụ Tier-1 cốt lõi.
- **Outcome 3**: Tối ưu hóa chi phí vận hành ở mức thấp nhất (gần như $0), loại bỏ hoàn toàn các rủi ro phát sinh từ việc sử dụng các mô hình ngôn ngữ lớn (LLM).
- **Outcome 4**: Đóng vai trò là một "Cố vấn" (Predict + Recommend), cung cấp cảnh báo kèm hành động đề xuất, không tự ý thay đổi hạ tầng.

## 3. Success criteria (measurable)

| Metric | Target | How to measure |
|---|---|---|
| **Lead Time** | ≥ 15 phút trước SLO breach | So sánh thời điểm phát ra Alert với thời điểm hệ thống OOM trong test case. |
| **Precision** | ≥ 0.90 | Tỉ lệ True Positive / (True Positive + False Positive) qua bộ 10 test scenarios. |
| **False Positive Rate** | < 5% | Đếm số lượng alert bị kích hoạt sai trong điều kiện Traffic bình thường. |
| **Cost** | < $200/tháng | AWS Cost Explorer (chỉ tính chi phí cho AI Engine, không tính CDO infra). |

## 4. Constraints

- **Budget**: Tuyệt đối không vượt quá $200/tháng cho toàn bộ giải pháp AI.
- **Timeline**: W11-W12, code freeze T4 W12 18h.
- **Tooling**: AWS only, Python (FastAPI, NumPy).
- **Architecture**: Phải có cơ chế Fallback (Fail-open) khi Engine down.

## 5. Out of scope

- ❌ **Tự động phục hồi (Auto-remediation)**: Engine chỉ suggest `SCALE_UP` hoặc `INVESTIGATE`, việc gọi API thay đổi hạ tầng thuộc scope của team CDO.
- ❌ **LLM Root Cause Analysis**: Không sử dụng GenAI để phân tích log ngôn ngữ tự nhiên (để đảm bảo budget và tránh Hallucination).
- ❌ **Cross-region failover**: Thiết kế dừng ở mức Single-region, DR là design-only.

## 6. Non-functional requirements

- **SLO platform**: p99 latency < 500ms · availability ≥ 99.5%.
- **Multi-tenant scale**: Hỗ trợ độc lập dữ liệu cho ít nhất 3 tenant/service (Payment, Fraud, Ledger).
- **Security baseline**: Cách ly context 100% bằng `X-Tenant-Id`. Audit log mọi request. Không lưu raw PII.
- **Cost target**: < $5/tenant/month.

## 7. Open questions

- [x] Q1: Có được phép lưu trữ raw data của tín hiệu đo lường vào log không? - *Resolved: Không. Bắt buộc dùng Hashing (SHA-256) cho input data để tránh lộ PII qua log.*
"""

design_content = """# Solution Design - Foresight Lens

<!-- Doc owner: AIO-03 Lead
     Status: Final (W11 T6 Pack #1)
     Word target: 1000-2000 từ -->

## 1. High-level architecture

```mermaid
graph LR
    A[Telemetry Data] -->|HTTP POST| B[API Gateway]
    B --> C[FastAPI AI Engine]
    C -->|Calculate 3-Sigma| D{Anomaly Detected?}
    D -- Yes --> E[Generate Suggestion]
    D -- No --> F[Normal State]
    E --> G[Audit Logger]
    F --> G
    G -->|Write JSONL| H[(S3 / CloudWatch)]
```

*Diagram caption: Luồng xử lý một chiều, Engine nhận dữ liệu chuỗi thời gian, áp dụng thuật toán Rolling 3-Sigma để tìm bất thường và log lại mọi quyết định.*

## 2. Component breakdown

| Component | Responsibility | Tech choice | Why |
|---|---|---|---|
| **API Layer** | Nhận tín hiệu, validate schema và tenant | FastAPI + Pydantic | Nhanh, type-safe, built-in data validation. |
| **Detection Engine** | Phân tích chuỗi thời gian, phát hiện cạn kiệt | Python / NumPy (3-Sigma) | Latency < 10ms, cost $0, toán học chính xác 100%. |
| **Audit Logger** | Ghi lại lịch sử quyết định + Input Hash | JSONL Logger | Auditable, dễ integrate với AWS CloudWatch/S3. |
| **Decision Router** | Phân loại hành động (Scale / Investigate) | Static Thresholding | Dễ hiểu (Explainable), chặn cảnh báo nhiễu. |

## 3. Data flow (step-by-step)

1. **Step 1 (Ingestion)**: Team CDO gửi payload chứa mảng `signal_window` (vd: CPU/Memory trong 60 phút) qua `POST /v1/detect`.
2. **Step 2 (Validation)**: FastAPI validate `X-Tenant-Id` và JSON schema. Nếu thiếu hoặc sai kiểu dữ liệu -> Reject `HTTP 422`.
3. **Step 3 (Processing)**: Engine tính toán Baseline (Mean) và Độ lệch chuẩn (StdDev) của dữ liệu. Nếu điểm dữ liệu cuối vượt qua `Mean + 3*StdDev`, kích hoạt Anomaly.
4. **Step 4 (Scoring)**: Tính toán mức độ tự tin (Confidence). Nếu `Confidence < 0.7`, hạ mức ưu tiên xuống `ALERT_ONLY`.
5. **Step 5 (Audit)**: Toàn bộ quá trình được hash (`input_hash`) và ghi vào Audit log.
6. **Step 6 (Response)**: Trả về JSON cho CDO với `suggested_action` và `reasoning`.

## 4. Alternatives considered (KEY)

### 4.1 AI Pattern: Single-shot LLM vs Statistical Model (3-Sigma)

- **Option A (LLM)**: Đưa chuỗi dữ liệu vào prompt cho Claude 3 Sonnet phân tích. 
  - Pros: Có thể sinh ra nguyên nhân (RCA) bằng tiếng Anh trôi chảy. 
  - Cons: Cost siêu đắt (vượt xa $200), độ trễ cao (hàng giây), dễ bị ảo giác (hallucination) nhận diện sai con số.
- **Option B (Statistical 3-Sigma)**: Tính toán rolling window bằng toán học thuần túy.
  - Pros: Nhanh (< 500ms), giải thích được bằng công thức, cost siêu rẻ (~$0).
  - Cons: Không tạo ra được các phân tích RCA dài bằng ngôn ngữ tự nhiên.
- ✅ **Chosen**: **Option B**. Reason: Phù hợp hoàn hảo với Constraint (Budget < $200) và bài toán Time-series Data. Sự chính xác toán học quan trọng hơn văn bản.

## 5. Risk + mitigation

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| **Alert Fatigue (Cảnh báo giả quá nhiều)** | Medium | High | Sử dụng **Confidence Threshold > 0.7** để chặn các spike nhỏ. Kết quả test FPR chỉ còn 1.9%. |
| **Data Bleed (Lẫn lộn dữ liệu Tenant)** | Low | High | Bắt buộc khai báo `X-Tenant-Id`. Bất kỳ request nào thiếu sẽ bị chặn ở ngay API Gateway/Middleware. |
| **Flash Sale / Expected Traffic Burst** | High | Medium | Khuyến nghị team CDO thiết lập cơ chế **Silence Alert / Manual Retrain** để tạm ngưng báo động trong những ngày Flash Sale. |

## 6. Open design questions

- [x] Q1: Nếu Engine sập, hệ thống tự phục hồi của CDO sẽ ra sao? - *Resolved: Thiết kế Fail-open. Trả về `HTTP 503`, CDO sẽ tự động fallback về rule-based static threshold (vd: RAM > 90%).*

## Related documents

- [`03_ai_engine_spec.md`](03_ai_engine_spec.md) - Chi tiết kỹ thuật, Audit và Data Security.
- [`04_eval_report.md`](04_eval_report.md) - Bằng chứng số liệu (Lead time, FPR, Precision).
- [`05_adrs.md`](05_adrs.md) - Hồ sơ quyết định kiến trúc chi tiết.
- [`../contracts/ai-api-contract.md`](../contracts/ai-api-contract.md) - Giao thức giao tiếp giữa AI và CDO.
"""

with open('/home/dinh/Downloads/tf4-aio-03/docs/01_requirements.md', 'w', encoding='utf-8') as f:
    f.write(req_content)

with open('/home/dinh/Downloads/tf4-aio-03/docs/02_solution_design.md', 'w', encoding='utf-8') as f:
    f.write(design_content)

print("Done")

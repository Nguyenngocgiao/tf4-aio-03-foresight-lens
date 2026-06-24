# Solution Design - Foresight Lens

<!-- Doc owner: AIO-03 Lead
     Status: Final (W11 T6 Pack #1)
     Word target: 1000-2000 từ -->

## 1. High-level architecture

![Solution Design](../diagrams/02_solution_design.png)

*(Sơ đồ có thể chỉnh sửa: [02_solution_design.drawio](../diagrams/02_solution_design.drawio))*

*Diagram caption: Luồng xử lý một chiều, Engine nhận dữ liệu chuỗi thời gian, áp dụng thuật toán Rolling EWMA & STL Decomposition để tìm bất thường và log lại mọi quyết định.*

## 2. Component breakdown

| Component | Responsibility | Tech choice | Why |
|---|---|---|---|
| **API Layer** | Nhận tín hiệu, validate schema và tenant | FastAPI + Pydantic | Nhanh, type-safe, built-in data validation. |
| **Detection Engine** | Phân tích chuỗi thời gian, phát hiện cạn kiệt | Python / NumPy (EWMA & STL Decomposition) | Latency < 10ms, cost $0, toán học chính xác 100%. |
| **Audit Logger** | Ghi lại lịch sử quyết định + Input Hash | JSONL Logger | Auditable, dễ integrate với AWS CloudWatch/S3. |
| **Decision Router** | Phân loại hành động (Scale / Investigate) | Static Thresholding | Dễ hiểu (Explainable), chặn cảnh báo nhiễu. |

## 3. Data flow (step-by-step)

1. **Step 1 (Ingestion)**: Team CDO gửi payload chứa mảng `signal_window` (vd: CPU/Memory trong 60 phút) qua `POST /v1/detect`.
2. **Step 2 (Validation)**: FastAPI validate `X-Tenant-Id` và JSON schema. Nếu thiếu hoặc sai kiểu dữ liệu -> Reject `HTTP 422`.
3. **Step 3 (Processing)**: Engine tính toán Baseline (Mean) và Độ lệch chuẩn (StdDev) của dữ liệu. Nếu điểm dữ liệu cuối vượt qua `EWMA Drift + STL Residual Threshold`, kích hoạt Anomaly.
4. **Step 4 (Scoring)**: Tính toán mức độ tự tin (Confidence). Nếu `Confidence < 0.7`, hạ mức ưu tiên xuống `ALERT_ONLY`.
5. **Step 5 (Audit)**: Toàn bộ quá trình được hash (`input_hash`) và ghi vào Audit log.
6. **Step 6 (Response)**: Trả về JSON cho CDO với `suggested_action` và `reasoning`.

## 4. Alternatives considered (KEY)

### 4.1 AI Pattern: Single-shot LLM vs Statistical Model (EWMA & STL Decomposition)

- **Option A (LLM)**: Đưa chuỗi dữ liệu vào prompt cho Claude 3 Sonnet phân tích. 
  - Pros: Có thể sinh ra nguyên nhân (RCA) bằng tiếng Anh trôi chảy. 
  - Cons: Cost siêu đắt (vượt xa $200), độ trễ cao (hàng giây), dễ bị ảo giác (hallucination) nhận diện sai con số.
- **Option B (Statistical EWMA & STL Decomposition)**: Tính toán rolling window bằng toán học thuần túy.
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

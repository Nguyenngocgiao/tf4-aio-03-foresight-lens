# AI Engine Spec - Foresight Lens

<!-- Doc owner: AIO-03 Lead
 Status: Final (W11 T6 Pack #1)
 Word target: 2500-4000 từ (Heavy tier)
 Reference: TCB DAB Framework - AI Model Governance + AI Security (adapted for capstone) -->

> ** Capstone scope guide** - 9 sections không phải tất cả "must-deploy", một số "design-only":
>
> **Pack #1 / W11 (Mock Integration Phase)**: AI Team deploy 1 Endpoint Skeleton.
> - Yêu cầu: Dummy logic (hardcoded JSON), IAM SigV4 optional để CDO dễ test.
> - Minimum Docs: Sections 1, 2, 3, 4 (skeleton) + 5.1-5.3 + 6.1, 6.2.1, 6.2.2 (skeleton) + 7 (skeleton) + 8 (forecast) + 9
>
> **Pack #2 / W12 (Final Build Phase)**: AI Team bàn giao Artifact + Thuật toán thật.
> - Yêu cầu: Real engine logic, IAM SigV4 enforced. Schema API không đổi.
> - Full Docs: TẤT CẢ sections refined với:
> - 5.5 Model NFR Control Matrix có MG-01..MG-08 evidence
> - 6 AI Security với Bedrock Guardrails configured (NOT just spec)
> - 7 Eval với real measured numbers
> - 8 Cost với actual measured
>
> **Design-only OK cho capstone** (note rõ trong doc nếu áp dụng): 6.6 LLM for AI Agents (nếu không dùng agentic) · 6.4 Training Model Security (capstone dùng foundation model)

## 1. Model architecture (Kiến trúc Mô hình)

Kiến trúc mô hình của Foresight Lens được thiết kế đặc trị cho bài toán phân tích dữ liệu chuỗi thời gian (Time-series data) của cơ sở hạ tầng (CPU, RAM, Connections).

- **Pattern chọn (Chosen Pattern)**: **Statistical Analysis Engine (EWMA & STL Decomposition)**. Thay vì sử dụng các mô hình Large Language Models (LLM) đắt đỏ, hệ thống sử dụng sức mạnh của Thống kê phân rã truyền thống.
- **Lý do lựa chọn (Rationale)**:
 - **STL (Seasonal and Trend decomposition using Loess)** giúp tách biệt hoàn toàn tín hiệu thô thành 3 mảng: Trend (Xu hướng), Seasonality (Tính chu kỳ ngày đêm), và Residual (Nhiễu cục bộ). Bằng cách khử seasonal trước (train offline ≥2 ngày/service), hệ thống đạt False Positive Rate đo thật **7.1%** (gate ≤12%).
 - **EWMA (Exponentially Weighted Moving Average)** cực kỳ nhạy bén trong việc bắt các dải trượt chậm (Slow drift) tiêu biểu của lỗi rò rỉ bộ nhớ (Memory leak) hoặc cạn kiệt Connection Pool.
 - Phối hợp hai phương pháp này mang lại khả năng dự báo cạn kiệt dung lượng (Capacity Exhaustion) với độ trễ tối thiểu (Lead Time) lớn hơn 15 phút, vượt tiêu chí của khách hàng, với chi phí và độ trễ tính toán cực thấp.
- **Alternatives rejected (Lựa chọn bị từ chối)**: LLM (Claude, GPT) hoặc Agentic Workflows. Bị reject vì latency cao (đôi khi mất hàng chục giây), tốn kém (vi phạm constraint Cost < $200), tiềm ẩn ảo giác (Hallucination), và hoàn toàn không phù hợp với bản chất dữ liệu chuỗi thời gian vốn cần tính toán số học chính xác thay vì sinh text ngôn ngữ tự nhiên. Isolation Forest cũng bị reject do nặng nề trong khâu dựng cây (dành cho dữ liệu đa biến multivariate, không cần thiết cho dự án đơn biến này).

## 2. Model selection (Lựa chọn Phiên bản Mô hình)

Các thông số vận hành kỹ thuật chi tiết của Mô hình AI:

| Field | Value | Rationale |
|---|---|---|
| **Provider** | Python / NumPy (In-house) | Không phụ thuộc vào 3rd-party API. Chạy offline an toàn, bảo mật dữ liệu. |
| **Model ID** | `tf4-ewma-stl-v1` | Đánh versioning rõ ràng để phục vụ roll-back nếu bản update Baseline bị lỗi. |
| **Region** | Single-region (us-east-1) | Engine region-agnostic (stateless, no PII, `AWS_REGION` env var) → co-locate cùng region với CDO platform; chọn us-east-1 vì chi phí AWS thấp nhất + catalog service rộng nhất. |
| **Context window** | ≥ 120 data points (120 phút) per request + per-service baseline | Window 2h cho EWMA tại inference; chu kỳ ngày học sẵn trong baseline STL (offline). |
| **Cost/1k input tokens** | $0 (Local execution) | Ưu thế tuyệt đối về FinOps. |
| **Cost/1k output tokens** | $0 (Local execution) | Không tốn phí sinh từ vựng. |
| **Estimated per-call latency** | < 5 ms (Milliseconds) | Cực nhanh nhờ NumPy vectorization. |

## 3. Multi-tenant routing (Định tuyến Đa khách hàng)

Một trong những yêu cầu cốt lõi là đảm bảo AI Engine có thể phục vụ cùng lúc nhiều nhóm dịch vụ (Tenant: Payment, Fraud, Ledger) mà không gây rò rỉ hoặc trộn lẫn dữ liệu.

<!-- Làm sao đảm bảo tenant A's data không leak sang tenant B? -->

- **Tenant identification (Định danh)**: Dữ liệu được xác thực bắt buộc qua HTTP Header `X-Tenant-Id`. Nếu request không có header này, request bị reject ngay tại Middleware (FastAPI layer) với lỗi `HTTP 401`. Nếu `tenant_id` trong datapoint không khớp header → `HTTP 400` (xem `ai-api-contract.md` §Error codes).
- **Context isolation (Cách ly bối cảnh)**: AI Engine áp dụng cơ chế xử lý phi trạng thái tuyệt đối (**Stateless Per-Request Scoping**). Thuật toán EWMA & STL được khởi tạo, tính toán, và bị hủy bỏ khỏi bộ nhớ RAM (Garbage Collected) ngay sau mỗi HTTP Request. Không có bất kỳ biến toàn cục (Global variable) nào lưu trữ trạng thái của Tenant A vượt quá vòng đời request, triệt tiêu 100% rủi ro Data Bleed.
- **State storage (Lưu trữ trạng thái)**: Baseline của từng Tenant (nếu cần tuning riêng) được định cấu hình bằng biến môi trường (Environment Variables) hoặc lưu trữ độc lập tại phân vùng DynamoDB (`partition_key = tenant_id`).
- **Audit log (Nhật ký thanh tra)**: Mọi quyết định AI sinh ra (AI Decision Call) đều ghi nhận một Record riêng biệt với trường `tenant_id` đóng vai trò là Primary Key, phục vụ tra cứu cách ly.

## 4. Prompt engineering / RAG strategy

*N/A — Hệ thống sử dụng Thuật toán Thống kê (Statistical Model) thay vì Mạng Neural LLM. Do không phải là GenAI, hệ thống hoàn toàn không có Prompt (câu lệnh mồi), không có Context Window Tokens hay RAG Pipeline (Truy xuất tăng cường sinh). Việc này loại trừ hoàn toàn các kỹ thuật Prompt Injection.*

## 5. AI Model Governance (Quản trị Mô hình AI)

### 5.1 Governance Objectives (Mục tiêu Quản trị)

<!-- Tại sao cần governance? Risk model + AI ethics + business assurance -->

Việc đưa AI vào chuỗi quyết định vận hành IT (AIOps) đòi hỏi khung kiểm soát chặt chẽ để đảm bảo:
- Đảm bảo AI decision luôn **explainable + auditable + reversible** (Giải thích được + Thanh tra được + Có thể Đảo ngược).
- Ngăn chặn triệt để rủi ro **autonomous unsafe action** (Hành động tự động thiếu an toàn) - mọi đề xuất phải nằm trong vùng an toàn (Safety boundary).
- **Compliance (Tuân thủ)**: model behavior (Hành vi mô hình) không vi phạm chính sách Data Privacy của tổ chức.
- **Reproducibility (Tính tái lập)**: Cùng một file dữ liệu log đầu vào (same input) bắt buộc phải cho ra cùng một kết quả cảnh báo (same output). Tính toán Deterministic là yêu cầu tối thượng.

### 5.2 Scope (Capstone Year-1 equivalent)

- **In-scope (Nằm trong phạm vi Capstone)**:
 - Statistical Model tự phát triển với Version Control minh bạch (`tf4-ewma-stl-v1`).
 - Assist-only decision (Cơ chế cố vấn tĩnh) - Human-in-the-loop: Chỉ cung cấp Recommendation, con người (SRE) hoặc Rule Engine của CDO mới là nơi đưa ra quyết định hành động thay đổi hạ tầng.
 - Multi-tenant với per-tenant context isolation mức phần mềm (Software-level).
 - Eval methodology: holdout sliding-window (4 scenario + FP trap) trên 3 service + drift log.
- **Out-of-scope (Defer to post-capstone - Ngoài phạm vi)**:
 - Multi-provider failover (Đổi nhà cung cấp ML Model khi sập).
 - Autonomous action without safety gate (AI tự động nâng cấp server mà không cần ai duyệt).
 - Cross-region model serving (Phân bổ mô hình xuyên lục địa).

### 5.3 Key Governance Principles (Các nguyên tắc chủ chốt)

| Principle | Rationale (Lý do) | Enforcement (Cơ chế thực thi) |
|---|---|---|
| **Explainability (Khả năng giải thích)** | Mọi quyết định phải được chứng minh bằng con số, không trả lời mập mờ. | Output schema trả về bao gồm `reasoning` field giải thích rõ ngưỡng Baseline bị vi phạm. |
| **Auditability (Khả năng thanh tra)** | Cần truy vết ngược dữ liệu để đổ lỗi (Blameless RCA) khi AI báo sai. | Bắt buộc hệ thống phải ghi Audit log thành công. Log ghi lại `input_hash` thay vì Payload PII thô. |
| **Confidence-gated action (Kiểm soát bởi độ tự tin)** | Low-confidence → Bắt buộc hạ cấp xuống INVESTIGATE, cấm đưa lệnh SCALE_UP. | Code hardcode mức Threshold: `if confidence < 0.7`. |
| **Reversibility (Tính đảo ngược)** | SRE có thể bác bỏ quyết định của AI. | Thiết kế ở dạng API Endpoint tĩnh, không tự động can thiệp vào máy chủ AWS, SRE có quyền Disable Webhook. |
| **Tenant isolation (Cách ly KH)** | Ngăn chặn Cross-tenant context bleed (lộ dữ liệu chéo). | Per-request scoping (Xử lý phi trạng thái trên từng request) + Audit assertion. |
| **Cost guard (Rào chắn chi phí)** | Spend không được vỡ kế hoạch $200. | Sử dụng mô hình In-house NumPy cost $0. Limit mức AWS Fargate container. |
| **Drift detection (Phát hiện trượt)** | Model behavior drift phải được phát hiện sớm để tránh báo giả trong tương lai. | Quản trị thủ công: Dành ra lịch Weekly eval re-run trên tập baseline mới (Post-capstone). |

### 5.4 Enforcement Mechanisms (Architectural Layer - Cơ chế Kiến trúc)

| Mechanism | Implementation | Layer |
|---|---|---|
| Input sanitization | Pydantic Schema Validation (reject ngay `HTTP 422` nếu sai schema hoặc data type). | API Layer |
| Output schema validation | Ép buộc trả về JSON cứng, reject ngầm nếu app code lỗi định dạng. | Post-Processing |
| Confidence threshold | Xử lý logic App-level: `confidence < 0.7` → Action verb = `INVESTIGATE`. | App layer |
| Audit log mandatory | Mã nguồn buộc phải pass qua dòng code ghi Logger S3 trước khi trả `return response`. | App layer |
| Per-tenant isolation | Context isolation thông qua biến `X-Tenant-Id` bóc tách từ HTTP Headers. | App layer |
| Rate limit | FastAPI Middleware: Áp mức trần 600 req/phút/tenant (đúng SLA contract) để chặn Spam/DDoS. | Edge / API Gateway |
| Circuit breaker | CDO-side: Khi AI trả về `HTTP 5xx` liên tục 3 lần → fallback về rules tĩnh. | CDO Layer |
| Eval baseline check | (Chỉ định) Chạy lệnh Script Evaluator để xuất File báo cáo JSON Brier Score hàng tuần. | CI/CD job |

### 5.5 Model NFR Control Matrix (Ma trận Kiểm soát Phi chức năng)

| NFR ID | Category | Requirement | Control | Evidence | Owner |
|---|---|---|---|---|---|
| MG-01 | Governance | Quyết định AI phải giải thích được | Trường `reasoning` ≤ 300 ký tự trả về trong mọi Response | Mã nguồn engine.py | Nhóm AI |
| MG-02 | Governance | Thanh tra toàn diện (Audit complete) | 100% lệnh AI phải lưu Audit | File log tại S3/DynamoDB | Nhóm AI |
| MG-03 | Governance | Confidence gating | Lệnh `SCALE_UP` yêu cầu confidence ≥ 0.7 | Bằng chứng test threshold | Nhóm AI |
| MG-04 | Performance | Độ trễ P99 < 500ms | Ứng dụng thuật toán NumPy cực nhẹ | Chỉ số Latency đo trên Postman | Nhóm AI |
| MG-05 | Cost | Chi phí tổng < $200 | Không gọi LLM external | AWS Cost Explorer estimate | Nhóm AI |
| MG-06 | Reliability | Fallback nếu AI Engine sập | Trả mã 503 HTTP cho CDO tự fallback | Postman 503 Scenario | CDO + AI |
| MG-07 | Compliance | Dữ liệu PII không được lọt vào Log | Hashing thuật toán SHA-256 (`input_hash`) | Audit log mẫu | Nhóm AI |
| MG-08 | Drift | Cảnh báo bị trượt khỏi thực tế | Đánh giá định kỳ độ chính xác (Brier Score) | File `evidence_algorithm_evaluation.json` | Nhóm AI |
| MG-09 | Safety | (N/A) Closed-loop tự thân | Foresight Lens là Assist-only, không tự execute | Kiến trúc Diagram | Nhóm AI |

### 5.6 Closed-loop Safety Pattern (N/A)

<!-- Skip section này nếu engine chỉ ALERT/SUGGEST, không EXECUTE action.
 Self-Heal Engine + auto-containment engines BẮT BUỘC có section này. -->

*Dự án Foresight Lens chỉ đóng vai trò ALERT/SUGGEST (Cố vấn), hoàn toàn không trực tiếp EXECUTE action (Thực thi hạ tầng). Do đó, thiết kế Closed-loop Safety Pattern với Dry-run / Blast-radius / Auto-rollback là KHÔNG CẦN THIẾT và được gạch bỏ để tiết kiệm scope.*

## 6. Statistical Engine Security (Bảo mật Tầng Thống kê)

*Vì hệ thống Foresight Lens sử dụng thuật toán Thống kê truyền thống (NumPy) thay vì Large Language Models (LLMs), toàn bộ các rủi ro kinh điển của lĩnh vực GenAI (Prompt Injection, Jailbreaking, Hallucination, Training Data Poisoning) được **LOẠI TRỪ HOÀN TOÀN** theo nguyên tắc thiết kế (Security-by-design).*

Do đó, các phương án phòng thủ bảo mật của nhóm AI sẽ chuyển dời hoàn toàn trọng tâm sang khu vực **Tầng API** và **Tầng Dữ liệu**:

### 6.1 Security Risks (Overview)

| Risk | Description | Severity | Mitigation Layer |
|---|---|---|---|
| **Data Bleed (Cross-tenant)** | Dữ liệu `tenant_A` vô tình được dùng làm Baseline tính toán báo động cho `tenant_B`. | High | **Code level**: Hệ thống phi trạng thái (Stateless). Context parsing khởi tạo lại toàn bộ và group bắt buộc theo `X-Tenant-Id`. |
| **Denial of Service (DoS/DDoS)**| CDO gửi một request chứa mảng `signal_window` có kích thước 1 triệu phần tử, vắt kiệt RAM & CPU của container. | Medium | **Pydantic**: Cấu hình Max Length cho danh sách input. Giới hạn độ dài mảng dữ liệu đo lường ở mức tối đa 10,000 data points. |
| **Data Poisoning (Bơm nhiễu)** | Attacker giả mạo hệ thống CDO, liên tục gửi dữ liệu rác để làm hỏng Baseline (khiến hệ thống tưởng lượng Traffic ảo là thật). | Medium | **Edge Auth**: Endpoint được bảo vệ bằng cơ chế IAM SigV4 / API Gateway Key. Bác bỏ mọi request không có chữ ký nội bộ. |
| **PII Leakage in Logs** | Lưu lọt IP khách hàng hoặc thông số nhạy cảm khác từ Payload vào ổ cứng Audit Log. | Medium | **Data Hash**: Sử dụng SHA-256 biến đổi toàn bộ Payload Body thành 1 đoạn Hash (`input_hash`) trước khi Dump log. |

### 6.2 Data Input Validation (Kiểm tra Dữ liệu Đầu vào)

Sức mạnh của Python Pydantic được tận dụng triệt để ở lớp khiên chắn API:

| Control | Description |
|---|---|
| Schema validation | Strict Pydantic JSON schema. Nếu thừa field, thiếu field, hệ thống reject lập tức (`HTTP 422 Unprocessable Entity`). Cấm tiệt SQL Injection / XSS lọt vào. |
| Data type checks | Biến `value` bắt buộc là `float` (không được nhận chữ). Biến `ts` (Timestamp) bắt buộc chuẩn `RFC3339`. |
| Context Isolation | Header `X-Tenant-Id` được đánh giá Validation Rule (bắt buộc). Không có header -> `HTTP 401`; `tenant_id` trong datapoint ≠ header -> `HTTP 400`. |

### 6.3 Security Audit Trail (Dấu vết Thanh tra Bảo mật)

Toàn bộ payload nhạy cảm không bao giờ được lưu thô (No Raw Write). Hệ thống sử dụng Hashing (SHA-256) nhằm tạo bằng chứng về tính nguyên vẹn (Integrity) để phục vụ giải trình, nhưng cấm tuyệt đối khả năng đọc ngược lại thông tin PII:

Audit record sử dụng **đúng 6 trường bắt buộc** của contract (`ai-api-contract.md` §Audit Log Schema), khớp 1-1 với code `app/audit.py`:

```json
{
  "audit_id": "f3b9c2a1-7d4e-4b8a-9c2e-1a2b3c4d5e6f",
  "timestamp": "2026-06-25T10:30:00Z",
  "tenant_id": "tnt-payment-core",
  "principal_id": "arn:aws:iam::123456789012:role/cdo-platform",
  "input_hash": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
  "recommendation_snapshot": {"action_verb": "SCALE_UP", "from_to": "Current -> +2 Tasks"}
}
```

> Lưu trữ **Encrypted at Rest** (KMS) với retention 365 ngày. Payload thô KHÔNG bao giờ ghi — chỉ lưu `input_hash` (SHA-256) để verify integrity mà không lộ PII.

## 7. Eval methodology (Phương pháp Lượng giá)

Độ tin cậy của thuật toán `EWMA & STL Decomposition` được chứng minh bằng một hệ quy chiếu đo lường khắt khe, chạy tự động.

- **Test set composition (Tập dữ liệu kiểm thử)**: Holdout 1 ngày/service (3 tier-1 service), 4 scenario inject (gradual drift / sudden spike / slow leak) + 1 FP trap (noisy baseline). Trượt window 120 phút, step 5 → ~790 window scored.
- **Metrics tracked (đo thật, `evidence_algorithm_evaluation.json`)**:
 - **Brier Score (Calibration)**: đo độ hiệu chuẩn của confidence. Đo được **0.049** (< 0.1, tốt).
 - **Precision**: TP/(TP+FP) = **0.793**.
 - **Recall (catch rate)**: TP/(TP+FN) = **0.971**.
 - **False Positive Rate (FPR)**: **7.1%** (gate ≤ 12%).
 - **Lead time (median)**: **110 phút** (gate ≥ 15 phút).
 - **P99 latency**: **< 10ms** (NumPy in-memory).
- **Acceptance threshold (theo gate Client)**:
 - FPR bắt buộc `≤ 12%`
 - Catch rate (recall) bắt buộc `≥ 80%`
 - Lead time bắt buộc `≥ 15 phút`; Brier `< 0.1`
- **Eval set location**: Toàn bộ kịch bản và báo cáo tự động được đặt tại `<repo>/tf4-evidence/evidence/` dưới định dạng JSON.

## 8. Cost model (Mô hình Chi phí Ước tính)

Foresight Lens tự hào là hệ thống có Cost Model tối ưu bật nhất, giải quyết triệt để vấn đề "hóa đơn sốc" của AIOps.

| Item | Đơn giá / Call | Tần suất dự báo | Chi phí / Ngày | Chi phí / Tenant / Tháng |
|---|---|---|---|---|
| Compute (AWS ECS Fargate Container) | $0.000001 (Tính quy đổi CPU) | 1,440 requests (Mỗi phút 1 lần) | ~$0.01 | ~$0.30 |
| Storage (Lưu trữ Audit logs JSONL qua S3 Standard) | ~$0.0000001 | 1,440 records (~500KB) | ~$0.01 | ~$0.30 |
| ALB (Internal Request Routing) | $0.0000035 | 1,440 requests | ~$0.005 | ~$0.15 |
| **Tổng cộng (Total Estimated)** | | | | **~$0.75 / Tháng** |

> **Kết luận Tài chính**: Với mức giá `< $1 / Tenant / Tháng`, hệ thống thỏa mãn tuyệt đối Constraint ngân sách (Budget < $200), thậm chí đủ khả năng mở rộng lên hàng ngàn Tenant mà không phát sinh gánh nặng tài chính.

## 9. Deployment topology (Cấu trúc Triển khai Hạ tầng)

Kiến trúc hạ tầng đảm bảo tính cô lập và sẵn sàng cao cho môi trường Production:

- **Compute Runtime**: Đóng gói thành Docker Container siêu nhẹ và triển khai trên **AWS ECS Fargate**. Lựa chọn này giúp nhóm AI không phải bảo trì máy chủ EC2 (Serverless Compute), đồng thời không chịu rủi ro Cold-start như AWS Lambda (vì container Fargate chạy liên tục 24/7).
- **Replica strategy (Chiến lược dự phòng)**: Chạy tối thiểu (Min) **2 Tasks** để cấu hình High-Availability. Tự động Scale out tối đa (Max) **4 Tasks** (đúng deployment-contract: min 2, max 4) khi Average CPU > 70% hoặc > 80 RPS/task. *(Lưu ý: đây là autoscale của **bản thân AI Engine** ở tầng hạ tầng — KHÔNG liên quan tới `action_verb`/`from_to` mà AI khuyến nghị cho service của CDO. Hai khái niệm "scale" này tách biệt hoàn toàn.)*
- **Region & AZ (Vùng khả dụng)**: Triển khai mặc định tại **us-east-1 (N. Virginia)** — region AWS chi phí thấp nhất + nhiều service nhất; engine region-agnostic nên đi theo region CDO deploy. Đảm bảo rải đều Task trên **Multi-AZ (3 Availability Zones)** để chống chịu đứt cáp khu vực.
- **Network (Mạng nội bộ)**: Các container Fargate được nhốt hoàn toàn trong dải mạng **Private Subnet**. CDO giao tiếp với AI API thông qua cổng trung gian **Internal Application Load Balancer (ALB)** hoặc **VPC Endpoint**. AI Engine không hề có kết nối mở ra Internet công cộng (No Public IP).
- **Secrets Management**: Thông tin chứng chỉ (nếu cần mã hóa data) được quản lý qua AWS Secrets Manager. Không được phép gắn biến môi trường cứng (Hard-coded Env Vars).

## Related documents

- [`02_solution_design.md`](02_solution_design.md) - High-level architecture context và giải thích quy trình luồng dữ liệu (Data flow).
- [`04_eval_report.md`](04_eval_report.md) - Báo cáo thực tế Eval methodology + results, đối chiếu NFR MG-04, MG-08.
- [`05_adrs.md`](05_adrs.md) - Hồ sơ lưu trữ ADRs giải thích các Trade-offs khi quyết định kiến trúc.
- [`06_metrics_justification.md`](06_metrics_justification.md) - Bằng chứng toán học & URL tham chiếu bảo vệ các con số Hợp đồng.
- [`../contracts/ai-api-contract.md`](../contracts/ai-api-contract.md) - Payload chi tiết giao tiếp với CDO.
- [`../../cdo/docs/03_security_design.md`](../../cdo/docs/03_security_design.md) - Thiết kế bảo mật phía CDO Platform (AI security details ở mục 6 doc này).
- [`../../cdo/docs/05_cost_analysis.md`](../../cdo/docs/05_cost_analysis.md) - Tổng phân tích chi phí TCO.

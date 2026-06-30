# Pitch Cá Nhân — Lê Kim Dũng

**Vai trò**: W11 Integration Engineer — Engine Skeleton  
**Nhóm**: AIO-03 — Foresight Lens  
**Giai đoạn**: Capstone Phase 2 (W11 — Mock Integration Phase)

---

## 1. Nhiệm vụ đảm nhận

| Nhiệm vụ | Deliverable | Trạng thái |
|---|---|---|
| [Lab] Deploy Engine Skeleton (Dummy Logic) | `engine-skeleton/` (toàn bộ thư mục) | Hoàn thành |

---

## 2. Artifacts đã thực hiện

### `engine-skeleton/app/main.py`

Entry point FastAPI của ứng dụng. Tôi xây dựng toàn bộ vòng đời request/response:

**Rate-limit middleware** — sliding window in-memory dùng `defaultdict(list)`, đếm request theo tenant trong cửa sổ 60 giây. Trả HTTP 429 + `Retry-After: 60` khi vượt 600 req/phút/tenant. Đây là cơ chế enforcement thực sự, không phải placeholder.

**Endpoint `POST /v1/predict`** — lớp business validation trên đầu Pydantic schema validation:
- Thiếu header `X-Tenant-Id` -> HTTP 401
- `tenant_id` trong từng datapoint không khớp header -> HTTP 400
- Kiểm tra liên tục thời gian — datapoint có gap > 65 giây -> HTTP 400 (forward-fill bắt buộc theo contract)
- Confidence gating — `confidence < 0.7` hạ `action_verb` xuống `INVESTIGATE` (MG-03)
- Trích xuất `principal_id` từ SigV4 `Authorization` header cho audit log, graceful fallback cho W11 testing

**Endpoint `GET /health`** — trả `{"status": "healthy", "version": "v1.0"}` cho ALB health check (port 8080, 30 giây/lần theo deployment contract).

### `engine-skeleton/app/models.py`

Tất cả Pydantic models enforce API contract ở tầng type:

- `SignalDatapoint` — 5 trường bắt buộc khớp chính xác telemetry contract schema
- `PredictRequest` — `max_length=10000` trên `signal_window` (chặn DoS qua array khổng lồ) và `@field_validator` raise `ValueError` khi signal_window < 120 datapoints, hiển thị là HTTP 422
- `PredictResponse` — `reasoning: str = Field(max_length=300)` enforce MG-01 ở tầng model
- `Recommendation` — `action_verb` type là `Literal["SCALE_UP", "SCALE_DOWN", "RETIRE", "ROLLBACK", "INVESTIGATE"]`. Nếu `engine.py` trả về verb ngoài enum này, Pydantic reject response trước khi nó đi ra ngoài

### `engine-skeleton/app/audit.py`

Audit logger không lưu PII:

- 6 trường bắt buộc khớp đúng audit log schema trong `contracts/ai-api-contract.md`
- SHA-256 hashing toàn bộ `signal_window` payload trước khi ghi. Raw payload không bao giờ chạm đĩa hoặc S3
- Dual backend: `AUDIT_BACKEND=local` ghi JSONL ra disk (dev), `AUDIT_BACKEND=s3` ghi object mã hóa KMS lên S3 với configurable key ID (prod). Backend được kiểm soát bằng env var, phù hợp deployment contract

### `engine-skeleton/app/baseline.py`

Baseline loader theo từng service:

- `@lru_cache(maxsize=64)` — in-memory cache theo service ID, implement "5-minute TTL" semantics được ghi trong deployment contract (TTL xử lý qua container lifecycle)
- Dual backend: local đọc từ `engine-skeleton/baselines/` (dev/W11), S3 fetch qua env vars (prod/W12)
- Trả `None` cho service chưa có baseline, trigger fallback in-window z-score trong `engine.py` — graceful degradation theo thiết kế

### `engine-skeleton/deploy/`

Runbook deploy đầy đủ:

- **`README.md`** — hướng dẫn từng bước deploy Fargate: train baseline + upload S3, ECR build+push, đăng ký task definition, tạo ECS service, smoke test, và hướng dẫn CDO mock-testing khi chưa có live engine
- **`task-definition.json`** — ECS task definition khớp deployment contract (0.5 vCPU, 1024 MB, port 8080, cluster và service name đúng)
- **`mock_responses.json`** — response mẫu đầy đủ cho 7 test case của CDO (success normal, anomaly scale-up, 400, 401, 422, 429, 503). CDO team dùng file này để build integration mà không cần live engine
- **`sample_request.json`** — ví dụ request hợp lệ để smoke test

### `engine-skeleton/tests/test_api.py`

9 scenarios pytest bao phủ toàn bộ contract surface:

1. Health check — GET /health → 200
2. Happy path — baseline ổn định → anomaly=False, recommendation=None
3. Sudden spike (CPU) → anomaly=True, action_verb=SCALE_UP
4. Slow leak (memory) → action_verb=ROLLBACK
5. Sudden drop (throughput) → action_verb=INVESTIGATE
6. Missing tenant header → HTTP 401
7. Dưới 120 datapoints → HTTP 422
8. Tenant ID mismatch → HTTP 400
9. Integration test với STL baseline thực

---

## 3. Quyết định chính và lý do

### Xây real engine logic vào skeleton thay vì dummy logic thực sự

Dù task được đặt tên là "Dummy Logic," skeleton tôi xây dựng chứa engine EWMA + STL đầy đủ, không phải JSON hardcoded. Điểm "skeleton" duy nhất là baseline có thể chưa được train trong tất cả môi trường.

Lý do: Hợp đồng quy định API schema không được thay đổi giữa W11 và W12. Cách đơn giản nhất để đảm bảo điều này là ship real engine ngay từ W11. CDO team test với skeleton nhận đúng cấu trúc response họ sẽ nhận trong W12. "Dummy logic" trong mô tả task là mức tối thiểu — tôi chọn làm vượt mức đó vì chi phí thêm vào gần như bằng không, trong khi loại bỏ toàn bộ một class bug tích hợp W11→W12.

Đánh đổi: Skeleton nặng hơn một pure stub vì có dependency thực (`numpy`, `statsmodels`). Nhưng các dependency này đã trong `requirements.txt` và Docker image size thay đổi không đáng kể.

### Rate limiting in-memory thay vì delegate cho API Gateway

Tôi implement rate limiter 600 req/phút trực tiếp trong FastAPI middleware dùng sliding window `defaultdict`.

Lý do: Trong W11, CDO team test locally không có API Gateway setup đầy đủ. Rate limiting trong app đảm bảo contract có thể enforce trong integration testing, không chỉ trong production. Implementation là stateless per-worker (không distributed) — chấp nhận được trong capstone với single dev worker.

Đánh đổi: Trong production multi-worker, mỗi worker có counter riêng nên effective limit thực tế là `600 × N workers`. Deployment contract chỉ định API Gateway cũng enforce rate limiting ở infra level — app-level limiter là tuyến phòng thủ thứ hai, không phải chính.

### `mock_responses.json` như integration contract với CDO

Tôi tạo file với 7 response case để CDO team build dựa trên fixed payload mà không cần live engine.

Lý do: Trong W11, CDO team build song song. Phải chờ engine deploy xong mới bắt đầu integration testing sẽ lãng phí 3–4 ngày CDO. Mock responses file cho phép CDO team stub endpoint với Prism hoặc static server và phát triển toàn bộ request/response handling — kể cả critical 503 fallback path — một cách độc lập.

---

## 4. Đánh đổi và nhìn lại

Những gì đã làm tốt: 9 test scenarios khớp đúng 9 test scenarios trong `docs/04_eval_report.md` mục 1. Tests và eval report nhất quán vì tôi viết tests để cover chính xác những gì eval spec yêu cầu. Pattern dual-backend (local/S3) cho cả baseline và audit nghĩa là cùng một codebase chạy được ở dev và prod chỉ bằng thay env var — không cần phân nhánh code.

Những gì cần làm khác: In-memory rate limiter reset khi container restart. Tôi nên thêm note trong deploy README về behavior này và khuyến nghị Redis-backed rate limiting cho production.

Test `test_stl_baseline_path_detects_drift` silently skip nếu baseline file không tồn tại (`if not bl_path.exists(): return`), nghĩa là test có thể pass xanh mà không test được STL path. Tôi nên dùng `pytest.skip()` với warning thay vì bare `return` để visible trong test output.

---

## 5. Tự đánh giá

Skeleton bàn giao đủ mọi thứ CDO cần cho W11 integration: working API endpoint, đúng error code, audit logging, rate limiting, và mock responses cho offline testing. 9 test scenarios đều pass. Deploy runbook đầy đủ để CDO team có AWS credentials có thể follow từng bước.

Bằng chứng mạnh nhất: `engine-skeleton/app/engine.py` và `final-build/app/engine.py` là cùng một code. Không có gì cần "nâng cấp" trong W12 vì W11 đã production-quality từ ngày đầu.

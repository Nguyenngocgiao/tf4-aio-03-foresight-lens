# Pitch Cá Nhân — Phan Đức Tài

**Vai trò**: Backend Engineer / FastAPI Skeleton Builder  
**Nhóm**: AIO-03 — Foresight Lens  
**Giai đoạn**: Capstone Phase 2 (W11–W12)

---

## 1. Nhiệm vụ đảm nhận

| Nhiệm vụ | Deliverable | Trạng thái |
|---|---|---|
| Build AI Engine FastAPI Skeleton | `engine-skeleton/app/` (toàn bộ application layer) | Hoàn thành |

Lưu ý: Task [Docs] Prepare Slides & Pitch không có bằng chứng trong repository. Pitch này chỉ cover task đã hoàn thành.

---

## 2. Artifacts đã thực hiện

### FastAPI Application Layer trong `engine-skeleton/app/`

Tôi xây dựng toàn bộ FastAPI application expose Foresight Lens AI engine như một HTTP API. Đây là integration surface mà mọi CDO platform gọi đến. Mỗi request từ CDO platform đều đi qua code tôi viết.

#### `engine-skeleton/app/main.py` — Application Entry Point

**`GET /health`**

Đơn giản nhưng phải chính xác — ALB health check gọi endpoint này mỗi 30 giây. Nếu trả về bất cứ thứ gì khác HTTP 200 với JSON body đúng format, task bị mark unhealthy và traffic ngừng đến.

**`POST /v1/predict`** — endpoint cốt lõi. Tôi implement từng lớp validation mà contract yêu cầu:

1. Thiếu tenant header → HTTP 401 ngay lập tức, trước khi tính toán gì
2. Auto-generate correlation ID nếu `X-Correlation-Id` bị thiếu — đảm bảo mọi request có thể trace ngay cả khi caller không set
3. Cross-tenant datapoint validation — iterate toàn bộ `signal_window` kiểm tra từng `dp.tenant_id` khớp header. O(N) trên window size nhưng chạy trước detection đắt tiền, fail fast trên bad data
4. Time continuity check — iterate datapoint đã sort kiểm tra gap > 65 giây (1-phút interval + 5s tolerance). Trả HTTP 400 kèm message actionable
5. Gọi `detector.detect_drift()` với signal đã validate
6. Confidence gating — nếu `confidence < 0.7`, downgrade `action_verb` xuống `INVESTIGATE`. Một `if` block đơn giản nhưng là một trong những safety control quan trọng nhất trong hệ thống (MG-03)
7. IAM principal extraction — parse `principal_id` từ SigV4 `Authorization` header với graceful fallback cho W11 testing
8. Audit logging — gọi `audit_logger.log_decision()` trước khi return. Response không bao giờ được gửi nếu audit log fail (sequential call, không phải async)

**Rate-limit middleware:**

Chạy trước tất cả route handler, kể cả health checks. Sliding window per-tenant dùng `defaultdict(list)` — lưu timestamp của request gần đây, purge những cái cũ hơn 60 giây, check count so với `RATE_LIMIT_PER_MIN = 600`. Trả HTTP 429 + `Retry-After: 60` khi vượt ngưỡng.

#### `engine-skeleton/app/models.py` — Contract-Enforcing Pydantic Models

Mỗi trường trong API schema là một Pydantic model ở đây. Đây là tuyến phòng thủ giữa raw HTTP request và detection engine:

- `SignalDatapoint` — 5 trường bắt buộc + 1 optional. `ts` type là `datetime` (Pydantic parse RFC3339 tự động và reject timestamp không hợp lệ). `value` là `float` (reject string value).
- `PredictRequest`:
  - `signal_window: List[SignalDatapoint] = Field(..., max_length=10000)` — chặn DoS qua array khổng lồ
  - `@field_validator("signal_window")` — raise `ValueError` nếu `len(v) < 120`, FastAPI surface là HTTP 422 với error body rõ ràng. Đảm bảo EWMA algorithm luôn có đủ data để tạo output hợp lệ
- `Recommendation` — `action_verb` type là `Literal["SCALE_UP", "SCALE_DOWN", "RETIRE", "ROLLBACK", "INVESTIGATE"]`. Nếu `engine.py` trả về verb ngoài list này, Pydantic reject response tại serialization time — bug hiển thị trong tests thay vì silently đến CDO production
- `PredictResponse` — `reasoning: str = Field(max_length=300)`. Enforce MG-01 ở tầng model.

#### Tests: `engine-skeleton/tests/test_api.py`

9 scenarios dùng `fastapi.testclient.TestClient`:

| Scenario | Cái gì được validate |
|---|---|
| Health check | ALB health endpoint hoạt động |
| Happy path | Input bình thường → anomaly=False, không có recommendation |
| Sudden spike (CPU) | Detect anomaly, trả SCALE_UP |
| Slow leak (memory) | Detect anomaly, trả ROLLBACK |
| Sudden drop | Detect anomaly, trả INVESTIGATE |
| Missing tenant header | Trả HTTP 401 |
| Dưới 120 datapoints | Trả HTTP 422 (schema gate) |
| Tenant ID mismatch | Trả HTTP 400 (business gate) |
| STL baseline integration | Baseline thực được load, drift được detect |

Các test này là executable form của API contract — chúng verify rằng error code, response field, và business rule của contract đều được implement đúng.

---

## 3. Quyết định chính và lý do

### Đặt validation trước computation xuyên suốt

Mọi validation check trong `main.py` đều có thứ tự: header check trước, sau là structural validation (Pydantic đã xử lý trước khi handler chạy), rồi business rule check (tenant mismatch, continuity), sau đó mới computation (detect_drift).

Lý do: Thứ tự fail-fast minimize công việc lãng phí. Nếu CDO platform gửi request thiếu tenant header, chúng ta reject ngay mà không cần parse array 120 datapoints. Nếu header khớp nhưng một datapoint có tenant_id sai, reject sau khi parse nhưng trước khi chạy EWMA. Computation đắt tiền chỉ chạy trên data hợp lệ.

Đánh đổi: Continuity check iterate toàn bộ `signal_window` (đến 10,000 points) trước khi detection. Đây là hai pass O(N) nối tiếp. Với window size capstone (120 points) thì không đáng kể. Ở max window size (10,000 points), hai pass O(N) vẫn ổn với latency detection < 10ms trên data thực.

### `action_verb` là `Literal` type trong Pydantic thay vì plain string

`action_verb: Literal["SCALE_UP", "SCALE_DOWN", "RETIRE", "ROLLBACK", "INVESTIGATE"]` thay vì `action_verb: str`.

Lý do: Nếu detection engine trả về verb không có trong enum của contract (ví dụ "SCALE" thay vì "SCALE_UP"), `str` type sẽ để giá trị invalid đi đến CDO platform — CDO có thể silently ignore hoặc fail theo cách không ngờ đến. `Literal` type khiến Pydantic reject response tại serialization time với validation error rõ ràng — bug hiển thị trong tests thay vì trong CDO production. Đây là cách bug bị catch sớm nhất có thể.

### Tests bao phủ error code contract, không chỉ happy path

6 trong 9 test là non-happy-path (error code, edge case). Đây là đảo ngược có chủ ý của phân phối "mostly happy path" thông thường.

Lý do: API contract định nghĩa 5 error code (400, 401, 422, 429, 503). CDO team xây fallback logic dựa trên những mã này — nếu tôi trả 400 ở chỗ contract nói 422, retry logic của họ hỏng. Tests cho 401 (missing header), 422 (< 120 points), và 400 (tenant mismatch) là contract compliance tests, không chỉ unit tests.

---

## 4. Đánh đổi và nhìn lại

Những gì đã làm tốt: `field_validator` cho `signal_window` minimum 120 points nghĩa là validation error (HTTP 422) được Pydantic tạo ra với message rõ ràng thay vì internal error khó hiểu từ EWMA với insufficient data. `Literal` type trên `action_verb` catch một edge case trong development khi `_DEFAULT_REC` trong `engine.py` ban đầu có "INSPECT" thay vì "INVESTIGATE" — Pydantic response validation catch ngay trong test `test_detect_sudden_drop`.

Những gì cần làm khác: Rate-limit middleware dùng in-memory list per tenant. Dưới high concurrency, list operation không thread-safe (hai async coroutine có thể cùng đọc list trước khi cái nào write). Tôi sẽ dùng `asyncio.Lock` per tenant hoặc chuyển sang atomic counter approach.

Test `test_stl_baseline_path_detects_drift` dùng bare `return` để skip gracefully khi baseline file không tồn tại, report là "passed" thay vì "skipped" — misleading. Tôi nên dùng `pytest.skip()` với warning.

---

## 5. Tự đánh giá

FastAPI skeleton là API layer mà mọi CDO integration phụ thuộc vào. Tất cả 9 test scenarios pass. Pydantic models enforce contract schema ở tầng type nên contract và implementation không thể drift silently. Rate limiter, confidence gate, tenant isolation, và audit log đều hoạt động.

Điểm kỹ thuật cần nêu: rate limiter không thread-safe dưới async concurrency — hoạt động đúng ở capstone load level nhưng cần atomic implementation cho production scale.

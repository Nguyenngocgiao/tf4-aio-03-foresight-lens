# Pitch Cá Nhân — Định Nguyễn

**Vai trò**: Technical Lead / Final Build Owner  
**Nhóm**: AIO-03 — Foresight Lens  
**Giai đoạn**: Capstone Phase 2 (W11–W12), Epic Owner

---

## 1. Nhiệm vụ đảm nhận

| Nhiệm vụ | Deliverable | Trạng thái |
|---|---|---|
| [Lab] Implement Real Inference Engine | `final-build/` (W12 production deliverable) | Hoàn thành |
| Epic: Foresight Lens — Capstone Phase 2 (W11–W12) | Kiến trúc tổng thể & điều phối dự án | Hoàn thành |
| [W12] Safety Guard & Multi-tenant Routing | `engine-skeleton/app/main.py` | Hoàn thành |

---

## 2. Artifacts đã thực hiện

### `final-build/` — W12 Production Deliverable

`final-build/` là artifact bàn giao cho CDO trong W12. Nó chứa inference engine production-ready:

- `final-build/app/engine.py` — giống hệt `engine-skeleton/app/engine.py`. Việc skeleton và final-build dùng cùng engine code là cố ý: skeleton được xây dựng production-quality từ ngày đầu, và giai đoạn W12 "final build" là về validation và packaging, không phải viết lại.
- `final-build/app/main.py`, `audit.py`, `baseline.py`, `models.py` — giống hệt skeleton app module, được xác nhận là production codebase trong `CLAUDE.md`: "final-build/ is the active code."
- `final-build/tests/test_api.py` — 9 test scenarios, tất cả pass
- `final-build/Dockerfile` — Docker image production (không có training dependency — những thứ đó nằm trong `requirements-train.txt` ở skeleton, không ship)
- `final-build/requirements.txt` — dependency set tinh gọn cho production

### Safety Guard & Multi-tenant Routing trong `engine-skeleton/app/main.py`

Là Technical Lead, tôi thiết kế và implement toàn bộ safety architecture trong FastAPI application layer.

**Multi-tenant routing — 3 lớp enforcement:**

Lớp 1: Header presence gate — `if not x_tenant_id: raise HTTPException(401)`. Thiếu `X-Tenant-Id` reject ngay trước khi xử lý bất cứ thứ gì.

Lớp 2: Per-datapoint cross-tenant check — iterate mọi datapoint trong `signal_window` và verify `dp.tenant_id == x_tenant_id`. Mọi mismatch raise HTTP 400. Điều này ngăn CDO platform vô tình (hay cố ý) gửi data của tenant khác qua auth header của họ.

Lớp 3: Stateless per-request scoping — `AnomalyDetector` được khởi tạo lúc app start nhưng `detect_drift()` group signal theo `(service_id, metric_type)` mới mẻ trên mỗi call. Không có class-level state variable nào carry context giữa các request. Đây là đảm bảo kiến trúc của tenant isolation.

**Confidence gating (MG-03 governance control):**
```python
if suggested_action and confidence < 0.7:
    suggested_action["action_verb"] = "INVESTIGATE"
```
Safety rail quan trọng: action có impact cao như `SCALE_UP` và `ROLLBACK` bị gated sau ngưỡng confidence 0.7. Anomaly detection với confidence thấp (thật nhưng không chắc) vẫn tạo alert — chỉ là downgrade action xuống `INVESTIGATE`, nghĩa là "người cần nhìn vào cái này" thay vì trigger automated response.

**Rate limiting middleware:**

Sliding window rate limiter dùng `defaultdict(list)` — counter per-tenant, cửa sổ 60 giây, cap 600 request. Trả HTTP 429 kèm `Retry-After: 60`. Đặt như FastAPI middleware nên chạy trước tất cả route handler, ngăn mọi processing cost cho over-limit request.

**Time continuity check:**

Validate các datapoint liên tiếp trong `signal_window` không có gap > 65 giây (interval 1 phút + tolerance 5 giây). Trả HTTP 400 với message rõ ràng. Đây là operationalization của imputation requirement trong telemetry contract.

**IAM SigV4 principal extraction:**
```python
principal_id = (authorization.split("Credential=")[-1].split("/")[0]
                if authorization and "Credential=" in authorization else "mock-principal-id")
```
Trích IAM role ARN từ SigV4 `Authorization` header cho audit logging, graceful fallback về `"mock-principal-id"` cho W11 testing. Engine không bao giờ reject dựa trên auth content — enforcement boundary là CDO-hosted ALB, app chỉ đọc để ghi audit.

### `archive/lab-w3-AIO03-dinh/`

Lab work từ giai đoạn chương trình trước được giữ lại như bằng chứng về background kỹ thuật mang vào capstone.

### Project Architecture tổng thể (Epic Owner)

Với vai trò Epic Owner, tôi chịu trách nhiệm:
- `CLAUDE.md` — build/run/test commands, mô tả kiến trúc, key directories, constraints, eval targets
- `README.md` — project overview, performance evidence summary, getting-started guide
- `.github/workflows/jira-sync.yml` — CI/CD integration cho project tracking
- Convention phân tách `final-build/` và `engine-skeleton/`: skeleton là W11 artifact, final-build là active production code. Điều này ngăn team vô tình sửa W11 artifact trong W12.

---

## 3. Quyết định chính và lý do

### Ship real engine làm W11 skeleton, không phải dummy logic

Là Epic Owner, tôi đặt hướng là W11 "skeleton" sẽ chứa full production-quality engine thay vì JSON stub hardcoded.

Lý do: W11→W12 transition được định nghĩa bởi API schema không đổi. Nếu W11 skeleton trả dummy JSON, W12 "upgrade" sẽ đòi CDO chuyển từ stub sang real prediction — điều đó có thể thay đổi các trường response tinh tế (ví dụ `reasoning` text khác, range `confidence` khác). Bằng cách ship real engine trong W11, thay đổi W12 duy nhất là baseline được train trên data thực thay vì trả None (fall back sang z-score). CDO integration hoàn toàn seamless.

Đánh đổi: Skeleton phức tạp hơn pure stub. Cần nhiều thời gian build và review hơn trong W11. Nhưng đầu tư này hoàn vốn trong W12 khi cutover có zero friction.

### SigV4 enforce ở CDO edge, không phải trong app

Header `Authorization` là `Optional[str]` trong app. App không bao giờ reject request dựa trên auth content — chỉ đọc `principal_id` từ nó cho audit. Enforcement là trách nhiệm của CDO-hosted Internal ALB.

Lý do: Trong private VPC deployment, ALB là security perimeter. AI engine chạy trong private subnet không thể tiếp cận từ bên ngoài VPC ngoài qua ALB. Double-enforce SigV4 trong app tạo ra maintenance problem: nếu AWS thay đổi SigV4 header format, cả ALB config lẫn app code đều cần thay đổi. Single enforcement ở đúng layer là kiến trúc đúng.

Rủi ro giảm thiểu: Nếu ai đó bypass ALB và gửi request không có auth, app vẫn xử lý nhưng audit log ghi `principal_id: "mock-principal-id"`, khiến truy cập trái phép có thể trace được.

### `final-build/app/` là physical copy thay vì symlink hay shared module

`final-build/app/` là bản copy vật lý của `engine-skeleton/app/` chứ không phải symlink hay Python package reference.

Lý do: W12 deliverable cần là một directory tự chứa mà CDO có thể lấy và deploy mà không cần hiểu cấu trúc repo. Symlink sẽ break khi copy. Shared Python package đòi CDO hiểu cấu trúc parent repo. Copy là rõ ràng, không mơ hồ, và có thể deploy độc lập.

Đánh đổi: Bug fix trong `engine-skeleton/app/` phải được mirror thủ công sang `final-build/app/`. Được ghi trong `CLAUDE.md`: "don't edit both." Với 2-tuần capstone đây là chấp nhận được. Với dự án dài hạn tôi sẽ dùng shared package hoặc sync script.

### `CLAUDE.md` như single source of truth vận hành

Tôi viết `CLAUDE.md` như operational reference toàn diện: build commands, test commands, architecture summary, key directories, constraints, và eval targets.

Lý do: Trong dự án nhóm, mọi developer cần biết: build cách nào, test cách nào, rules nào không được phá. Đặt vào `CLAUDE.md` tạo ra một chỗ kiểm tra thay vì phải hỏi teammate. Mục constraints (`contracts/ is FROZEN`, training deps trong `requirements-train.txt`, `final-build/` là active code) ngăn chặn một số lỗi tiềm ẩn trong W12.

---

## 4. Đánh đổi và nhìn lại

Những gì đã làm tốt: Quyết định skeleton quality là đòn bẩy cao nhất của dự án. Nó compress W12 integration về gần bằng không về phía CDO. `CLAUDE.md` như operational reference giúp tất cả thành viên có build/test command nhất quán mà không cần Slack thread.

Những gì cần làm khác: Tôi sẽ thêm `Makefile` với targets (`make test`, `make train`, `make build`) để giảm cognitive load khi nhớ exact command trong `CLAUDE.md`.

`archive/lab-w3-AIO03-dinh/` rỗng trong state hiện tại. Tôi nên điền nó với actual lab artifacts hoặc xóa directory để giữ repo gọn.

Copy-sync problem giữa `final-build/app/` và `engine-skeleton/app/` là real technical debt. Cho W13+ tôi sẽ cấu trúc lại thành `src/foresight_lens/` package mà cả hai import từ đó, loại bỏ duplication.

---

## 5. Tự đánh giá

Là Epic Owner và Technical Lead, trách nhiệm của tôi là đảm bảo dự án ship một deliverable nhất quán, đầy đủ, và production-quality — không chỉ code chạy được locally. `final-build/` có thể deploy, safety guards đầy đủ và có test, multi-tenant routing được enforce ở ba lớp.

Bằng chứng mạnh nhất: `engine-skeleton/app/engine.py` và `final-build/app/engine.py` là cùng một code. Không có gì cần "nâng cấp" trong W12 vì W11 đã production quality từ ngày đầu.

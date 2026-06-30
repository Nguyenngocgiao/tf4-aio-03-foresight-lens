# Pitch Cá Nhân — Thanh Hoang (Jax)

**Vai trò**: Evaluation Engineer  
**Nhóm**: AIO-03 — Foresight Lens  
**Giai đoạn**: Capstone Phase 2 (W11–W12)

---

## 1. Nhiệm vụ đảm nhận

| Nhiệm vụ | Deliverable | Trạng thái |
|---|---|---|
| Generate Evaluation Report | `tf4-evidence/eval_engine.py` + `tf4-evidence/tf4_evidence.py` + `tf4-evidence/evidence/` | Hoàn thành |

---

## 2. Artifacts đã thực hiện

### `tf4-evidence/eval_engine.py` — Evaluation Harness chính

Đây là nguồn đo lường duy nhất cho tất cả metric trong `docs/04_eval_report.md`. Mọi con số trong report — Precision 0.793, Recall 0.971, FP Rate 7.1%, Brier 0.049, Lead Time 110 phút — đều do script này tạo ra. Không có hardcode.

Cách hoạt động:

Script import `AnomalyDetector` trực tiếp từ `engine-skeleton/app/engine.py`, không phải một implementation riêng. Đây là lựa chọn có chủ ý: evaluation harness đo engine thực sự được ship, không phải một bản re-implement.

Với mỗi service trong 3 service tier-1, script slide một window 120 phút qua ngày holdout (step 5 phút), gọi `detector.detect_drift()` trên mỗi window. Tổng cộng khoảng 790 window được chấm điểm trên 3 service.

Ground truth matching qua `true_region_at(idx, labels)` tra cứu label từ `holdout_<service>_labels.json`. Label mã hóa 4 anomaly scenario (gradual_drift, sudden_spike, slow_leak) và 1 false-positive trap (noisy_fp_trap). Window nằm trong vùng anomaly là `is_true=True`.

Lead time được tính cho slow-leak và gradual-drift scenario: `breach_index - first_alert_index`, trong đó breach index là điểm đầu tiên metric vượt ngưỡng cứng (ví dụ CPU >= 90%). Đây là phép đo "engine cảnh báo sớm bao nhiêu phút trước breach thực tế."

Brier Score calibration: với mỗi window tôi tính `(predicted_prob - actual_outcome)²`. Với window anomalous, predicted probability là `confidence` của model; với window bình thường là `1 - confidence`. Mean trên tất cả window cho Brier Score (0.049, được calibrate tốt dưới ngưỡng 0.1).

Output: `tf4-evidence/evidence/evidence_algorithm_evaluation.json`

### `tf4-evidence/tf4_evidence.py` — Orchestrator + A/B Comparison

Script master chạy toàn bộ pipeline tạo evidence:

1. Gọi `eval_engine.evaluate()` để lấy số EWMA+STL
2. Chạy head-to-head Isolation Forest trên cùng holdout window (`isolation_forest_scores()`). Dùng `sklearn.ensemble.IsolationForest` với `contamination=0.02`, fit trên 105 phút đầu của mỗi window, predict trên 5 phút cuối — cùng methodology với EWMA eval
3. Ghi `evidence_algorithm_comparison.json` — A/B comparison (EWMA Recall 0.971/FP 7.1% vs IF Recall 0.638/FP 21.4%)
4. Generate `algorithm_comparison.png` bằng matplotlib — grouped bar chart FP rate % và Recall % của cả hai thuật toán với đường đỏ đứt ở gate 12% FP

### `tf4-evidence/load_test.py`

Load test tạo ra throughput numbers trong `docs/04_eval_report.md` mục 3.3. Dùng `asyncio` + `httpx` (không có k6/Locust trong build environment, nhưng `httpx` đã là app dependency nên không cần tooling bổ sung).

Hai phase:
- SLA validation: 100 RPS × 30 giây, 13 tenant tổng hợp round-robin (~8 RPS/tenant, dưới rate cap 600 req/phút/tenant). Kết quả: 3000/3000 → HTTP 200, 0 lỗi, p99=4.0ms
- Capacity probe: 400 RPS × 15 giây, 50 tenant. Kết quả: 6000/6000 → HTTP 200, 0 lỗi — xác nhận headroom >= 4x trên single uvicorn worker

### Toàn bộ evidence files trong `tf4-evidence/evidence/`

- `holdout_<service>.csv` + `holdout_<service>_labels.json` — holdout sets có label cho 3 service
- `evidence_algorithm_evaluation.json` — kết quả eval chính
- `evidence_algorithm_comparison.json` — A/B comparison
- `evidence_confidence_threshold.json` — bằng chứng confidence gating (MG-03)
- `evidence_cost.json`, `evidence_lead_time.json`, `evidence_load_test.json` — evidence bổ sung
- `algorithm_comparison.png`, `metrics_comparison.png` — visual evidence charts

---

## 3. Quyết định chính và lý do

### Import và test engine thực, không phải stub

`eval_engine.py` import `AnomalyDetector` từ `engine-skeleton/app/engine.py` trực tiếp.

Lý do: Evaluation harness re-implement thuật toán để test thì đang test bản re-implement, không phải sản phẩm. Cách duy nhất để biết engine ship có đạt gate hay không là chạy engine thực sự trên holdout data thực sự. Mọi delta hiệu suất giữa eval environment và production environment được track riêng qua load test.

Đánh đổi: Điều này tạo ra hard dependency giữa eval harness và engine codebase. Nếu cấu trúc module của engine thay đổi, import trong `eval_engine.py` sẽ break. Đây là trade-off đúng — breakage hiển thị là test failure thay vì metric drift thầm lặng.

### Dùng asyncio + httpx cho load test thay vì bọc k6

Tôi viết load test bằng `asyncio` + `httpx` thay vì k6 hay Locust.

Lý do: k6 và Locust không có trong build environment. Nhưng `httpx` đã trong `requirements.txt` như app dependency. Dùng nó cho load test nghĩa là test không cần tooling bổ sung — bất kỳ ai chạy được `pip install -r requirements.txt` đều chạy được load test. Open-loop generator approach (fire request ở fixed rate không chờ response trước) model đúng real load pattern.

Đánh đổi: asyncio + httpx ít configurable hơn k6 cho complex traffic pattern. Với capstone chỉ cần một throughput number ở fixed RPS, đây là đủ.

### Trải tenant across load test để tôn trọng per-tenant rate limit

Load test 100 RPS dùng 13 tenant tổng hợp round-robin (~8 RPS/tenant) thay vì hammering từ một tenant duy nhất.

Lý do: API contract chỉ định rate limit 600 req/phút (10 RPS) per tenant. Nếu dùng single tenant ở 100 RPS, request đầu tiên 10 sẽ success và phần còn lại nhận 429 — kết quả "load test thất bại" sai lệch. 13-tenant spread model đúng cách các CDO platform thực tế đạt aggregate throughput (mỗi CDO platform là một tenant riêng) và validate global throughput SLA mà không kích hoạt per-tenant limiter giả tạo.

### A/B trung thực với Isolation Forest trên cùng holdout

Tôi chạy Isolation Forest trên cùng 790 holdout window với cùng ground truth label và report kết quả trung thực, bao gồm IF trượt FP gate (21.4% vs limit 12%) và recall thấp hơn (0.638 vs 0.971).

Lý do: Comparison cherry-pick baseline yếu để thuật toán của mình trông tốt là vô nghĩa với reviewer am hiểu lĩnh vực. Isolation Forest là thuật toán production-grade thực sự. Cho thấy EWMA+STL outperform nó trên cả hai metric chính trên cùng holdout là kết quả thật — không phải vì IF tệ nói chung, mà vì daily seasonality trong infra metric đặc biệt làm hại IF (nó treat business-hours peak bình thường là anomaly).

---

## 4. Đánh đổi và nhìn lại

Những gì đã làm tốt: Mọi metric đều tái tạo được (`python tf4-evidence/tf4_evidence.py`) nghĩa là Panel có thể reproduce bất kỳ con số nào trong `04_eval_report.md` dưới 2 phút. Brier Score calibration check là insight từ requirements doc của Thanh Phạm Hữu Tiến — implement nó trong eval harness xác nhận confidence score có ý nghĩa cho CDO downstream gating, không phải field trang trí.

Những gì cần làm khác: Hàm `true_region_at` dùng index range check đơn giản, không xử lý overlapping anomaly regions. Với 4-scenario holdout hiện tại điều này không quan trọng, nhưng đây là latent bug cho holdout set phức tạp hơn.

Load test đo throughput với engine chạy local. Fargate latency thực tế gồm cả network hop đến/từ CDO VPC. p99 4ms sẽ likely là 15–30ms trong deployment thực — vẫn trong SLA 500ms, nhưng đáng ghi chú.

---

## 5. Tự đánh giá

Evaluation harness là nền tảng credibility của dự án. Không có nó, các con số trong `04_eval_report.md` là tuyên bố. Với nó, chúng là phép đo. Harness rõ ràng, trung thực (không hardcode ở đâu), và tạo ra output có thể verify. A/B comparison với Isolation Forest là contribution thực — nó cho thấy team hiểu bài toán đủ sâu để biết phải benchmark với alternative nào.

Điểm cần nêu trước Panel: holdout data là tổng hợp (sinh bởi `scripts/train_baseline.py`). Anomaly injection là deterministic và realistic nhưng không lấy từ production traffic log. Real-world performance có thể khác — điều này được ghi trong `docs/04_eval_report.md` mục 7 là known gap.

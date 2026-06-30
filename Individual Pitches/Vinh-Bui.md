# Pitch Cá Nhân — Vinh Bui

**Vai trò**: Algorithm Engineer & Contracts Freeze Owner  
**Nhóm**: AIO-03 — Foresight Lens  
**Giai đoạn**: Capstone Phase 2 (W11–W12)

---

## 1. Nhiệm vụ đảm nhận

| Nhiệm vụ | Deliverable | Trạng thái |
|---|---|---|
| Implement Drift Detection Algorithm | `engine-skeleton/app/engine.py` + `scripts/train_baseline.py` | Hoàn thành |
| Freeze Discovery & API Contracts | `contracts/` (freeze enforcement), `CLAUDE.md` | Hoàn thành |

---

## 2. Artifacts đã thực hiện

### `engine-skeleton/app/engine.py` — Detection Engine

Đây là trung tâm của Foresight Lens. Tôi implement thuật toán STL seasonal baseline + EWMA control chart mà mọi dự đoán đều chạy qua.

**EWMA control chart — method `_ewma_breach`:**

```python
z = alpha * r + (1 - alpha) * z    # cập nhật EWMA
limit = K * sigma * sqrt(alpha / (2 - alpha))   # control limit tiệm cận
```

Hai tham số quan trọng nhất:
- `alpha=0.3` — cân bằng giữa độ nhạy và nhiễu. Alpha thấp (0.05–0.1) khiến EWMA trôi dạt trên nhiễu, FP rate lên đến 20–42% trong sweep. 0.3 là điểm ngọt tìm được qua thực nghiệm.
- `K=4.0` — độ rộng control limit. Công thức control limit EWMA tiệm cận (không phải K*sigma đơn giản) tính đến tính chất giảm phương sai của EWMA statistic. K=4.0 cho FP 7.1% trên holdout.

Method này còn trả về `direction` (-1 cho downward breach, +1 cho upward) để lớp recommendation phân biệt capacity exhaustion (lên) với under-utilisation bất ngờ (xuống).

**Trừ seasonal STL:**

Tại inference, tôi load baseline JSON theo từng service và trừ `profile[minute_of_day % len(profile)]` khỏi mỗi datapoint thô trước khi chạy EWMA. Việc de-seasonalise tín hiệu này — loại bỏ đường cong tải theo giờ trong ngày — giúp EWMA không phát hiện nhầm traffic peak bình thường của business hours.

Fallback: nếu không có baseline cho một service, tôi fall back sang in-window z-score (`residuals = values - mean(values)`). Nghĩa là engine không bao giờ hard-fail với service chưa được đăng ký.

**Method `_recommend` — router 5 verb:**

- Upward breach: route theo `metric_type` đến `_RECS` map cho recommendation cụ thể (CPU → `SCALE_UP`, memory → `ROLLBACK`, queue → `SCALE_UP` workers). Metric không biết → `INVESTIGATE`.
- Downward breach có sustained under-utilisation (`below_frac >= 0.5`): route đến `RETIRE` (queue/pool nhàn rỗi) hoặc `SCALE_DOWN` (ECS service right-sizing). Drop ngắn đột ngột → `INVESTIGATE` (có thể là outage, không phải under-utilisation).
- Confidence tính từ tỉ lệ EWMA breach: `0.6 + 0.15 * (ratio - 1.0)`, cap ở 0.99. Cho ra confidence được calibrate tự nhiên — breach nhỏ khoảng 0.6, breach lớn tiến đến 1.0.

**Method `detect_drift` — public API:**

Group signal theo `(service_id, metric_type)` để một request với 3 service × 4 metric được xử lý đúng theo từng luồng riêng. Trả về khi phát hiện breach đầu tiên (early exit). Trả về `(False, 0.0, None, "No anomaly...", 0.95)` cho window bình thường.

### `scripts/train_baseline.py` — Offline STL Trainer

Script training offline tạo ra baseline file theo từng service, được engine đọc tại inference time.

Cách hoạt động:
1. Sinh 7 ngày telemetry tổng hợp theo đúng hình dạng contract cho mỗi service, dùng hàm `daily_shape()` mô phỏng double-hump business hours thực tế
2. Inject 4 anomaly scenario vào ngày thứ 7 (gradual CPU drift, sudden latency spike, slow memory leak, noisy FP trap) và ghi holdout files có label ra `tf4-evidence/evidence/`
3. Chạy STL (`period=1440`, daily seasonality ở granularity 1 phút) chỉ trên 6 ngày clean (ngày thứ 7 là holdout)
4. Collapse kết quả STL thành seasonal profile theo từng phút trong ngày (1440 giá trị) + một giá trị `resid_std` duy nhất mỗi metric
5. Ghi `engine-skeleton/baselines/<service>.json`

Về dữ liệu tổng hợp: dự án không có quyền truy cập vào telemetry CDO thực. Dữ liệu tổng hợp dùng đúng signal shape từ telemetry contract với seasonality business hours. Kết quả eval là trung thực — anomaly injection là deterministic (`np.random.default_rng(42)`) nên có thể tái tạo.

### `CLAUDE.md` — Freeze Enforcement

Tôi thêm cảnh báo freeze rõ ràng: "contracts/ is FROZEN. Do NOT modify, commit, or touch any file under contracts/" để bảo vệ các hợp đồng đã ký khỏi bị chỉnh sửa vô tình trong giai đoạn W12.

---

## 3. Quyết định chính và lý do

### Dùng EWMA control chart thay vì 3-sigma threshold

Tôi dùng công thức control limit EWMA tiệm cận thay vì rolling 3-sigma đơn giản.

Lý do: Rolling mean ± 3σ tính trên window 120 phút có hai vấn đề. Một, nó bắn nhầm trên spike đơn lẻ vì window mean bị kéo lên bởi chính spike đó. Hai, nó không tích lũy bằng chứng về drift kéo dài — metric leo dần đến exhaustion có thể không bao giờ vượt 3σ cho đến khi đã quá muộn.

EWMA giải quyết cả hai: exponential smoothing weight các điểm gần hơn so với cũ, làm nó nhạy với trend, trong khi đồng thời làm mượt spike đơn lẻ. Control limit formula được dẫn xuất từ phương sai của EWMA statistic, không phải series thô — đó là lý do K=4.0 cho FP rate chặt hơn nhiều so với K=3.0 trên raw series.

Bằng chứng: sweep alpha trong ADR-006 cho thấy alpha thấp (0.05) tạo FP rate 20–42% vì EWMA trôi dạt trên zero-mean noise. alpha=0.3 với K=4.0 cho 7.1% FP và 97.1% recall.

### Tách biệt breach lên và breach xuống

Tôi detect cả breach upward (capacity exhaustion) lẫn downward (drop bất ngờ / under-utilisation) trong `_ewma_breach`, trả về flag `direction`.

Lý do: TF4 brief ghi rõ "retire queue Z không còn dùng" là một recommendation case. Drop đột ngột trong throughput cũng có thể là dấu hiệu outage (INVESTIGATE) thay vì under-utilisation lành mạnh (SCALE_DOWN hoặc RETIRE). Nếu không có direction awareness, mọi anomaly đều trigger scale-up, sai hoàn toàn trong những trường hợp này.

Đánh đổi: Phân biệt "sustained under-utilisation" với "sudden drop" dựa trên `below_frac` (tỉ lệ residual dưới -1σ). Đây là heuristic — `below_frac >= 0.5` nghĩa là hơn nửa window dưới baseline, chỉ báo hoạt động thấp kéo dài. Một cách tiếp cận chắc chắn hơn sẽ dùng time profile của breach, nhưng cách này đủ cho 4 test scenario.

### Grouping in-memory theo (service_id, metric_type) trong một request

Một request `/v1/predict` duy nhất có thể chứa signal cho nhiều service và metric. Tôi group theo `(service_id, metric_type)` và xử lý từng luồng độc lập, return khi phát hiện breach đầu tiên.

Lý do: CDO platform monitor 3 service gửi một batched request. Nếu xử lý tất cả signal như một flat series, cross-service interaction sẽ tạo ra EWMA value vô nghĩa (ví dụ CPU của payment-gw trộn với queue depth của ledger). Per-stream processing đảm bảo baseline của mỗi service được áp dụng đúng cho data của service đó.

Đánh đổi: Early exit khi breach đầu tiên nghĩa là nếu hai service anomalous đồng thời, chỉ cái tìm thấy trước được báo cáo. Use case của khách hàng là "dự đoán trước breach" — nhận một alert sớm có thể hành động được tốt hơn report đa anomaly bị delay.

---

## 4. Đánh đổi và nhìn lại

Những gì đã làm tốt: Fallback z-score cho service chưa có baseline đảm bảo engine không fail với HTTP 500 khi gặp service ID lạ — quan trọng trong W11 khi CDO team gửi traffic test với service ID không chuẩn. Hàm `daily_shape()` trong train_baseline.py tạo ra seasonality đủ thực tế để exercise logic de-seasonalisation một cách có ý nghĩa.

Những gì cần làm khác: Synthetic data generator dùng fixed random seed nhưng chỉ model đường cong business hours đơn giản. Infra metric thực tế có pattern phức tạp hơn (weekly seasonality, maintenance windows, deployment events). Training trên synthetic data phong phú hơn sẽ tạo ra baseline chắc chắn hơn.

Early exit trên breach đầu tiên là thứ tự ưu tiên ngầm định — metric nào xuất hiện đầu trong `groups` dict thì thắng. Tôi nên làm điều này tường minh — ví dụ luôn check `memory_usage_percent` trước vì memory leak khó giảm thiểu nhất trong thực tế.

---

## 5. Tự đánh giá

Drift detection algorithm là core value-add của dự án. Nó vượt tất cả gate của khách hàng: Recall 97.1% vs target 80%, FP Rate 7.1% vs gate 12%, Lead Time 110 phút vs tối thiểu 15 phút, latency < 10ms vs SLA 500ms. So sánh thuật toán trong `tf4-evidence/evidence/evidence_algorithm_comparison.json` ghi lại head-to-head với Isolation Forest, Panel có thể verify bằng cách chạy lại `python tf4-evidence/tf4_evidence.py`.

Implementation rõ ràng, có comment đầy đủ, và implement trực tiếp các quyết định ADR. Điểm còn chủ quan là heuristic `below_frac` để phân biệt outage với under-utilisation — hoạt động đúng với 4 test scenario nhưng cần validation trên data đa dạng hơn.

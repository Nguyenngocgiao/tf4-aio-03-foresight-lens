# ADR 001: Lựa chọn thuật toán STL + EWMA control chart (Foresight Lens)

> Đây là bản chi tiết của quyết định thuật toán. ADR log tổng hợp ở `docs/05_adrs.md`
> (ADR-001/004/005). Hai tài liệu phải nhất quán với nhau và với `engine-skeleton/app/engine.py`.

## Trạng thái
**Chấp thuận (Accepted)** — 2026-06-25

## Bối cảnh (Context)
**Foresight Lens** cần dự đoán Capacity Exhaustion từ telemetry time-series (CPU, Memory,
Connection Pool, Queue...). Gate của Client:
1. **Ngân sách** ≤ $200/tháng.
2. **False Positive ≤ 12%**, **Catch (Recall) ≥ 80%**, **Lead time ≥ 15 phút**.

Đặc thù dữ liệu infra có **chu kỳ ngày/đêm mạnh** (business hours vs đêm), nên ngưỡng tĩnh
hoặc 3-sigma thuần sẽ báo nhầm vào peak tải bình thường.

## Quyết định (Decision)
Chọn **STL seasonal baseline (train offline) + EWMA control chart (inference)**:
- **STL** (Seasonal-Trend decomposition, period=1440) chạy offline trong
 `scripts/train_baseline.py` trên ≥6 ngày/service → tách chu kỳ ngày, lưu seasonal profile +
 residual σ thành per-service baseline (S3). STL **không** chạy trong window 120 phút vì 2 tiếng
 không chứa nổi 1 chu kỳ ngày.
- **EWMA control chart** (α=0.3, K=4.0σ) chạy trong engine trên phần dư đã khử seasonal → bắt
 drift kéo dài sớm (lead time), làm mượt gai đơn lẻ (chặn false positive).

## Căn cứ (Evidence — đo thật)
Nguồn: `tf4-evidence/evidence/evidence_algorithm_evaluation.json` + `evidence_algorithm_comparison.json`
(re-run: `python tf4-evidence/tf4_evidence.py`).

| Thuật toán | Recall | FP Rate | Đạt gate ≤12% ? |
|---|---|---|---|
| **STL + EWMA** | **0.971** | **7.1%** | |
| Isolation Forest | 0.638 | 21.4% | |

- Precision 0.793 · F1 0.873 · Brier 0.049 · Lead time (median) 110 phút.
- Tham số α=0.3, K=4.0 chọn từ sweep 16 tổ hợp (xem `05_adrs.md` ADR-005).

## Hệ quả (Consequences)
**Tích cực:**
- Latency `POST /v1/predict` < 10ms (NumPy vectorised); cost serving ~$36/tháng (Fargate 2-task).
- Khử seasonality đúng cách → FP thấp (7.1%) mà vẫn catch 97.1%.
- Explainable: mọi alert quy ra "residual vượt K·σ control limit", không hallucinate.

**Tiêu cực / cần lưu ý:**
- Có **training phase offline** (khác 3-sigma thuần): phải train baseline + upload S3, refresh
 thủ công hàng tuần (drift-triggered retrain chỉ design — xem ADR retrain).
- Seasonal profile hiện theo chu kỳ **ngày**; chu kỳ **tuần** là future work (train ≥14 ngày).

## Alternatives rejected
- **3-Sigma thuần (z-score in-window)**: rejected — không khử được seasonality, FP cao khi gặp
 peak tải bình thường. (Vẫn giữ làm *fallback* khi service chưa có baseline.)
- **Isolation Forest**: rejected — FP 21.4% > gate, recall 0.638; nặng compute, cần warm-up.
- **LLM / Agentic**: rejected — latency giây, cost token phá $200, hallucinate trên số học.

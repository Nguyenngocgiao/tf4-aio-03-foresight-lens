# Eval Report - Foresight Lens

<!-- Doc owner: AIO-03
     Status: Skeleton (W11 T6 Pack #1) → Full results (W12 T4 Pack #2)
     Word target: 1000-1800 từ -->

## 1. Test scenarios

| # | Scenario | Type | Expected output |
|---|---|---|---|
| 1 | Happy Path (Normal CPU) | Happy | ALERT_ONLY |
| 2 | Sudden Spike (CPU 50→98) | Happy | SCALE_UP |
| 3 | Gradual Drift (CPU tăng dần→95) | Happy | anomaly=True |
| 4 | Slow Leak (Memory 40→92 OOM) | Happy | ROLLBACK |
| 5 | Noisy Baseline (Flash Sale traffic) | Edge | ALERT_ONLY (No FP) |
| 6 | Sudden Drop (Throughput 1000→50) | Edge | INVESTIGATE (two-tailed) |
| 7 | Multi-tenant Isolation | Edge | Tenant B unaffected |
| 8 | Missing X-Tenant-Id | Adversarial | HTTP 422 |
| 9 | Verify Success (metrics normal) | Verify | success=True |
| 10 | Verify Regression (metrics still bad) | Verify | regression_detected=True, ESCALATE |

## 2. Methodology

- **Setup**: Chạy local qua script `tf4_evidence.py`.
- **Test data**: Dữ liệu synthetic giả lập 7 ngày của 5 services độc lập (PaymentGW, Fraud, Ledger, KYC, Reporting) để chứng minh tính đa nhiệm.
- **Run procedure**:
  1. Load dữ liệu giả lập có nhồi nhiễu (noise) và chu kỳ (seasonality).
  2. Bơm 4 Root Causes (CPU, Memory, Queue, Connection) vào data.
  3. Chạy A/B/C testing đối chứng 3 thuật toán (EWMA & STL Decomposition, EWMA, Isolation Forest).
  4. Record metric.
- **Metrics measured**: precision · recall · F1 · P50/P99 latency · cost/call

![Service Comparison](../xbrain-learner/tf4-evidence/evidence/service_comparison_cpu.png)
*(Biểu đồ trên: Bằng chứng cho thấy 3 dịch vụ có baseline và đỉnh tải (Peak hours) hoàn toàn khác nhau, chứng minh AI không bị học vẹt)*

## 3. Results (Statistical EWMA & STL Decomposition Model)

Dựa trên kết quả chạy mô phỏng tự động từ script `tf4-evidence/tf4_evidence.py`. Toàn bộ số liệu gốc được lưu tự động và có thể đối chứng tại thư mục `tf4-evidence/evidence/`.

| Metric | Target | Actual | Pass/Fail | Nguồn trích xuất (Evidence Source) |
|---|---|---|---|---|
| Precision (σ=3.0) | ≥ 0.8 | **1.000** | ✓ Pass | `evidence_confidence_threshold.json` (real ewma_stl eval, 200 windows) |
| Recall (σ=3.0) | ≥ 0.7 | **1.000** | ✓ Pass | `evidence_confidence_threshold.json` (real ewma_stl eval, 200 windows) |
| F1 Score (σ=3.0) | ≥ 0.75 | **1.000** | ✓ Pass | `evidence_confidence_threshold.json` |
| False Positive Rate | ≤ 0.12 | **0.000 (0%)** | ✓ Pass | `evidence_confidence_threshold.json` (σ=3.0) |
| Brier Score | < 0.25 | **0.032** | ✓ Pass | `evidence_confidence_threshold.json` + `evidence_reliability_diagram.json` |
| Lead Time | ≥ 15 mins | **106 mins** | ✓ Pass | `evidence_lead_time.json` |
| P99 latency | < 500ms | **< 10ms** | ✓ Pass | In-memory NumPy computation |
| Cost per month | < $200 | **$0 - $3** | ✓ Pass | `evidence_cost.json` |
| Pytest Scenarios | ≥ 10 | **10/10 passed** | ✓ Pass | `engine-skeleton/tests/test_api.py` |

![Metric Priority](../xbrain-learner/tf4-evidence/evidence/metric_priority_multi_root.png)
*(Biểu đồ trên: Phân tích Metric Priority. Chứng minh rạch ròi rằng bất kể là lỗi gì (Root cause nào), thì `latency` và `queue_depth` luôn là 2 chỉ số báo hiệu sớm nhất, trước cả khi CPU/Memory chết).*

### 3.1 Algorithm Evaluation (Đang tiến hành)

Thiết kế ban đầu của team là sử dụng `EWMA + Isolation Forest`. Tuy nhiên, kết quả test thực tế (A/B/C testing trên 100 windows) đã dẫn đến đề xuất "quay xe":

| Thuật toán | F1 Score | FP Rate (Báo động giả) | Compute Latency |
|---|---|---|---|
| **EWMA & STL Decomposition** | ~ 1.0 | **0%** | **< 1 ms** |
| **Isolation Forest** | ~ 1.0 | > 0% (nhạy cảm nhiễu) | ~ 20 ms (nặng nhất) |
| **EWMA** | Thấp hơn | > 0% | < 1 ms |

**Đề xuất**: Kết quả sơ bộ cho thấy EWMA & STL Decomposition có ưu thế về độ trễ và tỷ lệ báo động giả (FP=0%), phù hợp làm baseline. Tuy nhiên Isolation Forest có thể mạnh hơn ở các pattern phức tạp. Chưa đưa ra quyết định cuối cùng, chờ thảo luận cùng CDO.

![Algorithm Evaluation](../xbrain-learner/tf4-evidence/evidence/algorithm_comparison.png)

### 3.2 Confusion matrix

```
                Predicted
              | Anomaly | Normal
Actual ─────┼─────────┼────────
   Anomaly   |   TP    |   FN
   Normal    |   FP    |   TN
```

| | Predicted Anomaly | Predicted Normal |
|---|---|---|
| Actual Anomaly | <TP> | <FN> |
| Actual Normal | <FP> | <TN> |

## 4. Failure analysis

### 4.1 Failure case 1: Dữ liệu quá "đẹp" (Zero variance)

- **Expected**: Thuật toán không bị crash khi dữ liệu không có độ lệch chuẩn (std = 0).
- **Got**: Báo lỗi `False` do `std_val = 0` (chia cho 0 hoặc không thỏa mãn điều kiện `> 0`).
- **Root cause**: Dữ liệu synthetic đôi khi hoàn toàn bằng phẳng (Ví dụ CPU lúc nào cũng đứng im ở 50%).
- **Fix**: Thêm một hằng số epsilon (`std_val = 1.0` nếu `std_val == 0`) trong `engine.py`.
- **Result after fix**: Đã pass toàn bộ Unit Test.

### 4.2 Failure case 2: Báo động giả dịp Flash Sale
- **Expected**: Không báo động giả.
- **Got**: False Positive tăng nhẹ lên 0.4% khi nhồi nhiễu có phương sai cực cao (std=20).
- **Root cause**: ewma_stl nhạy cảm với các spike (gai) vượt rào ngẫu nhiên.
- **Fix**: Yêu cầu duy trì số lượng điểm bất thường liên tiếp (M/N) hoặc sử dụng tính năng "Manual Silence" (đã ghi nhận trong ADR-003).
- **Evidence Source**: Trích xuất từ file `evidence_noisy_baseline.json` (FP Rate = 0.004).

## 5. Curveball impact

<!-- 3 curveball - pass/fail mỗi cái + lessons learned -->

| Curveball | Tier | Response | Outcome | Lesson |
|---|---|---|---|---|
| #1 small (T5 W11) | Small | <how engine adapted> | Pass/Partial/Fail | ... |
| #2 medium (T2 W12) | Medium | ... | ... | ... |
| #3 chaos (T4 W12) | Chaos | ... | ... | ... |

## 6. Cost vs forecast

| Phase | Forecast | Actual | Delta |
|---|---|---|---|
| Dev (W11) | $5.00 | **$0.00** | -100% |
| Testing | $10.00 | **$0.00** | -100% |
| Buổi chấm demo | $20.00 | **$0.01 (Tiền điện server)** | -99.9% |

> **Lưu ý:** Việc sử dụng AI thuần thống kê (In-house) giúp team triệt tiêu hoàn toàn chi phí token của LLM, đảm bảo dư sức vượt qua NFR về giới hạn Cost < $200.

## 7. Improvement next iteration

<!-- Top 3 gap + plan (cho post-capstone production roadmap) -->

1. **Gap**: <description> → **Plan**: ...
2. **Gap**: ... → **Plan**: ...
3. **Gap**: ... → **Plan**: ...

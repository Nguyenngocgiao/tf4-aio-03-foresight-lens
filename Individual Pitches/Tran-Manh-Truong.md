# Pitch Cá Nhân — Trần Mạnh Trường

**Vai trò**: Solution Architecture & Presentation Lead  
**Nhóm**: AIO-03 — Foresight Lens  
**Giai đoạn**: Capstone Phase 2 (W11–W12)

---

## 1. Nhiệm vụ đảm nhận

| Nhiệm vụ | Deliverable | Trạng thái |
|---|---|---|
| [W12] Document Curveball Responses | `docs/04_eval_report.md` mục 5 | Còn là placeholder — chưa điền sau W12 curveball sessions |
| [W12] Build Pitch Slides | `tf4-foresight-lens.html` (referenced trong README) | Không có file trong repository |
| [Docs] Solution Design & ADRs | `docs/02_solution_design.md` + `docs/05_adrs.md` + `diagrams/` | Hoàn thành |

---

## 2. Artifacts đã thực hiện

### `docs/02_solution_design.md` — High-Level Architecture

Đây là tài liệu kể câu chuyện kiến trúc của Foresight Lens. Tôi tự viết toàn bộ các mục:

**Bảng component breakdown** — 4 component với trách nhiệm, tech choice, và lý do:
- API & Routing Layer (FastAPI + Pydantic)
- Anomaly Detection Engine (NumPy EWMA + STL)
- Audit Logger (JSONL + S3/DynamoDB)
- Decision Router (static thresholding)

**Data flow 6 bước** — từ CDO ingestion qua validation, xử lý STL+EWMA, confidence scoring, audit trail, đến trả response. Mỗi bước ghi rõ error code được throw tại boundary validation.

**Alternatives considered** — hai so sánh kiến trúc lớn:
- GenAI (LLM) vs Statistical Model: ba lý do reject LLM là cost, latency, và hallucination risk, mỗi cái định lượng cụ thể
- AI query Prometheus vs CDO push qua API: lý do reject pull model là tight-coupling risk

**Risk + mitigation** — 4 rủi ro với likelihood, impact, và mitigation:
- Alert Fatigue → Confidence threshold + K=4.0 EWMA
- Data Bleed → Per-request stateless scoping
- Flash Sale traffic burst → CDO Silence Alert mechanism
- DDoS → Rate limiting middleware

**Open design questions & Technical Debt** — ghi lại resolution fail-open và technical debt về EWMA hard-coded parameters.

### `docs/05_adrs.md` — Architecture Decision Records ADR-001 đến ADR-006

Tôi viết hoặc đồng viết toàn bộ ADR log:

- **ADR-001** — Statistical Analysis vs LLM. Ba lý do reject LLM: cost, latency, hallucination
- **ADR-002** — Confidence Threshold 0.7. Giải thích vì sao 0.5 (quá lỏng) và 0.8 (quá chặt) bị loại
- **ADR-003** — Manual Retrain cho Flash Sales. Vấn đề seasonal anomaly và cơ chế Silence Alert
- **ADR-004** — STL + EWMA vs Isolation Forest. Quyết định A/B quan trọng nhất với con số đo thực: EWMA Recall 0.971 vs IF 0.638, EWMA FP 7.1% vs IF 21.4%
- **ADR-005** — Retrain Trigger Logic (đồng viết với Thịnh Nguyễn Hưng)
- **ADR-006** — EWMA parameter sweep (alpha=0.3, K=4.0), gồm bảng so sánh 4 dòng từ holdout sweep

### `diagrams/`

Ba sơ đồ kiến trúc ở cả định dạng `.drawio` (có thể chỉnh sửa) và `.png` (đã render):
- `02_solution_design.drawio/.png` — high-level architecture
- `03_ai_action_loop.drawio/.png` — AI request/response action loop
- `deployment_topology.drawio/.png` — ECS Fargate deployment topology

---

## 3. Quyết định chính và lý do

### Ghi lý do reject LLM thành ba lý do độc lập, định lượng được

Trong ADR-001 và phần alternatives của solution design, tôi tách lý do reject LLM thành ba failure mode riêng biệt thay vì một nhận định chung chung.

Lý do: Một reviewer biết lĩnh vực khi nghe "LLM không phù hợp" sẽ ngay lập tức hỏi "tại sao?". Có ba lý do độc lập và định lượng được làm câu trả lời không thể bác bỏ:
- Cost: LLM API call khoảng $0.001/call × 1,440 calls/ngày × 30 ngày × 3 service = $130/tháng. Tiêu 65% ngân sách $200 chỉ cho inference, không còn chỗ cho compute, storage, hay CDO infrastructure.
- Latency: LLM call trung bình 2–10 giây. SLA của chúng ta là P99 < 500ms. Vi phạm 4–20 lần.
- Hallucination: Với anomaly detection trên số liệu, một model có thể "bịa" lý do là nguy hiểm chủ động. SRE hành động dựa trên "CPU spike" hallucinated có thể gây incident production.

### "Fail-open" như nguyên tắc kiến trúc tường minh

Tôi định nghĩa "fail-open" là nguyên tắc kiến trúc được đặt tên trong solution design: nếu AI engine trả về 5xx hay timeout, CDO phải fallback sang rule-based alerting. AI engine không được phép làm CDO monitoring đen tối.

Lý do: Trong hệ thống AIOps, AI layer là advisory infrastructure. Nghĩa vụ monitoring cốt lõi thuộc về CDO. Nếu thiết kế CDO monitoring phụ thuộc vào AI engine available, chúng ta đang đưa vào một Single Point of Failure mới trong production. Fail-open nghĩa là CDO outage AI engine là trải nghiệm degraded (không có ML predictions), không phải monitoring outage.

Đánh đổi: Fail-open yêu cầu CDO phải duy trì và test rule-based fallback path — không thể deprecated sau khi AI deploy. Đây là chi phí vận hành lâu dài cho CDO, nhưng đây là trade-off đúng.

### Sơ đồ kiến trúc ở định dạng `.drawio` thay vì chỉ image

Tôi tạo tất cả sơ đồ ở cả `.drawio` source lẫn `.png` render, không chỉ PNG.

Lý do: File `.drawio` có thể chỉnh sửa — nếu kiến trúc thay đổi sau capstone, một thành viên tương lai có thể mở sơ đồ trong draw.io và cập nhật mà không cần vẽ lại từ đầu. Cùng lý do với việc giữ source code thay vì chỉ compiled binary: source mới là artifact có thể bảo trì.

---

## 4. Đánh đổi và nhìn lại

Những gì đã làm tốt: Data flow 6 bước trong `02_solution_design.md` trở thành tài liệu onboarding hữu ích. Trong W11 integration, CDO team dùng nó để hiểu engine làm gì tại mỗi giai đoạn. ADR format (Context → Decision → Consequences → Alternatives) tạo ra tài liệu dễ scan trong buổi defense trực tiếp.

Những gì chưa hoàn thành: Phần Curveball Responses trong `docs/04_eval_report.md` mục 5 còn là placeholder table. Các buổi W12 curveball đã diễn ra nhưng outcome không được ghi lại vào file. Đây là gap thật trong deliverable. Pitch Slides (`tf4-foresight-lens.html`) được đề cập trong README nhưng file không có trong repository.

Những gì cần làm khác: Tôi nên ghi kết quả curveball ngay sau mỗi buổi thay vì để dành "điền sau". Tài liệu hoãn lại gần như luôn là tài liệu không đầy đủ. Tôi cũng nên thêm cross-reference đến `docs/03_ai_engine_spec.md` từ bảng component breakdown trong solution design — tài liệu spec tồn tại nhưng `02_solution_design.md` không link đến nó từ bảng component.

---

## 5. Tự đánh giá

Solution design và ADR documents hoàn chỉnh và tạo thành một câu chuyện kiến trúc nhất quán. Sơ đồ chính xác và có thể chỉnh sửa. ADR-001 đến ADR-006 có căn cứ bằng số đo thực ở những chỗ cần thiết (ADR-004 và ADR-006 dẫn chiếu holdout numbers).

Nhìn thẳng vào phần chưa hoàn thành: curveball section và pitch slides là gap thật, không phải thiếu sót trong tài liệu hóa. Nội dung hoặc không được capture (curveball) hoặc không được commit (slides).

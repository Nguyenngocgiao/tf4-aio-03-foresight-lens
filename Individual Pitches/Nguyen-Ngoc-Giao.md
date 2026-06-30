# Pitch Cá Nhân — Nguyễn Ngọc Giao (MrKnife0912)

**Vai trò**: AI Contracts Lead  
**Nhóm**: AIO-03 — Foresight Lens  
**Giai đoạn**: Capstone Phase 2 (W11–W12)

---

## 1. Nhiệm vụ đảm nhận

| Nhiệm vụ | Deliverable | Trạng thái |
|---|---|---|
| [Contracts] Draft AI API Contract | `contracts/ai-api-contract.md` | Hoàn thành & Đã đóng băng |

---

## 2. Artifacts đã thực hiện

### `contracts/ai-api-contract.md`

Đây là tài liệu hợp đồng ràng buộc giữa AI engine (AIO-03) và ba nền tảng CDO (Payment, Fraud, Ledger). Mọi quyết định tích hợp phía CDO đều phụ thuộc vào tính ổn định và rõ ràng của tài liệu này.

Những phần tôi trực tiếp soạn thảo:

**Chiến lược versioning** — định nghĩa path versioning `/v1/` với cửa sổ hỗ trợ song song 30 ngày cho breaking changes, giúp các CDO team không bị ép phải nâng cấp đồng thời.

**Mô hình xác thực** — thiết kế để IAM SigV4 được enforce ở tầng edge (Internal ALB / API Gateway `AWS_IAM` authorizer + SG-to-SG), không phải trong application code. Đây là một quyết định kiến trúc có chủ ý: engine chạy sau cổng CDO-hosted nên việc verify chữ ký hai lần ở app là thừa và tạo ra ảo giác bảo mật sai chỗ.

**Điều khoản bàn giao hai giai đoạn W11/W12** — ghi rõ rằng `Authorization` ở app giữ là `Optional` trong W11 là cố ý, không phải lỗi. SigV4 chỉ được enforce nghiêm từ CDO edge trong W12. Điều khoản này tránh sự nhầm lẫn cho ba CDO team trong giai đoạn test với curl/Postman.

**Schema request/response đầy đủ** — tất cả các trường với kiểu dữ liệu, ràng buộc (`signal_window >= 120 datapoints`, timestamp RFC3339, giá trị float), và phân biệt required/optional. Khớp 1-1 với Pydantic models trong `engine-skeleton/app/models.py`.

**Audit Log Schema** — định nghĩa 6 trường bắt buộc (`audit_id`, `timestamp`, `tenant_id`, `principal_id`, `input_hash`, `recommendation_snapshot`) cùng yêu cầu mã hóa và lưu trữ (KMS at rest, 365 ngày). Được enforce trong `engine-skeleton/app/audit.py`.

**Rate limiting spec** — 600 req/phút mỗi tenant, 6000 req/phút toàn cục, HTTP 429 kèm `Retry-After`. Implement trong middleware của `engine-skeleton/app/main.py`.

**Bảng mã lỗi** — 5 mã lỗi (400, 401, 422, 429, 503) với hướng dẫn xử lý cụ thể cho CDO (sửa vs retry vs fallback).

---

## 3. Quyết định chính và lý do

### SigV4 enforce ở edge, không phải trong app code

Tôi quyết định engine không verify chữ ký SigV4 trong application code mà chỉ đọc `principal_id` từ header đã được xác thực để ghi audit. Enforcement thuộc về CDO-hosted Internal ALB.

Lý do: Trong kiến trúc microservices đặt sau private ALB, ranh giới mạng bản thân là perimeter xác thực. Nếu enforce ở cả gateway lẫn app, khi cấu hình gateway thay đổi thì app-level check trở thành tuyến phòng thủ duy nhất mà không có người chịu trách nhiệm rõ ràng. Bằng cách giữ enforcement ở infra layer của CDO, AI engine giữ được vai trò thuần xử lý. Hợp đồng ghi rõ điều này để không có sự mơ hồ về "ai enforce cái gì."

Đánh đổi: Nếu ai đó bypass ALB và hit engine trực tiếp trong VPC bị cấu hình sai, auth ở app level sẽ không chặn được. Rủi ro này được giảm thiểu bởi Security Group rules (`tf-4-ai-engine-sg`) chỉ cho phép traffic từ CDO platform SGs.

### Authorization header Optional trong W11 là quyết định thiết kế, không phải bug

Trong W11 mock testing, `Authorization` được type là `Optional[str]` trong `main.py`. Tôi ghi rõ trong hợp đồng rằng đây là cố ý.

Lý do: CDO team cần test integration bằng curl và Postman mà không cần setup SigV4 signing. Nếu bắt buộc auth ở engine level trong W11 thì sẽ mất vài ngày làm chậm tiến độ CDO. Hợp đồng nêu rõ điều này thay đổi trong W12 khi CDO edge enforce nghiêm.

### Cơ chế đóng băng

Sau khi hợp đồng được ký (2026-06-25), tôi thêm header `FREEZE` và quy trình change request chính thức, đồng thời thêm cảnh báo FROZEN vào `CLAUDE.md`.

Lý do: API contract là loại tài liệu khó thay đổi nhất khi đã đưa vào sản xuất. Nếu CDO đã build integration dựa trên một schema mà tôi thay đổi thầm lặng một tên trường, code phía CDO hỏng mà không có cảnh báo rõ ràng. Cơ chế freeze bắt chước cách các tổ chức kỹ thuật thực sự quản lý API contract production.

---

## 4. Đánh đổi và nhìn lại

Những gì đã làm tốt: Điều khoản W11/W12 phased delivery giúp CDO không phải thay đổi code khi chuyển từ skeleton sang real engine vì API schema đồng nhất suốt. Spec 6 trường audit cho implementation `audit.py` một contract rõ ràng có thể test được.

Đánh đổi đã thực hiện: Tôi giữ mức tối thiểu `signal_window` ở 120 datapoints và reject bằng HTTP 422 với window nhỏ hơn. Một số CDO team phản hồi về cold-start scenario. Tôi giữ nguyên vì EWMA thực sự cần 120 điểm để tạo ra mean đủ ổn định — window nhỏ hơn sẽ tăng false positive đáng kể, được ghi rõ trong `docs/06_metrics_justification.md`.

Nếu làm lại: Tôi sẽ thêm một flag `dry_run` tùy chọn vào request để CDO team có thể gửi request nhận phản hồi schema validation mà không trigger prediction hay audit log thật. Điều này sẽ giúp ích nhiều trong W11 integration testing.

---

## 5. Tự đánh giá

Hợp đồng giữ nguyên không cần sửa đổi trong toàn bộ chu kỳ W11–W12. Cả W11 skeleton lẫn W12 real engine đều implement đúng schema tôi đã định nghĩa. Tất cả 9 test scenarios trong `tests/test_api.py` validate đúng với error code và field requirement của hợp đồng. Freeze được tuân thủ, không có thay đổi nào được thực hiện sau khi ký.

Điểm tôi tự nhận xét thêm: trường `from_to` gây nhầm lẫn trong quá trình review — một số người tưởng nó đề cập đến việc scale bản thân AI engine thay vì service CDO đang quản lý. Tôi đã thêm note cảnh báo vào hợp đồng để làm rõ. Nếu thiết kế lại, tôi sẽ đặt tên trường này rõ hơn từ đầu, ví dụ `target_from_to`.

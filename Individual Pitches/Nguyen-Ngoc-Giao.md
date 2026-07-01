# Pitch Cá Nhân — Nguyễn Ngọc Giao (MrKnife0912)

**Vai trò**: AI Contracts Lead  
**Nhóm**: AIO-03 — Foresight Lens  
**Giai đoạn**: Capstone Phase 2 (W11–W12)

---

## 1. Nhiệm vụ & Kết quả

| Nhiệm vụ | Deliverable | Trạng thái |
|---|---|---|
| Thiết kế & chốt AI API Contract | `contracts/ai-api-contract.md` | Hoàn thành & Đã đóng băng (Frozen) |

Tài liệu `ai-api-contract.md` là "xương sống" cho việc giao tiếp giữa AI engine của nhóm tôi và ba nền tảng CDO (Payment, Fraud, Ledger). Để các team CDO có thể code tích hợp mà không sợ bị loạn, tài liệu này cần cực kỳ rõ ràng và ổn định.

Những điểm chính tôi đã trực tiếp thiết kế trong hợp đồng này:

- **Chiến lược Versioning**: Dùng path `/v1/`. Nếu có breaking changes sẽ đẩy lên `/v2/` và duy trì bản cũ ít nhất 30 ngày để các CDO team có thời gian migrate, không bị ép phải làm ngay lập tức.
- **Mô hình Xác thực (SigV4)**: Chuyển toàn bộ việc verify IAM SigV4 ra tầng mạng ngoài cùng (Edge/Internal ALB). App sẽ không check lại chữ ký nữa mà chỉ lấy `principal_id` để ghi log. 
- **Lộ trình bàn giao W11/W12**: Trong W11 (Mock), tôi chủ động để header `Authorization` là `Optional` để các team khác dễ dàng dùng Postman/curl test thử. Sang W12 (Real), việc chặn SigV4 sẽ do infra của CDO lo.
- **Data Schema chuẩn chỉ**: Định nghĩa rõ input/output khớp 1-1 với Pydantic models (ví dụ: bắt buộc `signal_window` >= 120 điểm, chuẩn thời gian RFC3339).
- **Audit Log & Rate Limiting**: Chốt luôn 6 trường bắt buộc cho Audit log, quy định rate limit rõ ràng (600 req/phút/tenant) và định nghĩa các mã lỗi HTTP (400, 401, 422, 429, 503) kèm cách xử lý cụ thể.

---

## 2. Các quyết định thiết kế quan trọng

### Tại sao lại đẩy SigV4 ra Edge thay vì check trong code?
Vì engine nằm sau lớp Private ALB, bản thân ranh giới mạng đã là một lớp bảo vệ. Nếu code ứng dụng cũng verify chữ ký thì thành ra làm hai lần, vừa dư thừa vừa dễ gây nhầm lẫn về việc "ai là người chịu trách nhiệm chặn request". Đẩy ra tầng infra giúp AI engine chỉ tập trung làm đúng việc của nó là xử lý data. Đổi lại, tôi thiết lập Security Group chỉ cho nhận traffic từ CDO SGs để bù đắp rủi ro.

### Bố trí `Authorization` là Optional trong W11
Đây là một quyết định thuần túy vì trải nghiệm của Developer (DX) bên CDO. Giai đoạn mock testing mà bắt họ phải setup tool tạo chữ ký SigV4 chỉ để gọi API thì quá tốn thời gian. Tôi ghi rõ trong hợp đồng việc này để họ yên tâm test, và cũng báo trước là sang W12 infra sẽ siết lại.

### Đóng băng hợp đồng (Freeze)
Ngay khi chốt xong vào ngày 25/06/2026, tôi dán nhãn `FREEZE` vào hợp đồng. Làm API contract sợ nhất là sửa ngầm (ví dụ đổi tên trường) làm chết code client. Việc đóng băng này ép mọi thay đổi phải qua quy trình rõ ràng, giống như cách làm việc ở các team production thực tế.

---

## 3. Nhìn lại: Đánh đổi & Kinh nghiệm rút ra

**Điểm hài lòng:**
Chiến lược phân đoạn W11/W12 rất hiệu quả. Các team CDO không cần sửa một dòng code nào khi chuyển từ engine giả lập sang engine thật vì schema API hoàn toàn đồng nhất. Cả 9 test cases trong `tests/test_api.py` cũng chạy qua trơn tru và tuân thủ đúng các error codes đã chốt.

**Sự đánh đổi:**
Tôi quyết định cứng rắn việc bắt buộc input phải có tối thiểu 120 data points (nếu ít hơn trả về lỗi 422). Vài team CDO than phiền vì lúc cold-start họ chưa gom đủ data. Dù vậy, tôi vẫn giữ nguyên vì thuật toán EWMA thực sự cần chừng đó điểm để không bị báo động giả (False Positive).

**Nếu được làm lại, tôi sẽ sửa gì?**
- **Thêm tính năng Dry-run**: Sẽ rất tiện nếu có thêm cờ `dry_run` trong request để CDO tự test format data mà không kích hoạt xử lý hay ghi log thật.
- **Đặt tên biến rõ ràng hơn**: Trường `from_to` trong recommendation hơi gây lú. Có người đọc vào tưởng là scale bản thân con AI engine, trong khi ý tôi là khuyên CDO scale service của họ. Nếu đặt là `target_from_to` thì sẽ đỡ phải giải thích nhiều.

---

## 4. Tự đánh giá chung
Tài liệu hợp đồng API đã làm tốt vai trò "chốt chặn". Nó sống sót qua cả hai phase W11 và W12 mà không cần phải đập đi xây lại. Mã nguồn hiện tại bám sát 100% hợp đồng này.

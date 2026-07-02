# KỊCH BẢN THUYẾT TRÌNH CHI TIẾT: FORESIGHT LENS
*Tài liệu hướng dẫn thuyết trình từng slide phục vụ buổi bảo vệ Capstone XBrain - Task Force 4 (AIO-03)*

---

## PHẦN 1: MỞ ĐẦU & BỐI CẢNH KHÁCH HÀNG (SLIDE 1 - 4)

### Slide 1: Slide Tiêu Đề
*   **Tiêu đề:** Foresight Lens — Hệ thống dự đoán cạn kiệt tài nguyên cho dịch vụ đám mây Tier 1.
*   **Nội dung hiển thị:** Tên dự án, đội ngũ Task Force 4 (AIO-03), các chỉ số chính (Lead time &ge; 15 min, Token cost ~$0, model ewma-stl-v1) và biểu đồ kiểm soát EWMA minh họa.
*   **Lời thoại đề xuất:**
    > "Kính chào Hội đồng và các bạn. Hôm nay, Task Force 4 xin phép được trình bày dự án **Foresight Lens** — Hệ thống dự đoán sớm nguy cơ cạn kiệt tài nguyên (capacity exhaustion) dành cho các dịch vụ đám mây Tier 1. Khác với các hệ thống cảnh báo tĩnh thông thường, Foresight Lens được thiết kế để dự báo trước sự cố ít nhất 15 phút, với chi phí vận hành tiệm cận 0 USD nhờ mô hình toán học thống kê tối ưu mà không phụ thuộc vào các API mô hình ngôn ngữ lớn đắt đỏ."
*   **Core Message:** Khẳng định ngay giải pháp là hệ thống dự đoán bằng toán học thực tế, chi phí siêu rẻ và hiệu quả cao.

---

### Slide 2: Phân Phần 2 — Bối cảnh khách hàng
*   **Tiêu đề:** 02. CLIENT CONTEXT — Khi màn hình giám sát chuyển sang màu đỏ, mọi sự đã quá muộn.
*   **Nội dung hiển thị:** Slide phân phần tối giản, trích dẫn triết lý vận hành.
*   **Lời thoại đề xuất:**
    > "Chúng ta sẽ bắt đầu với Phần 2: Bối cảnh khách hàng. Trong vận hành SRE thực tế, khi các hệ thống giám sát truyền thống chuyển sang màu đỏ báo động, tức là thảm họa sập dịch vụ đã xảy ra. Khách hàng của chúng tôi cần một cách tiếp cận hoàn toàn khác."

---

### Slide 3: Bối cảnh chi tiết & Yêu cầu của CDO Platform
*   **Tiêu đề:** CLIENT CONTEXT — 8 Core Requirements
*   **Nội dung hiển thị:** Trích dẫn từ phỏng vấn khách hàng tuần 11: *"Khi màn hình chuyển đỏ, hệ thống đã sập. Chúng tôi cần dự báo sớm để SRE can thiệp, nhưng công cụ không được tự ý hành động và chi phí dưới $200/tháng"*. Bảng 3 ràng buộc chính: Dưới $200, Vai trò Cố vấn (Advise), Giám sát 3 dịch vụ chính.
*   **Lời thoại đề xuất:**
    > "Trong buổi phỏng vấn tuần 11, Giám đốc nền tảng dữ liệu (CDO Platform) đã nhấn mạnh: Họ cần dự báo trước sự cố đủ sớm để kỹ sư SRE kịp can thiệp thủ công. Họ tuyệt đối không tin tưởng để một hệ thống tự động can thiệp (Auto-Remediation) tự ý khởi động lại server vì rủi ro gây sập dây chuyền. Ngoài ra, ngân sách vận hành công cụ này phải nằm dưới $200/tháng cho cả 3 dịch vụ lõi: Payment Gateway, Fraud Detector và Ledger."

---

### Slide 4: Ranh giới dự án (Out of Scope)
*   **Tiêu đề:** PROJECT BOUNDARY — Out of Scope (Client Confirmed)
*   **Nội dung hiển thị:** 3 điểm Out of Scope: Auto-Remediation, LLM/Generative AI in Hot Path, Dynamic Baseline Retraining.
*   **Lời thoại đề xuất:**
    > "Để đảm bảo tính khả thi và an toàn tuyệt đối, chúng tôi và khách hàng đã thống nhất ranh giới dự án: Thứ nhất, không tự động can thiệp cấu hình. Thứ hai, không sử dụng Generative AI hay LLM trong luồng suy luận thời gian thực để tránh độ trễ cao và ảo giác. Thứ ba, không tự động huấn luyện lại baselines trong thời gian thực để tránh nhiễm độc dữ liệu baseline."

---

## PHẦN 2: ĐẶT VẤN ĐỀ & THỰC TẾ VẬN HÀNH (SLIDE 5 - 7)

### Slide 5: Phân Phần 3 — Đặt Vấn Đề
*   **Tiêu đề:** 03. THE PROBLEM — Các ngưỡng tĩnh truyền thống cảnh báo quá trễ.
*   **Nội dung hiển thị:** Slide phân phần đặt vấn đề.
*   **Lời thoại đề xuất:**
    > "Tiếp theo là Phần 3: Đặt Vấn Đề. Chúng tôi sẽ phân tích tại sao các công cụ giám sát hiện tại của khách hàng không thể giải quyết bài toán cạn kiệt tài nguyên."

---

### Slide 6: 4 Yếu tố thúc đẩy sự dịch chuyển sang Cảnh báo dự báo
*   **Tiêu đề:** 4 Factors Driving the Shift to Predictive Alerts.
*   **Nội dung hiển thị:** 4 yếu tố: Cạn kiệt thầm lặng (Silent Exhaustion), Tính thụ động, Chi phí công cụ AIOps trên thị trường quá đắt đỏ, Sự e dè đối với hệ thống tự động.
*   **Lời thoại đề xuất:**
    > "Có 4 yếu tố thúc đẩy sự dịch chuyển này: Một là cạn kiệt thầm lặng (như rò rỉ bộ nhớ, nghẽn pool kết nối) diễn ra chậm nhưng sập đột ngột. Hai là các ngưỡng tĩnh cảnh báo ở mức 99% không cho SRE thời gian phản ứng. Ba là các công cụ thương mại ngốn ngân sách vượt xa mức $200/tháng. Bốn là sự e ngại của SRE đối với các hành động tự động hóa không có sự phê duyệt của con người."

---

### Slide 7: Minh họa thực tế — Sự cố cạn kiệt thầm lặng (Silent Exhaustion)
*   **Tiêu đề:** HARSH REALITY — Illustration: Silent Exhaustion Incident.
*   **Nội dung hiển thị:** Biểu đồ mô phỏng 3 tiếng rò rỉ bộ nhớ. Cảnh báo tĩnh chỉ kích hoạt ở phút thứ 180 khi đã chạm ngưỡng 99% và gây sập hệ thống.
*   **Lời thoại đề xuất:**
    > "Đây là biểu đồ minh họa một sự cố rò rỉ bộ nhớ thực tế. Dữ liệu trôi dạt liên tục trong suốt 3 tiếng đồng hồ, nhưng các ngưỡng tĩnh truyền thống hoàn toàn mù lòa cho đến phút thứ 180 — thời điểm RAM chạm ngưỡng 99%. Lúc này SRE nhận được cảnh báo thì hệ thống đã sập hoàn toàn, thời gian phản ứng bằng 0."

---

## PHẦN 3: KẾT QUẢ ĐẠT ĐƯỢC (SLIDE 8 - 12)

### Slide 8: Phân Phần 4 — Kết Quả Đạt Được
*   **Tiêu đề:** 04. RESULTS — Dự đoán sớm, khuyến nghị rõ ràng, không tự ý hành động.
*   **Nội dung hiển thị:** Slide phân phần kết quả.
*   **Lời thoại đề xuất:**
    > "Chúng ta chuyển sang Phần 4: Kết Quả Đạt Được. Foresight Lens đã hoàn thành xuất sắc toàn bộ các chỉ tiêu cam kết ban đầu."

---

### Slide 9: Kết quả 1/4 — Lead Time 106 phút
*   **Tiêu đề:** MEASURABLE OUTCOMES (1/4) — 106 Minutes Lead Time.
*   **Nội dung hiển thị:** Kết quả thực tế đạt 106 phút thời gian cảnh báo sớm trước khi xảy ra sập dịch vụ (vượt xa mức tối thiểu 15 phút cam kết).
*   **Lời thoại đề xuất:**
    > "Chỉ số đầu tiên: Thời gian cảnh báo sớm đạt **106 phút** trên tập holdout thử nghiệm rò rỉ bộ nhớ. Nghĩa là chúng tôi cung cấp cho đội ngũ SRE gần 2 tiếng đồng hồ để kiểm tra mã nguồn, tìm vị trí rò rỉ và chủ động scale-up, thay vì chỉ 15 phút như yêu cầu ban đầu."

---

### Slide 10: Kết quả 2/4 — Cô lập đa thuê (3 Tenants Isolated)
*   **Tiêu đề:** MEASURABLE OUTCOMES (2/4) — 3 Isolated Tenants.
*   **Nội dung hiển thị:** Minh họa 3 tenants (Alpha, Beta, Gamma) được cô lập dữ liệu tuyệt đối ở mức lưu trữ baseline trên S3 và xử lý RAM.
*   **Lời thoại đề xuất:**
    > "Chỉ số thứ hai: Cô lập hoàn toàn 3 tenants (Alpha, Beta, Gamma). Mỗi tenant có một bộ baseline huấn luyện riêng biệt lưu trên S3 và được mã hóa KMS. Luồng xử lý dữ liệu thời gian thực được phân tách hoàn chỉnh, đảm bảo không xảy ra rò rỉ dữ liệu chéo giữa các khách hàng."

---

### Slide 11: Kết quả 3/4 — Chi phí Token bằng $0 (Zero Token Cost)
*   **Tiêu đề:** MEASURABLE OUTCOMES (3/4) — $0 Token Cost.
*   **Nội dung hiển thị:** Chi phí suy luận thực tế bằng $0 nhờ chạy mô hình toán học thống kê cục bộ. Tổng TCO cả hệ thống chỉ khoảng $53/tháng.
*   **Lời thoại đề xuất:**
    > "Chỉ số thứ ba: Chi phí suy luận bằng **0 USD**. Do không sử dụng mô hình ngôn ngữ lớn (LLM) trong luồng phân tích thời gian thực mà sử dụng mô hình toán học thống kê tối ưu, chúng tôi hoàn toàn loại bỏ chi phí token. Toàn bộ hạ tầng AWS chạy thực tế chỉ tốn khoảng **$53/tháng**, chiếm 26.5% ngân sách giới hạn của khách hàng."

---

### Slide 12: Kết quả 4/4 — Khuyến nghị chuẩn 5 thành phần
*   **Tiêu đề:** MEASURABLE OUTCOMES (4/4) — 5 Action Components.
*   **Nội dung hiển thị:** Cấu trúc khuyến nghị chuẩn bao gồm: Action, Target, Value Transition, Confidence, và Evidence Link.
*   **Lời thoại đề xuất:**
    > "Chỉ số thứ tư: Mỗi khuyến nghị gửi sang CDO Platform đều đóng gói đầy đủ 5 thành phần nghiệp vụ: Hành động đề xuất (ví dụ: SCALE_UP), Đối tượng tác động (payment-gw CPU), Biên độ trôi dạt (40% -> 94%), Độ tin cậy toán học (ví dụ: 95.8%), và Đường dẫn liên kết bằng chứng để kỹ sư SRE nhấp vào xem chi tiết."

---

## PHẦN 4: PHƯƠNG PHÁP & THUẬT TOÁN (SLIDE 13 - 23)

### Slide 13: Phân Phần 5 — Phương pháp & Cơ sở thuật toán
*   **Tiêu đề:** 05. METHODOLOGY & RATIONALE — Tại sao chúng tôi thiết kế hệ thống như vậy.
*   **Nội dung hiển thị:** Slide phân phần phương pháp thuật toán.
*   **Lời thoại đề xuất:**
    > "Chúng ta chuyển sang Phần 5: Phương pháp & Cơ sở thuật toán. Đây là phần mô tả chi tiết chiều sâu nghiên cứu toán học và kiểm thử thực tế của dự án."

---

### Slide 14: Sinh dữ liệu huấn luyện (Synthetic Baseline Generation)
*   **Tiêu đề:** ALGORITHMIC RATIONALE · PRE-FLIGHT — Synthetic Baseline Generation.
*   **Nội dung hiển thị:** Quá trình sinh dữ liệu 7 ngày, tần suất 1 phút. Khử chu kỳ STL (ngày 0-5) và tiêm 4 kịch bản lỗi vào ngày 6 (holdout set).
*   **Lời thoại đề xuất:**
    > "Để huấn luyện mô hình khi không có dữ liệu sản xuất thật của khách hàng, chúng tôi đã xây dựng một bộ mô phỏng dữ liệu lịch sử 7 ngày với độ phân giải 1 phút. Dữ liệu bao gồm các hình thái tải ngày/đêm và tải tuần thực tế. Chúng tôi tách biệt hoàn toàn **Ngày 6** làm tập Holdout đánh giá độc lập và tiêm vào đó 4 kịch bản lỗi phổ biến nhất."

---

### Slide 15: Mô phỏng dựa trên Lịch sử sự cố (Step 0A - Historical Outages)
*   **Tiêu đề:** ALGORITHMIC RATIONALE · STEP 0A — Grounding tests in Historical Outages.
*   **Nội dung hiển thị:** Bản đồ tiêm lỗi dựa trên 4 nguyên nhân gốc rễ lịch sử: CPU Core Exhaustion, Memory Leak, DB Connection Pool Exhaustion, và API Latency Spike.
*   **Lời thoại đề xuất:**
    > "Chúng tôi không tự nghĩ ra các kịch bản kiểm thử ngẫu nhiên. Task Force 4 đã ánh xạ trực tiếp các bài test vào 4 sự cố lịch sử nghiêm trọng nhất của khách hàng bao gồm: cạn kiệt nhân CPU, rò rỉ bộ nhớ, nghẽn pool kết nối cơ sở dữ liệu, và tăng vọt độ trễ API do lỗi bên thứ ba."

---

### Slide 16: Nhận diện bẫy chỉ số trễ (Step 0B - Visualizing the Lagging Trap)
*   **Tiêu đề:** ALGORITHMIC RATIONALE · STEP 0B — Visualizing the Lagging Trap.
*   **Nội dung hiển thị:** Biểu đồ so sánh độ trễ phản ứng giữa các chỉ số. Cho thấy API Latency và Queue Depth tăng vọt rất sớm, trong khi CPU và Memory phản ứng cực kỳ trễ.
*   **Lời thoại đề xuất:**
    > "Trong quá trình phân tích hành vi sự cố, chúng tôi phát hiện ra **Bẫy chỉ số trễ (Lagging Trap)**. Biểu đồ này chứng minh: Khi có lỗi nghẽn hệ thống, chỉ số API Latency và Queue Depth lập tức tăng vọt ở phút thứ 15. Tuy nhiên, chỉ số CPU và Memory (vốn là các chỉ số khách hàng thường dùng để cảnh báo) vẫn đi ngang phẳng lặng và chỉ tăng vọt sát thời điểm sập. Nếu chỉ giám sát CPU/Memory, SRE chắc chắn sẽ phát hiện muộn."

---

### Slide 17: Đánh giá độ ưu tiên của chỉ số (Step 0B Cont.)
*   **Tiêu đề:** ALGORITHMIC RATIONALE · STEP 0B (CONT.) — Metric Priority Assessment.
*   **Nội dung hiển thị:** Bảng xếp hạng thứ tự phát hiện lỗi của 7 chỉ số trên 4 kịch bản sự cố.
*   **Lời thoại đề xuất:**
    > "Chúng tôi thực hiện đánh giá độ ưu tiên phát hiện của cả 7 chỉ số đối với từng loại lỗi. Bảng phân tích này chỉ ra chỉ số nào nhạy bén nhất với lỗi nào, giúp tối ưu hóa trọng số của thuật toán dự báo."

---

### Slide 18: Chứng minh Toán học về Độ ưu tiên chỉ số (Step 0C)
*   **Tiêu đề:** ALGORITHMIC RATIONALE · STEP 0C — Mathematical Proof of Priority.
*   **Nội dung hiển thị:** Công thức tính tổng hạng $R_m$ và kết luận toán học: CPU và Memory xếp hạng trễ nhất (hạng 5 và 6), trong khi Queue Depth và Latency xếp hạng sớm nhất (hạng 1.5 và 2).
*   **Lời thoại đề xuất:**
    > "Để thuyết phục khách hàng bằng toán học định lượng, chúng tôi tính toán tổng hạng phát hiện $R_m$. Kết quả chứng minh không thể chối cãi: Queue Depth và API Latency là hai chỉ số nhạy bén nhất (đạt hạng 1.5 và 2.0). CPU và Memory xếp cuối bảng về tốc độ phản ứng. Đây là cơ sở cốt lõi để Foresight Lens ưu tiên giám sát các chỉ số dẫn đầu (leading metrics)."

---

### Slide 19: Khử tính chu kỳ bằng phân tách STL (Step 1)
*   **Tiêu đề:** ALGORITHMIC RATIONALE · STEP 1 — De-seasonalise: STL Decomposition.
*   **Nội dung hiển thị:** Giải thuật STL (Seasonal and Trend decomposition using Loess). Khử chu kỳ hoạt động ngày/đêm để tránh báo động giả vào giờ cao điểm.
*   **Lời thoại đề xuất:**
    > "Bước 1 của thuật toán là khử chu kỳ bằng STL. Tải của khách hàng tăng mạnh vào 9-11h sáng và 2-4h chiều. Nếu dùng ngưỡng tĩnh, hệ thống sẽ báo động giả liên tục vào giờ cao điểm. STL bóc tách tải thành chu kỳ (Seasonal), xu hướng (Trend) và nhiễu (Residual). Thuật toán chỉ thực hiện dự báo trên phần Xu hướng đã được lọc bỏ chu kỳ."

---

### Slide 20: Dự báo trôi dạt bằng biểu đồ kiểm soát EWMA (Step 2)
*   **Tiêu đề:** ALGORITHMIC RATIONALE · STEP 2 — Detect: The EWMA Radar.
*   **Nội dung hiển thị:** Thuật toán EWMA (Exponentially Weighted Moving Average). Lọc nhiễu gai nhọn và tích lũy sai số trôi dạt chậm (drift) để cảnh báo sớm.
*   **Lời thoại đề xuất:**
    > "Bước 2 là chạy bộ lọc EWMA trên phần dư và xu hướng sau STL. EWMA gán trọng số giảm dần theo hàm mũ cho các dữ liệu quá khứ. Điều này giúp loại bỏ hoàn toàn các gai nhọn nhất thời (nhiễu traffic) nhưng lại cực kỳ nhạy bén với các lỗi trôi dạt chậm như rò rỉ bộ nhớ. Khi đường EWMA vượt quá giới hạn kiểm soát $4\sigma$, hệ thống sẽ kích hoạt cảnh báo cạn kiệt."

---

### Slide 21: Tại sao mô hình Thống kê vượt trội hơn Học máy (ML)
*   **Tiêu đề:** ALGORITHMIC DEFENSE — Why Statistical won over Machine Learning.
*   **Nội dung hiển thị:** Bảng so sánh kết quả thực tế giữa STL+EWMA và Isolation Forest (ML). Mô hình thống kê đạt tỷ lệ báo động giả chỉ 7.1% (vượt qua gate 12%), trong khi Isolation Forest thất bại ở mức 21.4%.
*   **Lời thoại đề xuất:**
    > "Chúng tôi đã thực hiện đánh giá đối chứng nghiêm ngặt với Isolation Forest — một thuật toán học máy phổ biến. Kết quả: Isolation Forest bị lừa bởi các đỉnh tải tự nhiên, gây ra tỷ lệ báo động giả lên tới **21.4%** (thất bại trước yêu cầu của khách hàng). Mô hình STL+EWMA của chúng tôi kiểm soát báo động giả ở mức xuất sắc **7.1%** nhờ bóc tách chu kỳ triệt để trước khi suy luận."

---

### Slide 22: Triết lý thiết kế — Đóng vai trò Cố vấn
*   **Tiêu đề:** ALGORITHMIC RATIONALE · GOVERNANCE — An Advisor, Not an Autonomous Actor.
*   **Nội dung hiển thị:** Giải thích triết lý bảo vệ lòng tin của SRE. Giới thiệu cơ chế Confidence Gating dựa trên Brier Score đạt mức 0.049 cực kỳ tối ưu.
*   **Lời thoại đề xuất:**
    > "Về mặt quản trị, chúng tôi tôn trọng triết lý: Hệ thống làm cố vấn, con người ra quyết định. Để tránh cảnh báo rác làm mệt mỏi kỹ sư SRE, chúng tôi áp dụng bộ hiệu chuẩn xác suất Brier Score (đạt mức cực tốt **0.049**). Nếu độ tin cậy toán học của dự báo dưới 70%, hệ thống tự động hạ cấp khuyến nghị từ SCALE_UP xuống INVESTIGATE để SRE kiểm tra thủ công."

---

### Slide 23: Sơ đồ luồng khuyến nghị (Predictive Advisor Action Loop Diagram)
*   **Tiêu đề:** GOVERNANCE — Predictive Advisor Action Loop.
*   **Nội dung hiển thị:** Sơ đồ luồng khép kín của quyết định cảnh báo từ Ingestion, Inference, Gating, Notification, đến SRE Approval.
*   **Lời thoại đề xuất:**
    > "Đây là sơ đồ trực quan mô tả Vòng lặp khuyến nghị của công cụ. Dữ liệu telemetry thô được đẩy lên, kiểm tra qua bộ lọc Brier Gating. Nếu tin cậy, thông báo được bắn về Slack/PagerDuty dưới dạng nút bấm tương tác. Kỹ sư SRE chỉ cần nhấn 'Approve' để kích hoạt CDO Platform thực thi hành động hạ tầng, đảm bảo kiểm soát hoàn toàn."

---

## PHẦN 5: KIẾN TRÚC & TRIỂN KHAI (SLIDE 24 - 36)

### Slide 24: Phân Phần 6 — Vận hành & Đánh giá thực nghiệm
*   **Tiêu đề:** 06. ENGINEERING & VALIDATION — Kiến trúc để vận hành tin cậy trong sản xuất.
*   **Nội dung hiển thị:** Slide phân phần vận hành kỹ thuật.
*   **Lời thoại đề xuất:**
    > "Chúng ta chuyển sang Phần 6: Vận hành & Đánh giá thực nghiệm. Phần này sẽ chứng minh tính sẵn sàng triển khai thực tế của hệ thống."

---

### Slide 25: Kiến trúc xử lý luồng dữ liệu một chiều (Architecture)
*   **Tiêu đề:** ARCHITECTURE — Unidirectional Data Flow & Stateless Processing.
*   **Nội dung hiển thị:** Sơ đồ 3 Phase: Edge & Validation (API Gateway, Pydantic, Tenant Isolation), Core Processing (STL, EWMA, Brier), và Governance & Audit (SHA-256 hash, KMS encrypt).
*   **Lời thoại đề xuất:**
    > "Foresight Lens được thiết kế theo mô hình xử lý một chiều và không lưu trạng thái (stateless). Độ trễ xử lý cực thấp (dưới 5ms) nhờ tối ưu hóa ma trận bằng thư viện NumPy. Dữ liệu được bảo vệ an toàn ngay tại ranh giới nhờ API Gateway SigV4 và Pydantic validator."

---

### Slide 26: Sơ đồ Kiến trúc giải pháp (System Architecture Diagram)
*   **Tiêu đề:** ARCHITECTURE — System Architecture & Data Flow.
*   **Nội dung hiển thị:** Sơ đồ thiết kế hệ thống chi tiết từ API Client, Gateway, bộ xử lý API đến hệ thống Audit Trail.
*   **Lời thoại đề xuất:**
    > "Sơ đồ kiến trúc giải pháp thể hiện rõ sự phân tách trách nhiệm. Bộ xử lý API nhận telemetry, gọi cấu hình baseline từ bộ đệm, chạy giải thuật toán học và đẩy kết quả khuyến nghị ra ngoài. Đồng thời, một bản ghi nhật ký kiểm toán (Audit Trail) được tự động ghi nhận song song."

---

### Slide 27: Các đường ống vận hành (Pipelines)
*   **Tiêu đề:** PIPELINES — Automated Data & Deployment Pipelines.
*   **Nội dung hiển thị:** Sơ đồ 3 Pipelines: Offline Training (statsmodels STL), Live Inference (POST /v1/predict), và Deployment (Docker, ECS Fargate).
*   **Lời thoại đề xuất:**
    > "Chúng tôi thiết lập 3 đường ống độc lập: Đường ống huấn luyện ngoại tuyến (chạy định kỳ hàng tuần để làm mới baseline); Đường ống suy luận thời gian thực qua API REST của FastAPI; và Đường ống triển khai CI/CD tự động đóng gói ứng dụng vào AWS ECS Fargate."

---

### Slide 28: Hợp đồng giao tiếp hệ thống (API Contracts)
*   **Tiêu đề:** CONTRACTS — Strict API Boundaries & Stable Interfaces.
*   **Nội dung hiển thị:** Chi tiết 3 hợp đồng đã ký kết và đóng băng từ Tuần 11: Telemetry Contract, Inference API Contract, và Deployment Contract.
*   **Lời thoại đề xuất:**
    > "Tính ổn định của hệ thống được đảm bảo bằng 3 hợp đồng phần mềm nghiêm ngặt. Hợp đồng Telemetry quy định rõ cấu trúc dữ liệu gửi lên; hợp đồng API quy định các mã phản hồi và SLA độ trễ; hợp đồng Deployment quy định tài nguyên phần cứng giới hạn (ECS Fargate 0.5 vCPU, 1GB RAM) và giới hạn ngân sách $200."

---

### Slide 29: Sơ đồ triển khai AWS (Serverless Deployment Topology)
*   **Tiêu đề:** DEPLOYMENT — Serverless Deployment Topology.
*   **Nội dung hiển thị:** Sơ đồ mạng AWS VPC, ALB, cụm máy chủ ECS Fargate đặt trong Private Subnets, kết nối với S3 và KMS.
*   **Lời thoại đề xuất:**
    > "Đây là sơ đồ triển khai thực tế trên đám mây AWS. Để đảm bảo an toàn tuyệt đối, cụm container FastAPI được đặt hoàn toàn trong các Private Subnets của VPC, không tiếp xúc trực tiếp với Internet. Dữ liệu baseline lưu trên S3 và log trên CloudWatch đều được mã hóa bằng khóa bảo mật KMS riêng biệt."

---

### Slide 30: Đánh giá chất lượng mô hình trên Holdout Set (Validation)
*   **Tiêu đề:** VALIDATION — Statistical Rigor & Holdout Evaluation.
*   **Nội dung hiển thị:** Các chỉ số đo lường chính thức: Recall 97.1%, False Positive 7.1%, Lead Time 106 phút, Brier Score 0.049, và Confusion Matrix chi tiết.
*   **Lời thoại đề xuất:**
    > "Chúng tôi đánh giá chất lượng mô hình trên tập Holdout gồm 790 cửa sổ dữ liệu của cả 3 dịch vụ. Các chỉ số đều vượt xa yêu cầu: Tỷ lệ bắt lỗi (Recall) đạt **97.1%**, tỷ lệ báo động giả khống chế ở mức cực thấp **7.1%** và chỉ số hiệu chuẩn xác suất Brier đạt **0.049**."

---

### Slide 31: Bộ kiểm thử tự động (Quality Assurance)
*   **Tiêu đề:** QUALITY ASSURANCE — Automated Test Suite & API Verification.
*   **Nội dung hiển thị:** Danh sách 9/9 ca kiểm thử tự động (pytest) màu xanh PASS và ảnh chụp log audit log mã hóa thực tế.
*   **Lời thoại đề xuất:**
    > "Mã nguồn của Foresight Lens được bảo vệ bằng bộ unit test và integration test tự động gồm **9 kịch bản kiểm thử**. Bộ test này kiểm tra toàn bộ các trường hợp dữ liệu bình thường, rò rỉ bộ nhớ, tăng tải đột biến, lỗi định dạng đầu vào và kiểm tra cô lập tenant."

---

### Slide 32: Kiểm thử hiệu năng chịu tải (Performance Validation)
*   **Tiêu đề:** PERFORMANCE VALIDATION — Load Test: 400 RPS with Zero Errors.
*   **Nội dung hiển thị:** Dữ liệu stress test thực tế: 100 RPS đạt p99 latency 4.01ms; 400 RPS (stress test gấp 4 lần SLA) đạt p99 latency 2.71ms với 0% lỗi.
*   **Lời thoại đề xuất:**
    > "Về hiệu năng, hợp đồng yêu cầu hệ thống chịu được tải 100 requests/giây (RPS). Chúng tôi đã chạy stress test lên tới **400 requests/giây (gấp 4 lần yêu cầu)**. Kết quả: Tỷ lệ lỗi bằng 0%, độ trễ phản hồi p99 chỉ vỏn vẹn **2.71ms** nhờ thuật toán xử lý vector hóa NumPy siêu tốc."

---

### Slide 33: Tối ưu hóa chi phí hạ tầng (FinOps)
*   **Tiêu đề:** FINOPS — Flat-Rate Serverless Economics.
*   **Nội dung hiển thị:** Phân tích chi tiêu AWS thực tế: Tổng cộng **$53/tháng** (ALB: $16, Fargate: $36, S3 & KMS: $1).
*   **Lời thoại đề xuất:**
    > "Về khía cạnh tối ưu chi phí (FinOps), do mô hình chạy không tốn token, chúng tôi chỉ trả tiền thuê hạ tầng AWS Fargate tĩnh và ALB. Tổng chi phí đo lường thực tế chỉ là **$53/tháng**, giúp khách hàng tiết kiệm được 73.5% ngân sách dự kiến ($200/tháng)."

---

### Slide 34: Quy trình onboarding dịch vụ mới (Operability)
*   **Tiêu đề:** OPERABILITY — 28-Minute Service Onboarding.
*   **Nội dung hiển thị:** 4 bước onboarding dịch vụ mới: Register (5m), Load 7d data (10m), Train baseline (10m), và Validate (3m). Tổng cộng dưới 30 phút.
*   **Lời thoại đề xuất:**
    > "Khả năng vận hành thực tế được chứng minh qua quy trình onboarding cực nhanh. Kỹ sư SRE chỉ mất tối đa **28 phút** để khai báo cấu hình, tải dữ liệu lịch sử từ S3, huấn luyện baseline ban đầu và kích hoạt giám sát cho một microservice mới."

---

### Slide 35: Cơ chế bảo mật và an toàn (Predictive Governance)
*   **Tiêu đề:** PREDICTIVE GOVERNANCE — Security-by-Design & Defense in Depth.
*   **Nội dung hiển thị:** 6 lớp bảo mật: Deterministic output, Confidence gating, Traceable audit, Fail-open degrade, Context isolation, và DoS protection.
*   **Lời thoại đề xuất:**
    > "Foresight Lens được thiết kế an toàn từ gốc. Do là mô hình toán học thuần túy, chúng tôi hoàn toàn loại bỏ các nguy cơ an ninh mạng của Generative AI như tấn công tiêm mã lệnh (Prompt Injection) hay dữ liệu ảo giác. Hệ thống tuyệt đối an toàn và có thể kiểm chứng toán học."

---

### Slide 36: Các quyết định kiến trúc cốt lõi (ADRs)
*   **Tiêu đề:** TRADE-OFFS — Architecture Decision Records (ADRs).
*   **Nội dung hiển thị:** Tóm tắt 6 bản ghi quyết định kiến trúc từ ADR-001 đến ADR-006.
*   **Lời thoại đề xuất:**
    > "Để lưu trữ tri thức cho các đội ngũ phát triển tương lai, chúng tôi ghi nhận đầy đủ 6 quyết định kiến trúc cốt lõi (ADRs) giải thích tường minh lý do chọn mô hình toán học thay vì mô hình ngôn ngữ lớn (LLM), lý do chọn ngưỡng confidence 0.7 và bộ tham số EWMA."

---

## PHẦN 6: KẾT LUẬN & PHỤ LỤC (SLIDE 37 - 40)

### Slide 37: Slide Kết Luận (Closing Slide)
*   **Tiêu đề:** ACHIEVEMENTS — Surpassed all stringent Client requirements, exceeding expectations.
*   **Nội dung hiển thị:** Các cột mốc đạt được: Chi phí ~$36 (hạ tầng compute), 3 hợp đồng ký kết, 9/9 tests pass, lead time 106 phút.
*   **Lời thoại đề xuất:**
    > "Tổng kết lại, Foresight Lens đã bàn giao một ứng dụng FastAPI hoàn chỉnh chạy trên AWS Fargate, đáp ứng vượt trội toàn bộ các yêu cầu khắt khe của khách hàng cả về tốc độ cảnh báo, độ an toàn đa thuê lẫn tối ưu hóa chi phí. Hệ thống đã sẵn sàng đưa vào vận hành thực tế. Cảm ơn Hội đồng đã lắng nghe."
*   **Core Message:** Khép lại bài thuyết trình tự tin, khẳng định hệ thống chạy thực tế thành công tốt đẹp.

---

### Slide 38: Phụ Lục A — EWMA Parameter Grid Search (Hỏi & Đáp)
*   **Tiêu đề:** APPENDIX A — EWMA Parameter Grid Search.
*   **Nội dung hiển thị:** Bảng quét tham số alpha và K, giải thích điểm tối ưu hóa Sweet Spot.
*   **Lời thoại đề xuất:**
    > "Đây là slide phụ lục phục vụ phần Q&A. Nếu Hội đồng có câu hỏi về việc tối ưu hóa tham số kiểm soát EWMA, đây là dữ liệu Grid Search chứng minh việc lựa chọn $\alpha=0.3$ và $K=4.0$ giúp cân bằng hoàn hảo giữa việc bắt lỗi (Recall) và lọc báo động giả."

---

### Slide 39: Phụ Lục B — Telemetry Signal Categorization (Hỏi & Đáp)
*   **Tiêu đề:** APPENDIX B — Telemetry Signal Categorization.
*   **Nội dung hiển thị:** Bảng phân chia 4 chỉ số có chu kỳ chạy STL và 3 chỉ số phẳng fallback chạy Z-score động.
*   **Lời thoại đề xuất:**
    > "Slide phụ lục B giải thích chi tiết cách phân loại 7 chỉ số đầu vào. Đối với các chỉ số có chu kỳ hoạt động rõ rệt, hệ thống dùng STL để khử nhiễu tải. Đối với các chỉ số phẳng như hàng đợi kết nối, hệ thống tự động sử dụng Z-score để tránh gây nhiễu cho mô hình."

---

### Slide 40: Phụ Lục C — API Incident & Error Contract (Hỏi & Đáp)
*   **Tiêu đề:** APPENDIX C — API Incident & Error Contract.
*   **Nội dung hiển thị:** Bảng quy định chi tiết 5 mã lỗi HTTP chuẩn mực phục vụ cơ chế tự bảo vệ Fail-Open của CDO Platform.
*   **Lời thoại đề xuất:**
    > "Slide phụ lục C mô tả hợp đồng xử lý sự cố API. Để đảm bảo hệ thống lõi của khách hàng không bao giờ bị ảnh hưởng, chúng tôi thiết kế cơ chế Fail-Open tự động. Nếu công cụ gặp sự cố và trả về mã lỗi 503, CDO Platform sẽ tự động bỏ qua công cụ và dùng các quy tắc tĩnh cục bộ."

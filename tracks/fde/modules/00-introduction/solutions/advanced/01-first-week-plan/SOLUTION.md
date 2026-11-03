# Lời giải: Kế hoạch tuần đầu tại khách

Không có đáp án duy nhất. Dưới đây là hướng làm, các quyết định cần cân nhắc, rubric và một bản mẫu rút gọn.

## Hướng làm

1. **Đọc thông tin máy như một preflight.** So với nhu cầu của bundle quillo (khoảng 1,1 GB tar, giải nén và nạp image
   cần thêm vài GB, Postgres + model GGUF): đĩa 8 GB là rủi ro số một; proxy soi HTTPS làm mọi lệnh kéo gói/image lỗi
   chứng chỉ; không có plugin compose nghĩa là `docker compose up` không chạy. Đây là những thứ **biết trước**, phải xử
   lý bằng yêu cầu gửi trước chứ không phải phát hiện vào thứ Hai.
2. **Neo lịch vào ràng buộc cứng.** Anh Tuấn chỉ có chiều thứ Ba, thứ Năm; mọi thay đổi hệ thống chỉ trong tối thứ Năm.
   Vậy tách hai loại việc. Thứ **xin trước** chỉ là những gì không đổi máy: tệp CA của proxy, quy trình mang bundle vào,
   duyệt dữ liệu, sponsor xác nhận mục tiêu, và **đặt lịch** cửa sổ thứ Năm kèm change request (mở rộng đĩa, trust CA,
   cài quillo) theo quy trình change của IT. Mọi thay đổi trên máy, kể cả mở rộng đĩa, nằm trong cửa sổ thứ Năm 20:00–22:00
   đã đặt. Thứ Hai, thứ Tư làm những thứ không cần đổi hệ thống: khảo sát, discovery với chị Lan, diễn tập trên lab, chuẩn
   bị bộ câu hỏi đánh giá.
3. **Định nghĩa lại "chạy thử được" cùng sponsor.** Hai nghĩa rất khác nhau: dịch vụ lên và trả lời `/healthz`, hay người
   dùng thật hỏi câu thật và nhận câu trả lời có trích dẫn đúng. Kế hoạch đề xuất một định nghĩa đo được và xin sponsor
   xác nhận trước khi đến.
4. **Bundle offline thay vì kéo qua proxy.** Mang bundle đã ký và có manifest sha256 vào theo quy trình của viện (USB
   được duyệt, hay kho nội bộ), kiểm manifest tại chỗ. Proxy TLS inspection vẫn phải xử lý nếu có bước nào cần ra ngoài,
   nhưng không để cả tuần phụ thuộc vào nó.
5. **Dữ liệu không rời viện.** Pháp chế/ATTT duyệt tập tài liệu pilot trước (một khoa, vài trăm tệp), không phải cả
   3 000 tệp ngày đầu. Bản scan cần OCR là rủi ro chất lượng; nói rõ trong rủi ro.
6. **Báo tin xấu sớm.** Status ngắn cuối mỗi ngày (đã xong, chặn bởi gì, cần ai), và một quy tắc: chặn quá nửa ngày
   thì báo sponsor, không chờ thứ Sáu.

## Bản mẫu rút gọn

**Mục tiêu tuần 1**

1. quillo chạy trên VM của viện từ bundle offline, khởi động lại máy vẫn tự lên, `/healthz` trả 200.
2. Nạp 300 tài liệu quy trình của khoa Nội (đã được ATTT duyệt); chị Lan hỏi 30 câu thật, ít nhất 20 câu có câu trả lời
   đúng kèm trích dẫn đúng tài liệu (chị Lan chấm).
3. Danh sách khoảng cách cho giai đoạn tiếp theo (đĩa, OCR bản scan, SSO) kèm ước lượng.

**Cần viện chuẩn bị trước** (gửi thứ Sáu tuần trước khi đến; trong tài liệu thật ghi ngày cụ thể). Không mục nào đòi
thay đổi máy trước cửa sổ thứ Năm; hạn chót đặt theo ngày việc đó thật sự cần, không dồn hết vào "trước thứ Hai":

| Việc | Người phụ trách | Hạn | Vì sao |
| --- | --- | --- | --- |
| Đặt cửa sổ thứ Năm 20:00–22:00 tuần 1 cho pilot và mở change request: mở rộng đĩa VM lên ≥ 40 GB (hoặc gắn ổ dữ liệu), trust CA proxy, cài quillo | anh Tuấn | change request vào hàng chờ thứ Hai, duyệt trước thứ Tư | 8 GB (≈7 GB trống) dưới mức tối thiểu 10 GB của quillo; mọi thay đổi máy chỉ được làm trong cửa sổ |
| Xác nhận định nghĩa "chạy thử được" (mục tiêu 1–2) | Phó giám đốc vận hành | buổi kick-off sáng thứ Hai | Tránh hiểu lệch lời hứa của sales |
| Cho biết quy trình mang bundle vào (USB quét virus, kho nội bộ) và ai duyệt | anh Tuấn, ATTT | thứ Ba | Không phụ thuộc proxy để kéo image; bundle phải có trên máy trước tối thứ Năm |
| Gửi tệp CA của proxy (PEM), chỉ đọc, chưa cài | anh Tuấn | thứ Ba | Để diễn tập trust CA trên lab thứ Tư trước khi làm thật thứ Năm |
| Duyệt tập 300 tài liệu khoa Nội cho pilot | Pháp chế, ATTT | thứ Tư | Dữ liệu không rời viện; nạp ngay sau khi cài tối thứ Năm |
| 30 câu hỏi thật kèm tài liệu đúng | chị Lan | thứ Ba | Bộ đánh giá dựng thứ Tư cho mục tiêu 2 |

**Lịch**

| Ngày | Việc chính | Làm cùng | Đầu ra |
| --- | --- | --- | --- |
| Thứ Hai | Khảo sát máy không đổi gì (OS, đĩa, mạng, proxy, quyền), kiểm bundle theo manifest, ngồi cùng chị Lan xem cách tra quy trình hiện tại | chị Lan | Báo cáo khảo sát, ghi chú workflow, status cuối ngày |
| Thứ Ba | Chiều: với anh Tuấn rà kế hoạch thay đổi cho tối thứ Năm (đĩa, plugin compose hay cách chạy thay thế, CA), diễn tập trên VM lab cùng hồ sơ | anh Tuấn | Change plan được duyệt, kế hoạch rollback |
| Thứ Tư | Diễn tập cài đầy đủ trên lab có cùng ràng buộc; chuẩn bị bộ eval từ 30 câu của chị Lan | (một mình) | Bộ eval, log cài thử |
| Thứ Năm | Chiều: kiểm lần cuối với anh Tuấn. Cửa sổ 20:00–22:00: mở rộng đĩa (20:00–20:30), trust CA, cài quillo từ bundle, xác minh; quá 21:30 chưa xong thì rollback theo kế hoạch | anh Tuấn | Dịch vụ lên, nạp 300 tài liệu chạy qua đêm |
| Thứ Sáu | Chạy eval, chị Lan hỏi thử, demo ngắn cho sponsor, thống nhất bước tiếp | chị Lan, sponsor | Kết quả eval, status tuần, danh sách khoảng cách |

**Rủi ro** (ví dụ): change request mở rộng đĩa chưa được duyệt hoặc không làm kịp trong cửa sổ (dấu hiệu: thứ Tư chưa
có phê duyệt; tối thứ Năm 20:30 đĩa chưa lớn hơn → phương án đã diễn tập trên lab đĩa 8 GB thứ Tư: nạp image thẳng từ
USB, không chép tar ra đĩa, chỉ model nhỏ, pilot thu nhỏ 50 tài liệu; vẫn không đủ chỗ thì mục tiêu 1 lùi sang cửa sổ kế
tiếp, báo sponsor ngay tối thứ Năm); bản scan không có lớp text (dấu hiệu: tỉ lệ trang rỗng khi nạp →
tách ra danh sách cần OCR, không tính vào mục tiêu 2); cửa sổ thứ Năm bị huỷ vì sự cố của viện (→ xin cửa sổ dự phòng
thứ Hai tuần sau ngay từ đầu, mục tiêu 1 lùi, mục tiêu 2 làm trên lab bằng tài liệu công khai); ATTT chưa duyệt dữ liệu
(→ không nạp gì, eval trên tài liệu công khai của Bộ Y tế để chứng minh luồng); proxy chặn một bước bắt buộc (→ chỉ
dùng bundle offline, ghi lại để xử lý trust CA trong tuần 2).

**Không làm tuần này**: SSO với AD của viện (cần ATTT, không ảnh hưởng mục tiêu đo được), nạp cả 3 000 tài liệu, tinh
chỉnh prompt theo từng khoa, tích hợp HIS.

## Rubric (20 điểm)

| Tiêu chí | 0 | 2 | 4 |
| --- | --- | --- | --- |
| Mục tiêu đo được | Mục tiêu chung chung ("triển khai hệ thống") | Có số nhưng không rõ ai chấm, chấm thế nào | ≤3 mục, có số, người chấm và tiêu chí; xử lý rõ lời hứa của sales |
| Xin trước những gì cần từ khách | Không có hoặc để tới thứ Hai mới hỏi | Có danh sách nhưng thiếu người hoặc hạn, hoặc đòi đổi máy ngoài cửa sổ | Chỉ xin trước thứ không đổi máy (CA, quy trình mang bundle vào, duyệt dữ liệu, bộ câu hỏi, sponsor xác nhận) cộng đặt cửa sổ + change request cho mọi thay đổi máy; đủ người và hạn thực tế |
| Lịch theo ràng buộc thật | Bỏ qua lịch IT hoặc cửa sổ bảo trì | Có tôn trọng nhưng việc đổi hệ thống rải rác ngoài cửa sổ | Mọi thay đổi hệ thống (cả mở rộng đĩa) trong cửa sổ thứ Năm, có diễn tập, mốc giờ rollback và phương án khi một thay đổi trượt; việc không cần IT xếp quanh đó |
| Rủi ro cụ thể | Rủi ro chung chung | Rủi ro đúng nhưng không có dấu hiệu sớm hoặc phương án | ≥4 rủi ro của máy và tổ chức này (đĩa 8 GB, proxy soi HTTPS, thiếu compose, scan cũ, duyệt dữ liệu, lịch IT) có dấu hiệu và phương án |
| Giao tiếp và won't | Không có báo cáo | Báo cáo cuối tuần | Status cuối ngày, quy tắc báo chặn sớm cho sponsor, danh sách won't có lý do |

Từ 16 điểm trở lên: kế hoạch gửi khách được. Dưới 10: đọc lại phần 3 của lý thuyết rồi viết lại.

## Sai lầm hay gặp

- Viết lịch như thể máy khách giống máy lab: thứ Hai `docker compose up`, thứ Ba demo.
- Coi lời hứa của sales là ràng buộc không đổi được, thay vì đưa sponsor quyết định nghĩa của nó.
- Kế hoạch toàn việc của FDE, không có dòng nào là việc của khách, trong khi phần lớn thứ chặn pilot nằm phía khách.

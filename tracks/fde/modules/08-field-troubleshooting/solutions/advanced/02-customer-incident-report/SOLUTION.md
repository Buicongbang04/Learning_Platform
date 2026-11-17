# Lời giải: báo cáo sự cố gửi khách

## Hướng làm

1. **Lọc ghi chép trước khi viết.** Ba thứ trong `case-notes.md` không bao giờ ra khỏi buổi chat: mảnh token quản trị anh
   IT dán nhầm (chỉ ghi "một thông tin xác thực bị lộ trong kênh chat nội bộ đã được xoay" nếu muốn nhắc, không trích),
   tên và email nhân viên, câu "anh Tuấn chuyển VM" như một nguyên nhân. Việc xoay token là một mục phòng ngừa riêng của
   khách, không cần nêu ai dán.
2. **Nguyên nhân theo bằng chứng.** Đã chứng minh: đồng hồ máy quillo nhanh ~9 phút (`date -u` so với giờ chuẩn), chrony
   không đồng bộ (`Leap status: Not synchronised`, nguồn duy nhất `10.20.0.11` không tới được), nguồn đó đã tắt từ tháng
   trước, máy chuyển sang host mới Chủ nhật; quillo từ chối token với lý do "Signature has expired" từ 07:31; sửa NTP
   xong thì đăng nhập được ngay. Cơ chế: token Keycloak sống 5 phút, quillo cho lệch tối đa 60 s, máy nhanh 9 phút nên
   mọi token mới cấp đều "đã hết hạn" theo đồng hồ của máy. Chưa chứng minh: giờ chuyển host chính xác, vì sao giờ VM
   theo giờ host (giả thuyết của bạn).
3. **Yếu tố góp phần** là điều kiện hệ thống, không phải người: nguồn NTP cũ tắt mà cấu hình máy không đổi theo; không có
   cảnh báo khi chrony mất đồng bộ; preflight lúc cài của nhà cung cấp không kiểm NTP; quillo không báo gợi ý lệch giờ
   khi từ chối token và `/healthz` không kiểm đồng hồ.
4. **Phòng ngừa chỉ cam kết thứ mình kiểm soát.** Khách: nguồn NTP, giám sát đồng bộ giờ, checklist chuyển host, xoay
   token đã lộ. Nhà cung cấp (bạn): thêm kiểm đồng bộ giờ vào preflight/checklist bàn giao (bạn làm được), gửi yêu cầu
   cho đội sản phẩm (bạn làm được việc **gửi**, không hứa tính năng hay ngày phát hành).
5. Ảnh hưởng tính từ dữ liệu: 07:31 (dòng từ chối đầu tiên) tới 09:12 (đăng nhập lại được) ≈ 1 giờ 41 phút; 37 người
   dùng khác nhau đăng nhập Keycloak cho client quillo trong khoảng đó; token quản trị và nạp tài liệu không bị ảnh
   hưởng (23 tài liệu vào, không tệp lỗi).

## Bài mẫu (đạt 20/20)

```markdown
# Báo cáo sự cố: không đăng nhập được quillo bằng tài khoản công ty sáng 09/11/2026

**Gửi:** Trưởng phòng IT · **Từ:** <FDE>, <công ty> · **Ngày:** 11/11/2026 · **Trạng thái:** đã khắc phục

## Tóm tắt

Sáng thứ Hai 09/11, từ 07:31 đến 09:12 (khoảng 1 giờ 40 phút), nhân viên không đăng nhập được trợ lý tài liệu quillo
bằng tài khoản công ty; 37 người đã thử trong thời gian này. Nguyên nhân là đồng hồ của máy chạy quillo bị nhanh 9 phút
sau khi máy được chuyển sang máy chủ vật lý mới cuối tuần, trong khi nguồn giờ chuẩn mà máy được cấu hình để đồng bộ đã
ngừng hoạt động từ tháng trước. Không có dữ liệu nào bị mất; việc nạp tài liệu vẫn chạy bình thường. Hệ thống đã ổn định
từ 09:12 và hai bên đã thống nhất các việc phòng ngừa bên dưới.

## Ảnh hưởng

- Đăng nhập bằng tài khoản công ty (SSO) vào quillo: không dùng được từ 07:31 đến 09:12. 37 người dùng khác nhau đã
  đăng nhập thành công vào hệ thống xác thực của công ty cho quillo nhưng bị quillo từ chối.
- Không bị ảnh hưởng: hệ thống xác thực của công ty và các ứng dụng khác dùng nó; truy cập quản trị quillo; việc nạp tài
  liệu (23 tài liệu được nạp từ 07:00 đến 09:25, không tài liệu nào lỗi).
- Dữ liệu: không mất, không sai lệch.

## Diễn biến (giờ Việt Nam)

| Giờ | Sự kiện |
| --- | --- |
| CN 08/11, khoảng 23:00 | Máy chạy quillo được chuyển sang máy chủ vật lý mới trong đợt bảo trì hạ tầng (giờ chính xác chưa xác định) |
| T2 09/11, 07:31 | quillo bắt đầu từ chối đăng nhập SSO (lý do trong log: token đã hết hạn) |
| 07:42 | Người dùng đầu tiên báo lỗi cho IT |
| 07:55 | IT xác nhận hệ thống xác thực vẫn hoạt động với ứng dụng khác |
| 08:05 | IT mở ticket cho nhà cung cấp |
| 08:20 | Bắt đầu chẩn đoán chung qua cuộc gọi |
| 08:31 | Phát hiện đồng hồ máy quillo nhanh khoảng 9 phút |
| 08:34 | Xác định máy không đồng bộ được với nguồn giờ chuẩn đã cấu hình |
| 08:58 | Đề xuất sửa nguồn giờ; chờ phê duyệt thay đổi trên hệ thống production |
| 09:05 | Thay đổi được phê duyệt |
| 09:07–09:10 | IT cấu hình lại nguồn giờ, đồng hồ được chỉnh, xác nhận đồng bộ |
| 09:12 | Đăng nhập SSO hoạt động trở lại |
| 09:20 | IT xác nhận 12 người dùng thử đều đăng nhập được |

## Nguyên nhân

Khi người dùng đăng nhập, hệ thống xác thực cấp một "vé" có hiệu lực 5 phút; quillo chấp nhận vé nếu đồng hồ của máy
lệch không quá 60 giây. Đồng hồ máy chạy quillo nhanh khoảng 9 phút, nên mọi vé vừa cấp đều bị quillo coi là đã hết hạn.

Đồng hồ lệch vì hai điều kiện gặp nhau:

1. Máy được cấu hình đồng bộ giờ với một nguồn giờ duy nhất đã ngừng hoạt động từ tháng trước khi công ty chuyển sang cụm
   nguồn giờ mới. Từ đó máy không đồng bộ được, nhưng không lệch vì máy chủ vật lý cũ có giờ đúng.
2. Sau khi chuyển sang máy chủ vật lý mới (giờ nhanh khoảng 9 phút), không còn gì chỉnh lại đồng hồ của máy.

Yếu tố góp phần: không có cảnh báo khi máy mất đồng bộ giờ; danh sách kiểm tra lúc cài đặt của chúng tôi không kiểm việc
đồng bộ giờ; quillo không ghi gợi ý về lệch giờ khi từ chối đăng nhập và trang trạng thái không kiểm đồng hồ, nên việc
chẩn đoán mất thêm thời gian.

## Đã khắc phục thế nào

IT cấu hình máy đồng bộ với cụm nguồn giờ mới và chỉnh đồng hồ ngay (09:07–09:10). Đồng hồ hiện lệch dưới 1 mili giây so
với nguồn chuẩn. Không cần thay đổi cấu hình hay khởi động lại quillo.

## Việc phòng ngừa

| Việc | Bên thực hiện | Hạn |
| --- | --- | --- |
| Rà soát mọi máy còn cấu hình nguồn giờ cũ, chuyển sang cụm mới | Công ty (IT) | 20/11/2026 |
| Cảnh báo khi một máy mất đồng bộ giờ quá 5 phút | Công ty (IT) | 30/11/2026 |
| Thêm bước kiểm đồng bộ giờ vào checklist chuyển máy sang máy chủ vật lý khác | Công ty (IT) | 30/11/2026 |
| Xoay thông tin xác thực quản trị của quillo đã bị dán vào kênh chat nội bộ trong lúc xử lý | Công ty (IT), nhà cung cấp hỗ trợ | 13/11/2026 |
| Thêm kiểm đồng bộ giờ vào preflight và checklist bàn giao của chúng tôi, chạy lại cho máy này | Nhà cung cấp (FDE) | 18/11/2026 |
| Gửi đội sản phẩm yêu cầu: ghi gợi ý lệch giờ khi từ chối token, cân nhắc kiểm đồng hồ trong trang trạng thái; báo lại kết quả xem xét | Nhà cung cấp (FDE) | Gửi trước 13/11/2026; cập nhật trong báo cáo định kỳ tháng 12 |

## Điều chưa biết

- Giờ chính xác máy được chuyển sang máy chủ vật lý mới.
- Vì sao đồng hồ của máy nhận giờ của máy chủ vật lý mới khi chuyển (cơ chế của nền tảng ảo hoá); IT đang kiểm với nhà
  cung cấp nền tảng. Việc phòng ngừa ở trên không phụ thuộc vào câu trả lời này.
```

## Rubric chi tiết

| Tiêu chí | Đủ điểm khi | Mất điểm khi |
| --- | --- | --- |
| Tóm tắt (3) | Người không kỹ thuật hiểu: gì, bao lâu, ai, ổn chưa, dữ liệu | Mở đầu bằng chrony, JWT, NTP không giải thích |
| Ảnh hưởng (3) | Số người, khoảng giờ từ log, cái gì vẫn chạy | "Nhiều người", "cả buổi sáng" |
| Timeline (3) | Giờ của khách, có mốc phát hiện, quyết định, khắc phục, xác nhận | Giờ UTC lẫn lộn, thiếu mốc chờ phê duyệt |
| Nguyên nhân (4) | Cơ chế đúng (token 5 phút, lệch cho phép 60 s, đồng hồ nhanh 9 phút), hai điều kiện, yếu tố góp phần, không gọi tên người | "Do IT chuyển máy", "do lỗi người dùng", hay đổ cho Keycloak |
| Phòng ngừa (4) | Mỗi việc có bên và hạn, đúng phạm vi kiểm soát | "Đội sản phẩm sẽ ra bản sửa trong tháng 12" |
| Đã biết/chưa biết (2) | Giả thuyết về hypervisor nằm ở "chưa biết" | Viết giả thuyết thành nguyên nhân |
| Trình bày (1) | Ngắn, cụ thể | Xin lỗi dài, không có nội dung |

Bài mẫu ở trên: không có tên, email, mảnh token nào; việc xoay thông tin xác thực được nêu như một việc của khách mà
không trích hay nói ai dán; mọi con số lấy từ ghi chép (07:31, 09:12, 37, 23, 12); giả thuyết ảo hoá nằm ở mục chưa biết;
cam kết của nhà cung cấp là việc FDE tự làm được (preflight, gửi yêu cầu và báo lại), không hứa tính năng.

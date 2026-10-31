# Lời giải: chọn giao thức theo tình huống

| Câu | Đáp án | Ràng buộc quyết định |
| --- | --- | --- |
| `partner-file-drop` | c. SFTP | Một cổng, có mã hoá, xác thực bằng khoá, dễ tự động hoá |
| `ftps-firewall` | b. Kênh data passive bị chặn | FTP dùng hai kết nối; firewall không đọc được lệnh `PASV` đã mã hoá |
| `smtp-submission-port` | b. 587 STARTTLS hoặc 465 | Submission có xác thực và TLS; 25 là cổng giữa các MTA |
| `imap-vs-pop3` | c. IMAPS | Trạng thái nằm trên server, nhiều thiết bị |
| `greylisting-otp` | a. Greylisting, trễ là bình thường lần đầu | Mã 4xx là tạm thời, MTA đúng sẽ retry |
| `dns-migration-ttl` | b. Hạ TTL trước, đổi, rồi nâng lại | Cache cũ sống bằng TTL cũ |
| `http3-blocked` | b. Rơi về HTTP/2 qua TCP | HTTP/3 được quảng bá qua Alt-Svc/HTTPS record, client tự fallback |
| `ssh-hop` | c. ProxyJump | Bastion không thấy phiên và không mượn được agent |
| `plain-protocols` | a, b, d, e | Chỉ SFTP chạy trong SSH |

## Giải thích từng câu

### `partner-file-drop`: SFTP

SFTP là một subsystem của SSH: một kết nối TCP tới cổng 22, mã hoá, xác thực bằng khoá (không có mật khẩu nằm trong
script cron), và có thể giới hạn tài khoản vào một thư mục (`ChrootDirectory`, `ForceCommand internal-sftp`). FTP thường
(a) gửi mật khẩu và dữ liệu dạng rõ. FTPS (b) mã hoá được nhưng cần thêm dải cổng passive, trái với ràng buộc một cổng.
HTTP basic auth trên cổng 80 (d) gửi mật khẩu gần như dạng rõ (base64).

### `ftps-firewall`: kênh data passive

FTP tách kênh điều khiển (21) và kênh dữ liệu (cổng động do server báo trong phản hồi `PASV`). Với FTP thường, firewall
và NAT có module "FTP helper" đọc lệnh `PASV` để mở cổng tạm. Với FTPS, kênh điều khiển đã mã hoá nên helper mù: lệnh
`LIST`, `RETR` mở kết nối data tới một cổng bị chặn và treo. Sửa: cấu hình dải passive cố định trên server (vd.
50000–50100) và mở đúng dải đó, hoặc chuyển sang SFTP. Cert hết hạn (a) làm lỗi ngay lúc bắt tay TLS, không phải ở `LIST`.

### `smtp-submission-port`: 587 hoặc 465

Cổng 25 là MTA-to-MTA, nhiều cloud (AWS, GCP, Azure) chặn chiều ra mặc định để chống spam, và ESP yêu cầu xác thực.
587 là cổng submission với STARTTLS; 465 là submission với TLS ngay từ đầu (implicit TLS, RFC 8314 khuyến nghị dùng
465). Cả hai đều cần `AUTH`. IMAP (c) không gửi thư. 2525 (d) là cổng phụ một số ESP mở khi 587 bị chặn, nhưng gửi không
mã hoá thì lộ mật khẩu SMTP.

### `imap-vs-pop3`: IMAPS

IMAP giữ thư, thư mục và cờ (đã đọc, đã trả lời) trên server, nhiều client đồng bộ cùng một trạng thái; IMAPS là IMAP
trên TLS cổng 993. POP3 (a, d) tải thư về một máy, trạng thái mỗi máy một kiểu. SMTP (b) chỉ để gửi.

### `greylisting-otp`: greylisting

Greylisting: lần đầu gặp bộ ba (IP gửi, người gửi, người nhận), server nhận trả `451` tạm thời. MTA thật sẽ thử lại sau
vài phút và được nhận; bot spam bắn-rồi-quên thì không. Cái giá là trễ ở lần đầu, rất tệ cho OTP. Giảm bằng cách gửi qua
ESP có reputation tốt (thường được whitelist), dùng dải IP ổn định, và với thư quan trọng, đề nghị đối tác whitelist IP
của bạn. Blacklist (b) trả lỗi 5xx vĩnh viễn hoặc nhận rồi vứt; SPF sai (c) không làm trễ có giới hạn kiểu này; 4xx (d)
nghĩa là tạm thời, ngược với đáp án.

### `dns-migration-ttl`: hạ TTL trước

Resolver đã cache bản ghi với TTL 86400 sẽ giữ IP cũ tới 24 giờ kể từ lần hỏi cuối. Hạ TTL chỉ có tác dụng sau khi bản
ghi TTL cũ hết hạn ở mọi cache, nên phải hạ trước **ít nhất một TTL cũ**. Sau khi đổi và ổn định, nâng TTL lại để giảm
tải và giảm phụ thuộc vào DNS. Vẫn giữ load balancer cũ chạy một thời gian: một số client (JVM cũ, ứng dụng tự cache)
không tôn trọng TTL. TTL 0 (d) làm mọi request đều hỏi DNS và nhiều resolver tự nâng lên mức tối thiểu.

### `http3-blocked`: rơi về HTTP/2

HTTP/3 chạy trên QUIC (UDP). Trình duyệt chỉ thử HTTP/3 sau khi biết server hỗ trợ (header `Alt-Svc` hoặc bản ghi DNS
`HTTPS`), và luôn có đường TCP song song hoặc dự phòng. UDP 443 bị chặn thì người dùng vẫn vào được qua HTTP/2, chỉ mất
lợi ích của QUIC. Không có chuyện rơi về HTTP/1.0 không mã hoá (c), và HTTP/3 không chạy trên TCP (d).

### `ssh-hop`: ProxyJump

`ssh -J bastion db-primary` mở một kênh TCP qua bastion, rồi chạy phiên SSH đầu-cuối từ laptop tới `db-primary`. Bastion
không có khoá, không có agent, không đọc được phiên. `ssh -A` (a) để lại socket agent trên bastion. Copy khoá riêng lên
bastion (b) là tệ nhất. Mở 22 ra Internet (d) bỏ hẳn lớp bastion.

### `plain-protocols`: FTP, Telnet, POP3, HTTP basic

FTP gửi `USER`/`PASS` dạng rõ; Telnet gửi cả phiên dạng rõ; POP3 cổng 110 gửi `USER`/`PASS` dạng rõ nếu không
`STLS`; HTTP basic auth chỉ là base64 của `user:pass`. SFTP chạy trong SSH nên luôn mã hoá. Kiểm thử thực tế: chạy
`tcpdump -A port 21` khi đăng nhập FTP và nhìn thấy mật khẩu.

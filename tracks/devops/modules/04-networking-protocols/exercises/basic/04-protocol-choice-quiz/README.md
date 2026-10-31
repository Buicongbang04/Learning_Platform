---
title: Chọn giao thức theo tình huống - truyền tệp, email, DNS, HTTP/3, SSH
level: basic
services: []
files: []
run: []
---

## Mục tiêu

Chọn giao thức từ ràng buộc thật (firewall chỉ mở một cổng, nhiều thiết bị cùng đọc một hộp thư, client sau NAT, bastion
có thể bị chiếm) thay vì từ thói quen, và nhận ra những giao thức vẫn gửi mật khẩu dạng rõ.

## Đề bài

Bài này không có code. Làm 9 câu trắc nghiệm trong app (card **Trắc nghiệm** bên dưới): 8 câu chọn một đáp án, câu cuối
chọn mọi đáp án đúng. Các câu đi qua: truyền tệp với đối tác (FTP, FTPS, SFTP), cổng SMTP cho ứng dụng, IMAP và POP3,
greylisting, TTL khi chuyển hạ tầng, HTTP/3 khi UDP bị chặn, đi qua bastion.

Trước khi chọn, với mỗi tình huống tự hỏi:

1. Có bao nhiêu kết nối TCP/UDP và cổng nào phải mở qua firewall?
2. Mật khẩu hoặc dữ liệu có đi dạng rõ ở đoạn nào không?
3. Khi một thành phần ở giữa (bastion, firewall, resolver) hỏng hay bị chiếm, điều gì xảy ra?

## Tiêu chí đạt

- Trả lời đúng ít nhất 7/9 câu.
- Với mỗi câu sai, nói lại được ràng buộc quyết định và điều kiện để phương án bạn chọn trở thành đúng.
- Nhấn **Đánh dấu hoàn thành** sau khi đã đọc lời giải.

## Gợi ý

### Gợi ý 1

FTP và FTPS dùng hai kênh (điều khiển và dữ liệu), SFTP dùng một kết nối SSH. SMTP cổng 25 là giữa các máy chủ thư,
ứng dụng gửi thư qua cổng submission có xác thực.

### Gợi ý 2

Mã SMTP `4xx` là lỗi tạm thời, `5xx` là lỗi vĩnh viễn. TTL là thời gian một câu trả lời được phép nằm trong cache, kể cả
khi bạn đã đổi bản ghi.

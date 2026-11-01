# Lời giải: gửi báo cáo qua SMTP vào Mailpit

Script đầy đủ ở `send_report.py` cạnh tệp này.

## Cách làm

1. **Kiểm hết dữ liệu trước khi mở kết nối SMTP.** Ngày, CSV, cột, số tiền đều được kiểm trước; lỗi nào cũng ra exit 2 và
   không có thư nào được gửi. Thư báo cáo sai số còn tệ hơn không có thư.
2. **`Decimal` cho tiền.** `sum(float)` của 38.71 + 141.46 + 72.20 cho ra 252.37000000000003; định dạng lại thì vẫn đúng
   ở đây, nhưng tổng của hàng nghìn dòng sẽ lệch xu.
3. **Envelope tách khỏi header.** `send_message(msg, from_addr=..., to_addrs=[...])`: `from_addr` là `MAIL FROM`, nơi
   nhận bounce, và là tên miền mà SPF kiểm; `to_addrs` là danh sách `RCPT TO`. Bcc chính là "có trong `RCPT TO` mà không
   có trong header". Đừng đặt header `Bcc` rồi trông vào thư viện xoá nó.
4. **Ba nhóm lỗi, ba mã thoát.** `0` gửi xong, `2` dữ liệu sai (đừng retry, sửa dữ liệu), `3` lỗi SMTP (retry được,
   scheduler như cron/systemd timer/Airflow nên retry với backoff). Người trực ca đọc mã thoát là biết làm gì.
5. **Không traceback cho người vận hành.** Bắt `OSError` (connection refused, timeout, DNS) và `smtplib.SMTPException`
   (server từ chối người nhận, từ chối xác thực), in một dòng có tiền tố cố định để grep.

## Header nào để làm gì

| Header | Vì sao |
| --- | --- |
| `Message-ID` thuộc tên miền mình | Định danh duy nhất để tra log MTA, ESP, và để client nhóm hội thoại. Thiếu hoặc sai tên miền là một điểm trừ trong bộ lọc spam |
| `Date` có múi giờ | Bắt buộc theo RFC 5322; thiếu thì một số MTA tự thêm, một số chấm điểm spam |
| `Reply-To` | Người nhận trả lời thì tới team vận hành, không tới hộp `reports@` không ai đọc |
| `Auto-Submitted: auto-generated` | Auto-responder (vắng mặt, ticket) không trả lời, tránh vòng lặp thư |
| `List-Unsubscribe` + `List-Unsubscribe-Post` | Từ 02/2024 Gmail và Yahoo đòi bulk sender có hủy đăng ký một chạm (RFC 8058); thiếu thì thư marketing bị lọc |

## Khi gửi thật

- Gửi qua ESP hoặc relay của công ty trên cổng 587 với STARTTLS bắt buộc (`smtp.starttls(context=ssl.create_default_context())`
  rồi `smtp.login(...)`) hoặc 465 với `smtplib.SMTP_SSL`. Mật khẩu SMTP lấy từ secret manager, không từ tham số dòng lệnh
  (lộ trong `ps`).
- Tên miền `bounces.olist-shop.com.br` phải có SPF cho ESP, thư phải ký DKIM `d=olist-shop.com.br`: xem bài Intermediate
  01 và Advanced 02.
- Ba lý do thư vẫn vào spam dù code đúng: tên miền/IP mới chưa có reputation (cần warm-up), DMARC fail vì DKIM chưa
  aligned, nội dung và tỉ lệ khiếu nại (giữ spam rate dưới 0,1% trong Postmaster Tools).
- Mailpit thay thế được cho môi trường dev/CI: mọi thư đi vào một hộp, không lọt ra ngoài; API cho test tự động như bài
  này. Các lựa chọn tương tự: MailHog (không còn được phát triển), smtp4dev, GreenMail.

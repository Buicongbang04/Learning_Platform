---
title: Gửi báo cáo qua SMTP vào Mailpit và kiểm bằng API
level: intermediate
services: [mailpit]
files:
  - path: starter/send_report.py
    note: 3 hàm có TODO
  - path: tests/test_send_report.py
    note: Không sửa
run:
  - docker compose -f setup/docker-compose.yml --profile devops up -d mailpit
  - uv run pytest tracks/devops/modules/04-networking-protocols/exercises/intermediate/02-mailpit-daily-report -q
  - docker compose -f setup/docker-compose.yml --profile devops stop mailpit
---

## Mục tiêu

Gửi một thư tự động "đúng nghề": envelope sender tách khỏi `From` để bounce về đúng chỗ, Bcc chỉ nằm trong envelope,
`Message-ID` thuộc tên miền của mình, header `List-Unsubscribe` một chạm mà Gmail và Yahoo đòi từ 2024, phần text và
HTML, tệp đính kèm, mã thoát phân biệt lỗi dữ liệu với lỗi SMTP. Kiểm kết quả bằng API của Mailpit thay vì mở hộp thư.

## Đề bài

Mỗi sáng một job gửi báo cáo đơn hàng hôm trước cho team vận hành. Viết `starter/send_report.py`:

```bash
python send_report.py --host HOST --port PORT --csv orders.csv --date 2026-11-01 \
  --to ops@olist-shop.com.br [--to ...] [--bcc audit@olist-shop.com.br ...]
```

**Dữ liệu**: CSV UTF-8 có header, bắt buộc có ba cột `order_id`, `order_status`, `payment_value` (cột khác bỏ qua). Đơn
có `order_status` đúng bằng `canceled` là đơn huỷ; mọi đơn khác là hợp lệ. Doanh thu là tổng `payment_value` của đơn hợp
lệ, cộng bằng `Decimal`, in đúng 2 chữ số thập phân (`252.37`).

**Thư gửi đi**:

| Thành phần | Giá trị bắt buộc |
| --- | --- |
| Envelope sender (`MAIL FROM`, thành `Return-Path`) | `bounces@olist-shop.com.br` |
| Envelope recipients (`RCPT TO`) | Mọi `--to` và mọi `--bcc` |
| `From` | `Olist Shop Reports <reports@olist-shop.com.br>` |
| `To` | Mọi `--to`, cách nhau bằng dấu phẩy. Không có header `Cc`. Địa chỉ `--bcc` **không** xuất hiện trong bất kỳ header nào |
| `Reply-To` | `ops@olist-shop.com.br` |
| `Subject` | `[Olist Shop] Báo cáo đơn hàng <date>` (UTF-8, thư viện `email` tự mã hoá) |
| `Date` | Thời điểm gửi, có múi giờ |
| `Message-ID` | Duy nhất mỗi lần chạy, dạng `<...@olist-shop.com.br>` |
| `Auto-Submitted` | `auto-generated` (RFC 3834: auto-responder không trả lời thư này) |
| `List-Unsubscribe` | Có một URI `mailto:` và một URI `https://`, mỗi URI trong `<...>`, cách nhau bằng dấu phẩy |
| `List-Unsubscribe-Post` | `List-Unsubscribe=One-Click` |
| Phần text | Có 4 dòng: `Ngày: <date>`, `Đơn hàng hợp lệ: <n>`, `Doanh thu (BRL): <x.xx>`, `Đơn huỷ: <k>` |
| Phần HTML | `multipart/alternative` cùng phần text, chứa số doanh thu |
| Đính kèm | Đúng một tệp `orders-<date>.csv`, `text/csv`, nội dung đúng bằng CSV đầu vào |

**Output và mã thoát**:

| Tình huống | Exit | stdout | stderr |
| --- | --- | --- | --- |
| Gửi xong | `0` | Đúng một dòng: `Message-ID` kèm `<>` | Tuỳ |
| Thiếu `--to`; `--date` không phải ngày hợp lệ dạng `YYYY-MM-DD`; không đọc được CSV; thiếu cột; `payment_value` không phải số | `2`, **không gửi gì** | Rỗng | Thông báo một dòng, không traceback |
| Không kết nối được SMTP, timeout, server từ chối | `3` | Rỗng | Bắt đầu bằng `smtp error:`, không traceback |

Timeout kết nối SMTP không quá 10 giây. Không có TLS và đăng nhập trong lab này (Mailpit không bật); mục 6 của lý thuyết
nói cách làm với ESP thật.

**Test**: bật Mailpit theo `run` (SMTP cổng `MAILPIT_SMTP_PORT`, mặc định `11025`; API cổng `MAILPIT_HTTP_PORT`, mặc định
`18025`; đổi trong `setup/.env` nếu trùng). Mailpit chưa chạy thì test skip. Test chạy script của bạn bằng Python của
repo trong sandbox bubblewrap (thiếu `bwrap` thì skip), với CSV 4 dòng trong thư mục tạm và một ngày ngẫu nhiên để tiêu
đề không trùng thư của lần chạy trước. Test xoá các thư có tiêu đề đó trước và sau khi chạy, rồi đọc thư qua
`GET /api/v1/search`, `GET /api/v1/message/{ID}`, `/headers`, `/part/{PartID}` và so từng dòng của bảng trên. Ca exit 3
dùng một cổng loopback vừa đóng.

## Tiêu chí đạt

- `uv run pytest tracks/devops/modules/04-networking-protocols/exercises/intermediate/02-mailpit-daily-report -q` pass,
  không skip.
- Mở `http://localhost:18025`, xem thư vừa gửi, tab **Headers** và **HTML Check**; giải thích vì sao `Return-Path` khác
  `From`, và nhìn vào đâu để biết `audit@` nhận được thư.
- Nói được ba lý do một thư như thế này vẫn vào spam khi gửi thật, dù code đúng (xem mục 6 của lý thuyết).
- Tắt Mailpit khi xong: `docker compose -f setup/docker-compose.yml --profile devops stop mailpit`.

## Gợi ý

### Gợi ý 1

`email.message.EmailMessage`: `set_content(text)`, rồi `add_alternative(html, subtype="html")`, rồi
`add_attachment(bytes, maintype="text", subtype="csv", filename=...)` tự dựng cây `multipart/mixed` → `alternative`.
`email.utils.make_msgid(domain=...)` và `formatdate(usegmt=True)` lo `Message-ID` và `Date`.

### Gợi ý 2

`smtp.send_message(msg, from_addr=..., to_addrs=[...])`: `from_addr` là envelope sender, `to_addrs` là envelope
recipients, độc lập với header. Đó chính là cách Bcc hoạt động. Bắt `OSError` (kết nối, timeout) và
`smtplib.SMTPException` (server từ chối) để trả exit 3. Kiểm hết dữ liệu **trước** khi mở kết nối SMTP.

---
title: Sự cố TLS chỉ một số client lỗi - chẩn đoán và viết postmortem
level: advanced
services: []
files:
  - path: starter/POSTMORTEM.md
    note: Khung postmortem, điền mọi TODO
  - path: tests/fixtures/evidence/alerts-and-chat.txt
    note: Bằng chứng, đọc trước
  - path: tests/fixtures/evidence/client-errors.txt
    note: Bằng chứng
  - path: tests/fixtures/evidence/s_client-before-fix.txt
    note: Bằng chứng
  - path: tests/fixtures/evidence/s_client-after-fix.txt
    note: Bằng chứng
  - path: tests/fixtures/evidence/s_client-no-sni.txt
    note: Bằng chứng
  - path: tests/fixtures/evidence/nginx-api-diff.txt
    note: Bằng chứng
  - path: tests/test_postmortem.py
    note: Không sửa; kiểm khung, chất lượng chấm theo rubric
run:
  - uv run pytest tracks/devops/modules/04-networking-protocols/exercises/advanced/01-tls-partial-outage-postmortem -q
---

## Mục tiêu

Chẩn đoán một sự cố mà "trên máy tôi vẫn chạy": cùng một endpoint HTTPS, trình duyệt và iPhone vào được, còn Android,
Java, Python và curl thì không. Rồi viết postmortem blameless mà người khác đọc xong biết chính xác chuyện gì đã xảy ra,
vì sao giám sát không thấy, và việc gì làm cho nó không lặp lại.

## Đề bài

Tối thứ Sáu, sau một change thay cert định kỳ cho `api.olist-shop.com.br`, team nhận được các triệu chứng sau:

- Trình duyệt desktop và app iOS: bình thường, ổ khoá xanh.
- App Android: không tải được giỏ hàng, lỗi `Trust anchor for certification path not found`.
- Đối tác logistics (Java): `PKIX path building failed`. Worker `payment-sync` (Python): `CERTIFICATE_VERIFY_FAILED`.
- Synthetic check về hạn cert: xanh suốt sự cố.
- Purge cache CDN không giúp gì.
- Một nhóm thiết bị POS cũ báo `hostname mismatch`, có vẻ từ trước tối nay.

Thư mục `tests/fixtures/evidence/` chứa chat và cảnh báo, số liệu lỗi theo loại client, output `openssl s_client` trước
và sau khi sửa, output không gửi SNI, và diff cấu hình Nginx của change. Dùng chúng để:

1. Xác định nguyên nhân kỹ thuật, và giải thích vì sao **chỉ một số** client lỗi (gợi ý: client lấy chứng chỉ trung gian
   từ đâu?). Xác định riêng vấn đề POS: có cùng nguyên nhân không, và có cần đưa vào postmortem này không.
2. Viết `starter/POSTMORTEM.md`, giữ nguyên các heading `## 1.` tới `## 7.`, không còn chữ `TODO`:

| Phần | Yêu cầu kiểm tự động |
| --- | --- |
| 1. Tóm tắt | Ít nhất 200 ký tự (không tính bảng) |
| 2. Tác động | Ít nhất 3 con số |
| 3. Dòng thời gian | Bảng ít nhất 8 dòng đủ 3 cột (`Thời điểm`, `Sự kiện`, `Nguồn`); cột đầu dạng `HH:MM`, tăng dần |
| 4. Nguyên nhân gốc và yếu tố góp phần | Ít nhất 400 ký tự (không tính bảng) và ít nhất 3 gạch đầu dòng |
| 5. Phát hiện và xử lý | Ít nhất 250 ký tự |
| 6. Việc cần làm | Bảng ít nhất 5 dòng đủ 4 cột (`Việc`, `Loại`, `Người phụ trách`, `Hạn`); `Loại` là một trong `phòng ngừa`, `phát hiện`, `giảm thiểu`, có ít nhất một `phòng ngừa` và một `phát hiện`; `Hạn` dạng `YYYY-MM-DD` |
| 7. Bài học | Ít nhất 2 gạch đầu dòng |

Test chỉ kiểm khung. Nội dung được chấm bằng rubric trong `solutions/advanced/01-tls-partial-outage-postmortem/SOLUTION.md`;
đọc rubric **sau** khi viết xong.

## Tiêu chí đạt

- `uv run pytest tracks/devops/modules/04-networking-protocols/exercises/advanced/01-tls-partial-outage-postmortem -q`
  pass.
- Đạt ít nhất 70/100 điểm rubric khi tự chấm.
- Mỗi kết luận trong phần 4 trỏ được về một dòng bằng chứng cụ thể trong `evidence/`.
- Postmortem không đổ lỗi cho cá nhân: mô tả hệ thống và quy trình đã cho phép lỗi lọt qua.
- Có ít nhất một việc cần làm biến lỗi này thành thứ máy chặn được trước khi tới production.

## Gợi ý

### Gợi ý 1

So sánh mục `Certificate chain` trong hai output `s_client` trước và sau khi sửa: đếm số cert server gửi. Rồi tự hỏi:
trình duyệt desktop có những cách nào để tự hoàn thiện một chuỗi mà server không gửi đủ, mà OpenSSL, Java hay OkHttp
không làm?

### Gợi ý 2

Synthetic check chỉ đọc ngày hết hạn trả lời câu hỏi "cert còn hạn không", không trả lời "một client chuẩn có tin cert
này không". Còn POS: so output `-noservername` với cấu hình `default_server` trong diff.

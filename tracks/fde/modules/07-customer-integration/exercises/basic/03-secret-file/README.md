---
title: "Secret theo chính sách khách: chỉ qua tệp, không lộ ở đâu"
level: basic
services: []
files:
  - path: starter/push_report.py
    note: Bản đồng nghiệp viết hôm triển khai thử; bạn viết lại
  - path: tests/test_secret_file.py
    note: Không sửa
run:
  - uv run pytest tracks/fde/modules/07-customer-integration/exercises/basic/03-secret-file -q
---

## Mục tiêu

Sau mỗi lượt đồng bộ, connector gửi báo cáo lên dịch vụ audit nội bộ của công ty luật bằng một token. Chính sách bảo
mật của khách (mục 4.2 trong bộ câu hỏi họ gửi): *secret của ứng dụng bên thứ ba chỉ được giao bằng tệp do Vault Agent
ghi ra, không qua biến môi trường hay tham số dòng lệnh; secret không được xuất hiện trong log, output, danh sách tiến
trình*. Script đồng nghiệp viết chạy được, nhưng sẽ trượt buổi rà soát. Bạn viết lại nó theo quy ước `*_FILE` và chứng
minh secret không lộ ở bất kỳ đâu, kể cả khi mọi thứ hỏng.

## Đề bài

Viết lại `starter/push_report.py` (Python 3.12, chỉ thư viện chuẩn hoặc thư viện có sẵn trong môi trường của repo;
được gọi chương trình ngoài nếu muốn). Cách chạy: `python push_report.py <tệp báo cáo JSON>`, với:

- `AUDIT_URL`: URL nhận báo cáo (`POST`).
- `AUDIT_TOKEN_FILE`: đường dẫn tệp chứa token (Vault Agent ghi token và một ký tự xuống dòng ở cuối).

Hành vi:

1. Gửi đúng **một** `POST` tới `AUDIT_URL`, thân là nguyên nội dung tệp báo cáo, header
   `Authorization: Bearer <token>` (token là nội dung tệp bỏ ký tự xuống dòng cuối). Không thử lại.
2. Ghi log vào `push_report.log` trong thư mục làm việc.
3. Mã thoát: `0` khi dịch vụ trả 2xx; `1` khi gửi thất bại (HTTP 4xx/5xx, không kết nối được, server đóng kết nối giữa
   chừng), kèm thông báo lỗi trên stderr; `2` khi cấu hình sai, **không gửi request nào**:
   - thiếu `AUDIT_URL` hay `AUDIT_TOKEN_FILE`, tệp token không có, không đọc được, hoặc rỗng;
   - tệp token cho group/other quyền nào đó (chính sách: chỉ chủ tệp, như `chmod 600`);
   - có biến `AUDIT_TOKEN` trong môi trường (chính sách cấm secret trong biến môi trường; từ chối thay vì lặng lẽ dùng).
4. Lỗi báo bằng thông báo, **không** in traceback ra stderr.
5. Token **không bao giờ** xuất hiện ở: stdout, stderr, bất kỳ tệp nào script ghi trong thư mục làm việc, dòng lệnh
   (`/proc/<pid>/cmdline`) hay biến môi trường (`/proc/<pid>/environ`) của bất kỳ tiến trình nào trong lúc script
   chạy, kể cả khi dịch vụ audit **lặp lại token trong thân phản hồi lỗi** (có dịch vụ thật làm vậy).

Test chạy script trên host trong sandbox (`testkit.run_sandboxed`) với token ngẫu nhiên mỗi lần chạy, một dịch vụ audit
HTTP giả trong tiến trình test (trả lời chậm 1,5 s để có thời gian quan sát), và quét `/proc` của mọi tiến trình liên
tục trong lúc script chạy. Cả bài ~10 s.

## Tiêu chí đạt

- `test_success_sends_token_from_file`: thoát `0`; dịch vụ nhận đúng 1 request tới `/api/reports`, đúng header, đúng
  thân; có `push_report.log`; token không lộ (mục 5), không traceback.
- `test_send_failures_do_not_leak` (4 ca: 401 có lặp token trong thân, 500 có lặp token, server đóng kết nối, cổng
  không mở): thoát `1`, có thông báo trên stderr, đúng 1 request (ca có server), token không lộ, không traceback.
- `test_config_errors`: thiếu `AUDIT_TOKEN_FILE`; tệp không có; tệp rỗng; chỉ có `AUDIT_TOKEN` trong môi trường; tệp
  token quyền `0644` ⇒ thoát `2`, không request nào tới dịch vụ, token không lộ ở stdout/stderr/tệp (ca có
  `AUDIT_TOKEN` trong môi trường thì không quét `/proc`, vì chính test đã đặt nó ở đó).

## Gợi ý

### Gợi ý 1

Chạy bản của đồng nghiệp rồi, trong lúc nó đang chờ server, xem `ps -eo pid,args` và `cat /proc/<pid>/environ | tr
'\0' '\n'` của chính bạn. User khác trên cùng máy thấy được gì trong hai chỗ đó?

### Gợi ý 2

Thông báo lỗi của thư viện (và của chương trình con) thường chứa đúng thứ bạn vừa đưa cho nó. Thứ gì bạn in ra là do
bạn chọn, không phải do exception chọn.

### Gợi ý 3

Nếu gọi chương trình ngoài, tìm cách nó nhận header hay cấu hình từ tệp hoặc stdin thay vì từ đối số.

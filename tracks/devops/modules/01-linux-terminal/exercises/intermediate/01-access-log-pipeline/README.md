---
title: Điều tra sự cố checkout từ access log Nginx bằng pipeline shell
level: intermediate
services: []
files:
  - path: starter/log_report.sh
    note: 7 TODO
  - path: tests/test_log_report.py
    note: Không sửa
  - path: tests/fixtures/access.log
    note: 611 dòng, định dạng combined + rt
  - path: tests/fixtures/access.jsonl
    note: Cùng khoảng thời gian, định dạng JSON
run:
  - bash tracks/devops/modules/01-linux-terminal/exercises/intermediate/01-access-log-pipeline/starter/log_report.sh status tracks/devops/modules/01-linux-terminal/exercises/intermediate/01-access-log-pipeline/tests/fixtures/access.log
  - uv run pytest tracks/devops/modules/01-linux-terminal/exercises/intermediate/01-access-log-pipeline -q
---

## Mục tiêu

Trả lời câu hỏi đầu tiên của mọi sự cố web ("lỗi gì, từ lúc nào, ở đâu, upstream nào") trong vài phút chỉ bằng
`awk`, `sed`, `sort`, `uniq` và `jq` trên log thật-dạng, trước khi có dashboard. Biết các bẫy làm pipeline một dòng
cho kết quả sai mà không báo lỗi.

## Đề bài

Sáng 28/10/2026, khách hàng báo không thanh toán được trong khoảng 10:10–10:20. Bạn có 30 phút access log của Nginx
đứng trước hai bản API Olist Shop (`10.0.1.11:8000` và `10.0.1.12:8000`):

- `tests/fixtures/access.log`, định dạng `combined` cộng thêm thời gian xử lý:

  ```nginx
  log_format olist '$remote_addr - $remote_user [$time_local] "$request" $status $body_bytes_sent '
                   '"$http_referer" "$http_user_agent" rt=$request_time';
  ```

  ```text
  203.113.37.211 - - [28/Oct/2026:10:00:00 +0700] "GET /api/products?category=informatica_acessorios&page=2 HTTP/1.1" 200 7229 "https://shop.olist.local/" "Mozilla/5.0 (...)" rt=0.056
  ```

- `tests/fixtures/access.jsonl`, cùng các request nhưng ghi bằng `log_format ... escape=json`, có thêm
  `upstream_addr` và `upstream_status`. Khi Nginx thử lại upstream khác (`proxy_next_upstream`), hai trường này là
  danh sách cách nhau bởi `, `, ví dụ `"10.0.1.12:8000, 10.0.1.11:8000"` và `"502, 201"`.

Viết `starter/log_report.sh <lệnh> [tham số] <tệp>`. Tệp là `-` thì đọc stdin (để dùng với log đã nén:
`gzip -dc access.log.2.gz | log_report.sh status -`).

| Lệnh | Output (mỗi dòng) | Sắp xếp |
| --- | --- | --- |
| `status <log>` | `<status> <số request>` | Theo status tăng dần |
| `top-ips <N> <log>` | `<số request> <ip>`, tối đa N dòng | Số request giảm dần, bằng nhau thì IP theo thứ tự byte |
| `errors <log>` | `<số request 5xx> <path>`; path bỏ query string (`/a?x=1` thành `/a`) | Số giảm dần, rồi path |
| `slow <giây> <log>` | `<rt như trong log> <status> <path>` cho request có `rt >=` ngưỡng | `rt` giảm dần theo **giá trị số**, rồi path |
| `per-minute <log>` | `<HH:MM> <tổng request> <số 5xx>` | Theo thời gian, như thứ tự trong log |
| `upstream-errors <jsonl>` | `<số lần> <upstream>`: mỗi lần **một upstream** trả 5xx, kể cả lần bị Nginx retry | Số giảm dần, rồi địa chỉ |

Log thật có những dòng làm pipeline ngây thơ sai, và fixture có đủ:

- Client IPv6 (`2001:db8:4f::1f`): địa chỉ có dấu `:`, nên cắt giờ theo `:` sẽ lệch.
- Request line không hợp lệ: `"-"` (client mở kết nối rồi đóng) và byte rác `"\x16\x03\x01..."` (ai đó nói TLS vào
  cổng HTTP), đều trả `400`. Chúng vẫn tính trong `status`, `top-ips`, `per-minute`, nhưng **không** có path nên bỏ
  khỏi `errors` và `slow`.
- Nginx escape dấu `"` trong request và User-Agent thành `\x22`, và User-Agent có thể chứa chuỗi trông giống
  `rt=99`.

Quy ước chung:

- Sai lệnh, thiếu tham số, `N` hoặc ngưỡng không phải số: stderr bắt đầu bằng `Usage:`, exit `2`, stdout rỗng.
- Tệp không đọc được: thông báo lỗi ra stderr, exit `1`.
- Kết quả không phụ thuộc locale của máy (test chạy với `LC_ALL=C`; bạn nên tự đặt trong script).
- `upstream-errors` cần `jq` (cài ở `## 0. Cài đặt`); thiếu `jq` thì hai test của lệnh này skip.

Làm xong, chạy các lệnh trên fixture và tự trả lời: sự cố bắt đầu và kết thúc lúc nào, endpoint nào, upstream nào
hỏng, khách hàng thấy lỗi gì (502 hay 504, khác nhau thế nào), và có request nào thành công nhờ retry không.

## Tiêu chí đạt

- `uv run pytest tracks/devops/modules/01-linux-terminal/exercises/intermediate/01-access-log-pipeline -q` pass toàn
  bộ, không skip.
- `shellcheck starter/log_report.sh` không có cảnh báo.
- Viết được 3–4 câu tóm tắt sự cố từ output của script: thời gian, endpoint, upstream, mức ảnh hưởng.
- Giải thích được vì sao `sort -n` cho thứ tự sai với `sort -u` hoặc `sort` không có `-n`, và vì sao `LC_ALL=C`.

## Gợi ý

### Gợi ý 1

Định dạng combined dễ tách nhất bằng dấu ngoặc kép: `awk -F'"'` cho `$2` là request line, `$3` là ` <status> <bytes> `,
`$6` là User-Agent, `$NF` là phần ` rt=...` cuối dòng (Nginx đã escape mọi `"` bên trong). IP là từ đầu tiên của `$1`;
giờ phút lấy từ đoạn trong `[...]`, không cắt cả dòng theo `:`. Viết một hàm `fields` in ra các cột đã chuẩn hoá
(`ip status path rt minute`, path rỗng thì in `-`), các lệnh khác chỉ còn là `awk '{...}' | sort | uniq -c | sort`.

### Gợi ý 2

`uniq -c` in `<số> <khoá>` có khoảng trắng đầu dòng; `awk '{print $2, $1}'` đổi chỗ và bỏ khoảng trắng. Sắp nhiều khoá:
`sort -k1,1nr -k2,2`. Số thực như `30.020` cần `sort -g` (hoặc `-n` với `LC_ALL=C` để dấu thập phân là `.`). Với `jq`,
tách hai danh sách bằng `split(", ")`, ghép từng cặp bằng `transpose`, rồi `select(.[1] | startswith("5"))`.

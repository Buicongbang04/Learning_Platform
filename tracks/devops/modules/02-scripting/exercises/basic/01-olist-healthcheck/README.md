---
title: Healthcheck Olist Shop theo hợp đồng exit code của Nagios
level: basic
services: []
files:
  - path: starter/healthcheck.sh
    note: 4 TODO
  - path: tests/test_healthcheck.py
    note: Không sửa; test tự chạy một API giả trên 127.0.0.1
run:
  - bash tracks/devops/modules/02-scripting/exercises/basic/01-olist-healthcheck/starter/healthcheck.sh -u http://localhost:28000
  - uv run pytest tracks/devops/modules/02-scripting/exercises/basic/01-olist-healthcheck -q
---

## Mục tiêu

Viết một healthcheck mà hệ thống giám sát dùng được: mỗi lần chạy trả đúng một dòng trạng thái và một exit code theo
hợp đồng của Nagios plugin (Icinga, Zabbix, Sensu, Checkmk đều hiểu), phân biệt "service chết" với "service sống
nhưng thiếu phụ thuộc". Làm quen với bẫy lớn nhất của `set -e`: lệnh lỗi làm script chết trước khi kịp báo gì.

## Đề bài

Olist Shop có hai endpoint (xem `tracks/devops/sample-app/README.md`): `/healthz` (liveness, không chạm DB/Redis) và
`/readyz` (readiness: `200 {"db":"ok","redis":"ok"}`, thành phần nào lỗi thì `503` với giá trị `"error"`). Viết
`starter/healthcheck.sh [-u base_url] [-t timeout_giây]`:

- `base_url` mặc định lấy từ biến `OLIST_SHOP_API_URL`; không có biến đó thì
  `http://localhost:${OLIST_SHOP_API_PORT:-28000}`. Option `-u` thắng biến môi trường.
- `-t` là số giây tối đa cho **mỗi** request (số nguyên `>= 1`, mặc định `3`), truyền cho `curl --max-time`.
- Gọi `GET <base_url>/healthz` trước. Chỉ khi nó trả `200` mới gọi `GET <base_url>/readyz`.
- Đọc `db`, `redis` trong JSON của `/readyz` bằng `jq`.
- In **đúng một dòng** ra stdout và thoát với exit code theo bảng (thứ tự kiểm từ trên xuống):

| Tình huống | Exit | Dòng stdout (chính xác) |
| --- | --- | --- |
| `curl` thất bại khi gọi một endpoint (từ chối kết nối, quá giờ, DNS...) | `2` | `CRITICAL - api unreachable (curl exit <mã thoát của curl>)` |
| `/healthz` trả mã khác `200` | `2` | `CRITICAL - healthz=<mã>` |
| `/readyz` trả mã khác `200` và `503`; body không phải JSON object; thiếu `db` hoặc `redis`; giá trị khác `ok`/`error`; trả `200` mà có `error`; trả `503` mà cả hai `ok` | `3` | `UNKNOWN - unexpected readyz response (status <mã>)` |
| `/readyz` `200`, cả hai `ok` | `0` | `OK - healthz=200 readyz=200 db=ok redis=ok` |
| `/readyz` `503`, `db` là `error` (bất kể `redis`) | `2` | `CRITICAL - healthz=200 readyz=503 db=error redis=<ok\|error>` |
| `/readyz` `503`, `db` `ok`, `redis` `error` | `1` | `WARNING - healthz=200 readyz=503 db=ok redis=error` |
| Option lạ, `-t` không phải số nguyên `>= 1`, thiếu giá trị cho option, có tham số vị trí thừa | `3` | stdout rỗng; stderr bắt đầu bằng `Usage:` |

Vì sao redis lỗi chỉ là WARNING: API vẫn đọc được đơn hàng, chỉ không đẩy được job tính lại doanh thu; mất DB thì
không phục vụ được gì. Đây là quyết định của team vận hành, ghi trong runbook, không phải quy luật chung.

Theo quy ước Nagios, lỗi cách dùng cũng là `3` (UNKNOWN), không phải `2` như phần lớn công cụ Unix, vì `2` đã mang
nghĩa CRITICAL với hệ thống giám sát. Exit code là hợp đồng với **người gọi** script.

Test chạy một API giả trên `127.0.0.1` (cổng ngẫu nhiên) và gọi script với `curl` thật; biến proxy (`http_proxy`...)
và `OLIST_SHOP_*` của bạn không đi vào môi trường của script. Trường hợp quá giờ: `/healthz` treo 20 giây,
script chạy với `-t 1` phải trả `CRITICAL - api unreachable (curl exit 28)` trong dưới 10 giây. Cổng đóng phải ra
`curl exit 7`. Bài cần `curl` từ 7.68 và `jq` từ 1.6 (cài ở module 01); thiếu thì test skip.
Mọi test chạy script của bạn trong sandbox bubblewrap (xem [Cài đặt](../../../README.md#0-cài-đặt)): `/` chỉ đọc, `/tmp` thật bị che, thư mục làm việc và thư mục duy nhất ghi được là thư mục tạm của test, môi trường biến dựng lại từ đầu (chỉ có `PATH`, `HOME` trỏ vào thư mục tạm, `LANG`/`LC_ALL`, cộng các biến test đặt). Thiếu `bwrap` thì test skip.

## Tiêu chí đạt

- `uv run pytest tracks/devops/modules/02-scripting/exercises/basic/01-olist-healthcheck -q` pass toàn bộ, gồm
  `shellcheck -S style starter/healthcheck.sh` không có cảnh báo nào.
- Chạy lại nhiều lần trên cùng trạng thái ra cùng một dòng.
- Khi Olist Shop đang chạy (`docker compose up -d` trong `tracks/devops/sample-app`), script in `OK - ...`; dừng
  container `redis` thì in `WARNING - ...` và exit `1`.
- Giải thích được vì sao `code=$(curl ...)` trong script có `set -e` làm script thoát im lặng khi curl lỗi, và hai
  cách bắt mã lỗi mà không tắt `set -e`.

## Gợi ý

### Gợi ý 1

`curl -sS --max-time "$timeout" -o "$body_file" -w '%{http_code}' "$url"` in mã HTTP ra stdout và ghi body vào tệp.
Không dùng `-f`/`--fail`: với `-f`, curl trả exit `22` cho `503` và bạn mất body cần đọc. Tệp body tạo bằng `mktemp`
và xoá bằng `trap 'rm -f "$body_file"' EXIT`.

### Gợi ý 2

Bắt mã lỗi mà không để `set -e` giết script: `rc=0; code="$(curl ...)" || rc=$?`. Với jq,
`jq -r 'select(type == "object") | "\(.db) \(.redis)"'` trả `null` cho trường thiếu và lỗi (exit khác 0) khi body
không phải JSON; cả hai đều dẫn tới UNKNOWN. Kiểm giá trị bằng `[[ $db =~ ^(ok|error)$ ]]`.

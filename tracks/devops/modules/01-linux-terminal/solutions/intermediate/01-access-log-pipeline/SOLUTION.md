# Lời giải: điều tra sự cố checkout từ access log Nginx

Script đầy đủ ở `log_report.sh` cạnh tệp này.

## Cách làm

1. **Chuẩn hoá một lần, đếm nhiều lần.** Hàm `fields` đọc log bằng `awk -F'"'` và in năm cột đã sạch:
   `ip status path rt minute`. Mọi lệnh khác chỉ thao tác trên năm cột này, nên các bẫy định dạng chỉ phải xử lý ở
   một chỗ.
   - `path`: request line có đúng 3 từ (`METHOD URI PROTO`) mới có path; `"-"` và byte rác thì in `-`. `sub(/\?.*/, "")`
     bỏ query string.
   - `rt`: lấy từ `$NF` (phần sau dấu `"` cuối cùng) rồi bỏ mọi thứ tới `rt=`, nên chuỗi `rt=99` trong User-Agent
     không lọt vào.
   - `minute`: `match($1, /\[[^]]+\]/)` tìm đoạn thời gian rồi `substr` lấy `HH:MM`. Cắt cả dòng theo `:` hỏng với
     IPv6.
2. **`export LC_ALL=C` ở đầu script.** `sort` theo locale UTF-8 bỏ qua dấu câu và khác nhau giữa các máy; `sort -n` với
   locale dùng dấu phẩy thập phân đọc `30.020` thành `30`. `LC_ALL=C` cũng làm `sort` và `awk` nhanh hơn đáng kể trên
   log lớn.
3. **`input` đọc `-` là stdin**, tệp không đọc được thì exit `1`. Nhờ vậy `zcat`, `gzip -dc`, `journalctl -o cat`,
   `kubectl logs` đều nối vào được mà không cần tệp tạm.
4. **Sắp nhiều khoá tường minh** (`sort -k1,1nr -k2,2`), không trông vào thứ tự ổn định của `uniq -c`.
5. **`upstream-errors`** với `jq`: `[(.upstream_addr | split(", ")), (.upstream_status | split(", "))] | transpose[]`
   ghép từng lần thử với kết quả của nó, rồi lọc status bắt đầu bằng `5`. Dòng `"-"` (Nginx tự trả, không qua upstream)
   tự rơi ra vì `"-"` không bắt đầu bằng `5`.

## Kết quả trên fixture và cách đọc

```text
$ log_report.sh per-minute access.log | sed -n '11,19p'
10:10 20 0
10:11 20 0
10:12 20 3
10:13 20 5
...
10:17 20 3
10:18 20 0
$ log_report.sh errors access.log
16 /api/checkout
1 /api/products/search
$ log_report.sh upstream-errors access.jsonl
18 10.0.1.12:8000
10 10.0.1.11:8000
```

Tóm tắt sự cố một senior viết được từ các số trên:

- **Thời gian**: 10:12–10:17 (6 phút), trước và sau đó không có 5xx.
- **Phạm vi**: chỉ `POST /api/checkout` (16 request lỗi); một lỗi 500 riêng lẻ ở `/api/products/search` là chuyện
  khác (query có ký tự lạ), không thuộc sự cố.
- **Upstream**: `10.0.1.12` có mặt trong mọi lần lỗi. `10.0.1.11` cũng xuất hiện 10 lần, nhưng đều là **lần retry**
  sau khi `10.0.1.12` lỗi trước: với 504, Nginx đã chờ 30 giây ở `.12` rồi retry `.11` và hết thời gian tổng. Đếm thô
  theo trường `upstream_addr` sẽ kết luận sai rằng cả hai bản đều hỏng.
- **Triệu chứng**: `502` trả trong vài mili giây (upstream từ chối kết nối hoặc đóng ngang: tiến trình chết, cổng sai),
  `504` sau 30 giây (`proxy_read_timeout`: upstream nhận request nhưng không trả lời, thường do treo hoặc chờ DB).
  Cùng một upstream sinh cả hai loại gợi ý tiến trình bị treo rồi bị restart.
- **Ảnh hưởng tốt**: một request `502, 201` thành công nhờ retry. Lưu ý `POST` mặc định **không** được Nginx retry
  (`non_idempotent`); fixture có retry cho `POST` là dấu hiệu cấu hình đã bật `proxy_next_upstream ... non_idempotent`,
  một rủi ro trừ tiền hai lần cần nêu trong postmortem.

## Bẫy hay gặp

| Viết | Sai ở đâu |
| --- | --- |
| `awk '{print $9}'` lấy status | Đúng với dòng bình thường, lệch khi request line là `"-"` (1 từ) hoặc có dấu cách bị escape |
| `cut -d: -f2` lấy giờ | Lệch với IPv6 |
| `grep -o 'rt=[0-9.]*'` | Bắt `rt=99` trong User-Agent trước |
| `sort | uniq -c | sort -r` | So chuỗi: `9` đứng trên `16` |
| `sort -n` trên số thực không đặt locale | Máy dùng locale `vi_VN` hoặc `de_DE` đọc dấu chấm sai |

Khi log lớn hơn vài GB hoặc cần lặp lại hằng ngày, chuyển sang công cụ có cấu trúc: log JSON vào Loki hoặc
Elasticsearch (module 13), hoặc truy vấn thẳng bằng DuckDB. Pipeline shell là công cụ của 10 phút đầu sự cố.

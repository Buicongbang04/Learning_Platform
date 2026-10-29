---
title: Web server log thật của NASA (07/1995) - parse, làm sạch, insight
level: basic
services: []
files:
  - path: starter/web_logs.ipynb
    note: 5 hàm TODO + 2 biểu đồ
  - path: tests/test_web_logs.py
    note: Không sửa
run:
  - uv run python data/download_dataset.py nasa-http-logs
  - uv run pytest tracks/data-engineer/modules/00-introduction/exercises/basic/02-web-server-logs -q
---

## Mục tiêu

Thu thập và xử lý một nguồn **log** thật từ đầu tới cuối: đọc streaming 1,9 triệu dòng Common Log
Format, tách dòng hỏng thay vì để pipeline sập, làm sạch về kiểu và múi giờ đúng, rồi rút ra những
điều thật sự đã xảy ra với web server của NASA trong tháng 7/1995.

## Đề bài

Bộ `nasa-http-logs` là access log của web server NASA Kennedy Space Center tháng 7/1995 (~20 MB
gzip, ~205 MB text). Cell đầu notebook tự tải bộ này nếu chưa có (`ensure("nasa-http-logs")`).

Mở `starter/web_logs.ipynb` (nút **Mở trong VS Code**), làm lần lượt:

1. `parse_line(line) -> dict | None` và `parse_log(lines) -> (DataFrame, rejected)`: đọc thẳng từ
   `gzip.open(...)` theo dòng, dòng không đọc được đưa vào danh sách `rejected`. Quy ước từng trường
   ghi ở markdown trong notebook (`bytes` là `-` thì thành `0`, request kiểu HTTP/0.9 không có protocol...).
2. `clean(df)`: timestamp về **UTC**, ép kiểu số nguyên, thêm `host_type` (`ip`, `local`, hoặc đuôi
   tên miền), sắp theo thời gian. Không dedup: log không có khoá.
3. `insights(df, rejected) -> dict`: 18 con số trong bảng của notebook (ngày đỉnh, nhịp theo giờ,
   ngày thường vs cuối tuần, 404, khoảng lặng dài nhất, thời điểm log dừng, ai tải nhiều byte nhất...).
   Tính theo giờ địa phương của server (`America/New_York`).
4. `write_clean(df, out_dir)`: ghi đè `data/clean/nasa-http-logs/requests.parquet`; chạy lại không nhân đôi.
5. Vẽ ít nhất 2 biểu đồ trong các cell `explore`: request theo ngày, và nhịp theo giờ ngày thường vs cuối tuần.
6. Tìm hiểu xem ngày đỉnh trùng với sự kiện gì của NASA. Báo cáo bài học: làm phần trắc nghiệm trong app sau khi chạy notebook.

## Tiêu chí đạt

- Test trên fixture nhỏ (luôn chạy, không cần mạng) pass: parse đúng các ca biên, clean đúng kiểu và UTC, insight đúng trên mẫu.
- Trên bộ thật: khoảng 1,89 triệu request đọc được, dưới 50 dòng hỏng; ngày đỉnh là 13/07/1995 với khoảng 134 nghìn request; log dừng lúc 1995-07-28 13:32:25.
- `write_clean` gọi hai lần vẫn ra đúng số dòng.
- Notebook có ít nhất 2 cell `explore` vẽ biểu đồ.

## Gợi ý

### Gợi ý 1

Regex cho một dòng: `^(\S+) \S+ \S+ \[([^\]]+)\] "(.*)" (\d{3}) (\d+|-)\s*$`. `(.*)` tham lam nên
request có dấu `"` bên trong vẫn khớp. Dòng cuối cùng của tệp bị cắt giữa chừng; vài request là byte
rác: in `rejected` ra xem tận mắt.

### Gợi ý 2

Đừng `strptime` từng dòng: giữ chuỗi ở bước parse, rồi
`pd.to_datetime(s, format="%d/%b/%Y:%H:%M:%S %z").dt.tz_convert("UTC")` một lần. Khi phân tích:
`local = df["ts"].dt.tz_convert("America/New_York")`, nhóm theo `local.dt.floor("D")` và
`local.dt.hour`. Khoảng lặng: sắp `ts`, `diff()`, `idxmax()`.

# Lời giải: Web server log NASA 07/1995

## Cách làm

1. **Parse** bằng một regex cho cả dòng, `(.*)` tham lam trong dấu ngoặc kép để request có `"` bên trong
   vẫn khớp. Tách request line theo khoảng trắng: token đầu là method, token cuối là protocol nếu bắt đầu
   bằng `HTTP/`, phần giữa là path. Dòng không khớp hoặc request rỗng trả `None`.
2. `parse_log` đọc từ iterator dòng (`gzip.open(..., "rt")`), không bao giờ nạp cả tệp text vào bộ nhớ;
   dòng hỏng vào danh sách reject. Pipeline thật ghi danh sách này ra tệp reject và cảnh báo khi tỉ lệ vượt ngưỡng.
3. **Clean** đổi kiểu hàng loạt (vector hoá) thay vì từng dòng: `to_datetime(..., format=... %z)` rồi
   `tz_convert("UTC")`. `host_type` tính trên ~82 nghìn host khác nhau rồi `map`, không gọi hàm 1,9 triệu lần.
4. **Insight** đổi về giờ địa phương một lần (`local`), nhóm theo `floor("D")` và `hour`. Khoảng lặng
   dài nhất: sắp theo thời gian, `diff()`, `idxmax()`.
5. **write_clean** ghi tệp tạm rồi `replace`: ghi đè nguyên tử, chạy lại không nhân đôi, không bao giờ để
   lại Parquet dở nếu kernel chết giữa chừng.

## Vì sao như vậy

- Lưu UTC, hiển thị giờ địa phương: trộn nhiều nguồn ở nhiều múi giờ sẽ không bị lệch, và giờ mùa hè không
  phá phép trừ thời gian.
- Không dedup log: không có khoá thì "trùng" không có nghĩa. Dedup ở đây làm mất 835 request thật.
- Giữ chuỗi timestamp ở bước parse: tách "cấu trúc" khỏi "kiểu" cho mỗi bước dễ test, và nhanh hơn
  `strptime` từng dòng nhiều lần.

## Con số tham chiếu (bộ thật)

| Khoá | Giá trị |
| --- | --- |
| `requests` / `rejected` | 1 891 709 / 6 |
| `unique_hosts`, `total_gb` | 81 982, 38,70 |
| `peak_day`, `peak_day_requests` | 1995-07-13, 134 203 |
| `busiest_hour`, `quietest_hour` | 14, 5 |
| `weekday_avg`, `weekend_avg` | 76 237, 45 871 |
| `not_found`, `top_404_path` (`top_404_count`) | 10 845, `/pub/winvn/readme.txt` (667) |
| `last_request` | 1995-07-28 13:32:25 |
| `max_gap_minutes`, `max_gap_start` | 22,1, 1995-07-13 19:48:59 |
| `top_bytes_host_type` | com |

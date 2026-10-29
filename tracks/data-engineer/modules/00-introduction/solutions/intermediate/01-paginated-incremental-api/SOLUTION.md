# Lời giải: API phân trang, rate limit, incremental (USGS)

## Cách làm

1. **`page_params`** ghim mọi tham số, kể cả `orderby=time-asc`: phân trang bằng offset chỉ ổn định khi thứ tự
   ổn định. `updatedafter` định dạng UTC có mili giây, không làm tròn watermark.
2. **`fetch_pages`** là generator: người gọi xử lý (ghi đĩa) từng trang ngay, không giữ cả năm trong bộ nhớ.
   - Throttle bằng đồng hồ đơn điệu (`time.monotonic`, không bị chỉnh giờ hệ thống), chỉ nghỉ phần còn thiếu.
   - Dừng ở trang ngắn hơn `page_size`: không cần gọi endpoint `count` trước.
   - `sleep` và `clock` truyền vào để test chạy tức thì và tất định.
3. **`collect`**:
   - mỗi lượt một thư mục `run-NNN`, mỗi trang một tệp thô (ghi tệp tạm rồi `replace`);
   - watermark = `max(updated)` đã thấy, **không** phải thời điểm chạy (đồng hồ máy mình và máy nguồn có thể lệch);
   - `state.json` chỉ ghi sau khi vòng lặp xong: lỗi giữa chừng thì lượt sau chạy lại đúng `run` đó, ghi đè các trang dở.
4. **`load_events`**: gộp mọi lượt rồi upsert theo `id` giữ `updated` lớn nhất. Vì `updatedafter` tính cả mốc
   bằng nên luôn lấy lại ít nhất một bản ghi: thiết kế at-least-once + idempotent, không cố đạt exactly-once ở bước thu thập.
5. **`insights`** và **`write_clean`** như các bài basic.

## Vì sao watermark theo `updated`

Dữ liệu thật trả lời: 100% bản ghi 2024 được sửa sau hơn 30 ngày (trung vị ~70 ngày, có bản sửa sau gần 3 năm).
Watermark theo `time` coi tháng 1 là "đã xong" và bỏ lỡ mọi bản sửa. Full reload mỗi đêm thì đúng nhưng tốn 7 request
(và tăng theo số năm lưu trữ); incremental theo `updated` tốn 1 request mỗi đêm và vẫn đúng.

## Con số tham chiếu (lấy 29/10/2026)

| Khoá | Giá trị |
| --- | --- |
| `events`, `m6_plus`, `m7_plus` | 6 397, 99, 10 |
| `largest_mag`, `largest_place`, `largest_time` | 7,5, 2024 Noto Peninsula, Japan Earthquake, 2024-01-01 |
| `top_region`, `top_region_events` | Indonesia, 605 |
| `busiest_month`, `busiest_month_events` | 4, 705 |
| `tsunami_flagged` | 81 |
| `median_update_lag_days`, `share_updated_after_30d` | 70,8, 1,0 |
| `gutenberg_richter_b` | 1,13 |

Test dùng dung sai (±1% số trận, ±1 trận M7) vì catalog còn được sửa.

## Rubric cho báo cáo

| Mức | Bộ dữ liệu | Làm sạch | Insight | Giới hạn |
| --- | --- | --- | --- | --- |
| Đạt | API, tham số, số trang | Upsert theo `id` | 3 con số đúng | 1 giới hạn |
| Tốt | Số request mỗi lượt | Giải thích vì sao lượt 2 lấy lại bản ghi ở watermark | Watermark theo `updated` có số liệu chứng minh; nối tháng 4 với Hoa Liên | `region` thô, catalog còn sửa |
| Xuất sắc | | Đề xuất lookback (lùi watermark vài phút) để chống lệch đồng hồ | Ước lượng chi phí full vs incremental khi lưu 10 năm | Thang magnitude trộn lẫn |

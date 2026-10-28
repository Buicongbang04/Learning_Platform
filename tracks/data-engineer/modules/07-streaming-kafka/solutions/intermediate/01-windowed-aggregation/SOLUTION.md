# Lời giải: Tumbling và hopping window

## Cách làm

1. `tumbling_window_start = ts - ts % size`.
2. `hopping_window_starts`: window cuối chứa `ts` bắt đầu tại `last = ts - ts % advance`; lùi dần
   theo bước `advance` cho tới `last - size + advance` (cắt ở 0), lọc điều kiện `s <= ts < s + size`
   (cần khi `size` không chia hết cho `advance`).
3. Một hàm `_aggregate(pairs, ...)` nhận các cặp `(window_start, event)` và cộng dồn vào
   `defaultdict` theo `(window_start, key)`. Tumbling sinh một cặp mỗi event, hopping sinh nhiều cặp.
4. Sắp kết quả theo key của dict (tuple) nên không phụ thuộc thứ tự đầu vào.

## Vì sao

- **Window được căn theo mốc thời gian (epoch-aligned)**, không theo event đầu tiên. Nhờ vậy mọi
  instance của processor (mỗi partition một instance) tính ra cùng biên window, kết quả gộp lại được.
- **Biên nửa mở `[start, end)`** để event đúng mốc 60 chỉ thuộc một tumbling window.
- **Hopping nhân bản event**: với `size/advance = k`, mỗi event được cộng vào `k` window, nên
  state và chi phí tăng `k` lần. Đây là lý do "GMV 1 giờ gần nhất, cập nhật mỗi giây" rất đắt;
  thường chọn advance lớn hơn hoặc tính trước tumbling nhỏ rồi cộng dồn (pre-aggregation).
- **Không phụ thuộc thứ tự đầu vào** là tính chất quan trọng của aggregate theo event time:
  event tới lệch thứ tự vẫn cho đúng kết quả, miễn là window chưa bị đóng. Khi nào đóng window là
  chủ đề bài 02 (watermark).
- Đây là phép tính mà Spark viết bằng `groupBy(F.window("event_time", "2 minutes", "1 minute"), "customer_state")`.

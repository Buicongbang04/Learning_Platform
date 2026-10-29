---
title: Heap cho dữ liệu dạng luồng
level: intermediate
services: []
files:
  - path: starter/streaming.py
    note: 3 hàm TODO
  - path: tests/test_streaming.py
    note: Không sửa
run:
  - uv run pytest tracks/data-science/modules/08-coding-for-ds/exercises/intermediate/01-heap-streaming -q
---

## Mục tiêu

Dùng `heapq` cho ba bài toán luồng hay gặp ở vòng DSA của DS: top-k, trung vị chạy, trộn nhiều luồng
đã sắp xếp. Hiểu vì sao phương án "giữ list đã sắp xếp" trông ổn mà vẫn là O(n²).

## Đề bài

Trong `starter/streaming.py`:

1. `top_k_sellers(sales, k)`: `sales` là iterable các cặp `(seller_id, amount)`, có thể là iterator chỉ
   đọc được một lần. Trả k seller có tổng doanh thu lớn nhất dạng `[(seller_id, tổng), ...]`, sắp giảm
   dần theo tổng, bằng nhau thì `seller_id` tăng dần.
2. `running_median(stream)`: list trung vị sau mỗi phần tử (số phần tử chẵn: trung bình hai phần tử
   giữa), kiểu `float`. Yêu cầu O(n log n).
3. `merge_sorted_streams(*streams)`: generator trộn các luồng đã sắp xếp tăng dần thành một luồng tăng
   dần, **lazy**: luồng có thể vô hạn, chỉ đọc phần tử khi cần. Hai giá trị bằng nhau thì phần tử của
   luồng đứng trước ra trước. Không dùng `heapq.merge` (sau khi xong, đọc mã nguồn của nó để so).

## Tiêu chí đạt

- `top_k_sellers` cộng dồn đúng, phá hoà theo `seller_id`, chạy được với iterator.
- `running_median` khớp `statistics.median` của từng tiền tố; 1 000 000 phần tử chạy xong trong 10 giây
  (`bisect.insort` mất vài chục giây trở lên ở cỡ này).
- `merge_sorted_streams` đúng thứ tự, ổn định khi bằng nhau, và lấy được 12 phần tử đầu từ ba luồng vô
  hạn mà không đọc quá 100 000 phần tử của luồng nào.

## Gợi ý

### Gợi ý 1

Top-k: `heapq.nsmallest(k, totals.items(), key=lambda kv: (-kv[1], kv[0]))` giữ một heap cỡ k. Trung
vị: max-heap `low` (lưu số âm) cho nửa dưới, min-heap `high` cho nửa trên; sau mỗi lần đẩy, cân lại sao
cho `len(low) == len(high)` hoặc `len(low) == len(high) + 1`.

### Gợi ý 2

Trộn luồng: heap chứa `(giá trị, chỉ số luồng, iterator)`. Chỉ số luồng vừa phá hoà để ổn định, vừa
tránh Python phải so sánh hai iterator. Pop phần tử nhỏ nhất, `yield`, rồi đẩy phần tử **kế tiếp của
chính luồng đó** (dùng `heapq.heapreplace`). Lấy phần tử đầu tiên an toàn với luồng rỗng bằng
`next(it, sentinel)`.

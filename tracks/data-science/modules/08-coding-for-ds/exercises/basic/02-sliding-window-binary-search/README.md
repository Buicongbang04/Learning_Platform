---
title: Sliding window và binary search trên đáp án
level: basic
services: []
files:
  - path: starter/windows.py
    note: 3 hàm TODO
  - path: tests/test_windows.py
    note: Không sửa
run:
  - uv run pytest tracks/data-science/modules/08-coding-for-ds/exercises/basic/02-sliding-window-binary-search -q
---

## Mục tiêu

Nắm hai mẫu giải hay xuất hiện trong bài toán dữ liệu thời gian và vận hành: cửa sổ trượt cho "đoạn
liên tiếp", và tìm nhị phân trên đáp án khi câu hỏi "đủ chưa?" là đơn điệu.

## Đề bài

Trong `starter/windows.py`:

1. `max_events_in_window(timestamps, window)`: số sự kiện nhiều nhất nằm trong một đoạn đóng
   `[t, t + window]` bất kỳ. `timestamps` đã sắp xếp, có thể trùng. Ví dụ: tải đỉnh (số đơn nhiều nhất
   trong 1 giờ) để chọn cỡ hạ tầng, hay phát hiện thẻ có quá nhiều giao dịch trong 1 phút.
2. `longest_run_within_budget(values, budget)`: độ dài đoạn con liên tiếp dài nhất có tổng `<= budget`,
   `values` không âm.
3. `min_daily_capacity(weights, days)`: sức chứa nhỏ nhất mỗi ngày để giao hết các kiện **theo đúng
   thứ tự** trong tối đa `days` ngày. Mỗi ngày chất kiện theo thứ tự cho tới khi kiện tiếp theo làm vượt
   sức chứa thì sang ngày mới. `weights` khác rỗng, mọi phần tử dương, `days >= 1`.

## Tiêu chí đạt

- Hai hàm sliding window khớp brute force trên 300 input ngẫu nhiên, kể cả rỗng và timestamp trùng.
- `min_daily_capacity` cho sức chứa vừa đủ (giao kịp) và tối thiểu (bớt 1 thì không kịp).
- Input lớn chạy xong trong 10 giây: 200 000 sự kiện với cửa sổ phủ một nửa, 200 000 giá trị, 100 000
  kiện.

## Gợi ý

### Gợi ý 1

Sliding window: con trỏ phải duyệt từng phần tử; trong khi cửa sổ vi phạm điều kiện (rộng hơn
`window`, hoặc tổng vượt `budget`) thì tăng con trỏ trái. Mỗi con trỏ chỉ đi tới, nên tổng O(n). Vì sao
cần `values` không âm cho hàm thứ hai?

### Gợi ý 2

`min_daily_capacity`: viết hàm phụ `days_needed(capacity)` mô phỏng chất hàng (O(n)). Nó giảm khi
`capacity` tăng, nên tìm nhị phân trong `[max(weights), sum(weights)]`: nếu `days_needed(mid) <= days`
thì `hi = mid`, ngược lại `lo = mid + 1`.

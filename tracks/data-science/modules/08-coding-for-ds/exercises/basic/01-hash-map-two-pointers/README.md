---
title: Hash map và two pointers
level: basic
services: []
files:
  - path: starter/hashing.py
    note: 3 hàm TODO
  - path: tests/test_hashing.py
    note: Không sửa
run:
  - uv run pytest tracks/data-science/modules/08-coding-for-ds/exercises/basic/01-hash-map-two-pointers -q
---

## Mục tiêu

Luyện hai mẫu giải O(n) gặp nhiều nhất ở vòng DSA: tra cứu bằng hash map / hash set, và hai con trỏ
trên mảng đã sắp xếp. Test chạy cả input 200 000 phần tử nên lời giải O(n²) sẽ không qua.

## Đề bài

Trong `starter/hashing.py`:

1. `two_sum(nums, target)`: trả cặp chỉ số `(i, j)`, `i < j`, với `nums[i] + nums[j] == target`; `None`
   nếu không có. Nhiều cặp hợp lệ thì chọn cặp có `j` nhỏ nhất, rồi tới `i` nhỏ nhất. Một phần tử
   không được dùng hai lần.
2. `first_duplicate(items)`: giá trị đầu tiên xuất hiện lần thứ hai khi đọc từ trái sang phải (ví dụ
   tìm `order_id` bị ghi trùng đầu tiên trong một log). `None` nếu không trùng.
3. `count_pairs_within_budget(prices, budget)`: số cặp `i < j` có `prices[i] + prices[j] <= budget`,
   với `prices` đã sắp xếp tăng dần (ví dụ: bao nhiêu cách mua combo 2 sản phẩm trong ngân sách).

Trước khi code mỗi hàm, viết ra brute force và độ phức tạp của nó, rồi mới tối ưu.

## Tiêu chí đạt

- `two_sum` đúng thứ tự ưu tiên `(j, i)`, khớp brute force trên 300 input ngẫu nhiên, không dùng một
  phần tử hai lần.
- `first_duplicate` trả đúng giá trị có lần lặp sớm nhất.
- `count_pairs_within_budget` khớp brute force kể cả khi có giá trùng.
- Cả ba hàm chạy xong input 200 000 phần tử trong 10 giây (O(n) hoặc O(n log n)).

## Gợi ý

### Gợi ý 1

`two_sum`: duyệt `j`, tra `target − nums[j]` trong dict giá trị → chỉ số **đầu tiên** của giá trị đó
(`setdefault`), rồi mới thêm `nums[j]` vào dict. `first_duplicate`: một `set`, không phải `list`
(`x in list` là O(n)).

### Gợi ý 2

`count_pairs_within_budget`: `left = 0`, `right = n − 1`. Nếu `prices[left] + prices[right] <= budget`
thì `prices[left]` ghép được với **mọi** phần tử từ `left + 1` tới `right` (vì mảng tăng dần), cộng
`right − left` rồi tăng `left`; ngược lại giảm `right`.

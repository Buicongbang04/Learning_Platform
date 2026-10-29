# Lời giải: heap cho dữ liệu dạng luồng

## top_k_sellers

Hai phần tách bạch: **đếm** bằng dict (một lượt, nên chạy được với iterator chỉ đọc một lần), rồi
**chọn** k phần tử bằng `heapq.nsmallest(k, totals.items(), key=lambda kv: (-kv[1], kv[0]))`.
`nsmallest` giữ một heap cỡ k: $$O(m \log k)$$ với m seller, $$O(k)$$ bộ nhớ thêm. Key `(-tổng, id)`
cho đúng thứ tự giảm theo tổng và phá hoà theo id tăng dần trong một lần so sánh.

`sorted(...)[:k]` cũng cho kết quả đúng với $$O(m \log m)$$; ở cỡ vài nghìn seller không khác biệt. Nêu
được khi nào heap đáng giá (m rất lớn, k nhỏ, hoặc dữ liệu đến dạng luồng không lưu hết được) là điều
người phỏng vấn muốn nghe. Lưu ý `heapq.nlargest` với key `(tổng, id)` sẽ phá hoà sai chiều (id giảm
dần).

## running_median

Bất biến: `low` (max-heap, lưu số âm) chứa nửa nhỏ, `high` (min-heap) chứa nửa lớn, mọi phần tử của
`low` không lớn hơn mọi phần tử của `high`, và `len(low)` bằng `len(high)` hoặc hơn đúng 1.

Mỗi phần tử: đẩy vào `high` nếu lớn hơn đỉnh `low`, ngược lại vào `low`; nếu lệch cỡ thì chuyển đỉnh
của heap đông hơn sang heap kia. Trung vị là đỉnh `low` (lẻ) hoặc trung bình hai đỉnh (chẵn). Mỗi
bước tối đa 3 thao tác heap $$O(\log n)$$, tổng $$O(n \log n)$$.

Vì sao `bisect.insort` không đạt: tìm vị trí $$O(\log n)$$ nhưng chèn vào giữa list phải dời mọi
phần tử phía sau, $$O(n)$$. Đo khi viết bài: 300 000 phần tử, hai heap 0.13 giây, `insort` 4.5 giây;
test dùng 1 000 000 phần tử nên `insort` bị dừng ở 10 giây.

## merge_sorted_streams

Heap chứa đúng một "đại diện" của mỗi luồng: `(giá trị, chỉ số luồng, iterator)`. Pop nhỏ nhất,
`yield`, rồi thay bằng phần tử kế tiếp của chính luồng đó (`heapreplace` gộp pop + push), hoặc pop hẳn
nếu luồng hết. Mỗi phần tử ra tốn $$O(\log k)$$ với k luồng.

- **Lazy**: chỉ đọc phần tử kế tiếp của một luồng khi phần tử trước của nó đã được `yield`. Vì thế lấy
  12 phần tử đầu từ ba luồng vô hạn chỉ đọc khoảng chục phần tử. `sorted(chain(...))` đọc hết luồng
  (test chặn bằng luồng có rào chắn 100 000 phần tử).
- **Ổn định**: hai giá trị bằng nhau thì so tiếp chỉ số luồng, luồng đứng trước ra trước.
- **Không so iterator**: chỉ số luồng là duy nhất nên tuple không bao giờ phải so tới phần tử thứ ba
  (iterator không so sánh được, sẽ ném `TypeError`).

Đây đúng là cách `heapq.merge` cài đặt, và là cách merge sort ngoài (external sort) trộn các file đã sắp
xếp không vừa bộ nhớ, hay cách gộp log đã sắp theo thời gian từ nhiều máy.

# Lời giải: hash map và two pointers

## two_sum

Brute force so mọi cặp là $$O(n^2)$$. Chỗ lãng phí: với mỗi `j`, ta tìm lại từ đầu "có `i` nào bằng
`target − nums[j]` không". Một dict giá trị → chỉ số trả lời câu đó trong $$O(1)$$ trung bình, nên cả
thuật toán là $$O(n)$$ thời gian, $$O(n)$$ bộ nhớ.

Hai chi tiết làm đúng thứ tự ưu tiên của đề:

- Tra **trước**, thêm `nums[j]` vào dict **sau**: không bao giờ ghép một phần tử với chính nó.
- `setdefault` giữ chỉ số **đầu tiên** của mỗi giá trị, nên với `j` nhỏ nhất tìm được, `i` cũng nhỏ
  nhất. Ghi đè (`seen[x] = j`) sẽ trả `(1, 3)` thay vì `(0, 3)` trong test `[1, 1, 4, 5, 2]`.

Vì duyệt `j` tăng dần và trả ngay lần đầu tìm thấy, `j` của kết quả là nhỏ nhất.

## first_duplicate

Một `set` các giá trị đã thấy; giá trị đầu tiên đã có trong set là đáp án. Dùng `list` thì `x in seen`
là $$O(n)$$ và cả hàm thành $$O(n^2)$$: với 200 000 `order_id` đó là khoảng $$2 \times 10^{10}$$ phép
so sánh. Đây là lỗi hay gặp nhất của vòng DSA: thuật toán đúng ý nhưng sai cấu trúc dữ liệu.

## count_pairs_within_budget

Mảng tăng dần, hai con trỏ ở hai đầu. Nếu `prices[left] + prices[right] <= budget` thì với mọi `k`
trong `(left, right]`, `prices[left] + prices[k] <= prices[left] + prices[right] <= budget`: cả
`right − left` cặp đều hợp lệ, đếm một lần rồi tăng `left`. Ngược lại `prices[right]` quá lớn để ghép
với bất kỳ phần tử nào từ `left` trở đi, giảm `right`. Mỗi bước loại một con trỏ nên $$O(n)$$.

Giá trùng không cần xử lý riêng vì ta đếm theo chỉ số, không theo giá trị.

Cách thay thế chấp nhận được: với mỗi `i`, `bisect_right(prices, budget − prices[i])` cho số phần tử
ghép được, $$O(n \log n)$$. Nói được cả hai cách và đánh đổi (two pointers $$O(n)$$, bisect dễ viết
đúng hơn) là câu trả lời tốt.

## Độ phức tạp trong test

Test input lớn dùng n = 200 000 và giới hạn 10 giây. Lời giải mẫu chạy cả ba test dưới 1 giây; bản
brute force của cả ba hàm bị dừng ở mốc 10 giây (đã thử khi viết bài).

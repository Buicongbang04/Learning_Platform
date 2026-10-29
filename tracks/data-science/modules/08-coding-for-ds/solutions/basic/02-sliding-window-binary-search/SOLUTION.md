# Lời giải: sliding window và binary search trên đáp án

## max_events_in_window

Con trỏ `right` duyệt từng sự kiện; trong khi `timestamps[right] − timestamps[left] > window`, tăng
`left`. Lúc đó mọi sự kiện trong `[left, right]` nằm trong đoạn `[timestamps[left], timestamps[left] +
window]`, và đây là cửa sổ lớn nhất kết thúc ở `right`. Đoạn tốt nhất luôn có thể dịch để bắt đầu đúng
ở một sự kiện, nên duyệt mọi `right` là đủ. Hai con trỏ chỉ đi tới: $$O(n)$$.

Đoạn **đóng**: dùng `>` (không phải `>=`) trong điều kiện co. Test `[0, 5, 10]`, `window = 5` cần ra 2.

## longest_run_within_budget

Cùng khung, điều kiện co là "tổng > budget". Đúng vì `values` không âm: thêm phần tử bên phải chỉ làm
tổng tăng, bỏ bên trái chỉ làm tổng giảm (đơn điệu). Nếu có số âm, co cửa sổ có thể làm tổng *tăng*, và
một cửa sổ đang vi phạm vẫn có thể thành hợp lệ khi mở rộng thêm: sliding window cho đáp án sai. Khi đó
dùng prefix sum: tìm `i` nhỏ nhất có `prefix[i] >= prefix[j] − budget`, với cấu trúc giữ prefix max
tăng dần + binary search, $$O(n \log n)$$.

## min_daily_capacity

Hàm `days_needed(c)` mô phỏng chất hàng theo thứ tự ($$O(n)$$) và **không tăng** khi `c` tăng. Vì vậy
tập các `c` "giao kịp" là một nửa đường thẳng `[c*, ∞)`, và ta tìm nhị phân `c*` trong
`[max(weights), sum(weights)]`:

- Cận dưới `max(weights)`: nhỏ hơn thì kiện nặng nhất không lên xe được (mô phỏng sẽ sai).
- Cận trên `sum(weights)`: chở hết trong một ngày.
- Bất biến: đáp án nằm trong `[lo, hi]`. Nếu `mid` đủ thì `hi = mid` (đáp án có thể chính là `mid`);
  nếu không thì `lo = mid + 1`. Vòng dừng khi `lo == hi`.

Độ phức tạp $$O(n \log S)$$ với S là tổng trọng lượng. Với 100 000 kiện nặng tới 1 000, S cỡ
$$5 \times 10^7$$, khoảng 26 lần mô phỏng. Dò tuyến tính từ `max(weights)` lên cần hàng triệu lần mô
phỏng: test dừng nó ở 10 giây.

Mẫu này xuất hiện trong công việc DS dưới dạng khác: ngưỡng điểm model nhỏ nhất để số cảnh báo mỗi ngày
không vượt năng lực đội vận hành (số cảnh báo giảm đơn điệu theo ngưỡng).

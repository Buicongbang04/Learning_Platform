# Lời giải: hình dạng phân phối, thang log và số bins

Code: `distribution.py`.

## Cách làm

- `shape_summary`: `dropna()` một lần, mọi thống kê từ pandas. `tail_ratio` dùng p99 thay vì max vì
  max là một điểm duy nhất, dễ là lỗi dữ liệu; p99 ổn định hơn mà vẫn đo được độ dài đuôi.
- `suggest_scale`: các quy tắc xét theo thứ tự trong docstring. Số âm không có log; đuôi ngắn thì log
  làm méo mà không được gì; có số 0 thì `log1p` (hoặc tách riêng phần bằng 0, tuỳ câu hỏi).
- `fd_bins`: `np.percentile` để khớp numpy, `ceil` số bins, Sturges khi IQR = 0 (FD sẽ chia cho 0).
- `ecdf`: sắp và chia hạng cho n. Không cần thư viện.

## Kết quả trên Olist thật

| Biến | median | p99 | p99/median | skew | Có số 0 | Thang |
| --- | --- | --- | --- | --- | --- | --- |
| `price` (item) | 74.99 | 890.00 | 11.87 | 7.9 | không | log |
| `freight_value` (item) | 16.26 | 84.52 | 5.20 | 5.6 | 383 item | linear |
| `payment_value` | 100.00 | 1 039.92 | 10.40 | 9.3 | 9 dòng (6 voucher, 3 `not_defined`) | log1p |

`fd_bins(price)` = 1 712 bins trên thang tuyến tính, mỗi bin rộng khoảng 3.9 BRL, và 73.6% số bins
**rỗng** vì đuôi dài tới 6 735 BRL. Trên `log10(price)` FD cho 178 bins, phân phối hiện ra gần như
chuông với đỉnh quanh 76 BRL. Quy tắc chọn bins chỉ có nghĩa sau khi chọn đúng thang.

ECDF cho thấy 64.2% item có giá không quá 100 BRL: một câu mà người không làm thống kê hiểu ngay,
và là lý do ECDF tốt cho so sánh nhiều nhóm (đọc thẳng "bao nhiêu phần trăm dưới ngưỡng X").

Với `payment_value`, các dòng bằng 0 là thanh toán bằng voucher hoặc loại `not_defined`, tức một
câu hỏi dữ liệu, không phải chuyện vẽ: trước khi chọn `log1p`, hỏi có nên loại chúng khỏi phân tích
giá trị thanh toán không.

## Sai lầm hay gặp

- Vẽ histogram giá trên thang tuyến tính với 10 bins: 98.3% item rơi vào cột đầu, không thấy gì.
- Log-transform rồi báo cáo trung bình của log mà gọi là "giá trung bình": đó là trung bình nhân.
- Dùng `log` khi có số 0: `-inf` lặng lẽ biến mất khỏi histogram, và bạn mất những dòng có thể quan
  trọng nhất.
- Tin quy tắc Sturges trên dữ liệu lớn: với n = 112 650 Sturges cho 18 bins, quá ít để thấy cấu trúc.

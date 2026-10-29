# Lời giải: SARIMA so với seasonal naive trên Olist

Notebook lời giải: `sarima.ipynb` (chạy được toàn bộ khi đã tải Olist).

## Chuỗi

588 ngày (2017-01-09 tới 2018-08-19), 97 845 đơn. Ngày cao nhất 2017-11-24 (Black Friday) với 1 176
đơn, gấp 6 tới 8 lần các thứ Sáu khác của tháng 11/2017 (143 tới 197 đơn). Trung bình 84 đơn/ngày nửa đầu 2017, 228
đơn/ngày nửa đầu 2018.

## Cấu trúc

- STL (chu kỳ 7, robust): thành phần mùa vụ trung bình +24 đơn thứ Hai, −43 đơn thứ Bảy, −27 đơn
  Chủ nhật. Độ mạnh xu hướng 0.71, độ mạnh mùa vụ 0.23 (theo định nghĩa của Hyndman).
- ADF/KPSS: chuỗi gốc không dừng (ADF p = 0.069, KPSS p ≤ 0.01); sai phân bậc 1 dừng.
- ACF của chuỗi sai phân: âm ở lag 1 (−0.24), dương ở lag 7 (0.23) và 14 (0.18): mùa vụ tuần.
  Đó là lý do chọn `d = 1`, `D = 1`, `m = 7` và một MA mùa vụ.

## Backtest

12 origin, mỗi lần 14 ngày, từ 2018-03-04 tới 2018-08-05:

| Model | MASE trung bình | MASE trung vị | Thắng seasonal naive |
| --- | --- | --- | --- |
| SARIMA(1,1,1)(0,1,1)[7] | 1.191 | 1.107 | 7/12 origin |
| Seasonal naive | 1.261 | 1.168 | |

Khi thử thêm trong lúc soạn bài (cùng 12 origin): ETS cộng tính trend damped + mùa vụ 7 đạt MASE
khoảng 1.22, SARIMA(1,1,1)(1,0,1)[7] khoảng 1.28, SARIMA "airline" (0,1,1)(0,1,1)[7] khoảng 1.23. Không
cấu hình nào thắng seasonal naive quá 6%.

## Đọc kết quả như một senior

- Mức thắng 5–6% nhỏ hơn nhiều so với độ dao động giữa các origin (MASE từ 0.57 tới 2.87). Một lần
  chia train/test duy nhất có thể cho kết luận ngược hẳn: origin 2018-04-15 seasonal naive thắng rõ.
- Origin 2018-05-13 làm mọi model sai nặng: tuần 21–27/5/2018 số đơn giảm còn khoảng một nửa (từ
  1 837 xuống 954 đơn/tuần), trùng thời gian cuộc đình công của tài xế xe tải ở Brazil cuối tháng
  5/2018. Không model đơn biến nào đoán được; cần một kênh để con người đưa sự kiện vào dự báo.
- MASE > 1 ở hầu hết origin: dự báo 14 ngày khó hơn "tuần này bằng tuần trước" một bước trong lịch
  sử. Đó là chuyện bình thường, không phải lỗi.

## Rubric cho phần kết luận

| Tiêu chí | Đạt khi |
| --- | --- |
| Con số | Nêu MASE của cả hai model và tỉ lệ origin thắng |
| So với độ dao động | Nói rõ mức thắng nhỏ so với chênh lệch giữa các origin |
| Bất thường | Nhận ra origin tháng 5/2018 và Black Friday, giải thích vì sao model không thấy |
| Khuyến nghị | Có khuyến nghị dùng được (model nào, kèm khoảng dự báo, điều chỉnh theo sự kiện) |

## Sai lầm hay gặp

- Dùng `orders.groupby(date)` mà quên ngày không có đơn: chuỗi thiếu ngày, lag 7 không còn là "cùng
  thứ tuần trước".
- Chỉ đánh giá một lần chia train/test, hoặc chọn cấu hình SARIMA bằng chính tập test rồi báo cáo
  trên tập đó.
- Tính MASE bằng mẫu số trên toàn chuỗi (dùng dữ liệu tương lai).

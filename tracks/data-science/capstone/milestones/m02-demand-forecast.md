# M02: Dự báo nhu cầu theo ngày

## Mục tiêu

Dự báo số đơn mỗi ngày cho 14 ngày tới, kèm khoảng dự báo có độ phủ đúng như đã hứa, để đội vận hành
và CSKH lập kế hoạch nhân lực. Dự báo này cũng cho biết **mỗi tuần sẽ có bao nhiêu đơn đi qua hệ thống
cảnh báo** ở M03 và M05, nên nó là đầu vào cho phần năng lực trong memo M07.

Milestone này ghép hai bài của module 07: `exercises/intermediate/02-olist-sarima-vs-naive` (dựng
chuỗi, SARIMA, backtest MASE) và `exercises/advanced/02-olist-forecast-intervals` (khoảng dự báo,
coverage, pinball loss). Dùng lại code của bạn từ hai bài đó.

## Việc cần làm

1. **Chuỗi**: `daily_orders(orders, start, end)` trong `project/src/olist_cx/series.py`, số đơn (mọi
   trạng thái) theo ngày mua từ 2017-01-09 tới 2018-08-19, điền 0 cho ngày không có đơn. Test trên vài
   dòng tự dựng.
2. **Đọc cấu trúc**: STL, mùa vụ theo thứ trong tuần, xu hướng, Black Friday 2017. Ghi lại ngày bất
   thường và quyết định xử lý (giữ, đánh dấu bằng biến ngoại sinh, hay loại khỏi phần đánh giá).
3. **Backtest nhiều origin**: horizon 14 ngày, 12 origin cách nhau 14 ngày từ 2018-03-04, mỗi origin
   chỉ dùng dữ liệu trước nó. So ít nhất ba model: seasonal naive (baseline bắt buộc), SARIMA, và một
   model của bạn (ETS, LightGBM với feature lịch, hoặc SARIMAX có biến ngày đặc biệt). Metric chính là
   MASE với mẫu số tính trên phần train của từng origin:

   $$
   \text{MASE} = \frac{\frac{1}{h}\sum_{t=1}^{h} |y_{T+t} - \hat y_{T+t}|}{\frac{1}{T-m}\sum_{t=m+1}^{T} |y_t - y_{t-m}|}, \quad m = 7
   $$

   Báo cáo trung bình **và** độ dao động giữa các origin. Thắng baseline 0.05 MASE khi độ lệch chuẩn
   giữa các origin là 0.5 chưa phải bằng chứng.
4. **Khoảng dự báo 80%**: hiệu chỉnh trên sai số backtest của các origin trước 2018-03-04, đánh giá
   coverage và interval score trên 12 origin ở trên. So khoảng lý thuyết của SARIMA với khoảng thực
   nghiệm (additive và log-ratio).
5. **Từ dự báo sang kế hoạch**: CSKH có chi phí thiếu người gấp 4 lần thừa người. Chọn phân vị lập kế
   hoạch bằng lập luận newsvendor, kiểm bằng pinball loss. Đổi dự báo đơn mỗi ngày thành số đơn đi qua
   bước giao vận chuyển mỗi tuần và số cảnh báo dự kiến nếu hệ thống cảnh báo top 5% đơn.
6. **`reports/FORECAST.md`** (300–600 từ): model chọn và lý do, bảng MASE, coverage thực tế so với danh
   nghĩa, phân vị khuyến nghị, rủi ro (tăng trưởng, ngày lễ, dữ liệu tháng 8/2018 chưa đủ).

Số tham chiếu (Olist thật, bản cài đặt của người soạn):

| Con số | Giá trị |
| --- | --- |
| Chuỗi 2017-01-09 → 2018-08-19 | 588 ngày, 97 845 đơn |
| Ngày cao nhất | 1 176 đơn, 2017-11-24 (Black Friday) |
| Trung bình theo thứ | thứ Hai khoảng 188 đơn, thứ Bảy khoảng 128 đơn |
| MASE seasonal naive, 12 origin | trung bình 1.261, từ 0.69 tới 2.52 giữa các origin |
| Đơn giao xong mỗi tuần, 06/2017 – 07/2018 | trung vị khoảng 1 259, từ 635 tới 2 915 |

## Kết quả nộp

- `project/src/olist_cx/series.py` kèm test.
- `project/notebooks/m02_forecast.ipynb`: cấu trúc chuỗi, backtest, khoảng dự báo, quyết định phân vị.
- `project/reports/FORECAST.md`.

## Tiêu chí đạt

- [ ] Chuỗi đủ 588 ngày, tổng 97 845 đơn; seasonal naive cho MASE trung bình khoảng 1.26 trên 12 origin.
- [ ] Backtest không dùng dữ liệu sau origin (kể cả khi chọn tham số và hiệu chỉnh khoảng).
- [ ] Bảng so sánh có ít nhất ba model, có độ dao động giữa các origin, kết luận không phóng đại mức thắng.
- [ ] Coverage thực tế được báo cáo cạnh mức danh nghĩa 80%, có giải thích khi lệch.
- [ ] Phân vị lập kế hoạch suy ra từ tỉ lệ chi phí (với tỉ lệ 4:1 là 0.8) và được kiểm bằng pinball loss.
- [ ] `FORECAST.md` đổi dự báo ra số cảnh báo mỗi tuần mà M05 và M07 dùng được.

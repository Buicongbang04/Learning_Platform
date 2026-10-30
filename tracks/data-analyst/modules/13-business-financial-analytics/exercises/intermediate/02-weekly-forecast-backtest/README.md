---
title: Dự báo doanh số 8 tuần cho FP&A và chọn phương pháp bằng backtest (Rossmann)
level: intermediate
services: []
files:
  - path: starter/weekly_forecast.ipynb
    note: 7 hàm TODO (chuỗi tuần so sánh được, 3 phương pháp, backtest, tổng hợp) + đọc 4 câu hỏi
  - path: tests/test_weekly_forecast.py
    note: Không sửa
run:
  - uv run python data/download_dataset.py store-sales
  - uv run jupyter lab tracks/data-analyst/modules/13-business-financial-analytics/exercises/intermediate/02-weekly-forecast-backtest/starter/weekly_forecast.ipynb
  - uv run pytest tracks/data-analyst/modules/13-business-financial-analytics/exercises/intermediate/02-weekly-forecast-backtest -q
---

## Mục tiêu

Làm một dự báo doanh số mà phòng tài chính dùng được: dựng chuỗi tuần so sánh được (không bị thiếu cửa hàng làm
tụt giả), viết ba phương pháp đơn giản, chọn phương pháp bằng backtest nhiều điểm cắt và trình bày con số kèm khoảng
sai số và giả định.

## Đề bài

Bộ `store-sales` (Rossmann), tệp `train.csv`: doanh số ngày của 1 115 cửa hàng, 01/01/2013 tới 31/07/2015. FP&A cần
dự báo doanh số tuần toàn chuỗi cho 8 tuần tới. Mở `starter/weekly_forecast.ipynb`:

1. `comparable_stores(train)` và `weekly_sales(train, stores)`: cửa hàng có dữ liệu mọi ngày; doanh số tuần thứ Hai
   tới Chủ nhật, chỉ tuần đủ 7 ngày, kèm cờ tuần có khuyến mãi.
2. `seasonal_naive(history, h, m=52)`, `moving_average(history, h, k=4)`, `promo_average(history, h, promo, k=4)`.
3. `backtest(weekly, forecasters, cutoffs, h=8)` (MAPE và bias mỗi điểm cắt) và `summarize(results)`.
4. Chạy các cell `explore`: so tổng mọi cửa hàng với tổng cửa hàng so sánh được, backtest 6 điểm cắt (thêm ETS để
   so), một điểm cắt có lễ Phục sinh, dự báo 8 tuần sau dữ liệu kèm khoảng. Trả lời bốn câu ở cuối notebook. Báo cáo
   bài học: làm phần trắc nghiệm trong app sau khi chạy notebook.

Định nghĩa chính xác trong notebook. Các hàm không được sửa dữ liệu đầu vào.

## Tiêu chí đạt

- Test trên dữ liệu nhỏ pass: chọn cửa hàng đủ ngày, tuần thứ Hai và bỏ tuần dở dang, cờ khuyến mãi; seasonal naive
  đúng pha cả khi `h > m`; trung bình theo cờ khuyến mãi; backtest không cho phương pháp thấy tương lai, báo lỗi khi
  thiếu thực tế; bảng tổng hợp.
- Trên bộ thật: 934 cửa hàng so sánh được; 133 tuần (07/01/2013 tới 20/07/2015), tổng 5 065 433 519; 71 tuần có
  khuyến mãi; MAPE trung bình 6 điểm cắt: `promo_average` 6.26%, `seasonal_naive` 6.31%, `moving_average` 14.82%.
- Trắc nghiệm trong app: đúng ít nhất 6/8 câu.

## Gợi ý

### Gợi ý 1

Thứ Hai của tuần là `Date - pd.to_timedelta(Date.dt.day_of_week, unit="D")`. Đếm số ngày khác nhau trong tuần bằng
`("Date", "nunique")` rồi lọc bằng 7. `comparable_stores`: số ngày cần có là `(max - min).days + 1`.

### Gợi ý 2

Trong `backtest`, lịch sử là `weekly.loc[weekly.index < cutoff, "sales"]`; truyền **cả** cột `promo` cho phương pháp
(lịch khuyến mãi biết trước), nhưng không truyền doanh số tương lai. `promo_average` lấy cờ tương lai bằng
`promo[promo.index > history.index[-1]].iloc[:h]`.

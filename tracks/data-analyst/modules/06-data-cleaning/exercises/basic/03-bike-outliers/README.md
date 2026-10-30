---
title: Outlier theo thống kê hay theo nghiệp vụ - những ngày lạ của Bike Sharing
level: basic
services: []
files:
  - path: starter/bike_outliers.ipynb
    note: 5 hàm TODO + quyết định xử lý từng loại
  - path: tests/test_bike_outliers.py
    note: Không sửa
run:
  - uv run python data/download_dataset.py bike-sharing-uci
  - uv run jupyter lab tracks/data-analyst/modules/06-data-cleaning/exercises/basic/03-bike-outliers/starter/bike_outliers.ipynb
  - uv run pytest tracks/data-analyst/modules/06-data-cleaning/exercises/basic/03-bike-outliers -q
---

## Mục tiêu

Thấy tận mắt vì sao "bỏ outlier bằng IQR" trước khi train model là một yêu cầu nguy hiểm: quy tắc thống kê bỏ sót
những ngày lạ thật và đánh dấu nhầm những giờ bình thường nhất. Tập phân loại một điểm lạ thành **lỗi đo**, **sự
kiện thật** hoặc **thiếu dữ liệu**, và quyết định theo mục đích sử dụng.

## Đề bài

Bộ `bike-sharing-uci`: `day.csv` (731 ngày) và `hour.csv` (17 379 giờ, thiếu 165 giờ so với 731 × 24). Trưởng nhóm
dự báo nhờ "bỏ outlier" trước khi train model dự báo lượt thuê theo ngày. Mở `starter/bike_outliers.ipynb`:

1. `iqr_flags(s, k=1.5)` và `zscore_flags(s, z=3.0)`: hai quy tắc thống kê, trả `Series[bool]` cùng index.
2. `demand_ratio(day, window=29)`: `cnt` chia trung vị trượt giữa 29 ngày (`min_periods = window // 2 + 1`).
3. `hours_recorded(hour)`: số giờ có dữ liệu mỗi ngày.
4. `flag_days(day, hour, window=29)`: bảng cờ theo ngày, cột `cnt`, `hours`, `iqr`, `zscore`, `demand_drop`
   (`demand_ratio < 0.4`), `sensor_error` (`hum == 0`).
5. Chạy các cell `explore`: IQR trên ngày và trên giờ, bảng ngày bị đánh dấu kèm thời tiết và độ phủ, chart chuỗi
   ngày có trung vị trượt. Quyết định xử lý cho từng loại. Báo cáo bài học: làm phần trắc nghiệm trong app sau khi
   chạy notebook.

Các hàm không được sửa DataFrame đầu vào.

## Tiêu chí đạt

- Test trên dữ liệu nhỏ sinh trong test pass: biên IQR theo nội suy tuyến tính, hiệu ứng masking của z-score, trung
  vị trượt giữa có `min_periods`, đếm giờ đúng, bảng cờ đúng cột và kiểu `bool`.
- Trên bộ thật: IQR và z-score trên `day.cnt` đánh dấu 0 ngày; `demand_drop` 17 ngày; `sensor_error` đúng 1 ngày
  (10/03/2011); ngày 29/10/2012 có 22 lượt và 1 giờ dữ liệu; IQR trên `hour.cnt` đánh dấu 505 giờ, 86.1% thuộc khung
  7-9h và 16-19h.
- Trắc nghiệm trong app: đúng ít nhất 5/7 câu.

## Gợi ý

### Gợi ý 1

`s.quantile(0.25)` và `s.quantile(0.75)` dùng nội suy tuyến tính, khớp với test. `cnt.rolling(29, center=True,
min_periods=15).median()` cho trung vị trượt giữa; không có `center=True` thì cửa sổ chỉ nhìn về quá khứ và lệch 14
ngày.

### Gợi ý 2

`hours_recorded(hour).reindex(day_index, fill_value=0)` để ngày không có giờ nào vẫn có dòng. Dựng DataFrame từ dict
các Series cùng index `dteday` thì các cột tự khớp theo ngày.

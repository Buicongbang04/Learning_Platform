# Lời giải: UCI Air Quality

## Cách làm

1. `load_raw`: `zipfile.ZipFile(...).open("AirQualityUCI.csv")` đưa thẳng vào `pd.read_csv(sep=";", decimal=",")`.
   Không giải nén ra đĩa, không sửa gì: bước thô phải giữ nguyên để so lại khi cần.
2. `clean`:
   - `dropna(how="all")` hai chiều bỏ 114 dòng rỗng và 2 cột `Unnamed`;
   - ghép `Date` + `Time` rồi `to_datetime` với format tường minh (không đoán, không nhầm ngày/tháng);
   - `mask(x == -200)`: chỉ đúng sentinel thành null;
   - `drop_duplicates("ts")` + sắp xếp: một dòng mỗi giờ là khoá tự nhiên của time series.
3. `outages`: cờ `down` = cả 5 cảm biến null; `(down != down.shift()).cumsum()` đánh số đoạn liên tiếp,
   `groupby` lấy `min` và `size`.
4. `monthly_profile`: `groupby(ts.dt.to_period("M"))`, `mean()` tự bỏ qua null; `days` đếm ngày khác nhau
   để biết tháng nào thiếu dữ liệu (tháng 3/2004 chỉ 22 ngày, tháng 4/2005 chỉ 4 ngày).
5. `insights`: các phép `groupby` theo giờ và ngày trong tuần; tháng sạch nhất chỉ xét tháng có ≥ 28 ngày,
   nếu không tháng 4/2005 (4 ngày, toàn ngày nắng ấm) sẽ thắng sai.
6. `write_clean`: tệp tạm rồi `replace`, chạy lại không nhân đôi.

## Vì sao như vậy

- Thay `-200` bằng null **trước** mọi phép tính: trung bình CO thô (còn `-200`) là số âm vô nghĩa.
- Phân biệt "mất kết nối" (cả 5 cảm biến null cùng lúc) với "một máy đo hỏng" (chỉ cột GT null):
  hai loại sự cố cần hai cảnh báo khác nhau trong hệ thống IoT thật.
- Không nội suy: báo cáo nói rõ thiếu ở đâu. Nội suy là quyết định của người dùng dữ liệu, không phải của ingest.

## Con số tham chiếu (bộ thật)

| Khoá | Giá trị |
| --- | --- |
| `rows`, `start`, `end` | 9 357, 2004-03-10 18:00, 2005-04-04 14:00 |
| `missing_share` | `nmhc_gt` 0,902; `co_gt` 0,180; `nox_gt` 0,175; cảm biến 0,039 |
| `nmhc_last_valid` | 2004-05-01 |
| `outage_hours`, `longest_outage_hours`, `longest_outage_start` | 366, 76, 2005-02-08 17:00 |
| `co_peak_hour`, `co_morning_peak_hour`, `co_trough_hour` | 19, 9, 5 |
| `co_weekday_mean`, `co_weekend_mean`, `weekend_drop_pct` | 2,36, 1,65, 29,9 |
| `lowest_co_month` | 2004-08 |

## Rubric cho báo cáo

| Mức | Bộ dữ liệu | Làm sạch | Insight | Giới hạn |
| --- | --- | --- | --- | --- |
| Đạt | Nguồn, giấy phép, số dòng, khoảng thời gian | `-200` → null, tỉ lệ thiếu | 3 con số đúng (giờ đỉnh, cuối tuần, tháng 8) | 1 giới hạn |
| Tốt | Phân biệt cảm biến rẻ và ground truth | Thiếu có cấu trúc: NMHC chết, đợt mất kết nối | Giải thích bằng giao thông, Ferragosto | Múi giờ/DST, thiếu không ngẫu nhiên |
| Xuất sắc | | Đề xuất cảnh báo cho hệ thống IoT (tỉ lệ `-200`, đợt mất kết nối > N giờ) | Nhận ra bước nhảy NOx có thể do thiết bị, đề xuất hỏi chủ nguồn | |

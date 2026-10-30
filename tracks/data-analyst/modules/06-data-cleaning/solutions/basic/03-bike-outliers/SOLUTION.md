# Lời giải: outlier theo thống kê hay theo nghiệp vụ

## Cách làm

- `iqr_flags`: `q1, q3 = s.quantile(0.25), s.quantile(0.75)`, biên `q1 - k * iqr` và `q3 + k * iqr`, so chặt (`<`, `>`).
- `zscore_flags`: `((s - s.mean()) / s.std()).abs() > z`.
- `demand_ratio`: `cnt / cnt.rolling(window, center=True, min_periods=window // 2 + 1).median()`.
- `hours_recorded`: `hour.groupby("dteday").size()`.
- `flag_days`: dựng DataFrame từ các Series cùng index `dteday`; `hours` dùng `reindex(..., fill_value=0)`.

## Kết quả trên bộ thật

| Cách | Trên `day.cnt` | Ghi chú |
| --- | --- | --- |
| IQR 1.5 | 0 ngày | Biên dưới −1 054, thấp hơn mọi giá trị có thể có |
| z-score 3 | 0 ngày | Ngày thấp nhất (22 lượt) có z = −2.31 |
| `demand_drop` | 17 ngày | 12 ngày có `weathersit = 3` hoặc lễ Giáng sinh; 10 ngày thiếu giờ dữ liệu |
| `sensor_error` | 1 ngày | 10/03/2011, `hum = 0` ở cả 22 giờ, trời mưa |

Trên `hour.cnt`, IQR đánh dấu 505 giờ (biên trên 642.5 lượt/giờ): 86.1% rơi vào 7-9h hoặc 16-19h, 82% là ngày làm
việc. Đó là giờ cao điểm đi làm, phần tín hiệu quan trọng nhất của dữ liệu, không phải lỗi.

Ngày 29/10/2012 (bão Sandy, hệ thống đóng cửa) có `demand_ratio` thấp nhất (0.004) nhưng chỉ có **1 giờ** dữ liệu;
30/10/2012 có 11 giờ; 27/01/2011 (bão tuyết) có 8 giờ. Không kiểm độ phủ thì sẽ diễn giải "nhu cầu giảm 99.6%" trong
khi phần lớn là **không đo**.

## Quyết định theo loại

| Loại | Ví dụ | Báo cáo lượt thuê | Train model dự báo ngày thường |
| --- | --- | --- | --- |
| Lỗi đo | `hum = 0` ngày 10/03/2011 | Giữ (lượt thuê đúng) | Đặt `hum` thiếu, điền bằng giá trị ngày lân cận hoặc bỏ cột đó cho ngày này; giữ ngày |
| Sự kiện thật | 29/10/2011 tuyết, 22/04/2012 mưa lớn, 24-26/12 | Giữ, chú thích | Giữ kèm biến thời tiết/ngày lễ, hoặc loại khỏi train nếu model không có các biến đó; ghi rõ |
| Thiếu dữ liệu | 29-30/10/2012, 26-27/01/2011 | Giữ nhưng ghi "hệ thống ngừng" | Loại khỏi train: con số không phải nhu cầu |
| Giờ cao điểm | 8h, 17-18h | Giữ | Giữ: là tín hiệu |

## Đáp án trắc nghiệm

| Câu | Đáp án | Giải thích |
| --- | --- | --- |
| `daily-iqr` | a. 0 ngày | Q1 3 152, Q3 5 956, biên [−1 054, 10 162] chứa mọi ngày |
| `hourly-iqr` | b | 505 giờ, 86% ở 7-9h hoặc 16-19h; nhiều nhất 17h (153), 18h (129), 8h (127) |
| `lowest-day-hours` | c. 1 giờ | Chỉ có giờ 0 của ngày 29/10/2012 |
| `demand-drops` | d. 17 ngày | Xem bảng trong notebook |
| `sensor-fix` | b | Giá trị độ ẩm sai, lượt thuê vẫn đúng; bỏ cả ngày làm mất một quan sát nhu cầu thật; điền 0.5 là bịa số |
| `zscore-miss` | a | std 1 937, mean 4 504: (22 − 4 504) / 1 937 = −2.31. z-score bắt cả hai phía, nhưng dữ liệu trải rộng theo mùa |
| `purpose` | c | Báo cáo mô tả cái đã xảy ra nên giữ; model học nhu cầu ngày thường nên loại hoặc gắn cờ để không học nhầm |

## Sai lầm hay gặp

- Bỏ mọi giờ bị IQR đánh dấu: mất đúng các giờ cao điểm mà đội vận hành cần dự báo nhất.
- Áp IQR trên chuỗi có mùa vụ: ngưỡng tính trên cả năm, nên mùa đông "thấp bất thường" thì không bao giờ vượt ngưỡng.
  So với trung vị trượt (hoặc cùng nhóm giờ × loại ngày) mới có mốc đúng.
- Gọi ngày 29/10/2012 là "nhu cầu thấp kỷ lục" mà không xem độ phủ.

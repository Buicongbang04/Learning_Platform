---
title: Cảnh báo KPI theo ngày với ngưỡng có mùa vụ (Bike Sharing)
level: basic
services: []
files:
  - path: starter/kpi_alerts.ipynb
    note: 5 hàm TODO (baseline, score, bảng cảnh báo, gộp đợt, phân loại) + đọc kết quả
  - path: tests/test_kpi_alerts.py
    note: Không sửa
run:
  - uv run python data/download_dataset.py bike-sharing-uci
  - uv run jupyter lab tracks/data-analyst/modules/13-business-financial-analytics/exercises/basic/03-kpi-anomaly-alerts/starter/kpi_alerts.ipynb
  - uv run pytest tracks/data-analyst/modules/13-business-financial-analytics/exercises/basic/03-kpi-anomaly-alerts -q
---

## Mục tiêu

Dựng một quy tắc cảnh báo KPI hằng ngày mà người nhận không bỏ qua: so với baseline cùng thứ của các tuần trước,
đo độ lệch bằng thang robust, gộp ngày liên tiếp thành một đợt và gắn lý do, rồi so với hai quy tắc ngây thơ
(ngưỡng cố định, giảm so với hôm qua).

## Đề bài

Bộ `bike-sharing-uci`, tệp `day.csv` (731 ngày, 01/01/2011 tới 31/12/2012, đủ mọi ngày), KPI là `cnt` (tổng lượt
thuê mỗi ngày). Head of Operations muốn mỗi sáng nhận tin nhắn khi lượt thuê hôm qua bất thường. Mở
`starter/kpi_alerts.ipynb`:

1. `seasonal_baseline(y, weeks=4)`: median của cùng thứ trong 4 tuần trước.
2. `robust_score(y, baseline, window=56, min_periods=28)`: `ln(y / baseline)` chia cho `1.4826 × MAD` của chính độ
   lệch đó trong 56 ngày **trước** (không tính ngày đang xét).
3. `alert_table`, `alert_episodes`, `triage`: các ngày `|score| > 4`, gộp ngày liên tiếp thành đợt, gắn lý do
   `holiday` / `bad_weather` / `investigate` từ cột `holiday` và `weathersit`.
4. Chạy các cell `explore`: hai quy tắc ngây thơ, quy tắc mùa vụ trên dữ liệu thật, chart, danh sách cần điều tra.
   Trả lời bốn câu ở cuối notebook. Báo cáo bài học: làm phần trắc nghiệm trong app sau khi chạy notebook.

Định nghĩa chính xác (NaN, thứ tự lý do, cột kết quả) nằm trong notebook. Các hàm không được sửa dữ liệu đầu vào.

## Tiêu chí đạt

- Test trên dữ liệu nhỏ pass: baseline đúng thứ và bỏ qua ngoại lệ, thang đo chỉ dùng ngày trước và bỏ `NaN`,
  bảng cảnh báo và hướng, gộp đợt (kể cả bảng rỗng), thứ tự ưu tiên lý do.
- Trên bộ thật: 675 ngày có score (từ 26/02/2011); 39 ngày cảnh báo (36 drop), 26 đợt; ngày tệ nhất 29/10/2012
  (22 lượt so với baseline 6 326.5, score khoảng −57.9); lý do: 25 `investigate`, 11 `bad_weather`, 3 `holiday`.
- Trắc nghiệm trong app: đúng ít nhất 6/8 câu.

## Gợi ý

### Gợi ý 1

`pd.concat([y.shift(7 * k) for k in range(1, weeks + 1)], axis=1).median(axis=1, skipna=False)` cho baseline.
Thang đo: `ratio.shift(1).rolling(window, min_periods=min_periods).apply(f, raw=True)`, trong đó `f` dùng
`np.nanmedian` để bỏ qua các ngày chưa có baseline.

### Gợi ý 2

Gộp đợt: `(dates.diff() != pd.Timedelta(days=1)).cumsum()` đánh số đợt, ngày đầu tiên luôn mở đợt mới. Phân
loại: `np.select([holiday == 1, weathersit >= 3], ["holiday", "bad_weather"], default="investigate")`, điều kiện
đứng trước được ưu tiên.

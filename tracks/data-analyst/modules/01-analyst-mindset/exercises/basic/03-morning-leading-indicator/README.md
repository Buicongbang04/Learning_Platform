---
title: Chỉ số dẫn trước - lượt thuê trước 10h có báo trước được cả ngày không?
level: basic
services: []
files:
  - path: starter/morning_signal.ipynb
    note: 4 hàm TODO + đọc kết quả
  - path: tests/test_morning_signal.py
    note: Không sửa
run:
  - uv run python data/download_dataset.py bike-sharing-uci
  - uv run jupyter lab tracks/data-analyst/modules/01-analyst-mindset/exercises/basic/03-morning-leading-indicator/starter/morning_signal.ipynb
  - uv run pytest tracks/data-analyst/modules/01-analyst-mindset/exercises/basic/03-morning-leading-indicator -q
---

## Mục tiêu

Phân biệt leading và lagging indicator bằng việc làm thật: lấy một ứng viên leading indicator, biến nó thành dự
báo, đo sai số, và thấy vì sao phải kiểm theo phân khúc trước khi đưa cho đội vận hành dùng.

## Đề bài

Bộ `bike-sharing-uci`, `hour.csv` (17 379 giờ, 01/01/2011 tới 31/12/2012). Trưởng ca vận hành của Capital
Bikeshare theo dõi **tổng lượt thuê cả ngày** (lagging), nhưng phải quyết định điều xe lúc 10h sáng. Bạn kiểm
xem **lượt thuê trước 10h** có báo trước được tổng cả ngày không. Mở `starter/morning_signal.ipynb`:

1. `daily_signal(hour, cutoff=10)`: mỗi ngày một dòng, cột `morning` (lượt các giờ trước `cutoff`), `total`,
   `workingday`; index là ngày.
2. `morning_share(daily)`: tỉ lệ tổng lượt buổi sáng trên tổng lượt cả ngày, tách theo `workingday`.
3. `nowcast(daily, share)`: dự báo tổng ngày = lượt buổi sáng / tỉ lệ của đúng loại ngày.
4. `median_ape(actual, forecast)`: sai số tương đối tuyệt đối trung vị, bỏ ngày tổng bằng 0.
5. Chạy các cell `explore`: so tỉ lệ theo loại ngày với một tỉ lệ chung, kiểm ngoài mẫu (tỉ lệ 2011 dự báo
   2012), xem những ngày sai nặng nhất, thử cutoff 8h và 12h. Báo cáo bài học: làm phần trắc nghiệm trong app
   sau khi chạy notebook.

Các hàm không được sửa DataFrame đầu vào.

## Tiêu chí đạt

- Test trên dữ liệu nhỏ pass: giờ đúng bằng `cutoff` không tính vào buổi sáng, ngày không có giờ buổi sáng có
  `morning = 0`, tỉ lệ là tỉ lệ của tổng (không phải trung bình tỉ lệ từng ngày), dự báo dùng tỉ lệ đúng loại
  ngày, sai số bỏ ngày tổng bằng 0.
- Trên bộ thật: 731 ngày, tổng 3 292 679 lượt; tỉ lệ buổi sáng 13.70% (cuối tuần/lễ) và 26.14% (ngày làm việc);
  sai số trung vị 8.86% khi tách loại ngày, 25.04% khi dùng một tỉ lệ chung; 8.00% khi lấy tỉ lệ 2011 dự báo 2012.
- Trắc nghiệm trong app: đúng ít nhất 6/8 câu.

## Gợi ý

### Gợi ý 1

`hour["cnt"].where(hour["hr"] < cutoff, 0)` giữ lượt của giờ buổi sáng và đặt 0 cho giờ khác; nhóm theo
`pd.to_datetime(hour["dteday"])` rồi `sum()` là ra `morning`, kể cả ngày không có giờ buổi sáng nào.

### Gợi ý 2

Tỉ lệ của tổng: `groupby("workingday")[["morning", "total"]].sum()` rồi chia hai cột. Dự báo:
`daily["workingday"].map(share)` cho mỗi ngày tỉ lệ của loại ngày đó.

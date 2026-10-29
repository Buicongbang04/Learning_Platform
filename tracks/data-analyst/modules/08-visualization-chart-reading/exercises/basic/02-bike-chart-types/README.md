---
title: Line, bar, heatmap, stacked trên Bike Sharing - chuẩn bị dữ liệu và đọc chart
level: basic
services: []
files:
  - path: starter/bike_charts.ipynb
    note: 4 hàm TODO + đọc 4 chart
  - path: tests/test_bike_charts.py
    note: Không sửa
run:
  - uv run python data/download_dataset.py bike-sharing-uci
  - uv run jupyter lab tracks/data-analyst/modules/08-visualization-chart-reading/exercises/basic/02-bike-chart-types/starter/bike_charts.ipynb
  - uv run pytest tracks/data-analyst/modules/08-visualization-chart-reading/exercises/basic/02-bike-chart-types -q
---

## Mục tiêu

Đi từ bốn câu hỏi của bốn stakeholder tới bốn chart (line, bar, heatmap, stacked 100%): biết mỗi chart
cần dữ liệu ở **hình dạng** nào (chuỗi theo ngày, bảng xếp hạng, ma trận 7 × 24, tỉ trọng theo
tháng), tự chuẩn bị đúng hình dạng đó bằng pandas, rồi đọc chart theo quy trình 5 bước, bắt đầu từ
việc kiểm tra nhãn và đơn vị.

## Đề bài

Bộ `bike-sharing-uci`, tệp `hour.csv` (17 379 giờ, 2011–2012). Cell đầu notebook tự tải bộ này nếu
chưa có (`ensure("bike-sharing-uci")`). Mở `starter/bike_charts.ipynb`, làm lần lượt:

1. `daily_rides(hour) -> Series`: tổng `cnt` mỗi ngày, index là `DatetimeIndex` tăng dần. Vẽ line
   chart kèm trung bình trượt 28 ngày.
2. `rides_by_season(hour) -> Series`: tổng `cnt` theo mùa, index là nhãn `spring`, `summer`, `fall`,
   `winter` (hằng `SEASON_LABELS`), sắp **giảm dần**. Vẽ bar giữ thứ tự mùa.
3. Chạy cell kiểm tra mỗi mã `season` gồm những ngày nào; đối chiếu với lịch và ghi nhận xét.
4. `weekday_hour_matrix(hour) -> DataFrame`: ma trận 7 × 24 (hàng `weekday` 0–6, cột `hr` 0–23) của
   **trung bình** `cnt`, ô không có dữ liệu là `NaN`. Vẽ heatmap.
5. `casual_share_by_month(hour) -> DataFrame`: mỗi tháng lịch một dòng (index ngày đầu tháng), cột
   `casual`, `registered` là tỉ trọng (cộng lại bằng 1). Vẽ stacked bar 100%.
6. Đọc 4 chart theo quy trình 5 bước, tách quan sát khỏi kết luận. Báo cáo bài học: làm phần trắc
   nghiệm trong app sau khi chạy notebook.

Các hàm không được sửa DataFrame đầu vào.

## Tiêu chí đạt

- Test trên dữ liệu nhỏ sinh trong test pass: tổng theo ngày, nhãn mùa và thứ tự giảm dần, ma trận đủ
  7 × 24 với `NaN` ở ô thiếu, tỉ trọng theo tháng cộng lại bằng 1.
- Trên bộ thật: 731 ngày, tổng 3 292 679 lượt (2011: 1 243 103; 2012: 2 049 576); ô heatmap cao nhất
  là thứ Ba 17h (khoảng 544 lượt/giờ); 24 tháng tỉ trọng.
- Notebook vẽ đủ 4 chart, mỗi chart có headline nói kết luận chứ không chỉ tên metric.
- Trắc nghiệm trong app: đúng ít nhất 6/8 câu.

## Gợi ý

### Gợi ý 1

`read_csv` đọc `dteday` thành chuỗi; đổi bằng `pd.to_datetime` **bên trong** hàm, gán vào biến mới
chứ không ghi đè cột của `hour`. `Series.groupby(other_series)` nhóm theo một Series cùng index mà
không cần thêm cột. Với mùa: `total.index.map(SEASON_LABELS)`.

### Gợi ý 2

`hour.pivot_table(index="weekday", columns="hr", values="cnt", aggfunc="mean")` rồi
`.reindex(index=range(7), columns=range(24))` để luôn đủ ô. Tháng lịch:
`pd.to_datetime(hour["dteday"]).dt.to_period("M").dt.to_timestamp()`; tỉ trọng:
`total.div(total.sum(axis=1), axis=0)`.

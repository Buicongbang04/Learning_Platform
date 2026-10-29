---
title: Cảm biến IoT thật (UCI Air Quality) - sentinel, mất kết nối, nhịp ô nhiễm
level: basic
services: []
files:
  - path: starter/air_quality.ipynb
    note: 6 hàm TODO + 2 biểu đồ
  - path: starter/report.md
    note: Báo cáo 4 mục, đang là TODO
  - path: tests/test_air_quality.py
    note: Không sửa
run:
  - uv run python data/download_dataset.py air-quality-uci
  - uv run pytest tracks/data-engineer/modules/00-introduction/exercises/basic/03-iot-air-quality -q
---

## Mục tiêu

Làm việc với dữ liệu **IoT** thật: đọc định dạng CSV kiểu châu Âu, nhận ra giá trị thiếu được mã hoá
bằng sentinel `-200`, phân biệt "cảm biến mất kết nối" với "một máy đo hỏng", và từ một năm số đo theo
giờ rút ra nhịp ô nhiễm của một con phố.

## Đề bài

Bộ `air-quality-uci` (UCI #360, CC BY 4.0) là 9 357 giờ số đo của một trạm cảm biến khí ở Ý, từ
10/03/2004 tới 04/04/2005. Cell đầu notebook tự tải bộ này nếu chưa có.

Mở `starter/air_quality.ipynb`, làm lần lượt:

1. `load_raw(zip_path)`: đọc `AirQualityUCI.csv` ngay trong zip (`sep=";"`, `decimal=","`).
2. `clean(raw)`: bỏ dòng/cột rỗng, ghép `Date` + `Time` thành `ts`, đổi tên cột theo `COLUMNS`,
   **chỉ** `-200` thành null, một dòng mỗi giờ, sắp theo `ts`.
3. `outages(df)`: các đợt cả 5 cảm biến cùng null (cột `start`, `hours`).
4. `monthly_profile(df)`: trung bình theo tháng và tỉ lệ thiếu CO.
5. `insights(df) -> dict`: 15 khoá trong bảng của notebook (tỉ lệ thiếu, đợt mất kết nối dài nhất,
   giờ CO cao/thấp nhất, ngày thường vs cuối tuần, tháng sạch nhất).
6. `write_clean(df, out_dir)`: ghi đè `data/clean/air-quality-uci/hourly.parquet`.
7. Ít nhất 2 biểu đồ trong cell `explore` (CO theo giờ; bản đồ nhiệt tỉ lệ thiếu theo tháng).
8. `starter/report.md`: 4 mục **Bộ dữ liệu**, **Làm sạch**, **Insight** (có số), **Giới hạn**.

## Tiêu chí đạt

- Test trên fixture nhỏ (luôn chạy) pass: đọc đúng dấu phẩy thập phân, `-200` thành null nhưng `-1,5 °C` giữ nguyên, bỏ giờ trùng.
- Trên bộ thật: 9 357 dòng liên tục từng giờ; `nmhc_gt` thiếu ~90%; 366 giờ mất kết nối, đợt dài nhất 76 giờ từ 2005-02-08 17:00; CO đỉnh sáng lúc 9h, đỉnh chiều lúc 19h; cuối tuần thấp hơn ~30%.
- `write_clean` gọi hai lần vẫn đúng số dòng.
- Notebook có ít nhất 2 cell `explore` vẽ biểu đồ; `report.md` đủ 4 mục, không còn TODO, Insight có số.

## Gợi ý

### Gợi ý 1

In `raw.tail()` và `(raw == -200).sum()` trước khi viết `clean`. `pd.to_datetime(date + " " + time,
format="%d/%m/%Y %H.%M.%S")`. `DataFrame.mask(cond)` thay ô thoả điều kiện bằng null.

### Gợi ý 2

Đánh số các đoạn liên tiếp: `run = (flag != flag.shift()).cumsum()`, rồi `groupby(run[flag])` để lấy
giờ đầu và độ dài mỗi đợt. Giờ trong ngày: `df.groupby(df["ts"].dt.hour)["co_gt"].mean()`; giờ cao nhất
buổi sáng: `.loc[0:11].idxmax()`.

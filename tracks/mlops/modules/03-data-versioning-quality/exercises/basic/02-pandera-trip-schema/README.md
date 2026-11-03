---
title: Schema Pandera cho chuyến taxi, bắt bốn loại lỗi dữ liệu thật
level: basic
services: []
files:
  - path: starter/schema.py
    note: 5 TODO
  - path: tests/test_schema.py
    note: Không sửa
run:
  - uv run pytest tracks/mlops/modules/03-data-versioning-quality/exercises/basic/02-pandera-trip-schema -q
---

## Mục tiêu

Viết schema Pandera như một "hàng rào" ở cửa vào pipeline: bắt đúng những dòng bẩn đã gặp ở NYC TLC mà không báo oan
dòng sạch.

## Đề bài

Trong `starter/schema.py`, hoàn thành `trip_schema(month)` trả về `pandera.DataFrameSchema` cho một tháng (`month` dạng
`"2019-01"`). DataFrame có các cột `tpep_pickup_datetime`, `tpep_dropoff_datetime`, `trip_distance`, `PULocationID`,
`DOLocationID`, `passenger_count` (có thể thiếu giá trị). Schema phải bắt bốn loại lỗi sau, mỗi loại là một luật riêng:

1. **thời lượng**: `dropoff` không muộn hơn `pickup` (thời lượng âm hoặc bằng 0). Đây là luật nhiều cột (`DataFrameSchema` check).
2. **distance**: `trip_distance` phải lớn hơn 0.
3. **ngày**: `pickup` phải nằm trong tháng `month` (tệp 2019-01 có chuyến ghi năm 2008 và 2018).
4. **zone**: `PULocationID` và `DOLocationID` trong khoảng 1 đến 265.

Ngoài ra `coerce=True` cho các cột, `passenger_count` cho phép `NaN`, và `validate_trips(df, month)` trả về
`df` nếu sạch hoặc ném `pandera.errors.SchemaErrors` gom **mọi** lỗi của mọi dòng (validation lazy), không dừng ở lỗi đầu tiên.

## Tiêu chí đạt

- DataFrame sạch đi qua, kể cả khi `passenger_count` có `NaN` và chuyến bắt đầu lúc 23:59 ngày cuối tháng.
- Mỗi loại lỗi chèn riêng lẻ cho ra đúng tập chỉ số dòng lỗi, không dòng nào khác.
- Khi một dòng vi phạm nhiều luật, mọi luật đều được báo trong cùng một lần gọi.
- `validate_trips` không sửa DataFrame đầu vào.

## Gợi ý

### Gợi ý 1

Luật nhiều cột đặt ở `DataFrameSchema(checks=pa.Check(lambda df: ...))`; hàm trả Series boolean cùng chỉ số với `df` để Pandera
biết dòng nào sai. Luật theo cột đặt trong `pa.Column(checks=...)`.

### Gợi ý 2

Mốc tháng: `start = pd.Timestamp(month + "-01")`, `end = start + pd.offsets.MonthBegin(1)`; hợp lệ là `start <= pickup < end`.
Gọi `schema.validate(df, lazy=True)`. Pandera trả lỗi qua `SchemaErrors.failure_cases` (có cột `index`).

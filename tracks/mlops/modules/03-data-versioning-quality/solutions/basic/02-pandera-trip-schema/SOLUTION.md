# Lời giải: schema Pandera cho chuyến taxi

Ba loại luật Pandera, mỗi loại hợp với một lỗi:

| Lỗi | Cách khai báo | Vì sao |
| --- | --- | --- |
| `trip_distance` bằng 0 | `pa.Column(float, pa.Check.gt(0))` | luật trên một cột, có sẵn |
| zone ngoài 1-265 | `pa.Check.in_range(1, 265)` | khoảng đóng hai đầu |
| ngày ngoài tháng | `pa.Check(lambda s: (s >= start) & (s < end))` | cửa sổ nửa mở `[start, end)` để chuyến 23:59 ngày cuối tháng vẫn hợp lệ |
| thời lượng ≤ 0 | check ở cấp `DataFrameSchema(checks=...)` | luật cần hai cột cùng lúc |

Mấu chốt:

- `validate(df, lazy=True)` gom lỗi của mọi dòng rồi ném `SchemaErrors`; không `lazy` thì dừng ở lỗi đầu và bạn sửa từng lỗi một
  qua nhiều lần chạy pipeline. `failure_cases["index"]` cho chỉ số dòng, dùng để quarantine thay vì vứt cả lô.
- `nullable=True` cho `passenger_count` vì TLC để trống ở vài nghìn chuyến: đây là lỗi *chất lượng* ta chấp nhận, không phải
  lỗi *hợp đồng*. Quyết định cột nào nullable là quyết định của data contract, không phải của schema.
- `coerce=True` biến `int32`/`float32` về kiểu chuẩn trước khi kiểm; không có nó, Parquet từ đợt export khác kiểu sẽ báo lỗi kiểu giả.
- Cửa sổ `end` dùng `MonthBegin(1)` thay vì cộng 31 ngày, vì tháng có 28-31 ngày.

---
title: Pivot table, bảng YoY và chart lượt thuê xe theo tháng - Bike Sharing 2011–2012
level: intermediate
services: []
files:
  - path: starter/bike_pivot.xlsx
    note: Cột Year + bảng YoY TODO; tự tạo pivot table và chart
  - path: tests/test_bike_pivot.py
    note: Không sửa
run:
  - libreoffice --calc tracks/data-analyst/modules/02-spreadsheets/exercises/intermediate/02-bike-pivot-chart/starter/bike_pivot.xlsx
  - uv run pytest tracks/data-analyst/modules/02-spreadsheets/exercises/intermediate/02-bike-pivot-chart -q
---

## Mục tiêu

Tóm tắt 731 ngày dữ liệu bằng pivot table, đối chiếu pivot với bảng SUMIFS dựng tay, tính tăng trưởng
cùng kỳ năm trước (YoY) đúng cách và vẽ một chart so sánh hai năm.

## Đề bài

Head of Operations của Capital Bikeshare hỏi: *"2012 tăng so với 2011 bao nhiêu, và tăng đều cả năm
hay dồn vào vài tháng?"*

Workbook `starter/bike_pivot.xlsx` có sheet `Days` là toàn bộ `day.csv` của Bike Sharing (UCI, CC BY
4.0): 731 ngày, 12 cột (`cnt` = `casual` + `registered`).

1. `Days!M` (`Year`): `=YEAR(A2)`, kéo hết 731 dòng.
2. **Pivot table** trên sheet mới tên `Pivot`: Rows = `mnth`, Columns = `Year`, Values = Sum of `cnt`
   (LibreOffice: chọn A1:M732, Insert > Pivot Table; Excel: Insert > PivotTable).
3. Sheet `YoY`: B2:C13 lượt thuê theo tháng của 2011 và 2012 bằng `SUMIFS` theo `Year` và `mnth`; D2:D13
   tăng trưởng = 2012 / 2011 − 1; dòng 14 là cả năm (D14 tính từ tổng, không lấy trung bình cột D).
   Đối chiếu với pivot: hai bảng phải ra cùng số.
4. **Chart** cột hoặc đường có 2 series (2011, 2012) theo tháng, đặt trên sheet `YoY` hoặc `Pivot`. Đổi
   tiêu đề chart thành kết luận.

Lưu `.xlsx` (Keep Current Format; pivot và chart được giữ trong `.xlsx`) rồi chạy test. Làm thêm phần
trắc nghiệm trong app.

## Tiêu chí đạt

- `Days!M2:M732` là công thức YEAR; `YoY!B2:D14` là công thức, khớp tính lại từ `Days`.
- Có pivot table với hàng `mnth`, cột `Year`, giá trị Sum of `cnt`; vùng kết quả có 38 189 (01/2011),
  218 573 (09/2012), tổng 1 243 103 và 2 049 576.
- Cả năm 2012 tăng 64.9% so với 2011.
- Có chart cột/đường với ít nhất 2 series.
- Trắc nghiệm trong app: đúng ít nhất 4/6 câu.

## Gợi ý

### Gợi ý 1

`=SUMIFS(Days!$L$2:$L$732,Days!$M$2:$M$732,2011,Days!$D$2:$D$732,A2)`. Thay `2011` bằng ô tiêu đề
nếu muốn một công thức cho cả hai cột (tiêu đề phải là số 2011, không phải chữ "Rentals 2011").

### Gợi ý 2

Test đọc định nghĩa pivot trong tệp `.xlsx`, nên phải lưu dạng Excel 2007-365. Chart: chọn `YoY!B1:C13`,
Insert > Chart, loại Column hoặc Line; nhãn trục x lấy từ `A2:A13`.

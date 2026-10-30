---
title: Báo cáo doanh thu Germany và France theo tháng - IF, SUMIFS, COUNTIFS, AVERAGEIF, MIN/MAX
level: basic
services: []
files:
  - path: starter/revenue_report.xlsx
    note: 4 cột phụ TODO + 3 bảng và 7 chỉ số ở sheet Report
  - path: tests/test_revenue_report.py
    note: Không sửa
run:
  - libreoffice --calc tracks/data-analyst/modules/02-spreadsheets/exercises/basic/03-sumifs-revenue-report/starter/revenue_report.xlsx
  - uv run pytest tracks/data-analyst/modules/02-spreadsheets/exercises/basic/03-sumifs-revenue-report -q
---

## Mục tiêu

Dựng một báo cáo doanh thu kiểu "quốc gia × tháng" hoàn toàn bằng công thức: định nghĩa doanh thu ở
một cột phụ, tổng hợp bằng SUMIFS/COUNTIFS, tính AOV đúng ở dòng tổng, và dùng các hàm tổng hợp cơ
bản (SUM, AVERAGE, COUNT, COUNTA, MIN, MAX) để mô tả dữ liệu.

## Đề bài

Country manager Đức và Pháp cần bảng doanh thu, số đơn, AOV ba tháng 9–11/2011. Workbook
`starter/revenue_report.xlsx` có sheet `Data` gồm **mọi** dòng (6 810 dòng, kể cả đơn huỷ và dòng
điều chỉnh) của khách Germany và France trong kỳ, Online Retail II (CC BY 4.0), sắp theo
`InvoiceDate` rồi `Invoice`.

1. Sheet `Data`, cột phụ (hàng 2, kéo xuống):
   - I `Valid`: 1 nếu `Invoice` không bắt đầu bằng `C`, `Quantity > 0`, `Price > 0`; ngược lại 0 (`IF` + `AND`).
   - J `Revenue`: `Quantity * Price` nếu Valid = 1, ngược lại 0.
   - K `Month`: số dạng `yyyymm` (`YEAR(E2)*100+MONTH(E2)`).
   - L `OrderStart`: 1 ở dòng đầu của mỗi hoá đơn không huỷ (`Invoice` khác dòng trên và không bắt đầu bằng `C`).
2. Sheet `Report`:
   - Doanh thu B3:D4 bằng **một** công thức SUMIFS kéo ra cả bảng (khoá đúng `$`); cột E và dòng 5 là tổng.
   - Số đơn B8:D9 bằng COUNTIFS trên `OrderStart`; cột E và dòng 10 là tổng.
   - AOV B13:E15 = doanh thu / số đơn, kể cả dòng 15 và cột E.
   - Khối chỉ số H2:H8: số dòng (`COUNTA`), số dòng hợp lệ, doanh thu trung bình mỗi dòng hợp lệ
     (`AVERAGEIF`), doanh thu dòng lớn nhất, ngày giao dịch đầu và cuối (`MIN`, `MAX`), số dòng có
     Customer ID (`COUNT`).

Lưu `.xlsx` rồi chạy test. Làm thêm phần trắc nghiệm trong app.

## Tiêu chí đạt

- Mọi ô TODO là công thức đúng họ hàm, giá trị khớp tính lại từ 8 cột gốc.
- Tổng 3 tháng: 166 426.86 GBP, 311 đơn, AOV 535.13 GBP; France 10/2011 AOV 956.73 GBP.
- Khối chỉ số: 6 810 dòng, 6 622 hợp lệ, dòng lớn nhất 4 161.06 GBP, 01/09/2011 09:40 tới 30/11/2011 16:47,
  6 761 dòng có Customer ID.
- Trắc nghiệm trong app: đúng ít nhất 4/6 câu.

## Gợi ý

### Gợi ý 1

Ô B3: `=SUMIFS(Data!$J$2:$J$6811,Data!$H$2:$H$6811,$A3,Data!$K$2:$K$6811,B$2)`. `$A3` khoá cột
nhãn quốc gia, `B$2` khoá hàng nhãn tháng; kéo sang phải và xuống là xong bảng.

### Gợi ý 2

AOV dòng tổng (B15:E15) là **tổng doanh thu chia tổng số đơn** (`=B5/B10`), không phải
`AVERAGE(B13:B14)`. Ô L2 so `A2` với `A1` (tiêu đề), vẫn đúng vì tiêu đề không trùng mã hoá đơn nào.

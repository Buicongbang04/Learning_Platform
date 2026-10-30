---
title: Làm sạch văn bản Online Retail II bằng TRIM, PROPER, UPPER/LOWER, SUBSTITUTE, REPLACE, CONCAT
level: basic
services: []
files:
  - path: starter/text_cleanup.xlsx
    note: 8 cột TODO (I–P) + 4 ô Summary
  - path: tests/test_text_cleanup.py
    note: Không sửa
run:
  - libreoffice --calc tracks/data-analyst/modules/02-spreadsheets/exercises/basic/01-text-cleanup/starter/text_cleanup.xlsx
  - uv run pytest tracks/data-analyst/modules/02-spreadsheets/exercises/basic/01-text-cleanup -q
---

## Mục tiêu

Chuẩn hoá cột văn bản bẩn của dữ liệu bán lẻ thật bằng hàm spreadsheet, giữ cột gốc bên cạnh cột
sạch, và hiểu vì sao mã hàng phải được chuẩn hoá trước khi tra cứu hay ghép bảng.

## Đề bài

Workbook `starter/text_cleanup.xlsx` có 300 dòng thật của Online Retail II (sheet `Year 2010-2011`,
CC BY 4.0, nguồn ghi ở sheet `README`): 255 dòng chọn ngẫu nhiên cộng các dòng có quốc gia viết tắt,
mã hàng chữ thường và mô tả có hai dấu cách liền nhau. Giá trị gốc giữ nguyên, kể cả khoảng trắng thừa.

Ở sheet `Lines`, điền công thức vào hàng 2 của 8 cột nền vàng rồi kéo xuống tới hàng 301:

| Cột | Tên | Yêu cầu |
| --- | --- | --- |
| I | `StockCode_clean` | Mã hàng bỏ khoảng trắng, viết HOA: `UPPER` + `TRIM` |
| J | `Description_clean` | Mô tả bỏ khoảng trắng thừa, viết hoa chữ đầu mỗi từ: `PROPER` + `TRIM` |
| K | `Country_clean` | `EIRE` → `Ireland`, `RSA` → `South Africa`, `USA` → `United States`: `SUBSTITUTE` lồng nhau |
| L | `Line_type` | `"Cancel"` nếu `Invoice` bắt đầu bằng `C`, ngược lại `"Sale"`: `IF` + `LEFT` |
| M | `Customer_masked` | Che ký tự thứ 3–4 của mã khách bằng `**` (`13085` → `13**5`) bằng `REPLACE`; mã trống → `"Guest"` |
| N | `Line_key` | `Invoice-StockCode_clean`, ví dụ `536406-21730`: `CONCAT` (hoặc `&`) |
| O | `Slug` | Mô tả gốc đã TRIM, chữ thường, dấu cách thành `-`: `LOWER` + `SUBSTITUTE` + `TRIM` |
| P | `Had_extra_spaces` | 1 nếu mô tả gốc khác bản đã TRIM (so phân biệt hoa thường bằng `EXACT`), ngược lại 0 |

Sheet `Summary`: B2 số dòng có mô tả thừa khoảng trắng, B3 số dòng huỷ, B4 số dòng khách vãng lai,
B5 số dòng có mã hàng gốc khác mã đã chuẩn hoá (gợi ý: `SUMPRODUCT` với `EXACT`).

Lưu dạng `.xlsx` (LibreOffice: Keep Current Format) rồi chạy test. Làm thêm phần trắc nghiệm trong app.

## Tiêu chí đạt

- Mọi ô I2:P301 và Summary!B2:B5 là **công thức** đúng họ hàm yêu cầu; ô gõ cứng giá trị làm test FAIL.
- Giá trị khớp quy tắc TRIM/PROPER/SUBSTITUTE/REPLACE trên cả 300 dòng (test tự tính lại từ cột gốc).
- Summary: 83 dòng mô tả thừa khoảng trắng, 5 dòng huỷ, 95 dòng khách vãng lai, 17 dòng mã hàng có chữ thường.
- Trắc nghiệm trong app: đúng ít nhất 4/6 câu.

## Gợi ý

### Gợi ý 1

`TRIM` vừa bỏ dấu cách hai đầu vừa gộp các dấu cách liền nhau ở giữa, nên `PROPER(TRIM(C2))` xử lý
`ZINC WILLIE WINKIE  CANDLE STICK` thành `Zinc Willie Winkie Candle Stick`. Mô tả trống thì công thức
trả chuỗi rỗng, không sao.

### Gợi ý 2

`REPLACE(G2,3,2,"**")` chạy được trên số (tự đổi thành text). Kiểm mã trống trước:
`=IF(G2="","Guest",REPLACE(G2,3,2,"**"))`. Với B5:
`=SUMPRODUCT(--NOT(EXACT(Lines!B2:B301,Lines!I2:I301)))` đếm số dòng mà mã gốc khác mã đã chuẩn hoá
(dấu `=` thường không phân biệt hoa thường, `EXACT` thì có).

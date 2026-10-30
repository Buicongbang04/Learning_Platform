---
title: Tra danh mục giá cho đơn hàng tháng 12/2011 - XLOOKUP, VLOOKUP, HLOOKUP, INDEX/MATCH
level: basic
services: []
files:
  - path: starter/catalog_lookup.xlsx
    note: 5 cột TODO (G–K) + 6 ô Summary
  - path: tests/test_catalog_lookup.py
    note: Không sửa
run:
  - libreoffice --calc tracks/data-analyst/modules/02-spreadsheets/exercises/basic/02-catalog-lookup/starter/catalog_lookup.xlsx
  - uv run pytest tracks/data-analyst/modules/02-spreadsheets/exercises/basic/02-catalog-lookup -q
---

## Mục tiêu

Gắn thông tin từ bảng tham chiếu vào dòng giao dịch bằng bốn cách tra cứu, luôn khớp chính xác,
xử lý "không tìm thấy" có chủ đích, và đọc được con số mà tra cứu làm lộ ra.

## Đề bài

Head of International Sales hỏi: *"Tháng 12 khách nước ngoài mua giá thấp hơn bảng giá bao nhiêu, và
bao nhiêu doanh thu đến từ hàng mới chưa có trong bảng giá?"*. Bảng giá duy nhất có trong tay là danh
mục năm trước.

Workbook `starter/catalog_lookup.xlsx` (Online Retail II, CC BY 4.0, nguồn ở sheet `README`):

- `Orders`: 1 518 dòng bán hợp lệ của khách ngoài Anh, 01–09/12/2011.
- `Catalog`: 4 101 mã hàng của sheet `Year 2009-2010`; cột A `Description`, cột B `StockCode`, cột C
  `ListPrice` (giá xuất hiện nhiều nhất năm đó). Mã nằm **bên phải** mô tả, sắp theo mô tả.
- `Regions`: bảng **ngang**, hàng 1 là quốc gia, hàng 2 là `EU`/`Non-EU` (thành viên EU năm 2011).

Sheet `Orders`, điền hàng 2 rồi kéo xuống hết bảng:

| Cột | Tên | Yêu cầu |
| --- | --- | --- |
| G | `Description` | Mô tả từ Catalog theo `StockCode` (cột D). `XLOOKUP` hoặc `INDEX/MATCH` (VLOOKUP không tra sang trái được); không thấy → `"NOT IN CATALOG"` |
| H | `ListPrice` | `VLOOKUP` khớp chính xác trên `Catalog!B:C`; không thấy → `""` (bọc `IFNA`) |
| I | `Region` | `HLOOKUP` quốc gia (cột C) trên bảng ngang `Regions` |
| J | `LineValue` | `Quantity * Price` |
| K | `DiscountPct` | `1 - Price / ListPrice`; ListPrice trống → `""` |

Sheet `Summary`: B2 số dòng `NOT IN CATALOG`; B3 số dòng có `DiscountPct > 0`; B4 tổng doanh thu; B5
doanh thu của dòng `NOT IN CATALOG` (`SUMIFS`); B6 tỉ trọng doanh thu khách EU; B9 giá niêm yết của mã
nhập ở B8 bằng `INDEX/MATCH` (không sửa B8).

Lưu `.xlsx` rồi chạy test. Làm thêm phần trắc nghiệm trong app.

## Tiêu chí đạt

- Mọi ô G2:K1519 và Summary B2:B6, B9 là công thức đúng họ hàm (G: XLOOKUP hoặc INDEX; H: VLOOKUP; I:
  HLOOKUP); giá trị khớp từng dòng.
- Summary: 440 dòng không có trong danh mục, 260 dòng bán dưới giá niêm yết, doanh thu 46 188.59 GBP,
  trong đó 17 297.98 GBP là hàng không có trong danh mục, khách EU chiếm 91.1%, giá mã `22423` là 12.75.
- Trắc nghiệm trong app: đúng ít nhất 4/6 câu.

## Gợi ý

### Gợi ý 1

`=XLOOKUP(D2,Catalog!$B$2:$B$4102,Catalog!$A$2:$A$4102,"NOT IN CATALOG")`. Khoá vùng tra cứu bằng `$`
trước khi kéo xuống. Bản không có XLOOKUP:
`=IFNA(INDEX(Catalog!$A$2:$A$4102,MATCH(D2,Catalog!$B$2:$B$4102,0)),"NOT IN CATALOG")`.

### Gợi ý 2

VLOOKUP thiếu tham số cuối là khớp **gần đúng**; Catalog sắp theo mô tả chứ không theo mã, nên kết quả
sẽ là giá của mã khác mà không báo lỗi. Viết `VLOOKUP(D2,Catalog!$B$2:$C$4102,2,FALSE)`. HLOOKUP tương
tự: `HLOOKUP(C2,Regions!$B$1:$S$2,2,FALSE)`.

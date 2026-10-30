---
title: File export "bẩn" từ ERP - encoding, delimiter, dấu thập phân, ngày dd/mm
level: basic
services: []
files:
  - path: starter/messy_export.ipynb
    note: 5 hàm TODO + đọc kết quả
  - path: tests/test_messy_export.py
    note: Không sửa
run:
  - uv run jupyter lab tracks/data-analyst/modules/05-data-collection/exercises/basic/02-messy-erp-export/starter/messy_export.ipynb
  - uv run pytest tracks/data-analyst/modules/05-data-collection/exercises/basic/02-messy-erp-export -q
---

## Mục tiêu

Đọc đúng một file CSV xuất từ hệ thống khác trước khi tính bất cứ con số nào: nhận ra encoding, delimiter, dấu thập
phân, thứ tự ngày, dòng thừa đầu/cuối, giữ đúng kiểu cho mã; rồi đối chiếu với control total của hệ thống nguồn.

## Đề bài

Tệp `tests/fixtures/ventes_france_2011-11.csv` gồm **1 580 dòng thật** của Online Retail II (UCI, CC BY 4.0): mọi
dòng hoá đơn của khách Pháp tháng 11/2011, xuất lại theo định dạng một hệ thống ERP cài tiếng Pháp (cp1252, `;`, dấu
thập phân `,`, ngày `dd/mm/yyyy HH:MM`, 2 dòng mở đầu, dòng `Total lignes;1580` ở cuối). Nội dung từng dòng giữ
nguyên bộ gốc; chỉ định dạng tệp là mô phỏng.

Trưởng nhóm kinh doanh châu Âu hỏi: *"Tháng 11 khách Pháp mua bao nhiêu, bao nhiêu khách, bao nhiêu đơn bị huỷ?"*
Mở `starter/messy_export.ipynb`:

1. `detect_encoding(raw)`: `utf-8-sig` (có BOM), `utf-8`, hoặc `cp1252`.
2. `sniff_delimiter(line)`: ký tự xuất hiện nhiều nhất trong `;`, `,`, tab, `|` trên dòng tiêu đề.
3. `read_export(path)`: bảng 8 cột tên chuẩn (`Invoice`, `StockCode`, `Description`, `Quantity`, `InvoiceDate`,
   `Price`, `Customer ID`, `Country`), mã là chuỗi, `Customer ID` kiểu `Int64`, ngày đọc theo dd/mm.
4. `control_total(path)`: số dòng ghi ở dòng `Total lignes`.
5. `summarize(df)`: số dòng, hoá đơn, hoá đơn huỷ, khách, dòng hợp lệ, doanh thu (định nghĩa chung của track).
6. Chạy các cell `explore`: ba cách đọc "nhanh" hỏng ra sao, đọc ngày kiểu Mỹ thì sai bao nhiêu dòng, phí vận
   chuyển chiếm bao nhiêu doanh thu. Báo cáo bài học: làm phần trắc nghiệm trong app sau khi chạy notebook.

Các hàm không được sửa DataFrame đầu vào.

## Tiêu chí đạt

- Test trên dữ liệu nhỏ pass: nhận đúng BOM/UTF-8/cp1252, chọn đúng delimiter, giữ `02113` và `C573868` là chuỗi,
  `03/11/2011` là ngày 3 tháng 11, `2,55` là 2.55, ô `Customer ID` trống là `<NA>` chứ không làm cả cột thành số thực.
- Trên tệp thật: 1 580 dòng bằng đúng control total, mọi ngày nằm trong tháng 11/2011, 76 hoá đơn (12 hoá đơn huỷ),
  40 khách, 1 544 dòng hợp lệ, doanh thu 31 758.71 GBP.
- Trắc nghiệm trong app: đúng ít nhất 6/8 câu.

## Gợi ý

### Gợi ý 1

Đọc bytes một lần, giải mã, `splitlines()`. Tìm chỉ số dòng bắt đầu bằng `Facture`, lấy từ đó trở đi, bỏ dòng
bắt đầu bằng `Total`, rồi đưa phần còn lại vào `pd.read_csv(io.StringIO("\n".join(body)), ...)`.

### Gợi ý 2

`pd.read_csv(..., sep=sep, decimal=",", dtype={"Facture": str, "Code article": str, "N° client": "Int64"})`, đổi tên
bằng `RENAME`, rồi `pd.to_datetime(df["InvoiceDate"], format="%d/%m/%Y %H:%M")`. Ghi rõ `format` thay vì để pandas tự
đoán: pandas đoán theo dòng đầu tiên (`01/11/2011`), và đoán sai thì hoặc lỗi, hoặc âm thầm đổi tháng.

---
title: Một phần tư số dòng không có mã khách - bỏ, điền hay giữ? Memo cho Head of CRM
level: advanced
services: []
files:
  - path: starter/missing_customer.ipynb
    note: 2 hàm TODO + điều tra cơ chế thiếu
  - path: starter/MEMO.md
    note: Memo một trang - cơ chế thiếu, ảnh hưởng tới chỉ số, khuyến nghị
  - path: tests/test_missing_customer.py
    note: Không sửa
run:
  - uv run python data/download_dataset.py online-retail-ii
  - uv run jupyter lab tracks/data-analyst/modules/06-data-cleaning/exercises/advanced/02-missing-customer-id/starter/missing_customer.ipynb
  - uv run pytest tracks/data-analyst/modules/06-data-cleaning/exercises/advanced/02-missing-customer-id -q
---

## Mục tiêu

Ra quyết định xử lý dữ liệu thiếu như DA senior: thu thập bằng chứng về **cơ chế thiếu** (MCAR, MAR, MNAR) thay vì
đoán, đo ảnh hưởng của từng cách xử lý (bỏ, điền, giữ) lên từng chỉ số, và chọn cách khác nhau cho các chỉ số khác
nhau. Viết memo để Head of CRM biết báo cáo quý tính thế nào và phải hỏi ai.

## Đề bài

Bộ `online-retail-ii`, sheet **`Year 2010-2011`**, dòng hợp lệ theo định nghĩa dùng chung. Khoảng 25% dòng không có
`Customer ID`; team CRM định bỏ hết hoặc điền cho đủ trước khi tính báo cáo khách hàng quý. Mở
`starter/missing_customer.ipynb`:

1. `missing_profile(df, col, by)`: số dòng, số dòng thiếu `col`, tỉ lệ thiếu theo từng giá trị của `by`; sắp số dòng
   giảm dần.
2. `invoice_summary(lines, col="Customer ID")`: một dòng mỗi hoá đơn với `lines`, `revenue`, `missing` (mọi dòng
   thiếu), `mixed` (có dòng thiếu và có dòng không), `country`, `hour` (giờ của dòng sớm nhất).
3. Điều tra: thiếu ở mức dòng hay hoá đơn; tập trung theo quốc gia, giờ, tháng; hoá đơn thiếu mã khác hoá đơn có mã
   thế nào (số dòng, giá trị, số lượng, giá đơn vị); ảnh hưởng lên doanh thu, AOV, số khách, khách giá trị cao, tỉ lệ
   quay lại nếu bỏ hoặc nếu điền một mã chung.
4. Viết `starter/MEMO.md` theo khung có sẵn (250-700 từ, dòng đầu là headline có con số, đủ các mục).

## Tiêu chí đạt

- `missing_profile` và `invoice_summary` đúng trên dữ liệu nhỏ (thứ tự, kiểu, hoá đơn lẫn lộn, giờ của dòng sớm nhất).
- Trên bộ thật: UK 485 123 dòng hợp lệ, tỉ lệ thiếu 27.0%; tổng 132 220 dòng thiếu; 19 960 hoá đơn, 1 428 hoá đơn
  thiếu mã, 0 hoá đơn lẫn lộn, doanh thu hoá đơn thiếu mã 1 755 276.64 GBP; trung vị số dòng 15 (có mã) so với 36.
- `MEMO.md` không còn TODO, đủ mục, headline có con số. Nội dung chấm theo rubric trong `SOLUTION.md`.

## Gợi ý

### Gợi ý 1

`groupby("Invoice")` trên cột cờ `isna()`: `.all()` cho hoá đơn thiếu toàn bộ, `.any() & ~.all()` cho hoá đơn lẫn
lộn. Sắp theo `InvoiceDate` trước khi lấy `first` nếu bạn muốn "dòng đầu tiên" có nghĩa.

### Gợi ý 2

Tách câu hỏi theo chỉ số: doanh thu có cần biết khách là ai không? Tỉ lệ quay lại thì sao? Một cách xử lý có thể đúng
cho chỉ số này và sai cho chỉ số kia. Thử điền một mã "GUEST" rồi xếp hạng khách theo doanh thu để thấy chuyện gì xảy
ra.

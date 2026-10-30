---
title: Star schema cho Online Retail II - fact dòng hàng, dimension sạch, unknown member
level: basic
services: []
files:
  - path: starter/star_schema.sql
    note: 3 bảng TODO (dim_product, dim_customer, fct_sales_line); dim_date có sẵn làm mẫu
  - path: starter/run_star.py
    note: Chạy thử trên dữ liệu thật, không chấm
  - path: tests/test_star_schema.py
    note: Không sửa
run:
  - uv run python data/download_dataset.py online-retail-ii
  - uv run python tracks/data-analyst/modules/09-analytics-data-modeling/exercises/basic/02-retail-star-schema/starter/run_star.py
  - uv run pytest tracks/data-analyst/modules/09-analytics-data-modeling/exercises/basic/02-retail-star-schema -q
---

## Mục tiêu

Biến bảng giao dịch phẳng của Online Retail II thành star schema mà dashboard join vào không bao giờ làm sai
tổng: khai báo grain đúng với dữ liệu, dựng dimension một dòng mỗi khoá từ dữ liệu bẩn, giữ khách vãng lai bằng
unknown member, và đặt từng cột (giá, quốc gia) vào đúng chỗ.

## Đề bài

Team BI sắp dựng dashboard sản phẩm và khách hàng trên DuckDB. Bạn viết `starter/star_schema.sql` (nhiều câu
lệnh, chạy tuần tự) đọc bảng `raw_sales_lines`: sheet `Year 2010-2011` của bộ `online-retail-ii` nguyên trạng
(tên cột như tệp xlsx: `Invoice`, `StockCode`, `Description`, `Quantity`, `InvoiceDate`, `Price`,
`Customer ID`, `Country`) cộng cột `source_row` là số thứ tự dòng trong tệp (bắt đầu từ 1).

Tệp đã có view `valid_lines` (dòng hợp lệ theo định nghĩa chung: bỏ hoá đơn `C...`, `Quantity <= 0`,
`Price <= 0`) và bảng `dim_date` làm mẫu. Viết ba bảng còn lại (cột và quy tắc chi tiết ghi ngay trong tệp):

1. `dim_product(product_key, stock_code, description, is_merchandise)`: một dòng mỗi mã có dòng hợp lệ. 220 mã có
   nhiều mô tả: chọn mô tả xuất hiện trên nhiều dòng hợp lệ nhất, hoà thì lấy mô tả nhỏ nhất theo chữ cái.
   `is_merchandise` sai với mã không bắt đầu bằng 5 chữ số (`POST`, `DOT`, `M`, `AMAZONFEE`...).
2. `dim_customer(customer_key, customer_id, current_country, first_purchase_date)`: một dòng mỗi khách có mã
   (`current_country` là quốc gia của dòng hợp lệ muộn nhất, SCD type 1) **cộng** dòng unknown member
   `customer_key = 0` cho khách vãng lai.
3. `fct_sales_line(line_key, invoice_no, date_key, customer_key, product_key, country, quantity, unit_price,
   revenue)`: grain một dòng hợp lệ, `line_key = source_row`. Không bỏ dòng nào của `valid_lines`, không để khoá
   ngoại rỗng; `country` là quốc gia ghi trên dòng.

Dùng `CREATE OR REPLACE` để tệp chạy lại được. `starter/run_star.py` dựng star trên dữ liệu thật và in số dòng,
doanh thu theo nhóm khách/hàng hoá để bạn tự kiểm. Làm xong, mở app làm phần **Báo cáo bài học** (trắc nghiệm).

## Tiêu chí đạt

- Test trên dữ liệu nhỏ sinh trong test pass: đúng cột, đúng dòng hợp lệ (kể cả hai dòng cùng hoá đơn, cùng
  mã), mô tả chuẩn và quy tắc hoà, unknown member, quốc gia hiện tại, khoá trong fact, tệp chạy lại được.
- Mọi khoá dimension unique, mọi khoá ngoại của fact có trong dimension, join fact với ba dimension giữ nguyên
  tổng doanh thu.
- Trên bộ thật: fact 530 105 dòng, doanh thu 10 666 702.54 GBP, 132 220 dòng của khách vãng lai;
  `dim_product` 3 922 mã (22 mã không phải hàng hoá); `dim_customer` 4 339 dòng; `dim_date` 374 ngày.
- Trắc nghiệm trong app (tuỳ chọn): đúng ít nhất 4/6 câu.

## Gợi ý

### Gợi ý 1

Mô tả chuẩn: `GROUP BY stock_code, description` để đếm, rồi
`row_number() OVER (PARTITION BY stock_code ORDER BY n DESC, description)` và giữ `rk = 1`. Khoá thay thế:
`row_number() OVER (ORDER BY stock_code)`, ép `INTEGER`. Kiểm hàng hoá: `regexp_matches(stock_code, '^[0-9]{5}')`.

### Gợi ý 2

`dim_customer` là `UNION ALL` của một dòng hằng (`SELECT 0, NULL, 'Unknown', NULL`) với truy vấn
`GROUP BY customer_id`; DuckDB có `arg_max(country, invoiced_at)` cho "quốc gia ở lần mua muộn nhất". Trong fact,
`LEFT JOIN dim_customer` rồi `coalesce(customer_key, 0)`: inner join sẽ làm mất 16.5% doanh thu.

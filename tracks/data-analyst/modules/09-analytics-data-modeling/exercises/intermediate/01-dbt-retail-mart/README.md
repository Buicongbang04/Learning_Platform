---
title: Project dbt staging → mart doanh thu tháng, có test đối soát và định nghĩa cột
level: intermediate
services: []
files:
  - path: starter/models/staging/stg_sales_lines.sql
    note: 1 TODO (cờ dòng hợp lệ)
  - path: starter/models/marts/fct_sales_line.sql
    note: TODO
  - path: starter/models/marts/dim_customer.sql
    note: TODO
  - path: starter/models/marts/mart_monthly_sales.sql
    note: TODO
  - path: starter/models/marts/_marts.yml
    note: TODO mô tả + data test
  - path: starter/data_tests/assert_mart_reconciles_to_fact.sql
    note: TODO singular test đối soát
  - path: starter/dbt_project.yml
    note: Có sẵn
  - path: starter/models/staging/_sources.yml
    note: Có sẵn
  - path: starter/models/staging/_staging.yml
    note: Có sẵn, mẫu cú pháp test
  - path: tests/test_dbt_mart.py
    note: Không sửa
run:
  - uv run python data/download_dataset.py online-retail-ii
  - uv run pytest tracks/data-analyst/modules/09-analytics-data-modeling/exercises/intermediate/01-dbt-retail-mart -q
---

## Mục tiêu

Đưa định nghĩa "doanh thu tháng" ra khỏi các truy vấn dashboard rời rạc, vào một project dbt có tầng staging,
fact, dimension và mart; mỗi cột của mart có định nghĩa; data test chặn được lỗi mà schema test không thấy.

## Đề bài

Dashboard doanh thu tháng hiện có ba phiên bản SQL do ba người viết. Bạn dựng project dbt (adapter `dbt-duckdb`)
làm nguồn duy nhất. Test đóng vai bước EL: nạp sheet `Year 2010-2011` của `online-retail-ii` nguyên trạng vào
`raw.sales_lines` (tên cột như xlsx + `source_row`), sinh `profiles.yml` trong thư mục tạm rồi chạy `dbt build`
trên bản sao `starter/`. Cột và quy tắc chi tiết ghi trong từng tệp.

1. `stg_sales_lines`: đã đổi tên, ép kiểu; viết cờ `is_valid_sale` (định nghĩa chung của track). Staging không lọc.
2. `fct_sales_line`: grain một dòng hợp lệ; thêm `invoice_month`, `is_guest`, `revenue`.
3. `dim_customer`: grain một khách có mã; `first_purchase_date`, `cohort_month`, `current_country` (SCD type 1).
4. `mart_monthly_sales`: grain một tháng; `revenue`, `orders`, `active_customers`, `new_customers`, `aov`,
   `is_complete_month` (tháng chưa đủ thì `false`, ví dụ 12/2011 dừng ở 09/12).
5. `_marts.yml`: mô tả model (nói rõ grain) và **mô tả từng cột của mart như một định nghĩa metric** (tính gì,
   cộng được qua tháng không); data test: `unique` + `not_null` cho `fct_sales_line.line_id`,
   `dim_customer.customer_id`, `mart_monthly_sales.month`; `relationships` từ `fct_sales_line.customer_id` tới
   `dim_customer`.
6. `data_tests/assert_mart_reconciles_to_fact.sql`: singular test so tổng doanh thu và số đơn của mart với fact.
   Test của bài thay mart của bạn bằng một bản "của Marketing" bỏ khách vãng lai: schema test vẫn xanh, test đối
   soát của bạn phải đỏ.

Chạy thử bằng lệnh `pytest` ở trên: test in tên node dbt bị lỗi. Làm xong, mở app làm phần **Báo cáo bài học**.

## Tiêu chí đạt

- `dbt build` thành công trên dữ liệu nhỏ sinh trong test; staging giữ đủ 10 dòng, fact 7 dòng, mart 3 tháng với
  doanh thu 19, 20, 16, AOV 9.5, 10, 16 và tháng cuối `is_complete_month = false`.
- Đủ data test đề yêu cầu; một singular test dùng `ref()` tới cả mart và fact; mô tả mart có chữ "grain", mỗi cột
  mart có mô tả từ 15 ký tự, không còn `TODO`.
- Mart bỏ khách vãng lai làm singular test của bạn FAIL.
- Trên bộ thật: 13 tháng; 11/2011 doanh thu 1 509 496.33 GBP, 2 769 đơn, 1 664 khách, 323 khách mới, AOV 545.14;
  12/2010 có 885 khách mới bằng đúng số khách hoạt động; 12/2011 chưa đủ tháng, AOV 779.99; tổng 13 tháng
  10 666 702.54 GBP và 4 338 khách mới.
- Trắc nghiệm trong app (tuỳ chọn): đúng ít nhất 4/6 câu.

## Gợi ý

### Gợi ý 1

`date_trunc('month', invoice_date)` trả `TIMESTAMP` trên DuckDB: ép `cast(... as date)`. Khách mới: tổng hợp
`dim_customer` theo `cohort_month` rồi `left join` vào bảng tháng, `coalesce(new_customers, 0)`. Ngày cuối tháng:
`month + interval 1 month - interval 1 day`, so với `max(invoice_date)` của cả fact (`cross join` một CTE một dòng).

### Gợi ý 2

Singular test là một `select` trả về dòng lỗi: tổng hợp mart thành một dòng (`sum(revenue)`, `sum(orders)`), fact
thành một dòng (`sum(revenue)`, `count(distinct invoice_no)`), `cross join`, rồi
`where abs(mart_revenue - fct_revenue) > 0.01 or mart_orders <> fct_orders`. `sum(orders)` qua các tháng đúng vì
mỗi hoá đơn chỉ thuộc một tháng; với `active_customers` thì không.

# Lời giải: project dbt staging → mart doanh thu tháng

## Cách làm

Lời giải đầy đủ là project trong thư mục này (cùng cây với `starter/`):

1. **`stg_sales_lines.sql`**: `is_valid_sale = not starts_with(Invoice, 'C') and Quantity > 0 and Price > 0`.
   Staging giữ đủ mọi dòng; cờ là tài liệu sống của định nghĩa.
2. **`fct_sales_line.sql`**: `where is_valid_sale`, `cast(date_trunc('month', invoice_date) as date)`,
   `customer_id is null as is_guest`, `quantity * unit_price as revenue`.
3. **`dim_customer.sql`**: `group by customer_id` trên dòng hợp lệ có mã; `min(invoice_date)`,
   `arg_max(country, invoiced_at)`.
4. **`mart_monthly_sales.sql`**: CTE tổng hợp fact theo tháng (`sum`, `count(distinct)`), CTE đếm khách mới theo
   `cohort_month` của `dim_customer`, CTE một dòng `max(invoice_date)`; `left join` + `coalesce` cho khách mới,
   `revenue / orders` cho AOV, so ngày cuối tháng với ngày bán cuối cho `is_complete_month`.
5. **`_marts.yml`**: mô tả grain cho cả ba model, mô tả từng cột của mart theo kiểu định nghĩa metric (cộng được
   qua tháng hay không), test `unique`/`not_null`/`relationships` theo đề.
6. **`data_tests/assert_mart_reconciles_to_fact.sql`**: một dòng tổng của mart `cross join` một dòng tổng của fact,
   trả dòng khi lệch. Lời giải có thêm `assert_fct_revenue_positive.sql` (dòng hợp lệ mà doanh thu `<= 0` là lọc sai).

## Vì sao như vậy

- **Staging không lọc**: dòng huỷ là dữ liệu cho model khác (doanh thu ròng, tỉ lệ huỷ, ghép đơn huỷ với đơn gốc
  như module 08). Lọc ở staging thì mọi model sau mất chúng, và định nghĩa "hợp lệ" bị giấu trong một `WHERE`.
- **Khách mới lấy từ `dim_customer`, không tính lại trong mart**: một nơi định nghĩa "lần mua đầu"; bài Advanced
  và dashboard khác dùng lại cùng cột `cohort_month`.
- **Metric non-additive tính lại từ fact**: `active_customers` và `aov` của tháng phải tính từ dòng, không cộng hay
  lấy trung bình từ bảng ngày. Mô tả cột ghi rõ "không cộng qua các tháng", vì BI tool mặc định `SUM`.
- **`is_complete_month` thay cho việc xoá tháng dở**: dashboard vẫn hiện tháng 12/2011 nhưng có thể vẽ nét đứt và
  không so MoM. Xoá tháng thì mất thông tin; không gắn cờ thì người xem tưởng doanh thu giảm 58%.
- **Test đối soát là test duy nhất bắt được lỗi định nghĩa**: bản mart bỏ khách vãng lai có tháng unique, không null,
  kiểu đúng; mỗi dòng "hợp lệ", chỉ tổng sai. Schema test kiểm từng dòng, singular test kiểm quan hệ giữa các bảng.

## Con số tham chiếu (bộ thật, sheet `Year 2010-2011`)

| Tháng | revenue | orders | active | new | aov | complete |
| --- | --- | --- | --- | --- | --- | --- |
| 2010-12 | 823 746.14 | 1 559 | 885 | 885 | 528.38 | true |
| 2011-01 | 691 364.56 | 1 086 | 741 | 417 | 636.62 | true |
| 2011-09 | 1 058 590.17 | 1 837 | 1 266 | 299 | 576.26 | true |
| 2011-10 | 1 154 979.30 | 2 040 | 1 364 | 358 | 566.17 | true |
| 2011-11 | 1 509 496.33 | 2 769 | 1 664 | 323 | 545.14 | true |
| 2011-12 | 638 810.68 | 819 | 615 | 41 | 779.99 | false |
| Cộng 13 tháng | 10 666 702.54 | 19 960 | 13 054 (không có nghĩa) | 4 338 | | |

`dbt build` trên bộ thật (4 model và các test) mất khoảng 5 giây trên laptop.

## Đáp án trắc nghiệm

- `dec2010-new` (b) **885**: bằng toàn bộ khách hoạt động tháng đó, vì sheet bắt đầu 01/12/2010 nên ai cũng "lần
  đầu". Mô tả cột/metric phải ghi lưu ý này; dùng thêm sheet 2009-2010 làm lịch sử sẽ sửa được. 41 (a) là khách mới
  tháng 12/2011; 323 (c) là tháng 11/2011.
- `dec2011-aov` (c): tháng chỉ có dữ liệu tới 09/12 12:50, và hoá đơn 581483 (168 470 GBP, huỷ sau 12 phút) nằm
  trong doanh thu gộp của 819 đơn. Không phải hành vi khách (a), không phải lỗi cộng trùng (b): test đối soát xanh.
- `sum-active` (d) **13 054**. 4 346 (b) là tổng số khách theo **quốc gia**, một lỗi cộng khác.
- `staging-no-filter` (a). dbt cho `WHERE` ở mọi model (b, c sai); nhiều dòng hơn không làm nhanh hơn (d).
- `buggy-mart` (b): lỗi ở tổng, không ở dòng. Schema test chạy trên mọi model có khai báo (a sai); materialization
  không ảnh hưởng việc chạy test (d sai).
- `severity` (c): tỉ lệ khách vãng lai là tín hiệu cần xem, không làm số sai: `warn` với ngưỡng. Khoá, đối soát và
  khoá ngoại sai thì số trên dashboard sai: giữ `error`.

---
title: Join nhân bản doanh thu, NULL làm rơi dòng và truy vấn reconcile (dunnhumby)
level: intermediate
services: []
files:
  - path: starter/fanout_audit.sql
    note: 1 TODO - đo mức nhân bản
  - path: starter/campaign_type_revenue.sql
    note: Câu SQL sai cho sẵn - sửa
  - path: starter/revenue_by_income.sql
    note: Câu SQL sai cho sẵn - sửa
  - path: starter/reconcile.sql
    note: 1 TODO - 4 phép kiểm đối chiếu
  - path: starter/run_query.py
    note: Chạy thử SQL trên dữ liệu thật, không cần sửa
  - path: tests/test_fanout.py
    note: Không sửa
run:
  - uv run python data/download_dataset.py dunnhumby-complete-journey
  - uv run python tracks/data-analyst/modules/03-sql-for-analysts/exercises/intermediate/02-join-fanout-reconcile/starter/run_query.py campaign_type_revenue.sql
  - uv run pytest tracks/data-analyst/modules/03-sql-for-analysts/exercises/intermediate/02-join-fanout-reconcile -q
---

## Mục tiêu

Trưởng nhóm marketing gửi hai báo cáo do một bạn mới viết: "doanh thu theo loại campaign" và "doanh thu theo
mức thu nhập". Cả hai chạy không lỗi, và cả hai sai. Bài này luyện ba thói quen của DA senior trước khi gửi số:
**biết grain của mỗi bảng trước khi join**, **không để NULL/join làm rơi dòng âm thầm**, và **viết truy vấn
reconcile** để chứng minh con số khớp với nguồn.

## Đề bài

Bộ `dunnhumby-complete-journey` (2 500 hộ có thẻ thành viên của một chuỗi siêu thị Mỹ, khoảng 2 năm). Test nạp
bốn bảng, giữ nguyên tên bảng và tên cột như tệp CSV:

| Bảng | Grain (một dòng là) | Cột dùng |
| --- | --- | --- |
| `transaction_data` | một mặt hàng trong một giỏ (2 595 732 dòng) | `household_key`, `QUANTITY`, `SALES_VALUE` |
| `hh_demographic` | một hộ **có** thông tin nhân khẩu (801 hộ) | `household_key`, `INCOME_DESC` |
| `campaign_table` | một hộ được gửi **một** campaign (7 208 dòng, 1 584 hộ) | `household_key`, `CAMPAIGN`, `DESCRIPTION` (TypeA/B/C) |
| `campaign_desc` | một campaign (30) | `CAMPAIGN`, `DESCRIPTION`, `START_DAY`, `END_DAY` |

Định nghĩa theo capstone của track: **dòng hợp lệ** là `SALES_VALUE > 0 AND QUANTITY > 0`; doanh thu =
`sum(SALES_VALUE)`; hộ = `household_key`. Mỗi tệp là **một** câu `SELECT`.

1. **`fanout_audit.sql`**: đúng một dòng đo cái giá của việc join thẳng dòng giao dịch hợp lệ với
   `campaign_table` theo `household_key`. Cột: `valid_rows` (số dòng hợp lệ), `joined_rows` (số dòng sau join),
   `fanout_factor` = `joined_rows / valid_rows`, `revenue_true` (doanh thu hợp lệ), `revenue_naive` (tổng
   `SALES_VALUE` sau join), `inflation_factor` = `revenue_naive / revenue_true`. Số thập phân làm tròn 2.
2. **`campaign_type_revenue.sql`** (starter là câu sai, hãy sửa): mỗi loại campaign một dòng, cộng dòng `None` cho
   các hộ có doanh thu nhưng không có trong `campaign_table`. Cột: `campaign_type`, `households` (số hộ đã nhận ít
   nhất một campaign loại đó; hộ nhận mà không có giao dịch hợp lệ vẫn tính, doanh thu 0), `revenue` (tổng doanh
   thu hợp lệ **cả kỳ** của các hộ đó, mỗi hộ tính một lần), `revenue_per_household`. Sắp theo `campaign_type`.
3. **`revenue_by_income.sql`** (starter là câu sai, hãy sửa): doanh thu theo `INCOME_DESC` của mọi hộ có doanh
   thu; hộ không có trong `hh_demographic` gộp vào `'Unknown'`. Cột: `income_desc`, `households`, `revenue`,
   `share` (trên tổng doanh thu hợp lệ, làm tròn 4). Sắp theo `revenue` giảm dần.
4. **`reconcile.sql`**: bốn dòng, cột `check_name, expected, actual, passed` (`passed` là `|expected - actual| <
   0.01`), làm tròn 2:

   | `check_name` | `expected` | `actual` |
   | --- | --- | --- |
   | `income_revenue_total` | tổng doanh thu hợp lệ | tổng `revenue` qua các nhóm thu nhập (cách tính của câu 3) |
   | `income_households_total` | số hộ có doanh thu | tổng `households` qua các nhóm thu nhập |
   | `campaign_households_total` | số hộ có doanh thu | số hộ `None` + số hộ khác nhau trong `campaign_table` có doanh thu |
   | `naive_join_revenue_total` | tổng doanh thu hợp lệ | tổng `SALES_VALUE` sau join thẳng với `campaign_table` |

   Ba dòng đầu phải `passed = TRUE`; dòng cuối `FALSE`, ghi lại bằng chứng vì sao không được join thẳng.

Sau khi test pass, làm phần trắc nghiệm trong app.

## Tiêu chí đạt

- Test trên dữ liệu nhỏ pass: hộ nhận nhiều campaign cùng loại chỉ tính một lần, hộ nhận campaign mà không mua
  vẫn có mặt, hộ không có nhân khẩu học vào `Unknown`, dòng `SALES_VALUE = 0` hoặc `QUANTITY = 0` bị loại.
- Trên bộ thật: join thẳng nhân 2 576 815 dòng thành 13 919 433 (5.40 lần), doanh thu 8.06 triệu thành 43.8
  triệu (5.44 lần); `Unknown` có 1 699 hộ và 44.2% doanh thu; bốn phép kiểm cho `TRUE, TRUE, TRUE, FALSE`.
- Trắc nghiệm: đúng ít nhất 6/8 câu.

## Gợi ý

### Gợi ý 1

Trước mỗi join, hỏi "khoá join có duy nhất ở bảng bên kia không?": `SELECT count(*), count(DISTINCT
household_key) FROM campaign_table`. Không duy nhất thì gom bảng nhiều dòng về đúng grain (hộ, hoặc hộ × loại
campaign bằng `SELECT DISTINCT`) **trước** khi join; hoặc dùng `EXISTS` khi chỉ cần biết "có hay không".

### Gợi ý 2

Gom doanh thu về grain hộ trước (`GROUP BY household_key`), rồi `LEFT JOIN` bảng thuộc tính và `coalesce(...,
'Unknown')`. Tỉ trọng: `sum(revenue) / sum(sum(revenue)) OVER ()`. Hộ `None`: `WHERE NOT EXISTS (SELECT 1 FROM
campaign_table c WHERE c.household_key = r.household_key)`; tránh `NOT IN` với cột có thể NULL.

---
title: Tối ưu một job Spark chậm - báo cáo seller Olist
level: advanced
services: []
files:
  - path: starter/job.py
    note: Viết lại, giữ nguyên chữ ký hàm
  - path: tests/test_job.py
    note: Không sửa
run:
  - uv run pytest tracks/data-engineer/modules/06-spark-big-data/exercises/advanced/01-optimize-slow-job -q
---

## Mục tiêu

Nhận ra các anti-pattern phổ biến trong code PySpark do người quen pandas viết (vòng lặp Python gọi
action, `collect()` về driver, Python UDF, tính lại không cache) và viết lại thành một plan thuần
DataFrame mà Catalyst tối ưu được.

## Đề bài

`starter/job.py` cho kết quả **đúng** nhưng chậm khủng khiếp khi số seller lên hàng nghìn. Hãy viết lại
hai hàm, giữ nguyên chữ ký và kết quả:

1. `seller_report(spark, orders, items, sellers)`: với đơn `delivered`, mỗi seller có ít nhất một item
   trong đơn delivered cho một dòng:
   - `seller_id`, `seller_state`
   - `n_orders`: số đơn khác nhau
   - `gmv`: tổng `price`, làm tròn 2
   - `avg_ticket`: `gmv / n_orders`, làm tròn 2
   - `tier`: `"gold"` nếu `gmv >= 1000`, `"silver"` nếu `gmv >= 200`, còn lại `"bronze"`
   - Sắp xếp `gmv` giảm dần, rồi `seller_id` tăng dần.
2. `tier_counts(report)`: trả về `dict` `{tier: số seller}` từ kết quả trên.

Ràng buộc hiệu năng (test kiểm):

- `seller_report` **không được kích hoạt Spark job nào** (chỉ dựng plan, không `collect`/`count`/`first`).
- Physical plan của report không có Python UDF (`BatchEvalPython`, `ArrowEvalPython`).
- `tier_counts` chỉ gọi **một** action: số Spark job không vượt quá số job của một lần
  `report.groupBy("tier").count().collect()` (với AQE và broadcast, một action có thể sinh vài job).

Ngoài test, viết ngắn trong docstring đầu tệp: các anti-pattern bạn đã sửa và vì sao mỗi cái chậm.

## Tiêu chí đạt

- Test correctness, laziness, no-UDF và số job đều pass.
- Code không còn vòng lặp Python trên dữ liệu.
- Giải thích được plan mới (`report.explain()`): có bao nhiêu `Exchange`, join nào là broadcast.

## Gợi ý

### Gợi ý 1

Mọi thứ trong vòng `for sid in seller_ids` đều là một `groupBy("seller_id")` sau khi join `items` với
đơn delivered. `F.when(...).when(...).otherwise(...)` thay cho UDF.

### Gợi ý 2

`sellers` là dimension nhỏ: `broadcast(sellers)`. `tier_counts`: một `groupBy("tier").count().collect()`
rồi dựng dict trên driver (kết quả chỉ vài dòng).

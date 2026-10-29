---
title: Funnel vòng đời đơn hàng bằng SQL
level: basic
services: []
files:
  - path: starter/funnel.sql
    note: Funnel tuần tự
  - path: starter/funnel_strict.sql
    note: Funnel có điều kiện thời gian
  - path: tests/test_funnel.py
    note: Không sửa
run:
  - uv run python data/download_olist.py
  - uv run pytest tracks/data-science/modules/08-coding-for-ds/exercises/basic/03-funnel-sql -q
---

## Mục tiêu

Viết funnel bằng một câu SQL trên DuckDB, và thấy một quyết định định nghĩa (có bắt buộc thứ tự thời
gian hay không) đổi con số trên dữ liệu thật thế nào.

## Đề bài

Bảng có sẵn: `orders`, `order_reviews` (cột như Olist). Hai query trả **6 dòng**, cột
`step` (1–6), `step_name`, `orders`, `pct_of_prev`, `pct_of_first`, sắp theo `step`:

| step | step_name | Đơn đạt bước khi |
| --- | --- | --- |
| 1 | purchased | mọi đơn |
| 2 | approved | `order_approved_at` có giá trị |
| 3 | shipped | `order_delivered_carrier_date` có giá trị |
| 4 | delivered | `order_status = 'delivered'` và có `order_delivered_customer_date` |
| 5 | reviewed | có review |
| 6 | good_review | review **mới nhất** (theo `review_answer_timestamp`) có `review_score >= 4` |

- `funnel.sql` (tuần tự): đơn chỉ được tính ở bước k nếu đạt **mọi** bước từ 2 tới k.
- `funnel_strict.sql`: như trên, thêm điều kiện thời gian cho bước 2–4: duyệt không sớm hơn lúc mua,
  giao cho hãng không sớm hơn lúc duyệt, khách nhận không sớm hơn lúc giao cho hãng.
- `pct_of_prev` = số đơn bước này / bước trước (bước 1 là 1.0); `pct_of_first` = / bước 1.

Chạy trên Olist thật rồi trả lời: chỗ rơi lớn nhất ở đâu? Bao nhiêu đơn bị loại vì sai thứ tự thời
gian, và bạn sẽ hỏi đội vận hành điều gì?

## Tiêu chí đạt

- Đúng cột, đúng 6 bước, đúng thứ tự.
- Trên dữ liệu test: review của đơn chưa duyệt không được tính, đơn có nhiều review dùng review mới
  nhất, đơn giao cho hãng trước khi duyệt bị loại ở funnel chặt.
- Trên Olist thật: funnel tuần tự `[99441, 99281, 97644, 96455, 95809, 75623]`, funnel chặt
  `[99441, 99281, 96285, 95082, 94443, 74480]`.

## Gợi ý

### Gợi ý 1

CTE `latest_review` bằng `QUALIFY ROW_NUMBER() OVER (PARTITION BY order_id ORDER BY
review_answer_timestamp DESC) = 1`, rồi `LEFT JOIN` vào `orders` và tạo một cột boolean cho mỗi bước.
Sau đó mỗi bước là `COUNT(*) FILTER (WHERE b2 AND b3 AND ...)`, ghép 6 dòng bằng `UNION ALL`.

### Gợi ý 2

So sánh với NULL cho NULL, và `FILTER (WHERE NULL)` không đếm dòng đó; vẫn nên `COALESCE(..., FALSE)`
để ý đồ rõ ràng. Tỉ lệ: `orders / LAG(orders) OVER (ORDER BY step)` (bước 1 không có dòng trước:
`COALESCE`), `orders / FIRST_VALUE(orders) OVER (ORDER BY step)`; ép `::DOUBLE` để tránh chia nguyên.

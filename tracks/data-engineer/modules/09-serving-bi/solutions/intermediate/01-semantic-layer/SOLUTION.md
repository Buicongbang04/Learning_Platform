# Lời giải: Tự viết semantic layer sinh SQL cho DuckDB

Xem `semantic.py` cùng thư mục.

## Cách biên dịch

1. **Validate trước.** Mọi tên metric, dimension, op phải có trong registry. Đây là whitelist: chuỗi do người
   dùng gửi lên không bao giờ được ghép vào SQL như tên cột. Giá trị filter đi qua `params`.
2. **Tìm measure cần thiết.** Metric `simple` cần một measure; `ratio` cần numerator và denominator. Gom lại, giữ thứ
   tự, bỏ trùng.
3. **Nhóm theo model, mỗi model một CTE.** `revenue` và `items` aggregate trên model `items` (grain item);
   `orders`, `late_orders`, `delivered_orders` trên model `orders` (grain đơn). Mỗi CTE aggregate về grain của các
   dimension được hỏi. Nhờ vậy không bao giờ có join 1-n trước khi aggregate, nên không fan-out.
4. **Nối các CTE theo dimension.** `FULL OUTER JOIN … USING (dims)` giữ cả tổ hợp dimension chỉ có ở một model
   (ví dụ ngày có đơn nhưng chưa có item). Không có dimension thì mỗi CTE trả đúng một dòng, nên `CROSS JOIN`.
5. **Tính ratio ở cuối.** `revenue / NULLIF(orders, 0)` sau khi aggregate, nên AOV toàn bộ là 730 / 5 = 146, không
   phải trung bình AOV các state ((93.33 + 225) / 2 = 159.17).

SQL sinh ra cho `run_query(con, ["aov"], ["customer_state"])` có dạng:

```sql
WITH m_items  AS (SELECT customer_state AS customer_state, SUM(price) AS revenue
                  FROM (...) AS base GROUP BY 1),
     m_orders AS (SELECT customer_state AS customer_state, COUNT(DISTINCT order_id) AS orders
                  FROM (...) AS base GROUP BY 1)
SELECT customer_state, revenue / NULLIF(orders, 0) AS aov
FROM m_items FULL OUTER JOIN m_orders USING (customer_state)
ORDER BY customer_state
```

## Hạn chế so với công cụ thật

- Chưa có join graph giữa entity (MetricFlow tự tìm đường join qua entity key). Ở đây mọi model đã join sẵn
  `customers`.
- Chưa có time spine cho cumulative metric, chưa có `limit`/`order by` metric, chưa có cache.
- Filter áp cho mọi model; công cụ thật cho phép filter riêng trên metric (ví dụ `revenue` chỉ tính đơn delivered).
- Chưa có phân quyền: bản thật cần row-level filter theo người dùng (xem module 10).

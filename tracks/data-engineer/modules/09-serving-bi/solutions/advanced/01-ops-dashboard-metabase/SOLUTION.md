# Hướng dẫn chấm: Dashboard vận hành giao hàng trên Metabase

Bài này không có một đáp án duy nhất. Dưới đây là hướng làm tham khảo, các quyết định cần cân nhắc và rubric.

## Hướng làm

### Marts

```sql
CREATE OR REPLACE TABLE mart_ops_daily AS
WITH o AS (
    SELECT order_id, CAST(order_purchase_timestamp AS DATE) AS order_date, order_status,
           order_delivered_customer_date > order_estimated_delivery_date AS is_late
    FROM orders WHERE order_status NOT IN ('canceled', 'unavailable')
), rev AS (SELECT order_id, SUM(price) AS value FROM order_items GROUP BY 1)
SELECT o.order_date,
       COUNT(*)                                                       AS orders,
       COUNT(*) FILTER (WHERE order_status = 'delivered')             AS delivered_orders,
       COUNT(*) FILTER (WHERE order_status = 'delivered' AND is_late) AS late_orders,
       COUNT(*) FILTER (WHERE order_status = 'delivered' AND is_late)
         / NULLIF(COUNT(*) FILTER (WHERE order_status = 'delivered'), 0) AS late_rate,
       COALESCE(SUM(rev.value), 0)                                    AS revenue,
       CURRENT_TIMESTAMP::TIMESTAMP                                   AS updated_at
FROM o LEFT JOIN rev USING (order_id)
GROUP BY 1;
```

- `mart_overdue_orders`: lọc `order_delivered_customer_date IS NULL`, không huỷ, ngày dự kiến `< as_of`;
  `days_overdue = date_diff('day', estimated, as_of)`; `seller_ids` bằng subquery `string_agg` để không nhân dòng.
- `mart_seller_late_rate`: `SELECT DISTINCT seller_id, order_id, is_late` từ đơn delivered join items, rồi group theo
  seller. Không có `DISTINCT` thì seller có 2 item trong một đơn bị đếm 2 đơn.
- `run_context.as_of` thay cho `CURRENT_DATE` giúp build tái lập được (backfill một ngày trong quá khứ ra đúng kết
  quả của ngày đó). Airflow truyền `{{ ds }}` vào đây.

### Dashboard spec

| Hàng | Card | Display | Nguồn |
| --- | --- | --- | --- |
| 0 | Đơn 7 ngày, Late rate 7 ngày (target 5%), Số đơn quá hạn, Doanh thu 7 ngày | scalar / smartscalar | `mart_ops_daily`, `mart_overdue_orders` |
| 1 | Đơn và late rate theo ngày; Late rate theo seller (top 10) | line; row | `mart_ops_daily`; `mart_seller_late_rate` |
| 2 | Đơn quá hạn: order, state, seller, số ngày trễ, sắp giảm dần | table | `mart_overdue_orders` |

### Publish

1. `POST /api/session` → token. Đọc user/mật khẩu từ biến môi trường.
2. Với mỗi card: tìm card cùng tên trong collection của dashboard (`GET /api/card`), có thì `PUT`, chưa có thì `POST`.
3. Tìm dashboard theo tên (`GET /api/dashboard`), chưa có thì `POST /api/dashboard`.
4. `PUT /api/dashboard/:id` với toàn bộ `dashcards` (thay thế danh sách cũ), mỗi phần tử có `card_id`, `row`, `col`,
   `size_x`, `size_y`.
5. Trả id dashboard. Chạy lại ra cùng id, số card không tăng.

## Quyết định cần cân nhắc

- **Bảng hay view?** Mart là bảng refresh 15 phút nếu dữ liệu lớn; view nếu nhỏ. Ghi rõ SLA freshness và hiện
  `MAX(updated_at)` trên dashboard.
- **Late rate theo ngày đặt hay ngày giao?** Theo ngày đặt thì số của các ngày gần đây còn thay đổi (đơn chưa giao);
  theo ngày giao thì ổn định hơn cho vận hành. Cần thống nhất với stakeholder và ghi trong metric spec.
- **Cửa sổ thời gian của KPI** (hôm nay, 7 ngày, 30 ngày) và so sánh với kỳ trước.
- **Quyền**: Metabase kết nối bằng user read-only chỉ thấy schema `mart`; `mart_overdue_orders` không chứa PII
  (không tên, không địa chỉ khách).
- **Dashboard as code**: Metabase bản open source không có serialization; script publish là cách giữ dashboard trong
  Git. Bản Pro/Enterprise có `serialization export/import`.

## Rubric (10 điểm)

| Tiêu chí | Điểm |
| --- | --- |
| Ba mart đúng số liệu, grain rõ, không fan-out, xử lý NULL đúng (test pass) | 3 |
| Bố cục dashboard: KPI có ngữ cảnh, xu hướng, bảng hành động; chọn đúng loại biểu đồ | 2 |
| `publish` hoạt động với Metabase thật và idempotent | 2 |
| Build tái lập được (`as_of`), có freshness và SLA được ghi rõ | 1 |
| Bảo mật: không hard-code mật khẩu, user read-only, không đưa PII lên dashboard | 1 |
| Ghi chú thiết kế: metric spec (định nghĩa late rate, cửa sổ thời gian), alert | 1 |

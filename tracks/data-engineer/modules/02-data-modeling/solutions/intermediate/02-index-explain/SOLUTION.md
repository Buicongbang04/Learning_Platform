# Lời giải: composite và covering index

```sql
CREATE INDEX idx_items_seller_date ON order_items (seller_id, shipping_limit_date, price);
CREATE INDEX idx_orders_status_ts  ON orders (order_status, order_purchase_timestamp);
CREATE INDEX idx_orders_customer   ON orders (customer_id);
CREATE INDEX idx_items_order       ON order_items (order_id, price);
```

## Q1

Trước: `SCAN order_items` + `USE TEMP B-TREE FOR ORDER BY`. Sau:
`SEARCH order_items USING COVERING INDEX idx_items_seller_date (seller_id=? AND shipping_limit_date>?)`.

- `seller_id` đứng đầu vì là điều kiện `=`; trong cùng một seller, các dòng trong index đã sắp
  theo `shipping_limit_date`, nên điều kiện `>=` thành một đoạn liên tiếp và `ORDER BY` không cần sort.
- Nếu đảo thứ tự `(shipping_limit_date, seller_id)`, index phải quét mọi ngày ≥ mốc của **mọi**
  seller rồi lọc, kém hơn nhiều.
- Thêm `price` vào cuối giúp index chứa đủ mọi cột truy vấn cần → covering, không phải nhảy về
  bảng cho từng dòng. Trên PostgreSQL viết `INCLUDE (price)`.

## Q2

`(order_status, order_purchase_timestamp)`: cột `=` trước, cột khoảng sau, nên plan dùng cả hai:
`(order_status=? AND order_purchase_timestamp>? AND order_purchase_timestamp<?)`. `order_status`
có độ chọn lọc thấp (90% là `delivered`) nên index chỉ trên nó gần như vô dụng cho `delivered`,
nhưng rất tốt cho `processing`; ghép với timestamp thì tốt cho cả hai. Trên PostgreSQL có thể cân
nhắc **partial index** `... (order_purchase_timestamp) WHERE order_status = 'processing'` nếu chỉ
hàng đợi đơn chưa xử lý là nóng.

## Q3

Trước: `SCAN i` (quét cả `order_items`). Sau: `SEARCH o USING INDEX idx_orders_customer` rồi với
mỗi đơn `SEARCH i USING COVERING INDEX idx_items_order (order_id=?)`. Đây là index cho **foreign
key** `order_items.order_id` — PostgreSQL và SQLite đều không tự tạo, và thiếu nó là nguyên nhân số
một khiến join và `DELETE` trên bảng cha chậm.

`USE TEMP B-TREE FOR GROUP BY` vẫn còn nhưng chỉ sort vài dòng của một khách, không đáng kể.

## Vì sao giới hạn 4 index

Mỗi index làm chậm INSERT/UPDATE và tốn dung lượng. Index tốt là index phục vụ được nhiều truy vấn:
`idx_items_seller_date` cũng phục vụ `WHERE seller_id = ?`; `idx_items_order` thay được khoá chính
`(order_id, order_item_id)` cho truy vấn theo đơn. Luôn đo bằng `EXPLAIN` trên dữ liệu đủ lớn và đã
`ANALYZE`, vì planner quyết định dựa trên thống kê.

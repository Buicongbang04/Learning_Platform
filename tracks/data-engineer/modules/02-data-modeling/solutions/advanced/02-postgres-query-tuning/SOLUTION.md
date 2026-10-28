# Lời giải: tối ưu workload PostgreSQL

Bài mở: nhiều cách đạt test. Dưới đây là hướng làm tham khảo, các quyết định cần cân nhắc và rubric.

## tune.sql tham khảo

```sql
-- Q1: '=' trước, khoảng/sort sau; INCLUDE để index-only scan mà không làm to phần khoá.
CREATE INDEX idx_items_seller_date ON order_items (seller_id, shipping_limit_date) INCLUDE (price);

-- Q3: partial index chỉ chứa ~1% dòng, thứ tự khớp ORDER BY ... DESC → không cần Sort, dừng sau 50 dòng.
CREATE INDEX idx_orders_processing_ts ON orders (order_purchase_timestamp DESC)
    WHERE order_status = 'processing';

-- Q2: chuyển sang declarative partitioning theo tháng, trong một transaction.
BEGIN;
ALTER TABLE order_events RENAME TO order_events_old;
CREATE TABLE order_events (
    order_id   TEXT NOT NULL,
    event_type TEXT NOT NULL,
    event_ts   TIMESTAMPTZ NOT NULL
) PARTITION BY RANGE (event_ts);

DO $$
DECLARE m date := DATE '2018-01-01';
BEGIN
    WHILE m < DATE '2019-01-01' LOOP
        EXECUTE format(
            'CREATE TABLE order_events_%s PARTITION OF order_events FOR VALUES FROM (%L) TO (%L)',
            to_char(m, 'YYYY_MM'), m::timestamptz, (m + INTERVAL '1 month')::timestamptz);
        m := m + INTERVAL '1 month';
    END LOOP;
END $$;
CREATE TABLE order_events_default PARTITION OF order_events DEFAULT;

INSERT INTO order_events SELECT * FROM order_events_old;
DROP TABLE order_events_old;
COMMIT;
```

Lưu ý: `m::timestamptz` dùng time zone của phiên. Nếu phiên không phải UTC, biên partition lệch
vài giờ so với ngày UTC; truy vấn một ngày UTC khi đó có thể chạm hai partition. Ghi rõ time zone
(`SET TIME ZONE 'UTC'` ở đầu script, hoặc biên dạng `'2018-03-01 00:00:00+00'`) là một điểm cộng.

Nếu Q2 còn nóng và mỗi partition vẫn lớn, thêm `CREATE INDEX ON order_events USING brin (event_ts)`
(tự áp lên mọi partition): rất nhỏ, hiệu quả vì dữ liệu append theo thời gian.

## Các quyết định cần cân nhắc

- **Thứ tự cột và INCLUDE** (Q1): `INCLUDE (price)` thay vì đưa `price` vào khoá, vì không ai lọc
  hay sắp xếp theo price; khoá nhỏ hơn, nút trong cây nhỏ hơn.
- **Partial index** (Q3): index toàn bộ `(order_status, order_purchase_timestamp)` cũng đạt, nhưng
  to gấp ~100 lần và mọi INSERT/UPDATE đơn `delivered` đều phải cập nhật nó. Đánh đổi: partial
  index chỉ được dùng khi truy vấn có đúng điều kiện `order_status = 'processing'`.
- **Partitioning** (Q2): lợi ích chính không phải tốc độ một truy vấn mà là **vận hành**: xoá dữ liệu
  cũ bằng `DETACH PARTITION ... CONCURRENTLY` + `DROP TABLE` (tức thì, không tạo dead tuple, không
  cần VACUUM lớn) thay vì `DELETE` hàng triệu dòng. Cần job tạo trước partition tháng tới (pg_partman
  hoặc cron) và partition `DEFAULT` để không mất dữ liệu đến sớm/muộn. Đánh đổi: khoá chính/unique
  phải chứa `event_ts`; quá nhiều partition làm planning chậm.
- **Migration an toàn**: làm trong transaction; với bảng thật đang nhận ghi thì cần chiến lược
  khác (tạo bảng mới, ghi kép hoặc trigger, backfill theo lô, đổi tên trong cửa sổ ngắn).
- **Cái giá phía ghi**: đo trước/sau, ví dụ `INSERT` 10k dòng vào `order_items` có/không có index;
  báo cáo `pg_indexes_size`.
- **Index-only scan** phụ thuộc visibility map; bảng ghi nhiều cần autovacuum đủ nhanh, xem
  `Heap Fetches` trong `EXPLAIN ANALYZE`.

## Rubric (100 điểm)

| Hạng mục | Điểm | Đạt tốt khi |
| --- | --- | --- |
| Test pass trên PostgreSQL | 30 | 4/4 test pass, dữ liệu nguyên vẹn |
| Q1 | 10 | Đúng thứ tự cột, dùng `INCLUDE`, giải thích leftmost prefix và index-only scan |
| Q2 | 15 | Partition theo tháng + DEFAULT, migration trong transaction, nêu rõ time zone, chứng minh pruning bằng plan |
| Q3 | 10 | Partial index, so sánh kích thước với index đầy đủ |
| Báo cáo đo đạc | 15 | Có `EXPLAIN (ANALYZE, BUFFERS)` trước/sau, thời gian, buffers, dung lượng index |
| Cái giá phía ghi | 10 | Đo hoặc lập luận định lượng về INSERT chậm đi, WAL, dung lượng |
| Vận hành | 10 | Retention bằng DETACH/DROP, tạo partition trước, giám sát index không dùng (`pg_stat_user_indexes`) |

Mức đạt: ≥ 70 điểm và toàn bộ test pass.

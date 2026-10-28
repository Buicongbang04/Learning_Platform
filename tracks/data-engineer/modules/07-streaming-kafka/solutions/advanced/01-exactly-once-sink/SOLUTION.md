# Lời giải: Sink exactly-once từ Kafka vào SQL

Bài advanced không có đáp án duy nhất. Dưới đây là hướng làm, các quyết định thiết kế và rubric.

## Hướng làm

1. **Ba bảng**: `orders` (trạng thái hiện tại theo `order_id`), `processed_events` (khoá chính
   `event_id`, dùng để dedup), `consumer_offsets` (`topic, partition → next_offset`).
2. **Một transaction cho mỗi batch**: lọc theo offset, dedup theo `event_id`, upsert có điều kiện,
   cập nhật offset, tất cả trong `with conn:`. Exception ở bất kỳ đâu thì rollback toàn bộ.
3. **Khi khởi động**: consumer đọc `committed_offsets()` và `seek(TopicPartition, next_offset)` cho
   từng partition được gán (trong `on_partitions_assigned` của `ConsumerRebalanceListener`). Offset
   trong Kafka chỉ còn để theo dõi lag, không phải nguồn sự thật.

## Các quyết định cần cân nhắc

- **Lọc theo offset vs dedup theo event_id**: offset chống xử lý lại do restart/rebalance (cùng record);
  event_id chống trùng do producer retry hoặc nguồn gửi lại (record khác, cùng nội dung). Cần cả hai.
- **Bảng `processed_events` phình mãi**: thêm cột thời gian và xoá theo TTL (vd. 7 ngày, bằng retention
  của topic), hoặc dựa hẳn vào upsert idempotent nếu phép biến đổi cho phép.
- **Upsert có điều kiện theo `event_time`**: chống event cũ làm lùi trạng thái. Hoà (`event_time` bằng
  nhau) cần quy tắc phụ: thứ tự trạng thái (`created < approved < shipped < delivered`) hoặc offset.
- **Phép tính không idempotent** (cộng dồn GMV trực tiếp vào bảng tổng) nguy hiểm khi replay. Ở đây GMV
  tính từ trạng thái hiện tại nên luôn đúng. Nếu buộc phải cộng dồn thì bắt buộc dedup + offset nguyên tử.
- **Nhiều consumer song song**: mỗi partition chỉ thuộc một consumer, và offset lưu theo partition,
  nên vẫn đúng, miễn là một consumer "zombie" (đã mất partition nhưng chưa biết) không ghi đè. Có thể
  thêm cột `generation`/epoch của group hoặc kiểm tra `next_offset` mong đợi trong câu UPDATE
  (optimistic concurrency).
- **Chuyển sang PostgreSQL**: `INSERT ... ON CONFLICT ... DO UPDATE ... WHERE` giữ nguyên; dùng
  `executemany`/`COPY` vào bảng tạm rồi `MERGE` cho batch lớn; mức cô lập `READ COMMITTED` đủ vì mỗi
  partition chỉ một writer.
- **So với Kafka transactions**: nếu đích là một topic Kafka khác, dùng `transactional.id` +
  `send_offsets_to_transaction` thay vì tự lưu offset.

## Lời giải tham khảo

```python
from __future__ import annotations

import sqlite3


class OrderSink:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def init_schema(self) -> None:
        with self.conn:
            self.conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS orders (
                    order_id TEXT PRIMARY KEY, status TEXT NOT NULL, amount REAL NOT NULL,
                    customer_state TEXT, event_time TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS processed_events (event_id TEXT PRIMARY KEY);
                CREATE TABLE IF NOT EXISTS consumer_offsets (
                    topic TEXT NOT NULL, partition INTEGER NOT NULL, next_offset INTEGER NOT NULL,
                    PRIMARY KEY (topic, partition));
                """
            )

    def process_batch(self, records, fail_after=None) -> int:
        applied = 0
        with self.conn:  # một transaction: commit khi thành công, rollback khi có exception
            cur = self.conn.cursor()
            stored = dict(((t, p), o) for t, p, o in
                          cur.execute("SELECT topic, partition, next_offset FROM consumer_offsets"))
            new_offsets: dict = {}
            for i, record in enumerate(records):
                if fail_after is not None and i >= fail_after:
                    raise RuntimeError("Giả lập crash giữa batch")
                tp = (record["topic"], record["partition"])
                if record["offset"] < stored.get(tp, 0):
                    continue
                new_offsets[tp] = max(new_offsets.get(tp, 0), record["offset"] + 1)
                e = record["value"]
                inserted = cur.execute(
                    "INSERT OR IGNORE INTO processed_events(event_id) VALUES (?)", (e["event_id"],)
                ).rowcount
                if not inserted:
                    continue
                applied += 1
                cur.execute(
                    """
                    INSERT INTO orders(order_id, status, amount, customer_state, event_time)
                    VALUES (:order_id, :status, :amount, :customer_state, :event_time)
                    ON CONFLICT(order_id) DO UPDATE SET
                        status = excluded.status, amount = excluded.amount,
                        customer_state = excluded.customer_state, event_time = excluded.event_time
                    WHERE excluded.event_time > orders.event_time
                    """,
                    e,
                )
            if fail_after is not None and fail_after >= len(records):
                raise RuntimeError("Giả lập crash trước khi commit")
            for (topic, partition), nxt in new_offsets.items():
                cur.execute(
                    """
                    INSERT INTO consumer_offsets(topic, partition, next_offset) VALUES (?, ?, ?)
                    ON CONFLICT(topic, partition) DO UPDATE SET
                        next_offset = MAX(next_offset, excluded.next_offset)
                    """,
                    (topic, partition, nxt),
                )
        return applied

    def committed_offsets(self):
        rows = self.conn.execute("SELECT topic, partition, next_offset FROM consumer_offsets")
        return {(t, p): o for t, p, o in rows}

    def order_status(self, order_id):
        row = self.conn.execute(
            "SELECT status, amount, customer_state, event_time FROM orders WHERE order_id = ?",
            (order_id,),
        ).fetchone()
        if row is None:
            return None
        return dict(zip(["status", "amount", "customer_state", "event_time"], row))

    def gmv_by_state(self):
        rows = self.conn.execute(
            "SELECT customer_state, ROUND(SUM(amount), 2) FROM orders "
            "WHERE status <> 'canceled' GROUP BY customer_state"
        )
        return {s: v for s, v in rows}
```

## Rubric (100 điểm)

| Tiêu chí | Điểm |
| --- | --- |
| Mọi test pass | 40 |
| Dữ liệu và offset trong cùng một transaction, crash giữa batch không để lại thay đổi | 15 |
| Dedup theo event_id và lọc theo offset, giải thích được vì sao cần cả hai | 10 |
| Upsert có điều kiện chống lùi trạng thái, có xử lý trường hợp hoà | 10 |
| Offset không bao giờ lùi (MAX hoặc kiểm tra) | 5 |
| Giải thích giới hạn: nhiều consumer, zombie, bảng dedup phình, chuyển PostgreSQL | 15 |
| Code rõ ràng, SQL có tham số (không nối chuỗi), schema có khoá chính phù hợp | 5 |

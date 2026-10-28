# Lời giải: Stream processor GMV theo phút theo bang

Bài advanced không có đáp án duy nhất. Dưới đây là hướng làm, các quyết định thiết kế và rubric.

## Hướng làm

1. Hàm `parse(raw)` thuần: decode, `json.loads`, kiểm tra kiểu và giá trị, ném `ValueError(reason)`.
   `process` bắt lỗi và đẩy vào DLQ, nên một message hỏng không làm dừng cả partition.
2. Dedup bằng dict `event_id → event_time`, dọn các id quá `dedup_ttl` mỗi khi `max_event_time` tăng.
3. Kiểm tra late bằng watermark **trước** khi cập nhật `max_event_time`.
4. State window là dict `(window_start, customer_state) → {orders, gmv, canceled}`; `_emit(ready)`
   pop các window đủ điều kiện, sắp theo khoá, đếm số window đã phát.
5. `flush()` cho kết thúc stream (test, shutdown có kiểm soát).

## Các quyết định cần cân nhắc

- **Thứ tự dedup và late**: ở đây dedup trước. Nếu late trước thì một bản trùng đến muộn bị đếm là
  late thay vì duplicate; cả hai đều không làm sai GMV nhưng metric giám sát khác nhau.
- **`dedup_ttl` vs bộ nhớ**: TTL nhỏ tiết kiệm bộ nhớ nhưng bản trùng đến muộn hơn TTL bị đếm hai lần
  (test `test_dedup_memory_has_ttl` cố ý cho thấy điều này). Chọn TTL ≥ `allowed_lateness` và ≥ thời
  gian retry tối đa của producer.
- **State nằm trong RAM**: restart là mất window đang mở và bộ nhớ dedup. Production cần checkpoint
  (Flink state backend, Kafka Streams state store + changelog topic) hoặc chấp nhận tính lại bằng cách
  seek lùi một khoảng bằng `allowed_lateness` khi khởi động.
- **Nhiều partition**: mỗi instance xử lý một số partition và tự tính watermark; để gộp đúng cần key
  theo `customer_state` (repartition) hoặc gộp ở sink bằng upsert cộng dồn theo
  `(window_start, customer_state)`. Watermark toàn cục là min các watermark partition.
- **Late data**: side output được lưu (topic `olist.orders.late`) để batch job sửa số liệu sau; hoặc
  chuyển sang chế độ "update" phát lại window đã sửa và sink upsert.
- **Semantics khi nối Kafka**: at-least-once (gửi kết quả, `flush()`, rồi commit offset). Kết quả có key
  `"{window_start}:{customer_state}"` nên sink upsert theo key là idempotent. Muốn exactly-once
  Kafka → Kafka thì dùng producer transactional và `send_offsets_to_transaction`.

## Lời giải tham khảo (phần lõi)

```python
from __future__ import annotations

import json

VALID_STATUSES = {"created", "approved", "shipped", "delivered", "canceled"}
REQUIRED = ("event_id", "order_id", "status", "amount", "customer_state", "event_time")


def _is_number(x) -> bool:
    return isinstance(x, (int, float)) and not isinstance(x, bool)


def parse(raw: bytes) -> dict:
    """Trả về event hợp lệ hoặc ném ValueError với lý do."""
    try:
        event = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"invalid_json: {exc}") from exc
    if not isinstance(event, dict):
        raise ValueError("not_an_object")
    missing = [f for f in REQUIRED if f not in event]
    if missing:
        raise ValueError(f"missing_fields: {missing}")
    if event["status"] not in VALID_STATUSES:
        raise ValueError(f"invalid_status: {event['status']!r}")
    if not _is_number(event["amount"]) or event["amount"] < 0:
        raise ValueError("invalid_amount")
    if not isinstance(event["event_time"], int) or isinstance(event["event_time"], bool):
        raise ValueError("invalid_event_time")
    return event


class OrderMetricsProcessor:
    def __init__(self, window_size: int = 60, allowed_lateness: int = 120, dedup_ttl: int = 3600):
        self.window_size = window_size
        self.allowed_lateness = allowed_lateness
        self.dedup_ttl = dedup_ttl
        self.dlq: list[dict] = []
        self.late: list[dict] = []
        self.duplicates = 0
        self.max_event_time: int | None = None
        self.emitted_windows = 0
        self._windows: dict[tuple[int, str], dict] = {}
        self._seen: dict[str, int] = {}  # event_id -> event_time

    @property
    def watermark(self) -> int | None:
        if self.max_event_time is None:
            return None
        return self.max_event_time - self.allowed_lateness

    def process(self, raw: bytes) -> list[dict]:
        try:
            event = parse(raw)
        except ValueError as exc:
            self.dlq.append({"raw": raw, "reason": str(exc)})
            return []
        if event["event_id"] in self._seen:
            self.duplicates += 1
            return []
        ts = event["event_time"]
        start = ts - ts % self.window_size
        wm = self.watermark
        if wm is not None and start + self.window_size <= wm:
            self.late.append(event)
            return []
        self._seen[event["event_id"]] = ts
        if event["status"] in ("created", "canceled"):
            w = self._windows.setdefault(
                (start, event["customer_state"]), {"orders": 0, "gmv": 0.0, "canceled": 0}
            )
            if event["status"] == "created":
                w["orders"] += 1
                w["gmv"] += float(event["amount"])
            else:
                w["canceled"] += 1
        if self.max_event_time is None or ts > self.max_event_time:
            self.max_event_time = ts
            horizon = ts - self.dedup_ttl
            self._seen = {k: t for k, t in self._seen.items() if t >= horizon}
        return self._emit(lambda end: end <= self.watermark)

    def flush(self) -> list[dict]:
        return self._emit(lambda end: True)

    def _emit(self, ready) -> list[dict]:
        out = []
        for start, state in sorted(self._windows):
            end = start + self.window_size
            if ready(end):
                w = self._windows.pop((start, state))
                out.append({"window_start": start, "window_end": end, "customer_state": state,
                            "orders": w["orders"], "gmv": round(w["gmv"], 2), "canceled": w["canceled"]})
        self.emitted_windows += len(out)
        return out

    def stats(self) -> dict:
        return {"emitted_windows": self.emitted_windows, "duplicates": self.duplicates,
                "late": len(self.late), "dlq": len(self.dlq)}
```

Phần nối Kafka (mở rộng), phác thảo:

```python
from kafka import KafkaConsumer, KafkaProducer


def run(bootstrap: str, in_topic: str = "olist.orders", out_topic: str = "olist.gmv_per_minute"):
    consumer = KafkaConsumer(in_topic, bootstrap_servers=bootstrap, group_id="gmv-per-minute",
                             enable_auto_commit=False, auto_offset_reset="earliest")
    producer = KafkaProducer(bootstrap_servers=bootstrap, acks="all", retries=5,
                             key_serializer=str.encode,
                             value_serializer=lambda v: json.dumps(v).encode())
    processor = OrderMetricsProcessor()
    try:
        while True:
            batch = consumer.poll(timeout_ms=1000)
            dlq_before = len(processor.dlq)
            for records in batch.values():
                for record in records:
                    for row in processor.process(record.value):
                        producer.send(out_topic, key=f"{row['window_start']}:{row['customer_state']}", value=row)
            for bad in processor.dlq[dlq_before:]:
                producer.send(f"{in_topic}.dlq", key="dlq", value={"reason": bad["reason"],
                              "raw": bad["raw"].decode("utf-8", "replace")})
            if batch:
                producer.flush()      # kết quả đã nằm an toàn trên Kafka
                consumer.commit()     # rồi mới commit: at-least-once
    finally:
        consumer.close()
        producer.close()
```

## Rubric (100 điểm)

| Tiêu chí | Điểm |
| --- | --- |
| Mọi test pass | 40 |
| Validate chặt (bool không phải số, event_time nguyên), lý do DLQ rõ ràng | 10 |
| State có giới hạn: dọn dedup theo TTL, xoá window khi phát | 10 |
| Watermark đúng (không lùi, kiểm late trước khi cập nhật) | 10 |
| Phân tích đánh đổi lateness/TTL, mất state khi restart, nhiều partition | 15 |
| (Mở rộng) Nối Kafka: commit sau khi flush, DLQ topic, key đầu ra idempotent | 10 |
| Code rõ ràng, tách hàm thuần dễ test | 5 |

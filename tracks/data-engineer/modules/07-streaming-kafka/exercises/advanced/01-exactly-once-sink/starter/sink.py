"""Sink "effectively exactly-once" từ Kafka vào SQL: lưu dữ liệu và offset trong cùng một transaction.

Mỗi record đọc từ Kafka có dạng:
    {"topic": str, "partition": int, "offset": int,
     "value": {"event_id", "order_id", "status", "amount", "customer_state", "event_time"}}

`event_time` là chuỗi ISO-8601 UTC cùng định dạng, nên so sánh chuỗi = so sánh thời gian.
"""

from __future__ import annotations

import sqlite3


class OrderSink:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def init_schema(self) -> None:
        """Tạo các bảng cần thiết (gọi nhiều lần không lỗi).

        Gợi ý tối thiểu:
        - orders(order_id PK, status, amount, customer_state, event_time)
        - processed_events(event_id PK)
        - consumer_offsets(topic, partition, next_offset, PK(topic, partition))
        """
        # TODO 1
        raise NotImplementedError

    def process_batch(self, records: list[dict], fail_after: int | None = None) -> int:
        """Áp dụng một batch trong MỘT transaction và trả về số record thực sự được áp dụng.

        - Bỏ qua record có offset < next_offset đã lưu của (topic, partition) (đã xử lý ở lần trước).
        - Bỏ qua event_id đã xử lý (trùng do producer retry, nằm ở offset khác).
        - Upsert orders: chỉ ghi đè khi event_time mới hơn event_time đang lưu
          (event cũ đến muộn không được làm lùi trạng thái).
        - Cập nhật next_offset = offset lớn nhất + 1 cho mỗi (topic, partition) có trong batch.
        - fail_after=n: giả lập crash, raise RuntimeError sau khi đã xử lý n record của batch.
          Khi đó KHÔNG thay đổi nào của batch được lưu.
        """
        # TODO 2
        raise NotImplementedError

    def committed_offsets(self) -> dict[tuple[str, int], int]:
        """{(topic, partition): next_offset} — vị trí consumer sẽ seek() tới khi khởi động lại."""
        # TODO 3
        raise NotImplementedError

    def order_status(self, order_id: str) -> dict | None:
        """{"status", "amount", "customer_state", "event_time"} hoặc None."""
        # TODO 4
        raise NotImplementedError

    def gmv_by_state(self) -> dict[str, float]:
        """Tổng amount theo customer_state của các đơn có trạng thái hiện tại khác 'canceled'.

        Làm tròn 2 chữ số.
        """
        # TODO 5
        raise NotImplementedError

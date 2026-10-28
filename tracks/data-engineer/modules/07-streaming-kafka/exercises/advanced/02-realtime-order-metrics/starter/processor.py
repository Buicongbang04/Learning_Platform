"""Stream processor cho order events của Olist: parse → validate → dedup → window theo event time.

Đầu vào là bytes (value của record Kafka), JSON object:
    {"event_id": str, "order_id": str, "status": str, "amount": number,
     "customer_state": str, "event_time": int (giây epoch)}

Đầu ra là kết quả theo tumbling window và bang:
    {"window_start", "window_end", "customer_state", "orders", "gmv", "canceled"}
    - orders: số event status == "created"
    - gmv: tổng amount của các event "created", làm tròn 2 chữ số
    - canceled: số event status == "canceled"
"""

from __future__ import annotations

VALID_STATUSES = {"created", "approved", "shipped", "delivered", "canceled"}


class OrderMetricsProcessor:
    def __init__(self, window_size: int = 60, allowed_lateness: int = 120, dedup_ttl: int = 3600):
        self.window_size = window_size
        self.allowed_lateness = allowed_lateness
        self.dedup_ttl = dedup_ttl
        self.dlq: list[dict] = []        # {"raw": bytes, "reason": str}
        self.late: list[dict] = []       # event (dict) đến sau khi window đã đóng
        self.duplicates = 0
        # TODO 1: khai báo state bạn cần (max_event_time, state của window, bộ nhớ dedup...)

    @property
    def watermark(self) -> int | None:
        """max_event_time - allowed_lateness, None khi chưa có event hợp lệ."""
        # TODO 2
        raise NotImplementedError

    def process(self, raw: bytes) -> list[dict]:
        """Xử lý một message, trả về các window vừa đóng (sắp theo window_start, customer_state).

        Thứ tự:
        1. Parse JSON + validate. Lỗi → self.dlq.append({"raw": raw, "reason": "..."}), trả [].
        2. Dedup theo event_id: đã thấy (và chưa hết TTL) → self.duplicates += 1, trả [].
           Bộ nhớ dedup quên event_id có event_time < max_event_time - dedup_ttl.
        3. Late: window của event có end <= watermark hiện tại → self.late.append(event), trả [].
        4. Cộng vào window (chỉ status created/canceled ảnh hưởng metric), cập nhật max_event_time.
        5. Phát mọi window có end <= watermark mới.
        """
        # TODO 3
        raise NotImplementedError

    def flush(self) -> list[dict]:
        """Kết thúc stream, phát mọi window còn lại."""
        # TODO 4
        raise NotImplementedError

    def stats(self) -> dict:
        """{"emitted_windows", "duplicates", "late", "dlq"} để xuất metric giám sát."""
        # TODO 5
        raise NotImplementedError

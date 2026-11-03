"""Consumer Kafka tính feature cửa sổ tumbling theo event time cho từng zone."""

import json
import uuid
from datetime import datetime

from kafka import KafkaConsumer


class ZoneWindows:
    def __init__(self, window_s: int, lateness_s: int):
        self.window_s = window_s
        self.lateness_s = lateness_s
        self.watermark: int | None = None
        self.late = 0
        self.duplicates = 0
        self._seen: set[str] = set()
        self._open: dict[tuple[int, int], list] = {}

    def add(self, event: dict) -> list[dict]:
        if event["event_id"] in self._seen:
            self.duplicates += 1
            return []
        self._seen.add(event["event_id"])
        ts = int(datetime.fromisoformat(event["pickup_at"]).timestamp())
        start = ts - ts % self.window_s
        if self.watermark is not None and start + self.window_s <= self.watermark:
            self.late += 1
            return []
        state = self._open.setdefault((event["zone_id"], start), [0, 0.0])
        state[0] += 1
        state[1] += event["fare"]
        mark = ts - self.lateness_s
        self.watermark = mark if self.watermark is None else max(self.watermark, mark)
        return self._close(lambda start: start + self.window_s <= self.watermark)

    def flush(self) -> list[dict]:
        return self._close(lambda start: True)

    def _close(self, ready) -> list[dict]:
        keys = sorted((k for k in self._open if ready(k[1])), key=lambda k: (k[1], k[0]))
        rows = []
        for zone_id, start in keys:
            trips, total = self._open.pop((zone_id, start))
            rows.append({"zone_id": zone_id, "window_start": start, "window_end": start + self.window_s,
                         "trips": trips, "avg_fare": total / trips})
        return rows


def consume_windows(bootstrap: str, topic: str, *, window_s: int = 900, lateness_s: int = 180, idle_ms: int = 3000) -> dict:
    consumer = KafkaConsumer(
        topic,
        bootstrap_servers=bootstrap,
        group_id=f"zone-windows-{uuid.uuid4().hex[:8]}",
        auto_offset_reset="earliest",
        enable_auto_commit=False,
        consumer_timeout_ms=idle_ms,
        value_deserializer=lambda raw: json.loads(raw.decode("utf-8")),
    )
    windows = ZoneWindows(window_s, lateness_s)
    rows, consumed = [], 0
    try:
        for message in consumer:
            consumed += 1
            rows.extend(windows.add(message.value))
    finally:
        consumer.close()
    rows.extend(windows.flush())
    return {"windows": rows, "late": windows.late, "duplicates": windows.duplicates, "consumed": consumed}

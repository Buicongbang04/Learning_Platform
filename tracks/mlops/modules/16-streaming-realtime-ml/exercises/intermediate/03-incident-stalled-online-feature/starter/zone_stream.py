"""Feature 15 phút cho từng zone (số chuyến, giá trung bình), nhận sự kiện từ các gateway qua Kafka."""

from datetime import datetime, timezone


def _when(raw: str) -> int:
    return int(datetime.fromisoformat(raw.replace("Z", "")).replace(tzinfo=timezone.utc).timestamp())


class ZoneStream:
    def __init__(self, window_s: int = 900, hold_s: int = 180):
        self.window_s = window_s
        self.hold_s = hold_s
        self.stats = {"accepted": 0, "skipped": 0, "repeated": 0, "rejected": 0}
        self._progress: int | None = None
        self._seen: set[str] = set()
        self._open: dict[tuple[int, int], list] = {}
        self._latest: dict[int, dict] = {}

    def ingest(self, event: dict) -> list[dict]:
        if event["event_id"] in self._seen:
            self.stats["repeated"] += 1
            return []
        self._seen.add(event["event_id"])
        ts = _when(event["pickup_at"])
        start = ts - ts % self.window_s
        if self._progress is not None and start + self.window_s <= self._progress:
            self.stats["skipped"] += 1
            return []
        self.stats["accepted"] += 1
        bucket = self._open.setdefault((event["zone_id"], start), [0, 0.0])
        bucket[0] += 1
        bucket[1] += event["fare"]
        mark = ts - self.hold_s
        self._progress = mark if self._progress is None else max(self._progress, mark)
        return self._close(lambda end: end <= self._progress)

    def flush(self) -> list[dict]:
        return self._close(lambda end: True)

    def snapshot(self) -> dict[int, dict]:
        return {zone: dict(row) for zone, row in self._latest.items()}

    def _close(self, ready) -> list[dict]:
        keys = sorted((k for k in self._open if ready(k[1] + self.window_s)), key=lambda k: (k[1], k[0]))
        rows = []
        for zone_id, start in keys:
            trips, total = self._open.pop((zone_id, start))
            row = {"zone_id": zone_id, "window_start": start, "window_end": start + self.window_s,
                   "trips": trips, "avg_fare": total / trips}
            rows.append(row)
            if zone_id not in self._latest or row["window_end"] >= self._latest[zone_id]["window_end"]:
                self._latest[zone_id] = row
        return rows

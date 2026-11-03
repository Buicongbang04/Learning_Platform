"""Cửa sổ theo event time: tumbling, sliding, session và bộ gộp có watermark, sự kiện trễ, trùng lặp."""


def tumbling_start(ts: int, size: int) -> int:
    return ts - ts % size


def sliding_windows(ts: int, size: int, step: int) -> list[tuple[int, int]]:
    last = ts - ts % step
    starts = range(last, ts - size, -step)
    return sorted((s, s + size) for s in starts if s <= ts < s + size)


def session_windows(timestamps: list[int], gap: int) -> list[tuple[int, int]]:
    sessions: list[list[int]] = []
    for ts in sorted(timestamps):
        if sessions and ts < sessions[-1][1]:
            sessions[-1][1] = max(sessions[-1][1], ts + gap)
        else:
            sessions.append([ts, ts + gap])
    return [(start, end) for start, end in sessions]


class WindowAggregator:
    def __init__(self, size: int, lateness: int):
        self.size = size
        self.lateness = lateness
        self.watermark: int | None = None
        self.late = 0
        self.duplicates = 0
        self._seen: set = set()
        self._open: dict[tuple, dict] = {}

    def add(self, event: dict) -> list[dict]:
        if event["event_id"] in self._seen:
            self.duplicates += 1
            return []
        self._seen.add(event["event_id"])
        start = tumbling_start(event["ts"], self.size)
        end = start + self.size
        if self.watermark is not None and end <= self.watermark:
            self.late += 1
            return []
        row = self._open.setdefault((event["key"], start), {
            "key": event["key"], "window_start": start, "window_end": end, "count": 0, "total": 0.0,
        })
        row["count"] += 1
        row["total"] += event["value"]
        candidate = event["ts"] - self.lateness
        self.watermark = candidate if self.watermark is None else max(self.watermark, candidate)
        return self._emit(lambda row: row["window_end"] <= self.watermark)

    def flush(self) -> list[dict]:
        return self._emit(lambda row: True)

    def _emit(self, ready) -> list[dict]:
        done = [key for key, row in self._open.items() if ready(row)]
        rows = [self._open.pop(key) for key in done]
        return sorted(rows, key=lambda r: (r["window_end"], r["key"]))

"""Tốc độ trung bình theo zone đón trong cửa sổ tumbling 15 phút theo event time (lúc trả khách), có watermark."""

import json
import math
import time
import uuid

import pandas as pd

from eta.streaming.events import LATENESS_S, WINDOW_S, epoch

FEATURE = "speed_15m_mph"
COLUMNS = ["PULocationID", "window_start", "window_end", "trips", FEATURE]


MAX_DISTANCE = 100.0
MAX_DURATION_S = 10_800.0


def _number(value) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def _valid(event) -> bool:
    if not isinstance(event, dict):
        return False
    try:
        epoch(event["dropoff_at"])
        zone, distance, seconds = event["PULocationID"], event["trip_distance"], event["duration_s"]
    except (KeyError, TypeError, ValueError, OverflowError):
        return False
    return (isinstance(event.get("trip_id"), str) and isinstance(zone, int) and not isinstance(zone, bool)
            and _number(distance) and _number(seconds) and 0 <= distance <= MAX_DISTANCE and 0 < seconds <= MAX_DURATION_S)


class ZoneSpeedWindows:
    def __init__(self, window_s: int = WINDOW_S, lateness_s: int = LATENESS_S):
        self.window_s = window_s
        self.lateness_s = lateness_s
        self.watermark: int | None = None
        self.late = 0
        self.duplicates = 0
        self.invalid = 0
        self._seen: set[str] = set()
        self._open: dict[tuple[int, int], list] = {}

    def add(self, event) -> list[dict]:
        if not _valid(event):
            self.invalid += 1
            return []
        if event["trip_id"] in self._seen:
            self.duplicates += 1
            return []
        self._seen.add(event["trip_id"])
        ts = epoch(event["dropoff_at"])
        start = ts - ts % self.window_s
        if self.watermark is not None and start + self.window_s <= self.watermark:
            self.late += 1
            return []
        state = self._open.setdefault((event["PULocationID"], start), [0, 0.0, 0.0])
        state[0] += 1
        state[1] += float(event["trip_distance"])
        state[2] += float(event["duration_s"])
        mark = ts - self.lateness_s
        self.watermark = mark if self.watermark is None else max(self.watermark, mark)
        return self._close(lambda s: s + self.window_s <= self.watermark)

    def flush(self) -> list[dict]:
        return self._close(lambda s: True)

    def _close(self, ready) -> list[dict]:
        keys = sorted((k for k in self._open if ready(k[1])), key=lambda k: (k[1], k[0]))
        rows = []
        for zone, start in keys:
            trips, distance, seconds = self._open.pop((zone, start))
            rows.append({"PULocationID": zone, "window_start": start, "window_end": start + self.window_s,
                         "trips": trips, FEATURE: distance / (seconds / 3600)})
        return rows


def _decode(raw):
    if not isinstance(raw, (bytes, bytearray)):
        return None
    try:
        return json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, ValueError, RecursionError):
        return None


def consume(bootstrap: str, topic: str, *, on_close=None, idle_ms: int = 3000, first_wait_s: float = 30.0,
            window_s: int = WINDOW_S, lateness_s: int = LATENESS_S) -> dict:
    from kafka import KafkaConsumer

    consumer = KafkaConsumer(topic, bootstrap_servers=bootstrap, group_id=f"eta-speed-{uuid.uuid4().hex[:8]}",
                             auto_offset_reset="earliest", enable_auto_commit=False, consumer_timeout_ms=200)
    windows = ZoneSpeedWindows(window_s, lateness_s)
    rows, consumed = [], 0
    started = time.monotonic()
    last = None

    def emit(closed):
        if closed:
            rows.extend(closed)
            if on_close is not None:
                on_close(closed)

    try:
        while (time.monotonic() - started < first_wait_s) if last is None else (time.monotonic() - last < idle_ms / 1000):
            for message in consumer:
                consumed += 1
                last = time.monotonic()
                emit(windows.add(_decode(message.value)))
    finally:
        consumer.close()
    emit(windows.flush())
    return {"windows": rows, "late": windows.late, "duplicates": windows.duplicates, "invalid": windows.invalid,
            "consumed": consumed}


def zone_speed_batch(trips: pd.DataFrame, window_s: int = WINDOW_S) -> pd.DataFrame:
    dropoff = pd.to_datetime(trips["tpep_dropoff_datetime"]).astype("datetime64[s]")
    ts = (dropoff - pd.Timestamp("1970-01-01")) // pd.Timedelta(seconds=1)
    frame = pd.DataFrame({"PULocationID": trips["PULocationID"].astype("int64").to_numpy(),
                          "window_start": (ts - ts % window_s).astype("int64").to_numpy(),
                          "distance": trips["trip_distance"].astype("float64").to_numpy(),
                          "seconds": trips["duration_s"].astype("float64").to_numpy()})
    grouped = frame.groupby(["PULocationID", "window_start"]).agg(trips=("seconds", "size"), distance=("distance", "sum"),
                                                                   seconds=("seconds", "sum")).reset_index()
    grouped["window_end"] = grouped["window_start"] + window_s
    grouped[FEATURE] = grouped["distance"] / (grouped["seconds"] / 3600)
    grouped["trips"] = grouped["trips"].astype("int64")
    return grouped[COLUMNS].sort_values(["window_end", "PULocationID"], kind="stable").reset_index(drop=True)

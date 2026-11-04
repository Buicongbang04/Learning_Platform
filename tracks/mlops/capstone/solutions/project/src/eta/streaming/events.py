"""Sự kiện "chuyến đã kết thúc" và đồng hồ mô phỏng để phát lại một lát dữ liệu TLC thật vào Kafka."""

import json
import time
from dataclasses import dataclass
from datetime import datetime, timezone

import pandas as pd

WINDOW_S = 900
LATENESS_S = 120
FIELDS = ("trip_id", "PULocationID", "dropoff_at", "trip_distance", "duration_s")


def epoch(value: str) -> int:
    return int(datetime.fromisoformat(value).replace(tzinfo=timezone.utc).timestamp())


def trip_events(trips: pd.DataFrame) -> list[dict]:
    dropoff = pd.to_datetime(trips["tpep_dropoff_datetime"])
    frame = pd.DataFrame({
        "trip_id": [str(i) for i in trips.index],
        "PULocationID": trips["PULocationID"].astype("int64").to_numpy(),
        "dropoff_at": dropoff.dt.strftime("%Y-%m-%dT%H:%M:%S").to_numpy(),
        "trip_distance": trips["trip_distance"].astype("float64").to_numpy(),
        "duration_s": trips["duration_s"].astype("float64").to_numpy(),
        "_order": dropoff.to_numpy(),
    })
    frame = frame.sort_values("_order", kind="stable")
    return [
        {"trip_id": t, "PULocationID": int(z), "dropoff_at": d, "trip_distance": float(x), "duration_s": float(s)}
        for t, z, d, x, s in zip(frame["trip_id"], frame["PULocationID"], frame["dropoff_at"], frame["trip_distance"],
                                 frame["duration_s"], strict=True)
    ]


@dataclass(frozen=True)
class SimClock:
    sim_start: float
    wall_start: float
    speedup: float

    def sim(self, wall: float) -> float:
        return self.sim_start + (wall - self.wall_start) * self.speedup

    def wall(self, sim: float) -> float:
        return self.wall_start + (sim - self.sim_start) / self.speedup


def replay(bootstrap: str, topic: str, events: list[dict], clock: SimClock, *, now=time.time, sleep=time.sleep) -> int:
    from kafka import KafkaProducer

    producer = KafkaProducer(bootstrap_servers=bootstrap, linger_ms=0,
                             key_serializer=lambda k: str(k).encode("utf-8"),
                             value_serializer=lambda v: json.dumps(v).encode("utf-8"))
    latest = None
    try:
        for event in events:
            ts = epoch(event["dropoff_at"])
            latest = ts if latest is None else max(latest, ts)
            wait = clock.wall(latest) - now()
            if wait > 0:
                sleep(wait)
            producer.send(topic, key=event["PULocationID"], value=event)
        producer.flush(timeout=30)
    finally:
        producer.close()
    return len(events)

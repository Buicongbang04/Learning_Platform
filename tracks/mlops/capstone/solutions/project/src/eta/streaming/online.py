"""Đọc feature `speed_15m_mph` cho train (point-in-time trên bảng cửa sổ) và cho API (snapshot online), một luật cho cả hai."""

import json
import os
import threading
from pathlib import Path

import numpy as np
import pandas as pd

from eta.streaming.events import LATENESS_S
from eta.streaming.windows import FEATURE
from eta.zone_features import DEFAULT_SPEED_MPH

TTL_S = 1800
FRESH, STALE, MISSING = "fresh", "stale", "missing"


class MissingOnlineFeatures(RuntimeError):
    pass


def needs_live_speed(model) -> bool:
    return FEATURE in getattr(model, "feature_names_in_", ())


def epoch_seconds(stamps) -> np.ndarray:
    values = pd.to_datetime(pd.Series(stamps)).astype("datetime64[s]")
    return ((values - pd.Timestamp("1970-01-01")) // pd.Timedelta(seconds=1)).to_numpy(dtype="int64")


def usable(age_s: float) -> bool:
    return LATENESS_S <= age_s <= TTL_S


def attach_live_speed(trips: pd.DataFrame, windows: pd.DataFrame) -> pd.DataFrame:
    left = pd.DataFrame({"_row": np.arange(len(trips)), "_ts": epoch_seconds(trips["tpep_pickup_datetime"]),
                         "PULocationID": trips["PULocationID"].astype("int64").to_numpy()})
    right = pd.DataFrame({"_ts": windows["window_end"].astype("int64").to_numpy() + LATENESS_S,
                          "PULocationID": windows["PULocationID"].astype("int64").to_numpy(),
                          FEATURE: windows[FEATURE].astype("float64").to_numpy()})
    merged = pd.merge_asof(left.sort_values("_ts", kind="mergesort"), right.sort_values("_ts", kind="mergesort"),
                           on="_ts", by="PULocationID", direction="backward", tolerance=TTL_S - LATENESS_S)
    out = trips.copy()
    out[FEATURE] = merged.sort_values("_row")[FEATURE].fillna(DEFAULT_SPEED_MPH).to_numpy()
    return out


class OnlineSpeed:
    def __init__(self, path):
        self.path = Path(path)
        self._lock = threading.Lock()
        self._stamp = None
        self._rows: dict[int, tuple[float, int]] = {}

    def rows(self) -> dict[int, tuple[float, int]]:
        try:
            stat = os.stat(self.path)
        except FileNotFoundError:
            return {}
        stamp = (stat.st_mtime_ns, stat.st_size, stat.st_ino)
        with self._lock:
            if stamp != self._stamp:
                data = json.loads(self.path.read_text(encoding="utf-8"))
                self._rows = {int(r["PULocationID"]): (float(r[FEATURE]), int(r["window_end"])) for r in data["rows"]}
                self._stamp = stamp
            return self._rows

    def lookup(self, zone: int, pickup) -> tuple[float, str, float | None]:
        found = self.rows().get(int(zone))
        if found is None:
            return DEFAULT_SPEED_MPH, MISSING, None
        value, window_end = found
        age = float(epoch_seconds([pickup])[0] - window_end)
        return (value, FRESH, age) if usable(age) else (DEFAULT_SPEED_MPH, STALE, age)

    def attach(self, frame: pd.DataFrame) -> tuple[pd.DataFrame, list[tuple[float, str, float | None]]]:
        found = [self.lookup(z, p) for z, p in zip(frame["PULocationID"], frame["tpep_pickup_datetime"], strict=True)]
        out = frame.copy()
        out[FEATURE] = [f[0] for f in found]
        return out, found

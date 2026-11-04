"""Đẩy cửa sổ đã đóng vào Feast qua push source và xuất snapshot online cho API.

Chạy trong container Feast (không có package `eta`): chỉ import pandas và thư viện chuẩn ở đầu tệp, `feast` bên trong hàm.
"""

import json
import os
from pathlib import Path

import pandas as pd

PUSH_SOURCE = "zone_speed_push"
FEATURE_VIEW = "zone_speed_15m"
FEATURE = "speed_15m_mph"
REFS = [f"{FEATURE_VIEW}:{FEATURE}", f"{FEATURE_VIEW}:trips"]


def to_push_frame(windows: list[dict]) -> pd.DataFrame:
    frame = pd.DataFrame({
        "PULocationID": pd.Series([w["PULocationID"] for w in windows], dtype="int64"),
        FEATURE: pd.Series([w[FEATURE] for w in windows], dtype="float64"),
        "trips": pd.Series([w["trips"] for w in windows], dtype="int64"),
        "event_timestamp": pd.to_datetime(pd.Series([w["window_end"] for w in windows], dtype="int64"), unit="s", utc=True),
    })
    return frame.sort_values(["event_timestamp", "PULocationID"], kind="stable").reset_index(drop=True)


def push(store, frame: pd.DataFrame) -> int:
    from feast.data_source import PushMode

    if frame.empty:
        return 0
    store.push(PUSH_SOURCE, frame, to=PushMode.OFFLINE)
    latest = frame.sort_values("event_timestamp", kind="stable").groupby("PULocationID").tail(1)
    current = store.get_online_features(features=REFS, entity_rows=[{"PULocationID": int(z)} for z in latest["PULocationID"]])
    stamps = current.to_dict(include_event_timestamps=True)
    online = dict(zip(stamps["PULocationID"], stamps[f"{FEATURE}__ts"], strict=True))
    keep = [ts.timestamp() >= (online.get(int(z)) or 0) for z, ts in zip(latest["PULocationID"], latest["event_timestamp"], strict=True)]
    newer = latest[keep]
    if not newer.empty:
        store.push(PUSH_SOURCE, newer, to=PushMode.ONLINE)
    return len(newer)


def export_online(store, zones: list[int], path) -> int:
    got = store.get_online_features(features=REFS, entity_rows=[{"PULocationID": int(z)} for z in zones])
    data = got.to_dict(include_event_timestamps=True)
    rows = [{"PULocationID": int(z), FEATURE: float(v), "trips": int(t), "window_end": int(ts)}
            for z, v, t, ts in zip(data["PULocationID"], data[FEATURE], data["trips"], data[f"{FEATURE}__ts"], strict=True) if v is not None]
    path = Path(path)
    tmp = path.with_name(f".{path.name}.tmp")
    tmp.write_text(json.dumps({"feature_view": FEATURE_VIEW, "rows": rows}), encoding="utf-8")
    os.replace(tmp, path)
    return len(rows)

"""Đẩy feature cửa sổ vào Feast qua push source; chạy trong container Feast, phần dựng DataFrame chạy được cả trên máy."""

import pandas as pd

PUSH_SOURCE = "zone_window_push"
REFS = ["zone_window:trips", "zone_window:avg_fare"]


def to_push_frame(windows: list[dict]) -> pd.DataFrame:
    frame = pd.DataFrame({
        "zone_id": pd.Series([w["zone_id"] for w in windows], dtype="int64"),
        "trips": pd.Series([w["trips"] for w in windows], dtype="int64"),
        "avg_fare": pd.Series([w["avg_fare"] for w in windows], dtype="float64"),
        "event_timestamp": pd.to_datetime(pd.Series([w["window_end"] for w in windows], dtype="int64"), unit="s", utc=True),
    })
    return frame.sort_values(["event_timestamp", "zone_id"], kind="stable").reset_index(drop=True)


def push(store, frame: pd.DataFrame) -> int:
    from feast.data_source import PushMode

    if frame.empty:
        return 0
    store.push(PUSH_SOURCE, frame, to=PushMode.OFFLINE)
    latest = frame.sort_values("event_timestamp", kind="stable").groupby("zone_id").tail(1)
    rows = [{"zone_id": int(z)} for z in latest["zone_id"]]
    current = store.get_online_features(features=REFS, entity_rows=rows).to_dict(include_event_timestamps=True)
    online_ts = dict(zip(current["zone_id"], current["trips__ts"]))
    keep = [ts.timestamp() >= (online_ts.get(int(z)) or 0) for z, ts in zip(latest["zone_id"], latest["event_timestamp"])]
    newer = latest[keep]
    if not newer.empty:
        store.push(PUSH_SOURCE, newer, to=PushMode.ONLINE)
    return len(newer)

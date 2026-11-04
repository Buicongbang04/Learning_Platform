"""Tiện ích chung cho test module 16: lát chuyến taxi NYC thật (TLC 2019-03) để phát lại thành stream.

Dữ liệu đi qua `mlopskit.real_month` (kiểm sha256, skip khi chưa tải).
"""

import random

import pandas as pd

import mlopskit

ZONES = (48, 161, 238)


def zone_trips(zones=ZONES, start="2019-03-05 08:00", hours=2, frac=0.5, seed=0) -> pd.DataFrame:
    """Chuyến đón khách ở `zones` trong `hours` giờ từ `start`, lấy mẫu `frac`; cột zone_id, pickup, fare, event_id."""
    path = mlopskit.real_month("nyc-tlc", "2019-03")
    begin = pd.Timestamp(start)
    end = begin + pd.Timedelta(hours=hours)
    df = pd.read_parquet(
        path,
        columns=["tpep_pickup_datetime", "PULocationID", "fare_amount"],
        filters=[("tpep_pickup_datetime", ">=", begin), ("tpep_pickup_datetime", "<", end)],
    )
    df = df[df["PULocationID"].isin(zones) & (df["fare_amount"] > 0)]
    df = df.sample(frac=frac, random_state=seed).sort_values(["tpep_pickup_datetime", "PULocationID"], kind="stable")
    out = pd.DataFrame({
        "zone_id": df["PULocationID"].astype("int64").to_numpy(),
        "pickup": df["tpep_pickup_datetime"].astype("datetime64[ns]").to_numpy(),
        "fare": df["fare_amount"].astype("float64").round(2).to_numpy(),
    })
    out["event_id"] = [f"trip-{i:06d}" for i in range(len(out))]
    return out


def shuffle_bounded(items: list, max_shift: int, seed: int) -> list:
    """Đảo thứ tự nhưng mỗi phần tử lệch tối đa `max_shift` vị trí so với gốc (mô phỏng mạng làm lệch thứ tự)."""
    rng = random.Random(seed)
    keyed = [(i + rng.uniform(0, max_shift), i, item) for i, item in enumerate(items)]
    return [item for _, _, item in sorted(keyed, key=lambda k: (k[0], k[1]))]

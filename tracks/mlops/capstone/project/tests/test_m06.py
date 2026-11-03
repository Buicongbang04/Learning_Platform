"""M06: feature tốc độ theo zone/giờ, point-in-time, Feast online == offline. Đề ở capstone/milestones/m06-feast-features.md."""

import json
import os
import shutil
import uuid

import numpy as np
import pandas as pd
import pytest
import yaml
from etakit import PROJECT, need, require_file, synthetic_month

import mlopskit

SPEED_COLUMNS = ["PULocationID", "pickup_hour", "avg_speed_mph", "event_timestamp"]
TRIP_COLUMNS = ["tpep_pickup_datetime", "tpep_dropoff_datetime", "PULocationID", "DOLocationID", "trip_distance"]


def clean_month(month: str, n: int, seed: int) -> pd.DataFrame:
    features = need("features", "clean")
    return features.clean(synthetic_month(n, month=month, seed=seed, extra_columns=False), month)


def lookup(features: pd.DataFrame, trips: pd.DataFrame) -> np.ndarray:
    keyed = features.set_index(["PULocationID", "pickup_hour"])["avg_speed_mph"]
    keys = list(zip(trips["PULocationID"], trips["tpep_pickup_datetime"].dt.hour))
    return np.array([keyed.get(k, np.nan) for k in keys], dtype=float)


def test_m06_zone_hour_speed_table(project):
    zf = need("zone_features", "zone_hour_speed", "MIN_TRIPS")
    jan = clean_month("2019-01", 6_000, 11)
    before = jan.copy()
    table = zf.zone_hour_speed(jan, "2019-01")
    assert jan.equals(before), "zone_hour_speed không được sửa DataFrame đầu vào"
    assert list(table.columns) == SPEED_COLUMNS
    assert not table.duplicated(["PULocationID", "pickup_hour"]).any(), "mỗi (zone, giờ) một dòng"
    assert (table["event_timestamp"] == pd.Timestamp("2019-02-01")).all(), "event_timestamp là đầu tháng sau"
    speed = jan["trip_distance"] / (jan["duration_s"] / 3600)
    groups = speed.groupby([jan["PULocationID"], jan["tpep_pickup_datetime"].dt.hour])
    expected = groups.median()[groups.size() >= zf.MIN_TRIPS]
    got = table.set_index(["PULocationID", "pickup_hour"])["avg_speed_mph"].sort_index()
    assert len(got) == len(expected), f"chỉ giữ nhóm có ít nhất MIN_TRIPS={zf.MIN_TRIPS} chuyến"
    assert np.allclose(got.to_numpy(), expected.sort_index().to_numpy()), "avg_speed_mph = trung vị tốc độ từng chuyến (dặm/giờ)"


def test_m06_point_in_time_no_future(project):
    zf = need("zone_features", "zone_hour_speed", "attach_speed", "DEFAULT_SPEED_MPH")
    jan, feb = clean_month("2019-01", 6_000, 11), clean_month("2019-02", 6_000, 12)
    table = pd.concat([zf.zone_hour_speed(jan, "2019-01"), zf.zone_hour_speed(feb, "2019-02")], ignore_index=True)
    jan_table = table[table["event_timestamp"] == pd.Timestamp("2019-02-01")]
    trips = feb.sample(frac=1.0, random_state=0)
    before = trips.copy()
    out = zf.attach_speed(trips, table)
    assert trips.equals(before), "attach_speed không được sửa DataFrame đầu vào"
    assert out.index.equals(trips.index) and len(out) == len(trips), "giữ nguyên thứ tự và index của chuyến"
    assert out["avg_speed_mph"].notna().all()
    expected = lookup(jan_table, trips)
    expected = np.where(np.isnan(expected), zf.DEFAULT_SPEED_MPH, expected)
    assert np.allclose(out["avg_speed_mph"].to_numpy(), expected), (
        "chuyến tháng 2 chỉ được dùng feature tính từ tháng 1 (event_timestamp <= giờ đón); feature tháng 2 là tương lai"
    )
    first = zf.attach_speed(jan, table)
    assert (first["avg_speed_mph"] == zf.DEFAULT_SPEED_MPH).all(), "chuyến tháng 1 chưa có feature nào trước nó"


def test_m06_default_for_unknown_zone(project):
    zf = need("zone_features", "zone_hour_speed", "attach_speed", "DEFAULT_SPEED_MPH")
    assert 9.5 <= zf.DEFAULT_SPEED_MPH <= 10.5, "DEFAULT_SPEED_MPH là trung vị toàn thành phố đo trên mẫu 2019-01 (xem đề)"
    table = zf.zone_hour_speed(clean_month("2019-01", 6_000, 11), "2019-01")
    pickup = pd.to_datetime(["2019-02-10 08:30", "2019-02-10 08:30", "2019-05-20 08:30"]).astype("datetime64[us]")
    known = int(table.loc[table["pickup_hour"] == 8, "PULocationID"].iloc[0])
    trips = pd.DataFrame({"tpep_pickup_datetime": pickup, "PULocationID": [7, known, known],
                          "DOLocationID": [1, 1, 1], "trip_distance": [1.0, 1.0, 1.0]})
    out = zf.attach_speed(trips, table)
    value = float(table.loc[(table["PULocationID"] == known) & (table["pickup_hour"] == 8), "avg_speed_mph"].iloc[0])
    assert out["avg_speed_mph"].tolist() == pytest.approx([zf.DEFAULT_SPEED_MPH, value, zf.DEFAULT_SPEED_MPH]), (
        "zone không có feature → mặc định; feature quá TTL 62 ngày → mặc định"
    )


def test_m06_build_features_optional_speed(project):
    zf = need("zone_features", "zone_hour_speed", "attach_speed")
    features = need("features", "FEATURES", "build_features")
    train = need("train", "train", "evaluate")
    jan, feb = clean_month("2019-01", 6_000, 11), clean_month("2019-02", 4_000, 12)
    X_plain, _ = features.build_features(feb)
    assert list(X_plain.columns) == features.FEATURES, "không có cột avg_speed_mph thì feature như M01"
    with_speed = zf.attach_speed(feb, zf.zone_hour_speed(jan, "2019-01"))
    X, y = features.build_features(with_speed)
    assert list(X.columns) == [*features.FEATURES, "avg_speed_mph"], "có cột avg_speed_mph thì thêm vào cuối"
    model = train.train(X, y, {"max_iter": 20, "random_state": 0})
    assert set(train.evaluate(model, X, y)) == {"mae", "p90_abs_err", "mae_airport"}


PARITY_SCRIPT = """
import json
import pandas as pd
from feast import FeatureStore
store = FeatureStore(repo_path="/repo")
entities = pd.read_parquet("/repo/entities.parquet")
ref = ["zone_hour_speed:avg_speed_mph"]
hist = store.get_historical_features(entity_df=entities, features=ref).to_df()
hist = hist.sort_values(["PULocationID", "pickup_hour"])
rows = entities[["PULocationID", "pickup_hour"]].astype(int).to_dict("records")
online = store.get_online_features(features=ref, entity_rows=rows).to_dict()
print(json.dumps({
    "historical": [[int(a), int(b), float(c)] for a, b, c in zip(hist["PULocationID"], hist["pickup_hour"], hist["avg_speed_mph"])],
    "online": [[int(a), int(b), None if c is None else float(c)] for a, b, c in zip(online["PULocationID"], online["pickup_hour"], online["avg_speed_mph"])],
}))
"""


def last_json(text: str) -> dict:
    lines = [line for line in text.splitlines() if line.startswith("{")]
    assert lines, f"script Feast không in JSON:\n{text[-2000:]}"
    return json.loads(lines[-1])


def test_m06_online_offline_parity(project, tmp_path):
    require_file("feature_repo", "feature_store.yaml")
    require_file("feature_repo", "features.py")
    zf = need("zone_features", "zone_hour_speed", "attach_speed")
    mlopskit.require_stack("redis")
    network = os.environ.get("MLOPS_NETWORK", "mlops_default")
    repo = tmp_path / "feature_repo"
    shutil.copytree(PROJECT / "feature_repo", repo, ignore=shutil.ignore_patterns("data", "__pycache__", "*.db"))
    store_yaml = yaml.safe_load((repo / "feature_store.yaml").read_text(encoding="utf-8"))
    store_yaml["project"] = f"eta_test_{uuid.uuid4().hex[:8]}"
    (repo / "feature_store.yaml").write_text(yaml.safe_dump(store_yaml, sort_keys=False), encoding="utf-8")
    (repo / "data").mkdir()
    jan, feb = clean_month("2019-01", 6_000, 11), clean_month("2019-02", 6_000, 12)
    table = pd.concat([zf.zone_hour_speed(jan, "2019-01"), zf.zone_hour_speed(feb, "2019-02")], ignore_index=True)
    table.to_parquet(repo / "data" / "zone_hour_speed.parquet", index=False)
    keys = table.loc[table["event_timestamp"] == pd.Timestamp("2019-03-01"), ["PULocationID", "pickup_hour"]]
    keys = keys.sample(20, random_state=0).sort_values(["PULocationID", "pickup_hour"]).reset_index(drop=True)
    pickup = (pd.Timestamp("2019-03-10") + pd.to_timedelta(keys["pickup_hour"] * 60 + 30, unit="min")).astype("datetime64[us]")
    entities = keys.assign(event_timestamp=pickup)
    entities.to_parquet(repo / "entities.parquet", index=False)
    try:
        applied = mlopskit.feast_run(repo, "apply", network=network)
        assert applied.returncode == 0, applied.stdout[-1500:] + applied.stderr[-3000:]
        loaded = mlopskit.feast_run(repo, "materialize", "2019-01-01T00:00:00", "2019-03-15T00:00:00", network=network)
        assert loaded.returncode == 0, loaded.stdout[-1500:] + loaded.stderr[-3000:]
        result = mlopskit.feast_python(repo, PARITY_SCRIPT, network=network)
        assert result.returncode == 0, result.stderr[-3000:]
        got = last_json(result.stdout)
    finally:
        down = mlopskit.feast_run(repo, "teardown", network=network)
    assert down.returncode == 0, f"feast teardown lỗi, còn key trong Redis:\n{down.stderr[-2000:]}"
    trips = pd.DataFrame({"tpep_pickup_datetime": pickup, "PULocationID": keys["PULocationID"],
                          "DOLocationID": 1, "trip_distance": 1.0})
    host = zf.attach_speed(trips, table)["avg_speed_mph"].to_numpy()
    historical = np.array([row[2] for row in got["historical"]], dtype=float)
    online = np.array([np.nan if row[2] is None else row[2] for row in got["online"]], dtype=float)
    assert [row[:2] for row in got["historical"]] == keys.astype(int).values.tolist()
    assert [row[:2] for row in got["online"]] == keys.astype(int).values.tolist()
    assert np.allclose(online, historical, atol=1e-6), "online (Redis) phải bằng offline (get_historical_features)"
    assert np.allclose(host, historical, atol=1e-6), "attach_speed trên host phải bằng Feast offline: không skew"

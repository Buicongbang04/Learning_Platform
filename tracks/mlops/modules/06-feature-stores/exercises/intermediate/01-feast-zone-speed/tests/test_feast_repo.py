import json
import shutil
import uuid
from datetime import datetime, timezone

import pandas as pd
import pytest

import mlopskit
from testkit import Exercise

ex = Exercise(__file__)
NETWORK = "mlops_default"
FEATURES = ["zone_speed:avg_speed_mph", "zone_speed:trip_count"]

STORE_YAML = """project: {project}
registry: data/registry.db
provider: local
online_store:
  type: redis
  connection_string: "redis:6379"
offline_store:
  type: file
entity_key_serialization_version: 3
"""

READ_SCRIPT = """
import json
import pandas as pd
from feast import FeatureStore

fs = FeatureStore(".")
zones = {zones}
names = {names}
online = fs.get_online_features(features=names, entity_rows=[{{"zone_id": z}} for z in zones]).to_dict()
now = pd.Timestamp.now(tz="UTC")
past = now - pd.Timedelta(hours=10, minutes=30)
entity_df = pd.DataFrame({{"zone_id": zones + zones, "event_timestamp": [now] * len(zones) + [past] * len(zones)}})
offline = fs.get_historical_features(entity_df=entity_df, features=names).to_df()
offline["event_timestamp"] = offline["event_timestamp"].astype(str)
view = fs.get_feature_view("zone_speed")
print(json.dumps({{"online": online, "offline": json.loads(offline.to_json(orient="records")),
                  "past": str(past), "ttl_seconds": view.ttl.total_seconds(),
                  "features": [f.name for f in view.features], "entities": view.entities}}))
"""


def real_zone_stats(now):
    path = mlopskit.real_month("nyc-tlc", "2019-03")
    df = pd.read_parquet(path, columns=["tpep_pickup_datetime", "tpep_dropoff_datetime", "PULocationID", "trip_distance"])
    df = df.sample(150_000, random_state=0)
    hours = (df["tpep_dropoff_datetime"] - df["tpep_pickup_datetime"]).dt.total_seconds() / 3600
    df = df[(hours > 1 / 60) & (df["trip_distance"] > 0.1)]
    df = df.assign(speed=df["trip_distance"] / hours[df.index], hour=df["tpep_pickup_datetime"].dt.floor("h"))
    df = df[df["speed"] < 80]
    df = df[(df["hour"] >= "2019-03-04") & (df["hour"] < "2019-03-10")]
    first = pd.Timestamp("2019-03-05")
    df = df[(df["hour"] >= first) & (df["hour"] < first + pd.Timedelta(hours=48))]
    top = df["PULocationID"].value_counts().head(8).index
    table = (
        df[df["PULocationID"].isin(top)]
        .groupby(["PULocationID", "hour"])
        .agg(avg_speed_mph=("speed", "mean"), trip_count=("speed", "size"))
        .reset_index()
        .rename(columns={"PULocationID": "zone_id"})
    )
    shift = (now.tz_localize(None).floor("h") - pd.Timedelta(hours=1)) - table["hour"].max()
    table["event_timestamp"] = (table["hour"] + shift).dt.tz_localize("UTC")
    table = table.drop(columns="hour").astype({"avg_speed_mph": "float32", "trip_count": "int64", "zone_id": "int64"})
    return table.sort_values(["zone_id", "event_timestamp"]).reset_index(drop=True)


@pytest.fixture(scope="module")
def deployed(tmp_path_factory):
    mlopskit.require_stack("redis")
    repo = tmp_path_factory.mktemp("repo")
    project = f"mlops_ex_{uuid.uuid4().hex[:8]}"
    (repo / "data").mkdir()
    (repo / "feature_store.yaml").write_text(STORE_YAML.format(project=project), encoding="utf-8")
    shutil.copy(ex.path("features.py"), repo / "features.py")
    now = pd.Timestamp.now(tz="UTC")
    table = real_zone_stats(now)
    table.to_parquet(repo / "data" / "zone_stats.parquet")
    zones = sorted(table["zone_id"].unique().tolist()) + [999999]
    result = {"table": table, "zones": zones, "now": now}
    try:
        result["apply"] = mlopskit.feast_run(repo, "apply", network=NETWORK)
        if result["apply"].returncode == 0:
            end = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")
            result["materialize"] = mlopskit.feast_run(repo, "materialize-incremental", end, network=NETWORK)
            script = READ_SCRIPT.format(zones=zones, names=FEATURES)
            result["read"] = mlopskit.feast_python(repo, script, network=NETWORK)
        yield result
    finally:
        mlopskit.feast_python(repo, "from feast import FeatureStore\nFeatureStore('.').teardown()", network=NETWORK)


def output(cp):
    return f"returncode={cp.returncode}\nstdout:\n{cp.stdout[-1200:]}\nstderr:\n{cp.stderr[-1500:]}"


def parse(deployed):
    assert deployed["apply"].returncode == 0, "feast apply lỗi:\n" + output(deployed["apply"])
    assert deployed["materialize"].returncode == 0, "materialize-incremental lỗi:\n" + output(deployed["materialize"])
    assert deployed["read"].returncode == 0, "đọc feature lỗi:\n" + output(deployed["read"])
    return json.loads(deployed["read"].stdout.strip().splitlines()[-1])


def test_apply_succeeds(deployed):
    assert deployed["apply"].returncode == 0, "feast apply lỗi:\n" + output(deployed["apply"])
    assert "zone_speed" in deployed["apply"].stdout + deployed["apply"].stderr, "apply không đăng ký feature view zone_speed:\n" + output(deployed["apply"])


def test_materialize_incremental_succeeds(deployed):
    assert deployed["apply"].returncode == 0, "feast apply lỗi:\n" + output(deployed["apply"])
    assert deployed["materialize"].returncode == 0, output(deployed["materialize"])
    assert "zone_speed" in deployed["materialize"].stdout, "materialize không chạm feature view zone_speed:\n" + output(deployed["materialize"])


def test_view_shape_matches_contract(deployed):
    got = parse(deployed)
    assert got["features"] == ["avg_speed_mph", "trip_count"]
    assert got["entities"] == ["zone"]
    assert got["ttl_seconds"] >= 3 * 86400


def test_online_equals_latest_offline_row(deployed):
    got = parse(deployed)
    latest = deployed["table"].sort_values("event_timestamp").groupby("zone_id").tail(1).set_index("zone_id")
    online = pd.DataFrame(got["online"]).set_index("zone_id")
    for zone_id, row in latest.iterrows():
        assert online.loc[zone_id, "avg_speed_mph"] == pytest.approx(row["avg_speed_mph"], rel=1e-5)
        assert online.loc[zone_id, "trip_count"] == row["trip_count"]


def test_online_equals_offline_for_same_entity_and_time(deployed):
    got = parse(deployed)
    online = pd.DataFrame(got["online"]).set_index("zone_id")
    offline = pd.DataFrame(got["offline"])
    offline["ts"] = pd.to_datetime(offline["event_timestamp"], utc=True)
    at_now = offline[offline["ts"] > pd.Timestamp(got["past"]) + pd.Timedelta(hours=1)].set_index("zone_id")
    for zone_id in deployed["zones"][:-1]:
        assert at_now.loc[zone_id, "avg_speed_mph"] == pytest.approx(online.loc[zone_id, "avg_speed_mph"], rel=1e-5)
        assert at_now.loc[zone_id, "trip_count"] == online.loc[zone_id, "trip_count"]


def test_unknown_zone_is_empty_online(deployed):
    online = pd.DataFrame(parse(deployed)["online"]).set_index("zone_id")
    assert pd.isna(online.loc[999999, "avg_speed_mph"])
    assert pd.isna(online.loc[999999, "trip_count"])


def test_offline_join_is_point_in_time_correct(deployed):
    got = parse(deployed)
    table = deployed["table"]
    past = pd.Timestamp(got["past"])
    offline = pd.DataFrame(got["offline"])
    offline["ts"] = pd.to_datetime(offline["event_timestamp"], utc=True)
    past_rows = offline[offline["ts"] == past].set_index("zone_id")
    assert len(past_rows) == len(deployed["zones"])
    for zone_id in deployed["zones"][:-1]:
        pool = table[(table["zone_id"] == zone_id) & (table["event_timestamp"] <= past)]
        row = pool.loc[pool["event_timestamp"].idxmax()]
        assert past_rows.loc[zone_id, "trip_count"] == row["trip_count"]
        assert past_rows.loc[zone_id, "avg_speed_mph"] == pytest.approx(row["avg_speed_mph"], rel=1e-5)

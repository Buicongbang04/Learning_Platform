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
REFS = ["zone_speed:avg_speed_mph", "zone_speed:trip_count"]
DEFAULTS = {"avg_speed_mph": -1.0, "trip_count": 0}

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

SERVER_SCRIPT = """
import json, subprocess, time, urllib.request
import client

refs = {refs}
zones = {zones}
proc = subprocess.Popen(["feast", "serve", "-p", "6566", "-h", "127.0.0.1", "--no-access-log"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
try:
    for _ in range(90):
        try:
            urllib.request.urlopen("http://127.0.0.1:6566/health", timeout=1)
            break
        except Exception:
            time.sleep(1)
    body = client.build_request(refs, zones)
    req = urllib.request.Request("http://127.0.0.1:6566/get-online-features", data=json.dumps(body).encode(), headers={{"Content-Type": "application/json"}})
    raw = json.loads(urllib.request.urlopen(req, timeout=20).read().decode())
    values, defaulted = client.parse_response(raw, {defaults})
    print(json.dumps({{"body": body, "values": {{str(k): v for k, v in values.items()}}, "defaulted": {{str(k): v for k, v in defaulted.items()}}}}))
finally:
    proc.terminate()
"""


@pytest.fixture
def client():
    return ex.module("client.py")


def response(zone_ids, speeds, counts, speed_status=None, count_status=None):
    n = len(zone_ids)
    epoch = "1970-01-01T00:00:00Z"
    return {
        "metadata": {"feature_names": ["zone_id", "avg_speed_mph", "trip_count"]},
        "results": [
            {"values": zone_ids, "statuses": ["PRESENT"] * n, "event_timestamps": [epoch] * n},
            {"values": speeds, "statuses": speed_status or ["PRESENT"] * n, "event_timestamps": [epoch] * n},
            {"values": counts, "statuses": count_status or ["PRESENT"] * n, "event_timestamps": [epoch] * n},
        ],
    }


def test_build_request_shape(client):
    body = client.build_request(REFS, [3, 7])
    assert body == {"features": REFS, "entities": {"zone_id": [3, 7]}}
    json.dumps(body)


def test_build_request_dedupes_in_order_and_casts(client):
    body = client.build_request(REFS, [7, 3, 7, "3", 9])
    assert body["entities"]["zone_id"] == [7, 3, 9]
    assert all(type(z) is int for z in body["entities"]["zone_id"])


def test_build_request_does_not_alias_input(client):
    refs = list(REFS)
    body = client.build_request(refs, [1])
    body["features"].append("x")
    assert refs == REFS


@pytest.mark.parametrize("refs,zones", [([], [1]), (REFS, [])])
def test_build_request_rejects_empty(client, refs, zones):
    with pytest.raises(ValueError):
        client.build_request(refs, zones)


def test_parse_response_reads_columns_by_name(client):
    resp = response([3, 7], [11.5, 14.0], [100, 250])
    values, defaulted = client.parse_response(resp, DEFAULTS)
    assert values == {3: {"avg_speed_mph": 11.5, "trip_count": 100}, 7: {"avg_speed_mph": 14.0, "trip_count": 250}}
    assert defaulted == {}


def test_parse_response_does_not_depend_on_column_order(client):
    resp = response([3, 7], [11.5, 14.0], [100, 250])
    resp["metadata"]["feature_names"] = ["trip_count", "zone_id", "avg_speed_mph"]
    resp["results"] = [resp["results"][2], resp["results"][0], resp["results"][1]]
    values, _ = client.parse_response(resp, DEFAULTS)
    assert values[7] == {"avg_speed_mph": 14.0, "trip_count": 250}


def test_null_value_gets_default_even_when_status_says_present(client):
    resp = response([3, 99], [11.5, None], [100, None])
    values, defaulted = client.parse_response(resp, DEFAULTS)
    assert values[99] == DEFAULTS
    assert defaulted == {99: ["avg_speed_mph", "trip_count"]}
    assert values[3] == {"avg_speed_mph": 11.5, "trip_count": 100}


def test_defaulted_names_are_sorted_whatever_the_column_order(client):
    resp = response([99], [None], [None])
    resp["metadata"]["feature_names"] = ["trip_count", "zone_id", "avg_speed_mph"]
    resp["results"] = [resp["results"][2], resp["results"][0], resp["results"][1]]
    _, defaulted = client.parse_response(resp, DEFAULTS)
    assert defaulted == {99: ["avg_speed_mph", "trip_count"]}


@pytest.mark.parametrize("status", ["NOT_FOUND", "OUTSIDE_MAX_AGE", "NULL_VALUE"])
def test_non_present_status_gets_default(client, status):
    resp = response([3], [11.5], [100], speed_status=[status])
    values, defaulted = client.parse_response(resp, DEFAULTS)
    assert values[3] == {"avg_speed_mph": -1.0, "trip_count": 100}
    assert defaulted == {3: ["avg_speed_mph"]}


def test_missing_default_for_missing_value_is_an_error(client):
    resp = response([3], [None], [100])
    with pytest.raises(KeyError):
        client.parse_response(resp, {"trip_count": 0})


def real_zone_stats(now):
    path = mlopskit.real_month("nyc-tlc", "2019-03")
    df = pd.read_parquet(path, columns=["tpep_pickup_datetime", "tpep_dropoff_datetime", "PULocationID", "trip_distance"])
    df = df.sample(150_000, random_state=0)
    hours = (df["tpep_dropoff_datetime"] - df["tpep_pickup_datetime"]).dt.total_seconds() / 3600
    df = df[(hours > 1 / 60) & (df["trip_distance"] > 0.1)]
    df = df.assign(speed=df["trip_distance"] / hours[df.index], hour=df["tpep_pickup_datetime"].dt.floor("h"))
    df = df[(df["speed"] < 80) & (df["hour"] >= "2019-03-05") & (df["hour"] < "2019-03-07")]
    top = df["PULocationID"].value_counts().head(6).index
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
def served(tmp_path_factory):
    mlopskit.require_stack("redis")
    repo = tmp_path_factory.mktemp("repo")
    project = f"mlops_ex_{uuid.uuid4().hex[:8]}"
    (repo / "data").mkdir()
    (repo / "feature_store.yaml").write_text(STORE_YAML.format(project=project), encoding="utf-8")
    shutil.copy(Exercise(__file__).fixtures / "features.py", repo / "features.py")
    shutil.copy(ex.path("client.py"), repo / "client.py")
    table = real_zone_stats(pd.Timestamp.now(tz="UTC"))
    table.to_parquet(repo / "data" / "zone_stats.parquet")
    zones = sorted(table["zone_id"].unique().tolist())[:2] + [999999]
    result = {"table": table, "zones": zones}
    try:
        result["apply"] = mlopskit.feast_run(repo, "apply", network=NETWORK)
        if result["apply"].returncode == 0:
            end = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")
            result["materialize"] = mlopskit.feast_run(repo, "materialize-incremental", end, network=NETWORK)
            script = SERVER_SCRIPT.format(refs=REFS, zones=zones + [zones[0]], defaults=DEFAULTS)
            result["run"] = mlopskit.feast_python(repo, script, network=NETWORK, timeout=240)
        yield result
    finally:
        mlopskit.feast_python(repo, "from feast import FeatureStore\nFeatureStore('.').teardown()", network=NETWORK)


def parsed(served):
    assert served["apply"].returncode == 0, "feast apply (fixture) lỗi:\n" + served["apply"].stderr[-1500:]
    assert served["materialize"].returncode == 0, served["materialize"].stderr[-1500:]
    run = served["run"]
    assert run.returncode == 0, f"client chạy với feature server lỗi:\nstdout:\n{run.stdout[-1000:]}\nstderr:\n{run.stderr[-1500:]}"
    return json.loads(run.stdout.strip().splitlines()[-1])


def test_against_real_feature_server_known_zones(served):
    got = parsed(served)
    latest = served["table"].sort_values("event_timestamp").groupby("zone_id").tail(1).set_index("zone_id")
    for zone_id in served["zones"][:2]:
        row = latest.loc[zone_id]
        assert got["values"][str(zone_id)]["avg_speed_mph"] == pytest.approx(row["avg_speed_mph"], rel=1e-5)
        assert got["values"][str(zone_id)]["trip_count"] == row["trip_count"]
        assert str(zone_id) not in got["defaulted"]


def test_against_real_feature_server_unknown_zone_defaults(served):
    got = parsed(served)
    unknown = str(served["zones"][2])
    assert got["values"][unknown] == DEFAULTS
    assert got["defaulted"][unknown] == ["avg_speed_mph", "trip_count"]


def test_request_dedupes_repeated_zone(served):
    got = parsed(served)
    assert got["body"]["entities"]["zone_id"] == served["zones"]

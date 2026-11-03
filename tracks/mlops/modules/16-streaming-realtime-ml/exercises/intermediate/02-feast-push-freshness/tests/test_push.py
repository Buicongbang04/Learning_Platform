import json
import random
import shutil
import uuid

import numpy as np
import pandas as pd
import pytest
import tlcstream

import mlopskit
from testkit import Exercise

ex = Exercise(__file__)
WINDOW = 900
LIVE_WINDOW = 2
LIVE_LATENESS = 1.0
LIVE_MAX_DELAY = 4.0
UNKNOWN_ZONE = 999_999

STORE_YAML = """project: {project}
registry: data/registry.db
provider: local
online_store:
  type: sqlite
  path: data/online.db
offline_store:
  type: file
entity_key_serialization_version: 3
"""

REPLAY_SCRIPT = """
import json
import pandas as pd
from feast import FeatureStore
import push_job

fs = FeatureStore(".")
batches = json.load(open("data/batches.json"))
written = [push_job.push(fs, push_job.to_push_frame(b)) for b in batches]
zones = {zones}
online = fs.get_online_features(features=push_job.REFS, entity_rows=[{{"zone_id": z}} for z in zones]).to_dict(include_event_timestamps=True)
queries = json.load(open("data/queries.json"))
entity_df = pd.DataFrame({{"zone_id": [q[0] for q in queries], "event_timestamp": pd.to_datetime([q[1] for q in queries], unit="s", utc=True)}})
offline = fs.get_historical_features(entity_df=entity_df, features=push_job.REFS).to_df()
offline["event_timestamp"] = offline["event_timestamp"].map(lambda t: int(t.timestamp()))
view = fs.get_feature_view("zone_window")
print(json.dumps({{"written": written, "online": online, "offline": json.loads(offline.to_json(orient="records")),
                  "features": {{f.name: str(f.dtype) for f in view.features}}, "entities": view.entities,
                  "ttl": view.ttl.total_seconds(), "source": type(view.stream_source).__name__ if view.stream_source else None,
                  "source_name": view.stream_source.name if view.stream_source else None}}))
"""

LIVE_SCRIPT = """
import json, math, time
from feast import FeatureStore
import push_job

WINDOW, LATENESS = {window}, {lateness}
fs = FeatureStore(".")
plan = json.load(open("data/live.json"))
start = math.ceil(time.time() / WINDOW) * WINDOW + WINDOW
events = [dict(e, event_time=start + e["offset"]) for e in plan]
pending = sorted(events, key=lambda e: e["event_time"] + e["delay"])
open_windows, records, dropped = {{}}, [], 0
while pending or open_windows:
    now = time.time()
    while pending and pending[0]["event_time"] + pending[0]["delay"] <= now:
        e = pending.pop(0)
        w_start = int(e["event_time"] // WINDOW * WINDOW)
        if w_start + WINDOW + LATENESS <= now:
            dropped += 1
            continue
        w = open_windows.setdefault((e["zone_id"], w_start), {{"events": [], "fares": []}})
        w["events"].append(dict(e, received_at=now))
        w["fares"].append(e["fare"])
    ready = sorted(k for k in open_windows if k[1] + WINDOW + LATENESS <= now)
    if ready:
        rows = []
        for zone_id, w_start in ready:
            w = open_windows[(zone_id, w_start)]
            rows.append({{"zone_id": zone_id, "window_start": w_start, "window_end": w_start + WINDOW,
                         "trips": len(w["fares"]), "avg_fare": sum(w["fares"]) / len(w["fares"])}})
        pushed_at = time.time()
        push_job.push(fs, push_job.to_push_frame(rows))
        targets = {{}}
        for r in rows:
            targets[r["zone_id"]] = max(targets.get(r["zone_id"], 0), r["window_end"])
        seen = {{}}
        deadline = time.time() + 10
        while len(seen) < len(targets) and time.time() < deadline:
            got = fs.get_online_features(features=push_job.REFS, entity_rows=[{{"zone_id": z}} for z in targets]).to_dict(include_event_timestamps=True)
            t = time.time()
            for z, ts in zip(got["zone_id"], got["trips__ts"]):
                if z not in seen and (ts or 0) >= targets[z]:
                    seen[z] = t
        for zone_id, w_start in ready:
            for e in open_windows.pop((zone_id, w_start))["events"]:
                if zone_id in seen:
                    records.append({{"event_time": e["event_time"], "received_at": e["received_at"],
                                    "pushed_at": pushed_at, "visible_at": seen[zone_id]}})
    time.sleep(0.05)
print(json.dumps({{"records": records, "dropped": dropped}}))
"""


@pytest.fixture(scope="module")
def job():
    return ex.module("push_job.py")


@pytest.fixture(scope="module")
def fresh():
    return ex.module("freshness.py")


def batch_windows():
    trips = tlcstream.zone_trips()
    now = pd.Timestamp.now(tz="UTC").tz_localize(None)
    last = trips["pickup"].max().floor("15min") + pd.Timedelta(minutes=15)
    shift = (now - pd.Timedelta(hours=1)).floor("15min") - last
    trips = trips.assign(pickup=trips["pickup"] + shift, window=(trips["pickup"] + shift).dt.floor("15min"))
    table = trips.groupby(["zone_id", "window"]).agg(trips=("fare", "size"), avg_fare=("fare", "mean")).reset_index()
    start = (table["window"] - pd.Timestamp("1970-01-01")) // pd.Timedelta(seconds=1)
    return [
        {"zone_id": int(z), "window_start": int(s), "window_end": int(s) + WINDOW, "trips": int(t), "avg_fare": float(f)}
        for z, s, t, f in zip(table["zone_id"], start, table["trips"], table["avg_fare"])
    ]


def micro_batches(windows, seed=0):
    rng = random.Random(seed)
    ordered = sorted(windows, key=lambda w: (w["window_end"], w["zone_id"]))
    third = len(ordered) // 3
    chunks = [ordered[:third], ordered[third:2 * third], ordered[2 * third:]]
    for chunk in chunks:
        rng.shuffle(chunk)
    latest = {w["zone_id"]: w["window_end"] for w in ordered}
    stale = [w for w in ordered if w["window_end"] < latest[w["zone_id"]] - WINDOW]
    return chunks + [rng.sample(stale, 10)]


def live_plan(seed=1):
    rng = random.Random(seed)
    trips = tlcstream.zone_trips().sample(150, random_state=seed)
    plan = []
    for r in trips.itertuples():
        roll = rng.random()
        delay = rng.uniform(0, 0.5) if roll < 0.85 else rng.uniform(0.5, 1.5) if roll < 0.95 else LIVE_MAX_DELAY
        plan.append({"zone_id": int(r.zone_id), "fare": float(r.fare), "offset": rng.uniform(0, 10), "delay": delay})
    return plan


def make_repo(root):
    (root / "data").mkdir()
    (root / "feature_store.yaml").write_text(STORE_YAML.format(project=f"mlops_ex_{uuid.uuid4().hex[:8]}"), encoding="utf-8")
    shutil.copy(ex.path("features.py"), root / "features.py")
    shutil.copy(ex.path("push_job.py"), root / "push_job.py")
    empty = pd.DataFrame({
        "zone_id": pd.Series([], dtype="int64"), "trips": pd.Series([], dtype="int64"),
        "avg_fare": pd.Series([], dtype="float64"), "event_timestamp": pd.Series([], dtype="datetime64[ns, UTC]"),
    })
    empty.to_parquet(root / "data" / "zone_window.parquet")
    return mlopskit.feast_run(root, "apply")


def output(cp):
    return f"returncode={cp.returncode}\nstdout:\n{cp.stdout[-1200:]}\nstderr:\n{cp.stderr[-2000:]}"


def last_json(cp):
    assert cp.returncode == 0, output(cp)
    return json.loads(cp.stdout.strip().splitlines()[-1])


@pytest.fixture(scope="module")
def replay(tmp_path_factory):
    windows = batch_windows()
    root = tmp_path_factory.mktemp("feast-replay")
    applied = make_repo(root)
    if applied.returncode != 0:
        return {"apply": applied}
    zones = sorted({w["zone_id"] for w in windows}) + [UNKNOWN_ZONE]
    (root / "data" / "batches.json").write_text(json.dumps(micro_batches(windows)), encoding="utf-8")
    queries = [[w["zone_id"], w["window_end"] + 60] for w in windows]
    (root / "data" / "queries.json").write_text(json.dumps(queries), encoding="utf-8")
    result = mlopskit.feast_python(root, REPLAY_SCRIPT.format(zones=zones))
    return {"apply": applied, "run": result, "windows": windows, "zones": zones}


@pytest.fixture(scope="module")
def live(tmp_path_factory):
    root = tmp_path_factory.mktemp("feast-live")
    applied = make_repo(root)
    if applied.returncode != 0:
        return {"apply": applied}
    (root / "data" / "live.json").write_text(json.dumps(live_plan()), encoding="utf-8")
    script = LIVE_SCRIPT.format(window=LIVE_WINDOW, lateness=LIVE_LATENESS)
    return {"apply": applied, "run": mlopskit.feast_python(root, script, timeout=180)}


def replayed(replay):
    assert replay["apply"].returncode == 0, "feast apply lỗi:\n" + output(replay["apply"])
    return last_json(replay["run"])


def test_push_frame_shape(job):
    windows = [
        {"zone_id": 7, "window_start": 1_800, "window_end": 2_700, "trips": 3, "avg_fare": 12.345678901},
        {"zone_id": 5, "window_start": 900, "window_end": 1_800, "trips": 1, "avg_fare": 8.0},
        {"zone_id": 7, "window_start": 900, "window_end": 1_800, "trips": 2, "avg_fare": 9.5},
    ]
    frame = job.to_push_frame(windows)
    assert list(frame.columns) == ["zone_id", "trips", "avg_fare", "event_timestamp"]
    assert str(frame["zone_id"].dtype) == "int64" and str(frame["trips"].dtype) == "int64"
    assert str(frame["avg_fare"].dtype) == "float64"
    assert str(frame["event_timestamp"].dt.tz) == "UTC"
    stamps = [int(t.timestamp()) for t in frame["event_timestamp"]]
    assert stamps == sorted(stamps)
    rows = {(int(z), s): (int(t), f) for z, s, t, f in zip(frame["zone_id"], stamps, frame["trips"], frame["avg_fare"])}
    assert rows == {(7, 2_700): (3, 12.345678901), (5, 1_800): (1, 8.0), (7, 1_800): (2, 9.5)}
    assert len(job.to_push_frame([])) == 0


def test_view_contract(replay):
    got = replayed(replay)
    assert got["features"] == {"trips": "Int64", "avg_fare": "Float64"}
    assert got["entities"] == ["zone"]
    assert got["source"] == "PushSource" and got["source_name"] == "zone_window_push"
    assert 3_600 <= got["ttl"] <= 86_400


def test_online_matches_batch_latest(replay):
    got = replayed(replay)
    latest = {}
    for w in replay["windows"]:
        if w["window_end"] > latest.get(w["zone_id"], {"window_end": 0})["window_end"]:
            latest[w["zone_id"]] = w
    online = got["online"]
    for i, zone_id in enumerate(online["zone_id"]):
        if zone_id == UNKNOWN_ZONE:
            assert online["trips"][i] is None and online["avg_fare"][i] is None
            continue
        expected = latest[zone_id]
        same = (
            online["trips__ts"][i] == expected["window_end"]
            and online["trips"][i] == expected["trips"]
            and online["avg_fare"][i] == pytest.approx(expected["avg_fare"], rel=1e-9)
        )
        assert same, f"zone {zone_id}: giá trị online lệch với tính batch trên cùng dữ liệu"


def test_stale_resend_does_not_overwrite_online(replay):
    got = replayed(replay)
    zones = len(replay["zones"]) - 1
    assert got["written"][:3] == [zones, zones, zones]
    assert got["written"][3] == 0


def test_offline_point_in_time_matches_batch(replay):
    got = replayed(replay)
    expected = {(w["zone_id"], w["window_end"] + 60): w for w in replay["windows"]}
    rows = {(r["zone_id"], r["event_timestamp"]): r for r in got["offline"]}
    assert set(rows) == set(expected)
    wrong = [
        key for key, w in expected.items()
        if rows[key]["trips"] != w["trips"] or rows[key]["avg_fare"] != pytest.approx(w["avg_fare"], rel=1e-9)
    ]
    assert not wrong, f"{len(wrong)}/{len(expected)} dòng huấn luyện (point-in-time) lệch với feature cửa sổ đã đóng"


def test_freshness_from_records(fresh):
    records = [
        {"event_time": 100.0, "received_at": 100.5, "pushed_at": 103.0, "visible_at": 103.2},
        {"event_time": 101.0, "received_at": 104.0, "pushed_at": 104.5, "visible_at": 104.6},
        {"event_time": 99.0, "received_at": 99.1, "pushed_at": 103.0, "visible_at": 103.2},
        {"event_time": 102.0, "received_at": 102.2, "pushed_at": 104.5, "visible_at": 104.6},
        {"event_time": 90.0, "received_at": 100.0, "pushed_at": 103.0, "visible_at": 110.0},
    ]
    lag = np.array([3.2, 3.6, 4.2, 2.6, 20.0])
    got = fresh.freshness(records)
    assert got["n"] == 5
    assert got["p50"] == pytest.approx(float(np.percentile(lag, 50)))
    assert got["p95"] == pytest.approx(float(np.percentile(lag, 95)))
    assert fresh.freshness([]) == {"n": 0, "p50": None, "p95": None}


def test_live_freshness_p50_p95(live, fresh):
    assert live["apply"].returncode == 0, "feast apply lỗi:\n" + output(live["apply"])
    got = last_json(live["run"])
    records = got["records"]
    assert len(records) >= 100 and got["dropped"] >= 1
    lag = np.array([r["visible_at"] - r["event_time"] for r in records])
    report = fresh.freshness(records)
    assert report["n"] == len(records)
    assert report["p50"] == pytest.approx(float(np.percentile(lag, 50)), abs=1e-6)
    assert report["p95"] == pytest.approx(float(np.percentile(lag, 95)), abs=1e-6)
    budget = 2 * (LIVE_WINDOW + LIVE_LATENESS + 2.0)
    assert LIVE_LATENESS <= report["p50"] <= report["p95"] <= budget, (
        f"freshness p50={report['p50']:.2f}s p95={report['p95']:.2f}s, cần p95 <= {budget:.0f}s"
    )

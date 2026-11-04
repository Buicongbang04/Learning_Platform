"""M16: feature tốc độ 15 phút theo zone từ stream Kafka phát lại, Feast online, API đọc feature, freshness.

Đề ở capstone/milestones/m16-streaming-features.md. Dữ liệu: chuyến thật 2019-03 của `nyc-tlc` qua `mlopskit.real_month`.
"""

import json
import random
import shutil
import threading
import time
import uuid
from datetime import datetime, timezone

import joblib
import numpy as np
import pandas as pd
import pytest
import yaml
from etakit import PROJECT, need, require_file

import mlopskit

WINDOW_S, LATENESS_S, TTL_S = 900, 120, 1800
DEFAULT_SPEED_MPH = 10.1
FEATURE = "speed_15m_mph"
ROW_KEYS = {"PULocationID", "window_start", "window_end", "trips", FEATURE}
EVENT_KEYS = {"trip_id", "PULocationID", "dropoff_at", "trip_distance", "duration_s"}
REPLAY_SPEEDUP = 1800
LIVE_SPEEDUP = 60
LIVE_PROCESSING_SIM_S = 60
FRESHNESS_P95_BUDGET_S = 2 * (WINDOW_S + LATENESS_S + LIVE_PROCESSING_SIM_S)
UNKNOWN_ZONE = 264

STORE_YAML = {
    "provider": "local",
    "registry": "data/registry.db",
    "offline_store": {"type": "file"},
    "online_store": {"type": "sqlite", "path": "data/online.db"},
    "entity_key_serialization_version": 3,
}


def epoch(text: str) -> int:
    return int(datetime.strptime(text, "%Y-%m-%dT%H:%M:%S").replace(tzinfo=timezone.utc).timestamp())


def iso(ts: int) -> str:
    return datetime.fromtimestamp(ts, timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")


def real_trips(start: str, end: str, frac: float, zones: int | None = None, seed: int = 0) -> pd.DataFrame:
    """Chuyến thật 2019-03 có lúc trả khách trong [start, end), làm sạch tối thiểu, có `duration_s`."""
    path = mlopskit.real_month("nyc-tlc", "2019-03")
    columns = ["tpep_pickup_datetime", "tpep_dropoff_datetime", "PULocationID", "DOLocationID", "trip_distance"]
    df = pd.read_parquet(path, columns=columns, filters=[("tpep_dropoff_datetime", ">=", pd.Timestamp(start)),
                                                        ("tpep_dropoff_datetime", "<", pd.Timestamp(end))])
    df["duration_s"] = (df["tpep_dropoff_datetime"] - df["tpep_pickup_datetime"]).dt.total_seconds()
    keep = (df["duration_s"].between(60, 10_800) & (df["trip_distance"] > 0) & (df["trip_distance"] <= 100)
            & df["PULocationID"].between(1, 263) & df["DOLocationID"].between(1, 263))
    df = df[keep]
    if zones:
        df = df[df["PULocationID"].isin(df["PULocationID"].value_counts().index[:zones])]
    df = df.sample(frac=frac, random_state=seed).sort_values(["tpep_dropoff_datetime", "PULocationID"], kind="stable")
    return df.reset_index(drop=True)


def own_events(trips: pd.DataFrame) -> list[dict]:
    return [{"trip_id": str(i), "PULocationID": int(r.PULocationID), "dropoff_at": r.tpep_dropoff_datetime.strftime("%Y-%m-%dT%H:%M:%S"),
             "trip_distance": float(r.trip_distance), "duration_s": float(r.duration_s)} for i, r in zip(trips.index, trips.itertuples())]


def reference(stream: list) -> dict:
    """Luật cửa sổ của đề, tính lại trên đúng thứ tự đã gửi."""
    seen, mark, late, dups, invalid, windows, accepted, late_ids = set(), None, 0, 0, 0, {}, [], []
    for e in stream:
        if not (isinstance(e, dict) and EVENT_KEYS <= set(e) and isinstance(e["trip_id"], str) and e["duration_s"] > 0):
            invalid += 1
            continue
        if e["trip_id"] in seen:
            dups += 1
            continue
        seen.add(e["trip_id"])
        ts = epoch(e["dropoff_at"])
        start = ts - ts % WINDOW_S
        if mark is not None and start + WINDOW_S <= mark:
            late += 1
            late_ids.append(e["trip_id"])
            continue
        w = windows.setdefault((e["PULocationID"], start), [0, 0.0, 0.0])
        w[0] += 1
        w[1] += e["trip_distance"]
        w[2] += e["duration_s"]
        accepted.append(e)
        mark = ts - LATENESS_S if mark is None else max(mark, ts - LATENESS_S)
    speeds = {k: (v[0], v[1] / (v[2] / 3600)) for k, v in windows.items()}
    return {"windows": speeds, "late": late, "duplicates": dups, "invalid": invalid, "accepted": accepted, "late_ids": late_ids}


def bounded_shuffle(items: list, max_shift: int, seed: int) -> list:
    rng = random.Random(seed)
    keyed = [(i + rng.uniform(0, max_shift), i, item) for i, item in enumerate(items)]
    return [item for _, _, item in sorted(keyed, key=lambda k: (k[0], k[1]))]


def make_late(stream: list, count: int, seed: int) -> list:
    """Dời `count` sự kiện của 10 phút đầu xuống cuối luồng: tới khi đọc được, watermark đã qua cửa sổ của chúng."""
    rng = random.Random(seed)
    first = epoch(stream[0]["dropoff_at"])
    early = [i for i, e in enumerate(stream) if epoch(e["dropoff_at"]) < first + 600]
    moved = sorted(rng.sample(early, count), reverse=True)
    out = list(stream)
    picked = [out.pop(i) for i in moved]
    for e in picked:
        out.insert(len(out) - rng.randrange(1, 40), e)
    return out


def produce_raw(bootstrap: str, topic: str, values: list[bytes]) -> None:
    from kafka import KafkaProducer

    producer = KafkaProducer(bootstrap_servers=bootstrap)
    try:
        for value in values:
            producer.send(topic, value=value)
        producer.flush(timeout=30)
    finally:
        producer.close()


def read_back(bootstrap: str, topic: str) -> list:
    from kafka import KafkaConsumer

    consumer = KafkaConsumer(topic, bootstrap_servers=bootstrap, group_id=f"mlops-ex-check-{uuid.uuid4().hex[:8]}",
                             auto_offset_reset="earliest", enable_auto_commit=False, consumer_timeout_ms=4000)
    try:
        return [(m.timestamp / 1000, m.value) for m in consumer]
    finally:
        consumer.close()


def same_window_values(rows: list[dict], expected: dict) -> bool:
    got = {(int(r["PULocationID"]), int(r["window_start"])): r for r in rows}
    if len(got) != len(rows) or set(got) != set(expected):
        return False
    return all(got[k]["trips"] == n and got[k][FEATURE] == pytest.approx(v, rel=1e-9) and got[k]["window_end"] == k[1] + WINDOW_S
               for k, (n, v) in expected.items())


def trip_event(tid: str, zone: int, ts: int, dist: float, secs: float) -> dict:
    return {"trip_id": tid, "PULocationID": zone, "dropoff_at": iso(ts), "trip_distance": dist, "duration_s": secs}


def test_m16_window_rules(project):
    windows = need("streaming.windows", "ZoneSpeedWindows")
    t0 = epoch("2019-03-05T08:00:00")
    steps = [
        trip_event("a", 1, t0 + 10, 1.0, 600.0), trip_event("b", 2, t0 + 20, 2.0, 600.0),
        trip_event("c", 1, t0 + 1_000, 3.0, 900.0), trip_event("d", 1, t0 + 890, 1.0, 300.0),
        trip_event("a", 1, t0 + 10, 1.0, 600.0), "oops", {"trip_id": "x"}, trip_event("z", 2, t0 + 1_100, 1.0, 0.0),
        trip_event("e", 2, t0 + 1_200, 1.5, 540.0), trip_event("f", 1, t0 + 300, 9.0, 60.0),
        trip_event("g", 2, t0 + 1_920, 4.0, 1_200.0), trip_event("h", 1, t0 + 1_500, 2.0, 300.0),
    ]
    agg = windows.ZoneSpeedWindows(window_s=WINDOW_S, lateness_s=LATENESS_S)
    closed_at, rows = {}, []
    for i, step in enumerate(steps):
        for row in agg.add(step):
            closed_at[(row["PULocationID"], row["window_start"] - t0)] = i
            rows.append(row)
    tail = agg.flush()
    assert closed_at == {(1, 0): 8, (2, 0): 8, (1, 900): 10, (2, 900): 10}, (
        "cửa sổ phải đóng ngay khi watermark (event time lớn nhất trừ lateness) qua window_end, không sớm hơn, không đợi flush"
    )
    assert [(r["PULocationID"], r["window_start"] - t0) for r in tail] == [(2, 1_800)], "flush trả các cửa sổ còn mở"
    assert all(set(r) == ROW_KEYS for r in rows + tail), "mỗi dòng cửa sổ có đúng năm khoá"
    assert (agg.late, agg.duplicates, agg.invalid) == (2, 1, 3), "đếm late, duplicates, invalid theo đúng luật của đề"
    got = {(r["PULocationID"], r["window_start"] - t0): (r["trips"], r[FEATURE]) for r in rows + tail}
    expected = {(1, 0): (2, 8.0), (2, 0): (1, 12.0), (1, 900): (1, 12.0), (2, 900): (1, 10.0), (2, 1_800): (1, 12.0)}
    assert got.keys() == expected.keys() and all(got[k] == (n, pytest.approx(v)) for k, (n, v) in expected.items()), (
        "speed_15m_mph = tổng quãng đường / tổng thời gian (giờ) của các chuyến được nhận"
    )


def test_m16_replay_stream_matches_batch(project):
    events_mod = need("streaming.events", "trip_events", "SimClock", "replay")
    windows = need("streaming.windows", "consume", "zone_speed_batch")
    trips = real_trips("2019-03-05 08:00", "2019-03-05 09:00", frac=0.25)
    shuffled = trips.sample(frac=1.0, random_state=8)
    events = events_mod.trip_events(shuffled)
    assert events == own_events(shuffled.sort_values("tpep_dropoff_datetime", kind="stable")), (
        "trip_events: một dict năm khoá mỗi chuyến, trip_id là index, sắp theo lúc trả khách (giữ thứ tự gốc khi trùng)"
    )
    stream = bounded_shuffle(events, max_shift=20, seed=1)
    stream = make_late(stream, 15, seed=2)
    rng = random.Random(3)
    for _ in range(25):
        i = rng.randrange(len(stream) - 30)
        stream.insert(i + rng.randrange(1, 30), dict(stream[i]))
    malformed = [b"not json", b'{"trip_id": "m1"}', json.dumps({**events[0], "trip_id": "m2", "duration_s": -5.0}).encode()]
    expected = reference([None, None, None, *stream])
    batches = []
    with mlopskit.kafka_topic() as topic:
        bootstrap = mlopskit.require_kafka()
        produce_raw(bootstrap, topic, malformed)
        sim_start = epoch(stream[0]["dropoff_at"])
        clock = events_mod.SimClock(sim_start=sim_start, wall_start=time.time() + 0.5, speedup=REPLAY_SPEEDUP)
        sent = events_mod.replay(bootstrap, topic, stream, clock)
        elapsed = time.time() - clock.wall_start
        got = windows.consume(bootstrap, topic, on_close=batches.append, idle_ms=3000)
        echoed = read_back(bootstrap, topic)[len(malformed):]
    assert sent == len(stream)
    span = (max(epoch(e["dropoff_at"]) for e in stream) - sim_start) / REPLAY_SPEEDUP
    paced = span - 0.3 <= elapsed <= span + 10
    early = 0
    latest = None
    for stamp, raw in echoed:
        ts = epoch(json.loads(raw)["dropoff_at"])
        latest = ts if latest is None else max(latest, ts)
        early += stamp < clock.wall(latest) - 0.05
    assert paced and early == 0 and len(echoed) == len(stream), (
        "replay phải gửi theo đồng hồ mô phỏng: sự kiện gửi khi wall time tới clock.wall(event time lớn nhất đã gặp)"
    )
    assert got["consumed"] == len(stream) + len(malformed)
    assert (got["invalid"], got["duplicates"]) == (3, 25), "message hỏng và bản trùng phải được đếm và bỏ qua"
    assert got["late"] == expected["late"] and got["late"] >= 15, (
        f"late={got['late']}, cần đúng số sự kiện có window_end <= watermark lúc đọc tới"
    )
    assert same_window_values(got["windows"], expected["windows"]), "cửa sổ của stream lệch với tính lại trên cùng sự kiện"
    order = [(r["window_end"], r["PULocationID"]) for r in got["windows"]]
    assert order == sorted(order), "các cửa sổ phải xuất theo thứ tự đóng (window_end, zone)"
    assert all(batches) and [r for b in batches for r in b] == got["windows"], "on_close nhận mỗi lô cửa sổ vừa đóng, không lô rỗng"
    kept = trips[~trips.index.astype(str).isin(expected["late_ids"])]
    batch = windows.zone_speed_batch(kept)
    assert list(batch.columns) == ["PULocationID", "window_start", "window_end", "trips", FEATURE]
    assert same_window_values(batch.to_dict("records"), expected["windows"]), (
        "zone_speed_batch trên đúng các chuyến được nhận phải bằng feature của stream"
    )


def test_m16_attach_point_in_time(project):
    online = need("streaming.online", "attach_live_speed", "TTL_S")
    assert online.TTL_S == TTL_S
    t = epoch("2019-03-05T08:15:00")
    windows = pd.DataFrame({"PULocationID": [5, 5, 7], "window_start": [t - 900, t, t - 900], "window_end": [t, t + 900, t],
                            "trips": [4, 6, 3], FEATURE: [8.0, 11.0, 15.0]})
    offsets = [(5, 60), (5, 120), (5, 1_000), (5, 1_020), (5, 900 + 1_800), (5, 900 + 1_801), (7, 1_799), (UNKNOWN_ZONE, 500)]
    pickup = pd.to_datetime([iso(t + o) for _, o in offsets]).astype("datetime64[us]")
    trips = pd.DataFrame({"tpep_pickup_datetime": pickup, "PULocationID": [z for z, _ in offsets], "DOLocationID": 1,
                          "trip_distance": 1.0}, index=[40, 3, 17, 9, 21, 5, 30, 11])
    before = trips.copy()
    out = online.attach_live_speed(trips, windows)
    assert trips.equals(before), "attach_live_speed không được sửa DataFrame đầu vào"
    assert out.index.equals(trips.index) and FEATURE in out
    expected = [DEFAULT_SPEED_MPH, 8.0, 8.0, 11.0, 11.0, DEFAULT_SPEED_MPH, 15.0, DEFAULT_SPEED_MPH]
    assert out[FEATURE].tolist() == pytest.approx(expected), (
        "chuyến chỉ thấy cửa sổ đã sẵn sàng (window_end + LATENESS_S <= giờ đón) và chưa quá TTL_S; còn lại DEFAULT_SPEED_MPH"
    )


PUSH_SCRIPT = """
import json
import pandas as pd
from feast import FeatureStore
import feast_push

fs = FeatureStore(".")
batches = json.load(open("data/batches.json"))
written = [feast_push.push(fs, feast_push.to_push_frame(b)) for b in batches]
zones = json.load(open("data/zones.json"))
online = fs.get_online_features(features=feast_push.REFS, entity_rows=[{"PULocationID": z} for z in zones]).to_dict(include_event_timestamps=True)
exported = feast_push.export_online(fs, zones, "data/online.json")
view = fs.get_feature_view("zone_speed_15m")
print(json.dumps({"written": written, "online": online, "exported": exported,
                  "features": {f.name: str(f.dtype) for f in view.features}, "entities": view.entities,
                  "ttl": view.ttl.total_seconds(), "source": type(view.stream_source).__name__ if view.stream_source else None}))
"""


def feast_repo(root):
    require_file("feature_repo", "streaming.py")
    source = require_file("src", "eta", "streaming", "feast_push.py")
    shutil.copytree(PROJECT / "feature_repo", root, ignore=shutil.ignore_patterns("data", "__pycache__", "*.db"))
    (root / "data").mkdir()
    store = {"project": f"eta_m16_{uuid.uuid4().hex[:8]}", **STORE_YAML}
    (root / "feature_store.yaml").write_text(yaml.safe_dump(store, sort_keys=False), encoding="utf-8")
    shutil.copy(source, root / "feast_push.py")
    empty = pd.DataFrame({"PULocationID": pd.Series([], dtype="int64"), FEATURE: pd.Series([], dtype="float64"),
                          "trips": pd.Series([], dtype="int64"), "event_timestamp": pd.Series([], dtype="datetime64[ns, UTC]")})
    empty.to_parquet(root / "data" / "zone_speed_15m.parquet")
    return mlopskit.feast_run(root, "apply", network="none")


def output(cp) -> str:
    return f"returncode={cp.returncode}\nstdout:\n{cp.stdout[-1200:]}\nstderr:\n{cp.stderr[-2500:]}"


def batch_windows(trips: pd.DataFrame) -> list[dict]:
    ref = reference(own_events(trips))["windows"]
    return [{"PULocationID": z, "window_start": s, "window_end": s + WINDOW_S, "trips": n, FEATURE: v}
            for (z, s), (n, v) in sorted(ref.items(), key=lambda kv: (kv[0][1], kv[0][0]))]


@pytest.fixture(scope="module")
def pushed(tmp_path_factory):
    try:
        return push_replay(tmp_path_factory)
    except pytest.fail.Exception as err:
        return {"failed": str(err)}


def push_replay(tmp_path_factory) -> dict:
    trips = real_trips("2019-03-05 07:00", "2019-03-05 09:00", frac=0.2, zones=25, seed=4)
    windows = batch_windows(trips)
    root = tmp_path_factory.mktemp("m16-feast") / "repo"
    applied = feast_repo(root)
    if applied.returncode != 0:
        return {"applied": applied}
    rng = random.Random(5)
    third = len(windows) // 3
    chunks = [windows[:third], windows[third:2 * third], windows[2 * third:]]
    for chunk in chunks:
        rng.shuffle(chunk)
    latest = {}
    for w in windows:
        latest[w["PULocationID"]] = max(latest.get(w["PULocationID"], 0), w["window_end"])
    stale = [w for w in windows if w["window_end"] < latest[w["PULocationID"]]]
    batches = [*chunks, rng.sample(stale, 10)]
    zones = sorted(latest) + [UNKNOWN_ZONE]
    (root / "data" / "batches.json").write_text(json.dumps(batches), encoding="utf-8")
    (root / "data" / "zones.json").write_text(json.dumps(zones), encoding="utf-8")
    run = mlopskit.feast_python(root, PUSH_SCRIPT, network="none")
    return {"applied": applied, "run": run, "root": root, "windows": windows, "batches": batches, "trips": trips}


def pushed_result(pushed) -> dict:
    if "failed" in pushed:
        pytest.fail(pushed["failed"], pytrace=False)
    assert pushed["applied"].returncode == 0, "feast apply lỗi:\n" + output(pushed["applied"])
    assert pushed["run"].returncode == 0, output(pushed["run"])
    return json.loads(pushed["run"].stdout.strip().splitlines()[-1])


def test_m16_feast_online_matches_batch(project, pushed):
    got = pushed_result(pushed)
    assert got["features"] == {FEATURE: "Float64", "trips": "Int64"} and got["entities"] == ["pu_zone"]
    assert got["source"] == "PushSource" and got["ttl"] == TTL_S, "feature view zone_speed_15m: push source, TTL 30 phút"
    latest = {}
    for w in pushed["windows"]:
        if w["window_end"] > latest.get(w["PULocationID"], {"window_end": 0})["window_end"]:
            latest[w["PULocationID"]] = w
    online, wrong = got["online"], 0
    for i, zone in enumerate(online["PULocationID"]):
        if zone == UNKNOWN_ZONE:
            wrong += online[FEATURE][i] is not None
            continue
        w = latest[zone]
        wrong += not (online[f"{FEATURE}__ts"][i] == w["window_end"] and online["trips"][i] == w["trips"]
                      and online[FEATURE][i] == pytest.approx(w[FEATURE], rel=1e-9))
    assert wrong == 0, f"{wrong} zone có giá trị online lệch với cửa sổ mới nhất tính batch"
    expected_written = [len({w["PULocationID"] for w in b}) for b in pushed["batches"][:3]] + [0]
    assert got["written"] == expected_written, "mỗi lô chỉ ghi online cửa sổ mới nhất mỗi zone, và chỉ khi mới hơn giá trị đang có"
    snapshot = json.loads((pushed["root"] / "data" / "online.json").read_text(encoding="utf-8"))
    rows = {r["PULocationID"]: r for r in snapshot["rows"]}
    assert got["exported"] == len(rows) == len(latest), "snapshot có đúng một dòng cho mỗi zone có giá trị online"
    assert all(rows[z]["window_end"] == w["window_end"] and rows[z][FEATURE] == pytest.approx(w[FEATURE], rel=1e-12)
               for z, w in latest.items()), "snapshot phải là đúng giá trị online"


def request_at(zone: int, ts: int) -> dict:
    return {"PULocationID": int(zone), "DOLocationID": 236, "pickup_datetime": iso(ts), "trip_distance": 2.5}


def test_m16_api_reads_online_feature(project, pushed, tmp_path, monkeypatch):
    from fastapi.testclient import TestClient

    pushed_result(pushed)
    online = need("streaming.online", "attach_live_speed")
    features = need("features", "make_features", "build_features")
    train = need("train", "train")
    serve = need("serve", "app")
    windows = pd.DataFrame(pushed["windows"])
    trips = online.attach_live_speed(pushed["trips"], windows)
    X, y = features.build_features(trips)
    assert list(X.columns)[-1] == FEATURE, "có cột speed_15m_mph thì build_features thêm nó vào cuối feature"
    model = train.train(X, y, {"max_iter": 20, "random_state": 0})
    joblib.dump(model, tmp_path / "live.joblib")
    for key in ("ETA_CHALLENGER_PATH", "ETA_CANARY_WEIGHT", "ETA_SHADOW", "ETA_SPEED_TABLE", "ETA_PREDICTION_LOG"):
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setenv("ETA_MODEL_PATH", str(tmp_path / "live.joblib"))
    monkeypatch.setenv("ETA_MODEL_VERSION", "live-v1")
    monkeypatch.delenv("ETA_ONLINE_FEATURES", raising=False)
    with TestClient(serve.app) as api:
        assert api.get("/readyz").status_code == 503, "model cần speed_15m_mph mà chưa đặt ETA_ONLINE_FEATURES thì chưa sẵn sàng"
    monkeypatch.setenv("ETA_ONLINE_FEATURES", str(pushed["root"] / "data" / "online.json"))
    latest = windows.sort_values("window_end").groupby("PULocationID").tail(1).head(12)
    cases = [(z, end + LATENESS_S + 60, "fresh") for z, end in zip(latest["PULocationID"], latest["window_end"])]
    cases += [(int(latest["PULocationID"].iloc[0]), int(latest["window_end"].iloc[0]) + TTL_S + 60, "stale"),
              (UNKNOWN_ZONE, int(latest["window_end"].iloc[0]) + 300, "missing")]
    with TestClient(serve.app) as api:
        assert api.get("/readyz").status_code == 200
        replies = [api.post("/predict", json=request_at(z, ts)) for z, ts, _ in cases]
    assert all(r.status_code == 200 for r in replies), replies[0].text
    frame = pd.DataFrame([{"tpep_pickup_datetime": pd.Timestamp(request_at(z, ts)["pickup_datetime"]), "PULocationID": z,
                           "DOLocationID": 236, "trip_distance": 2.5} for z, ts, _ in cases])
    frame["tpep_pickup_datetime"] = frame["tpep_pickup_datetime"].astype("datetime64[us]")
    offline = online.attach_live_speed(frame, windows)
    expected_eta = np.maximum(model.predict(features.make_features(offline)), 60.0)
    body = [r.json() for r in replies]
    same_feature = all(b[FEATURE] == pytest.approx(v, rel=1e-9) for b, v in zip(body, offline[FEATURE]))
    same_eta = np.allclose([b["eta_s"] for b in body], expected_eta)
    assert same_feature and same_eta, "API phải dùng giá trị online giống hệt feature train (point-in-time) cho cùng zone và giờ"
    assert [b.get("speed_15m_status") for b in body] == [c[2] for c in cases], "speed_15m_status: fresh, stale hoặc missing"
    assert body[-1][FEATURE] == DEFAULT_SPEED_MPH and body[-2][FEATURE] == DEFAULT_SPEED_MPH, (
        "thiếu feature hay quá TTL thì dùng DEFAULT_SPEED_MPH, không bao giờ 0"
    )


LIVE_SCRIPT = """
import json, os, time
from feast import FeatureStore
import feast_push

fs = FeatureStore(".")
fs.get_online_features(features=feast_push.REFS, entity_rows=[{{"PULocationID": 1}}])
open("data/ready", "w").write("1")
pos, zones, visible = 0, set(), []
deadline = time.time() + {timeout}
while time.time() < deadline:
    done = os.path.exists("data/done")
    with open("data/outbox.jsonl", "rb") as fh:
        fh.seek(pos)
        chunk = fh.read()
    cut = chunk.rfind(b"\\n") + 1
    pos += cut
    rows = [json.loads(line) for line in chunk[:cut].splitlines() if line.strip()]
    if rows:
        feast_push.push(fs, feast_push.to_push_frame(rows))
        zones.update(r["PULocationID"] for r in rows)
        feast_push.export_online(fs, sorted(zones), "data/online.json")
        t = time.time()
        visible += [[r["PULocationID"], r["window_end"], t] for r in rows]
    elif done:
        break
    else:
        time.sleep(0.05)
print(json.dumps({{"visible": visible}}))
"""


def test_m16_live_freshness(project, tmp_path):
    events_mod = need("streaming.events", "trip_events", "SimClock", "replay")
    windows = need("streaming.windows", "consume")
    fresh = need("streaming.freshness", "freshness")
    bootstrap = mlopskit.require_kafka()
    mlopskit.feast_image()
    trips = real_trips("2019-03-05 08:00", "2019-03-05 08:45", frac=0.3, zones=10, seed=6)
    stream = make_late(events_mod.trip_events(trips), 5, seed=7)
    expected = reference(stream)
    root = tmp_path / "repo"
    applied = feast_repo(root)
    assert applied.returncode == 0, "feast apply lỗi:\n" + output(applied)
    outbox = root / "data" / "outbox.jsonl"
    outbox.touch()
    span = (max(epoch(e["dropoff_at"]) for e in stream) - epoch(stream[0]["dropoff_at"])) / LIVE_SPEEDUP
    holder: dict = {}

    def run_push():
        try:
            holder["run"] = mlopskit.feast_python(root, LIVE_SCRIPT.format(timeout=int(span) + 120), network="none",
                                                  timeout=int(span) + 180)
        except BaseException as err:
            holder["error"] = err

    def on_close(rows):
        with outbox.open("a", encoding="utf-8") as fh:
            fh.write("".join(json.dumps(r) + "\n" for r in rows))

    def run_consume():
        try:
            holder["consumed"] = windows.consume(bootstrap, topic, on_close=on_close, idle_ms=3000)
        except BaseException as err:
            holder["error"] = err

    pusher = threading.Thread(target=run_push, daemon=True)
    pusher.start()
    deadline = time.time() + 120
    while not (root / "data" / "ready").exists() and pusher.is_alive() and time.time() < deadline:
        time.sleep(0.2)
    try:
        assert (root / "data" / "ready").exists(), f"container Feast chưa sẵn sàng: {holder}"
        with mlopskit.kafka_topic() as topic:
            consumer = threading.Thread(target=run_consume, daemon=True)
            consumer.start()
            clock = events_mod.SimClock(sim_start=epoch(stream[0]["dropoff_at"]), wall_start=time.time() + 1.0,
                                        speedup=LIVE_SPEEDUP)
            events_mod.replay(bootstrap, topic, stream, clock)
            consumer.join(timeout=60)
    finally:
        (root / "data" / "done").touch()
        pusher.join(timeout=span + 200)
    if "error" in holder:
        raise holder["error"]
    assert "consumed" in holder and "run" in holder, "consumer hoặc container push chưa kết thúc"
    assert holder["run"].returncode == 0, output(holder["run"])
    got = holder["consumed"]
    assert got["late"] == expected["late"] >= 5, "sự kiện tới sau khi watermark qua cửa sổ của nó bị loại và đếm"
    seen = {(z, end): t for z, end, t in json.loads(holder["run"].stdout.strip().splitlines()[-1])["visible"]}
    records = []
    for e in expected["accepted"]:
        ts = epoch(e["dropoff_at"])
        key = (e["PULocationID"], ts - ts % WINDOW_S + WINDOW_S)
        if key in seen:
            records.append({"event_time": ts, "visible_at": clock.sim(seen[key])})
    assert len(records) >= 0.95 * len(expected["accepted"]), f"chỉ {len(records)}/{len(expected['accepted'])} sự kiện có feature online"
    report = fresh.freshness(records)
    lag = np.array([r["visible_at"] - r["event_time"] for r in records])
    assert report["n"] == len(records)
    assert report["p50"] == pytest.approx(float(np.percentile(lag, 50)), abs=1e-6)
    assert report["p95"] == pytest.approx(float(np.percentile(lag, 95)), abs=1e-6)
    assert LATENESS_S <= report["p50"] <= report["p95"] <= FRESHNESS_P95_BUDGET_S, (
        f"freshness p50={report['p50']:.0f}s p95={report['p95']:.0f}s (giây mô phỏng), cần p95 <= {FRESHNESS_P95_BUDGET_S}s"
    )

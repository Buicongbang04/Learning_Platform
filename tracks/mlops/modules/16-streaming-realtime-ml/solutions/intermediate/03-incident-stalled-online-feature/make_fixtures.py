"""Sinh lại fixture của bài sự cố từ TLC 2019-03: uv run python tracks/mlops/modules/16-streaming-realtime-ml/solutions/intermediate/03-incident-stalled-online-feature/make_fixtures.py

Log phát lại chuyến taxi thật; trong 10 phút 08:50–09:00 (giờ nhận) gateway mới gửi 40% sự kiện với `pickup_at` có offset +07:00.
Kết quả mong đợi tính bằng bản tham chiếu độc lập dưới đây (dùng thời điểm thật, không parse chuỗi).
"""

import json
import random
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
MODULE = HERE.parents[2]
FIXTURES = MODULE / "exercises" / "intermediate" / HERE.name / "tests" / "fixtures"
WINDOW, HOLD, AHEAD = 900, 180, 300
ROLLOUT_FROM = datetime(2019, 3, 5, 8, 50, tzinfo=timezone.utc)
ROLLOUT_TO = datetime(2019, 3, 5, 9, 0, tzinfo=timezone.utc)
GATEWAY_B = timezone(timedelta(hours=7))


def stamp(moment, tz=timezone.utc):
    return moment.astimezone(tz).isoformat(timespec="seconds").replace("+00:00", "Z")


def build_log(seed=0):
    sys.path[:0] = [str(MODULE.parents[3]), str(MODULE)]
    import tlcstream

    rng = random.Random(seed)
    log = []
    for r in tlcstream.zone_trips().itertuples():
        pickup = r.pickup.to_pydatetime().replace(tzinfo=timezone.utc)
        delay = 600.0 if rng.random() < 0.02 else min(rng.expovariate(1 / 20), 150)
        received = pickup + timedelta(seconds=delay)
        via_b = ROLLOUT_FROM <= received < ROLLOUT_TO and rng.random() < 0.4
        log.append({"event_id": r.event_id, "zone_id": int(r.zone_id), "fare": float(r.fare),
                    "pickup_at": stamp(pickup, GATEWAY_B if via_b else timezone.utc), "received_at": stamp(received),
                    "_instant": pickup, "_received": received})
    for item in rng.sample(log, 25):
        log.append(dict(item, _received=item["_received"] + timedelta(seconds=30)))
    log.sort(key=lambda e: e["_received"])
    return log


def reference(log):
    seen, mark = set(), None
    stats = {"accepted": 0, "skipped": 0, "repeated": 0, "rejected": 0}
    windows, emitted, latest = {}, [], {}

    def close(limit):
        for key in sorted((k for k in windows if k[1] + WINDOW <= limit), key=lambda k: (k[1], k[0])):
            trips, total = windows.pop(key)
            row = {"zone_id": key[0], "window_start": key[1], "window_end": key[1] + WINDOW, "trips": trips, "avg_fare": total / trips}
            emitted.append(row)
            if key[0] not in latest or row["window_end"] >= latest[key[0]]["window_end"]:
                latest[key[0]] = row

    for e in log:
        if e["event_id"] in seen:
            stats["repeated"] += 1
            continue
        seen.add(e["event_id"])
        ts = int(e["_instant"].timestamp())
        if ts > int(e["_received"].timestamp()) + AHEAD:
            stats["rejected"] += 1
            continue
        start = ts - ts % WINDOW
        if mark is not None and start + WINDOW <= mark:
            stats["skipped"] += 1
            continue
        stats["accepted"] += 1
        w = windows.setdefault((e["zone_id"], start), [0, 0.0])
        w[0] += 1
        w[1] += e["fare"]
        mark = ts - HOLD if mark is None else max(mark, ts - HOLD)
        close(mark)
    snapshot = {str(z): dict(r) for z, r in latest.items()}
    close(float("inf"))
    return {"rows": emitted, "snapshot": snapshot, "stats": stats}


def with_bad_device(log):
    broken = [dict(e) for e in log]
    at = len(broken) // 3
    victim = dict(broken[at], event_id="trip-x00001")
    victim["_instant"] = victim["_received"] + timedelta(days=3)
    victim["pickup_at"] = stamp(victim["_instant"])
    broken.insert(at + 1, victim)
    return broken, at + 1, victim


def public(e):
    return {k: v for k, v in e.items() if not k.startswith("_")}


def main():
    log = build_log()
    FIXTURES.mkdir(parents=True, exist_ok=True)
    with (FIXTURES / "events.jsonl").open("w", encoding="utf-8") as fh:
        for e in log:
            fh.write(json.dumps(public(e)) + "\n")
    broken, position, victim = with_bad_device(log)
    expected = {"main": reference(log), "extra": dict(reference(broken), position=position, event=public(victim))}
    (FIXTURES / "expected.json").write_text(json.dumps(expected, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()

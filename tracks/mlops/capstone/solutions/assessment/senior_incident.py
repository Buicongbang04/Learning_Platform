"""Sinh sự cố dựng sẵn của M18 từ ngày thật 2019-11-14 của `nyc-tlc`. Đáp án của bài đánh giá: đừng mở khi đang làm M18.

Nền tảng ETA phục vụ ba market (borough đón khách của TLC: manhattan, queens, brooklyn), mỗi market một deployment. Mỗi
chuyến thật của ngày là một request ETA lúc đón khách; nhãn là thời gian chuyến thật, về lúc trả khách.

- Cả ngày, market nào cũng dùng model `v41`: trung vị thời gian chuyến theo cặp zone và giờ của tháng 2019-10.
- 13:05 (`mdl-731`): queens lên `v42` ngay 100% traffic, bỏ canary. `v42` nhân dự đoán của `v41` với tỉ số tốc độ điển hình
  của zone đón trên tốc độ 15 phút gần nhất (feature view `zone_speed_15m`, materialize mỗi phút theo market).
- 15:20: consumer của partition queens chết vì một message hỏng và không ai biết (không có alert freshness). Feature online
  giữ giá trị cuối tới hết TTL 30 phút, rồi trả null; `v42` điền null bằng 0 (`fillna(0)`), chặn mẫu số ở 1 mph, nên tỉ số
  chạm trần 2.5 và ETA ở queens dài gấp 2.5 lần `v41` từ 15:50.
- 16:40 restart consumer không có tác dụng (chết lại ở cùng offset). 17:00 rollback queens về `v41` (`mdl-733`) chấm dứt tác
  động. Alert chất lượng có sẵn chỉ bắn lúc 17:18, sau rollback, vì nhãn về lúc trả khách; người phát hiện là đội support
  (16:21). 18:27 bỏ qua offset hỏng, feature tươi lại.
- Nhiễu có chủ ý: `cfg-514` bật debug log ở queens lúc 14:31 (thay đổi gần nhất trước tác động trên service queens),
  `cfg-515` tăng timeout ở brooklyn lúc 15:48, partition brooklyn kẹt 23 phút buổi sáng (cũ hơn 15 phút trong 8 phút, không
  ảnh hưởng chất lượng), một alert latency ngắn ở manhattan.
"""

from pathlib import Path

import numpy as np
import pandas as pd

DAY = "2019-11-14"
SOURCE = ("nyc-tlc", "2019-11")
REFERENCE = ("nyc-tlc", "2019-10")
LOOKUP = "taxi_zone_lookup.csv"
LOOKUP_SHA256 = "1a99e105092230f8620f301edcca7f80d3080642ff404d28ed957d3fa222c8ed"
MARKETS = {"Manhattan": "manhattan", "Queens": "queens", "Brooklyn": "brooklyn"}
FEATURE_VIEW = "zone_speed_15m"
AFFECTED = ["queens"]
CAUSES = ("stale_feature", "unsafe_default", "skipped_canary", "missing_freshness_alert")
TRIGGER = "mdl-731"
DECISION = "rollback"
ROLES = {"incident_commander": "quynh", "comms": "yen", "ops": "phuc"}
PEOPLE = ("nhung", "hieu", "diep", "phuc", "quynh", "yen", "trinh")
DETECTED = "16:21"
ROLLOUT, STALL, TTL_MIN, RESTART, ROLLBACK, FIX = "13:05", "15:20", 30, "16:40", "17:00", "18:27"
BROOKLYN_STALL = ("09:58", "10:21")
KEEP = ["tpep_pickup_datetime", "tpep_dropoff_datetime", "PULocationID", "DOLocationID", "trip_distance"]
RATIO_CLIP = (0.6, 2.5)
MISSING_SPEED = 0.0
MIN_SPEED_TRIPS = 5
GOOD_REL, GOOD_ABS_S = 0.3, 300
ALERT_RATIO, ALERT_FOR_MIN = 0.5, 10


def minute_of(hhmm: str) -> int:
    hours, minutes = hhmm.split(":")
    return int(hours) * 60 + int(minutes)


def hhmm(minute: int) -> str:
    return f"{minute // 60:02d}:{minute % 60:02d}"


def _trips(path: Path, start: pd.Timestamp, end: pd.Timestamp) -> pd.DataFrame:
    frame = pd.read_parquet(path, columns=KEEP)
    frame = frame[(frame["tpep_pickup_datetime"] >= start) & (frame["tpep_pickup_datetime"] < end)].copy()
    frame["duration_s"] = (frame["tpep_dropoff_datetime"] - frame["tpep_pickup_datetime"]).dt.total_seconds()
    keep = frame["duration_s"].between(60, 10_800) & (frame["trip_distance"] > 0) & (frame["trip_distance"] < 100)
    return frame[keep].reset_index(drop=True)


def _speed(frame: pd.DataFrame) -> float:
    return float(frame["trip_distance"].sum() / (frame["duration_s"].sum() / 3600))


def _reference_tables(reference: pd.DataFrame):
    reference = reference.assign(hour=reference["tpep_pickup_datetime"].dt.hour)
    pair_hour = reference.groupby(["PULocationID", "DOLocationID", "hour"])["duration_s"].median().rename("pair_hour")
    pair = reference.groupby(["PULocationID", "DOLocationID"])["duration_s"].median().rename("pair")
    zone = reference.groupby("PULocationID")["duration_s"].median().rename("zone")
    sums = reference.groupby(["PULocationID", "hour"])[["trip_distance", "duration_s"]].sum()
    typical = (sums["trip_distance"] / (sums["duration_s"] / 3600)).rename("typical_speed")
    return pair_hour, pair, zone, typical, float(reference["duration_s"].median()), _speed(reference)


def _live_speed(day: pd.DataFrame, start: pd.Timestamp) -> pd.DataFrame:
    drop_minute = ((day["tpep_dropoff_datetime"] - start).dt.total_seconds() // 60).astype(int)
    done = day.assign(minute=drop_minute)
    done = done[(done["minute"] >= 0) & (done["minute"] < 1440)]
    grid = pd.MultiIndex.from_product([sorted(day["PULocationID"].unique()), range(1440)], names=["PULocationID", "minute"])
    sums = done.groupby(["PULocationID", "minute"]).agg(distance=("trip_distance", "sum"), seconds=("duration_s", "sum"),
                                                        trips=("duration_s", "size"))
    sums = sums.reindex(grid, fill_value=0).reset_index()
    rolled = sums.groupby("PULocationID")[["distance", "seconds", "trips"]].transform(
        lambda col: col.rolling(15, min_periods=1).sum().shift(1, fill_value=0))
    speed = np.where(rolled["trips"] >= MIN_SPEED_TRIPS, rolled["distance"] / (rolled["seconds"].clip(lower=1) / 3600), np.nan)
    return pd.DataFrame({"PULocationID": sums["PULocationID"], "feature_minute": sums["minute"], "live_speed": speed})


def predictions(day: pd.DataFrame, reference: pd.DataFrame, start: pd.Timestamp) -> pd.DataFrame:
    pair_hour, pair, zone, typical, overall, train_speed = _reference_tables(reference)
    frame = day.assign(hour=day["tpep_pickup_datetime"].dt.hour)
    frame = frame.join(pair_hour, on=["PULocationID", "DOLocationID", "hour"]).join(pair, on=["PULocationID", "DOLocationID"])
    frame = frame.join(zone, on="PULocationID").join(typical, on=["PULocationID", "hour"])
    v41 = frame["pair_hour"].fillna(frame["pair"]).fillna(frame["zone"]).fillna(overall)
    minute = ((frame["tpep_pickup_datetime"] - start).dt.total_seconds() // 60).astype(int)
    stall, ttl_end = minute_of(STALL), minute_of(STALL) + TTL_MIN
    frame["feature_minute"] = np.where(minute >= stall, stall, minute)
    frame = frame.merge(_live_speed(day, start), on=["PULocationID", "feature_minute"], how="left")
    typical_speed = frame["typical_speed"].fillna(train_speed)
    served = frame["live_speed"].fillna(typical_speed)
    served = served.where(minute < ttl_end, MISSING_SPEED)
    v42 = v41 * (typical_speed / served.clip(lower=1.0)).clip(*RATIO_CLIP)
    uses_v42 = (frame["market"] == AFFECTED[0]) & (minute >= minute_of(ROLLOUT)) & (minute < minute_of(ROLLBACK))
    frame["model_version"] = np.where(uses_v42, "v42", "v41")
    frame["eta_s"] = np.where(uses_v42, v42, v41).round().astype("int64")
    return frame


def freshness() -> pd.DataFrame:
    rows = []
    stall, fix = minute_of(STALL), minute_of(FIX)
    b_from, b_to = (minute_of(t) for t in BROOKLYN_STALL)
    for index, market in enumerate(MARKETS.values()):
        for minute in range(1440):
            age = 20 + (minute * 37 + index * 11) % 45
            if market == AFFECTED[0] and stall <= minute < fix:
                age = (minute - stall) * 60 + 20
            if market == "brooklyn" and b_from <= minute < b_to:
                age = (minute - b_from) * 60 + 20
            rows.append((hhmm(minute), market, FEATURE_VIEW, age))
    return pd.DataFrame(rows, columns=["minute", "market", "feature_view", "age_s"])


def _quality_alert(labels: pd.DataFrame, start: pd.Timestamp) -> list[tuple[str, int, int]]:
    arrived = ((labels["label_ts"] - start).dt.total_seconds() // 60).astype(int)
    bad = ((labels["eta_s"] - labels["duration_s"]).abs() > GOOD_REL * labels["duration_s"] + GOOD_ABS_S).astype(int)
    events = []
    for market in MARKETS.values():
        mask = labels["market"] == market
        counts = pd.DataFrame({"m": arrived[mask], "bad": bad[mask]}).groupby("m")["bad"].agg(["sum", "size"])
        counts = counts.reindex(range(1440 + 240), fill_value=0)
        ratio = {w: counts["sum"].rolling(w, min_periods=1).sum() / counts["size"].rolling(w, min_periods=1).sum().clip(lower=1)
                 for w in (60, 5)}
        hot = ((ratio[60] > ALERT_RATIO) & (ratio[5] > ALERT_RATIO)).to_numpy()
        firing, run = None, 0
        for minute in range(1440):
            run = run + 1 if hot[minute] else 0
            if firing is None and run >= ALERT_FOR_MIN:
                firing = minute
            elif firing is not None and not hot[minute]:
                events.append((market, firing, minute))
                firing = None
        if firing is not None:
            events.append((market, firing, 1439))
    return events


def _write_logs(out: Path, alert_events) -> None:
    fire = {market: (on, off) for market, on, off in alert_events}
    if set(fire) != set(AFFECTED) or not minute_of(ROLLBACK) < fire[AFFECTED[0]][0] < minute_of(FIX):
        raise RuntimeError(f"Dữ liệu nguồn đổi: alert chất lượng {fire} không khớp kịch bản")
    on, off = fire[AFFECTED[0]]
    alert_lines = [
        (minute_of("08:41"), "firing  ", "ETALatencyP95High market=manhattan severity=warning"),
        (minute_of("08:49"), "resolved", "ETALatencyP95High market=manhattan severity=warning"),
        (minute_of("11:03"), "firing  ", "DiskSpaceLow service=batch-scoring severity=warning"),
        (minute_of("12:30"), "resolved", "DiskSpaceLow service=batch-scoring severity=warning"),
        (on, "firing  ", "ETAQualityFastBurn market=queens severity=critical"),
        (off, "resolved", "ETAQualityFastBurn market=queens severity=critical"),
    ]
    (out / "alerts.log").write_text("".join(f"{DAY}T{hhmm(m)}:00 {state} {text}\n" for m, state, text in sorted(alert_lines)),
                                    encoding="utf-8")
    deploys = [
        ("09:12:40", "cfg-512", "eta-manhattan", "tăng replicas 6 -> 8", "ci"),
        ("13:05:11", "mdl-731", "eta-queens", "model eta v41 -> v42 (100% traffic, bỏ canary: cửa sổ hotfix)", "ci"),
        ("14:31:02", "cfg-514", "eta-queens", "log level info -> debug cho /predict", "ci"),
        ("15:48:27", "cfg-515", "eta-brooklyn", "tăng timeout gọi feature store từ 300ms lên 400ms", "ci"),
        ("16:59:52", "mdl-733", "eta-queens", "model eta v42 -> v41", "manual"),
        ("18:26:44", "ops-77", "feature-pipeline", "consumer zone_speed_15m partition queens: bỏ qua offset 88123017", "manual"),
    ]
    (out / "deploys.log").write_text("".join(f'{DAY}T{t} deploy_id={d} service={s} change="{c}" by={b}\n'
                                             for t, d, s, c, b in deploys), encoding="utf-8")
    detected = minute_of(DETECTED)
    chat = [
        (minute_of("09:59"), "nhung", "[feature-pipeline] partition brooklyn của zone_speed_15m lag, đang xem"),
        (minute_of("10:22"), "nhung", "brooklyn hết lag, consumer tự hồi sau rebalance"),
        (minute_of("13:04"), "hieu", "đẩy v42 cho queens luôn 100%, cửa sổ hotfix chiều nay, canary làm sau"),
        (minute_of("14:30"), "hieu", "bật debug log /predict ở queens để soi feature mới"),
        (minute_of("15:47"), "diep", "brooklyn tăng timeout feature store lên 400ms (cfg-515), p99 feature store hơi cao"),
        (detected, "support-desk", "nhiều tài xế ở JFK và LGA báo app hiện ETA dài gấp hai, gấp ba thực tế, khách huỷ chuyến"),
        (detected + 2, "phuc", "mình on-call, support vừa chuyển. đang xem queens, dashboard chất lượng vẫn xanh vì nhãn chưa về"),
        (detected + 3, "phuc", "@quynh làm IC giúp mình nhé, mình cần tay để debug"),
        (detected + 4, "quynh", "nhận vai trò IC. @yen nhận comms: cập nhật kênh #ops-eta và đội support mỗi 20 phút"),
        (detected + 4, "yen", "nhận comms"),
        (detected + 6, "phuc", "nghi cfg-515 lúc 15:48, timeout feature store đổi đúng lúc ETA hỏng"),
        (detected + 8, "quynh", "cfg-515 chỉ ở brooklyn. phuc xem từng market trước khi kết luận"),
        (detected + 11, "trinh", "consumer partition queens của zone_speed_15m chết từ 15:20, lỗi deserialize một message"),
        (detected + 13, "trinh", "online store đặt TTL 30 phút cho zone_speed_15m, quá TTL thì trả null"),
        (minute_of(RESTART) - 1, "quynh", "thử restart consumer queens, phuc làm"),
        (minute_of(RESTART), "phuc", "đã restart consumer queens"),
        (minute_of(RESTART) + 3, "trinh", "consumer chết lại ở cùng offset, feature vẫn không cập nhật"),
        (minute_of(ROLLBACK) - 4, "quynh", "quyết định: rollback queens về v41, v41 không đọc zone_speed_15m. phuc chạy"),
        (minute_of(ROLLBACK), "phuc", "đã chạy mdl-733, queens về v41"),
        (on, "alertbot", "FIRING ETAQualityFastBurn market=queens severity=critical"),
        (on + 1, "quynh", "alert chất lượng tới sau rollback, nhãn về trễ. vẫn giữ sự cố mở tới khi feature tươi lại"),
        (on + 8, "phuc", "ETA queens trên request mới bình thường lại, chờ nhãn để xác nhận"),
        (minute_of(FIX) - 1, "trinh", "bỏ qua offset hỏng (ops-77), giữ message để phân tích"),
        (minute_of(FIX) + 3, "trinh", "zone_speed_15m queens tươi lại"),
        (max(off, minute_of(FIX) + 3) + 1, "quynh", "alert đã resolved, feature tươi. đóng sự cố, postmortem trong 5 ngày làm việc"),
    ]
    if not all(a[0] <= b[0] for a, b in zip(chat, chat[1:])):
        raise RuntimeError("Dữ liệu nguồn đổi: thứ tự kênh chat không còn khớp kịch bản")
    (out / "chat.log").write_text("".join(f"{hhmm(m)} @{who}: {text}\n" for m, who, text in chat), encoding="utf-8")


def build(source: Path, reference: Path, lookup: Path, out: Path) -> Path:
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    start = pd.Timestamp(DAY)
    month = pd.Timestamp(f"{REFERENCE[1]}-01")
    reference_trips = _trips(reference, month, month + pd.offsets.MonthBegin(1))
    zones = pd.read_csv(lookup)
    borough = dict(zip(zones["LocationID"], zones["Borough"].map(MARKETS)))
    day = _trips(source, start, start + pd.Timedelta(days=1))
    day["market"] = day["PULocationID"].map(borough)
    day = day[day["market"].notna()]
    day = day.sort_values(KEEP, kind="stable").reset_index(drop=True)
    frame = predictions(day, reference_trips, start)
    frame["request_id"] = np.arange(1, len(frame) + 1, dtype="int64")
    logged = frame.rename(columns={"tpep_pickup_datetime": "ts"})[
        ["request_id", "ts", "market", "model_version", "PULocationID", "DOLocationID", "trip_distance", "eta_s"]]
    labels = pd.DataFrame({"request_id": frame["request_id"], "label_ts": frame["tpep_dropoff_datetime"],
                           "duration_s": frame["duration_s"].round().astype("int64")})
    for name, table in (("predictions.parquet", logged), ("labels.parquet", labels)):
        tmp = out / f"{name}.tmp"
        table.to_parquet(tmp, index=False)
        tmp.replace(out / name)
    freshness().to_csv(out / "freshness.csv", index=False)
    joined = labels.assign(market=frame["market"], eta_s=frame["eta_s"])
    _write_logs(out, _quality_alert(joined, start))
    return out

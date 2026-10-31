"""Fixture `<city>_<day>.json`: response thật của Open-Meteo Historical Weather API (CC BY 4.0) cho từng thành phố,
từng ngày 20–21/10/2026, tải ngày 30/10/2026. Test không gọi mạng."""
import hashlib
import json
import logging
import re
import sqlite3

import pytest

from testkit import Exercise

ex = Exercise(__file__)
DAY = "2026-10-20"
HEADINGS = ["## Mục đích và người dùng", "## Lịch chạy và ngày dữ liệu", "## Chạy lại và backfill",
            "## Giám sát và cảnh báo", "## Dữ liệu thô và metadata", "## Giới hạn và bàn giao"]


@pytest.fixture(scope="module")
def pl():
    return ex.module("pipeline.py")


def fixture_body(city, day):
    return (ex.fixtures / f"{city}_{day}.json").read_bytes()


class FakeApi:
    """Trả response đã lưu theo (vĩ độ, ngày); `broken` là các thành phố trả lỗi mạng."""

    def __init__(self, pl, broken=(), patch=None):
        self.by_lat = {lat: city for city, (lat, _) in pl.CITIES.items()}
        self.broken, self.patch, self.calls = set(broken), patch or {}, []

    def __call__(self, url, params):
        self.calls.append((url, params))
        city = self.by_lat[params["latitude"]]
        if city in self.broken:
            raise ConnectionError(f"timeout khi gọi {city}")
        body = fixture_body(city, params["start_date"])
        if city in self.patch:
            payload = json.loads(body)
            payload["daily"].update(self.patch[city])
            body = json.dumps(payload).encode()
        return body


def rows(db, sql, *args):
    conn = sqlite3.connect(db)
    try:
        return conn.execute(sql, args).fetchall()
    finally:
        conn.close()


def test_save_raw_writes_body_and_metadata(pl, tmp_path):
    body = fixture_body("hcmc", DAY)
    params = pl.build_params(10.82, 106.63, DAY)
    path = pl.save_raw(tmp_path, DAY, "hcmc", body, pl.URL, params, "2026-10-30T00:00:00+00:00")
    assert path == tmp_path / DAY / "hcmc.json"
    assert path.read_bytes() == body
    meta = json.loads((tmp_path / DAY / "hcmc.meta.json").read_text())
    assert meta == {"url": pl.URL, "params": params, "fetched_at": "2026-10-30T00:00:00+00:00",
                    "sha256": hashlib.sha256(body).hexdigest(), "n_bytes": len(body)}
    assert sorted(p.name for p in (tmp_path / DAY).iterdir()) == ["hcmc.json", "hcmc.meta.json"]


def test_parse_day(pl):
    assert pl.parse_day(fixture_body("hcmc", DAY), "hcmc", DAY) == {
        "city": "hcmc", "date": DAY, "tmax": 32.2, "tmin": 24.3, "precip_mm": 0.7}
    with pytest.raises(ValueError):
        pl.parse_day(fixture_body("hcmc", DAY), "hcmc", "2026-10-21")
    error = b'{"reason":"Parameter \'start_date\' is out of allowed range","error":true}'
    with pytest.raises(ValueError):
        pl.parse_day(error, "hcmc", DAY)


def test_run_day_success(pl, tmp_path):
    db, raw = tmp_path / "w.sqlite", tmp_path / "raw"
    api = FakeApi(pl)
    out = pl.run_day(DAY, api, raw, db, now=lambda: "T1")
    assert out == {"day": DAY, "status": "success", "n_rows": 3, "error": None}
    assert len(api.calls) == 3
    assert rows(db, "SELECT city, date, tmax, tmin, precip_mm FROM weather_daily ORDER BY city") == [
        ("danang", DAY, 30.3, 24.6, 1.1), ("hanoi", DAY, 32.1, 24.8, 0.0), ("hcmc", DAY, 32.2, 24.3, 0.7)]
    assert rows(db, "SELECT day, status, n_rows, error FROM run_log") == [(DAY, "success", 3, None)]
    assert len(list((raw / DAY).glob("*.meta.json"))) == 3
    source = rows(db, "SELECT source_file FROM weather_daily WHERE city = 'hcmc'")[0][0]
    assert source.endswith("hcmc.json")


def test_run_day_is_idempotent_and_takes_revisions(pl, tmp_path):
    db, raw = tmp_path / "w.sqlite", tmp_path / "raw"
    pl.run_day(DAY, FakeApi(pl), raw, db, now=lambda: "T1")
    # nguồn sửa số của ngày gần đây: chạy lại phải cập nhật, không thêm dòng
    pl.run_day(DAY, FakeApi(pl, patch={"hcmc": {"temperature_2m_max": [33.0]}}), raw, db, now=lambda: "T2")
    assert rows(db, "SELECT COUNT(*) FROM weather_daily") == [(3,)]
    assert rows(db, "SELECT tmax, loaded_at FROM weather_daily WHERE city = 'hcmc'") == [(33.0, "T2")]
    assert rows(db, "SELECT status FROM run_log ORDER BY run_id") == [("success",), ("success",)]


def test_run_day_failure_writes_nothing_and_does_not_raise(pl, tmp_path, caplog):
    db, raw = tmp_path / "w.sqlite", tmp_path / "raw"
    with caplog.at_level(logging.INFO, logger="weather_pipeline"):
        out = pl.run_day(DAY, FakeApi(pl, broken={"danang"}), raw, db, now=lambda: "T1")
    assert out["status"] == "failed" and out["n_rows"] == 0 and "danang" in out["error"]
    assert rows(db, "SELECT COUNT(*) FROM weather_daily") == [(0,)]
    (status, error), = rows(db, "SELECT status, error FROM run_log")
    assert status == "failed" and "danang" in error
    assert any(r.levelno == logging.ERROR and DAY in r.getMessage() for r in caplog.records)
    # sửa xong nguồn, chạy lại cùng ngày: đủ 3 dòng
    assert pl.run_day(DAY, FakeApi(pl), raw, db, now=lambda: "T2")["status"] == "success"
    assert rows(db, "SELECT COUNT(*) FROM weather_daily") == [(3,)]


def test_run_day_logs_info(pl, tmp_path, caplog):
    with caplog.at_level(logging.INFO, logger="weather_pipeline"):
        pl.run_day(DAY, FakeApi(pl), tmp_path / "raw", tmp_path / "w.sqlite", now=lambda: "T1")
    messages = [r.getMessage() for r in caplog.records if r.levelno == logging.INFO]
    assert any(DAY in m and "success" in m and "3" in m for m in messages)


def test_missing_days(pl, tmp_path):
    db, raw = tmp_path / "w.sqlite", tmp_path / "raw"
    pl.run_day(DAY, FakeApi(pl), raw, db, now=lambda: "T1")
    assert pl.missing_days(db, "2026-10-19", "2026-10-21") == ["2026-10-19", "2026-10-21"]
    # ngày chỉ có 2/3 thành phố vẫn là ngày thiếu
    conn = sqlite3.connect(db)
    with conn:
        conn.execute("INSERT INTO weather_daily VALUES ('hcmc', '2026-10-21', 32, 24.5, 10.1, 'x', 'T')")
        conn.execute("INSERT INTO weather_daily VALUES ('hanoi', '2026-10-21', 32, 24.7, 1.0, 'x', 'T')")
    conn.close()
    assert pl.missing_days(db, "2026-10-20", "2026-10-21") == ["2026-10-21"]
    pl.run_day("2026-10-21", FakeApi(pl), raw, db, now=lambda: "T2")
    assert pl.missing_days(db, "2026-10-19", "2026-10-21") == ["2026-10-19"]


@pytest.mark.parametrize("n", ["0", "-3"])
def test_last_must_be_positive(pl, n, capsys):
    with pytest.raises(SystemExit) as e:
        pl.main(["--last", n])
    assert e.value.code == 2
    assert "--last" in capsys.readouterr().err


def test_runbook_filled():
    text = ex.read("RUNBOOK.md")
    assert "TODO" not in text, "RUNBOOK.md còn TODO"
    positions = [text.find(h) for h in HEADINGS]
    assert all(p >= 0 for p in positions), "RUNBOOK.md thiếu mục bắt buộc"
    assert positions == sorted(positions), "Các mục phải theo đúng thứ tự"
    words = len(re.findall(r"\w+", text))
    assert 250 <= words <= 1200, f"RUNBOOK.md có {words} từ, cần 250-1200"

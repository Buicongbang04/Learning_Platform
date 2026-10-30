"""Pipeline thời tiết hằng ngày cho bảng `weather_daily` (Open-Meteo, không cần key, CC BY 4.0).

Chạy một ngày:      uv run python <thư mục bài>/starter/pipeline.py --day 2026-10-20
Backfill ngày thiếu: uv run python <thư mục bài>/starter/pipeline.py --backfill 2026-10-01 2026-10-21

Phần cho sẵn: hằng số, schema, `build_params`, `http_fetch`, `connect`, `main`.
Phần bạn viết (TODO): `save_raw`, `parse_day`, `run_day`, `missing_days`.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import logging
import os
import sqlite3
import tempfile
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

CITIES = {"hcmc": (10.82, 106.63), "hanoi": (21.03, 105.85), "danang": (16.05, 108.22)}
URL = "https://archive-api.open-meteo.com/v1/archive"
DAILY = ("temperature_2m_max", "temperature_2m_min", "precipitation_sum")

SCHEMA = """
CREATE TABLE IF NOT EXISTS weather_daily (
    city        TEXT NOT NULL,
    date        TEXT NOT NULL,
    tmax        REAL,
    tmin        REAL,
    precip_mm   REAL,
    source_file TEXT NOT NULL,
    loaded_at   TEXT NOT NULL,
    PRIMARY KEY (city, date)
);
CREATE TABLE IF NOT EXISTS run_log (
    run_id      INTEGER PRIMARY KEY AUTOINCREMENT,
    day         TEXT NOT NULL,
    status      TEXT NOT NULL,          -- running | success | failed
    n_rows      INTEGER,
    started_at  TEXT NOT NULL,
    finished_at TEXT,
    error       TEXT
);
"""

logger = logging.getLogger("weather_pipeline")


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def build_params(lat: float, lon: float, day: str) -> dict:
    """Tham số cho một thành phố, một ngày; ghim timezone để "ngày" là ngày theo giờ Việt Nam."""
    return {"latitude": lat, "longitude": lon, "start_date": day, "end_date": day,
            "daily": ",".join(DAILY), "timezone": "Asia/Bangkok"}


def http_fetch(url: str, params: dict) -> bytes:
    """Gọi API thật, trả nguyên bytes của response (dùng khi chạy từ dòng lệnh)."""
    import httpx

    resp = httpx.get(url, params=params, timeout=30, headers={"User-Agent": "da-learning-course/1.0"})
    resp.raise_for_status()
    return resp.content


def connect(db_path: Path) -> sqlite3.Connection:
    """Mở SQLite và tạo bảng nếu chưa có."""
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.executescript(SCHEMA)
    return conn


def save_raw(raw_dir: Path, day: str, city: str, body: bytes, url: str, params: dict, fetched_at: str) -> Path:
    """Ghi `raw_dir/<day>/<city>.json` (nguyên bytes) và `raw_dir/<day>/<city>.meta.json`.

    Metadata gồm đúng các khoá: url, params, fetched_at, sha256 (hex của body), n_bytes.
    Ghi qua tệp tạm rồi `os.replace` để không bao giờ để lại tệp ghi dở. Trả đường dẫn tệp `.json`.
    """
    # TODO
    raise NotImplementedError


def parse_day(body: bytes, city: str, day: str) -> dict:
    """Một dòng {city, date, tmax, tmin, precip_mm} cho đúng ngày `day`.

    `ValueError` nếu response báo lỗi (`"error": true`) hoặc không có ngày `day` trong `daily.time`.
    """
    # TODO
    raise NotImplementedError


def run_day(day: str, fetch, raw_dir: Path, db_path: Path, cities: dict = CITIES, now=utc_now) -> dict:
    """Thu thập một ngày cho mọi thành phố, nạp idempotent, ghi run_log. Không ném lỗi ra ngoài.

    - ghi run_log một dòng `running` ngay khi bắt đầu (commit luôn, để thấy được run đang chạy hoặc bị kill);
    - mỗi thành phố: `fetch(URL, build_params(...))` -> `save_raw` -> `parse_day`;
    - chỉ khi **mọi** thành phố thành công: upsert các dòng vào `weather_daily` theo khoá (city, date) và cập nhật
      run_log thành `success` trong cùng một transaction;
    - có lỗi: không ghi dòng nào vào `weather_daily`, run_log thành `failed` kèm `error`, log mức ERROR;
    - log mức INFO một dòng có ngày, trạng thái, số dòng.
    Trả {"day", "status", "n_rows", "error"} (`error` là None khi thành công).
    """
    # TODO
    raise NotImplementedError


def missing_days(db_path: Path, start: str, end: str, cities: dict = CITIES) -> list[str]:
    """Các ngày trong [start, end] (gồm cả hai đầu) mà weather_daily chưa đủ mọi thành phố, sắp tăng dần."""
    # TODO
    raise NotImplementedError


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--day", help="YYYY-MM-DD")
    group.add_argument("--backfill", nargs=2, metavar=("START", "END"))
    parser.add_argument("--root", default=".", help="gốc repo (mặc định thư mục hiện tại)")
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    root = Path(args.root)
    raw_dir, db_path = root / "data/raw_api/weather-daily", root / "data/clean/weather.sqlite"
    days = [args.day] if args.day else missing_days(db_path, *args.backfill)
    results = [run_day(d, http_fetch, raw_dir, db_path) for d in days]
    return 0 if all(r["status"] == "success" for r in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())

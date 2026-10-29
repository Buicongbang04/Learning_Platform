import json
import re
from datetime import datetime, timedelta, timezone

import nbformat
import numpy as np
import pandas as pd
import pytest

from testkit import ROOT, Exercise

ex = Exercise(__file__)
_CACHE = {}
DAY_MS = 86_400_000


@pytest.fixture(scope="module")
def nb():
    return ex.notebook("earthquakes.ipynb")


def ms(text: str) -> int:
    return int(datetime.fromisoformat(text).replace(tzinfo=timezone.utc).timestamp() * 1000)


def feature(eid, time, mag, place, lag_days=70, tsunami=0, updated=None):
    t = ms(time)
    return {"type": "Feature", "id": eid,
            "properties": {"mag": mag, "place": place, "time": t, "updated": updated or t + lag_days * DAY_MS,
                           "tsunami": tsunami, "status": "reviewed", "sig": 300, "magType": "mb", "type": "earthquake"},
            "geometry": {"type": "Point", "coordinates": [140.0, 35.0, 10.0]}}


class FakeUSGS:
    """Giả lập FDSN event service: lọc theo updatedafter, sắp theo time, cắt theo offset (bắt đầu từ 1) và limit."""

    def __init__(self, catalog):
        self.catalog = catalog
        self.calls = []

    def __call__(self, url, params=None, timeout=None):
        self.calls.append(dict(params))
        rows = sorted(self.catalog, key=lambda f: f["properties"]["time"])
        if "updatedafter" in params:
            after = ms(params["updatedafter"].rstrip("Z"))
            rows = [f for f in rows if f["properties"]["updated"] >= after]
        start = params["offset"] - 1
        page = rows[start:start + params["limit"]]
        return Resp({"type": "FeatureCollection", "metadata": {"count": len(page)}, "features": page})


class Resp:
    status_code = 200
    headers = {}

    def __init__(self, payload):
        self.payload = payload

    def json(self):
        return self.payload


class Clock:
    def __init__(self):
        self.t = 0.0
        self.slept = []

    def __call__(self):
        return self.t

    def sleep(self, seconds):
        self.slept.append(seconds)
        self.t += seconds


def catalog():
    return [feature("a", "2024-01-01T07:10:09", 7.5, "2024 Noto Peninsula, Japan Earthquake", tsunami=1),
            feature("b", "2024-01-05T00:00:00", 4.5, "10 km S of Sabang, Indonesia", lag_days=2),
            feature("c", "2024-02-01T00:00:00", 5.0, "Banda Sea, Indonesia", lag_days=40),
            feature("d", "2024-02-10T00:00:00", 6.1, "50 km W of Iquique, Chile", lag_days=100, tsunami=1),
            feature("e", "2024-02-20T00:00:00", 4.6, "Fiji region", lag_days=10)]


def run(nb, get, tmp_path, clock=None, page_size=2):
    clock = clock or Clock()
    return nb.collect(get, tmp_path / "raw", start="2024-01-01", end="2025-01-01", min_mag=4.5,
                      page_size=page_size, min_interval=1.0, sleep=clock.sleep, clock=clock)


# ---------- phân trang ----------

def test_page_params(nb):
    p = nb.page_params("2024-01-01", "2025-01-01", 4.5, limit=1000, offset=1)
    assert p == {"format": "geojson", "starttime": "2024-01-01", "endtime": "2025-01-01", "minmagnitude": 4.5,
                 "orderby": "time-asc", "limit": 1000, "offset": 1}
    p = nb.page_params("2024-01-01", "2025-01-01", 4.5, limit=1000, offset=1001, updated_after=ms("2024-03-01T00:00:00"))
    assert p["offset"] == 1001
    assert p["updatedafter"] == "2024-03-01T00:00:00.000"


def test_fetch_pages_walks_offsets_until_short_page(nb):
    get = FakeUSGS(catalog())
    clock = Clock()
    pages = list(nb.fetch_pages(get, nb.page_params("2024-01-01", "2025-01-01", 4.5, 2, 1), page_size=2,
                                min_interval=1.0, sleep=clock.sleep, clock=clock))
    assert [len(p["features"]) for p in pages] == [2, 2, 1]
    assert [c["offset"] for c in get.calls] == [1, 3, 5]


def test_fetch_pages_stops_on_exact_multiple(nb):
    get = FakeUSGS(catalog()[:4])
    clock = Clock()
    pages = list(nb.fetch_pages(get, nb.page_params("2024-01-01", "2025-01-01", 4.5, 2, 1), page_size=2,
                                min_interval=1.0, sleep=clock.sleep, clock=clock))
    assert [len(p["features"]) for p in pages] == [2, 2, 0]


def test_fetch_pages_throttles(nb):
    clock = Clock()
    list(nb.fetch_pages(FakeUSGS(catalog()), nb.page_params("2024-01-01", "2025-01-01", 4.5, 2, 1), page_size=2,
                        min_interval=1.0, sleep=clock.sleep, clock=clock))
    assert clock.slept == [pytest.approx(1.0), pytest.approx(1.0)]     # 3 request, nghỉ giữa các request, không nghỉ trước request đầu


# ---------- thu thập incremental ----------

def test_collect_full_then_incremental(nb, tmp_path):
    cat = catalog()
    get = FakeUSGS(cat)
    first = run(nb, get, tmp_path)
    assert first == {"run": 1, "pages": 3, "events": 5, "watermark": max(f["properties"]["updated"] for f in cat)}
    assert sorted(p.name for p in (tmp_path / "raw" / "run-001").iterdir()) == ["page-001.json", "page-002.json", "page-003.json"]
    assert all("updatedafter" not in c for c in get.calls)

    # Nguồn sửa magnitude của "b" và thêm một trận mới; cả hai có updated sau watermark
    late = first["watermark"] + DAY_MS
    cat[1] = feature("b", "2024-01-05T00:00:00", 4.9, "10 km S of Sabang, Indonesia", updated=late)
    cat.append(feature("f", "2024-12-30T00:00:00", 5.5, "Tonga", updated=late))
    get.calls.clear()
    second = run(nb, get, tmp_path)
    assert second["run"] == 2 and second["watermark"] == late
    assert get.calls[0]["updatedafter"] == datetime.fromtimestamp(first["watermark"] / 1000, timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3]
    assert second["events"] < 5, "Lần chạy incremental chỉ lấy bản ghi mới/sửa sau watermark"

    df = nb.load_events(tmp_path / "raw")
    assert len(df) == 6 and df["id"].is_unique
    assert df.set_index("id").loc["b", "mag"] == 4.9                   # upsert: giữ bản cập nhật sau cùng


def test_collect_failure_keeps_old_state(nb, tmp_path):
    get = FakeUSGS(catalog())
    first = run(nb, get, tmp_path)

    def broken(url, params=None, timeout=None):
        raise RuntimeError("API sập giữa chừng")

    with pytest.raises(RuntimeError):
        run(nb, broken, tmp_path)
    state = json.loads((tmp_path / "raw" / "state.json").read_text())
    assert state["watermark"] == first["watermark"] and state["runs"] == 1


# ---------- dữ liệu sạch và insight ----------

def write_pages(tmp_path, features):
    page_dir = tmp_path / "raw" / "run-001"
    page_dir.mkdir(parents=True)
    (page_dir / "page-001.json").write_text(json.dumps({"features": features}))
    return tmp_path / "raw"


def test_load_events_schema(nb, tmp_path):
    df = nb.load_events(write_pages(tmp_path, catalog()))
    assert list(df.columns) == ["id", "time", "updated", "mag", "mag_type", "place", "region",
                                "lat", "lon", "depth_km", "tsunami", "status", "sig", "type"]
    assert str(df["time"].dt.tz) == "UTC" and str(df["updated"].dt.tz) == "UTC"
    assert df["time"].is_monotonic_increasing
    regions = dict(zip(df["id"], df["region"]))
    assert regions == {"a": "Japan", "b": "Indonesia", "c": "Indonesia", "d": "Chile", "e": "Fiji region"}
    assert df["tsunami"].dtype == bool


def test_insights_on_toy(nb, tmp_path):
    got = nb.insights(nb.load_events(write_pages(tmp_path, catalog())))
    assert got["events"] == 5
    assert (got["m6_plus"], got["m7_plus"]) == (2, 1)
    assert (got["largest_mag"], got["largest_time"]) == (7.5, "2024-01-01")
    assert got["largest_place"] == "2024 Noto Peninsula, Japan Earthquake"
    assert (got["top_region"], got["top_region_events"]) == ("Indonesia", 2)
    assert (got["busiest_month"], got["busiest_month_events"]) == (2, 3)
    assert got["tsunami_flagged"] == 2
    assert got["median_update_lag_days"] == pytest.approx(40)
    assert got["share_updated_after_30d"] == pytest.approx(0.6)
    m = np.arange(4.5, 7.01, 0.5)
    expected_b = -np.polyfit(m, np.log10([5, 3, 2, 2, 1, 1]), 1)[0]
    assert got["gutenberg_richter_b"] == pytest.approx(expected_b)


def test_write_clean_overwrites(nb, tmp_path):
    df = nb.load_events(write_pages(tmp_path, catalog()))
    first = nb.write_clean(df, tmp_path / "clean")
    assert nb.write_clean(df, tmp_path / "clean") == first
    back = pd.read_parquet(tmp_path / "clean")
    assert len(back) == 5 and back["id"].is_unique


# ---------- dữ liệu thật: USGS, M4.5+ toàn cầu năm 2024 ----------

def real(nb):
    raw = ROOT / "data" / "raw" / "usgs-earthquakes"
    if not list(raw.glob("run-*/page-*.json")):
        pytest.skip("Chưa thu thập USGS. Chạy cell `explore: thu thập` trong notebook (gọi API thật, "
                    "ghi data/raw/usgs-earthquakes/)")
    if "real" not in _CACHE:
        df = nb.load_events(raw)
        _CACHE["real"] = df, nb.insights(df)
    return _CACHE["real"]


def test_real_catalog(nb):
    df, got = real(nb)
    assert got["events"] == pytest.approx(6397, rel=0.01)
    assert df["id"].is_unique
    assert df["time"].min() >= pd.Timestamp("2024-01-01", tz="UTC")
    assert df["time"].max() < pd.Timestamp("2025-01-01", tz="UTC")
    assert (df["mag"] >= 4.5).all()


def test_real_big_events(nb):
    _, got = real(nb)
    assert got["largest_mag"] == pytest.approx(7.5)
    assert "Noto" in got["largest_place"] and got["largest_time"] == "2024-01-01"
    assert got["m7_plus"] == pytest.approx(10, abs=1)
    assert got["m6_plus"] == pytest.approx(99, abs=3)
    assert got["tsunami_flagged"] == pytest.approx(81, abs=5)


def test_real_where_and_when(nb):
    _, got = real(nb)
    assert got["top_region"] == "Indonesia"
    assert got["top_region_events"] == pytest.approx(605, abs=15)
    assert got["busiest_month"] == 4                         # dư chấn trận Hoa Liên (Đài Loan) 02/04/2024


def test_real_late_updates_and_physics(nb):
    _, got = real(nb)
    assert got["share_updated_after_30d"] > 0.95             # gần như mọi bản ghi bị sửa sau hơn 1 tháng
    assert 50 <= got["median_update_lag_days"] <= 400
    assert 1.0 <= got["gutenberg_richter_b"] <= 1.3          # luật Gutenberg-Richter: b ≈ 1


# ---------- biểu đồ và báo cáo ----------

def test_notebook_draws_charts():
    book = nbformat.read(ex.path("earthquakes.ipynb"), as_version=4)
    plots = [c for c in book.cells if c.cell_type == "code" and "explore" in c.metadata.get("tags", [])
             and re.search(r"plt\.|\.plot\(|\.bar\(|\.hist\(|\.scatter\(", "\n".join(
                 line for line in c.source.splitlines() if not line.lstrip().startswith("#")))]
    assert len(plots) >= 2, "Cần ít nhất 2 cell explore vẽ biểu đồ"


def test_report_sections_and_numbers():
    text = ex.read("report.md")
    assert "TODO" not in text, "Điền hết các mục TODO trong report.md"
    for heading in ("## Bộ dữ liệu", "## Làm sạch", "## Insight", "## Giới hạn"):
        assert heading in text
    insight = text.split("## Insight", 1)[1].split("\n## ", 1)[0]
    assert len(re.findall(r"\d[\d.,]*", insight)) >= 3, "Mục Insight cần số liệu cụ thể"

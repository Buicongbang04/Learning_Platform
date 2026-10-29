import json
import re

import nbformat
import pandas as pd
import pytest
import requests

from testkit import ROOT, Exercise

ex = Exercise(__file__)
URL = "https://archive-api.open-meteo.com/v1/archive"
PAYLOAD = json.loads((ex.fixtures / "open_meteo_sample.json").read_text(encoding="utf-8"))
_CACHE = {}


@pytest.fixture(scope="module")
def nb():
    return ex.notebook("weather.ipynb")


class FakeResponse:
    def __init__(self, status=200, payload=None, headers=None):
        self.status_code = status
        self._payload = payload if payload is not None else PAYLOAD
        self.headers = headers or {}

    def json(self):
        return self._payload


class FakeGet:
    """Thay requests.get: trả lần lượt các phản hồi trong `script`, ghi lại mọi lời gọi."""

    def __init__(self, *script):
        self.script = list(script)
        self.calls = []

    def __call__(self, url, params=None, timeout=None):
        self.calls.append((url, dict(params or {}), timeout))
        item = self.script.pop(0) if len(self.script) > 1 else self.script[0]
        if isinstance(item, Exception):
            raise item
        return item


# ---------- gọi API ----------

def test_build_params_pins_everything(nb):
    params = nb.build_params(10.82, 106.63, "2023-01-01", "2023-12-31")
    assert params == {
        "latitude": 10.82, "longitude": 106.63, "start_date": "2023-01-01", "end_date": "2023-12-31",
        "daily": "temperature_2m_max,temperature_2m_min,temperature_2m_mean,precipitation_sum",
        "timezone": "Asia/Bangkok", "models": "era5",
    }


def test_fetch_json_success_sets_timeout(nb):
    get = FakeGet(FakeResponse())
    assert nb.fetch_json(get, URL, {"a": 1}, sleep=lambda s: None) == PAYLOAD
    assert len(get.calls) == 1 and get.calls[0][2] is not None


def test_fetch_json_retries_429_and_5xx_with_backoff(nb):
    slept = []
    get = FakeGet(FakeResponse(429), FakeResponse(503), requests.ConnectionError("reset"), FakeResponse())
    assert nb.fetch_json(get, URL, {}, max_retries=4, sleep=slept.append) == PAYLOAD
    assert slept == [1, 2, 4]


def test_fetch_json_honours_retry_after(nb):
    slept = []
    get = FakeGet(FakeResponse(429, headers={"Retry-After": "7"}), FakeResponse())
    nb.fetch_json(get, URL, {}, sleep=slept.append)
    assert slept == [7]


def test_fetch_json_gives_up(nb):
    slept = []
    get = FakeGet(FakeResponse(429))
    with pytest.raises(RuntimeError):
        nb.fetch_json(get, URL, {}, max_retries=3, sleep=slept.append)
    assert len(get.calls) == 4 and slept == [1, 2, 4]


def test_fetch_json_does_not_retry_client_errors(nb):
    get = FakeGet(FakeResponse(400, payload={"error": True, "reason": "bad date"}))
    with pytest.raises(RuntimeError, match="400"):
        nb.fetch_json(get, URL, {}, sleep=lambda s: None)
    assert len(get.calls) == 1


def test_collect_caches_raw_json(nb, tmp_path):
    get = FakeGet(FakeResponse())
    cities = {"hcmc": (10.82, 106.63), "hanoi": (21.03, 105.85)}
    paths = nb.collect(get, tmp_path, cities, "2023-01-01", "2023-01-04", sleep=lambda s: None)
    assert sorted(p.name for p in paths) == ["hanoi_2023-01-01_2023-01-04.json", "hcmc_2023-01-01_2023-01-04.json"]
    assert len(get.calls) == 2
    assert json.loads(paths[0].read_text(encoding="utf-8")) == PAYLOAD      # lưu nguyên response thô
    assert [p.name for p in tmp_path.iterdir() if not p.name.endswith(".json")] == []   # không để lại tệp tạm

    again = nb.collect(get, tmp_path, cities, "2023-01-01", "2023-01-04", sleep=lambda s: None)
    assert len(get.calls) == 2, "Lần chạy thứ hai phải đọc cache, không gọi API"
    assert sorted(again) == sorted(paths)


# ---------- parse, clean ----------

def test_parse_daily(nb):
    df = nb.parse_daily(PAYLOAD, "hcmc")
    assert list(df.columns) == ["city", "date", "tmax", "tmin", "tmean", "precip_mm"]
    assert len(df) == 4 and (df["city"] == "hcmc").all()
    assert pd.api.types.is_datetime64_any_dtype(df["date"])
    assert df["tmax"].iloc[1] == pytest.approx(30.6)


def test_clean_drops_empty_days_and_overlaps(nb):
    once = nb.parse_daily(PAYLOAD, "hcmc")
    df = nb.clean(pd.concat([once, once, nb.parse_daily(PAYLOAD, "hanoi")]))   # hai lần lấy chồng nhau
    assert len(df) == 6                                         # 3 ngày có số x 2 thành phố
    assert not df.duplicated(["city", "date"]).any()
    assert df[["tmax", "tmin", "tmean", "precip_mm"]].notna().all().all()
    assert list(df["city"]) == ["hanoi"] * 3 + ["hcmc"] * 3


# ---------- insight ----------

def _toy():
    rows = [("a", "2023-01-01", 25, 20, 0), ("a", "2023-01-02", 36, 22, 2), ("a", "2023-06-01", 35, 30, 10),
            ("a", "2023-06-02", 34, 32, 0.5), ("a", "2023-12-01", 22, 18, 1), ("b", "2023-03-01", 30, 27, 3)]
    df = pd.DataFrame(rows, columns=["city", "date", "tmax", "tmean", "precip_mm"])
    df["date"] = pd.to_datetime(df["date"])
    df["tmin"] = df["tmean"] - 5
    return df[["city", "date", "tmax", "tmin", "tmean", "precip_mm"]]


def test_insights_on_toy(nb):
    got = nb.insights(_toy())
    assert set(got) == {"a", "b"}
    a = got["a"]
    assert a["annual_rain_mm"] == pytest.approx(13.5)
    assert a["rainy_season_share"] == pytest.approx(10.5 / 13.5)
    assert (a["hottest_month"], a["coldest_month"]) == (6, 12)
    assert a["amplitude_c"] == pytest.approx(13.0)
    assert (a["max_temp"], a["max_temp_date"]) == (36, "2023-01-02")
    assert a["hot_days"] == 2
    assert a["rainy_days"] == 3


def test_write_clean_overwrites(nb, tmp_path):
    df = _toy()
    first = nb.write_clean(df, tmp_path / "clean")
    assert nb.write_clean(df, tmp_path / "clean") == first
    assert len(pd.read_parquet(tmp_path / "clean")) == len(df)


# ---------- dữ liệu thật: TP.HCM và Hà Nội, cả năm 2023 (ERA5) ----------

def real(nb):
    raw = ROOT / "data" / "raw" / "open-meteo"
    files = [raw / f"{city}_2023-01-01_2023-12-31.json" for city in ("hcmc", "hanoi")]
    if not all(f.exists() for f in files):
        pytest.skip("Chưa thu thập dữ liệu Open-Meteo. Chạy cell `explore: thu thập` trong notebook "
                    "(gọi API thật, ghi data/raw/open-meteo/)")
    if "real" not in _CACHE:
        frames = [nb.parse_daily(json.loads(f.read_text(encoding="utf-8")), f.name.split("_")[0]) for f in files]
        df = nb.clean(pd.concat(frames))
        _CACHE["real"] = df, nb.insights(df)
    return _CACHE["real"]


def test_real_complete_year(nb):
    df, _ = real(nb)
    assert df.groupby("city").size().to_dict() == {"hanoi": 365, "hcmc": 365}


def test_real_seasonality_contrast(nb):
    _, got = real(nb)
    hcmc, hanoi = got["hcmc"], got["hanoi"]
    assert hcmc["amplitude_c"] == pytest.approx(3.3, abs=0.4)     # nhiệt đới: gần như không có mùa đông
    assert hanoi["amplitude_c"] == pytest.approx(13.6, abs=0.4)   # cận nhiệt đới gió mùa: biên độ gấp 4 lần
    assert hcmc["hottest_month"] == 4                             # nóng nhất ngay TRƯỚC mùa mưa
    assert hanoi["hottest_month"] == 7
    assert hcmc["coldest_month"] == hanoi["coldest_month"] == 1


def test_real_rain_and_heat(nb):
    _, got = real(nb)
    hcmc, hanoi = got["hcmc"], got["hanoi"]
    assert hcmc["annual_rain_mm"] == pytest.approx(1826, abs=60)
    assert hanoi["annual_rain_mm"] == pytest.approx(1502, abs=60)
    assert hcmc["rainy_season_share"] == pytest.approx(0.82, abs=0.02)
    assert hanoi["rainy_season_share"] == pytest.approx(0.84, abs=0.02)
    assert hanoi["max_temp"] == pytest.approx(39.8, abs=0.5)
    assert hanoi["hot_days"] == pytest.approx(47, abs=5)
    assert hcmc["hot_days"] <= 12
    assert hcmc["rainy_days"] > hanoi["rainy_days"]


# ---------- biểu đồ ----------

def test_notebook_draws_charts():
    book = nbformat.read(ex.path("weather.ipynb"), as_version=4)
    plots = [c for c in book.cells if c.cell_type == "code" and "explore" in c.metadata.get("tags", [])
             and re.search(r"plt\.|\.plot\(|\.bar\(|\.hist\(", "\n".join(
                 line for line in c.source.splitlines() if not line.lstrip().startswith("#")))]
    assert len(plots) >= 2, "Cần ít nhất 2 cell explore vẽ biểu đồ"

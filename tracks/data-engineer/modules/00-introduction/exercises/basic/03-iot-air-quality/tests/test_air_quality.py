import re
import zipfile

import nbformat
import pandas as pd
import pytest

from testkit import Exercise

ex = Exercise(__file__)
SENSORS = ["s1_co", "s2_nmhc", "s3_nox", "s4_no2", "s5_o3"]
_CACHE = {}


@pytest.fixture(scope="module")
def nb():
    return ex.notebook("air_quality.ipynb")


@pytest.fixture
def sample_zip(tmp_path):
    path = tmp_path / "air-quality.zip"
    with zipfile.ZipFile(path, "w") as zf:
        zf.write(ex.fixtures / "air_quality_sample.csv", "AirQualityUCI.csv")
    return path


def sample(nb, sample_zip):
    return nb.clean(nb.load_raw(sample_zip))


# ---------- đọc tệp thô: ; và dấu phẩy thập phân ----------

def test_load_raw_reads_semicolon_and_decimal_comma(nb, sample_zip):
    raw = nb.load_raw(sample_zip)
    assert "CO(GT)" in raw.columns and "Date" in raw.columns
    assert raw["CO(GT)"].iloc[0] == pytest.approx(2.0)
    assert raw["AH"].iloc[0] == pytest.approx(0.6)


# ---------- làm sạch ----------

def test_clean_columns_and_timestamp(nb, sample_zip):
    df = sample(nb, sample_zip)
    assert list(df.columns) == ["ts", *nb.COLUMNS.values()]
    assert pd.api.types.is_datetime64_any_dtype(df["ts"])
    assert df["ts"].iloc[0] == pd.Timestamp("2004-03-12 07:00")
    assert df["ts"].is_monotonic_increasing


def test_clean_drops_empty_rows_and_duplicate_hours(nb, sample_zip):
    df = sample(nb, sample_zip)
    assert len(df) == 6
    assert df["ts"].is_unique


def test_clean_sentinel_becomes_null_but_real_negatives_stay(nb, sample_zip):
    df = sample(nb, sample_zip)
    numeric = df.drop(columns="ts")
    assert not (numeric == -200).any().any()
    assert numeric["nmhc_gt"].isna().sum() == 5
    assert (df["temp_c"] == -1.5).sum() == 1           # -1,5 °C là nhiệt độ thật, không phải giá trị thiếu


def test_outages_on_sample(nb, sample_zip):
    df = sample(nb, sample_zip)
    out = nb.outages(df)
    assert list(out.columns) == ["start", "hours"]
    assert out.to_dict("records") == [{"start": pd.Timestamp("2004-03-12 09:00"), "hours": 1}]


def test_insights_on_sample(nb, sample_zip):
    got = nb.insights(sample(nb, sample_zip))
    assert got["rows"] == 6
    assert (got["start"], got["end"]) == ("2004-03-12 07:00", "2004-03-13 08:00")
    assert got["missing_share"]["nmhc_gt"] == pytest.approx(5 / 6)
    assert got["missing_share"]["co_gt"] == pytest.approx(1 / 6)
    assert got["nmhc_last_valid"] == "2004-03-12"
    assert got["outage_hours"] == 1
    assert (got["longest_outage_hours"], got["longest_outage_start"]) == (1, "2004-03-12 09:00")
    assert got["co_peak_hour"] == 10
    assert got["co_morning_peak_hour"] == 10
    assert got["co_trough_hour"] == 7
    assert got["co_weekday_mean"] == pytest.approx(3.0)
    assert got["co_weekend_mean"] == pytest.approx(1.25)
    assert got["weekend_drop_pct"] == pytest.approx(58.33, abs=0.01)
    assert got["lowest_co_month"] is None              # không có tháng nào đủ ngày


def test_monthly_profile_on_sample(nb, sample_zip):
    m = nb.monthly_profile(sample(nb, sample_zip))
    assert list(m.index.astype(str)) == ["2004-03"]
    row = m.iloc[0]
    assert row["days"] == 2
    assert row["co_gt"] == pytest.approx((2 + 4 + 3 + 1 + 1.5) / 5)
    assert row["co_missing_share"] == pytest.approx(1 / 6)


def test_write_clean_overwrites(nb, sample_zip, tmp_path):
    df = sample(nb, sample_zip)
    first = nb.write_clean(df, tmp_path / "clean")
    assert nb.write_clean(df, tmp_path / "clean") == first
    back = pd.read_parquet(tmp_path / "clean")
    assert len(back) == 6 and back["ts"].is_unique


# ---------- dữ liệu thật: UCI Air Quality, 03/2004 - 04/2005 ----------

def real(nb):
    raw = ex.dataset("air-quality-uci")
    if "real" not in _CACHE:
        df = nb.clean(nb.load_raw(raw / "air-quality.zip"))
        _CACHE["real"] = df, nb.insights(df)
    return _CACHE["real"]


def test_real_shape_and_range(nb):
    df, got = real(nb)
    assert got["rows"] == 9357
    assert (got["start"], got["end"]) == ("2004-03-10 18:00", "2005-04-04 14:00")
    assert df["ts"].diff().dropna().eq(pd.Timedelta(hours=1)).all()    # đủ mọi giờ, không thiếu dòng


def test_real_missingness_is_structural(nb):
    _, got = real(nb)
    assert got["missing_share"]["nmhc_gt"] == pytest.approx(0.902, abs=0.002)   # máy phân tích NMHC ngừng sau 04/2004
    assert got["nmhc_last_valid"] == "2004-05-01"
    assert got["missing_share"]["co_gt"] == pytest.approx(0.180, abs=0.002)
    assert got["outage_hours"] == 366
    assert (got["longest_outage_hours"], got["longest_outage_start"]) == (76, "2005-02-08 17:00")


def test_real_traffic_rhythm(nb):
    _, got = real(nb)
    assert got["co_morning_peak_hour"] == 9
    assert got["co_peak_hour"] == 19
    assert got["co_trough_hour"] == 5
    assert got["co_weekday_mean"] == pytest.approx(2.36, abs=0.01)
    assert got["co_weekend_mean"] == pytest.approx(1.65, abs=0.01)
    assert got["weekend_drop_pct"] == pytest.approx(29.9, abs=0.3)
    assert got["lowest_co_month"] == "2004-08"          # kỳ nghỉ Ferragosto


def test_real_monthly_profile(nb):
    df, _ = real(nb)
    m = nb.monthly_profile(df)
    m.index = m.index.astype(str)
    assert len(m) == 14
    assert m.loc["2004-11", "nox_gt"] > 3 * m.loc["2004-06", "nox_gt"]


# ---------- biểu đồ ----------

def test_notebook_draws_charts():
    book = nbformat.read(ex.path("air_quality.ipynb"), as_version=4)
    plots = [c for c in book.cells if c.cell_type == "code" and "explore" in c.metadata.get("tags", [])
             and re.search(r"plt\.|\.plot\(|\.bar\(|\.hist\(|imshow\(", "\n".join(
                 line for line in c.source.splitlines() if not line.lstrip().startswith("#")))]
    assert len(plots) >= 2, "Cần ít nhất 2 cell explore vẽ biểu đồ"

import re

import nbformat
import pandas as pd
import pytest

from testkit import Exercise

ex = Exercise(__file__)
_CACHE = {}


@pytest.fixture(scope="module")
def nb():
    return ex.notebook("source_profile.ipynb")


def toy():
    ts = pd.to_datetime(["2024-01-01 00:00", "2024-01-01 00:01", "2024-01-01 00:02",
                         "2024-01-01 00:10", "2024-01-01 00:10", "2024-01-01 00:11"])
    return pd.DataFrame({"ts": ts, "id": [1, 2, 3, 4, 4, 6], "a": [1.0, -200.0, None, 4.0, 4.0, 5.0]})


# ---------- profile ----------

def test_profile_on_toy(nb):
    got = nb.profile(toy(), "ts", key=["id"], sentinels=(-200,))
    assert got["rows"] == 6 and got["columns"] == 3
    assert (got["start"], got["end"]) == ("2024-01-01 00:00:00", "2024-01-01 00:11:00")
    assert got["span_days"] == pytest.approx(11 / 1440)
    assert got["rows_per_day"] == pytest.approx(6 / (11 / 1440))
    assert got["median_interval_s"] == pytest.approx(60)
    assert (got["max_gap_s"], got["max_gap_start"]) == (pytest.approx(480), "2024-01-01 00:02:00")
    assert got["duplicate_rows"] == 1
    assert got["duplicate_keys"] == 1
    assert got["sentinel_count"] == 1
    assert (got["worst_null_column"], got["worst_null_share"]) == ("a", pytest.approx(2 / 6))


def test_profile_without_key_or_sentinel(nb):
    got = nb.profile(toy(), "ts")
    assert got["duplicate_keys"] is None
    assert got["sentinel_count"] == 0
    assert got["worst_null_share"] == pytest.approx(1 / 6)       # -200 không được coi là thiếu nếu không khai báo


def test_profile_unsorted_input(nb):
    shuffled = toy().sample(frac=1, random_state=3)
    assert nb.profile(shuffled, "ts")["max_gap_s"] == pytest.approx(480)


def test_gaps(nb):
    out = nb.gaps(toy(), "ts", min_gap_s=120)
    assert list(out.columns) == ["start", "end", "seconds"]
    assert out.to_dict("records") == [{"start": pd.Timestamp("2024-01-01 00:02"),
                                       "end": pd.Timestamp("2024-01-01 00:10"), "seconds": 480.0}]


# ---------- dung lượng ----------

def test_footprint_writes_parquet_and_measures(nb, tmp_path):
    path = tmp_path / "toy.parquet"
    got = nb.footprint(toy(), raw_bytes=1000, path=path)
    size = path.stat().st_size
    assert got == {"raw_bytes": 1000, "parquet_bytes": size, "raw_bytes_per_row": pytest.approx(1000 / 6),
                   "parquet_bytes_per_row": pytest.approx(size / 6), "compression_ratio": pytest.approx(1000 / size)}
    assert nb.footprint(toy(), raw_bytes=1000, path=path)["parquet_bytes"] == size     # ghi đè, không cộng dồn


def test_yearly_volume(nb):
    assert nb.yearly_volume_gb(rows_per_day=1000, bytes_per_row=200) == pytest.approx(0.073)


def test_compare_and_write(nb, tmp_path):
    table = nb.compare({"slow": {"rows_per_day": 1.0, "rows": 3}, "fast": {"rows_per_day": 5.0, "rows": 9}})
    assert list(table.index) == ["fast", "slow"]
    first = nb.write_clean(table, tmp_path / "clean")
    assert nb.write_clean(table, tmp_path / "clean") == first
    assert len(pd.read_parquet(tmp_path / "clean")) == 2


# ---------- dữ liệu thật ----------

def nasa(nb):
    raw = ex.dataset("nasa-http-logs")
    if "nasa" not in _CACHE:
        df = nb.load_nasa(raw / "NASA_access_log_Jul95.gz")
        _CACHE["nasa"] = df, nb.profile(df, "ts")
    return _CACHE["nasa"]


def air(nb):
    raw = ex.dataset("air-quality-uci")
    if "air" not in _CACHE:
        df = nb.load_air(raw / "air-quality.zip")
        _CACHE["air"] = df, nb.profile(df, "ts", key=["ts"], sentinels=(-200,))
    return _CACHE["air"]


def test_real_log_velocity_and_gaps(nb):
    _, got = nasa(nb)
    assert got["rows"] == pytest.approx(1_891_714, abs=10)
    assert got["rows_per_day"] == pytest.approx(68_629, rel=0.005)
    assert got["median_interval_s"] == 1.0
    assert got["max_gap_s"] == 1326.0                            # 22 phút tối 13/07 (giờ UTC)
    assert got["max_gap_start"] == "1995-07-13 23:48:59"
    assert got["duplicate_rows"] == pytest.approx(835, abs=5)


def test_real_log_long_gaps(nb):
    df, _ = nasa(nb)
    out = nb.gaps(df, "ts", min_gap_s=600)
    assert len(out) == 1 and out.iloc[0]["seconds"] == 1326.0


def test_real_iot_regular_but_sentinel_heavy(nb):
    _, got = air(nb)
    assert got["rows"] == 9357
    assert got["rows_per_day"] == pytest.approx(24.0, abs=0.01)
    assert got["median_interval_s"] == got["max_gap_s"] == 3600.0
    assert got["duplicate_keys"] == 0
    assert got["sentinel_count"] == pytest.approx(16_701, abs=10)
    assert got["worst_null_column"] == "NMHC(GT)"
    assert got["worst_null_share"] == pytest.approx(0.902, abs=0.002)


def test_real_parquet_footprint(nb, tmp_path):
    df, _ = air(nb)
    got = nb.footprint(df, raw_bytes=785_065, path=tmp_path / "air.parquet")    # AirQualityUCI.csv giải nén
    assert got["raw_bytes_per_row"] == pytest.approx(83.9, abs=0.1)
    assert got["compression_ratio"] > 2


# ---------- biểu đồ và báo cáo ----------

def test_notebook_draws_charts():
    book = nbformat.read(ex.path("source_profile.ipynb"), as_version=4)
    plots = [c for c in book.cells if c.cell_type == "code" and "explore" in c.metadata.get("tags", [])
             and re.search(r"plt\.|\.plot\(|\.bar\(|\.barh\(|\.hist\(", "\n".join(
                 line for line in c.source.splitlines() if not line.lstrip().startswith("#")))]
    assert len(plots) >= 2, "Cần ít nhất 2 cell explore vẽ biểu đồ"


def test_report_sections_and_numbers():
    text = ex.read("report.md")
    assert "TODO" not in text, "Điền hết các mục TODO trong report.md"
    for heading in ("## Bộ dữ liệu", "## Làm sạch", "## Insight", "## Giới hạn"):
        assert heading in text
    insight = text.split("## Insight", 1)[1].split("\n## ", 1)[0]
    assert len(re.findall(r"\d[\d.,]*", insight)) >= 3, "Mục Insight cần số liệu cụ thể"

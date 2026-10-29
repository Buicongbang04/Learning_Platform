import gzip
import re

import nbformat
import pandas as pd
import pytest

from testkit import Exercise

ex = Exercise(__file__)
SAMPLE = ex.fixtures / "access_sample.log"


@pytest.fixture(scope="module")
def nb():
    return ex.notebook("web_logs.ipynb")


_CACHE = {}


def parsed_sample(nb):
    with SAMPLE.open(encoding="latin-1") as fh:
        df, rejected = nb.parse_log(fh)
    return df, rejected


def sample(nb):
    df, rejected = parsed_sample(nb)
    return nb.clean(df), rejected


# ---------- parse: cấu trúc từng dòng ----------

def test_parse_line_common_log_format(nb):
    row = nb.parse_line('gamma.uni.edu - - [04/Jul/1995:00:10:05 -0400] "GET /history/apollo/ HTTP/1.0" 200 6245\n')
    assert row == {"host": "gamma.uni.edu", "ts": "04/Jul/1995:00:10:05 -0400", "method": "GET",
                   "path": "/history/apollo/", "protocol": "HTTP/1.0", "status": 200, "bytes": 6245}


def test_parse_line_dash_bytes_is_zero(nb):
    row = nb.parse_line('beta.nasa.gov - - [04/Jul/1995:00:10:00 -0400] "GET /missing.html HTTP/1.0" 404 -')
    assert row["status"] == 404 and row["bytes"] == 0


def test_parse_line_http09_request_has_no_protocol(nb):
    row = nb.parse_line('delta.example.com - - [04/Jul/1995:00:41:00 -0400] "GET /old/page.html" 200 1204')
    assert row["method"] == "GET" and row["path"] == "/old/page.html" and row["protocol"] is None


def test_parse_line_rejects_garbage(nb):
    assert nb.parse_line("this line is garbage and has no timestamp") is None
    assert nb.parse_line("theta.exa") is None
    assert nb.parse_line('eta.example.com - - [08/Jul/1995:12:01:00 -0400] "" 400 -') is None


def test_parse_log_streams_and_counts_rejects(nb):
    df, rejected = parsed_sample(nb)
    assert len(df) == 9
    assert len(rejected) == 3
    assert all(not line.endswith("\n") for line in rejected)


# ---------- clean: kiểu dữ liệu, múi giờ, không tự ý dedup ----------

def test_clean_types_and_utc(nb):
    df, _ = sample(nb)
    assert str(df["ts"].dt.tz) == "UTC"
    assert df["ts"].min() == pd.Timestamp("1995-07-04 03:59:58", tz="UTC")
    assert pd.api.types.is_integer_dtype(df["status"]) and pd.api.types.is_integer_dtype(df["bytes"])
    assert (df["bytes"] >= 0).all()
    assert df[["host", "ts", "method", "path", "status", "bytes"]].notna().all().all()


def test_clean_keeps_identical_requests(nb):
    # Log không có khoá: hai request giống hệt trong cùng giây là hai request thật, không được dedup.
    df, _ = sample(nb)
    assert (df["host"] == "192.0.2.10").sum() == 2


def test_clean_host_type(nb):
    df, _ = sample(nb)
    types = dict(zip(df["host"], df["host_type"]))
    assert types["192.0.2.10"] == "ip"
    assert types["beta.nasa.gov"] == "gov"
    assert types["gamma.uni.edu"] == "edu"
    assert types["epsilon"] == "local"


# ---------- insights trên fixture ----------

def test_insights_on_sample(nb):
    df, rejected = sample(nb)
    got = nb.insights(df, rejected)
    assert got["requests"] == 9
    assert got["rejected"] == 3
    assert got["reject_rate"] == pytest.approx(0.25)
    assert got["unique_hosts"] == 7
    assert got["total_gb"] == pytest.approx(11946 / 1e9)
    assert got["not_found"] == 3
    assert (got["top_404_path"], got["top_404_count"]) == ("/missing.html", 2)
    assert (got["peak_day"], got["peak_day_requests"]) == ("1995-07-04", 6)
    assert got["busiest_hour"] == 0
    assert got["quietest_hour"] == 23
    assert got["weekday_avg"] == pytest.approx(3.5)
    assert got["weekend_avg"] == pytest.approx(2.0)
    assert got["last_request"] == "1995-07-08 12:00:30"
    assert got["max_gap_minutes"] == pytest.approx(6439.0)
    assert got["max_gap_start"] == "1995-07-04 00:41:00"
    assert got["top_bytes_host_type"] == "edu"


# ---------- ghi dữ liệu sạch: chạy lại không nhân đôi ----------

def test_write_clean_overwrites(nb, tmp_path):
    df, _ = sample(nb)
    first = nb.write_clean(df, tmp_path / "clean")
    second = nb.write_clean(df, tmp_path / "clean")
    assert first == second and first.suffix == ".parquet"
    back = pd.read_parquet(tmp_path / "clean")
    assert len(back) == len(df)
    assert str(back["ts"].dt.tz) == "UTC"


# ---------- dữ liệu thật: NASA KSC tháng 7/1995 ----------

def real(nb):
    """Parse cả tháng một lần (~10 giây) rồi dùng lại cho mọi test dữ liệu thật."""
    raw = ex.dataset("nasa-http-logs")
    if "real" not in _CACHE:
        with gzip.open(raw / "NASA_access_log_Jul95.gz", "rt", encoding="latin-1") as fh:
            df, rejected = nb.parse_log(fh)
        df = nb.clean(df)
        _CACHE["real"] = df, nb.insights(df, rejected)
    return _CACHE["real"]


def test_real_volume(nb):
    _, got = real(nb)
    assert got["requests"] == pytest.approx(1_891_709, abs=50)     # 1 891 715 dòng, gần như dòng nào cũng đọc được
    assert got["rejected"] <= 50
    assert got["unique_hosts"] == pytest.approx(81_982, abs=20)
    assert got["total_gb"] == pytest.approx(38.70, abs=0.05)


def test_real_launch_day_peak(nb):
    # 13/07/1995: tàu con thoi Discovery (STS-70) phóng, gấp ~1,8 lần ngày thường
    _, got = real(nb)
    assert got["peak_day"] == "1995-07-13"
    assert got["peak_day_requests"] == pytest.approx(134_203, abs=20)
    assert got["max_gap_start"].startswith("1995-07-13 19:4")
    assert got["max_gap_minutes"] == pytest.approx(22.1, abs=0.1)


def test_real_daily_rhythm(nb):
    _, got = real(nb)
    assert got["busiest_hour"] in (12, 14)        # giờ miền Đông Mỹ, hai giờ gần bằng nhau
    assert got["quietest_hour"] == 5
    assert got["weekday_avg"] == pytest.approx(76_237, rel=0.01)
    assert got["weekend_avg"] == pytest.approx(45_871, rel=0.01)


def test_real_errors_and_end_of_log(nb):
    _, got = real(nb)
    assert got["not_found"] == pytest.approx(10_845, abs=20)
    assert got["top_404_path"] == "/pub/winvn/readme.txt"
    assert got["last_request"] == "1995-07-28 13:32:25"       # log dừng sớm 3,4 ngày
    assert got["top_bytes_host_type"] == "com"


def test_real_clean_quality(nb):
    df, _ = real(nb)
    assert str(df["ts"].dt.tz) == "UTC"
    assert df["ts"].between(pd.Timestamp("1995-07-01 04:00", tz="UTC"), pd.Timestamp("1995-07-28 18:00", tz="UTC")).all()
    assert df["status"].between(100, 599).all()
    assert (df["bytes"] >= 0).all()


# ---------- biểu đồ ----------

def test_notebook_draws_charts():
    book = nbformat.read(ex.path("web_logs.ipynb"), as_version=4)
    plots = [c for c in book.cells if c.cell_type == "code" and "explore" in c.metadata.get("tags", [])
             and re.search(r"plt\.|\.plot\(|\.bar\(|\.hist\(", "\n".join(
                 line for line in c.source.splitlines() if not line.lstrip().startswith("#")))]
    assert len(plots) >= 2, "Cần ít nhất 2 cell explore vẽ biểu đồ"

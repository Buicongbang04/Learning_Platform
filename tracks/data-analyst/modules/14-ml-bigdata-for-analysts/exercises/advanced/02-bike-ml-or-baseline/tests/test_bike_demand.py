import re

import numpy as np
import pandas as pd
import pytest

from testkit import Exercise

ex = Exercise(__file__)
HEADINGS = ["## Trả lời ngắn", "## So sánh baseline và model", "## Dữ liệu có sẵn lúc dự báo", "## Rủi ro và giới hạn",
            "## Đề xuất"]


@pytest.fixture(scope="module")
def nb():
    return ex.notebook("bike_demand.ipynb")


def tiny_hour():
    return pd.DataFrame({
        "dteday": pd.to_datetime(["2012-01-01", "2012-01-01", "2012-01-20", "2012-01-20", "2012-02-01", "2012-02-01",
                                  "2012-02-02"]),
        "hr":         [8, 9, 8, 9, 8, 9, 10],
        "workingday": [1, 1, 1, 0, 1, 0, 1],
        "cnt":        [100, 50, 300, 40, 999, 999, 999],
    }, index=[10, 11, 12, 13, 14, 15, 16])


def test_time_split(nb):
    hour = tiny_hour()
    before = hour.copy()
    train, test = nb.time_split(hour, "2012-02-01")
    pd.testing.assert_frame_equal(hour, before)
    assert list(train.index) == [10, 11, 12, 13] and list(test.index) == [14, 15, 16]
    for cutoff in ["2011-01-01", "2013-01-01"]:
        with pytest.raises(ValueError):
            nb.time_split(hour, cutoff)


def test_profile_baseline(nb):
    train, test = nb.time_split(tiny_hour(), "2012-02-01")
    pred = nb.profile_baseline(train, test)
    assert pred.name == "pred" and list(pred.index) == [14, 15, 16]
    # (1, 8): (100 + 300) / 2; (0, 9): 40; (1, 10) không có trong train → mean chung (100+50+300+40)/4
    assert pred.tolist() == pytest.approx([200.0, 40.0, 122.5])


def test_profile_baseline_recent_weeks(nb):
    train, test = nb.time_split(tiny_hour(), "2012-02-01")
    pred = nb.profile_baseline(train, test, weeks=1)       # chỉ dòng sau 2012-01-13: ngày 20/01
    assert pred.tolist() == pytest.approx([300.0, 40.0, 170.0])


def test_mae(nb):
    assert nb.mae([1, 2, 3], [2, 2, 5]) == pytest.approx(1.0)
    assert isinstance(nb.mae(pd.Series([1.0]), np.array([1.0])), float)
    for a, b in [([1, 2], [1]), ([], []), ([1.0, np.nan], [1.0, 2.0])]:
        with pytest.raises(ValueError):
            nb.mae(a, b)


def test_real_baseline(nb):
    hour = pd.read_csv(ex.dataset("bike-sharing-uci") / "hour.csv", parse_dates=["dteday"])
    train, test = nb.time_split(hour, "2012-10-01")
    assert len(train) == 15211 and len(test) == 2168
    assert nb.mae(test.cnt, nb.profile_baseline(train, test)) == pytest.approx(79.95, abs=0.01)
    assert nb.mae(test.cnt, nb.profile_baseline(train, test, weeks=8)) == pytest.approx(94.13, abs=0.01)


def test_memo_written():
    memo = ex.read("MEMO.md")
    assert "TODO" not in memo, "Còn dòng TODO trong MEMO.md"
    words = len(memo.split())
    assert 200 <= words <= 600, f"Memo hai phút: 200-600 từ, hiện có {words}"
    title = memo.strip().splitlines()[0]
    assert title.startswith("# ") and re.search(r"\d", title), "Dòng đầu là headline: kết luận có con số"
    for heading in HEADINGS:
        assert heading in memo, f"Thiếu mục {heading}"

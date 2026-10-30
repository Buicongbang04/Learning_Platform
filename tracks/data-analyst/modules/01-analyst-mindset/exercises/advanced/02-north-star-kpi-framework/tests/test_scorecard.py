import re

import numpy as np
import pandas as pd
import pytest

from testkit import Exercise

ex = Exercise(__file__)
METRICS = ["rides", "registered_rides", "rides_per_day", "registered_share", "bad_weather_days"]
FRAMEWORK_HEADINGS = ["## North star", "## Input metrics", "## Leading và lagging", "## Guardrails",
                      "## Metric tree", "## Nhịp xem và chủ sở hữu", "## Rủi ro game metric"]


@pytest.fixture(scope="module")
def nb():
    return ex.notebook("scorecard.ipynb")


def tiny_day():
    # 2021-01-01 .. 2022-01-10; cnt = 100 năm 2021, 150 năm 2022; vài ngày mưa
    dates = pd.date_range("2021-01-01", "2022-01-10", freq="D")
    cnt = np.where(dates.year == 2022, 150, 100)
    registered = np.where(dates.year == 2022, 120, 70)
    weathersit = np.ones(len(dates), dtype=int)
    weathersit[(dates >= "2021-01-03") & (dates <= "2021-01-04")] = 3
    weathersit[dates == "2022-01-05"] = 4
    weathersit[dates == "2022-01-06"] = 2
    return pd.DataFrame({"dteday": dates.strftime("%Y-%m-%d"), "weathersit": weathersit,
                         "casual": cnt - registered, "registered": registered, "cnt": cnt})


def test_scorecard_shape_and_windows(nb):
    day = tiny_day()
    before = day.copy()
    out = nb.kpi_scorecard(day, "2022-01-10", window=7)
    pd.testing.assert_frame_equal(day, before)
    assert list(out.index) == METRICS
    assert list(out.columns) == ["current", "previous", "change_pct"]
    # kỳ hiện tại 2022-01-04..10 (7 ngày, 150/ngày, 1 ngày mưa to); kỳ trước kết thúc 2021-01-11: 2021-01-05..11
    assert out["current"].tolist() == pytest.approx([1050, 840, 150, 0.8, 1])
    assert out["previous"].tolist() == pytest.approx([700, 490, 100, 0.7, 0])
    assert out.loc["rides", "change_pct"] == pytest.approx(0.5)
    assert out.loc["registered_share", "change_pct"] == pytest.approx(0.8 / 0.7 - 1)
    assert np.isnan(out.loc["bad_weather_days", "change_pct"])


def test_scorecard_default_window_and_bad_days(nb):
    out = nb.kpi_scorecard(tiny_day(), "2021-02-01")
    # 28 ngày 2021-01-05..02-01 (không có ngày mưa); kỳ trước 2020-01-07..02-03 không có dữ liệu nào
    assert out.loc["rides", "current"] == 2800
    assert out.loc["bad_weather_days", "current"] == 0
    out = nb.kpi_scorecard(tiny_day(), "2021-01-28")
    assert out.loc["bad_weather_days", "current"] == 2


def test_real_scorecard(nb):
    day = pd.read_csv(ex.dataset("bike-sharing-uci") / "day.csv")
    oct_ = nb.kpi_scorecard(day, "2012-10-31")
    assert oct_.loc["rides", "current"] == 179_852 and oct_.loc["rides", "previous"] == 113_566
    assert oct_.loc["registered_rides", "change_pct"] == pytest.approx(0.6340, abs=1e-4)
    assert oct_.loc["registered_share", "current"] == pytest.approx(0.8180, abs=1e-4)
    assert oct_.loc["bad_weather_days"].tolist()[:2] == [1, 3]
    sep = nb.kpi_scorecard(day, "2012-09-30")
    assert sep.loc["rides_per_day", "change_pct"] == pytest.approx(0.8205, abs=1e-4)


def framework_text():
    return ex.read("KPI_FRAMEWORK.md")


def test_framework_complete():
    text = framework_text()
    assert "TODO" not in text, "Còn dòng TODO trong KPI_FRAMEWORK.md"
    words = len(text.split())
    assert 300 <= words <= 900, f"300-900 từ, hiện có {words}"
    positions = [text.find(h) for h in FRAMEWORK_HEADINGS]
    missing = [h for h, p in zip(FRAMEWORK_HEADINGS, positions) if p < 0]
    assert not missing, f"Thiếu mục: {missing}"
    assert positions == sorted(positions), "Các mục phải theo đúng thứ tự của khung"


def test_framework_has_tree_and_numbers():
    text = framework_text()
    assert "TODO" not in text, "Còn dòng TODO trong KPI_FRAMEWORK.md"
    tree = text.split("## Metric tree", 1)[1].split("\n## ", 1)[0]
    assert "```mermaid" in tree, "Mục Metric tree cần một sơ đồ mermaid"
    north = text.split("## North star", 1)[1].split("\n## ", 1)[0]
    assert re.search(r"\d", north), "Mục North star cần giá trị hiện tại và so cùng kỳ (có con số)"
    guard = text.split("## Guardrails", 1)[1].split("\n## ", 1)[0]
    assert len([l for l in guard.splitlines() if re.match(r"\s*[-*] |\s*\|", l)]) >= 2, "Cần ít nhất 2 guardrail"

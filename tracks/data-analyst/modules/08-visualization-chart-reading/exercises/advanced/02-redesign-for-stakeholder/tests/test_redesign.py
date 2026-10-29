import re

import matplotlib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pytest
from matplotlib.figure import Figure
from matplotlib.patches import Wedge
from matplotlib.text import Annotation

from testkit import Exercise

ex = Exercise(__file__)
MEMO_HEADINGS = ["## Người đọc và câu hỏi", "## Trang mới", "## Chart cũ: giữ, đổi hay bỏ",
                 "## Kiểm tra năm giây", "## Giới hạn"]


@pytest.fixture(scope="module")
def nb():
    return ex.notebook("redesign.ipynb")


def test_yoy_by_month(nb):
    day = pd.DataFrame({
        "dteday": ["2020-01-01", "2020-01-02", "2020-02-01", "2021-01-05", "2021-02-10", "2021-02-11"],
        "cnt": [10, 20, 5, 60, 5, 10],
    })
    before = day.copy()
    out = nb.yoy_by_month(day)
    pd.testing.assert_frame_equal(day, before)
    assert list(out.columns) == ["prev", "curr", "growth"]
    assert list(out.index) == list(range(1, 13)) and out.index.name == "month"
    assert out.loc[1, ["prev", "curr", "growth"]].tolist() == pytest.approx([30, 60, 1.0])
    assert out.loc[2, ["prev", "curr", "growth"]].tolist() == pytest.approx([5, 15, 2.0])
    assert out.loc[3, "prev"] == 0 and out.loc[3, "curr"] == 0


def test_weather_effect_controls_for_month(nb):
    day = pd.DataFrame({
        "dteday": ["2020-01-01", "2020-01-02", "2020-01-03", "2020-01-04", "2020-02-01", "2020-02-02", "2020-03-01"],
        "weathersit": [1, 1, 2, 3, 1, 2, 3],
        "cnt": [100, 200, 75, 30, 50, 50, 10],
    })
    before = day.copy()
    out = nb.weather_effect(day)
    pd.testing.assert_frame_equal(day, before)
    assert out.name == "effect"
    assert list(out.index) == [1, 2, 3]
    # nền tháng 1 = 150, tháng 2 = 50; tháng 3 không có ngày quang nên ngày 1/3 bị bỏ
    assert out.tolist() == pytest.approx([0.0, (0.5 + 1.0) / 2 - 1, 0.2 - 1])


def synthetic_day():
    rng = np.random.default_rng(7)
    dates = pd.date_range("2021-01-01", "2022-12-31", freq="D")
    season = 1 + 0.6 * np.sin((dates.dayofyear - 100) / 365 * 2 * np.pi)
    growth = np.where(dates.year == 2022, 1.5, 1.0)
    weathersit = rng.choice([1, 2, 3], size=len(dates), p=[0.6, 0.3, 0.1])
    weather = np.select([weathersit == 1, weathersit == 2], [1.0, 0.85], 0.45)
    cnt = np.round(3000 * season * growth * weather * rng.uniform(0.9, 1.1, len(dates))).astype(int)
    casual = (cnt * 0.2).astype(int)
    return pd.DataFrame({"dteday": dates.strftime("%Y-%m-%d"), "season": (dates.month % 12 // 3) + 1,
                         "weathersit": weathersit, "temp": season / 2, "casual": casual,
                         "registered": cnt - casual, "cnt": cnt})


_PAGES = {}


def build(nb):
    """Vẽ trang một lần cho cả module; gọi trong thân test để starter FAIL (không ERROR ở fixture)."""
    if "fig" not in _PAGES:
        matplotlib.use("Agg")
        _PAGES["fig"] = nb.build_page(synthetic_day())
    return _PAGES["fig"]


@pytest.fixture(scope="module", autouse=True)
def close_pages():
    yield
    for fig in _PAGES.values():
        plt.close(fig)


def visible_axes(fig):
    return [ax for ax in fig.axes if ax.get_visible()]


def test_page_is_figure_with_headline(nb):
    page = build(nb)
    assert isinstance(page, Figure)
    headline = page._suptitle.get_text() if page._suptitle else ""
    assert headline.strip(), "Trang cần fig.suptitle là headline"
    assert re.search(r"\d", headline), "Headline là kết luận có con số"


def test_page_has_two_to_four_titled_charts(nb):
    page = build(nb)
    axes = visible_axes(page)
    assert 2 <= len(axes) <= 4, f"Một trang có 2-4 chart, hiện có {len(axes)}"
    for ax in axes:
        assert any(ax.get_title(loc).strip() for loc in ("left", "center", "right")), "Mỗi chart cần tiêu đề"


def test_page_has_no_pie_table_or_dual_axis(nb):
    page = build(nb)
    axes = visible_axes(page)
    assert not any(isinstance(p, Wedge) for ax in axes for p in ax.patches), "Không dùng pie"
    assert not any(ax.tables for ax in axes), "Không dán bảng số vào trang"
    boxes = [tuple(np.round(ax.get_position().bounds, 4)) for ax in axes]
    assert len(boxes) == len(set(boxes)), "Không dùng dual axis (twinx)"


def test_page_has_annotation(nb):
    page = build(nb)
    assert any(isinstance(t, Annotation) for ax in visible_axes(page) for t in ax.texts), "Cần ít nhất một annotation"


def test_real_numbers(nb):
    day = pd.read_csv(ex.dataset("bike-sharing-uci") / "day.csv")
    yoy = nb.yoy_by_month(day)
    assert yoy["prev"].sum() == 1_243_103 and yoy["curr"].sum() == 2_049_576
    assert yoy["growth"].idxmin() == 6 and yoy["growth"].idxmax() == 3
    assert yoy.loc[3, "growth"] == pytest.approx(1.5744, abs=1e-4)
    effect = nb.weather_effect(day)
    assert effect.loc[1] == pytest.approx(0.0, abs=1e-9)
    assert effect.loc[2] == pytest.approx(-0.1367, abs=1e-4)
    assert effect.loc[3] == pytest.approx(-0.5647, abs=1e-4)


def test_memo_written():
    memo = ex.read("MEMO.md")
    assert "TODO" not in memo, "Còn dòng TODO trong MEMO.md"
    words = len(memo.split())
    assert 150 <= words <= 500, f"Memo ngắn: 150-500 từ, hiện có {words}"
    title = memo.strip().splitlines()[0]
    assert title.startswith("# ") and re.search(r"\d", title), "Dòng đầu là headline của trang: kết luận có con số"
    for heading in MEMO_HEADINGS:
        assert heading in memo, f"Thiếu mục {heading}"

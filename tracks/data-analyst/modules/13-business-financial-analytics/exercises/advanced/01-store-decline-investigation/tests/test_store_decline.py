import re

import numpy as np
import pandas as pd
import pytest

from testkit import Exercise

ex = Exercise(__file__)
MEMO_HEADINGS = ["## Trả lời ngắn", "## Phân rã", "## Nguyên nhân theo nhóm cửa hàng", "## Việc cần làm",
                 "## Giới hạn"]
P0 = ("2014-01-01", "2014-01-04")
P1 = ("2015-01-01", "2015-01-04")


@pytest.fixture(scope="module")
def nb():
    return ex.notebook("store_decline.ipynb")


def tiny_train():
    rows = []
    # cửa hàng 1: 4 ngày mở mỗi kỳ; cửa hàng 2: kỳ sau đóng 1 ngày; cửa hàng 3 chỉ có kỳ 2015
    for date, store, sales, cust, open_ in [
        ("2014-01-01", 1, 100, 10, 1), ("2014-01-02", 1, 100, 10, 1), ("2014-01-03", 1, 100, 10, 1),
        ("2014-01-04", 1, 100, 10, 1), ("2014-01-05", 1, 999, 99, 1),
        ("2015-01-01", 1, 110, 10, 1), ("2015-01-02", 1, 110, 10, 1), ("2015-01-03", 1, 110, 10, 1),
        ("2015-01-04", 1, 110, 10, 1),
        ("2014-01-01", 2, 200, 20, 1), ("2014-01-02", 2, 200, 20, 1), ("2014-01-03", 2, 200, 20, 1),
        ("2014-01-04", 2, 200, 20, 1),
        ("2015-01-01", 2, 0, 0, 0), ("2015-01-02", 2, 180, 15, 1), ("2015-01-03", 2, 180, 15, 1),
        ("2015-01-04", 2, 180, 15, 1),
        ("2015-01-01", 3, 50, 5, 1),
    ]:
        rows.append({"Store": store, "Date": pd.Timestamp(date), "Sales": sales, "Customers": cust, "Open": open_})
    return pd.DataFrame(rows)


def test_store_yoy(nb):
    tr = tiny_train()
    before = tr.copy()
    out = nb.store_yoy(tr, P0, P1)
    pd.testing.assert_frame_equal(tr, before)
    assert list(out.columns) == ["sales0", "sales1", "open_days0", "open_days1", "customers0", "customers1",
                                 "growth", "days_growth", "traffic_growth", "spc_growth"]
    assert list(out.index) == [1, 2]
    assert out.loc[1, ["sales0", "sales1"]].tolist() == [400, 440]      # ngày 05/01/2014 nằm ngoài kỳ
    assert out.loc[1, "growth"] == pytest.approx(0.10)
    assert out.loc[1, "spc_growth"] == pytest.approx(0.10)
    s2 = out.loc[2]
    assert s2["growth"] == pytest.approx(540 / 800 - 1)
    assert s2["days_growth"] == pytest.approx(-0.25)
    assert s2["traffic_growth"] == pytest.approx(15 / 20 - 1)
    assert s2["spc_growth"] == pytest.approx(12 / 10 - 1)
    product = (1 + out["days_growth"]) * (1 + out["traffic_growth"]) * (1 + out["spc_growth"])
    assert product.tolist() == pytest.approx((1 + out["growth"]).tolist())


def tiny_stores():
    nan = np.nan
    return pd.DataFrame({
        "Store": [7, 1, 2, 3, 4, 5, 6],
        "CompetitionOpenSinceMonth": [12.0, 5.0, 1.0, 1.0, 7.0, 1.0, nan],
        "CompetitionOpenSinceYear": [2015.0, 2010.0, 2014.0, 2015.0, 2014.0, 2015.0, 2012.0],
    })


def test_competition_timing(nb):
    st = tiny_stores()
    before = st.copy()
    out = nb.competition_timing(st, ("2014-01-01", "2014-06-30"), ("2015-01-01", "2015-06-30"))
    pd.testing.assert_frame_equal(st, before)
    assert out.name == "competition"
    assert list(out.index) == [1, 2, 3, 4, 5, 6, 7]
    assert out.tolist() == ["before_p0", "during_p0", "during_p1", "between", "during_p1", "unknown", "after_p1"]


def test_group_growth(nb):
    yoy = pd.DataFrame({"sales0": [100.0, 100.0, 300.0, 50.0], "sales1": [80.0, 110.0, 330.0, 60.0]},
                       index=pd.Index([1, 2, 3, 4], name="Store"))
    yoy["growth"] = yoy["sales1"] / yoy["sales0"] - 1
    labels = pd.Series(["x", "x", "y", "z"], index=pd.Index([1, 2, 3, 9], name="Store"), name="grp")
    out = nb.group_growth(yoy, labels)
    assert list(out.columns) == ["stores", "sales0", "sales1", "growth", "median_growth", "share_below_10"]
    assert out.index.name == "grp"
    assert list(out.index) == ["x", "y"]                 # cửa hàng 4 không có nhãn, nhãn z không có cửa hàng
    assert out.loc["x", "stores"] == 2
    assert out.loc["x", "growth"] == pytest.approx(-0.05)
    assert out.loc["x", "median_growth"] == pytest.approx(-0.05)
    assert out.loc["x", "share_below_10"] == pytest.approx(0.5)
    assert out.loc["y", "growth"] == pytest.approx(0.10)


_D = {}


def real(nb):
    if not _D:
        root = ex.dataset("store-sales")
        train = pd.read_csv(root / "train.csv", parse_dates=["Date"], dtype={"StateHoliday": str})
        stores = pd.read_csv(root / "store.csv")
        p0, p1 = ("2014-01-01", "2014-06-30"), ("2015-01-01", "2015-06-30")
        _D["yoy"] = nb.store_yoy(train, p0, p1)
        _D["timing"] = nb.competition_timing(stores, p0, p1)
    return _D["yoy"], _D["timing"]


def test_real_yoy(nb):
    yoy, _ = real(nb)
    assert len(yoy) == 1115
    assert yoy["sales1"].sum() / yoy["sales0"].sum() - 1 == pytest.approx(0.03353, abs=1e-5)
    decliners = yoy[yoy["growth"] < -0.10]
    assert len(decliners) == 33
    assert decliners["growth"].idxmin() == 91
    assert (decliners["traffic_growth"] < -0.10).sum() == 30
    assert yoy.loc[674, "open_days1"] == 115


def test_real_competition_groups(nb):
    yoy, timing = real(nb)
    assert timing.value_counts().to_dict() == {"before_p0": 653, "unknown": 354, "between": 39, "during_p0": 31,
                                               "during_p1": 27, "after_p1": 11}
    groups = nb.group_growth(yoy, timing)
    assert list(groups.index[:2]) == ["during_p0", "between"]
    assert groups.loc["between", "growth"] == pytest.approx(-0.0390, abs=1e-4)
    assert groups.loc["before_p0", "growth"] == pytest.approx(0.0376, abs=1e-4)


def test_memo_written():
    memo = ex.read("MEMO.md")
    assert "TODO" not in memo, "Còn dòng TODO trong MEMO.md"
    words = len(memo.split())
    assert 200 <= words <= 600, f"Memo một trang: 200-600 từ, hiện có {words}"
    title = memo.strip().splitlines()[0]
    assert title.startswith("# ") and re.search(r"\d", title), "Dòng đầu là headline: kết luận có con số"
    for heading in MEMO_HEADINGS:
        assert heading in memo, f"Thiếu mục {heading}"

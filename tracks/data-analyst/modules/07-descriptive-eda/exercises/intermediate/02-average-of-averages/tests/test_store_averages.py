import pandas as pd
import pytest

from testkit import Exercise

ex = Exercise(__file__)


@pytest.fixture(scope="module")
def nb():
    return ex.notebook("store_averages.ipynb")


def tiny_train():
    # cửa hàng 1: đủ 4 ngày 01..04/01 (ngày 03 đóng cửa); cửa hàng 2: thiếu ngày 02; cửa hàng 3: đủ 4 ngày
    rows = [
        (1, "2015-01-01", 100, 10, 1), (1, "2015-01-02", 300, 20, 1), (1, "2015-01-03", 0, 0, 0), (1, "2015-01-04", 200, 20, 1),
        (2, "2015-01-01", 1000, 50, 1), (2, "2015-01-03", 1000, 100, 1), (2, "2015-01-04", 0, 0, 1),
        (3, "2015-01-01", 50, 5, 1), (3, "2015-01-02", 70, 10, 1), (3, "2015-01-03", 90, 10, 1), (3, "2015-01-04", 0, 0, 0),
    ]
    out = pd.DataFrame(rows, columns=["Store", "Date", "Sales", "Customers", "Open"])
    out["Type"] = out.Store.map({1: "x", 2: "y", 3: "x"})
    return out


def test_open_days(nb):
    tr = tiny_train()
    before = tr.copy()
    out = nb.open_days(tr)
    pd.testing.assert_frame_equal(tr, before)
    assert len(out) == 8                                                  # 11 dòng, bỏ 2 ngày đóng cửa và 1 dòng mở cửa doanh số 0
    assert (out.Sales > 0).all() and (out.Open == 1).all()
    assert list(out.columns) == list(tr.columns)


def test_full_coverage_stores(nb):
    tr = tiny_train()
    assert nb.full_coverage_stores(tr, "2015-01-01", "2015-01-04") == [1, 3]
    assert nb.full_coverage_stores(tr, "2015-01-03", "2015-01-04") == [1, 2, 3]
    tr_dt = tr.assign(Date=pd.to_datetime(tr.Date))
    assert nb.full_coverage_stores(tr_dt, "2015-01-01", "2015-01-05") == []   # chưa ai có ngày 05


def test_full_coverage_counts_dates_not_rows(nb):
    tr = tiny_train()
    dup = pd.concat([tr, tr[(tr.Store == 2) & (tr.Date == "2015-01-01")]])  # dòng lặp không bù được ngày thiếu
    assert nb.full_coverage_stores(dup, "2015-01-01", "2015-01-04") == [1, 3]


def test_mean_two_ways(nb):
    days = nb.open_days(tiny_train())
    out = nb.mean_two_ways(days, "Type")
    assert list(out.columns) == ["n_rows", "n_units", "row_mean", "unit_mean"]
    assert out.index.name == "Type"
    # x: cửa hàng 1 có 100, 300, 200 (mean 200); cửa hàng 3 có 50, 70, 90 (mean 70)
    assert out.loc["x", ["n_rows", "n_units"]].tolist() == [6, 2]
    assert out.loc["x", "row_mean"] == pytest.approx(810 / 6)
    assert out.loc["x", "unit_mean"] == pytest.approx((200 + 70) / 2)
    assert out.loc["y", "row_mean"] == pytest.approx(1000)


def test_mean_two_ways_unequal_days(nb):
    df = pd.DataFrame({"g": ["a"] * 4, "Store": [1, 1, 1, 2], "Sales": [10.0, 10.0, 10.0, 50.0]})
    out = nb.mean_two_ways(df, "g")
    assert out.loc["a", "row_mean"] == pytest.approx(20.0)
    assert out.loc["a", "unit_mean"] == pytest.approx(30.0)


def test_ratio_two_ways(nb):
    tr = tiny_train()
    out = nb.ratio_two_ways(tr, "Type")
    assert list(out.columns) == ["pooled", "mean_of_ratios"]
    assert out.index.name == "Type"
    # x (Customers > 0): 100/10, 300/20, 200/20, 50/5, 70/10, 90/10 → tổng 810/75
    assert out.loc["x", "pooled"] == pytest.approx(810 / 75)
    assert out.loc["x", "mean_of_ratios"] == pytest.approx((10 + 15 + 10 + 10 + 7 + 9) / 6)
    assert out.loc["y", "pooled"] == pytest.approx(2000 / 150)          # dòng Customers = 0 bị bỏ


def test_functions_do_not_mutate_input(nb):
    tr = tiny_train()
    before = tr.copy()
    nb.full_coverage_stores(tr, "2015-01-01", "2015-01-04")
    nb.mean_two_ways(tr, "Type")
    nb.ratio_two_ways(tr, "Type")
    pd.testing.assert_frame_equal(tr, before)


@pytest.fixture(scope="module")
def real_train():
    return pd.read_csv(ex.dataset("store-sales") / "train.csv", dtype={"StateHoliday": str}, parse_dates=["Date"])


def test_real_coverage(nb, real_train):
    assert len(nb.full_coverage_stores(real_train, "2013-01-01", "2015-07-31")) == 934
    panel = nb.full_coverage_stores(real_train, "2013-07-01", "2014-12-31")
    assert len(panel) == 935 and 988 in panel


def test_real_half_year(nb, real_train):
    days = nb.open_days(real_train)
    assert len(days) == 844_338
    period = pd.Series("khác", index=days.index)
    period[days.Date.between("2013-07-01", "2013-12-31")] = "2013H2"
    period[days.Date.between("2014-07-01", "2014-12-31")] = "2014H2"
    half = days.assign(period=period)[period != "khác"]
    m = nb.mean_two_ways(half, "period")
    assert m.n_units.tolist() == [1115, 935]
    assert m.loc["2014H2", "row_mean"] / m.loc["2013H2", "row_mean"] - 1 == pytest.approx(0.0341, abs=1e-4)
    panel = nb.full_coverage_stores(real_train, "2013-07-01", "2014-12-31")
    mb = nb.mean_two_ways(half[half.Store.isin(panel)], "period")
    assert mb.loc["2014H2", "row_mean"] / mb.loc["2013H2", "row_mean"] - 1 == pytest.approx(0.0266, abs=1e-4)


def test_real_store_type_ratios(nb, real_train):
    stores = pd.read_csv(ex.dataset("store-sales") / "store.csv")
    days = nb.open_days(real_train).merge(stores[["Store", "StoreType"]], on="Store")
    r = nb.ratio_two_ways(days, "StoreType")
    assert r.loc["b", "pooled"] == pytest.approx(5.0605, abs=1e-4)
    assert r.loc["d", "pooled"] == pytest.approx(11.2514, abs=1e-4)
    m = nb.mean_two_ways(days, "StoreType")
    assert m.loc["b", "n_units"] == 17
    assert m.loc["b", "unit_mean"] == pytest.approx(10112.31, abs=0.01)

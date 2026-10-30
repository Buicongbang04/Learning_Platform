import numpy as np
import pandas as pd
import pytest

from testkit import Exercise

ex = Exercise(__file__)
COLUMNS = ["revenue", "known_revenue", "guest_revenue", "customers", "orders", "frequency", "aov"]


@pytest.fixture(scope="module")
def nb():
    return ex.notebook("revenue_tree.ipynb")


def tiny_tx():
    # Invoice trộn int và str như khi đọc từ Excel; một hoá đơn huỷ, một dòng giá 0, một dòng số lượng âm
    return pd.DataFrame({
        "Invoice": [1001, 1001, 1002, 1003, "C1004", 1005, 2001, 2002, 2002, 2003, 2004, 2005],
        "InvoiceDate": pd.to_datetime([
            "2011-01-03 09:00", "2011-01-03 09:00", "2011-01-10 10:00", "2011-01-20 11:00", "2011-01-21 12:00",
            "2011-01-31 23:00",
            "2011-02-01 08:00", "2011-02-05 09:00", "2011-02-05 09:00", "2011-02-14 10:00", "2011-02-20 15:00",
            "2011-02-28 16:00",
        ]),
        "Quantity": [10, 5, 4, 2, -3, 1, 6, 10, -1, 3, 2, 8],
        "Price": [2.0, 4.0, 5.0, 10.0, 5.0, 0.0, 5.0, 3.0, 3.0, 10.0, 25.0, 5.0],
        "Customer ID": [1.0, 1.0, 1.0, 2.0, 2.0, 3.0, 1.0, 2.0, 2.0, 3.0, 4.0, np.nan],
    })


def test_monthly_tree_columns_and_values(nb):
    tree = nb.monthly_tree(tiny_tx())
    assert list(tree.columns) == COLUMNS
    assert list(tree.index) == list(pd.to_datetime(["2011-01-01", "2011-02-01"]))
    assert tree.index.name == "month"
    jan, feb = tree.iloc[0], tree.iloc[1]
    # tháng 1: hoá đơn 1001 (20 + 20), 1002 (20), 1003 (20); C1004 và dòng giá 0 bị bỏ; không có khách vãng lai
    assert jan[["revenue", "known_revenue", "guest_revenue"]].tolist() == pytest.approx([80.0, 80.0, 0.0])
    assert jan[["customers", "orders"]].tolist() == [2, 3]
    assert jan[["frequency", "aov"]].tolist() == pytest.approx([1.5, 80 / 3])
    # tháng 2: 2001 (30), 2002 (30, bỏ dòng -1), 2003 (30), 2004 (50) có mã; 2005 (40) không mã
    assert feb[["revenue", "known_revenue", "guest_revenue"]].tolist() == pytest.approx([180.0, 140.0, 40.0])
    assert feb[["customers", "orders"]].tolist() == [4, 4]
    assert feb[["frequency", "aov"]].tolist() == pytest.approx([1.0, 35.0])


def test_monthly_tree_identity_and_no_mutation(nb):
    tx = tiny_tx()
    before = tx.copy()
    tree = nb.monthly_tree(tx)
    pd.testing.assert_frame_equal(tx, before)
    product = tree["customers"] * tree["frequency"] * tree["aov"]
    assert product.tolist() == pytest.approx(tree["known_revenue"].tolist())


def test_monthly_tree_month_without_known_customer(nb):
    tx = pd.DataFrame({
        "Invoice": ["10", "11"], "InvoiceDate": pd.to_datetime(["2011-03-02", "2011-04-02"]),
        "Quantity": [2, 1], "Price": [10.0, 7.0], "Customer ID": [np.nan, 9.0],
    })
    tree = nb.monthly_tree(tx)
    march = tree.loc[pd.Timestamp("2011-03-01")]
    assert march[["revenue", "known_revenue", "guest_revenue", "customers", "orders"]].tolist() == pytest.approx(
        [20.0, 0.0, 20.0, 0, 0])


def make_tree():
    return pd.DataFrame({
        "revenue": [1000.0, 1500.0, 1300.0],
        "known_revenue": [800.0, 1200.0, 800.0],
        "guest_revenue": [200.0, 300.0, 500.0],
        "customers": [10, 15, 8],
        "orders": [20, 24, 16],
        "frequency": [2.0, 1.6, 2.0],
        "aov": [40.0, 50.0, 50.0],
    }, index=pd.DatetimeIndex(pd.to_datetime(["2011-01-01", "2011-02-01", "2011-03-01"]), name="month"))


def test_decompose_lmdi_sums_to_change(nb):
    tree = make_tree()
    out = nb.decompose(tree, "2011-01-01", "2011-02-01")
    assert out.name == "contribution"
    assert list(out.index) == ["customers", "frequency", "aov", "guest"]
    weight = (1200 - 800) / (np.log(1200) - np.log(800))
    expected = [weight * np.log(1.5), weight * np.log(0.8), weight * np.log(1.25), 100.0]
    assert out.tolist() == pytest.approx(expected)
    assert out.sum() == pytest.approx(500.0)


def test_decompose_when_known_revenue_unchanged(nb):
    tree = make_tree()
    out = nb.decompose(tree, "2011-01-01", "2011-03-01")
    # known_revenue 800 -> 800: L = 800; customers 10 -> 8, frequency 2 -> 2, aov 40 -> 50
    assert out.tolist() == pytest.approx([800 * np.log(0.8), 0.0, 800 * np.log(1.25), 300.0])
    assert out.sum() == pytest.approx(300.0)


@pytest.fixture(scope="module")
def real_tx():
    path = ex.dataset("online-retail-ii") / "online_retail_II.xlsx"
    return pd.read_excel(path, sheet_name="Year 2010-2011")      # xlsx: đọc một lần cho cả module


_TREE = {}


def real_tree(nb, real_tx):
    """Tính cây một lần; gọi trong thân test để starter FAIL chứ không ERROR."""
    if "tree" not in _TREE:
        _TREE["tree"] = nb.monthly_tree(real_tx)
    return _TREE["tree"]


def test_real_tree(nb, real_tx):
    tree = real_tree(nb, real_tx)
    assert len(tree) == 13
    assert tree["revenue"].sum() == pytest.approx(10_666_702.54, abs=1)
    assert tree["known_revenue"].sum() / tree["revenue"].sum() == pytest.approx(0.8354, abs=1e-4)
    nov = tree.loc[pd.Timestamp("2011-11-01")]
    assert nov["customers"] == 1664 and nov["orders"] == 2657
    assert nov["guest_revenue"] == pytest.approx(347_679.0, abs=1)


def test_real_decompose_oct_nov(nb, real_tx):
    out = nb.decompose(real_tree(nb, real_tx), "2011-10-01", "2011-11-01")
    assert out.sum() == pytest.approx(354_517.03, abs=1)
    assert out.tolist() == pytest.approx([218_569.93, 133_463.38, -229_534.72, 232_018.44], abs=1)


def test_real_decompose_dec_jan(nb, real_tx):
    out = nb.decompose(real_tree(nb, real_tx), "2010-12-01", "2011-01-01")
    assert out.tolist() == pytest.approx([-101_416.02, -98_208.53, 196_355.70, -129_112.73], abs=1)

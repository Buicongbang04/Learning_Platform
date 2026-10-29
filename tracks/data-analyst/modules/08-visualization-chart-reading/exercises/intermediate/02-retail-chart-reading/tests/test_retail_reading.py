import pandas as pd
import pytest

from testkit import Exercise

ex = Exercise(__file__)


@pytest.fixture(scope="module")
def nb():
    return ex.notebook("retail_reading.ipynb")


def tiny_tx():
    # tháng 2 không có giao dịch hợp lệ nào (chỉ một hoá đơn huỷ): phải hiện với doanh thu 0 và 0 ngày
    return pd.DataFrame({
        "Invoice": [536365, 536365, 536366, "C536379", 536367, 536368, 536369, 536370, "C540001", 536371],
        "InvoiceDate": pd.to_datetime([
            "2011-01-04 08:26", "2011-01-04 08:26", "2011-01-04 17:00", "2011-01-05 09:41", "2011-01-31 23:59",
            "2011-03-01 00:00", "2011-03-01 10:00", "2011-03-15 12:00", "2011-02-10 10:00", "2011-03-20 09:00",
        ]),
        "Quantity": [6, -2, 10, -1, 1, 4, 2, 5, 3, 7],
        "Price": [2.5, 2.5, 1.0, 4.0, 100.0, 0.5, 3.0, 0.0, 9.0, 1.0],
        "Country": ["United Kingdom", "United Kingdom", "France", "United Kingdom", "Germany",
                    "United Kingdom", "EIRE", "France", "Germany", "United Kingdom"],
    })


def test_monthly_revenue_cleans_and_fills_empty_month(nb):
    out = nb.monthly_revenue(tiny_tx())
    assert list(out.index) == list(pd.date_range("2011-01-01", "2011-03-01", freq="MS"))
    # tháng 1: 6*2.5 + 10*1 + 1*100 (bỏ dòng -2, hoá đơn C); tháng 2: chỉ có đơn huỷ; tháng 3: 4*0.5 + 2*3 + 7*1
    assert out.tolist() == pytest.approx([125.0, 0.0, 15.0])


def test_monthly_revenue_does_not_mutate_input(nb):
    tx = tiny_tx()
    before = tx.copy()
    nb.monthly_revenue(tx)
    pd.testing.assert_frame_equal(tx, before)


def test_country_share_top_and_other(nb):
    out = nb.country_share(tiny_tx(), top=2)
    # doanh thu hợp lệ: UK 15+2+7=24, Germany 100, France 10, EIRE 6; tổng 140
    assert list(out.index) == ["Germany", "United Kingdom", "Other"]
    assert out.tolist() == pytest.approx([100 / 140, 24 / 140, 16 / 140])
    assert out.sum() == pytest.approx(1.0)


def test_country_share_without_remainder_has_no_other(nb):
    out = nb.country_share(tiny_tx(), top=10)
    assert "Other" not in out.index
    assert list(out.index) == ["Germany", "United Kingdom", "France", "EIRE"]
    assert out.sum() == pytest.approx(1.0)


def test_country_share_does_not_mutate_input(nb):
    tx = tiny_tx()
    before = tx.copy()
    nb.country_share(tx, top=1)
    pd.testing.assert_frame_equal(tx, before)


def test_month_coverage_counts_distinct_days(nb):
    out = nb.month_coverage(tiny_tx())
    assert list(out.index) == list(pd.date_range("2011-01-01", "2011-03-01", freq="MS"))
    # tháng 1: ngày 4 và 31 (ngày 5 chỉ có đơn huỷ); tháng 3: ngày 1 và 20 (ngày 15 giá 0 bị loại)
    assert out.tolist() == [2, 0, 2]


@pytest.fixture(scope="module")
def real_tx():
    path = ex.dataset("online-retail-ii") / "online_retail_II.xlsx"
    return pd.read_excel(path, sheet_name="Year 2010-2011")      # xlsx: đọc một lần cho cả module


def test_real_monthly_revenue(nb, real_tx):
    rev = nb.monthly_revenue(real_tx)
    assert len(rev) == 13
    assert rev.index[0] == pd.Timestamp("2010-12-01") and rev.index[-1] == pd.Timestamp("2011-12-01")
    assert rev.sum() == pytest.approx(10_666_702.54, abs=1)
    assert rev.idxmax() == pd.Timestamp("2011-11-01")
    assert rev.max() == pytest.approx(1_509_496.33, abs=1)


def test_real_country_share(nb, real_tx):
    share = nb.country_share(real_tx, top=5)
    assert list(share.index) == ["United Kingdom", "Netherlands", "EIRE", "Germany", "France", "Other"]
    assert share["United Kingdom"] == pytest.approx(0.8461, abs=1e-4)
    assert share.sum() == pytest.approx(1.0)


def test_real_month_coverage(nb, real_tx):
    days = nb.month_coverage(real_tx)
    assert days[pd.Timestamp("2011-12-01")] == 8
    assert days[pd.Timestamp("2010-12-01")] == 20
    assert days[pd.Timestamp("2011-11-01")] == 26

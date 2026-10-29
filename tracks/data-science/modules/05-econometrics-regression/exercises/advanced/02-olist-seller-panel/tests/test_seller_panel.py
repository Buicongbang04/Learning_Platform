import numpy as np
import pandas as pd
import pytest

from testkit import ROOT, Exercise

ex = Exercise(__file__)


@pytest.fixture(scope="module")
def nb():
    return ex.notebook("seller_panel.ipynb")


def ts(values):
    return pd.to_datetime(values)


def fixture_tables():
    """Seller A: 3 tháng (01: 2 đơn, 02: 2 đơn, 03: 1 đơn). Seller B: 1 tháng. Các đơn bẫy ở cuối."""
    oid = ["a1", "a2", "a3", "a4", "a5", "b1", "b2", "m1", "c1", "x1", "x2"]
    orders = pd.DataFrame({
        "order_id": oid,
        "order_status": ["delivered"] * 8 + ["canceled", "delivered", "delivered"],
        "order_purchase_timestamp": ts(["2017-01-03", "2017-01-20", "2017-02-02", "2017-02-25", "2017-03-05",
                                        "2017-01-10", "2017-01-11", "2017-01-12", "2017-01-13",
                                        "2016-12-30", "2017-01-15"]),
        "order_delivered_customer_date": ts(["2017-01-10", "2017-02-05", "2017-02-08", "2017-03-09", "2017-03-10",
                                             "2017-01-15", "2017-01-20", "2017-01-20", None,
                                             "2017-01-05", None]),
        "order_estimated_delivery_date": ts(["2017-01-15", "2017-02-01", "2017-02-20", "2017-03-09", "2017-03-20",
                                             "2017-01-20", "2017-01-25", "2017-01-25", "2017-01-25",
                                             "2017-01-10", "2017-01-30"]),
    })
    # a4 giao 2017-03-09 00:00 = ngày hẹn 00:00 -> không trễ; a2 trễ
    reviews = pd.DataFrame({
        "order_id": ["a1", "a2", "a2", "a3", "a4", "a5", "b1", "b2", "m1", "c1", "x1"],
        "review_score": [5, 5, 1, 2, 4, 1, 3, 1, 1, 1, 1],
        "review_answer_timestamp": ts(["2017-01-11", "2017-02-06", "2017-02-10", "2017-02-09", "2017-03-10",
                                       "2017-03-11", "2017-01-16", "2017-01-21", "2017-01-21", "2017-01-26",
                                       "2017-01-06"]),
    })
    items = pd.DataFrame({
        "order_id": ["a1", "a2", "a3", "a4", "a5", "b1", "b2", "m1", "m1", "c1", "x1", "x2"],
        "seller_id": ["A", "A", "A", "A", "A", "B", "B", "A", "B", "A", "A", "A"],
    })
    return orders, reviews, items


def test_panel_cells_and_rates(nb):
    orders, reviews, items = fixture_tables()
    p = nb.seller_month_panel(orders, reviews, items, start="2017-01-01", end="2017-04-01",
                              min_orders=1, min_months=1)
    assert list(p.columns) == ["seller_id", "month", "n_orders", "late_rate", "bad_rate"]
    assert list(p.index) == list(range(len(p)))
    p = p.set_index(["seller_id", "month"])
    jan, feb, mar = pd.Timestamp("2017-01-01"), pd.Timestamp("2017-02-01"), pd.Timestamp("2017-03-01")
    # m1 có 2 seller, c1 huỷ, x1 trước start, x2 chưa giao -> không tính
    assert set(p.index) == {("A", jan), ("A", feb), ("A", mar), ("B", jan)}
    assert p.loc[("A", jan), "n_orders"] == 2
    assert p.loc[("A", jan), "late_rate"] == pytest.approx(0.5)      # a2 trễ
    assert p.loc[("A", jan), "bad_rate"] == pytest.approx(0.5)       # a2: review mới nhất 1 sao
    assert p.loc[("A", feb), "late_rate"] == pytest.approx(0.0)      # a4 giao đúng 00:00 ngày hẹn
    assert p.loc[("A", feb), "bad_rate"] == pytest.approx(0.5)       # a3: 2 sao
    assert p.loc[("B", jan), "bad_rate"] == pytest.approx(0.5)


def test_panel_filters_in_order(nb):
    orders, reviews, items = fixture_tables()
    p = nb.seller_month_panel(orders, reviews, items, start="2017-01-01", end="2017-04-01",
                              min_orders=2, min_months=2)
    # ô >= 2 đơn: A-01, A-02, B-01; seller còn >= 2 tháng: chỉ A
    assert list(p.seller_id) == ["A", "A"]
    assert list(p.month) == [pd.Timestamp("2017-01-01"), pd.Timestamp("2017-02-01")]


def simulate(seed: int, n_sellers: int = 300, n_months: int = 12) -> pd.DataFrame:
    """Seller kém (q cao) và tháng cao điểm (m cao) làm cả late_rate lẫn bad_rate tăng. Hệ số thật 0.45."""
    rng = np.random.default_rng(seed)
    q = np.repeat(rng.normal(0, 1, n_sellers), n_months)
    m = np.tile(rng.normal(0, 1, n_months), n_sellers)
    late = 0.10 + 0.04 * q + 0.04 * m + rng.normal(0, 0.06, len(q))
    bad = 0.08 + 0.45 * late + 0.03 * q + 0.03 * m + rng.normal(0, 0.05, len(q))
    return pd.DataFrame({
        "seller_id": np.repeat([f"s{i}" for i in range(n_sellers)], n_months),
        "month": np.tile(pd.date_range("2017-01-01", periods=n_months, freq="MS"), n_sellers),
        "n_orders": 10, "late_rate": late, "bad_rate": bad,
    })


@pytest.mark.parametrize("seed", [0, 1, 2])
def test_fit_specs_on_simulation(nb, seed):
    out = nb.fit_specs(simulate(seed))
    assert list(out.index) == ["pooled", "seller_fe", "twfe"]
    assert list(out.columns) == ["coef", "se"]
    assert out.loc["twfe", "coef"] == pytest.approx(0.45, abs=0.03)
    assert out.loc["pooled", "coef"] > 0.45 + 0.15
    assert out.loc["pooled", "coef"] > out.loc["seller_fe", "coef"] > out.loc["twfe", "coef"]
    assert (out.se > 0).all()


def test_real_olist(nb):
    raw = ROOT / "data" / "raw"
    if not (raw / "olist_orders_dataset.csv").exists():
        pytest.skip("Chưa tải Olist thật: uv run python data/download_olist.py")
    orders = pd.read_csv(raw / "olist_orders_dataset.csv", parse_dates=[
        "order_purchase_timestamp", "order_delivered_customer_date", "order_estimated_delivery_date"])
    reviews = pd.read_csv(raw / "olist_order_reviews_dataset.csv", parse_dates=["review_answer_timestamp"])
    items = pd.read_csv(raw / "olist_order_items_dataset.csv")
    p = nb.seller_month_panel(orders, reviews, items)
    assert len(p) == 3322 and p.seller_id.nunique() == 313
    out = nb.fit_specs(p)
    assert out.loc["twfe", "coef"] == pytest.approx(0.478, abs=0.005)
    assert out.loc["pooled", "coef"] > out.loc["twfe", "coef"]


def test_report_written():
    report = ex.read("REPORT.md")
    assert "TODO" not in report
    assert len(report.split()) >= 300

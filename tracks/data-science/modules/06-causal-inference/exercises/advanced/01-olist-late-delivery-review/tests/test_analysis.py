import numpy as np
import pandas as pd
import pytest

from testkit import ROOT, Exercise

ex = Exercise(__file__)

NUMERIC = ["promised_days", "log_freight", "log_price", "n_items", "same_state"]
CATEGORICAL = ["customer_state", "purchase_month"]

ORDERS = pd.DataFrame({
    "order_id": ["o1", "o2", "o3", "o4", "o5", "o6"],
    "customer_id": ["c1", "c2", "c3", "c4", "c5", "c6"],
    "order_status": ["delivered", "delivered", "delivered", "canceled", "delivered", "delivered"],
    "order_purchase_timestamp": pd.to_datetime([
        "2018-01-02 10:00", "2018-01-05 00:00", "2018-01-06 00:00", "2018-01-07 00:00", "2018-01-08 00:00",
        "2018-01-20 08:00"]),
    "order_delivered_customer_date": pd.to_datetime([
        "2018-01-10 12:00", "2018-01-20 06:00", None, None, "2018-01-12 00:00", "2018-02-01 15:00"]),
    "order_estimated_delivery_date": pd.to_datetime([
        "2018-01-15", "2018-01-18", "2018-01-20", "2018-01-25", "2018-01-30", "2018-02-01"]),
})
REVIEWS = pd.DataFrame({
    "order_id": ["o1", "o1", "o2", "o4", "o6"],
    "review_score": [1, 5, 2, 1, 4],
    "review_answer_timestamp": pd.to_datetime(["2018-01-11", "2018-01-14", "2018-01-21", "2018-01-26", "2018-02-02"]),
})
ITEMS = pd.DataFrame({
    "order_id": ["o1", "o2", "o6", "o6", "o5"],
    "order_item_id": [1, 1, 2, 1, 1],
    "seller_id": ["s1", "s2", "s1", "s2", "s1"],
    "price": [100.0, 50.0, 70.0, 30.0, 10.0],
    "freight_value": [10.0, 20.0, 5.0, 5.0, 1.0],
})
CUSTOMERS = pd.DataFrame({"customer_id": [f"c{i}" for i in range(1, 7)],
                          "customer_state": ["SP", "SP", "RJ", "MG", "SP", "SP"]})
SELLERS = pd.DataFrame({"seller_id": ["s1", "s2"], "seller_state": ["RJ", "SP"]})


@pytest.fixture(scope="module")
def nb():
    return ex.notebook("analysis.ipynb")


def test_build_orders_small(nb):
    out = nb.build_orders(ORDERS, REVIEWS, ITEMS, CUSTOMERS, SELLERS).set_index("order_id").sort_index()
    assert list(out.index) == ["o1", "o2", "o6"]          # bỏ đơn chưa giao, đơn huỷ, đơn không review
    assert list(out.late) == [0, 1, 1]                    # o6 giao 15:00 đúng ngày hẹn vẫn là trễ
    assert list(out.bad_review) == [0, 1, 0]              # o1: giữ review mới nhất (5 sao)
    assert out.days_late.to_numpy() == pytest.approx([-4.5, 2.25, 0.625])
    assert out.promised_days.to_numpy() == pytest.approx([12 + 14 / 24, 13.0, 11 + 16 / 24])
    assert list(out.n_items) == [1, 1, 2]
    assert out.log_price.to_numpy() == pytest.approx(np.log1p([100.0, 50.0, 100.0]))
    assert out.log_freight.to_numpy() == pytest.approx(np.log1p([10.0, 20.0, 10.0]))
    assert list(out.same_state) == [0, 1, 1]              # o6: seller của item 1 là s2 (SP)
    assert list(out.purchase_month) == ["2018-01", "2018-01", "2018-01"]
    assert list(out.customer_state) == ["SP", "SP", "SP"]


def simulate(n: int = 30000, seed: int = 0) -> pd.DataFrame:
    """Vùng N và quãng đường xa làm tăng cả giao trễ lẫn review xấu. Tác động thật của late: +0.30."""
    rng = np.random.default_rng(seed)
    region = rng.choice(["N", "S", "E"], n, p=[0.2, 0.5, 0.3])
    dist = rng.uniform(0, 2, n)
    logit = -3.0 + 1.5 * (region == "N") + 0.8 * dist
    late = rng.binomial(1, 1 / (1 + np.exp(-logit)))
    p_bad = 0.05 + 0.30 * late + 0.25 * (region == "N") + 0.04 * dist
    return pd.DataFrame({"late": late, "bad_review": rng.binomial(1, p_bad), "region": region, "dist": dist})


@pytest.mark.parametrize("seed", range(5))
def test_effect_estimates_remove_confounding(nb, seed):
    df = simulate(seed=seed)
    est = nb.effect_estimates(df, ["dist"], ["region"])
    assert set(est) == {"naive", "regression", "ipw_att"}
    assert est["naive"] - est["regression"] > 0.05          # ngây thơ lệch lên
    assert est["regression"] == pytest.approx(0.30, abs=0.03)
    assert est["ipw_att"] == pytest.approx(0.30, abs=0.03)


def test_effect_estimates_without_covariates_equal_naive(nb):
    df = simulate(n=2000, seed=9)
    est = nb.effect_estimates(df, [], [])
    assert est["regression"] == pytest.approx(est["naive"], abs=1e-9)
    assert est["ipw_att"] == pytest.approx(est["naive"], abs=1e-6)


def test_e_value(nb):
    assert nb.e_value(1.0) == pytest.approx(1.0)
    assert nb.e_value(2.0) == pytest.approx(2 + np.sqrt(2))
    assert nb.e_value(0.5) == pytest.approx(2 + np.sqrt(2))   # RR < 1: tính trên 1/RR
    assert nb.e_value(5.863) == pytest.approx(11.20, abs=0.01)


def test_real_olist(nb):
    raw = ROOT / "data" / "raw"
    if not (raw / "olist_orders_dataset.csv").exists():
        pytest.skip("Chưa tải Olist thật: uv run python data/download_olist.py")
    dates = ["order_purchase_timestamp", "order_delivered_customer_date", "order_estimated_delivery_date"]
    df = nb.build_orders(
        pd.read_csv(raw / "olist_orders_dataset.csv", parse_dates=dates),
        pd.read_csv(raw / "olist_order_reviews_dataset.csv", parse_dates=["review_answer_timestamp"]),
        pd.read_csv(raw / "olist_order_items_dataset.csv"),
        pd.read_csv(raw / "olist_customers_dataset.csv"),
        pd.read_csv(raw / "olist_sellers_dataset.csv"),
    )
    assert len(df) == 95824
    assert df.late.mean() == pytest.approx(0.0799, abs=5e-4)
    rates = df.groupby("late").bad_review.mean()
    assert rates[1] == pytest.approx(0.541, abs=1e-3) and rates[0] == pytest.approx(0.092, abs=1e-3)
    sub = df[df.purchase_month >= "2017-01"]
    est = nb.effect_estimates(sub, NUMERIC, CATEGORICAL)
    assert est["naive"] == pytest.approx(0.448, abs=0.003)
    assert 0.40 < est["regression"] < est["naive"]


def test_report_written():
    report = ex.read("REPORT.md")
    assert "TODO" not in report
    assert len(report.split()) >= 400

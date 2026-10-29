import numpy as np
import pandas as pd
import pytest
from sklearn.metrics import average_precision_score, roc_auc_score

from testkit import ROOT, Exercise

ex = Exercise(__file__)

T = pd.to_datetime
ORDERS = pd.DataFrame({
    "order_id": ["o1", "o2", "o3", "o4"],
    "customer_id": ["c1", "c2", "c3", "c4"],
    "order_status": ["delivered", "delivered", "canceled", "delivered"],
    "order_purchase_timestamp": T(["2017-12-31 23:59:00", "2018-01-01 00:00:00", "2018-02-01 00:00:00", "2018-04-01 00:00:00"]),
    "order_approved_at": T(["2018-01-01 00:00:00"] * 4),
    "order_delivered_carrier_date": T(["2018-01-02 11:59:00", "2018-01-03 00:00:00", None, None]),
    "order_delivered_customer_date": T(["2018-01-10 00:00:00", "2018-01-25 00:00:00", None, "2018-04-20 00:00:00"]),
    "order_estimated_delivery_date": T(["2018-01-20 00:00:00", "2018-01-21 00:00:00", "2018-02-20 00:00:00", "2018-04-30 00:00:00"]),
})
ITEMS = pd.DataFrame({
    "order_id": ["o1", "o2", "o2", "o2", "o3", "o4"],
    "order_item_id": [1, 1, 2, 3, 1, 1],
    "seller_id": ["s1", "s1", "s2", "s2", "s1", "s2"],
    "freight_value": [10.0, 5.0, 3.0, 2.0, 7.0, 0.0],
})
CUSTOMERS = pd.DataFrame({"customer_id": ["c1", "c2", "c3", "c4"], "customer_state": ["SP", "SP", "RJ", "BA"]})
SELLERS = pd.DataFrame({"seller_id": ["s1", "s2"], "seller_state": ["SP", "MG"]})


@pytest.fixture(scope="module")
def nb():
    return ex.notebook("decision.ipynb")


def build_small(nb):
    return nb.build_orders(ORDERS, ITEMS, CUSTOMERS, SELLERS).set_index("order_id")


def test_build_orders_rows_and_label(nb):
    small = build_small(nb)
    assert sorted(small.index) == ["o1", "o2", "o4"]
    assert list(small.loc[["o1", "o2", "o4"], "late"]) == [0, 1, 0]
    assert {"purchase_ts", "promised_days", "same_state", "log_freight", "n_items", "n_sellers",
            "customer_state", "handling_days", "remaining_days"} <= set(small.columns)


def test_build_orders_items_and_state(nb):
    small = build_small(nb)
    assert small.loc["o2", "n_items"] == 3 and small.loc["o2", "n_sellers"] == 2
    assert small.loc["o2", "log_freight"] == pytest.approx(np.log1p(10.0))
    assert small.loc["o1", "same_state"] == 1
    assert small.loc["o2", "same_state"] == 0        # một seller khác bang là không cùng bang
    assert small.loc["o4", "same_state"] == 0
    assert small.loc["o4", "customer_state"] == "BA"


def test_build_orders_days(nb):
    small = build_small(nb)
    assert small.loc["o1", "promised_days"] == pytest.approx(19 + 1 / 1440)
    assert small.loc["o1", "handling_days"] == pytest.approx(1.5)
    assert small.loc["o1", "remaining_days"] == pytest.approx(17.5 + 1 / 1440)
    assert np.isnan(small.loc["o4", "handling_days"]) and np.isnan(small.loc["o4", "remaining_days"])


def test_time_split_boundaries(nb):
    df = build_small(nb).reset_index()
    extra = df.iloc[[0]].assign(order_id="o9", purchase_ts=pd.Timestamp("2018-09-01 00:00:00"))
    train, val, test = nb.time_split(pd.concat([df, extra], ignore_index=True))
    assert list(train.order_id) == ["o1"] and list(val.order_id) == ["o2"] and list(test.order_id) == ["o4"]


def test_features_at(nb):
    purchase, carrier = nb.features_at("purchase"), nb.features_at("carrier")
    assert "handling_days" not in purchase and "remaining_days" not in purchase
    assert {"handling_days", "remaining_days"} <= set(carrier)
    assert set(purchase) < set(carrier)
    forbidden = {"late", "order_id", "purchase_ts"}
    assert not forbidden & set(carrier)
    with pytest.raises(ValueError):
        nb.features_at("delivery")


def test_offline_report_matches_sklearn(nb):
    rng = np.random.default_rng(0)
    y = (rng.random(2000) < 0.1).astype(int)
    p = np.clip(0.1 + 0.3 * y + rng.normal(0, 0.2, 2000), 0, 1)
    out = nb.offline_report(y, p, ks=(10, 200))
    assert out["prevalence"] == pytest.approx(y.mean())
    assert out["roc_auc"] == pytest.approx(roc_auc_score(y, p))
    assert out["pr_auc"] == pytest.approx(average_precision_score(y, p))
    assert out["precision@200"] == pytest.approx(y[np.argsort(-p)[:200]].mean())
    assert "precision@10" in out


def test_value_table_by_hand(nb):
    y = [1, 0, 1, 0, 0, 1, 0, 0, 0, 0]
    p = [0.9, 0.8, 0.7, 0.6, 0.5, 0.4, 0.3, 0.2, 0.15, 0.1]
    out = nb.value_table(y, p, [0.2, 0.5], cost_action=0.5, loss_event=30, effect=0.15, n_weeks=2)
    assert out.loc[0.2, "k"] == 2 and out.loc[0.2, "precision"] == pytest.approx(0.5)
    assert out.loc[0.2, "value"] == pytest.approx(1 * 4.5 - 2 * 0.5)
    assert out.loc[0.5, "value"] == pytest.approx(2 * 4.5 - 5 * 0.5)
    assert out.loc[0.5, "value_per_week"] == pytest.approx((2 * 4.5 - 5 * 0.5) / 2)


def test_fit_predict_learns_signal_with_nan(nb):
    rng = np.random.default_rng(1)
    n = 4000
    df = pd.DataFrame({
        "promised_days": rng.uniform(5, 40, n), "same_state": rng.integers(0, 2, n),
        "log_freight": rng.normal(3, 0.5, n), "n_items": rng.integers(1, 4, n), "n_sellers": 1,
        "customer_state": rng.choice(["SP", "RJ", "BA", "AM"], n),
        "handling_days": rng.exponential(3, n), "remaining_days": rng.uniform(-2, 30, n),
    })
    logit = -2.5 + 0.25 * (5 - df.remaining_days).clip(-10, 10) + 0.8 * (df.customer_state == "AM")
    df["late"] = (rng.random(n) < 1 / (1 + np.exp(-logit))).astype(int)
    df.loc[rng.random(n) < 0.05, ["handling_days", "remaining_days"]] = np.nan
    train, test = df.iloc[:3000], df.iloc[3000:]
    p = np.asarray(nb.fit_predict(train, test, nb.features_at("carrier")))
    assert p.shape == (1000,)
    assert np.all((p >= 0) & (p <= 1))
    assert roc_auc_score(test.late, p) > 0.75


def test_real_olist(nb):
    raw = ROOT / "data" / "raw"
    if not (raw / "olist_orders_dataset.csv").exists():
        pytest.skip("Chưa tải Olist thật: uv run python data/download_olist.py")
    dates = ["order_purchase_timestamp", "order_approved_at", "order_delivered_carrier_date",
             "order_delivered_customer_date", "order_estimated_delivery_date"]
    orders = pd.read_csv(raw / "olist_orders_dataset.csv", parse_dates=dates)
    df = nb.build_orders(orders, pd.read_csv(raw / "olist_order_items_dataset.csv"),
                         pd.read_csv(raw / "olist_customers_dataset.csv"), pd.read_csv(raw / "olist_sellers_dataset.csv"))
    assert len(df) == 96470
    assert df.late.mean() == pytest.approx(0.0811, abs=0.0005)
    train, val, test = nb.time_split(df)
    assert (len(train), len(val), len(test)) == (43693, 20627, 32150)
    pr = {t: average_precision_score(test.late, nb.fit_predict(train, test, nb.features_at(t)))
          for t in ["purchase", "carrier"]}
    assert pr["carrier"] > pr["purchase"] + 0.15

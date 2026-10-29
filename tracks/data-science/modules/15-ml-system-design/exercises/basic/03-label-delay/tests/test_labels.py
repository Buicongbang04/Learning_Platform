import math

import pandas as pd
import pytest

from testkit import ROOT, Exercise

ex = Exercise(__file__)

ORDERS = pd.DataFrame({
    "order_id": ["a", "b", "c", "d", "e"],
    "order_status": ["delivered", "delivered", "delivered", "shipped", "delivered"],
    "order_purchase_timestamp": pd.to_datetime(["2018-02-01", "2018-02-02", "2018-02-03", "2018-02-04", "2018-02-05"]),
    "order_delivered_customer_date": pd.to_datetime(["2018-02-10 00:00", "2018-03-05 10:00", "2018-02-20 00:00", None, None]),
    "order_estimated_delivery_date": pd.to_datetime(["2018-02-20", "2018-02-25", "2018-02-20", "2018-02-28", "2018-03-01"]),
})


@pytest.fixture(scope="module")
def labels():
    return ex.module("labels.py")


def test_known_at(labels):
    out = labels.late_label_known_at(ORDERS)
    assert sorted(out.index) == ["a", "b", "c"]
    assert {"purchase_ts", "late", "known_at"} <= set(out.columns)
    assert list(out.loc[["a", "b", "c"], "late"]) == [False, True, False]
    assert out.loc["a", "known_at"] == pd.Timestamp("2018-02-10")
    assert out.loc["b", "known_at"] == pd.Timestamp("2018-02-25")     # biết trễ khi quá hẹn, trước ngày giao
    assert out.loc["c", "known_at"] == pd.Timestamp("2018-02-20")     # giao đúng 00:00 ngày hẹn: không trễ


def test_observed_rate(labels):
    lab = labels.late_label_known_at(ORDERS)
    share, rate = labels.observed_late_rate(lab, "2018-02-15")
    assert share == pytest.approx(1 / 3) and rate == pytest.approx(0.0)
    share, rate = labels.observed_late_rate(lab, pd.Timestamp("2018-02-28"))
    assert share == pytest.approx(1.0) and rate == pytest.approx(1 / 3)
    share, rate = labels.observed_late_rate(lab, "2018-02-01")
    assert share == 0 and math.isnan(rate)


def test_maturity_days(labels):
    lab = labels.late_label_known_at(ORDERS)
    # số ngày: a 9, b 23, c 17
    assert labels.maturity_days(lab, 1.0) == pytest.approx(23)
    assert labels.maturity_days(lab, 0.5) == pytest.approx(17)


def test_real_olist(labels):
    raw = ROOT / "data" / "raw"
    if not (raw / "olist_orders_dataset.csv").exists():
        pytest.skip("Chưa tải Olist thật: uv run python data/download_olist.py")
    dates = ["order_purchase_timestamp", "order_delivered_customer_date", "order_estimated_delivery_date"]
    orders = pd.read_csv(raw / "olist_orders_dataset.csv", parse_dates=dates)
    lab = labels.late_label_known_at(orders)
    assert len(lab) == 96470
    assert lab.late.mean() == pytest.approx(0.081, abs=0.001)
    feb = lab[(lab.purchase_ts >= "2018-02-01") & (lab.purchase_ts < "2018-03-01")]
    assert feb.late.mean() == pytest.approx(0.160, abs=0.002)
    share, rate = labels.observed_late_rate(feb, "2018-03-01")
    assert share == pytest.approx(0.47, abs=0.01)
    assert rate == pytest.approx(0.0135, abs=0.002)
    assert labels.maturity_days(lab, 0.95) == pytest.approx(25.4, abs=0.3)

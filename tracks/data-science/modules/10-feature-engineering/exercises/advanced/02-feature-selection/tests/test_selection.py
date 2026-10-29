import numpy as np
import pandas as pd
import pytest
from sklearn.model_selection import KFold, StratifiedKFold

from testkit import ROOT, Exercise

ex = Exercise(__file__)


@pytest.fixture(scope="module")
def sel():
    return ex.module("selection.py")


def noise_data(seed: int, n: int = 200, p: int = 2000):
    rng = np.random.default_rng(seed)
    return rng.normal(size=(n, p)), rng.integers(0, 2, n)


def signal_data(seed: int, n: int = 1000, p: int = 200, informative: int = 5):
    rng = np.random.default_rng(seed)
    X = rng.normal(size=(n, p))
    logit = X[:, :informative] @ np.full(informative, 0.8)
    y = (rng.random(n) < 1 / (1 + np.exp(-logit))).astype(int)
    return pd.DataFrame(X, columns=[f"f{i}" for i in range(p)]), y


def test_leaky_selection_looks_great_on_pure_noise(sel):
    X, y = noise_data(0)
    cv = StratifiedKFold(5, shuffle=True, random_state=0)
    assert sel.leaky_selection_auc(X, y, k=20, cv=cv) > 0.75


def test_honest_selection_stays_near_chance(sel):
    X, y = noise_data(0)
    cv = StratifiedKFold(5, shuffle=True, random_state=0)
    assert 0.3 < sel.honest_selection_auc(X, y, k=20, cv=cv) < 0.7


def test_both_agree_when_signal_is_real(sel):
    X, y = signal_data(1)
    cv = StratifiedKFold(5, shuffle=True, random_state=0)
    honest = sel.honest_selection_auc(X, y, k=5, cv=cv)
    leaky = sel.leaky_selection_auc(X, y, k=5, cv=cv)
    assert honest > 0.8
    assert abs(leaky - honest) < 0.03


def test_selection_frequency(sel):
    X, y = signal_data(2)
    freq = sel.selection_frequency(X, y, k=5, splits=KFold(5, shuffle=True, random_state=0).split(X))
    assert isinstance(freq, pd.Series) and set(freq.index) == set(X.columns)
    assert list(freq.values) == sorted(freq.values, reverse=True)
    assert (freq[[f"f{i}" for i in range(5)]] >= 0.8).all()
    assert freq.drop([f"f{i}" for i in range(5)]).mean() < 0.05
    assert freq.sum() == pytest.approx(5)          # mỗi fold chọn đúng k feature


def test_selection_frequency_uses_train_part_only(sel):
    X, y = signal_data(3, n=400, p=20)
    X = X.copy()
    test_rows = np.arange(300, 400)
    X.loc[test_rows, "f19"] = y[test_rows] * 10.0        # cột này chỉ "rò" ở phần test của split
    splits = [(np.arange(300), test_rows)]
    freq = sel.selection_frequency(X, y, k=5, splits=splits)
    assert freq["f19"] == 0


def test_report_written():
    doc = ex.read("REPORT.md")
    assert "TODO" not in doc
    assert len(doc.split()) >= 300


def test_real_olist_delivery_features_always_selected(sel):
    raw = ROOT / "data" / "raw"
    if not (raw / "olist_orders_dataset.csv").exists():
        pytest.skip("Chưa tải Olist thật: uv run python data/download_olist.py")
    orders = pd.read_csv(raw / "olist_orders_dataset.csv", parse_dates=[
        "order_purchase_timestamp", "order_approved_at", "order_delivered_customer_date",
        "order_estimated_delivery_date"])
    reviews = pd.read_csv(raw / "olist_order_reviews_dataset.csv", parse_dates=["review_answer_timestamp"])
    delivered = orders[(orders.order_status == "delivered") & orders.order_delivered_customer_date.notna()]
    latest = reviews.sort_values("review_answer_timestamp").drop_duplicates("order_id", keep="last")
    df = delivered.merge(latest, on="order_id")
    df = df[df.order_purchase_timestamp < "2018-01-01"].sort_values("order_purchase_timestamp")
    day = pd.Timedelta(days=1)
    X = pd.DataFrame({
        "promised_days": (df.order_estimated_delivery_date - df.order_purchase_timestamp) / day,
        "delivery_days": (df.order_delivered_customer_date - df.order_purchase_timestamp) / day,
        "delay_days": (df.order_delivered_customer_date - df.order_estimated_delivery_date) / day,
        "approve_hours": (df.order_approved_at - df.order_purchase_timestamp) / pd.Timedelta(hours=1),
        "purchase_hour": df.order_purchase_timestamp.dt.hour,
        "purchase_dow": df.order_purchase_timestamp.dt.day_of_week,
    }).fillna(0).reset_index(drop=True)
    y = (df.review_score <= 2).astype(int).to_numpy()
    from sklearn.model_selection import TimeSeriesSplit
    freq = sel.selection_frequency(X, y, k=2, splits=TimeSeriesSplit(4).split(X))
    assert set(freq.index[:2]) == {"delivery_days", "delay_days"}
    assert freq["delivery_days"] == 1 and freq["delay_days"] == 1

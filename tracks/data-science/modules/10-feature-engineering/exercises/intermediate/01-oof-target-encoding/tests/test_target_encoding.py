import numpy as np
import pandas as pd
import pytest
from sklearn.metrics import roc_auc_score

from testkit import ROOT, Exercise

ex = Exercise(__file__)

CATS = pd.Series(["a", "a", "a", "b", "b", "c", None, "a"])
Y = np.array([1, 0, 1, 0, 0, 1, 1, 1])


@pytest.fixture(scope="module")
def te():
    return ex.module("target_encoding.py")


def noise_data(seed: int, n: int = 4000, k: int = 1500):
    rng = np.random.default_rng(seed)
    return pd.Series(rng.integers(0, k, n).astype(str)), (rng.random(n) < 0.15).astype(int)


def signal_data(seed: int, n: int = 4000, k: int = 40):
    rng = np.random.default_rng(seed)
    effect = rng.normal(0, 1, k)
    c = rng.integers(0, k, n)
    p = 1 / (1 + np.exp(-(-1.5 + effect[c])))
    return pd.Series(c.astype(str)), (rng.random(n) < p).astype(int)


def test_fit_formula(te):
    mapping, prior = te.fit_target_encoding(CATS, Y, smoothing=2)
    assert prior == pytest.approx(5 / 8)       # prior tính trên mọi dòng, kể cả dòng category NaN
    assert mapping["a"] == pytest.approx((3 + 2 * 0.625) / (4 + 2))
    assert mapping["b"] == pytest.approx((0 + 2 * 0.625) / (2 + 2))
    assert mapping["c"] == pytest.approx((1 + 2 * 0.625) / (1 + 2))
    assert set(mapping.index) == {"a", "b", "c"}


def test_smoothing_zero_is_raw_mean_and_more_smoothing_shrinks(te):
    raw, _ = te.fit_target_encoding(CATS, Y, smoothing=0)
    assert raw["a"] == pytest.approx(0.75) and raw["b"] == pytest.approx(0.0)
    small, prior = te.fit_target_encoding(CATS, Y, smoothing=1)
    big, _ = te.fit_target_encoding(CATS, Y, smoothing=100)
    assert abs(big["b"] - prior) < abs(small["b"] - prior)


def test_transform_unseen_and_missing_get_prior(te):
    mapping, prior = te.fit_target_encoding(CATS, Y, smoothing=2)
    out = te.transform_target_encoding(pd.Series(["a", "zzz", None]), mapping, prior)
    assert isinstance(out, np.ndarray)
    assert out[0] == pytest.approx(mapping["a"])
    assert out[1] == pytest.approx(prior) and out[2] == pytest.approx(prior)


def test_oof_row_never_sees_its_own_label(te):
    cats, y = signal_data(0, n=600, k=30)
    base = te.oof_target_encoding(cats, y, seed=3)
    assert base.shape == (600,)
    for i in [0, 17, 250, 599]:
        flipped = y.copy()
        flipped[i] = 1 - flipped[i]
        again = te.oof_target_encoding(cats, flipped, seed=3)
        assert again[i] == pytest.approx(base[i])      # đổi nhãn của chính dòng i không đổi mã của dòng i
        assert not np.allclose(again, base)            # nhưng có đổi mã của dòng khác cùng nhóm


def test_oof_is_reproducible(te):
    cats, y = signal_data(1, n=500)
    assert np.array_equal(te.oof_target_encoding(cats, y, seed=5), te.oof_target_encoding(cats, y, seed=5))


def test_naive_encoding_leaks_on_noise_but_oof_does_not(te):
    cats, y = noise_data(0)
    mapping, prior = te.fit_target_encoding(cats, y)
    naive_auc = roc_auc_score(y, te.transform_target_encoding(cats, mapping, prior))
    oof_auc = roc_auc_score(y, te.oof_target_encoding(cats, y, seed=0))
    assert naive_auc > 0.8            # nhãn ngẫu nhiên mà "dự đoán" tốt: đó là leakage
    assert 0.40 < oof_auc < 0.58


def test_oof_keeps_real_signal(te):
    cats, y = signal_data(2)
    assert roc_auc_score(y, te.oof_target_encoding(cats, y)) > 0.62


def test_real_olist_customer_zip(te):
    raw = ROOT / "data" / "raw"
    if not (raw / "olist_orders_dataset.csv").exists():
        pytest.skip("Chưa tải Olist thật: uv run python data/download_olist.py")
    orders = pd.read_csv(raw / "olist_orders_dataset.csv",
                         parse_dates=["order_purchase_timestamp", "order_delivered_customer_date"])
    reviews = pd.read_csv(raw / "olist_order_reviews_dataset.csv", parse_dates=["review_answer_timestamp"])
    customers = pd.read_csv(raw / "olist_customers_dataset.csv", dtype={"customer_zip_code_prefix": str})
    delivered = orders[(orders.order_status == "delivered") & orders.order_delivered_customer_date.notna()]
    latest = reviews.sort_values("review_answer_timestamp").drop_duplicates("order_id", keep="last")
    df = delivered.merge(latest, on="order_id").merge(customers, on="customer_id")
    df["bad_review"] = (df.review_score <= 2).astype(int)
    train = df[df.order_purchase_timestamp < "2018-01-01"].reset_index(drop=True)
    val = df[(df.order_purchase_timestamp >= "2018-01-01") & (df.order_purchase_timestamp < "2018-04-01")]
    col = "customer_zip_code_prefix"
    mapping, prior = te.fit_target_encoding(train[col], train.bad_review, smoothing=20)
    naive_train = roc_auc_score(train.bad_review, te.transform_target_encoding(train[col], mapping, prior))
    naive_val = roc_auc_score(val.bad_review, te.transform_target_encoding(val[col], mapping, prior))
    oof_train = roc_auc_score(train.bad_review, te.oof_target_encoding(train[col], train.bad_review, smoothing=20))
    assert naive_train == pytest.approx(0.856, abs=0.003)
    assert naive_val == pytest.approx(0.536, abs=0.003)
    assert oof_train < 0.56

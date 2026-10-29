import time

import numpy as np
import pandas as pd
import pytest

from testkit import ROOT, Exercise

ex = Exercise(__file__)


def ts(values):
    return pd.to_datetime(values, format="ISO8601")


# Seller A: a1..a6, seller B: b1, b2. Thứ tự dòng bị xáo, index không phải 0..n-1.
FIXTURE = pd.DataFrame({
    "order": ["a4", "b2", "a1", "a6", "a3", "b1", "a5", "a2"],
    "seller_id": ["A", "B", "A", "A", "A", "B", "A", "A"],
    "prediction_time": ts(["2018-01-21", "2018-01-20", "2018-01-10", "2018-02-01",
                           "2018-01-12", "2018-01-13", "2018-01-30", "2018-01-11"]),
    "label_time": ts(["2018-01-25", "2018-01-22", "2018-01-12", None,
                      "2018-01-15", "2018-01-14", "2018-01-28", "2018-01-20"]),
    "bad_review": [0, 0, 1, 0, 1, 1, 1, 0],
}, index=[70, 71, 72, 73, 74, 75, 76, 77])
# Kỳ vọng (số review quá khứ, số review xấu quá khứ):
#   a1: chưa có gì                                   (0, 0)
#   a2: nhãn a1 lúc 01-12, chưa có lúc 01-11          (0, 0)
#   a3: nhãn a1 đúng 01-12 = lúc dự đoán: KHÔNG tính  (0, 0)
#   a4: a1, a3, a2 (01-12, 01-15, 01-20 < 01-21)      (3, 2)
#   a5: a1..a4; nhãn của chính a5 (01-28, trước lúc giao 01-30) không tính  (4, 2)
#   a6: a1..a5                                       (5, 3)
#   b1: không tính seller A                          (0, 0)
#   b2: b1                                           (1, 1)
EXPECTED = {"a1": (0, 0), "a2": (0, 0), "a3": (0, 0), "a4": (3, 2), "a5": (4, 2), "a6": (5, 3),
            "b1": (0, 0), "b2": (1, 1)}


@pytest.fixture(scope="module")
def nb():
    return ex.notebook("seller_history.ipynb")


def brute_force(df: pd.DataFrame, prior: float, smoothing: float) -> pd.DataFrame:
    rows = []
    for i, row in df.iterrows():
        past = df[(df.index != i) & (df.seller_id == row.seller_id) & (df.label_time < row.prediction_time)]
        rows.append((len(past), (past.bad_review.sum() + smoothing * prior) / (len(past) + smoothing)))
    return pd.DataFrame(rows, index=df.index, columns=["seller_past_reviews", "seller_past_bad_rate"])


def test_fixture_counts_and_rates(nb):
    out = nb.seller_history(FIXTURE.drop(columns="order"), prior=0.2, smoothing=2)
    assert list(out.index) == list(FIXTURE.index)
    for idx, order in FIXTURE.order.items():
        n, bad = EXPECTED[order]
        assert out.loc[idx, "seller_past_reviews"] == n, order
        assert out.loc[idx, "seller_past_bad_rate"] == pytest.approx((bad + 2 * 0.2) / (n + 2)), order


def test_does_not_mutate_input(nb):
    df = FIXTURE.drop(columns="order")
    copy = df.copy()
    nb.seller_history(df, prior=0.2)
    pd.testing.assert_frame_equal(df, copy)


def test_matches_brute_force_on_random_data(nb):
    rng = np.random.default_rng(0)
    n = 300
    pred = pd.Timestamp("2018-01-01") + pd.to_timedelta(rng.integers(0, 60, n), unit="D")
    label = pred + pd.to_timedelta(rng.integers(-5, 20, n), unit="D")     # có cả nhãn trước lúc giao
    df = pd.DataFrame({
        "seller_id": rng.choice(list("ABCDE"), n),
        "prediction_time": pred,
        "label_time": label.where(rng.random(n) > 0.1),                     # 10% chưa có review
        "bad_review": (rng.random(n) < 0.3).astype(int),
    }, index=rng.permutation(n) + 1000)
    out = nb.seller_history(df, prior=0.15, smoothing=5)
    expected = brute_force(df, 0.15, 5)
    assert out.seller_past_reviews.tolist() == expected.seller_past_reviews.tolist()
    assert out.seller_past_bad_rate.to_numpy() == pytest.approx(expected.seller_past_bad_rate.to_numpy())


def test_fast_on_large_data(nb):
    rng = np.random.default_rng(1)
    n = 100_000
    seller = np.where(rng.random(n) < 0.1, "big", rng.integers(0, 3000, n).astype(str))   # một seller rất lớn
    pred = pd.Timestamp("2017-01-01") + pd.to_timedelta(rng.uniform(0, 600, n), unit="D")
    df = pd.DataFrame({"seller_id": seller, "prediction_time": pred,
                       "label_time": pred + pd.to_timedelta(rng.uniform(-2, 15, n), unit="D"),
                       "bad_review": (rng.random(n) < 0.13).astype(int)})
    start = time.perf_counter()
    out = nb.seller_history(df, prior=0.13)
    assert time.perf_counter() - start < 5
    assert len(out) == n and out.seller_past_reviews.min() >= 0


def test_report_written():
    doc = ex.read("REPORT.md")
    assert "TODO" not in doc
    assert len(doc.split()) >= 300


def test_real_olist(nb):
    raw = ROOT / "data" / "raw"
    if not (raw / "olist_orders_dataset.csv").exists():
        pytest.skip("Chưa tải Olist thật: uv run python data/download_olist.py")
    table = nb.load_olist_table(raw)
    prior = table[table.order_purchase_timestamp < "2018-01-01"].bad_review.mean()
    hist = nb.seller_history(table.rename(columns={"order_delivered_customer_date": "prediction_time",
                                                   "review_answer_timestamp": "label_time"}), prior)
    val = table.join(hist)
    val = val[(val.order_purchase_timestamp >= "2018-01-01") & (val.order_purchase_timestamp < "2018-04-01")]
    assert hist.seller_past_reviews.max() == 1792
    assert (val.seller_past_reviews == 0).mean() == pytest.approx(0.0202, abs=5e-4)
    assert hist.seller_past_bad_rate.mean() == pytest.approx(0.1222, abs=5e-4)

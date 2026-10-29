import datetime as dt
import signal
from contextlib import contextmanager

import numpy as np
import pandas as pd
import polars as pl
import pytest

from testkit import ROOT, Exercise

ex = Exercise(__file__)

COLUMNS = ["seller_id", "n_orders", "revenue", "late_rate", "review_score", "bad_review_rate"]
D = dt.datetime


@contextmanager
def time_limit(seconds: float, what: str):
    if not hasattr(signal, "setitimer"):
        pytest.skip("Cần SIGALRM (Linux/macOS) để giới hạn thời gian")

    def handler(signum, frame):
        raise TimeoutError

    old = signal.signal(signal.SIGALRM, handler)
    signal.setitimer(signal.ITIMER_REAL, seconds)
    try:
        yield
    except TimeoutError:
        pytest.fail(f"{what}: chạy quá {seconds} giây")
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, old)


ORDERS = pl.DataFrame({
    "order_id": ["o1", "o2", "o3", "o4", "o5"],
    "order_status": ["delivered", "delivered", "delivered", "canceled", "delivered"],
    "order_purchase_timestamp": [D(2018, 1, 1), D(2018, 1, 3), D(2018, 1, 9), D(2018, 1, 9), D(2018, 1, 10)],
    "order_delivered_customer_date": [D(2018, 1, 5), D(2018, 1, 12), D(2018, 1, 20), None, None],
    "order_estimated_delivery_date": [D(2018, 1, 10)] * 5,
})
ITEMS = pl.DataFrame({
    "order_id": ["o1", "o1", "o2", "o2", "o3", "o4", "o5"],
    "order_item_id": [1, 2, 1, 2, 1, 1, 1],
    "seller_id": ["s1", "s1", "s1", "s2", "s2", "s3", "s3"],
    "price": [10.0, 20.0, 5.0, 7.0, 100.0, 50.0, 60.0],
})
REVIEWS = pl.DataFrame({
    "review_id": ["r1", "r2b", "r2a", "r4"],                  # cố ý không sắp theo thời gian
    "order_id": ["o1", "o2", "o2", "o4"],
    "review_score": [5, 1, 4, 3],
    "review_answer_timestamp": [D(2018, 1, 6), D(2018, 1, 15), D(2018, 1, 13), D(2018, 1, 7)],
})


@pytest.fixture(scope="module")
def p():
    return ex.module("pipeline.py")


def test_returns_lazyframes(p):
    assert isinstance(p.seller_scorecard(ORDERS.lazy(), ITEMS.lazy(), REVIEWS.lazy()), pl.LazyFrame)
    assert isinstance(p.weekly_gmv(ORDERS.lazy(), ITEMS.lazy()), pl.LazyFrame)


def test_scorecard_hand_data(p):
    out = p.seller_scorecard(ORDERS.lazy(), ITEMS.lazy(), REVIEWS.lazy()).collect()
    assert out.columns == COLUMNS
    assert out["seller_id"].to_list() == ["s1", "s2"]
    s1, s2 = out.row(0, named=True), out.row(1, named=True)
    assert (s1["n_orders"], s1["revenue"], s1["late_rate"]) == (2, pytest.approx(35.0), pytest.approx(0.5))
    assert (s1["review_score"], s1["bad_review_rate"]) == (pytest.approx(3.0), pytest.approx(0.5))
    assert (s2["n_orders"], s2["revenue"], s2["late_rate"]) == (2, pytest.approx(107.0), pytest.approx(1.0))
    assert (s2["review_score"], s2["bad_review_rate"]) == (pytest.approx(1.0), pytest.approx(1.0))


def test_scorecard_seller_without_reviews_is_null(p):
    out = p.seller_scorecard(ORDERS.lazy(), ITEMS.lazy(), REVIEWS.filter(pl.col("order_id") != "o2").lazy()).collect()
    row = out.filter(pl.col("seller_id") == "s2").row(0, named=True)
    assert row["review_score"] is None or np.isnan(row["review_score"])
    assert row["bad_review_rate"] is None or np.isnan(row["bad_review_rate"])


def pandas_oracle(orders: pd.DataFrame, items: pd.DataFrame, reviews: pd.DataFrame) -> pd.DataFrame:
    done = orders[(orders.order_status == "delivered") & orders.order_delivered_customer_date.notna()]
    done = done.assign(late=done.order_delivered_customer_date > done.order_estimated_delivery_date)[["order_id", "late"]]
    latest = reviews.sort_values("review_answer_timestamp").drop_duplicates("order_id", keep="last")
    revenue = items.merge(done, on="order_id").groupby("seller_id").price.sum()
    pairs = items[["seller_id", "order_id"]].drop_duplicates().merge(done, on="order_id")
    pairs = pairs.merge(latest[["order_id", "review_score"]], on="order_id", how="left")
    pairs["bad"] = (pairs.review_score <= 2).where(pairs.review_score.notna())
    out = pairs.groupby("seller_id").agg(n_orders=("order_id", "size"), late_rate=("late", "mean"),
                                         review_score=("review_score", "mean"), bad_review_rate=("bad", "mean"))
    out["revenue"] = revenue
    return out.reset_index()[COLUMNS].sort_values("seller_id").reset_index(drop=True)


def make_data(n_orders: int, n_items: int, n_sellers: int, seed: int):
    rng = np.random.default_rng(seed)
    order_ids = np.array([f"o{i}" for i in range(n_orders)])
    purchase = np.datetime64("2018-01-01") + rng.integers(0, 200 * 86400, n_orders).astype("timedelta64[s]")
    delivered = purchase + rng.integers(2 * 86400, 35 * 86400, n_orders).astype("timedelta64[s]")
    delivered = np.where(rng.random(n_orders) > 0.03, delivered, np.datetime64("NaT"))
    orders = pd.DataFrame({
        "order_id": order_ids,
        "order_status": np.where(rng.random(n_orders) < 0.9, "delivered", "shipped"),
        "order_purchase_timestamp": purchase.astype("datetime64[us]"),
        "order_delivered_customer_date": delivered.astype("datetime64[us]"),
        "order_estimated_delivery_date": (purchase + rng.integers(10, 30, n_orders).astype("timedelta64[D]")).astype("datetime64[us]"),
    })
    items = pd.DataFrame({
        "order_id": order_ids[rng.integers(0, n_orders, n_items)],
        "order_item_id": rng.integers(1, 4, n_items),
        "seller_id": np.array([f"s{i}" for i in range(n_sellers)])[rng.integers(0, n_sellers, n_items)],
        "price": rng.integers(500, 50_000, n_items) / 100,
    })
    reviewed = order_ids[rng.random(n_orders) < 0.85]
    review_orders = np.concatenate([reviewed, reviewed[rng.random(len(reviewed)) < 0.05]])
    reviews = pd.DataFrame({
        "review_id": [f"r{i}" for i in range(len(review_orders))],
        "order_id": review_orders,
        "review_score": rng.integers(1, 6, len(review_orders)),
        "review_answer_timestamp": (np.datetime64("2018-03-01T00:00") + rng.permutation(len(review_orders)).astype("timedelta64[m]")).astype("datetime64[us]"),
    })
    return orders, items, reviews


@pytest.mark.parametrize("seed", [0, 1, 2])
def test_scorecard_matches_pandas_oracle(p, seed):
    orders, items, reviews = make_data(1500, 2000, 30, seed)
    got = p.seller_scorecard(pl.from_pandas(orders).lazy(), pl.from_pandas(items).lazy(),
                             pl.from_pandas(reviews).lazy()).collect().to_pandas()
    pd.testing.assert_frame_equal(got, pandas_oracle(orders, items, reviews), check_dtype=False)


def test_scorecard_scales(p):
    orders, items, reviews = make_data(400_000, 1_000_000, 3000, 3)
    lazy = [pl.from_pandas(df).lazy() for df in (orders, items, reviews)]
    with time_limit(20, "seller_scorecard"):
        out = p.seller_scorecard(*lazy).collect()
    assert out.height == 3000


def test_weekly_gmv_hand_data(p):
    out = p.weekly_gmv(ORDERS.lazy(), ITEMS.lazy()).collect()
    assert out.columns == ["week", "gmv", "orders", "wow_growth"]
    # tuần bắt đầu thứ Hai: o1, o2 (mua 01/01, 03/01) thuộc tuần 2018-01-01; o3 (09/01) thuộc tuần 2018-01-08
    assert out["week"].to_list() == [dt.date(2018, 1, 1), dt.date(2018, 1, 8)]
    assert out["gmv"].to_list() == pytest.approx([42.0, 100.0])
    assert out["orders"].to_list() == [2, 1]
    assert out["wow_growth"][0] is None
    assert out["wow_growth"][1] == pytest.approx(100 / 42 - 1)


def test_real_olist(p):
    raw = ROOT / "data" / "raw"
    if not (raw / "olist_orders_dataset.csv").exists():
        pytest.skip("Chưa tải Olist thật: uv run python data/download_olist.py")
    orders = pl.scan_csv(raw / "olist_orders_dataset.csv", try_parse_dates=True)
    items = pl.scan_csv(raw / "olist_order_items_dataset.csv")
    reviews = pl.scan_csv(raw / "olist_order_reviews_dataset.csv", try_parse_dates=True)
    card = p.seller_scorecard(orders, items, reviews).collect()
    assert card.height == 2970 and card["n_orders"].sum() == 97811
    assert card["revenue"].sum() == pytest.approx(13_220_248.93, abs=0.01)
    weeks = p.weekly_gmv(orders, items).collect()
    peak = weeks.sort("gmv", descending=True).row(0, named=True)
    assert peak["week"] == dt.date(2017, 11, 20) and peak["orders"] == 2915


def test_benchmark_written():
    doc = ex.read("BENCHMARK.md")
    assert "TODO" not in doc
    assert len(doc.split()) >= 300
    assert "|" in doc, "cần một bảng kết quả đo"

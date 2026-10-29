import inspect
import signal
from contextlib import contextmanager

import numpy as np
import pandas as pd
import pytest

from testkit import ROOT, Exercise

ex = Exercise(__file__)

COLUMNS = ["n_orders", "revenue", "late_rate", "review_score", "bad_review_rate"]
T = pd.Timestamp
NaT = pd.NaT


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
        pytest.fail(f"{what}: chạy quá {seconds} giây, còn vòng lặp Python theo từng dòng?")
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, old)


def make_data(n_orders: int, n_items: int, n_sellers: int, seed: int):
    rng = np.random.default_rng(seed)
    order_ids = "o" + pd.Series(np.arange(n_orders)).astype(str)
    purchase = T("2018-01-01") + pd.to_timedelta(rng.integers(0, 200 * 86400, n_orders), unit="s")
    estimated = purchase + pd.to_timedelta(rng.integers(10, 30, n_orders), unit="D")
    delivered = pd.Series(purchase + pd.to_timedelta(rng.integers(2 * 86400, 35 * 86400, n_orders), unit="s"))
    delivered = delivered.where(rng.random(n_orders) > 0.03)
    status = np.where(rng.random(n_orders) < 0.9, "delivered", rng.choice(["shipped", "canceled"], n_orders))
    orders = pd.DataFrame({
        "order_id": order_ids, "order_status": status, "order_purchase_timestamp": purchase,
        "order_delivered_customer_date": delivered.to_numpy(), "order_estimated_delivery_date": estimated,
    })
    items = pd.DataFrame({
        "order_id": order_ids.to_numpy()[rng.integers(0, n_orders, n_items)],
        "order_item_id": rng.integers(1, 4, n_items),
        "seller_id": ("s" + pd.Series(rng.integers(0, n_sellers, n_items)).astype(str)).to_numpy(),
        "price": rng.integers(500, 50_000, n_items) / 100,
    })
    reviewed = order_ids[rng.random(n_orders) < 0.85].to_numpy()
    review_orders = np.concatenate([reviewed, reviewed[rng.random(len(reviewed)) < 0.05]])   # 5% đơn có 2 review
    reviews = pd.DataFrame({
        "review_id": ("r" + pd.Series(np.arange(len(review_orders))).astype(str)).to_numpy(),
        "order_id": review_orders,
        "review_score": rng.integers(1, 6, len(review_orders)),
        "review_answer_timestamp": T("2018-03-01") + pd.to_timedelta(rng.permutation(len(review_orders)), unit="min"),
    })
    return orders, items, reviews


# Dữ liệu tay: s1 bán o1 (2 món), o2; s2 bán o2, o3 (trễ, không review); s3 chỉ bán đơn chưa giao xong
ORDERS = pd.DataFrame({
    "order_id": ["o1", "o2", "o3", "o4", "o5"],
    "order_status": ["delivered", "delivered", "delivered", "canceled", "delivered"],
    "order_purchase_timestamp": [T("2018-01-01")] * 5,
    "order_delivered_customer_date": [T("2018-01-05"), T("2018-01-12"), T("2018-01-20"), NaT, NaT],
    "order_estimated_delivery_date": [T("2018-01-10")] * 5,
})
ITEMS = pd.DataFrame({
    "order_id": ["o1", "o1", "o2", "o2", "o3", "o4", "o5"],
    "order_item_id": [1, 2, 1, 2, 1, 1, 1],
    "seller_id": ["s1", "s1", "s1", "s2", "s2", "s3", "s3"],
    "price": [10.0, 20.0, 5.0, 7.0, 100.0, 50.0, 60.0],
})
REVIEWS = pd.DataFrame({
    "review_id": ["r1", "r2a", "r2b", "r4"],
    "order_id": ["o1", "o2", "o2", "o4"],
    "review_score": [5, 4, 1, 3],
    "review_answer_timestamp": [T("2018-01-06"), T("2018-01-13"), T("2018-01-15"), T("2018-01-07")],
})


@pytest.fixture(scope="module")
def nb():
    return ex.notebook("report.ipynb")


def test_fast_on_hand_data(nb):
    out = nb.fast_seller_report(ORDERS, ITEMS, REVIEWS)
    assert list(out.columns) == COLUMNS
    assert list(out.index) == ["s1", "s2"]                 # s3 không có đơn giao xong
    s1, s2 = out.loc["s1"], out.loc["s2"]
    assert s1["n_orders"] == 2 and s1["revenue"] == pytest.approx(35.0)
    assert s1["late_rate"] == pytest.approx(0.5)            # o2 giao 12/01 > hẹn 10/01
    assert s1["review_score"] == pytest.approx(3.0)         # o1: 5, o2: review mới nhất 1
    assert s1["bad_review_rate"] == pytest.approx(0.5)
    assert s2["n_orders"] == 2 and s2["revenue"] == pytest.approx(107.0)
    assert s2["late_rate"] == pytest.approx(1.0)
    assert s2["review_score"] == pytest.approx(1.0)         # chỉ o2 có review; o3 không tính vào mẫu số
    assert s2["bad_review_rate"] == pytest.approx(1.0)


def test_seller_without_reviews_gets_nan(nb):
    out = nb.fast_seller_report(ORDERS, ITEMS, REVIEWS[REVIEWS.order_id != "o2"])
    assert np.isnan(out.loc["s2", "review_score"]) and np.isnan(out.loc["s2", "bad_review_rate"])


@pytest.mark.parametrize("seed", [0, 1, 2])
def test_fast_matches_slow_on_random_data(nb, seed):
    orders, items, reviews = make_data(1500, 2000, 30, seed)
    expected = nb.slow_seller_report(orders, items, reviews)
    got = nb.fast_seller_report(orders, items, reviews)
    pd.testing.assert_frame_equal(got, expected, check_dtype=False, check_names=False)


def test_fast_does_not_modify_inputs(nb):
    orders, items, reviews = make_data(300, 400, 5, 3)
    copies = [orders.copy(), items.copy(), reviews.copy()]
    nb.fast_seller_report(orders, items, reviews)
    for before, after in zip(copies, [orders, items, reviews]):
        pd.testing.assert_frame_equal(before, after)


def test_fast_has_no_row_wise_python(nb):
    nb.fast_seller_report(ORDERS, ITEMS, REVIEWS)          # phải chạy được trước đã
    source = inspect.getsource(nb.fast_seller_report)
    for banned in ["iterrows", "itertuples", ".apply(", "axis=1"]:
        assert banned not in source, f"fast_seller_report còn dùng {banned}: hãy thay bằng thao tác theo cột"


def test_fast_on_one_million_items(nb):
    # Bản vector hoá: vài giây. Bản iterrows / apply(axis=1): vài phút. Giới hạn 20 giây.
    orders, items, reviews = make_data(800_000, 1_000_000, 3000, 4)
    with time_limit(20, "fast_seller_report"):
        out = nb.fast_seller_report(orders, items, reviews)
    assert len(out) == 3000
    done = orders.loc[orders.order_status.eq("delivered") & orders.order_delivered_customer_date.notna(), "order_id"]
    assert out["revenue"].sum() == pytest.approx(items.loc[items.order_id.isin(done), "price"].sum())


def test_optimize_dtypes(nb):
    rng = np.random.default_rng(5)
    n = 10_000
    df = pd.DataFrame({
        "order_id": [f"o{i}" for i in range(n)],                              # gần như duy nhất: giữ str
        "state": rng.choice(["SP", "RJ", "MG", "RS"], n),                     # ít giá trị: category
        "qty": rng.integers(1, 5, n).astype("int64"),                         # nhỏ: int8
        "big": rng.integers(0, 100_000, n).astype("int64"),                   # cần int32
        "price": rng.random(n) * 100,                                         # float: giữ nguyên
        "ts": pd.Timestamp("2018-01-01") + pd.to_timedelta(rng.integers(0, 1000, n), unit="h"),
    })
    before = df.copy()
    out = nb.optimize_dtypes(df)
    pd.testing.assert_frame_equal(df, before)                                 # không sửa input
    assert isinstance(out["state"].dtype, pd.CategoricalDtype)
    assert not isinstance(out["order_id"].dtype, pd.CategoricalDtype)
    assert out["qty"].dtype == np.int8 and out["big"].dtype == np.int32
    assert out["price"].dtype == np.float64 and out["ts"].dtype == df["ts"].dtype
    pd.testing.assert_frame_equal(out, df, check_dtype=False, check_categorical=False)
    assert out.memory_usage(deep=True).sum() < 0.75 * df.memory_usage(deep=True).sum()


def test_real_olist(nb):
    raw = ROOT / "data" / "raw"
    if not (raw / "olist_orders_dataset.csv").exists():
        pytest.skip("Chưa tải Olist thật: uv run python data/download_olist.py")
    dates = ["order_purchase_timestamp", "order_delivered_customer_date", "order_estimated_delivery_date"]
    orders = pd.read_csv(raw / "olist_orders_dataset.csv", parse_dates=dates)
    items = pd.read_csv(raw / "olist_order_items_dataset.csv")
    reviews = pd.read_csv(raw / "olist_order_reviews_dataset.csv", parse_dates=["review_answer_timestamp"])
    out = nb.fast_seller_report(orders, items, reviews)
    assert len(out) == 2970
    assert out["n_orders"].sum() == 97811
    assert out["revenue"].sum() == pytest.approx(13_220_248.93, abs=0.01)

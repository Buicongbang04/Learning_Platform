import numpy as np
import pandas as pd
import pytest

from testkit import ROOT, Exercise

ex = Exercise(__file__)


@pytest.fixture(scope="module")
def nb():
    return ex.notebook("freight_gd.ipynb")


ITEMS = pd.DataFrame({
    "order_id": ["a", "a", "b", "c", "d", "e", "f"],
    "order_item_id": [1, 2, 1, 1, 1, 1, 1],
    "product_id": ["p1", "p2", "p1", "p3", "p2", "p1", "p4"],
    "freight_value": [10.0, 20.0, 11.0, 30.0, 19.0, 12.0, 15.0],
})
PRODUCTS = pd.DataFrame({
    "product_id": ["p1", "p2", "p3", "p4"],
    "product_weight_g": [500.0, 2000.0, np.nan, 1000.0],
    "product_length_cm": [10.0, 20.0, 30.0, 10.0],
    "product_height_cm": [10.0, 10.0, 30.0, 10.0],
    "product_width_cm": [10.0, 50.0, 30.0, 20.0],
})
ORDERS = pd.DataFrame({
    "order_id": ["a", "b", "c", "d", "e", "f"],
    "order_purchase_timestamp": pd.to_datetime([
        "2017-12-31 23:59:59", "2018-01-01 00:00:00", "2018-02-01 10:00:00", "2018-04-01 00:00:00",
        "2018-08-31 23:00:00", "2018-09-01 00:00:00",
    ]),
})


def synthetic(n: int = 2000, seed: int = 0):
    """Dữ liệu đã chuẩn hoá + cột intercept, y tuyến tính có nhiễu."""
    rng = np.random.default_rng(seed)
    Z = rng.normal(size=(n, 2))
    Z[:, 1] = 0.8 * Z[:, 0] + 0.6 * Z[:, 1]           # hai feature tương quan như khối lượng / thể tích
    A = np.column_stack([np.ones(n), Z])
    y = A @ np.array([20.0, 6.0, 4.0]) + rng.normal(0, 10, n)
    return A, y


def test_build_freight_table(nb):
    out = nb.build_freight_table(ITEMS, PRODUCTS, ORDERS)
    assert {"freight_value", "weight_kg", "volume_l", "split"} <= set(out.columns)
    # c (p3 thiếu khối lượng) và f (mua 2018-09-01) bị bỏ
    assert len(out) == 5
    assert sorted(out.split.tolist()) == ["test", "test", "train", "train", "val"]
    row = out[(out.freight_value == 20.0)].iloc[0]
    assert row.weight_kg == pytest.approx(2.0) and row.volume_l == pytest.approx(10.0)
    assert out[out.freight_value == 11.0].split.iloc[0] == "val"       # đúng 2018-01-01 00:00 là val
    assert out[out.freight_value == 19.0].split.iloc[0] == "test"      # đúng 2018-04-01 là test


def test_lr_schedules(nb):
    assert nb.lr_at(37, 0.1) == pytest.approx(0.1)
    assert nb.lr_at(9, 1.0, "step", decay=0.5, step_size=10) == pytest.approx(1.0)
    assert nb.lr_at(10, 1.0, "step", decay=0.5, step_size=10) == pytest.approx(0.5)
    assert nb.lr_at(25, 1.0, "step", decay=0.5, step_size=10) == pytest.approx(0.25)
    assert nb.lr_at(10, 1.0, "inverse_time", decay=0.1) == pytest.approx(0.5)
    assert nb.lr_at(10, 1.0, "exponential", decay=0.1) == pytest.approx(np.exp(-1))
    with pytest.raises(ValueError):
        nb.lr_at(0, 1.0, "cosine-magic")


def test_gradient_descent_converges_to_least_squares(nb):
    A, y = synthetic(seed=1)
    w, losses = nb.gradient_descent(A, y, lr0=0.3, n_iter=500)
    ref, *_ = np.linalg.lstsq(A, y, rcond=None)
    assert w == pytest.approx(ref, abs=1e-6)
    assert len(losses) == 501
    assert losses[0] == pytest.approx(np.mean(y ** 2))                 # khởi tạo w = 0
    assert losses[-1] == pytest.approx(np.mean((A @ ref - y) ** 2), rel=1e-9)
    assert np.all(np.diff(losses) <= 1e-12)                            # lr nhỏ: loss không tăng


@pytest.mark.parametrize("seed", range(2, 12))
def test_learning_rate_threshold(nb, seed):
    A, y = synthetic(seed=seed)
    L = np.linalg.eigvalsh(2 * A.T @ A / len(y)).max()     # độ cong lớn nhất của MSE
    ref, *_ = np.linalg.lstsq(A, y, rcond=None)
    best = np.mean((A @ ref - y) ** 2)
    _, ok = nb.gradient_descent(A, y, lr0=0.95 * 2 / L, n_iter=300)
    _, bad = nb.gradient_descent(A, y, lr0=1.05 * 2 / L, n_iter=300)
    assert ok[-1] == pytest.approx(best, rel=1e-6)       # dưới ngưỡng: hội tụ
    assert bad[-1] > 1e3 * bad[0]                        # trên ngưỡng: phân kỳ


def test_schedule_is_used(nb):
    A, y = synthetic(seed=5)
    _, losses = nb.gradient_descent(A, y, lr0=0.1, n_iter=20, schedule="step", decay=0.0, step_size=5)
    assert losses[5] < losses[0]
    assert np.allclose(losses[5:], losses[5])            # lr = 0 từ bước thứ 6: w đứng yên


def test_standardize_and_back_transform(nb):
    rng = np.random.default_rng(6)
    X = np.column_stack([rng.lognormal(0, 1, 1000), rng.lognormal(2, 1, 1000)])
    y = 13 + 1.5 * X[:, 0] + 0.2 * X[:, 1] + rng.normal(0, 3, 1000)
    mu, sd = nb.standardize_fit(X)
    assert mu == pytest.approx(X.mean(axis=0)) and sd == pytest.approx(X.std(axis=0))
    Z = (X - mu) / sd
    w_std, *_ = np.linalg.lstsq(np.column_stack([np.ones(1000), Z]), y, rcond=None)
    w_raw, *_ = np.linalg.lstsq(np.column_stack([np.ones(1000), X]), y, rcond=None)
    assert nb.to_original_scale(w_std, mu, sd) == pytest.approx(w_raw, rel=1e-8)


def test_real_olist(nb):
    raw = ROOT / "data" / "raw"
    if not (raw / "olist_order_items_dataset.csv").exists():
        pytest.skip("Chưa tải Olist thật: uv run python data/download_olist.py")
    items = pd.read_csv(raw / "olist_order_items_dataset.csv")
    products = pd.read_csv(raw / "olist_products_dataset.csv")
    orders = pd.read_csv(raw / "olist_orders_dataset.csv", parse_dates=["order_purchase_timestamp"])
    table = nb.build_freight_table(items, products, orders)
    assert table.split.value_counts().to_dict() == {"train": 51216, "test": 37318, "val": 24097}

    train = table[table.split == "train"]
    X, y = train[["weight_kg", "volume_l"]].to_numpy(), train.freight_value.to_numpy()
    mu, sd = nb.standardize_fit(X)
    A = np.column_stack([np.ones(len(X)), (X - mu) / sd])
    w_std, losses = nb.gradient_descent(A, y, lr0=0.25, n_iter=300)
    assert nb.to_original_scale(w_std, mu, sd) == pytest.approx([13.2485, 1.4592, 0.1790], abs=1e-3)
    assert losses[-1] == pytest.approx(111.864, abs=1e-2)

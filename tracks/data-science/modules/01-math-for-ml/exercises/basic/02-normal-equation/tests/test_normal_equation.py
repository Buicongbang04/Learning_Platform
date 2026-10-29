import numpy as np
import pandas as pd
import pytest
from sklearn.linear_model import LinearRegression
from sklearn.metrics import r2_score

from testkit import ROOT, Exercise

ex = Exercise(__file__)


@pytest.fixture(scope="module")
def ne():
    return ex.module("normal_equation.py")


def make_data(n: int = 500, seed: int = 0):
    rng = np.random.default_rng(seed)
    weight = rng.lognormal(-0.3, 1.0, n)
    volume = 6 * weight + rng.lognormal(1.5, 1.0, n)
    X = np.column_stack([weight, volume])
    y = 13 + 1.5 * weight + 0.2 * volume + rng.normal(0, 5, n)
    return X, y


def test_add_intercept(ne):
    X = np.array([[2.0, 3.0], [4.0, 5.0], [6.0, 7.0]])
    out = ne.add_intercept(X)
    assert out.shape == (3, 3)
    assert np.all(out[:, 0] == 1.0)
    assert np.array_equal(out[:, 1:], X)
    assert np.array_equal(X, [[2.0, 3.0], [4.0, 5.0], [6.0, 7.0]])   # không sửa đầu vào


@pytest.mark.parametrize("seed", [0, 1, 2])
def test_fit_matches_lstsq_and_sklearn(ne, seed):
    X, y = make_data(seed=seed)
    w = ne.fit_normal_equation(ne.add_intercept(X), y)
    ref, *_ = np.linalg.lstsq(ne.add_intercept(X), y, rcond=None)
    assert w == pytest.approx(ref, rel=1e-8)
    lr = LinearRegression().fit(X, y)
    assert w[0] == pytest.approx(lr.intercept_, rel=1e-8)
    assert w[1:] == pytest.approx(lr.coef_, rel=1e-8)


def test_fit_does_not_invert(ne, monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("Không dùng np.linalg.inv: giải hệ bằng np.linalg.solve")

    monkeypatch.setattr(np.linalg, "inv", forbidden)
    monkeypatch.setattr(np.linalg, "pinv", forbidden)
    X, y = make_data(seed=3)
    ne.fit_normal_equation(ne.add_intercept(X), y)


def test_residual_orthogonal_to_columns(ne):
    X, y = make_data(seed=4)
    A = ne.add_intercept(X)
    w = ne.fit_normal_equation(A, y)
    residual = y - ne.predict(A, w)
    assert A.T @ residual == pytest.approx(np.zeros(3), abs=1e-6)
    assert residual.mean() == pytest.approx(0.0, abs=1e-9)    # có intercept thì residual trung bình 0


@pytest.mark.parametrize("seed", [0, 5])
def test_r2_matches_sklearn(ne, seed):
    X, y = make_data(seed=seed)
    A = ne.add_intercept(X)
    w = ne.fit_normal_equation(A, y)
    pred = ne.predict(A, w)
    assert ne.r2_score(y, pred) == pytest.approx(r2_score(y, pred), rel=1e-10)
    assert ne.r2_score(y, np.full_like(y, y.mean())) == pytest.approx(0.0, abs=1e-12)
    assert ne.r2_score(y, y) == pytest.approx(1.0)


def test_real_olist_freight():
    raw = ROOT / "data" / "raw"
    if not (raw / "olist_order_items_dataset.csv").exists():
        pytest.skip("Chưa tải Olist thật: uv run python data/download_olist.py")
    ne = ex.module("normal_equation.py")
    items = pd.read_csv(raw / "olist_order_items_dataset.csv")
    products = pd.read_csv(raw / "olist_products_dataset.csv")
    orders = pd.read_csv(raw / "olist_orders_dataset.csv", parse_dates=["order_purchase_timestamp"])
    df = items.merge(products, on="product_id").merge(orders[["order_id", "order_purchase_timestamp"]], on="order_id")
    dims = ["product_weight_g", "product_length_cm", "product_height_cm", "product_width_cm"]
    df = df.dropna(subset=dims)
    df["weight_kg"] = df.product_weight_g / 1000
    df["volume_l"] = df.product_length_cm * df.product_height_cm * df.product_width_cm / 1000
    t = df.order_purchase_timestamp
    train, test = df[t < "2018-01-01"], df[(t >= "2018-04-01") & (t < "2018-09-01")]
    assert len(train) == 51216 and len(test) == 37318

    w = ne.fit_normal_equation(ne.add_intercept(train[["weight_kg", "volume_l"]].to_numpy()), train.freight_value.to_numpy())
    assert w == pytest.approx([13.2485, 1.4592, 0.1790], abs=5e-4)
    pred = ne.predict(ne.add_intercept(test[["weight_kg", "volume_l"]].to_numpy()), w)
    assert ne.r2_score(test.freight_value.to_numpy(), pred) == pytest.approx(0.342, abs=1e-3)

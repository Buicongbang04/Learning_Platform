import numpy as np
import pandas as pd
import pytest
from sklearn.linear_model import LogisticRegression

from testkit import ROOT, Exercise

ex = Exercise(__file__)


@pytest.fixture(scope="module")
def nb():
    return ex.notebook("logistic.ipynb")


def make_data(n: int = 3000, seed: int = 0, scale: float = 1.0):
    rng = np.random.default_rng(seed)
    Z = rng.normal(size=(n, 3))
    Z[:, 2] = 0.7 * Z[:, 0] + 0.7 * Z[:, 2]
    X = np.column_stack([np.ones(n), Z])
    p = 1 / (1 + np.exp(-scale * (X @ np.array([-1.5, 0.8, -0.4, 0.5]))))
    return X, (rng.random(n) < p).astype(float)


def numeric_grad(f, w, eps=1e-6):
    out = []
    for i in range(len(w)):
        e = np.zeros_like(w)
        e[i] = eps
        out.append((f(w + e) - f(w - e)) / (2 * eps))
    return np.array(out)


ORDERS = pd.DataFrame({
    "order_id": ["o1", "o2", "o3", "o4", "o5", "o6"],
    "order_status": ["delivered", "delivered", "delivered", "canceled", "delivered", "delivered"],
    "order_purchase_timestamp": pd.to_datetime([
        "2017-06-01 10:00:00", "2018-02-01 10:00:00", "2018-05-01 10:00:00", "2018-05-02 10:00:00",
        "2018-06-01 10:00:00", "2018-09-03 10:00:00"]),
    "order_delivered_customer_date": pd.to_datetime([
        "2017-06-10 12:00:00", "2018-02-20 15:00:00", "2018-05-05 09:00:00", None, None, "2018-09-10 10:00:00"]),
    "order_estimated_delivery_date": pd.to_datetime([
        "2017-06-20 00:00:00", "2018-02-20 00:00:00", "2018-05-15 00:00:00", "2018-05-20 00:00:00",
        "2018-06-20 00:00:00", "2018-09-20 00:00:00"]),
})
REVIEWS = pd.DataFrame({
    "review_id": ["r1", "r2a", "r2b", "r3", "r4", "r6"],
    "order_id": ["o1", "o2", "o2", "o3", "o4", "o6"],
    "review_score": [5, 5, 1, 2, 1, 4],
    "review_answer_timestamp": pd.to_datetime([
        "2017-06-12", "2018-02-21", "2018-02-25", "2018-05-06", "2018-05-10", "2018-09-12"]),
})


def test_build_review_table(nb):
    out = nb.build_review_table(ORDERS, REVIEWS)
    # o4 bị huỷ, o5 chưa giao, o6 mua sau 2018-08-31 → còn o1, o2, o3
    assert sorted(out.order_id) == ["o1", "o2", "o3"]
    row = out.set_index("order_id")
    assert row.loc["o2", "bad"] == 1                          # review mới nhất của o2 là 1 sao
    assert row.loc["o2", "late"] == 1                         # giao 15:00 đúng ngày hẹn vẫn là trễ
    assert row.loc["o2", "delay_days"] == pytest.approx(15 / 24)
    assert row.loc["o1", "delivery_days"] == pytest.approx(9 + 2 / 24)
    assert (row.loc["o3", "bad"], row.loc["o3", "late"]) == (1, 0)
    assert row.split.to_dict() == {"o1": "train", "o2": "val", "o3": "test"}


@pytest.mark.parametrize("seed", [0, 1])
def test_loss_grad_hess_are_consistent(nb, seed):
    X, y = make_data(n=400, seed=seed)
    w = np.random.default_rng(seed).normal(size=4)
    for l2 in (0.0, 0.1):
        loss, grad, hess = nb.logistic_loss_grad_hess(w, X, y, l2=l2)
        f = lambda v: nb.logistic_loss_grad_hess(v, X, y, l2=l2)[0]
        g = lambda v: nb.logistic_loss_grad_hess(v, X, y, l2=l2)[1]
        assert grad == pytest.approx(numeric_grad(f, w), abs=1e-6)
        H_num = np.array([numeric_grad(lambda v: g(v)[i], w) for i in range(4)])
        assert hess == pytest.approx(H_num, abs=1e-6)
        assert np.linalg.eigvalsh(hess).min() > -1e-12        # Hessian nửa xác định dương: loss lồi


def test_l2_does_not_penalize_intercept(nb):
    X, y = make_data(n=400, seed=2)
    w = np.array([5.0, 0.0, 0.0, 0.0])
    l0 = nb.logistic_loss_grad_hess(w, X, y, l2=0.0)[0]
    l1 = nb.logistic_loss_grad_hess(w, X, y, l2=10.0)[0]
    assert l1 == pytest.approx(l0)


@pytest.mark.parametrize("seed", [0, 1, 2])
def test_newton_matches_sklearn_quickly(nb, seed):
    X, y = make_data(seed=seed)
    w, losses = nb.fit_logistic_newton(X, y)
    ref = LogisticRegression(C=np.inf, tol=1e-12, max_iter=10_000).fit(X[:, 1:], y)
    assert w[0] == pytest.approx(ref.intercept_[0], abs=1e-5)
    assert w[1:] == pytest.approx(ref.coef_[0], abs=1e-5)
    assert len(losses) <= 12                                   # hội tụ bậc hai: vài bước là xong
    assert np.all(np.diff(losses) <= 1e-12)


def test_newton_with_l2_matches_sklearn(nb):
    X, y = make_data(seed=3)
    C = 0.05
    w, _ = nb.fit_logistic_newton(X, y, l2=1 / (C * len(y)))
    ref = LogisticRegression(C=C, tol=1e-12, max_iter=10_000).fit(X[:, 1:], y)
    assert w == pytest.approx(np.r_[ref.intercept_, ref.coef_[0]], abs=1e-5)


@pytest.mark.parametrize("seed", [0, 4, 7])
def test_gd_slows_down_with_bad_scaling_newton_does_not(nb, seed):
    X, y = make_data(seed=seed)
    first_close = {}
    for scale in (1.0, 10.0):                                   # nhân một feature với 10: κ tăng ~100 lần
        Xs = X.copy()
        Xs[:, 1] *= scale
        w_newton, newton_losses = nb.fit_logistic_newton(Xs, y)
        assert len(newton_losses) <= 12                         # Newton không quan tâm thang đo
        L = np.linalg.eigvalsh(Xs.T @ Xs / len(y)).max() / 4   # cận trên độ cong của logistic loss
        w_gd, gd_losses = nb.fit_logistic_gd(Xs, y, lr=1 / L, n_iter=5000)
        assert len(gd_losses) == 5001
        assert gd_losses[-1] == pytest.approx(newton_losses[-1], abs=1e-8)
        assert w_gd == pytest.approx(w_newton, abs=1e-4)
        first_close[scale] = np.argmax(gd_losses - newton_losses[-1] < 1e-6)
    assert first_close[10.0] > 10 * first_close[1.0]


def test_l2_keeps_separable_data_finite(nb):
    rng = np.random.default_rng(5)
    x = rng.normal(size=200)
    X = np.column_stack([np.ones(200), x])
    y = (x > 0).astype(float)                                   # tách được hoàn toàn: MLE không tồn tại
    w, _ = nb.fit_logistic_newton(X, y, l2=1e-2)
    assert np.all(np.isfinite(w)) and 0 < w[1] < 100


def test_real_olist(nb):
    raw = ROOT / "data" / "raw"
    if not (raw / "olist_orders_dataset.csv").exists():
        pytest.skip("Chưa tải Olist thật: uv run python data/download_olist.py")
    dates = ["order_purchase_timestamp", "order_delivered_customer_date", "order_estimated_delivery_date"]
    orders = pd.read_csv(raw / "olist_orders_dataset.csv", parse_dates=dates)
    reviews = pd.read_csv(raw / "olist_order_reviews_dataset.csv", parse_dates=["review_answer_timestamp"])
    table = nb.build_review_table(orders, reviews)
    train = table[table.split == "train"]
    assert len(train) == 43362
    assert table.bad.mean() == pytest.approx(0.128, abs=0.002)
    feats = ["late", "delay_days", "delivery_days"]
    Z = (train[feats] - train[feats].mean()) / train[feats].std(ddof=0)
    X = np.column_stack([np.ones(len(Z)), Z.to_numpy()])
    w, losses = nb.fit_logistic_newton(X, train.bad.to_numpy(dtype=float))
    assert w == pytest.approx([-2.1452, 0.4517, -0.0464, 0.3332], abs=1e-3)
    assert len(losses) <= 10

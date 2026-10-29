import numpy as np
import pandas as pd
import pytest

from testkit import Exercise

ex = Exercise(__file__)


@pytest.fixture(scope="module")
def mf():
    return ex.module("mf.py")


def synthetic(seed: int, n_users: int = 300, n_items: int = 200, rank: int = 3, density: float = 0.25):
    """Rating = 3.5 + bias user + bias item + tích vô hướng hạng 3 + nhiễu 0.3; chia ngẫu nhiên 80/20."""
    rng = np.random.default_rng(seed)
    P = rng.normal(0, 0.6, (n_users, rank))
    Q = rng.normal(0, 0.6, (n_items, rank))
    bu = rng.normal(0, 0.4, n_users)
    bi = rng.normal(0, 0.5, n_items)
    u, i = np.nonzero(rng.random((n_users, n_items)) < density)
    r = 3.5 + bu[u] + bi[i] + np.sum(P[u] * Q[i], axis=1) + rng.normal(0, 0.3, len(u))
    df = pd.DataFrame({"userId": u + 1, "movieId": i + 1000, "rating": r})
    is_test = rng.random(len(df)) < 0.2
    return df[~is_test], df[is_test]


def bias_only_rmse(train, test, reg=5.0):
    mu = train.rating.mean()
    bi = (train.rating - mu).groupby(train.movieId).sum() / (train.groupby("movieId").size() + reg)
    rest = train.rating - mu - train.movieId.map(bi)
    bu = rest.groupby(train.userId).sum() / (train.groupby("userId").size() + reg)
    pred = mu + test.movieId.map(bi).fillna(0) + test.userId.map(bu).fillna(0)
    return float(np.sqrt(np.mean((pred - test.rating) ** 2)))


def rmse(model, test):
    return float(np.sqrt(np.mean((model.predict(test.userId.to_numpy(), test.movieId.to_numpy()) - test.rating) ** 2)))


@pytest.mark.parametrize("seed", [0, 1, 2])
def test_learns_low_rank_structure(mf, seed):
    train, test = synthetic(seed)
    model = mf.MatrixFactorization(n_factors=10, seed=0).fit(train)
    err = rmse(model, test)
    assert err < 0.85 * bias_only_rmse(train, test)
    assert err < 0.6


def test_predict_shape_and_reproducible(mf):
    train, test = synthetic(3)
    a = mf.MatrixFactorization(n_factors=5, seed=1).fit(train)
    b = mf.MatrixFactorization(n_factors=5, seed=1).fit(train)
    pa = a.predict(test.userId.to_numpy(), test.movieId.to_numpy())
    assert pa.shape == (len(test),)
    assert np.allclose(pa, b.predict(test.userId.to_numpy(), test.movieId.to_numpy()))


def test_cold_start_falls_back_to_biases(mf):
    train, _ = synthetic(4)
    model = mf.MatrixFactorization(n_factors=5, seed=0).fit(train)
    mu = train.rating.mean()
    # user lạ + phim lạ → trung bình toàn cục của train
    assert model.predict(np.array([10**6]), np.array([10**6]))[0] == pytest.approx(mu)
    # user lạ: mọi user lạ nhận cùng một dự đoán, và thứ tự theo chất lượng phim
    items = np.sort(train.movieId.unique())
    cold_a = model.predict(np.full(len(items), 10**6), items)
    cold_b = model.predict(np.full(len(items), 10**6 + 1), items)
    assert np.allclose(cold_a, cold_b)
    item_mean = train.groupby("movieId").rating.mean().reindex(items).to_numpy()
    assert np.corrcoef(cold_a, item_mean)[0, 1] > 0.8
    # phim lạ cho user đã biết: hữu hạn, không lỗi
    assert np.isfinite(model.predict(np.array([1]), np.array([10**6]))).all()


def test_recommend(mf):
    train, _ = synthetic(5)
    model = mf.MatrixFactorization(n_factors=5, seed=0).fit(train)
    seen = set(train[train.userId == 1].movieId)
    recs = model.recommend(1, k=10, exclude=seen)
    assert len(recs) == 10 and len(set(recs)) == 10
    assert not set(recs) & seen
    assert set(recs) <= set(train.movieId)
    scores = model.predict(np.full(10, 1), np.array(recs))
    assert np.all(np.diff(scores) <= 1e-12)
    # không phim nào ngoài danh sách (và chưa xem) có điểm cao hơn phim cuối danh sách
    others = np.array(sorted(set(train.movieId) - seen - set(recs)))
    assert model.predict(np.full(len(others), 1), others).max() <= scores[-1] + 1e-12


def test_real_movielens(mf):
    ratings = pd.read_csv(ex.dataset("movielens") / "ratings.csv").sort_values(["userId", "timestamp", "movieId"])
    from_end = ratings.groupby("userId").cumcount(ascending=False)
    is_test = from_end < np.ceil(0.2 * ratings.groupby("userId").movieId.transform("size"))
    train, test = ratings[~is_test], ratings[is_test]
    model = mf.MatrixFactorization(seed=0).fit(train)
    pred = np.clip(model.predict(test.userId.to_numpy(), test.movieId.to_numpy()), 0.5, 5.0)
    err = float(np.sqrt(np.mean((pred - test.rating) ** 2)))
    assert err < 0.92                       # trung bình toàn cục: 1.068; chỉ bias: 0.902


def test_report_written():
    report = ex.read("REPORT.md")
    assert "TODO" not in report
    assert len(report.split()) >= 300

import numpy as np
import pandas as pd
import pytest
from sklearn.metrics import average_precision_score

from testkit import Exercise

ex = Exercise(__file__)


@pytest.fixture(scope="module")
def nb():
    return ex.notebook("fraud.ipynb")


def blobs(seed: int, n_normal: int = 3000, n_anomaly: int = 30):
    """Bình thường nằm gần một mặt phẳng 3 chiều trong không gian 10 chiều; bất thường lệch khỏi mặt phẳng."""
    basis = np.linalg.qr(np.random.default_rng(0).normal(size=(10, 3)))[0].T   # cùng mặt phẳng cho mọi seed
    rng = np.random.default_rng(seed)
    normal = rng.normal(size=(n_normal, 3)) @ basis * 3 + rng.normal(0, 0.1, (n_normal, 10))
    anomaly = rng.normal(size=(n_anomaly, 3)) @ basis * 3 + rng.normal(0, 2.0, (n_anomaly, 10))
    X = np.vstack([normal, anomaly])
    y = np.r_[np.zeros(n_normal), np.ones(n_anomaly)].astype(int)
    return X, y


def far_outliers(seed: int, n_normal: int = 3000, n_anomaly: int = 30):
    """Bình thường là một đám mây chuẩn 5 chiều; bất thường rải đều trong hộp lớn, xa tâm."""
    rng = np.random.default_rng(seed)
    normal = rng.normal(size=(n_normal, 5))
    anomaly = rng.uniform(4, 8, (n_anomaly, 5)) * rng.choice([-1, 1], (n_anomaly, 5))
    X = np.vstack([normal, anomaly])
    y = np.r_[np.zeros(n_normal), np.ones(n_anomaly)].astype(int)
    return X, y


def test_day_split(nb):
    df = pd.DataFrame({"Time": [0.0, 86_399.0, 86_400.0, 172_000.0], "Class": [0, 1, 0, 1]})
    train, test = nb.day_split(df)
    assert list(train.Time) == [0.0, 86_399.0]
    assert list(test.Time) == [86_400.0, 172_000.0]


@pytest.mark.parametrize("seed", [0, 1, 2])
def test_average_precision_matches_sklearn(nb, seed):
    rng = np.random.default_rng(seed)
    y = (rng.random(2000) < 0.05).astype(int)
    score = y * rng.normal(1, 1, 2000) + rng.normal(0, 1, 2000)
    assert nb.average_precision(y, score) == pytest.approx(average_precision_score(y, score), abs=1e-12)


def test_average_precision_groups_ties(nb):
    rng = np.random.default_rng(3)
    y = (rng.random(3000) < 0.1).astype(int)
    score = np.round(y * 0.5 + rng.random(3000), 1)      # chỉ khoảng 15 giá trị khác nhau
    assert nb.average_precision(y, score) == pytest.approx(average_precision_score(y, score), abs=1e-12)
    # mọi điểm bằng nhau → một ngưỡng duy nhất → AP = tỉ lệ dương tính
    assert nb.average_precision(y, np.zeros(3000)) == pytest.approx(y.mean())


def test_average_precision_extremes(nb):
    y = np.array([0, 1, 0, 0, 1, 0])
    assert nb.average_precision(y, np.array([0.1, 0.9, 0.2, 0.3, 0.8, 0.0])) == pytest.approx(1.0)
    # thứ hạng: 0, 0, 1 (P = 1/3), 0, 1 (P = 2/5)... → (1/3 + 2/5) / 2
    assert nb.average_precision(y, np.array([0.9, 0.5, 0.0, 0.8, 0.6, 0.7])) == pytest.approx(
        average_precision_score(y, [0.9, 0.5, 0.0, 0.8, 0.6, 0.7]))


def test_random_scores_give_ap_near_prevalence(nb):
    rng = np.random.default_rng(4)
    y = (rng.random(50_000) < 0.01).astype(int)
    assert nb.average_precision(y, rng.random(50_000)) == pytest.approx(y.mean(), abs=0.004)


def test_alert_metrics(nb):
    y = np.array([1, 0, 1, 0, 0, 1, 0, 0])
    score = np.array([0.9, 0.8, 0.7, 0.6, 0.5, 0.4, 0.3, 0.2])
    out = nb.alert_metrics(y, score, 3)
    assert out == pytest.approx({"precision": 2 / 3, "recall": 2 / 3})
    assert nb.alert_metrics(y, score, 8) == pytest.approx({"precision": 3 / 8, "recall": 1.0})


@pytest.mark.parametrize("seed", [0, 1, 2])
def test_isolation_forest_direction_and_quality(nb, seed):
    X, y = far_outliers(seed)
    X_train, _ = far_outliers(seed + 100, n_anomaly=0)
    s = nb.isolation_forest_scores(X_train, X, seed=0, n_estimators=100)
    assert s.shape == (len(X),)
    assert s[y == 1].mean() > s[y == 0].mean()
    assert average_precision_score(y, s) > 0.9


@pytest.mark.parametrize("seed", [0, 1, 2])
def test_pca_reconstruction_finds_off_subspace_points(nb, seed):
    X, y = blobs(seed)
    X_train, _ = blobs(seed + 100, n_anomaly=0)
    s = nb.pca_reconstruction_scores(X_train, X, n_components=3)
    assert s.shape == (len(X),)
    assert average_precision_score(y, s) > 0.95


def test_scores_do_not_depend_on_other_test_rows(nb):
    X, _ = blobs(7)
    X_train, _ = blobs(8, n_anomaly=0)
    full_iso = nb.isolation_forest_scores(X_train, X, seed=1, n_estimators=50)
    part_iso = nb.isolation_forest_scores(X_train, X[:20], seed=1, n_estimators=50)
    assert np.allclose(full_iso[:20], part_iso)
    full_pca = nb.pca_reconstruction_scores(X_train, X, n_components=3)
    part_pca = nb.pca_reconstruction_scores(X_train, X[:20] * 1.0, n_components=3)
    assert np.allclose(full_pca[:20], part_pca)


def test_pca_standardises_with_train_statistics(nb):
    X_train, _ = blobs(9, n_anomaly=0)
    X_test, _ = blobs(10, n_anomaly=0)
    base = nb.pca_reconstruction_scores(X_train, X_test, n_components=3)
    # đổi đơn vị một cột ở cả train và test: chuẩn hoá theo train nên điểm không đổi
    X_train2, X_test2 = X_train.copy(), X_test.copy()
    X_train2[:, 0] *= 1000
    X_test2[:, 0] *= 1000
    assert np.allclose(base, nb.pca_reconstruction_scores(X_train2, X_test2, n_components=3), rtol=1e-6)


def test_real_creditcard(nb):
    df = pd.read_csv(ex.dataset("creditcard-fraud") / "creditcard.csv")
    train, test = nb.day_split(df)
    assert (len(train), int(train.Class.sum()), len(test), int(test.Class.sum())) == (144786, 281, 140021, 211)
    X_tr = train[nb.FEATURES].assign(Amount=np.log1p(train.Amount))
    X_te = test[nb.FEATURES].assign(Amount=np.log1p(test.Amount))
    y = test.Class.to_numpy()
    iso = nb.average_precision(y, nb.isolation_forest_scores(X_tr, X_te, seed=0, n_estimators=100))
    clean = nb.average_precision(y, nb.pca_reconstruction_scores(X_tr[train.Class.to_numpy() == 0], X_te))
    dirty = nb.average_precision(y, nb.pca_reconstruction_scores(X_tr, X_te))
    assert 0.05 < iso < 0.25             # hơn 30 lần tỉ lệ nền 0.15%, nhưng còn xa mới dùng được
    assert clean == pytest.approx(0.209, abs=0.01)
    assert dirty < 0.08 < clean           # học trên dữ liệu lẫn gian lận làm hỏng bộ phát hiện

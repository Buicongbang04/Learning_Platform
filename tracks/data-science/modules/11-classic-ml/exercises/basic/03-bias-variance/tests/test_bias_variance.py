import numpy as np
import pytest

from testkit import Exercise

ex = Exercise(__file__)

X_TEST = np.linspace(0.05, 0.95, 40)


def f(x):
    return np.sin(2 * np.pi * x)


def mean_model(x_train, y_train, x_test):
    return np.full(len(x_test), y_train.mean())


@pytest.fixture(scope="module")
def bv():
    return ex.module("bias_variance.py")


def test_shape_and_reproducible(bv):
    a = bv.simulate_predictions(mean_model, f, X_TEST, n_train=30, noise_sd=0.3, n_rep=50, seed=1)
    b = bv.simulate_predictions(mean_model, f, X_TEST, n_train=30, noise_sd=0.3, n_rep=50, seed=1)
    c = bv.simulate_predictions(mean_model, f, X_TEST, n_train=30, noise_sd=0.3, n_rep=50, seed=2)
    assert a.shape == (50, len(X_TEST))
    np.testing.assert_allclose(a, b)
    assert not np.allclose(a, c)


def test_training_sets_are_fresh_and_sized(bv):
    seen = []

    def spy(x_train, y_train, x_test):
        seen.append((len(x_train), float(x_train.min()), float(x_train.max()), float(y_train.std())))
        return np.zeros(len(x_test))

    bv.simulate_predictions(spy, f, X_TEST, n_train=25, noise_sd=0.3, n_rep=20, seed=0)
    assert len(seen) == 20 and all(s[0] == 25 for s in seen)
    assert len({s[1] for s in seen}) == 20              # mỗi lần một tập train mới
    assert all(0 <= s[1] and s[2] <= 1 for s in seen)   # x ~ Uniform(0, 1)


def test_decompose_identity(bv):
    rng = np.random.default_rng(0)
    preds = rng.normal(size=(30, len(X_TEST))) + f(X_TEST)
    out = bv.decompose(preds, f(X_TEST), noise_sd=0.3)
    assert set(out) == {"bias2", "variance", "noise", "expected_mse"}
    assert out["noise"] == pytest.approx(0.09)
    assert out["bias2"] + out["variance"] == pytest.approx(np.mean((preds - f(X_TEST)) ** 2))
    assert out["expected_mse"] == pytest.approx(out["bias2"] + out["variance"] + out["noise"])


def test_mean_model_is_high_bias_low_variance(bv):
    preds = bv.simulate_predictions(mean_model, f, X_TEST, n_train=50, noise_sd=0.3, n_rep=300, seed=3)
    out = bv.decompose(preds, f(X_TEST), noise_sd=0.3)
    assert out["bias2"] == pytest.approx(np.mean(f(X_TEST) ** 2), rel=0.1)   # ≈ 0.5: model hằng số
    assert out["variance"] < 0.05


def test_knn_k_controls_tradeoff(bv):
    common = dict(f=f, x_test=X_TEST, n_train=60, noise_sd=0.3, n_rep=200, seed=4)
    flexible = bv.decompose(bv.simulate_predictions(bv.knn_fit_predict(1), **common), f(X_TEST), 0.3)
    smooth = bv.decompose(bv.simulate_predictions(bv.knn_fit_predict(30), **common), f(X_TEST), 0.3)
    middle = bv.decompose(bv.simulate_predictions(bv.knn_fit_predict(7), **common), f(X_TEST), 0.3)
    assert flexible["variance"] > 3 * smooth["variance"]
    assert smooth["bias2"] > 3 * flexible["bias2"]
    assert middle["expected_mse"] < min(flexible["expected_mse"], smooth["expected_mse"])

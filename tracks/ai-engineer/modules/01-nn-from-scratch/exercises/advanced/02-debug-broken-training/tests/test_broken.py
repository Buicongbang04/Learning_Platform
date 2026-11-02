import inspect
import re

import numpy as np
import pytest
from testkit import Exercise

ex = Exercise(__file__)


@pytest.fixture(scope="module")
def nb():
    return ex.notebook("broken.ipynb")


def reference_spirals(n_per_class: int, n_classes: int, seed: int) -> tuple[np.ndarray, np.ndarray]:
    rng = np.random.default_rng(seed)
    X, y = [], []
    for k in range(n_classes):
        r = np.linspace(0.05, 1.0, n_per_class)
        t = k * 2 * np.pi / n_classes + 8 * r + rng.normal(0, 0.2, n_per_class)
        X.append(np.c_[r * np.sin(t), r * np.cos(t)])
        y.append(np.full(n_per_class, k))
    return np.concatenate(X), np.concatenate(y)


def check_setup_unchanged(nb) -> None:
    """Dữ liệu và siêu tham số mặc định phải giữ nguyên: sửa bug ở gốc, không bù triệu chứng."""
    X, y = nb.make_spirals(50, 3, 7)
    Xr, yr = reference_spirals(50, 3, 7)
    np.testing.assert_allclose(X, Xr, err_msg="không đổi make_spirals")
    assert np.array_equal(y, yr), "không đổi make_spirals"
    defaults = {k: v.default for k, v in inspect.signature(nb.train).parameters.items() if k != "seed"}
    assert defaults == {"epochs": 60, "lr": 0.05, "batch_size": 32, "momentum": 0.9}, (
        "không đổi siêu tham số mặc định của train"
    )


@pytest.mark.parametrize("seed", [0, 1, 2])
def test_train_reaches_95(nb, seed):
    check_setup_unchanged(nb)
    acc = nb.train(seed)
    assert acc >= 0.95, f"test accuracy {acc:.4f}"


def test_gradient_check_passes(nb):
    assert nb.gradient_check_passes() is True


def test_gradients_match_finite_differences(nb):
    """Gradient check độc lập với hàm trong notebook: MLP khác cỡ, batch khác, mọi phần tử mọi tham số."""
    rng = np.random.default_rng(5)
    model = nb.MLP(3, 4, 2, seed=2)
    for name in ["b1", "b2", "b3"]:
        b = getattr(model, name)
        b[...] = rng.normal(0, 0.1, b.shape)
    X, y = rng.normal(size=(5, 3)), rng.integers(0, 2, 5)
    model.loss_and_backward(X, y)
    analytic = [g.copy() for _, g in model.params()]
    for (p, _), ga in zip(model.params(), analytic):
        numeric = np.zeros_like(p)
        for i in np.ndindex(p.shape):
            old = p[i]
            p[i] = old + 1e-6
            plus = model.loss_and_backward(X, y)
            p[i] = old - 1e-6
            minus = model.loss_and_backward(X, y)
            p[i] = old
            numeric[i] = (plus - minus) / 2e-6
        np.testing.assert_allclose(ga, numeric, rtol=1e-5, atol=1e-8)


def test_bugs_written():
    doc = ex.read("BUGS.md")
    assert "TODO" not in doc
    assert len(re.findall(r"^## Bug \d", doc, re.M)) >= 4, "mỗi bug một mục `## Bug N: ...`"
    assert len(doc.split()) >= 250

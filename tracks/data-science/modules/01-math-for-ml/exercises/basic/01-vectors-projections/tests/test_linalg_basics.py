import numpy as np
import pytest

from testkit import Exercise

ex = Exercise(__file__)


@pytest.fixture(scope="module")
def la():
    return ex.module("linalg_basics.py")


def design(n: int = 200, seed: int = 0) -> np.ndarray:
    """Ma trận thiết kế nhỏ: cột hằng + khối lượng (kg) + thể tích (lít), giống bài Olist."""
    rng = np.random.default_rng(seed)
    weight = rng.lognormal(-0.3, 1.0, n)
    volume = 6 * weight + rng.lognormal(1.5, 1.0, n)
    return np.column_stack([np.ones(n), weight, volume])


def test_cosine_similarity_basic_cases(la):
    assert la.cosine_similarity(np.array([1.0, 0.0]), np.array([0.0, 3.0])) == pytest.approx(0.0, abs=1e-12)
    assert la.cosine_similarity(np.array([1.0, 2.0, 3.0]), np.array([2.0, 4.0, 6.0])) == pytest.approx(1.0)
    assert la.cosine_similarity(np.array([1.0, 2.0]), np.array([-1.0, -2.0])) == pytest.approx(-1.0)
    assert la.cosine_similarity(np.array([1.0, 1.0]), np.array([1.0, 0.0])) == pytest.approx(1 / np.sqrt(2))


def test_cosine_similarity_ignores_scale(la):
    rng = np.random.default_rng(1)
    a, b = rng.normal(size=10), rng.normal(size=10)
    assert la.cosine_similarity(a, b) == pytest.approx(la.cosine_similarity(1000 * a, 0.001 * b))


def test_project_onto_vector(la):
    v, u = np.array([3.0, 4.0]), np.array([1.0, 0.0])
    assert la.project_onto_vector(v, u) == pytest.approx(np.array([3.0, 0.0]))
    rng = np.random.default_rng(2)
    v, u = rng.normal(size=5), rng.normal(size=5)
    p = la.project_onto_vector(v, u)
    assert np.dot(v - p, u) == pytest.approx(0.0, abs=1e-10)          # phần dư vuông góc với u
    assert la.project_onto_vector(p, u) == pytest.approx(p)          # chiếu hai lần = chiếu một lần
    assert la.project_onto_vector(v, 7 * u) == pytest.approx(p)      # không phụ thuộc độ dài u


def test_projection_matrix_properties(la):
    X = design()
    P = la.projection_matrix(X)
    assert P.shape == (200, 200)
    assert np.allclose(P, P.T, atol=1e-10)              # đối xứng
    assert np.allclose(P @ P, P, atol=1e-8)             # idempotent
    assert np.trace(P) == pytest.approx(X.shape[1])     # trace = số cột độc lập
    assert np.allclose(P @ X, X, atol=1e-8)             # cột của X đã nằm sẵn trong không gian cột


def test_projection_gives_least_squares_fit(la):
    X = design(seed=3)
    rng = np.random.default_rng(3)
    y = 13 + 1.5 * X[:, 1] + 0.2 * X[:, 2] + rng.normal(0, 5, len(X))
    P = la.projection_matrix(X)
    w, *_ = np.linalg.lstsq(X, y, rcond=None)
    assert P @ y == pytest.approx(X @ w)
    assert X.T @ (y - P @ y) == pytest.approx(np.zeros(3), abs=1e-7)   # residual ⟂ mọi cột


def test_condition_number_matches_numpy(la):
    X = design(seed=4)
    assert la.condition_number(X) == pytest.approx(np.linalg.cond(X), rel=1e-10)
    Q, _ = np.linalg.qr(X)
    assert la.condition_number(Q) == pytest.approx(1.0)


def test_condition_number_grows_with_bad_units(la):
    X = design(seed=5)
    grams = X.copy()
    grams[:, 1] *= 1000      # kg → g
    grams[:, 2] *= 1000      # lít → cm³
    assert la.condition_number(grams) > 100 * la.condition_number(X)

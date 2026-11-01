import numpy as np
import pytest

from testkit import Exercise

ex = Exercise(__file__)


@pytest.fixture(scope="module")
def nb():
    return ex.notebook("pq.ipynb")


def data(n=500, d=8, seed=0):
    rng = np.random.default_rng(seed)
    return rng.normal(size=(n, d)).astype(np.float32)


def test_train_shapes_init_and_errors(nb):
    x = data()
    cb = nb.pq_train(x, 2, ks=4, n_iter=0, seed=3)
    assert cb.shape == (2, 4, 4) and cb.dtype == np.float32
    for j in range(2):
        want = x[:, 4 * j:4 * (j + 1)][np.random.default_rng(3 + j).choice(500, 4, replace=False)]
        np.testing.assert_allclose(cb[j], want, err_msg=f"đoạn {j} khởi tạo bằng default_rng(seed + j)")
    with pytest.raises(ValueError):
        nb.pq_train(x, 3, ks=4)


def test_encode_is_nearest_per_subspace(nb):
    x = data()
    cb = nb.pq_train(x, 4, ks=8, n_iter=5, seed=0)
    codes = nb.pq_encode(x, cb)
    assert codes.shape == (500, 4) and codes.dtype == np.uint8
    for j in range(4):
        sub = x[:, 2 * j:2 * (j + 1)]
        want = np.argmin(((sub[:, None, :] - cb[j][None]) ** 2).sum(-1), axis=1)
        assert (codes[:, j] == want).all()


def test_decode_and_error_shrinks_with_ks(nb):
    x = data(n=2000, d=16, seed=1)
    errs = []
    for ks in (4, 16, 64):
        cb = nb.pq_train(x, 4, ks=ks, n_iter=8, seed=0)
        rec = nb.pq_decode(nb.pq_encode(x, cb), cb)
        assert rec.shape == x.shape and rec.dtype == np.float32
        errs.append(float(((x - rec) ** 2).sum(1).mean()))
    assert errs[0] > errs[1] > errs[2], errs


def test_search_equals_exact_on_decoded(nb):
    x = data(n=800, d=16, seed=2)
    cb = nb.pq_train(x, 8, ks=16, n_iter=5, seed=0)
    codes = nb.pq_encode(x, cb)
    rec = nb.pq_decode(codes, cb)
    rng = np.random.default_rng(3)
    for q in rng.normal(size=(5, 16)).astype(np.float32):
        want = np.argsort(((rec - q) ** 2).sum(1), kind="stable")[:10].tolist()
        got = nb.pq_search(q, codes, cb, 10)
        assert got == want and all(isinstance(i, int) for i in got)


def test_search_ties_smaller_index(nb):
    cb = np.array([[[0.0], [1.0]], [[0.0], [1.0]]], dtype=np.float32)       # m = 2, ks = 2, ds = 1
    codes = np.array([[1, 1], [0, 1], [1, 0], [0, 0]], dtype=np.uint8)
    assert nb.pq_search(np.array([0.0, 0.0], dtype=np.float32), codes, cb, 4) == [3, 1, 2, 0]


def test_pareto_front(nb):
    rows = [
        {"name": "flat", "recall": 1.0, "ms": 9.0, "bytes": 4096},
        {"name": "hnsw", "recall": 0.97, "ms": 0.5, "bytes": 4224},
        {"name": "ivf-slow", "recall": 0.95, "ms": 2.0, "bytes": 4100},
        {"name": "pq64", "recall": 0.60, "ms": 1.0, "bytes": 64},
        {"name": "pq64-copy", "recall": 0.60, "ms": 1.0, "bytes": 64},
        {"name": "pq32", "recall": 0.40, "ms": 1.5, "bytes": 32},
        {"name": "bad", "recall": 0.40, "ms": 1.6, "bytes": 64},
    ]
    names = [r["name"] for r in nb.pareto_front(rows)]
    assert names == ["flat", "hnsw", "ivf-slow", "pq64", "pq64-copy", "pq32"], \
        "ivf-slow: không dòng nào vừa recall >= 0.95, ms <= 2, bytes <= 4100; hai dòng bằng nhau không trội nhau"

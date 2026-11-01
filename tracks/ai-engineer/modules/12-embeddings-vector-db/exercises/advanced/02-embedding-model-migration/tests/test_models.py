import numpy as np
import pytest

from testkit import Exercise

ex = Exercise(__file__)


@pytest.fixture(scope="module")
def nb():
    return ex.notebook("models.ipynb")


def test_int8_per_dimension(nb):
    x = np.array([[1.0, -0.5, 0.0], [-2.0, 0.25, 0.0], [0.5, 1.0, 0.0]], dtype=np.float32)
    codes, scale = nb.quantize_int8(x)
    assert codes.dtype == np.int8 and scale.dtype == np.float32 and scale.shape == (3,)
    np.testing.assert_allclose(scale, [2 / 127, 1 / 127, 1.0], rtol=1e-6), "mỗi chiều một scale; chiều toàn 0 dùng 1"
    assert codes[:, 0].tolist() == [64, -127, 32]           # round(1 / (2/127)) = round(63.5) = 64 (làm tròn về số chẵn)
    assert codes[:, 1].tolist() == [-64, 32, 127]
    rec = nb.dequantize_int8(codes, scale)
    assert rec.dtype == np.float32
    assert np.abs(rec - x).max() <= (scale / 2).max() + 1e-6


def test_int8_keeps_ranking_on_unit_vectors(nb):
    rng = np.random.default_rng(0)
    x = rng.normal(size=(500, 64)).astype(np.float32)
    x /= np.linalg.norm(x, axis=1, keepdims=True)
    rec = nb.dequantize_int8(*nb.quantize_int8(x))
    q = x[:20]
    exact = np.argsort(-(q @ x.T), axis=1)[:, :10]
    approx = np.argsort(-(q @ rec.T), axis=1)[:, :10]
    assert np.mean([len(set(a) & set(b)) / 10 for a, b in zip(exact, approx)]) > 0.9


def test_binarize_layout(nb):
    x = np.array([[0.3, -1.0, 0.0, 2.0, -0.1, 0.1, 5.0, -5.0, 1.0, 0.0]], dtype=np.float32)
    bits = nb.binarize(x)
    assert bits.dtype == np.uint8 and bits.shape == (1, 2)
    assert bits.tolist() == [[0b10010110, 0b10000000]], "bit 1 khi > 0 (0 là bit 0), bit đầu là bit cao"


def test_hamming_topk(nb):
    db = np.array([[0b11110000], [0b11110001], [0b00001111], [0b11110000], [0b01110000]], dtype=np.uint8)
    q = np.array([0b11110000], dtype=np.uint8)
    assert nb.hamming_topk(q, db, 5) == [0, 3, 1, 4, 2]
    out = nb.hamming_topk(q, db, 2)
    assert out == [0, 3] and all(isinstance(i, int) for i in out)


def test_rescore(nb):
    x = np.array([[1, 0], [0.9, 0.1], [0.6, 0.8], [0.9, 0.1], [0, 1]], dtype=np.float32)
    q = np.array([1.0, 0.0], dtype=np.float32)
    assert nb.rescore(q, [4, 2, 3, 1], x, 3) == [1, 3, 2], "chỉ trong candidates, bằng điểm thì chỉ số nhỏ"
    assert nb.rescore(q, np.array([2, 0]), x, 5) == [0, 2]


def test_binary_with_rescoring_beats_binary(nb):
    rng = np.random.default_rng(1)
    x = rng.normal(size=(3000, 128)).astype(np.float32)
    x /= np.linalg.norm(x, axis=1, keepdims=True)
    bits = nb.binarize(x)
    queries = x[:30] + 0.3 * rng.normal(size=(30, 128)).astype(np.float32)
    exact = np.argsort(-(queries @ x.T), axis=1)[:, :10]
    plain, rescored = [], []
    for q, e in zip(queries, exact):
        qb = nb.binarize(q[None])[0]
        plain.append(len(set(nb.hamming_topk(qb, bits, 10)) & set(e)) / 10)
        cands = nb.hamming_topk(qb, bits, 200)
        rescored.append(len(set(nb.rescore(q, cands, x, 10)) & set(e)) / 10)
    assert np.mean(rescored) > np.mean(plain) + 0.1

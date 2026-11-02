"""M02: chuẩn hoá vector, dense top-k, gộp điểm chunk lên điều, RRF."""

import numpy as np
import pytest


def test_normalize_rows(la):
    fusion = la("fusion")
    m = np.array([[3.0, 4.0], [0.0, 0.0], [np.nan, 1.0], [1.0, 0.0]])
    before = m.copy()
    out, bad = fusion.normalize_rows(m)
    np.testing.assert_array_equal(m, before)
    assert out.dtype == np.float32
    np.testing.assert_allclose(out, [[0.6, 0.8], [0, 0], [0, 0], [1, 0]], atol=1e-6)
    assert bad == 2
    assert np.isfinite(out).all()


def test_dense_top_k(la):
    fusion = la("fusion")
    m = np.array([[1.0, 0.0], [0.0, 1.0], [0.6, 0.8], [1.0, 0.0]], dtype=np.float32)
    assert fusion.dense_top_k(m, np.array([1.0, 0.0], dtype=np.float32), 3) == [0, 3, 2]
    assert fusion.dense_top_k(m, np.array([0.0, 1.0], dtype=np.float32), 1) == [1]


def test_max_by_article(la):
    fusion = la("fusion")
    out = fusion.max_by_article(["B", "A", "B", "C", "A"], [0.2, 0.5, 0.9, 0.5, 0.1])
    assert out == [("B", 0.9), ("A", 0.5), ("C", 0.5)]
    with pytest.raises(ValueError):
        fusion.max_by_article(["A"], [0.1, 0.2])


def test_rrf_hand_example(la):
    fusion = la("fusion")
    out = fusion.rrf([["A", "B", "C"], ["C", "A", "D"]], k=60)
    assert out == ["A", "C", "B", "D"]
    assert fusion.rrf([["A", "B"]], k=1) == ["A", "B"]
    assert fusion.rrf([["B"], ["A"]]) == ["A", "B"]
    assert fusion.rrf([["A", "B"], ["X", "Y", "B"]], k=1) == ["B", "A", "X", "Y"]


def test_rrf_weights(la):
    fusion = la("fusion")
    bm25, dense = ["A", "B", "C"], ["C", "A", "D"]
    assert fusion.rrf([bm25, dense], k=60, weights=[1.0, 1.0]) == fusion.rrf([bm25, dense], k=60)
    weighted = fusion.rrf([bm25, dense], k=60, weights=[1.0, 2.0])
    assert weighted[:2] == ["C", "A"]
    assert weighted.index("D") < weighted.index("B")
    with pytest.raises(ValueError):
        fusion.rrf([bm25, dense], weights=[1.0])

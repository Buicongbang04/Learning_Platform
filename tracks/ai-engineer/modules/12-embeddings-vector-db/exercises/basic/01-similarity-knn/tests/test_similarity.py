import numpy as np
import pytest

from testkit import Exercise

ex = Exercise(__file__)


@pytest.fixture(scope="module")
def sim():
    return ex.module("similarity.py")


# ---------- l2_normalize ----------


def test_normalize_values_dtype_and_no_mutation(sim):
    x = np.array([[3.0, 4.0], [0.0, -2.0]])
    before = x.copy()
    out = sim.l2_normalize(x)
    assert out.dtype == np.float32
    np.testing.assert_allclose(out, [[0.6, 0.8], [0.0, -1.0]], rtol=1e-6)
    np.testing.assert_array_equal(x, before, err_msg="không được sửa mảng đầu vào")


def test_normalize_zero_row_and_1d(sim):
    out = sim.l2_normalize(np.array([[0.0, 0.0, 0.0], [1.0, 2.0, 2.0]]))
    assert not np.isnan(out).any(), "vector 0 phải giữ nguyên 0, không thành NaN"
    np.testing.assert_allclose(out, [[0, 0, 0], [1 / 3, 2 / 3, 2 / 3]], rtol=1e-6)
    v = sim.l2_normalize(np.array([0.0, 5.0]))
    assert v.shape == (2,)
    np.testing.assert_allclose(v, [0.0, 1.0])


# ---------- pairwise ----------

Q = np.array([[1.0, 0.0], [1.0, 1.0]])
B = np.array([[2.0, 0.0], [0.0, 1.0], [3.0, 4.0]])


def test_pairwise_hand_values(sim):
    np.testing.assert_allclose(sim.pairwise(Q, B, "dot"), [[2, 0, 3], [2, 1, 7]], rtol=1e-6)
    r = 1 / np.sqrt(2)
    np.testing.assert_allclose(sim.pairwise(Q, B, "cosine"), [[1, 0, 0.6], [r, r, 7 / (5 * np.sqrt(2))]], rtol=1e-5)
    np.testing.assert_allclose(sim.pairwise(Q, B, "l2"), [[1, 2, 20], [2, 1, 13]], rtol=1e-5)
    assert sim.pairwise(Q, B, "dot").shape == (2, 3)


def test_pairwise_cosine_zero_vector_is_zero(sim):
    out = sim.pairwise(np.array([[0.0, 0.0]]), B, "cosine")
    assert not np.isnan(out).any()
    np.testing.assert_allclose(out, 0.0)


def test_pairwise_l2_never_negative(sim):
    rng = np.random.default_rng(0)
    x = (1000 + rng.normal(size=(20, 64))).astype(np.float32)
    d = sim.pairwise(x, x, "l2")
    assert (d >= 0).all(), "bình phương khoảng cách không được âm (sai số làm tròn khi khai triển)"


def test_pairwise_unknown_metric(sim):
    with pytest.raises(ValueError):
        sim.pairwise(Q, B, "manhattan")


def test_unit_vectors_l2_equals_two_minus_two_cos(sim):
    rng = np.random.default_rng(1)
    a = sim.l2_normalize(rng.normal(size=(5, 32)))
    b = sim.l2_normalize(rng.normal(size=(7, 32)))
    np.testing.assert_allclose(sim.pairwise(a, b, "l2"), 2 - 2 * sim.pairwise(a, b, "cosine"), atol=1e-5)


# ---------- knn ----------


def test_knn_metrics_disagree_on_unnormalized(sim):
    base = np.array([
        [10.0, 10.0],   # 0: dài, lệch 45 độ
        [0.2, -0.06],   # 1: ngắn, cùng hướng với query
        [0.9, -0.5],    # 2: gần query nhất theo khoảng cách
    ])
    q = np.array([[1.0, -0.3]])
    assert sim.knn(q, base, 1, "dot").tolist() == [[0]], "dot ưu tiên vector dài"
    assert sim.knn(q, base, 1, "cosine").tolist() == [[1]], "cosine chỉ xét hướng"
    assert sim.knn(q, base, 1, "l2").tolist() == [[2]], "l2: khoảng cách nhỏ nhất là gần nhất"
    assert sim.knn(q, base, 3, "l2").tolist() == [[2, 1, 0]]


def test_knn_same_ranking_after_normalization(sim):
    rng = np.random.default_rng(2)
    base = sim.l2_normalize(rng.normal(size=(60, 16)))
    q = sim.l2_normalize(rng.normal(size=(8, 16)))
    by_cos = sim.knn(q, base, 10, "cosine")
    np.testing.assert_array_equal(by_cos, sim.knn(q, base, 10, "dot"))
    np.testing.assert_array_equal(by_cos, sim.knn(q, base, 10, "l2"))


def test_knn_ties_k_and_dtype(sim):
    base = np.array([[1.0, 0.0], [0.0, 1.0], [1.0, 0.0], [1.0, 0.0]])
    out = sim.knn(np.array([[1.0, 0.0]]), base, 3, "cosine")
    assert out.tolist() == [[0, 2, 3]], "bằng điểm thì chỉ số nhỏ trước"
    assert np.issubdtype(out.dtype, np.integer)
    assert sim.knn(np.array([[0.0, 1.0]]), base, 10, "l2").shape == (1, 4), "k > n_base thì trả n_base cột"
    assert sim.knn(np.array([[1.0, 0.0]]), base, 4, "l2").tolist() == [[0, 2, 3, 1]]
    rng = np.random.default_rng(4)
    many = np.repeat(rng.normal(size=(3, 4)), 40, axis=0)[rng.permutation(120)]
    for metric in ("dot", "cosine", "l2"):
        got = sim.knn(many[:1], many, 40, metric)[0]
        want = np.flatnonzero((many == many[0]).all(axis=1))
        assert got.tolist() == want.tolist(), f"{metric}: 40 vector trùng nhau phải theo thứ tự chỉ số tăng"


# ---------- ann_recall ----------


def test_ann_recall_hand(sim):
    exact = np.array([[0, 1, 2, 3], [4, 5, 6, 7]])
    approx = np.array([[1, 0, 9, 9], [7, 8, 9, 4]])
    assert sim.ann_recall(approx, exact, 2) == pytest.approx(0.5)     # {0,1}: 2/2; {7,8} vs {4,5}: 0/2
    assert sim.ann_recall(approx, exact, 4) == pytest.approx((2 / 4 + 2 / 4) / 2)
    assert sim.ann_recall(exact, exact, 3) == pytest.approx(1.0)


def test_ann_recall_uses_only_first_k_of_each(sim):
    exact = np.array([[0, 1, 2, 3, 4]])
    approx = np.array([[9, 0, 1, 2, 3]])
    assert sim.ann_recall(approx, exact, 1) == pytest.approx(0.0), "chỉ so top-1 với top-1"
    assert sim.ann_recall(approx, exact, 3) == pytest.approx(2 / 3)
    assert sim.ann_recall([[5, 6]], [[6, 5]], 2) == pytest.approx(1.0), "thứ tự trong top-k không quan trọng"


def test_ann_recall_on_knn_output(sim):
    rng = np.random.default_rng(3)
    base = rng.normal(size=(200, 8))
    q = rng.normal(size=(10, 8))
    exact = sim.knn(q, base, 10, "l2")
    noisy = sim.knn(q, base + rng.normal(scale=0.3, size=base.shape), 10, "l2")
    r = sim.ann_recall(noisy, exact, 10)
    assert 0.2 < r < 1.0

import math

import numpy as np
import pytest
from sklearn.metrics import ndcg_score

from testkit import Exercise

ex = Exercise(__file__)

# 3 truy vấn để tính tay. Truy vấn 1 là ví dụ ở mục 6 lý thuyết.
RETRIEVED = [
    ["C", "A", "D", "B", "E"],  # đúng: A (hạng 2), B (hạng 4)
    ["X", "Y", "Z"],  # đúng: Z (hạng 3)
    ["P", "Q", "R", "S"],  # đúng: S (hạng 4), T (không được trả về)
]
RELEVANT = [{"A", "B"}, {"Z"}, {"S", "T"}]
L3 = 1 / math.log2(3)  # 0.63093: gain ở hạng 2
L4 = 1 / math.log2(4)  # 0.5: gain ở hạng 3
L5 = 1 / math.log2(5)  # 0.43068: gain ở hạng 4


@pytest.fixture(scope="module")
def m():
    return ex.module("metrics.py")


def test_recall_hand_computed(m):
    # k = 3: 1/2, 1/1, 0/2
    assert m.recall_at_k(RETRIEVED, RELEVANT, 3) == pytest.approx((0.5 + 1 + 0) / 3, abs=1e-12)
    # k = 5 (dài hơn danh sách của truy vấn 2 và 3): 2/2, 1/1, 1/2
    assert m.recall_at_k(RETRIEVED, RELEVANT, 5) == pytest.approx((1 + 1 + 0.5) / 3, abs=1e-12)
    assert isinstance(m.recall_at_k(RETRIEVED, RELEVANT, 3), float)


def test_recall_divides_by_number_of_relevant_docs(m):
    # 3 tài liệu đúng, k = 1: recall = 1/3 theo định nghĩa ở lý thuyết (chia |Rel|, không chia k)
    assert m.recall_at_k([["A", "B", "C"]], [{"A", "B", "C"}], 1) == pytest.approx(1 / 3, abs=1e-12)
    assert m.recall_at_k([["A", "X", "Y", "Z"]], [{"A"}], 4) == pytest.approx(1.0, abs=1e-12)


def test_mrr_hand_computed(m):
    # k = 3: 1/2, 1/3, 0 (S ở hạng 4, ngoài top 3); trung bình trên 3 truy vấn, không phải tổng
    assert m.mrr_at_k(RETRIEVED, RELEVANT, 3) == pytest.approx((1 / 2 + 1 / 3 + 0) / 3, abs=1e-12)  # 0.27778
    # k = 5: 1/2, 1/3, 1/4
    assert m.mrr_at_k(RETRIEVED, RELEVANT, 5) == pytest.approx((1 / 2 + 1 / 3 + 1 / 4) / 3, abs=1e-12)  # 0.36111


def test_mrr_counts_only_first_relevant(m):
    # hai tài liệu đúng ở hạng 1 và 2: chỉ hạng 1 tính, RR = 1 (không phải 1 + 1/2)
    assert m.mrr_at_k([["A", "B", "C"]], [{"A", "B"}], 3) == pytest.approx(1.0, abs=1e-12)
    assert m.mrr_at_k([["C", "B", "A"]], [{"A", "B"}], 3) == pytest.approx(0.5, abs=1e-12)


def test_ndcg_hand_computed(m):
    # k = 5, truy vấn 1: DCG = 1/log2(3) + 1/log2(5) = 1.0616, IDCG = 1 + 1/log2(3) = 1.6309 -> 0.6509
    q1 = (L3 + L5) / (1 + L3)
    assert q1 == pytest.approx(0.6509, abs=1e-4)
    # truy vấn 2: DCG = 1/log2(4), IDCG = 1. Truy vấn 3: DCG = 1/log2(5), IDCG = 1 + 1/log2(3) (2 tài liệu đúng,
    # dù T không được trả về)
    q2 = L4 / 1
    q3 = L5 / (1 + L3)
    assert m.ndcg_at_k(RETRIEVED, RELEVANT, 5) == pytest.approx((q1 + q2 + q3) / 3, abs=1e-12)  # 0.47166
    # k = 3: truy vấn 1 chỉ còn A, truy vấn 3 không còn gì
    assert m.ndcg_at_k(RETRIEVED, RELEVANT, 3) == pytest.approx((L3 / (1 + L3) + L4 + 0) / 3, abs=1e-12)  # 0.29562


def test_ndcg_ideal_is_truncated_at_k(m):
    # 3 tài liệu đúng, k = 1, hạng 1 đúng: IDCG@1 = 1, nên nDCG@1 = 1
    assert m.ndcg_at_k([["A", "X", "B"]], [{"A", "B", "C"}], 1) == pytest.approx(1.0, abs=1e-12)
    # thứ tự lý tưởng cho đúng 1
    assert m.ndcg_at_k([["B", "A", "X", "Y"]], [{"A", "B"}], 4) == pytest.approx(1.0, abs=1e-12)


def test_ndcg_matches_sklearn(m):
    rng = np.random.default_rng(0)
    retrieved, relevant, labels = [], [], []
    for _ in range(20):
        docs = [f"d{i}" for i in rng.permutation(12)]
        rel = {f"d{i}" for i in rng.choice(12, size=int(rng.integers(1, 5)), replace=False)}
        retrieved.append(docs)
        relevant.append(rel)
        labels.append([int(d in rel) for d in docs])
    scores = np.tile(np.arange(12, 0, -1), (20, 1))  # điểm giảm dần = đúng thứ tự trả về
    for k in (1, 3, 5, 10):
        assert m.ndcg_at_k(retrieved, relevant, k) == pytest.approx(ndcg_score(np.array(labels), scores, k=k), abs=1e-9)


def test_k_larger_than_list_and_empty_list(m):
    for fn in (m.recall_at_k, m.mrr_at_k, m.ndcg_at_k):
        assert fn([["A"]], [{"A"}], 100) == pytest.approx(1.0, abs=1e-12)
        assert fn([[]], [{"A"}], 10) == 0.0


@pytest.mark.parametrize("name", ["recall_at_k", "mrr_at_k", "ndcg_at_k"])
def test_rejects_bad_input(m, name):
    fn = getattr(m, name)
    with pytest.raises(ValueError):
        fn([["A"], ["B"]], [{"A"}, set()], 3)  # truy vấn không có tài liệu liên quan
    with pytest.raises(ValueError):
        fn([["A"], ["B"]], [{"A"}], 3)  # số truy vấn không khớp
    with pytest.raises(ValueError):
        fn([["A"]], [{"A"}], 0)  # k < 1
    with pytest.raises(ValueError):
        fn([], [], 3)  # không có truy vấn nào: trung bình trên 0 truy vấn không xác định

import numpy as np
import pytest

from testkit import Exercise

ex = Exercise(__file__)


@pytest.fixture(scope="module")
def ivf():
    return ex.module("ivf.py")


def blobs(n_per=100, d=8, seed=0, spread=0.3):
    rng = np.random.default_rng(seed)
    centers = rng.normal(scale=5.0, size=(4, d))
    x = np.concatenate([c + rng.normal(scale=spread, size=(n_per, d)) for c in centers])
    return x.astype(np.float32), centers


def exact_topk(x, q, k):
    d = ((x - q) ** 2).sum(1)
    return np.argsort(d, kind="stable")[:k].tolist()


def inertia(ivf, x, c):
    return float(ivf.sq_dists(x, c).min(axis=1).sum())


# ---------- assign, kmeans ----------


def test_assign_nearest_and_ties(ivf):
    c = np.array([[0.0, 0.0], [10.0, 0.0], [0.0, 10.0]])
    x = np.array([[1.0, 1.0], [9.0, -1.0], [-1.0, 8.0], [5.0, 0.0]])
    out = ivf.assign(x, c)
    assert out.tolist() == [0, 1, 2, 0], "điểm (5, 0) cách đều centroid 0 và 1: chọn chỉ số nhỏ"
    assert np.issubdtype(out.dtype, np.integer)


def test_kmeans_init_is_specified(ivf):
    x, _ = blobs()
    c0 = ivf.kmeans(x, 6, n_iter=0, seed=7)
    want = x[np.random.default_rng(7).choice(len(x), 6, replace=False)]
    np.testing.assert_allclose(c0, want)
    assert c0.dtype == np.float32 and c0.shape == (6, 8)
    small = np.arange(20, dtype=np.float32).reshape(10, 2)
    want = small[np.random.default_rng(3).choice(10, 10, replace=False)]
    np.testing.assert_allclose(ivf.kmeans(small, 10, n_iter=0, seed=3), want)


def test_kmeans_recovers_blobs(ivf):
    x, centers = blobs()
    c = ivf.kmeans(x, 4, n_iter=20, seed=0)
    # mỗi tâm thật có đúng một centroid gần nó, cách dưới 0.2
    d = np.sqrt(ivf.sq_dists(centers, c))
    assert sorted(d.argmin(axis=1).tolist()) == [0, 1, 2, 3]
    assert d.min(axis=1).max() < 0.2


def test_kmeans_inertia_never_increases(ivf):
    x, _ = blobs(n_per=60, seed=3, spread=2.0)
    values = [inertia(ivf, x, ivf.kmeans(x, 8, n_iter=t, seed=1)) for t in range(6)]
    assert all(b <= a + 1e-3 for a, b in zip(values, values[1:])), values
    assert values[-1] < values[0]


def test_kmeans_empty_cluster_keeps_centroid(ivf):
    # 5 điểm trùng nhau: hai centroid khởi tạo có thể trùng, cụm thứ hai rỗng
    x = np.array([[1.0, 1.0]] * 5 + [[9.0, 9.0]] * 5, dtype=np.float32)
    for seed in range(5):
        c = ivf.kmeans(x, 3, n_iter=3, seed=seed)
        assert not np.isnan(c).any(), "cụm rỗng không được thành NaN"
        assert {tuple(row) for row in c.round(4)} <= {(1.0, 1.0), (9.0, 9.0)}


# ---------- IVFIndex ----------


def build(ivf, nlist=8, n=400, seed=0):
    x, _ = blobs(n_per=n // 4, seed=seed, spread=1.5)
    index = ivf.IVFIndex(nlist, n_iter=10, seed=0)
    index.train(x)
    index.add(x)
    return index, x


def test_lists_partition_and_match_assign(ivf):
    index, x = build(ivf)
    assert len(index.lists) == 8
    all_ids = np.concatenate(index.lists)
    assert sorted(all_ids.tolist()) == list(range(len(x))), "mỗi id nằm trong đúng một danh sách"
    labels = ivf.assign(x, index.centroids)
    for c, ids in enumerate(index.lists):
        assert (labels[ids] == c).all()


def test_add_twice_continues_ids(ivf):
    x, _ = blobs(seed=5)
    index = ivf.IVFIndex(4, n_iter=5, seed=0)
    index.train(x)
    index.add(x[:150])
    index.add(x[150:])
    assert sorted(np.concatenate(index.lists).tolist()) == list(range(len(x)))
    labels = ivf.assign(x, index.centroids)
    for c, ids in enumerate(index.lists):
        assert (labels[ids] == c).all(), "id của lần add thứ hai nối tiếp sau 150"


def test_search_all_lists_is_exact(ivf):
    index, x = build(ivf)
    rng = np.random.default_rng(9)
    for q in rng.normal(scale=4.0, size=(10, 8)).astype(np.float32):
        ids, scanned = index.search(q, 10, nprobe=8)
        assert ids == exact_topk(x, q, 10)
        assert scanned == len(x)
        assert all(isinstance(i, int) for i in ids)


def test_search_scans_only_probed_lists(ivf):
    index, x = build(ivf)
    rng = np.random.default_rng(10)
    for q in rng.normal(scale=4.0, size=(10, 8)).astype(np.float32):
        order = np.argsort(ivf.sq_dists(q[None], index.centroids)[0], kind="stable")
        for nprobe in (1, 3):
            probed = set(order[:nprobe].tolist())
            ids, scanned = index.search(q, 5, nprobe=nprobe)
            assert scanned == sum(len(index.lists[c]) for c in probed), "đếm đúng số vector đã so"
            inside = np.concatenate([index.lists[c] for c in probed])
            assert set(ids) <= set(inside.tolist()), "chỉ trả id thuộc các danh sách được probe"
            assert ids == [int(i) for i in inside[np.argsort(((x[inside] - q) ** 2).sum(1), kind="stable")[:5]]]


def test_recall_grows_with_nprobe(ivf):
    rng = np.random.default_rng(11)
    x = rng.normal(size=(2000, 16)).astype(np.float32)
    index = ivf.IVFIndex(32, n_iter=8, seed=0)
    index.train(x)
    index.add(x)
    queries = rng.normal(size=(40, 16)).astype(np.float32)
    recalls, costs = [], []
    for nprobe in (1, 4, 16, 32):
        hits, cost = 0, 0
        for q in queries:
            ids, scanned = index.search(q, 10, nprobe=nprobe)
            hits += len(set(ids) & set(exact_topk(x, q, 10)))
            cost += scanned
        recalls.append(hits / (10 * len(queries)))
        costs.append(cost / len(queries))
    assert recalls[0] < 0.8 and recalls[-1] == 1.0, recalls
    assert recalls == sorted(recalls) and costs == sorted(costs)
    assert costs[0] < 0.15 * len(x), "nprobe = 1 chỉ quét khoảng 1/nlist dữ liệu"


def test_search_k_larger_than_candidates(ivf):
    x = np.array([[0.0, 0.0], [0.1, 0.0], [10.0, 10.0], [10.1, 10.0], [10.0, 10.2]], dtype=np.float32)
    index = ivf.IVFIndex(2, n_iter=5, seed=0)
    index.train(x)
    index.add(x)
    ids, scanned = index.search(np.array([0.05, 0.0]), 10, nprobe=1)
    assert ids == [0, 1] and scanned == 2


def test_search_ties_across_lists_smaller_id_first(ivf):
    index = ivf.IVFIndex(2)
    index.centroids = np.array([[-3.0, 0.0], [1.5, 0.0]], dtype=np.float32)
    index.lists = [np.zeros(0, dtype=np.int64), np.zeros(0, dtype=np.int64)]
    index.vectors = np.zeros((0, 2), dtype=np.float32)
    # id 0 = (-1, 0) thuộc danh sách 0 (xa q hơn), id 1 = (1, 0) thuộc danh sách 1 (gần q hơn)
    index.add(np.array([[-1.0, 0.0], [1.0, 0.0], [2.0, 0.0], [-20.0, 0.0]], dtype=np.float32))
    assert [ids.tolist() for ids in index.lists] == [[0, 3], [1, 2]]
    ids, scanned = index.search(np.array([0.0, 0.0]), 2, nprobe=2)
    assert ids == [0, 1], "id 0 và 1 cách q bằng nhau: id nhỏ trước, dù danh sách của nó được probe sau"
    assert scanned == 4

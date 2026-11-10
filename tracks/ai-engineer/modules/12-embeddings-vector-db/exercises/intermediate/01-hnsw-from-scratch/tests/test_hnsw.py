import json
import math

import numpy as np
import pytest

from testkit import Exercise

ex = Exercise(__file__)


@pytest.fixture(scope="module")
def nb():
    return ex.notebook("hnsw.ipynb")


def circle(degrees):
    rad = np.deg2rad(np.asarray(degrees, dtype=float))
    return np.stack([np.cos(rad), np.sin(rad)], axis=1).astype(np.float32)


def cosd(a, b):
    return 1 - math.cos(math.radians(a - b))


def unit(x):
    return (x / np.linalg.norm(x, axis=1, keepdims=True)).astype(np.float32)


def toy(seed=0, n_clusters=20, per=100, d=32):
    rng = np.random.default_rng(seed)
    centers = rng.normal(size=(n_clusters, d))
    x = np.concatenate([c + 0.5 * rng.normal(size=(per, d)) for c in centers])
    x = unit(x)[rng.permutation(n_clusters * per)]
    q = unit(x[rng.choice(len(x), 40)] + 0.05 * rng.normal(size=(40, d)))
    return x, q


def recall(found, truth, k=10):
    return float(np.mean([len(set(f[:k]) & set(t[:k].tolist())) / k for f, t in zip(found, truth)]))


# ---------- random_level ----------


def test_random_level_formula_and_one_draw(nb):
    m_l = 1 / math.log(16)
    rng, ref = np.random.default_rng(0), np.random.default_rng(0)
    for _ in range(200):
        assert nb.random_level(rng, m_l) == int(-math.log(1 - ref.random()) * m_l)
    assert rng.random() == ref.random(), "mỗi lần gọi lấy đúng một số ngẫu nhiên"


def test_random_level_distribution(nb):
    rng = np.random.default_rng(1)
    levels = np.array([nb.random_level(rng, 1 / math.log(16)) for _ in range(20000)])
    assert levels.min() == 0
    assert abs((levels >= 1).mean() - 1 / 16) < 0.01
    assert (levels >= 2).mean() < 0.01


# ---------- search_layer ----------


def chain_index(nb):
    # node: 0 ở 0°, 1 ở 60°, 2 ở 120°, 3 ở 170°, 4 ở 260°; tầng 0 có cạnh 0-1, 1-2, 2-3, 0-4
    h = nb.HNSW(2, M=2)
    h.vectors = circle([0, 60, 120, 170, 260])
    h.levels = [0] * 5
    h.graph = [{0: [1, 4], 1: [0, 2], 2: [1, 3], 3: [2], 4: [0]}]
    h.entry_point = 0
    return h


def test_search_layer_greedy_gets_stuck(nb):
    h = chain_index(nb)
    q = circle([175])[0]
    out = h.search_layer(q, [0], 1, 0)
    assert [i for _, i in out] == [4], "ef = 1: nút 4 (85°) gần hơn mọi láng giềng của nó, tham lam dừng ở đó"
    assert out[0][0] == pytest.approx(cosd(260, 175), abs=1e-6)


def test_search_layer_beam_escapes(nb):
    h = chain_index(nb)
    q = circle([175])[0]
    out = h.search_layer(q, [0], 2, 0)
    assert [i for _, i in out] == [3, 2]
    assert [d for d, _ in out] == pytest.approx([cosd(170, 175), cosd(120, 175)], abs=1e-6)
    h.n_dist = 0
    out = h.search_layer(q, [0], 10, 0)
    assert [i for _, i in out] == [3, 2, 4, 1, 0], "ef lớn hơn số nút: trả mọi nút tới được, tăng dần"
    assert h.n_dist <= 5, "mỗi nút chỉ tính khoảng cách một lần (tập visited)"


def test_search_layer_multiple_entry_points(nb):
    h = chain_index(nb)
    out = h.search_layer(circle([118])[0], [3, 4], 1, 0)
    assert [i for _, i in out] == [2]


# ---------- select_neighbors ----------


def test_select_neighbors_heuristic_vs_simple(nb):
    # gốc ở 0°; ứng viên 10°, 12°, -30°, 40° (đã sắp theo khoảng cách tới gốc)
    angles = [0, 10, 12, -30, 40]
    cands = [(cosd(a, 0), i) for i, a in enumerate(angles) if i > 0]
    for heuristic, m, want in [(False, 3, [1, 2, 3]), (True, 3, [1, 3]), (True, 1, [1]), (False, 10, [1, 2, 3, 4])]:
        h = nb.HNSW(2, M=4, heuristic=heuristic)
        h.vectors = circle(angles)
        assert h.select_neighbors(cands, m) == want, f"heuristic={heuristic}, m={m}"


# ---------- _insert / add ----------


_BUILT: dict = {}


def built(nb):
    if "h" not in _BUILT:
        rng = np.random.default_rng(5)
        x = unit(rng.normal(size=(400, 16)))
        h = nb.HNSW(16, M=4, ef_construction=20, seed=3)
        h.add(x)
        _BUILT.update(h=h, x=x)
    return _BUILT["h"], _BUILT["x"]


def test_levels_follow_rng(nb):
    h, x = built(nb)
    ref = np.random.default_rng(3)
    assert h.levels == [nb.random_level(ref, 1 / math.log(4)) for _ in range(len(x))]
    assert len(h.graph) == max(h.levels) + 1


def test_graph_structure(nb):
    h, x = built(nb)
    top = max(h.levels)
    assert h.levels[h.entry_point] == top and h.entry_point == h.levels.index(top), \
        "entry_point là nút đầu tiên đạt tầng cao nhất"
    for layer, g in enumerate(h.graph):
        assert set(g) == {i for i, lv in enumerate(h.levels) if lv >= layer}
        for node, links in g.items():
            assert len(links) <= h.max_degree(layer)
            assert node not in links and len(set(links)) == len(links)
            assert all(h.levels[n] >= layer for n in links)
    assert all(len(links) > 0 for links in h.graph[0].values()), "mọi nút có ít nhất một láng giềng ở tầng 0"


def test_second_node_links_first(nb):
    h = nb.HNSW(2, M=2, seed=0)
    h.add(circle([0, 30]))
    assert h.entry_point in (0, 1)
    assert h.graph[0][1] == [0] and h.graph[0][0] == [1], "nối hai chiều"


def test_degree_pruned_with_selection(nb):
    rng = np.random.default_rng(6)
    x = unit(rng.normal(size=(150, 8)))
    h = nb.HNSW(8, M=2, ef_construction=10, seed=0)
    h.add(x)
    degrees = [len(v) for v in h.graph[0].values()]
    assert max(degrees) <= 4


def test_overflow_pruned_from_neighbor_view(nb):
    # m_l = 0: mọi nút ở tầng 0; M = 2 nên bậc tối đa tầng 0 là 4. Góc chọn để không có khoảng cách bằng nhau.
    angles = [0, 100, 10, 90, 22, 80, 33, 71, 4, 60, 45, 52]
    h = nb.HNSW(2, M=2, ef_construction=20, seed=0)
    h.m_l = 0.0
    h.add(circle(angles))
    want = {0: {1, 2, 8}, 1: {0, 2, 3}, 2: {8, 4}, 3: {1, 2, 4, 5}, 4: {2, 3, 5, 6}, 5: {3, 4, 6, 7}, 6: {4, 10},
            7: {5, 6, 9}, 8: {0, 2}, 9: {7, 6, 10, 11}, 10: {6, 9, 11}, 11: {10, 9}}
    got = {node: set(links) for node, links in h.graph[0].items()}
    assert got[2] == want[2] and got[6] == want[6], "nút bị tràn bậc tỉa lại bằng select_neighbors, nhìn từ chính nó"
    assert got == want


def test_entry_point_first_to_reach_top(nb):
    rng = np.random.default_rng(8)
    for seed in range(6):
        h = nb.HNSW(4, M=2, ef_construction=8, seed=seed)
        h.add(unit(rng.normal(size=(60, 4))))
        top = max(h.levels)
        assert h.entry_point == h.levels.index(top), f"seed={seed}: nút sau cùng tầng không thay entry_point"


# ---------- search ----------


def test_search_recall_on_clusters(nb):
    x, q = toy()
    truth = np.argsort(-(q @ x.T), axis=1, kind="stable")[:, :10]
    h = nb.HNSW(32, M=8, ef_construction=40, seed=0)
    h.add(x)
    h.n_dist = 0
    found = [h.search(v, 10, ef=40) for v in q]
    assert recall(found, truth) >= 0.95
    assert h.n_dist / len(q) < 0.25 * len(x), "HNSW phải tính ít khoảng cách hơn nhiều so với quét hết"
    low = recall([h.search(v, 10, ef=10) for v in q], truth)
    assert low <= recall(found, truth)
    assert all(isinstance(i, int) for i in found[0]) and len(found[0]) == 10
    assert len(h.search(q[0], 15, ef=5)) == 15, "ef nhỏ hơn k thì dùng k"


def test_search_descends_upper_layers(nb):
    # tầng 0 có hai thành phần rời {0,1,2} và {3,4,5}; chỉ tầng 1 nối 0 với 3
    h = nb.HNSW(2, M=2)
    h.vectors = circle([0, 20, 40, 150, 170, 190])
    h.levels = [1, 0, 0, 1, 0, 0]
    h.graph = [{0: [1], 1: [0, 2], 2: [1], 3: [4], 4: [3, 5], 5: [4]}, {0: [3], 3: [0]}]
    h.entry_point = 0
    assert h.search(circle([188])[0], 1, ef=1) == [5]


# ---------- IVF dán từ Basic 02 ----------


def test_pasted_ivf(nb):
    rng = np.random.default_rng(7)
    x = rng.normal(size=(300, 8)).astype(np.float32)
    index = nb.IVFIndex(8, n_iter=5, seed=0)
    index.train(x)
    index.add(x)
    assert sorted(np.concatenate(index.lists).tolist()) == list(range(300))
    q = x[17]
    ids, scanned = index.search(q, 5, nprobe=8)
    assert ids == np.argsort(((x - q) ** 2).sum(1), kind="stable")[:5].tolist() and scanned == 300
    np.testing.assert_allclose(nb.kmeans(x, 4, n_iter=0, seed=1), x[np.random.default_rng(1).choice(300, 4, replace=False)])


# ---------- dữ liệu thật: tự skip nếu chưa có cache bge-m3 ----------


def test_on_cached_bge_m3(nb):
    root = ex.dataset("zalo-legal")
    path = root / "cache" / "bge-m3.npy"
    if not path.exists():
        pytest.skip("Chưa có cache bge-m3: chạy cell embed trong notebook một lần")
    ids = json.loads((root / "cache" / "bge-m3.ids.json").read_text(encoding="utf-8"))
    assert len(ids) == 61425
    x = np.ascontiguousarray(np.load(path, mmap_mode="r")[:1500])
    h = nb.HNSW(1024, M=8, ef_construction=40, seed=0)
    h.add(x)
    queries = x[::50]
    truth = np.argsort(-(queries @ x.T), axis=1, kind="stable")[:, :10]
    found = [h.search(v, 10, ef=40) for v in queries]
    assert recall(found, truth) >= 0.9
    assert all(f[0] == t[0] for f, t in zip(found, truth)), "vector của chính nó luôn đứng đầu"

from collections import Counter

import pytest

from testkit import Exercise

ex = Exercise(__file__)

KEYS = [f"order-{i}" for i in range(20_000)]
NODES = ["node-a", "node-b", "node-c", "node-d"]


@pytest.fixture(scope="module")
def ring_mod():
    if ex.target.name != "starter" and not (ex.target / "ring.py").exists():
        pytest.skip("Bài advanced không có lời giải dạng code, xem SOLUTION.md")
    return ex.module("ring.py")


# ---------- HashRing ----------


def test_empty_ring_raises(ring_mod):
    with pytest.raises(LookupError):
        ring_mod.HashRing().get_node("x")


def test_add_remove_validation(ring_mod):
    ring = ring_mod.HashRing(["a", "b"], vnodes=10)
    assert ring.nodes == {"a", "b"}
    with pytest.raises(ValueError):
        ring.add_node("a")
    ring.remove_node("a")
    assert ring.nodes == {"b"}
    with pytest.raises(KeyError):
        ring.remove_node("a")
    assert all(ring.get_node(k) == "b" for k in KEYS[:100])


def test_deterministic(ring_mod):
    r1 = ring_mod.HashRing(NODES, vnodes=50)
    r2 = ring_mod.HashRing(list(reversed(NODES)), vnodes=50)
    assert [r1.get_node(k) for k in KEYS[:500]] == [r2.get_node(k) for k in KEYS[:500]]


def test_owner_is_first_vnode_clockwise(ring_mod):
    ring = ring_mod.HashRing(["a", "b", "c"], vnodes=1)
    points = sorted((ring_mod.stable_hash(f"{n}#0"), n) for n in ["a", "b", "c"])
    for key in KEYS[:300]:
        h = ring_mod.stable_hash(key)
        expected = next((n for p, n in points if p >= h), points[0][1])
        assert ring.get_node(key) == expected


def test_balanced_with_virtual_nodes(ring_mod):
    ring = ring_mod.HashRing(NODES, vnodes=100)
    counts = Counter(ring.get_node(k) for k in KEYS)
    shares = {n: counts[n] / len(KEYS) for n in NODES}
    assert all(0.15 <= s <= 0.35 for s in shares.values()), shares


def test_adding_node_moves_few_keys_only_to_new_node(ring_mod):
    ring = ring_mod.HashRing(NODES, vnodes=100)
    before = {k: ring.get_node(k) for k in KEYS}
    ring.add_node("node-e")
    after = {k: ring.get_node(k) for k in KEYS}
    moved = [k for k in KEYS if before[k] != after[k]]
    assert 0.10 <= len(moved) / len(KEYS) <= 0.30, len(moved) / len(KEYS)
    assert all(after[k] == "node-e" for k in moved)


def test_removing_node_moves_only_its_keys(ring_mod):
    ring = ring_mod.HashRing(NODES, vnodes=100)
    before = {k: ring.get_node(k) for k in KEYS}
    ring.remove_node("node-b")
    after = {k: ring.get_node(k) for k in KEYS}
    for k in KEYS:
        if before[k] != "node-b":
            assert after[k] == before[k]
        else:
            assert after[k] != "node-b"


def test_get_nodes_distinct_replicas(ring_mod):
    ring = ring_mod.HashRing(NODES, vnodes=100)
    for key in KEYS[:500]:
        replicas = ring.get_nodes(key, 3)
        assert len(replicas) == 3 == len(set(replicas))
        assert replicas[0] == ring.get_node(key)
    assert sorted(ring.get_nodes("k", 4)) == sorted(NODES)
    with pytest.raises(ValueError):
        ring.get_nodes("k", 5)


# ---------- QuorumStore ----------


def make_store(ring_mod, n=3, r=2, w=2):
    ring = ring_mod.HashRing(NODES, vnodes=50)
    return ring, ring_mod.QuorumStore(ring, n=n, r=r, w=w)


def test_store_validates_config(ring_mod):
    ring = ring_mod.HashRing(NODES, vnodes=10)
    for kwargs in ({"n": 5}, {"n": 3, "r": 0}, {"n": 3, "w": 4}):
        with pytest.raises(ValueError):
            ring_mod.QuorumStore(ring, **kwargs)


def test_put_get_roundtrip(ring_mod):
    ring, store = make_store(ring_mod)
    assert store.get("order-1") is None
    assert store.put("order-1", "created") == 1
    assert store.put("order-1", "shipped") == 2
    assert store.get("order-1") == "shipped"
    replicas = ring.get_nodes("order-1", 3)
    assert all(store.data[n]["order-1"] == (2, "shipped") for n in replicas)
    others = set(NODES) - set(replicas)
    assert all("order-1" not in store.data[n] for n in others)


def test_quorum_read_sees_latest_and_repairs(ring_mod):
    ring, store = make_store(ring_mod)
    key = "order-42"
    first, second, third = ring.get_nodes(key, 3)
    store.put(key, "v1")
    store.mark_down(first)
    assert store.put(key, "v2") == 2          # W=2: second + third
    assert store.data[first][key] == (1, "v1")
    store.mark_up(first)
    assert store.get(key) == "v2"             # R=2 đọc first (cũ) + second (mới)
    assert store.data[first][key] == (2, "v2"), "Read repair phải cập nhật replica cũ"


def test_write_fails_without_quorum(ring_mod):
    ring, store = make_store(ring_mod)
    key = "order-7"
    first, second, third = ring.get_nodes(key, 3)
    store.put(key, "v1")
    store.mark_down(second)
    store.mark_down(third)
    with pytest.raises(ring_mod.QuorumError):
        store.put(key, "v2")
    assert store.data[first][key] == (1, "v1"), "Ghi thất bại không được để lại dữ liệu"
    with pytest.raises(ring_mod.QuorumError):
        store.get(key)


def test_weak_quorum_can_return_stale_data(ring_mod):
    ring, store = make_store(ring_mod, n=3, r=1, w=1)  # R + W <= N
    key = "order-99"
    first, second, third = ring.get_nodes(key, 3)
    store.put(key, "v1")
    store.mark_down(second)
    store.mark_down(third)
    store.put(key, "v2")                      # chỉ first nhận
    for node in (second, third):
        store.mark_up(node)
    store.mark_down(first)
    assert store.get(key) == "v1"             # đọc phải dữ liệu cũ: cái giá của R + W <= N

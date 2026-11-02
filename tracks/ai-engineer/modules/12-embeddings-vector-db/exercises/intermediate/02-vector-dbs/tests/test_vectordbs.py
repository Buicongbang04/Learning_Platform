import uuid

import numpy as np
import pytest

from testkit import Exercise

ex = Exercise(__file__)

STORES = ["ChromaStore", "FaissStore", "QdrantStore", "LanceStore"]


@pytest.fixture(scope="module")
def nb():
    return ex.notebook("vectordbs.ipynb")


def data(n=300, d=16, seed=0):
    rng = np.random.default_rng(seed)
    x = rng.normal(size=(n, d)).astype(np.float32)
    x /= np.linalg.norm(x, axis=1, keepdims=True)
    laws = ["100/2019/nđ-cp", "47/2011/tt-bca", "luật o'brien", "01/2009/tt-bnn"]
    uids = [f"{laws[i % 4]}+{i}" for i in range(n)]
    metas = [{"law": laws[i % 4]} for i in range(n)]
    return x, uids, metas


def exact(x, uids, metas, q, k, law=None):
    order = [i for i in np.argsort(-(x @ q), kind="stable") if law is None or metas[i]["law"] == law][:k]
    return [uids[i] for i in order], [float(x[i] @ q) for i in order]


def make(nb, cls_name, **kw):
    return getattr(nb, cls_name)(16, name=f"t-{uuid.uuid4().hex[:8]}", **kw)


# ---------- distance_to_cosine, latency_summary ----------


def test_distance_to_cosine(nb):
    rng = np.random.default_rng(1)
    a = rng.normal(size=(20, 8))
    a /= np.linalg.norm(a, axis=1, keepdims=True)
    cos = a @ a[0]
    sq = ((a - a[0]) ** 2).sum(1)
    np.testing.assert_allclose(nb.distance_to_cosine(cos, "cosine_similarity"), cos)
    np.testing.assert_allclose(nb.distance_to_cosine(1 - cos, "cosine_distance"), cos, atol=1e-12)
    np.testing.assert_allclose(nb.distance_to_cosine(sq, "squared_l2"), cos, atol=1e-12)
    np.testing.assert_allclose(nb.distance_to_cosine(np.sqrt(sq), "l2"), cos, atol=1e-12)
    with pytest.raises(ValueError):
        nb.distance_to_cosine(cos, "dot")


def test_latency_summary(nb):
    out = nb.latency_summary([5.0, 1.0, 3.0, 2.0, 4.0, 100.0])
    assert out == pytest.approx({"p50": 3.5, "p95": 76.25, "mean": 115 / 6})
    assert all(isinstance(v, float) for v in out.values())


def test_sql_quote(nb):
    assert nb.sql_quote("abc") == "'abc'"
    assert nb.sql_quote("luật o'brien") == "'luật o''brien'"


# ---------- bốn store, cùng một hợp đồng ----------


@pytest.mark.parametrize("cls_name", STORES)
def test_search_matches_exact_cosine(nb, cls_name):
    x, uids, metas = data()
    store = make(nb, cls_name)
    try:
        store.upsert(uids, x, metas)
        assert store.count() == 300
        for qi in (0, 17, 123):
            hits = store.search(x[qi], 5)
            want_u, want_c = exact(x, uids, metas, x[qi], 5)
            assert [u for u, _ in hits] == want_u
            assert [c for _, c in hits] == pytest.approx(want_c, abs=1e-4), "điểm trả về là cosine similarity"
            assert all(isinstance(c, float) for _, c in hits)
    finally:
        store.close()


@pytest.mark.parametrize("cls_name", STORES)
def test_filter_equality_with_quote(nb, cls_name):
    x, uids, metas = data()
    store = make(nb, cls_name)
    try:
        store.upsert(uids, x, metas)
        for law in ("47/2011/tt-bca", "luật o'brien"):
            hits = store.search(x[2], 5, where={"law": law})
            assert [u for u, _ in hits] == exact(x, uids, metas, x[2], 5, law)[0]
        assert store.search(x[2], 5, where={"law": "không có văn bản này"}) == []
    finally:
        store.close()


@pytest.mark.parametrize("cls_name", STORES)
def test_fewer_matches_than_k(nb, cls_name):
    x, uids, metas = data(n=10)
    store = make(nb, cls_name)
    try:
        store.upsert(uids, x, metas)
        hits = store.search(x[0], 5, where={"law": "47/2011/tt-bca"})   # chỉ i = 1, 5, 9
        assert sorted(u for u, _ in hits) == sorted([uids[1], uids[5], uids[9]]), "không trả phần tử giả khi thiếu"
    finally:
        store.close()


@pytest.mark.parametrize("cls_name", STORES)
def test_delete_and_upsert_replace(nb, cls_name):
    x, uids, metas = data()
    store = make(nb, cls_name)
    try:
        store.upsert(uids, x, metas)
        store.delete([uids[7], uids[8]])
        assert store.count() == 298
        assert uids[7] not in [u for u, _ in store.search(x[7], 10)]
        # thay vector của uid 20 bằng vector của 7 (đã xoá) và đổi metadata: count không đổi, uid 20 thành gần x[7] nhất
        store.upsert([uids[20]], x[7:8], [{"law": "mới"}])
        assert store.count() == 298
        hits = store.search(x[7], 1)
        assert hits[0][0] == uids[20] and hits[0][1] == pytest.approx(1.0, abs=1e-4)
        assert [u for u, _ in store.search(x[7], 3, where={"law": "mới"})] == [uids[20]]
        assert uids[20] not in [u for u, _ in store.search(x[20], 50, where={"law": metas[20]["law"]})], \
            "metadata cũ phải bị thay"
    finally:
        store.close()


@pytest.mark.parametrize("cls_name", ["QdrantStore", "LanceStore", "ChromaStore"])
def test_persist_and_reopen(nb, cls_name, tmp_path):
    x, uids, metas = data()
    store = getattr(nb, cls_name)(16, path=str(tmp_path / "db"), name="zalo")
    store.upsert(uids, x, metas)
    store.close()
    again = getattr(nb, cls_name)(16, path=str(tmp_path / "db"), name="zalo")
    try:
        assert again.count() == 300
        assert again.search(x[3], 1)[0][0] == uids[3]
        again.upsert([uids[3]], x[4:5], [metas[3]])
        assert again.count() == 300, "uid cũ sau khi mở lại vẫn được nhận ra (thay chứ không nhân bản)"
    finally:
        again.close()


def test_qdrant_point_ids_are_stable_uuids(nb):
    pid = nb.QdrantStore.point_id("100/2019/nđ-cp+5")
    assert pid == str(uuid.uuid5(uuid.NAMESPACE_URL, "100/2019/nđ-cp+5"))

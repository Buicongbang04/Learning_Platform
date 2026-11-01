import base64
import json

import numpy as np
import pytest
from llmkit import FakeLLM

from testkit import Exercise

ex = Exercise(__file__)


@pytest.fixture(scope="module")
def ec():
    return ex.module("embed_client.py")


def b64(vec, dtype="<f4"):
    return base64.b64encode(np.asarray(vec, dtype=dtype).tobytes()).decode()


# ---------- build_request ----------


def test_build_request_minimal_and_full(ec):
    body = ec.build_request(["a", "b c"], "bge-m3")
    assert body == {"model": "bge-m3", "input": ["a", "b c"], "encoding_format": "float"}
    assert "dimensions" not in body, "không gửi dimensions khi không truyền: nhiều model báo lỗi với khoá lạ"
    body = ec.build_request(("x",), "text-embedding-3-small", dimensions=256, encoding_format="base64")
    assert body == {"model": "text-embedding-3-small", "input": ["x"], "encoding_format": "base64", "dimensions": 256}
    json.dumps(body)


@pytest.mark.parametrize("texts", [[], ["ok", ""], ["   ", "ok"]])
def test_build_request_rejects_empty(ec, texts):
    with pytest.raises(ValueError):
        ec.build_request(texts, "bge-m3")


def test_build_request_rejects_bad_encoding(ec):
    with pytest.raises(ValueError):
        ec.build_request(["a"], "bge-m3", encoding_format="float16")


# ---------- parse_response ----------


def test_parse_float_sorted_by_index(ec):
    payload = {"data": [
        {"object": "embedding", "index": 2, "embedding": [0.0, 3.0]},
        {"object": "embedding", "index": 0, "embedding": [1.0, 0.0]},
        {"object": "embedding", "index": 1, "embedding": [0.5, 0.5]},
    ]}
    out = ec.parse_response(payload, n_expected=3)
    assert out.dtype == np.float32 and out.shape == (3, 2)
    np.testing.assert_allclose(out, [[1, 0], [0.5, 0.5], [0, 3]])


def test_parse_base64_little_endian_float32(ec):
    v0, v1 = [0.25, -1.5, 3.0], [1e-3, 2.0, -0.5]
    payload = {"data": [{"index": 1, "embedding": b64(v1)}, {"index": 0, "embedding": b64(v0)}]}
    np.testing.assert_allclose(ec.parse_response(payload), [v0, v1], rtol=1e-6)


def test_parse_errors(ec):
    good = {"data": [{"index": 0, "embedding": [1.0, 2.0]}, {"index": 1, "embedding": [3.0, 4.0]}]}
    with pytest.raises(ValueError):
        ec.parse_response(good, n_expected=3)
    with pytest.raises(ValueError):
        ec.parse_response({"data": [{"index": 0, "embedding": [1.0]}, {"index": 0, "embedding": [2.0]}]})
    with pytest.raises(ValueError):
        ec.parse_response({"data": [{"index": 0, "embedding": [1.0, 2.0]}, {"index": 1, "embedding": [3.0]}]})


def test_parse_real_ollama_payloads(ec):
    """Response thật của Ollama /v1/embeddings (nomic-embed-text, dimensions=8), cùng 3 câu, hai encoding."""
    as_float = json.loads((ex.fixtures / "ollama-v1-embeddings-float.json").read_text(encoding="utf-8"))
    as_b64 = json.loads((ex.fixtures / "ollama-v1-embeddings-base64.json").read_text(encoding="utf-8"))
    a = ec.parse_response(as_float, n_expected=3)
    b = ec.parse_response(as_b64, n_expected=3)
    assert a.shape == b.shape == (3, 8)
    np.testing.assert_allclose(a, b, rtol=1e-6, atol=1e-7)


# ---------- batched ----------


def test_batched_items_and_chars(ec):
    texts = ["aaaa", "bb", "cccccc", "d", "ee", "fffffffffffff", "g"]
    assert ec.batched(texts, max_items=3, max_chars=100) == [[0, 1, 2], [3, 4, 5], [6]]
    # max_chars = 8: "aaaa"+"bb" = 6, thêm "cccccc" thành 12 > 8; văn bản 13 ký tự đứng một mình
    assert ec.batched(texts, max_items=10, max_chars=8) == [[0, 1], [2, 3], [4], [5], [6]]
    assert ec.batched(texts, max_items=10, max_chars=9) == [[0, 1], [2, 3, 4], [5], [6]]
    assert ec.batched([], 4, 10) == []


def test_batched_cover_in_order(ec):
    rng = np.random.default_rng(0)
    texts = ["x" * int(n) for n in rng.integers(1, 50, size=200)]
    batches = ec.batched(texts, max_items=16, max_chars=120)
    assert [i for b in batches for i in b] == list(range(200))
    for b in batches:
        assert len(b) <= 16
        assert len(b) == 1 or sum(len(texts[i]) for i in b) <= 120


# ---------- cache ----------


def test_cache_key(ec):
    k = ec.cache_key("bge-m3", "luật")
    assert k == ec.cache_key("bge-m3", "luật") and len(k) == 64
    assert k != ec.cache_key("nomic-embed-text", "luật"), "đổi model là đổi không gian vector: khoá phải khác"
    assert ec.cache_key("ab", "c") != ec.cache_key("a", "bc"), "cần dấu phân cách giữa model và text"


class Counting:
    def __init__(self):
        self.fake = FakeLLM(dim=16)
        self.calls: list[list[str]] = []

    def __call__(self, texts):
        self.calls.append(list(texts))
        return self.fake.embed(texts)


def test_embed_cached_dedup_order_and_batches(ec):
    embed_fn = Counting()
    cache: dict = {}
    texts = ["một", "hai", "một", "ba", "bốn", "hai"]
    out = ec.embed_cached(texts, "m", embed_fn, cache, max_items=2)
    assert embed_fn.calls == [["một", "hai"], ["ba", "bốn"]], "chỉ gửi văn bản chưa có, mỗi văn bản một lần"
    np.testing.assert_allclose(out, FakeLLM(dim=16).embed(texts))
    assert out.dtype == np.float32 and len(cache) == 4

    out2 = ec.embed_cached(["năm", "ba", "một"], "m", embed_fn, cache, max_items=2)
    assert embed_fn.calls[-1] == ["năm"] and len(embed_fn.calls) == 3
    np.testing.assert_allclose(out2, FakeLLM(dim=16).embed(["năm", "ba", "một"]))


def test_embed_cached_model_separates_entries(ec):
    embed_fn = Counting()
    cache: dict = {}
    ec.embed_cached(["a b"], "model-1", embed_fn, cache)
    ec.embed_cached(["a b"], "model-2", embed_fn, cache)
    assert len(embed_fn.calls) == 2 and len(cache) == 2


def test_embed_cached_respects_char_limit(ec):
    embed_fn = Counting()
    texts = ["x" * 30, "y" * 30, "z" * 30]
    ec.embed_cached(texts, "m", embed_fn, {}, max_items=32, max_chars=60)
    assert [len(c) for c in embed_fn.calls] == [2, 1]


# ---------- truncate ----------


def test_truncate_renormalizes(ec):
    v = np.array([[3.0, 4.0, 12.0], [0.0, 0.0, 5.0]])
    out = ec.truncate(v, 2)
    assert out.shape == (2, 2) and out.dtype == np.float32
    np.testing.assert_allclose(out, [[0.6, 0.8], [0.0, 0.0]], atol=1e-7)
    np.testing.assert_allclose(ec.truncate(np.array([1.0, 1.0, 1.0, 1.0]), 2), [2 ** -0.5, 2 ** -0.5], rtol=1e-6)

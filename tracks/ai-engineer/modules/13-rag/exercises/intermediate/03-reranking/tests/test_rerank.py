import sys
import types

import numpy as np
import pytest
from testkit import Exercise

ex = Exercise(__file__)


@pytest.fixture(scope="module")
def nb():
    return ex.notebook("rerank.ipynb")


def arts(nb, n):
    return [nb.Article(f"luat+{i}", f"Điều {i}. Tiêu đề {i}", f"nội dung {i}") for i in range(n)]


class FakeScore:
    """score_fn giả: điểm theo bảng, ghi lại mọi lời gọi."""

    def __init__(self, scores):
        self.scores = scores
        self.calls: list[tuple[str, list[str]]] = []

    def __call__(self, query, texts):
        self.calls.append((query, list(texts)))
        return self.scores[: len(texts)]


def test_rerank_orders_by_score(nb):
    cands = arts(nb, 5)
    fn = FakeScore([0.1, 0.9, 0.3, 0.7, 0.5])
    out = nb.rerank("câu hỏi", cands, fn, top_n=5)
    assert [a.uid for a in out] == ["luat+1", "luat+3", "luat+4", "luat+2", "luat+0"]
    assert out[0] is cands[1], "trả chính các Article ứng viên"


def test_rerank_calls_score_fn_once_with_title_and_text(nb):
    cands = arts(nb, 3)
    fn = FakeScore([0.2, 0.1, 0.3])
    nb.rerank("phạt nồng độ cồn", cands, fn, top_n=2)
    assert len(fn.calls) == 1, "chấm cả danh sách trong một lần gọi"
    query, texts = fn.calls[0]
    assert query == "phạt nồng độ cồn"
    assert texts == ["Điều 0. Tiêu đề 0\nnội dung 0", "Điều 1. Tiêu đề 1\nnội dung 1", "Điều 2. Tiêu đề 2\nnội dung 2"]


def test_rerank_top_n_cuts(nb):
    cands = arts(nb, 6)
    fn = FakeScore([0.6, 0.5, 0.4, 0.3, 0.2, 0.1])
    assert [a.uid for a in nb.rerank("q", cands, fn, top_n=2)] == ["luat+0", "luat+1"]
    assert len(nb.rerank("q", cands, FakeScore([0.6, 0.5, 0.4, 0.3, 0.2, 0.1]), top_n=10)) == 6


def test_rerank_ties_keep_retrieval_order(nb):
    cands = arts(nb, 5)
    out = nb.rerank("q", cands, FakeScore([0.5, 0.9, 0.5, 0.9, 0.5]), top_n=5)
    assert [a.uid for a in out] == ["luat+1", "luat+3", "luat+0", "luat+2", "luat+4"]


def test_rerank_accepts_numpy_scores_and_empty(nb):
    cands = arts(nb, 3)
    out = nb.rerank("q", cands, lambda q, t: np.array([0.1, 0.3, 0.2], dtype=np.float32), top_n=3)
    assert [a.uid for a in out] == ["luat+1", "luat+2", "luat+0"]
    fn = FakeScore([])
    assert nb.rerank("q", [], fn, top_n=5) == []
    assert fn.calls == [], "không có ứng viên thì không gọi score_fn"


@pytest.fixture
def fake_sentence_transformers(monkeypatch):
    """Thay module sentence_transformers bằng bản giả: không tải model, ghi lại mọi lần tạo và predict."""
    log = {"init": [], "predict": []}

    class CrossEncoder:
        def __init__(self, model_name, **kwargs):
            log["init"].append((model_name, kwargs))

        def predict(self, pairs, batch_size=32, **kwargs):
            log["predict"].append((list(pairs), batch_size))
            return np.array([len(text) for _, text in pairs], dtype=np.float32)

    module = types.ModuleType("sentence_transformers")
    module.CrossEncoder = CrossEncoder
    monkeypatch.setitem(sys.modules, "sentence_transformers", module)
    return log


def test_cross_encoder_score_fn_is_lazy(nb, fake_sentence_transformers):
    log = fake_sentence_transformers
    score = nb.cross_encoder_score_fn()
    assert callable(score)
    assert log["init"] == [], "tạo hàm chấm không được nạp model"

    out = score("câu hỏi", ["ngắn", "dài hơn nhiều"])
    assert len(log["init"]) == 1
    name, kwargs = log["init"][0]
    assert name == "BAAI/bge-reranker-v2-m3"
    assert kwargs.get("device") == "cpu" and kwargs.get("max_length") == 512
    assert log["predict"][0] == ([("câu hỏi", "ngắn"), ("câu hỏi", "dài hơn nhiều")], 16)
    assert out == [4.0, 13.0] and all(type(s) is float for s in out)

    score("câu khác", ["x"])
    assert len(log["init"]) == 1, "model nạp một lần, dùng lại cho các lần sau"
    assert len(log["predict"]) == 2


def test_cross_encoder_score_fn_options(nb, fake_sentence_transformers):
    log = fake_sentence_transformers
    score = nb.cross_encoder_score_fn("BAAI/bge-reranker-base", device="cuda", max_length=256, batch_size=4)
    score("q", ["a"])
    name, kwargs = log["init"][0]
    assert name == "BAAI/bge-reranker-base"
    assert kwargs.get("device") == "cuda" and kwargs.get("max_length") == 256
    assert log["predict"][0][1] == 4


def test_cross_encoder_with_rerank(nb, fake_sentence_transformers):
    cands = [nb.Article("a+1", "Điều 1.", "ngắn"), nb.Article("a+2", "Điều 2.", "văn bản dài nhất")]
    out = nb.rerank("q", cands, nb.cross_encoder_score_fn(), top_n=1)
    assert [a.uid for a in out] == ["a+2"]

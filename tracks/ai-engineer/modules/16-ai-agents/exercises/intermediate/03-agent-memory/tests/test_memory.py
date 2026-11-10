import json
import math

import numpy as np
import pytest

import llmkit
from llmkit import FakeLLM
from testkit import Exercise

ex = Exercise(__file__)


@pytest.fixture(scope="module")
def nb():
    return ex.notebook("memory.ipynb")


class TableEmbed:
    """Embedding giả: mỗi văn bản một vector cho trước (chưa chuẩn hoá), đếm số lần gọi."""

    def __init__(self, table):
        self.table = {k: np.asarray(v, dtype=np.float32) for k, v in table.items()}
        self.calls = 0

    def __call__(self, texts):
        self.calls += 1
        return np.stack([self.table[t] for t in texts])


def test_recency_weight(nb):
    assert nb.recency_weight(0, 168) == pytest.approx(1.0)
    assert nb.recency_weight(168, 168) == pytest.approx(0.5)
    assert nb.recency_weight(336, 168) == pytest.approx(0.25)
    assert nb.recency_weight(-5, 168) == pytest.approx(1.0), "tuổi âm coi như 0"


def test_add_normalizes_and_assigns_ids(nb):
    emb = TableEmbed({"a": [3, 4, 0], "b": [0, 0, 2]})
    store = nb.MemoryStore(emb)
    assert store.add("  a ", t=1.0, source=7) == "added"
    assert store.add("b", t=2.0, importance=0.9) == "added"
    assert [m.id for m in store.items] == [0, 1]
    m = store.items[0]
    assert m.text == "a" and m.t == 1.0 and m.source == 7 and m.importance == 0.5
    assert np.linalg.norm(m.vector) == pytest.approx(1.0) and m.vector[1] == pytest.approx(0.8)
    assert store.add("   ", t=3.0) == "skipped" and len(store.items) == 2


def test_dedup_updates_in_place(nb):
    emb = TableEmbed({"cũ": [1, 0, 0], "mới": [0.96, 0.28, 0], "khác": [0.5, -0.866, 0]})
    store = nb.MemoryStore(emb, dedup_threshold=0.95)
    store.add("cũ", t=1.0, importance=0.8, source=1)
    assert store.add("mới", t=5.0, importance=0.3, source=2) == "updated", "cos 0.96 >= 0.95"
    assert len(store.items) == 1
    m = store.items[0]
    assert (m.id, m.text, m.t, m.source, m.importance) == (0, "mới", 5.0, 2, 0.8)
    assert m.vector[1] == pytest.approx(0.28, abs=1e-6)
    assert store.add("khác", t=6.0) == "added", "cos 0.24 < 0.95 là ghi nhớ mới"
    assert [x.id for x in store.items] == [0, 1]


def test_dedup_threshold_inclusive(nb):
    emb = TableEmbed({"x": [1, 0], "y": [0.6, 0.8]})
    store = nb.MemoryStore(emb, dedup_threshold=0.6)
    store.add("x", t=0.0)
    assert store.add("y", t=1.0) == "updated", "cos đúng bằng ngưỡng cũng là trùng"


def test_capacity_evicts_lowest_retention(nb):
    emb = TableEmbed({f"m{i}": np.eye(7)[i] for i in range(7)})
    store = nb.MemoryStore(emb, capacity=3, half_life_hours=10)
    store.add("m0", t=0.0, importance=1.0)
    store.add("m1", t=10.0, importance=0.2)
    store.add("m2", t=20.0, importance=0.5)
    assert store.add("m3", t=20.0, importance=0.01) == "added"
    # lúc t=20: m0 1.0*0.25=0.25, m1 0.2*0.5=0.1, m2 0.5*1=0.5 -> xoá m1; m3 vừa thêm không bị xoá dù thấp nhất
    assert [m.text for m in store.items] == ["m0", "m2", "m3"]
    store.add("m4", t=40.0, importance=0.5)
    # t=40: m0 0.0625, m2 0.125, m3 0.0025 -> xoá m3
    assert [m.text for m in store.items] == ["m0", "m2", "m4"]
    store.add("m5", t=80.0, importance=0.5)
    # t=80: m0 1.0*0.5**8=0.004, m2 0.5*0.5**6=0.008, m4 0.5*0.5**4=0.031 -> xoá m0 dù importance cao nhất
    assert [m.text for m in store.items] == ["m2", "m4", "m5"]


def test_capacity_tie_breaks_older_then_lower_id(nb):
    emb = TableEmbed({f"m{i}": np.eye(5)[i] for i in range(5)})
    store = nb.MemoryStore(emb, capacity=2, half_life_hours=1e9)
    store.add("m0", t=5.0)
    store.add("m1", t=1.0)
    store.add("m2", t=6.0)
    assert [m.text for m in store.items] == ["m0", "m2"], "bằng điểm giữ lại cái mới hơn"


def test_search_scoring_and_order(nb):
    emb = TableEmbed({"q": [1, 0], "gần": [0.8, 0.6], "xa": [0, 1], "giữa": [0.6, 0.8]})
    store = nb.MemoryStore(emb, dedup_threshold=1.01, half_life_hours=10)
    store.add("gần", t=0.0, importance=0.1)
    store.add("xa", t=20.0, importance=1.0)
    store.add("giữa", t=10.0, importance=0.5)
    got = store.search("q", now=20.0, k=3)
    assert [m.text for m, _ in got] == ["gần", "giữa", "xa"]
    assert [s for _, s in got] == pytest.approx([0.8, 0.6, 0.0], abs=1e-6)
    got = store.search("q", now=20.0, k=2, w_rel=1.0, w_rec=1.0)
    # gần 0.8+0.25=1.05, giữa 0.6+0.5=1.1, xa 0+1=1.0
    assert [m.text for m, _ in got] == ["giữa", "gần"]
    assert got[0][1] == pytest.approx(1.1, abs=1e-6)
    got = store.search("q", now=20.0, k=1, w_rel=0.0, w_imp=1.0)
    assert got[0][0].text == "xa" and got[0][1] == pytest.approx(1.0)


def test_search_ties_newer_first_and_empty(nb):
    emb = TableEmbed({"q": [1, 0], "a": [1, 0], "b": [2, 0], "c": [0, 1]})
    store = nb.MemoryStore(emb, dedup_threshold=1.01)
    assert store.search("q", now=0.0) == []
    store.add("a", t=1.0)
    store.add("b", t=3.0)
    store.add("c", t=3.0)
    assert [m.text for m, _ in store.search("q", now=5.0, k=5, w_rel=0.0)] == ["c", "b", "a"]
    assert [m.text for m, _ in store.search("q", now=5.0, k=2)] == ["b", "a"]


def test_works_with_fakellm_embed(nb):
    store = nb.MemoryStore(FakeLLM().embed)
    store.add("Người dùng bị dị ứng hải sản.", t=0.0, source=2)
    store.add("Người dùng có con chó tên Mực.", t=1.0, source=3)
    store.add("Người dùng sống ở Đà Nẵng.", t=2.0, source=12)
    top = store.search("con chó tên gì", now=3.0, k=1)
    assert top[0][0].source == 3


class SchemaFake(FakeLLM):
    def __init__(self, replies):
        super().__init__(replies)
        self.schemas = []

    def chat(self, messages, *, model=None, temperature=0.0, json_schema=None):
        self.schemas.append(json_schema)
        return super().chat(messages, model=model, temperature=temperature, json_schema=json_schema)


def test_extract_facts_prompt_and_parse(nb):
    fake = SchemaFake([json.dumps({"facts": [" Người dùng tên Minh. ", "", 42, "Người dùng 29 tuổi."]},
                                  ensure_ascii=False)])
    out = nb.extract_facts(fake, "Mình tên Minh, 29 tuổi.")
    assert out == ["Người dùng tên Minh.", "Người dùng 29 tuổi."]
    assert fake.calls[0] == [{"role": "system", "content": nb.EXTRACT_SYSTEM},
                             {"role": "user", "content": 'Câu: "Mình tên Minh, 29 tuổi."'}]
    assert fake.schemas == [nb.FACT_SCHEMA]


@pytest.mark.parametrize("reply", ["không phải JSON", '{"facts": "tên Minh"}', '{"fact": []}', "[]", '{"facts": [',
                                   '{"facts": []}'])
def test_extract_facts_broken_is_empty(nb, reply):
    assert nb.extract_facts(FakeLLM([reply]), "Mình tên Minh.") == []


def test_extract_facts_llm_error(nb):
    class Down(FakeLLM):
        def chat(self, messages, **kwargs):
            raise llmkit.LLMError("Ollama tắt")

    assert nb.extract_facts(Down(), "Mình tên Minh.") == []


def test_dialogue_fixture(nb):
    import dialogue

    turns = dialogue.build_sessions()
    assert len(turns) == 108 and sum(t["fact_id"] is not None for t in turns) == 24
    store = nb.MemoryStore(FakeLLM().embed)
    statuses = [store.add(t["user"], t["session"] * 168.0, source=t["fact_id"]) for t in turns]
    assert statuses.count("updated") > 0, "chuyện phiếm lặp lại nguyên văn phải được gộp"
    assert math.isclose(len(store.items) + statuses.count("updated"), 108)

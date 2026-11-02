import re

import pytest
from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.documents import Document
from langchain_core.language_models.fake_chat_models import FakeListChatModel
from langchain_core.runnables import RunnableLambda
from llmkit import FakeLLM
from testkit import Exercise

ex = Exercise(__file__)

QUESTION = "Công an xã có được xử phạt lỗi không mang bằng lái xe không?"
REFUSAL = "Không tìm thấy căn cứ trong tài liệu được cung cấp."
ROWS = [
    ("47/2011/tt-bca+7", "Điều 7. Nhiệm vụ của Công an xã", "4. Công an xã được xử lý các hành vi ...", 0.81),
    ("100/2019/nđ-cp+74", "Điều 74. Phân định thẩm quyền xử phạt", "1. Cảnh sát giao thông xử phạt ...", 0.77),
    ("01/2009/tt-bnn+1", "Điều 1. Phạm vi áp dụng", "Thông tư này hướng dẫn tuần tra, canh gác bảo vệ đê", 0.62),
    ("47/2011/tt-bca+7", "Điều 7. Nhiệm vụ của Công an xã", "5. Khi phát hiện vi phạm, Công an xã lập biên bản ...", 0.58),
]


@pytest.fixture(scope="module")
def nb():
    return ex.notebook("frameworks.ipynb")


def hits(nb, scores=None):
    rows = ROWS if scores is None else [(*r[:3], s) for r, s in zip(ROWS, scores)]
    return [(nb.Article(u, t, x), s) for u, t, x, s in rows]


def documents(hit_list):
    return [Document(page_content=a.text, metadata={"uid": a.uid, "title": a.title, "score": s}) for a, s in hit_list]


class Capture(BaseCallbackHandler):
    """Ghi lại mọi lần chat model được gọi và các message nó nhận."""

    def __init__(self):
        self.prompts = []

    def on_chat_model_start(self, serialized, messages, **kwargs):
        self.prompts.append(messages[0])


def run_chain(nb, hit_list, reply, min_score=0.5, question=QUESTION):
    seen = []

    def retrieve(q):
        seen.append(q)
        return documents(hit_list)

    capture = Capture()
    chain = nb.build_chain(RunnableLambda(retrieve), FakeListChatModel(responses=[reply]), min_score)
    result = chain.invoke(question, config={"callbacks": [capture]})
    return result, capture.prompts, seen


# ---------- Bản SDK (dán từ Intermediate 02) ----------

def test_sdk_baseline(nb):
    assert nb.parse_citations("Theo [2], phạt tiền [1]. Xem [7] và [2], [0].", 5) == [2, 1]
    msgs = nb.build_messages(QUESTION, [a for a, _ in hits(nb)])
    assert [m["role"] for m in msgs] == ["system", "user"]
    assert REFUSAL in msgs[0]["content"] and msgs[1]["content"].rstrip().endswith(QUESTION)
    assert "[1] 47/2011/tt-bca, Điều 7. Nhiệm vụ của Công an xã" in msgs[1]["content"]
    fake = FakeLLM(["Công an xã chỉ xử lý hành vi liệt kê [4][1]; thẩm quyền ở [2]. Xem [9]."])
    result = nb.answer(QUESTION, lambda q: hits(nb), fake, 0.5)
    assert result.citations == ["47/2011/tt-bca+7", "100/2019/nđ-cp+74"] and result.refused is False
    gated = FakeLLM([])
    assert nb.answer(QUESTION, lambda q: hits(nb, [0.4, 0.3, 0.2, 0.1]), gated, 0.5).refused is True
    assert gated.calls == []


# ---------- Bản LangChain ----------

def test_build_chain_runs_with_fake_chat_model(nb):
    reply = "Công an xã chỉ xử lý các hành vi liệt kê [1]; thẩm quyền xử phạt ở [2]. Xem [7], [4]."
    result, prompts, seen = run_chain(nb, hits(nb), reply)
    assert isinstance(result, nb.RagAnswer), "chain.invoke trả RagAnswer"
    assert result.text == reply
    assert result.citations == ["47/2011/tt-bca+7", "100/2019/nđ-cp+74"], "[7] bị bỏ, [4] trùng uid với [1]"
    assert result.refused is False
    assert len(prompts) == 1, "gọi model đúng một lần"
    assert seen == [QUESTION], "retriever nhận đúng câu hỏi, một lần"


def test_chain_prompt_is_build_messages(nb):
    _, prompts, _ = run_chain(nb, hits(nb), "Theo [1].")
    sent = prompts[0]
    expected = nb.build_messages(QUESTION, [a for a, _ in hits(nb)])
    roles = {"system": "system", "human": "user"}
    assert [roles.get(m.type, m.type) for m in sent] == ["system", "user"], "đúng hai message: system và human"
    assert [m.content for m in sent] == [m["content"] for m in expected], "prompt bằng hệt build_messages"


@pytest.mark.parametrize("scores", [[0.49, 0.41, 0.30, 0.2], []])
def test_chain_gate_skips_model(nb, scores):
    hit_list = hits(nb, scores) if scores else []
    result, prompts, _ = run_chain(nb, hit_list, "KHÔNG ĐƯỢC GỌI MODEL")
    assert prompts == [], "mọi điểm dưới min_score (hoặc không có nguồn) thì không gọi model"
    assert result == nb.RagAnswer(REFUSAL, [], True)


def test_chain_gate_uses_best_score(nb):
    result, prompts, _ = run_chain(nb, hits(nb, [0.9, 0.1, 0.1, 0.1]), "Theo [3].")
    assert len(prompts) == 1 and "[4]" in prompts[0][-1].content, "hit điểm thấp vẫn vào prompt"
    assert result.citations == ["01/2009/tt-bnn+1"]


def test_chain_detects_model_refusal(nb):
    result, prompts, _ = run_chain(nb, hits(nb), REFUSAL)
    assert len(prompts) == 1
    assert result == nb.RagAnswer(REFUSAL, [], True)


@pytest.mark.parametrize("reply", [
    "Không, theo khoản 4 Điều 7 [1], Công an xã chỉ xử lý hành vi liệt kê. Thẩm quyền chung ở [2][2].",
    "Theo Điều 5 Nghị định 100/2019/NĐ-CP, phạt tiền từ 800.000 đồng.",
    "Không tìm thấy căn cứ trong tài liệu được cung cấp. Theo [3] không có quy định.",
])
def test_chain_matches_sdk(nb, reply):
    chain_result, _, _ = run_chain(nb, hits(nb), reply)
    sdk_result = nb.answer(QUESTION, lambda q: hits(nb), FakeLLM([reply]), 0.5)
    assert chain_result == sdk_result, "cùng câu trả lời của model thì hai bản cho cùng RagAnswer"


# ---------- So sánh ----------

def test_compare_written():
    doc = ex.read("COMPARE.md")
    assert "TODO" not in doc
    assert len(doc.split()) >= 400, "so sánh: ít nhất 400 từ"
    assert re.search(r"^\|.*\|\s*$", doc, re.M), "cần bảng so sánh"

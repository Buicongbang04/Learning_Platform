import json
import math
import re

import pandas as pd
import pytest
from llmkit import FakeLLM
from testkit import Exercise

ex = Exercise(__file__)

COLUMNS = ["config", "n", "recall@5", "mrr@10", "context_hit", "refused", "faithfulness", "relevance",
           "judge_nan", "latency_s"]
PASSAGES = [
    "47/2011/tt-bca, Điều 7. Nhiệm vụ của Công an xã\n4. Công an xã được xử lý các hành vi: không đội mũ bảo hiểm ...",
    "100/2019/nđ-cp, Điều 74. Phân định thẩm quyền xử phạt\n1. Cảnh sát giao thông xử phạt ...",
]
ANSWER = "Công an xã chỉ xử lý các hành vi được liệt kê [1]. Không mang bằng lái không nằm trong danh sách [1]."


@pytest.fixture(scope="module")
def nb():
    return ex.notebook("eval.ipynb")


class SchemaLLM(FakeLLM):
    """FakeLLM ghi lại cả json_schema của mỗi lời gọi."""

    def __init__(self, replies):
        super().__init__(replies)
        self.schemas = []

    def chat(self, messages, *, model=None, temperature=0.0, json_schema=None):
        self.schemas.append(json_schema)
        return super().chat(messages, model=model, temperature=temperature, json_schema=json_schema)


def claims(*flags):
    return json.dumps({"claims": [{"claim": f"ý {i}", "supported": f} for i, f in enumerate(flags)]},
                      ensure_ascii=False)


# ---------- Thước đo retrieval (dán từ Basic 03) ----------

def test_retrieval_metrics_hand_example(nb):
    # Ví dụ mục 6 lý thuyết: đúng {A, B}, hệ thống trả [C, A, D, B, E]
    retrieved, relevant = [["C", "A", "D", "B", "E"]], [{"A", "B"}]
    assert nb.recall_at_k(retrieved, relevant, 3) == pytest.approx(0.5)
    assert nb.recall_at_k(retrieved, relevant, 5) == pytest.approx(1.0)
    assert nb.mrr_at_k(retrieved, relevant, 10) == pytest.approx(0.5)
    assert nb.mrr_at_k(retrieved, relevant, 1) == pytest.approx(0.0)
    two = [["A", "X"], ["X", "Y", "B"]]
    assert nb.mrr_at_k(two, [{"A"}, {"B"}], 10) == pytest.approx((1 + 1 / 3) / 2)


# ---------- Judge faithfulness ----------

def test_faithfulness_parses_claims(nb):
    llm = SchemaLLM([claims(True, False, True)])
    score = nb.judge_faithfulness(ANSWER, PASSAGES, llm)
    assert isinstance(score, float) and score == pytest.approx(2 / 3)
    assert len(llm.calls) == 1, "gọi judge đúng một lần"
    assert llm.schemas[0] == nb.FAITHFULNESS_SCHEMA, "truyền json_schema=FAITHFULNESS_SCHEMA"


def test_faithfulness_prompt_has_answer_and_every_passage(nb):
    llm = SchemaLLM([claims(True)])
    assert nb.judge_faithfulness(ANSWER, PASSAGES, llm) == 1.0
    prompt = "\n".join(m["content"] for m in llm.calls[0])
    assert ANSWER in prompt
    for p in PASSAGES:
        assert p in prompt, "judge phải thấy mọi đoạn nguồn"


def test_faithfulness_all_unsupported_is_zero(nb):
    assert nb.judge_faithfulness(ANSWER, PASSAGES, FakeLLM([claims(False, False)])) == 0.0


@pytest.mark.parametrize("reply", [
    "Câu trả lời này trung thực.",                            # không phải JSON
    '{"claims": [{"claim": "a", "supported": tr',               # JSON bị cắt giữa chừng
    '{"verdict": "ok"}',                                       # thiếu khoá claims
    '{"claims": "tất cả đều đúng"}',                           # claims sai kiểu
    '{"claims": [{"claim": "a"}]}',                            # thiếu supported
    '{"claims": [{"claim": "a", "supported": "yes"}]}',        # supported không phải bool
    '{"claims": []}',                                          # không có khẳng định nào để chấm
    "[]",
])
def test_faithfulness_broken_json_is_nan(nb, reply):
    score = nb.judge_faithfulness(ANSWER, PASSAGES, FakeLLM([reply]))
    assert isinstance(score, float) and math.isnan(score), f"{reply!r} phải cho nan, không crash"


class DownLLM(FakeLLM):
    """Judge không gọi được: Ollama tắt, quá thời gian chờ, gateway trả 504."""

    def chat(self, messages, **kwargs):
        import llmkit

        self.calls.append(messages)
        raise llmkit.LLMError("HTTP 504 Gateway Timeout")


def test_judges_survive_llm_errors(nb):
    down = DownLLM()
    faith = nb.judge_faithfulness(ANSWER, PASSAGES, down)
    rel = nb.judge_relevance("?", ANSWER, down)
    assert math.isnan(faith) and math.isnan(rel), "llm.chat ném LLMError thì trả nan, không crash"
    assert len(down.calls) == 2


# ---------- Judge relevance ----------

@pytest.mark.parametrize("score, expected", [(5, 1.0), (4, 0.75), (1, 0.0)])
def test_relevance_maps_score(nb, score, expected):
    llm = SchemaLLM([json.dumps({"reason": "trả lời đúng câu hỏi", "score": score}, ensure_ascii=False)])
    assert nb.judge_relevance("Công an xã có được phạt không?", ANSWER, llm) == pytest.approx(expected)
    assert llm.schemas[0] == nb.RELEVANCE_SCHEMA
    prompt = "\n".join(m["content"] for m in llm.calls[0])
    assert "Công an xã có được phạt không?" in prompt and ANSWER in prompt


@pytest.mark.parametrize("reply", [
    "điểm 5", '{"reason": "ok"}', '{"reason": "ok", "score": 9}', '{"reason": "ok", "score": 0}',
    '{"reason": "ok", "score": "năm"}', '{"reason": "ok", "score": 3.5}', '{"reason": "ok", "score": true}',
])
def test_relevance_broken_is_nan(nb, reply):
    score = nb.judge_relevance("?", ANSWER, FakeLLM([reply]))
    assert isinstance(score, float) and math.isnan(score), f"{reply!r} phải cho nan"


# ---------- run_eval ----------

def make_questions(nb):
    return [nb.Question("q1", "câu một", {"A"}), nb.Question("q2", "câu hai", {"B"}),
            nb.Question("q3", "câu ba", {"C", "D"})]


def scripted(nb, outputs, calls):
    def config(text):
        calls.append(text)
        return outputs[text]
    return config


def test_run_eval_table(nb, monkeypatch):
    qs = make_questions(nb)
    good = {
        "câu một": nb.RagOutput(["A", "X"], [("A", "đoạn A")], "Trả lời một [1].", False, 2.0),
        "câu hai": nb.RagOutput(["X", "Y", "B"], [("X", "đoạn X")], "Trả lời hai [1].", False, 4.0),
        "câu ba": nb.RagOutput(["Z", "C"], [("C", "đoạn C"), ("Z", "đoạn Z")], "Không tìm thấy căn cứ ...", True, 1.0),
    }
    weak = {
        "câu một": nb.RagOutput(["X", "A"], [("X", "đoạn X")], "Một.", False, 0.5),
        "câu hai": nb.RagOutput(["Y", "X"], [("Y", "đoạn Y")], "Hai.", False, 0.5),
        "câu ba": nb.RagOutput(["D"], [("D", "đoạn D")], "Ba.", False, 0.5),
    }
    judged = []

    def fake_faith(answer, passages, llm):
        judged.append(("faith", answer, list(passages)))
        return {"Trả lời một [1].": 1.0, "Trả lời hai [1].": 0.5, "Một.": math.nan}.get(answer, 0.0)

    def fake_rel(question, answer, llm):
        judged.append(("rel", question, answer))
        return 0.75

    monkeypatch.setattr(nb, "judge_faithfulness", fake_faith)
    monkeypatch.setattr(nb, "judge_relevance", fake_rel)
    calls_good, calls_weak = [], []
    df = nb.run_eval({"tốt": scripted(nb, good, calls_good), "yếu": scripted(nb, weak, calls_weak)}, qs,
                     judge=FakeLLM([]))

    assert isinstance(df, pd.DataFrame)
    assert list(df.columns) == COLUMNS, "cột đúng COLUMNS, đúng thứ tự"
    assert list(df["config"]) == ["tốt", "yếu"] and len(df) == 2
    assert calls_good == ["câu một", "câu hai", "câu ba"], "gọi mỗi cấu hình đúng một lần mỗi câu, theo thứ tự"
    assert calls_weak == ["câu một", "câu hai", "câu ba"]
    assert ("faith", "Không tìm thấy căn cứ ...", ["đoạn C", "đoạn Z"]) not in judged, "câu từ chối không gửi judge"
    assert ("faith", "Trả lời một [1].", ["đoạn A"]) in judged, "judge faithfulness nhận đúng đoạn văn của context"
    assert ("rel", "câu hai", "Trả lời hai [1].") in judged

    g, w = df.iloc[0], df.iloc[1]
    assert g["n"] == 3
    assert g["recall@5"] == pytest.approx((1 + 1 + 0.5) / 3)
    assert g["mrr@10"] == pytest.approx((1 + 1 / 3 + 1 / 2) / 3)
    assert g["context_hit"] == pytest.approx(2 / 3)
    assert g["refused"] == pytest.approx(1 / 3)
    assert g["faithfulness"] == pytest.approx(0.75), "trung bình trên câu không từ chối"
    assert g["relevance"] == pytest.approx(0.75)
    assert g["judge_nan"] == 0
    assert g["latency_s"] == pytest.approx(2.0), "trung vị của seconds"
    assert w["refused"] == 0
    assert w["context_hit"] == pytest.approx(1 / 3)
    assert w["faithfulness"] == pytest.approx(0.0), "bỏ qua nan khi lấy trung bình"
    assert w["judge_nan"] == 1


def test_run_eval_broken_judge_does_not_crash(nb):
    qs = make_questions(nb)
    outputs = {q.text: nb.RagOutput(sorted(q.relevant), [("A", "đoạn")], "Trả lời [1].", False, None)
               for q in qs}
    judge = FakeLLM(lambda messages: "xin lỗi, tôi không chấm được")     # mọi lời gọi đều không phải JSON
    df = nb.run_eval({"cấu hình": scripted(nb, outputs, [])}, qs, judge=judge)
    row = df.iloc[0]
    assert len(judge.calls) == 6, "3 câu không từ chối x 2 judge"
    assert math.isnan(row["faithfulness"]) and math.isnan(row["relevance"])
    assert row["judge_nan"] == 6
    assert row["recall@5"] == pytest.approx(1.0)
    assert row["latency_s"] >= 0.0, "seconds = None thì run_eval tự đo"


def test_run_eval_default_judge_is_llmkit_client(nb):
    import llmkit

    qs = make_questions(nb)[:1]
    outputs = {qs[0].text: nb.RagOutput(["A"], [("A", "đoạn A")], "Trả lời [1].", False, 1.0)}
    class BySchema(FakeLLM):
        def chat(self, messages, *, model=None, temperature=0.0, json_schema=None):
            self.calls.append(messages)
            if "claims" in (json_schema or {}).get("properties", {}):
                return claims(True, True)
            return json.dumps({"reason": "ok", "score": 5})

    fake = BySchema()
    with llmkit.use(fake):
        df = nb.run_eval({"c": scripted(nb, outputs, [])}, qs)
    assert len(fake.calls) == 2, "judge=None thì dùng llmkit.get_client()"
    assert df.iloc[0]["faithfulness"] == pytest.approx(1.0) and df.iloc[0]["relevance"] == pytest.approx(1.0)


# ---------- Báo cáo ----------

def test_report_written():
    doc = ex.read("REPORT.md")
    assert "TODO" not in doc
    assert len(doc.split()) >= 500, "báo cáo: ít nhất 500 từ"
    assert re.search(r"^\|.*\|\s*$", doc, re.M), "cần bảng so sánh cấu hình"

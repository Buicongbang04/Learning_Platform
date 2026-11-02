"""M03: chunk theo khoản có địa chỉ, prompt có nguồn, trích dẫn, cổng từ chối, judge, tổng hợp số liệu."""

import json
import math

import pytest

import llmkit
from llmkit import FakeLLM


def _articles(la, mini):
    return {a.uid: a for a in la("data").load_corpus(mini)}


def test_split_clauses_by_khoan_and_diem(la, mini):
    chunking = la("chunking")
    art = _articles(la, mini)["901/2099/nđ-cp+2"]
    short = chunking.split_clauses(art, max_chars=1500)
    assert [p.label for p in short] == ["khoản 1", "khoản 2", "khoản 3"]
    assert all(p.uid == art.uid for p in short)
    assert all(p.text.startswith("Điều 2. Xử phạt người nuôi ong không đăng ký\n") for p in short)
    assert "200.000 đồng đến 400.000 đồng" in short[0].text and "a) Đặt thùng ong" in short[1].text
    tight = chunking.split_clauses(art, max_chars=100)
    assert [p.label for p in tight] == ["khoản 1", "khoản 2 điểm a", "khoản 2 điểm b", "khoản 3"]
    point_b = tight[2].text
    assert point_b.startswith("Điều 2.") and "2. Phạt tiền từ 1.000.000" in point_b
    assert "b) Không treo biển" in point_b and "a) Đặt thùng" not in point_b


def test_split_clauses_preamble_plain_and_empty(la, mini):
    chunking = la("chunking")
    arts = _articles(la, mini)
    hs = chunking.split_clauses(arts["77/2098/tt-bxd+3"])
    assert [p.label for p in hs] == ["", "khoản 1", "khoản 2", "khoản 3"]
    assert hs[0].text == "Điều 3. Hồ sơ xin giấy phép\nHồ sơ gồm:"
    plain = chunking.split_clauses(arts["77/2098/tt-bxd+2"])
    assert len(plain) == 1 and plain[0].label == "" and "6 mét" in plain[0].text
    assert "khoản 2. Trường hợp đặc biệt" in plain[0].text
    empty = chunking.split_clauses(arts["77/2098/tt-bxd+4"])
    assert [(p.label, p.text) for p in empty] == [("", "Điều 4. Điều khoản thi hành")]
    money = chunking.split_clauses(arts["901/2099/nđ-cp+3"])
    assert len(money) == 1 and money[0].text.endswith("2.000.000 đồng là mức tối đa áp dụng cho cá nhân.")


def _passages(la):
    chunking = la("chunking")
    return [
        chunking.Passage("901/2099/nđ-cp+2", "khoản 1", "Điều 2. Xử phạt\n1. Phạt tiền từ 200.000 đồng"),
        chunking.Passage("77/2098/tt-bxd+2", "", "Điều 2. Chiều cao\nKhông quá 6 mét"),
        chunking.Passage("901/2099/nđ-cp+2", "khoản 3", "Điều 2. Xử phạt\n3. Buộc di chuyển thùng ong"),
    ]


def test_build_messages(la):
    citations = la("citations")
    ps = _passages(la)
    msgs = citations.build_messages("Nuôi ong không đăng ký bị phạt bao nhiêu?", ps)
    assert [m["role"] for m in msgs] == ["system", "user"]
    assert citations.REFUSAL in msgs[0]["content"]
    assert "[số]" in msgs[0]["content"] or "[1]" in msgs[0]["content"]
    user = msgs[1]["content"]
    positions = [user.index(f"[{i}]") for i in (1, 2, 3)]
    assert positions == sorted(positions)
    for i, p in enumerate(ps):
        assert p.text in user
        assert user.index(f"[{i + 1}]") < user.index(p.text)
    header1 = user[positions[0]: user.index(ps[0].text)]
    assert "901/2099/nđ-cp" in header1 and "Điều 2" in header1 and "khoản 1" in header1
    assert user.rindex("Nuôi ong không đăng ký bị phạt bao nhiêu?") > user.index(ps[-1].text)
    assert "[4]" not in user


def test_parse_citations(la):
    citations = la("citations")
    assert citations.parse_citations("Theo [2], phạt tiền [7]. Xem thêm [1][2] và [0].", 5) == [2, 1]
    assert citations.parse_citations("nguồn [1, 3] hoặc nguồn số 1", 5) == []
    assert citations.parse_citations("[3]", 3) == [3]
    assert citations.parse_citations("không có trích dẫn", 5) == []


def test_is_refusal(la):
    citations = la("citations")
    assert citations.is_refusal(citations.REFUSAL)
    assert citations.is_refusal("không tìm thấy căn cứ trong tài liệu được cung cấp. Bạn nên hỏi luật sư.")
    assert not citations.is_refusal("Phạt tiền từ 200.000 đồng [1].")


def test_cited_uids(la):
    citations = la("citations")
    ps = _passages(la)
    assert citations.cited_uids("Phạt tiền [3] và buộc di chuyển [1]; chiều cao [2] [9]", ps) == [
        "901/2099/nđ-cp+2", "77/2098/tt-bxd+2",
    ]


def test_answer_gate_skips_llm(la):
    rag, citations = la("rag"), la("citations")
    ps = _passages(la)
    fake = FakeLLM([])
    out = rag.answer("Giá vàng hôm nay?", lambda q: [(ps[0], 0.31), (ps[1], 0.29)], fake, min_score=0.5)
    assert out.text == citations.REFUSAL and out.refused and out.gated and out.citations == []
    assert fake.calls == []
    out = rag.answer("?", lambda q: [], fake, min_score=0.5)
    assert out.gated and fake.calls == []


def test_answer_calls_llm_once_and_parses(la):
    rag = la("rag")
    ps = _passages(la)
    fake = FakeLLM(["Phạt từ 200.000 đồng [1], buộc di chuyển thùng ong [3] [8]."])
    out = rag.answer("Nuôi ong không đăng ký?", lambda q: [(ps[0], 0.45), (ps[1], 0.8), (ps[2], 0.6)], fake, 0.5)
    assert len(fake.calls) == 1
    assert "Nuôi ong không đăng ký?" in fake.calls[0][-1]["content"]
    assert out.citations == ["901/2099/nđ-cp+2"]
    assert not out.refused and not out.gated
    assert out.passages == ps
    assert out.seconds >= 0


def test_answer_llm_refusal(la):
    rag, citations = la("rag"), la("citations")
    ps = _passages(la)
    fake = FakeLLM([citations.REFUSAL + " Theo [1] thì không rõ."])
    out = rag.answer("?", lambda q: [(ps[0], 0.9)], fake, 0.5)
    assert out.refused and not out.gated and out.citations == []


def _claims(*flags):
    return json.dumps({"claims": [{"claim": f"ý {i}", "supported": f} for i, f in enumerate(flags)]})


def test_judge_faithfulness_ratio_and_prompt(la):
    judge = la("judge")
    fake = FakeLLM([_claims(True, False, True)])
    score = judge.judge_faithfulness("Phạt 200.000 đồng [1]. Phải đi tù [2].", ["nguồn một ABC", "nguồn hai XYZ"], fake)
    assert score == pytest.approx(2 / 3)
    assert len(fake.calls) == 1
    prompt = "\n".join(m["content"] for m in fake.calls[0])
    assert "Phải đi tù" in prompt and "nguồn một ABC" in prompt and "nguồn hai XYZ" in prompt


def test_judge_faithfulness_bad_outputs_are_nan(la):
    judge = la("judge")
    bad = ["không phải JSON", json.dumps({"claims": []}), json.dumps({"x": 1}),
           json.dumps({"claims": [{"claim": "a", "supported": "yes"}]}), json.dumps({"claims": [{"claim": "a"}]}),
           json.dumps([1, 2])]
    for raw in bad:
        assert math.isnan(judge.judge_faithfulness("a", ["b"], FakeLLM([raw]))), raw

    def broken(messages):
        raise llmkit.LLMError("gateway 504")

    assert math.isnan(judge.judge_faithfulness("a", ["b"], FakeLLM(broken)))


def test_rag_summary(la):
    judge = la("judge")
    nan = float("nan")
    records = [
        {"refused": False, "citations": ["A"], "context": ["A", "B"], "relevant": ["A"], "faithfulness": 1.0},
        {"refused": False, "citations": ["B", "C"], "context": ["B", "C"], "relevant": ["A"], "faithfulness": 0.5},
        {"refused": True, "citations": [], "context": ["A"], "relevant": ["A"], "faithfulness": nan},
        {"refused": True, "citations": [], "context": ["D"], "relevant": ["A"]},
        {"refused": False, "citations": [], "context": ["E"], "relevant": ["E"], "faithfulness": nan},
    ]
    s = judge.rag_summary(records)
    assert s["n"] == 5
    assert s["context_hit"] == pytest.approx(3 / 5)
    assert s["refused"] == pytest.approx(2 / 5)
    assert s["refused_with_hit"] == 1
    assert s["cited_any"] == pytest.approx(2 / 5)
    assert s["cited_correct"] == pytest.approx(1 / 5)
    assert s["citation_precision"] == pytest.approx(1 / 3)
    assert s["faithfulness"] == pytest.approx(0.75)
    assert s["fully_faithful"] == pytest.approx(0.5)
    assert s["judge_nan"] == 1
    none = judge.rag_summary([{"refused": True, "citations": [], "context": [], "relevant": ["A"]}])
    assert math.isnan(none["faithfulness"]) and math.isnan(none["citation_precision"])
    with pytest.raises(ValueError):
        judge.rag_summary([])


def test_citation_precision_counts_every_correct_citation(la):
    judge = la("judge")
    records = [
        {"refused": False, "citations": ["A", "B"], "context": ["A", "B"], "relevant": ["A", "B"], "faithfulness": 1.0},
        {"refused": False, "citations": ["C"], "context": ["C"], "relevant": ["A"], "faithfulness": 1.0},
    ]
    s = judge.rag_summary(records)
    assert s["citation_precision"] == pytest.approx(2 / 3)
    assert s["cited_correct"] == pytest.approx(1 / 2)

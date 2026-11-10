import pytest
from llmkit import FakeLLM
from testkit import Exercise

ex = Exercise(__file__)

QUESTION = "Công an xã có được xử phạt lỗi không mang bằng lái xe không?"
REFUSAL = "Không tìm thấy căn cứ trong tài liệu được cung cấp."


@pytest.fixture(scope="module")
def nb():
    return ex.notebook("rag.ipynb")


def passages(nb, n=5):
    data = [
        ("100/2019/nđ-cp+74", "Điều 74. Phân định thẩm quyền xử phạt", "1. Cảnh sát giao thông xử phạt ..."),
        ("47/2011/tt-bca+7", "Điều 7. Nhiệm vụ của Công an xã", "4. Công an xã được xử lý các hành vi ..."),
        ("01/2009/tt-bnn+1", "Điều 1. Phạm vi áp dụng", "Thông tư này hướng dẫn tuần tra, canh gác bảo vệ đê"),
        ("47/2011/tt-bca+7", "Điều 7. Nhiệm vụ của Công an xã", "5. Khi phát hiện vi phạm, Công an xã lập biên bản ..."),
        ("12/2017/tt-bgtvt+16", "Điều 16. Giấy phép lái xe", "1. Giấy phép lái xe có thời hạn ..."),
    ]
    return [nb.Article(*row) for row in data[:n]]


def test_build_messages_shape(nb):
    msgs = nb.build_messages(QUESTION, passages(nb))
    assert [m["role"] for m in msgs] == ["system", "user"]
    assert all(isinstance(m["content"], str) for m in msgs)
    system, user = msgs[0]["content"], msgs[1]["content"]
    assert nb.REFUSAL == REFUSAL
    assert REFUSAL in system, "system phải chứa đúng câu từ chối để code nhận ra được"
    assert "nguồn" in system.lower()
    assert "[" in system, "nói rõ định dạng trích dẫn [số]"
    assert user.rstrip().endswith(QUESTION), "câu hỏi đứng cuối message user"


def test_build_messages_numbered_sources_in_order(nb):
    ps = passages(nb)
    user = nb.build_messages(QUESTION, ps)[1]["content"]
    positions = []
    for i, p in enumerate(ps, start=1):
        header = f"[{i}] {p.uid.rsplit('+', 1)[0]}, {p.title}"
        assert header in user, f"thiếu dòng đầu nguồn: {header!r}"
        assert p.text in user
        positions.append(user.index(header))
        assert user.index(header) < user.index(p.text), "nội dung đứng sau dòng đầu của nguồn"
    assert positions == sorted(positions), "nguồn theo đúng thứ tự passages"
    assert "[6]" not in user
    assert user.index(ps[-1].text) < user.index(QUESTION)


def test_build_messages_few_passages(nb):
    user = nb.build_messages(QUESTION, passages(nb, 2))[1]["content"]
    assert "[1]" in user and "[2]" in user and "[3]" not in user


def test_parse_citations(nb):
    assert nb.parse_citations("Theo [2], phạt tiền [1]. Xem [7] và [2], [0].", 5) == [2, 1]
    assert nb.parse_citations("Có [1][3] và [3].", 3) == [1, 3]
    assert nb.parse_citations("Không có trích dẫn nào, chỉ có [a] và 1.", 5) == []
    assert nb.parse_citations("Nguồn [5] và [6].", 5) == [5]
    assert nb.parse_citations(REFUSAL, 5) == []


def fixed_retrieve(nb, scores):
    hits = list(zip(passages(nb, len(scores)), scores))
    seen = []

    def retrieve(q):
        seen.append(q)
        return hits

    return retrieve, seen


def test_answer_maps_citations_to_uids(nb):
    retrieve, seen = fixed_retrieve(nb, [0.81, 0.77, 0.66, 0.60, 0.55])
    fake = FakeLLM(["Công an xã chỉ xử lý các hành vi liệt kê [2]; thẩm quyền xử phạt ở [1]. Xem [7], [4]."])
    result = nb.answer(QUESTION, retrieve, fake, min_score=0.5)
    assert seen == [QUESTION]
    assert len(fake.calls) == 1, "gọi LLM đúng một lần"
    assert fake.calls[0] == nb.build_messages(QUESTION, passages(nb)), "prompt dựng bằng build_messages với mọi hit"
    assert result.text.startswith("Công an xã chỉ xử lý")
    # [2] và [4] cùng là 47/2011/tt-bca+7: giữ một lần; [7] ngoài khoảng bị bỏ
    assert result.citations == ["47/2011/tt-bca+7", "100/2019/nđ-cp+74"]
    assert result.refused is False


def test_answer_gate_blocks_llm(nb):
    retrieve, _ = fixed_retrieve(nb, [0.49, 0.41, 0.30])
    fake = FakeLLM([])
    result = nb.answer("Giá vàng hôm nay?", retrieve, fake, min_score=0.5)
    assert fake.calls == [], "mọi điểm dưới min_score thì không được gọi LLM"
    assert result.refused is True and result.citations == [] and result.text == REFUSAL


def test_answer_no_hits_refuses(nb):
    fake = FakeLLM([])
    result = nb.answer("?", lambda q: [], fake, min_score=0.0)
    assert fake.calls == [] and result.refused is True and result.text == REFUSAL


def test_answer_gate_uses_best_score_and_keeps_all_hits(nb):
    retrieve, _ = fixed_retrieve(nb, [0.9, 0.1])
    fake = FakeLLM(["Theo [2]."])
    result = nb.answer(QUESTION, retrieve, fake, min_score=0.5)
    assert len(fake.calls) == 1
    assert "[2]" in fake.calls[0][1]["content"], "hit điểm thấp vẫn vào prompt khi điểm cao nhất qua cổng"
    assert result.citations == ["47/2011/tt-bca+7"]


def test_answer_detects_model_refusal(nb):
    retrieve, _ = fixed_retrieve(nb, [0.8, 0.7, 0.6])
    fake = FakeLLM([REFUSAL])
    result = nb.answer(QUESTION, retrieve, fake, min_score=0.5)
    assert len(fake.calls) == 1
    assert result.refused is True and result.citations == [] and result.text == REFUSAL

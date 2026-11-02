import re

import pytest

from testkit import Exercise

ex = Exercise(__file__)

SECTIONS = ["Bài toán", "Khối lượng và token", "Phương án và chi phí", "Độ trễ", "Model và giấy phép", "Vai trò",
            "Rủi ro và đo lường", "Khuyến nghị"]


@pytest.fixture(scope="module")
def nb():
    return ex.notebook("brief.ipynb")


def chars(text: str) -> list[str]:
    return list(text)


# ---------- request_tokens ----------


def test_request_tokens_counts_every_part(nb):
    # encode theo ký tự: câu hỏi 10, các điều 100, 30, 5
    q = "x" * 10
    arts = ["a" * 100, "b" * 30, "c" * 5]
    assert nb.request_tokens(q, arts, chars) == 150 + 10 + 135
    assert nb.request_tokens(q, arts, chars, system_tokens=0) == 145
    assert isinstance(nb.request_tokens(q, arts, chars), int)


def test_request_tokens_cap_and_k(nb):
    q = "x" * 10
    arts = ["a" * 100, "b" * 30, "c" * 5, "d" * 1000]
    # cắt mỗi điều ở 50: 50 + 30 + 5
    assert nb.request_tokens(q, arts, chars, system_tokens=0, max_article_tokens=50, k=3) == 10 + 85
    # k = 4 lấy cả điều dài, cắt ở 50
    assert nb.request_tokens(q, arts, chars, system_tokens=0, max_article_tokens=50, k=4) == 10 + 135
    # k mặc định 5, chỉ có 4 điều: không lỗi
    assert nb.request_tokens(q, arts, chars, system_tokens=0) == 10 + 1135
    assert nb.request_tokens(q, [], chars) == 160
    assert nb.request_tokens(q, arts, chars, system_tokens=0, k=0) == 10


def test_request_tokens_uses_encode(nb):
    words = str.split
    assert nb.request_tokens("phạt bao nhiêu tiền", ["Điều 1. Phạm vi", "Điều 2"], words, system_tokens=7) == 7 + 4 + 6


# ---------- overflow_rate ----------


def test_overflow_rate(nb):
    toks = [1000, 3796, 3797, 5000]
    # 3796 + 300 = 4096 vừa khít, 3797 + 300 tràn
    assert nb.overflow_rate(toks, 300, 4096) == pytest.approx(0.5)
    assert nb.overflow_rate(toks, 0, 4096) == pytest.approx(0.25)
    assert nb.overflow_rate(toks, 300, 32768) == 0.0
    with pytest.raises(ValueError):
        nb.overflow_rate([], 300, 4096)


# ---------- MEMO.md ----------


def test_memo_written():
    doc = ex.read("MEMO.md")
    assert "TODO" not in doc, "còn TODO trong MEMO.md"
    headings = re.findall(r"^## (.+?)\s*$", doc, re.M)
    for s in SECTIONS:
        assert s in headings, f"thiếu mục `## {s}`"
    assert len(doc.split()) >= 600, "memo quá ngắn: cần ít nhất 600 từ"
    assert len(re.findall(r"\d[\d .,]*", doc)) >= 15, "memo phải có số đo, không chỉ nhận xét"
    assert "USD" in doc
    assert "|" in doc, "cần ít nhất một bảng so sánh phương án"

import time
import unicodedata

import pandas as pd
import pytest
from testkit import Exercise

ex = Exercise(__file__)


@pytest.fixture(scope="module")
def bpe():
    return ex.module("bpe.py")


TOY = "low " * 5 + "lower " * 2 + "newest " * 6 + "widest " * 3

VI = [
    "Giảng viên dạy rất nhiệt tình và dễ hiểu.",
    "Phòng học nóng, máy chiếu hay bị hỏng!",
    "Môn học bổ ích nhưng bài tập quá nhiều.",
    "Thầy giảng bài hay, có nhiều ví dụ thực tế.",
    "Cơ sở vật chất của trường còn thiếu thốn.",
] * 20


def test_normalize_nfd_to_nfc(bpe):
    nfd = unicodedata.normalize("NFD", "Tiếng Việt có dấu")
    out = bpe.normalize(nfd)
    assert out == "Tiếng Việt có dấu"
    assert len(out) == 17 and len(nfd) == 24


def test_pretokenize_keeps_text_and_boundaries(bpe):
    text = "Xin chào,  thế giới!\nHà Nội 2024"
    chunks = bpe.pretokenize(text)
    assert chunks == ["Xin", " chào", ",", " ", " thế", " giới", "!", "\n", "Hà", " Nội", " 2024"]
    assert "".join(chunks) == text


def test_pretokenize_normalizes_first(bpe):
    nfd = unicodedata.normalize("NFD", "hoà bình")
    assert bpe.pretokenize(nfd) == ["hoà", " bình"]


def test_train_toy_merges_exact(bpe):
    merges = bpe.train_bpe([TOY], 266)
    assert [tuple(m) for m in merges] == [
        (101, 115), (256, 116), (108, 111), (258, 119), (32, 110),
        (32, 259), (101, 119), (260, 262), (263, 257), (32, 119),
    ], "cặp đầu tiên phải là ('e','s'): hoà với ('s','t') thì chọn (id trái, id phải) nhỏ nhất"


def test_train_respects_vocab_size_and_min_count(bpe):
    assert len(bpe.train_bpe([TOY], 260)) == 4
    # Mọi cặp chỉ xuất hiện 1 lần: không merge nào đủ điều kiện
    assert bpe.train_bpe(["abcdefg"], 300) == []


def test_merges_never_cross_pretokens(bpe):
    merges = bpe.train_bpe(VI, 600)
    for i in range(len(merges)):
        piece = bpe.decode([256 + i], merges)
        assert " " not in piece[1:], f"token {piece!r} chứa dấu cách ở giữa: merge vượt ranh giới pretoken"


def test_encode_applies_merges_by_rank(bpe):
    # (b, c) có thứ hạng 0, (a, b) thứ hạng 1: "abc" → a + bc, không phải ab + c
    merges = [(98, 99), (97, 98)]
    assert bpe.encode("abc", merges) == [97, 256]
    assert bpe.encode("ab", merges) == [257]


def test_encode_toy(bpe):
    merges = bpe.train_bpe([TOY], 266)
    assert bpe.encode("lowest newer", merges) == [259, 257, 263, 101, 114]


@pytest.mark.parametrize(
    "text",
    ["Xin chào thế giới", "hai  dấu cách\tvà tab\n", "emoji 🙂 và 中文", "", "   ", "a_b __init__ 3.14"],
)
def test_roundtrip(bpe, text):
    merges = bpe.train_bpe(VI, 400)
    assert bpe.decode(bpe.encode(text, merges), merges) == text


def test_roundtrip_nfd_gives_nfc(bpe):
    merges = bpe.train_bpe(VI, 400)
    nfd = unicodedata.normalize("NFD", "Giảng viên nhiệt tình")
    ids = bpe.encode(nfd, merges)
    assert ids == bpe.encode("Giảng viên nhiệt tình", merges), "NFD và NFC phải cho cùng id"
    assert bpe.decode(ids, merges) == "Giảng viên nhiệt tình"


def test_decode_invalid_bytes_replaced(bpe):
    # Byte đầu của "ế" (3 byte UTF-8) đứng một mình: không phải UTF-8 hợp lệ
    assert bpe.decode([0xE1], []) == "�"


def test_training_word_becomes_single_token(bpe):
    merges = bpe.train_bpe(VI, 700)
    assert len(bpe.encode(" nhiệt", merges)) == 1
    assert len(bpe.encode("Giảng viên dạy rất nhiệt tình", merges)) == 6


# ---------- Dữ liệu thật: tự skip nếu chưa tải UIT-VSFC ----------

def test_uit_vsfc_compression(bpe):
    root = ex.dataset("uit-vsfc")
    train = pd.read_parquet(root / "default/train/0000.parquet").sentence.tolist()[:3000]
    test = pd.read_parquet(root / "default/test/0000.parquet").sentence.tolist()[:500]
    start = time.perf_counter()
    merges = bpe.train_bpe(train, 600)
    assert time.perf_counter() - start < 20, "train 344 merge trên 3000 câu phải dưới 20 giây"
    assert len(merges) == 344
    ids = [bpe.encode(s, merges) for s in test]
    assert all(bpe.decode(i, merges) == s for i, s in zip(ids, test))
    n_tokens = sum(map(len, ids))
    n_syllables = sum(len(s.split()) for s in test)
    # Lời giải mẫu: 1.468 token mỗi âm tiết (byte thô: khoảng 5.4)
    assert n_tokens / n_syllables == pytest.approx(1.468, abs=0.002)

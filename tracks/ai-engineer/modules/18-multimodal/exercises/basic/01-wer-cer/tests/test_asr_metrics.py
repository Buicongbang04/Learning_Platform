import random
import unicodedata

import jiwer
import pytest

from testkit import Exercise

ex = Exercise(__file__)


@pytest.fixture(scope="module")
def m():
    return ex.module("asr_metrics.py")


def test_normalize_vi(m):
    assert m.normalize_vi("Mặt khác, băng và tuyết là hiện tượng.") == "mặt khác băng và tuyết là hiện tượng"
    assert m.normalize_vi("  ĐÂY   là\n\t“câu”!!  ") == "đây là câu"
    assert m.normalize_vi("giá 60.000 đồng (đã gồm VAT)") == "giá 60 000 đồng đã gồm vat"
    assert m.normalize_vi("hiện-tượng/khác") == "hiện tượng khác"
    nfd = unicodedata.normalize("NFD", "Tiếng Việt")
    assert m.normalize_vi(nfd) == "tiếng việt", "chuỗi NFD phải về NFC trước khi so"


def test_edit_counts_hand(m):
    assert m.edit_counts("a b c d".split(), "a x c d e".split()) == {"S": 1, "D": 0, "I": 1, "N": 4}
    assert m.edit_counts("a b c".split(), []) == {"S": 0, "D": 3, "I": 0, "N": 3}
    assert m.edit_counts([], "x y".split()) == {"S": 0, "D": 0, "I": 2, "N": 0}
    assert m.edit_counts([], []) == {"S": 0, "D": 0, "I": 0, "N": 0}
    assert m.edit_counts("tôi đi học".split(), "tôi học".split()) == {"S": 0, "D": 1, "I": 0, "N": 3}
    assert m.edit_counts(list("abc"), list("abc")) == {"S": 0, "D": 0, "I": 0, "N": 3}


def test_edit_counts_total_is_minimal(m):
    rng = random.Random(0)
    vocab = list("abcde")
    for _ in range(200):
        ref = [rng.choice(vocab) for _ in range(rng.randint(0, 9))]
        hyp = [rng.choice(vocab) for _ in range(rng.randint(0, 9))]
        c = m.edit_counts(ref, hyp)
        if not ref:
            assert c == {"S": 0, "D": 0, "I": len(hyp), "N": 0}
            continue
        o = jiwer.process_words(" ".join(ref), " ".join(hyp))
        assert c["N"] == len(ref)
        assert c["S"] + c["D"] + c["I"] == o.substitutions + o.deletions + o.insertions
        assert len(hyp) == len(ref) - c["D"] + c["I"], "S/D/I phải là một alignment hợp lệ: |hyp| = N - D + I"


def test_wer_is_corpus_level(m):
    refs = ["xin chào", "hôm nay trời rất đẹp và tôi đi dạo"]
    hyps = ["xin chao", "hôm nay trời rất đẹp và tôi đi dạo"]
    # 1 lỗi trên 2 + 9 = 11 từ, không phải trung bình (0.5 + 0) / 2
    assert m.wer(refs, hyps) == pytest.approx(1 / 11)
    assert isinstance(m.wer(refs, hyps), float)


def test_wer_normalizes_both_sides(m):
    assert m.wer(["Xin chào, Việt Nam!"], ["xin chào việt nam"]) == 0.0
    assert m.wer([unicodedata.normalize("NFD", "tiếng việt")], ["Tiếng Việt."]) == 0.0


def test_wer_counts_insertions_above_one(m):
    assert m.wer(["chào"], ["xin chào bạn nhé"]) == pytest.approx(3.0)


def test_wer_cer_match_jiwer(m):
    refs = ["Mặt khác, băng và tuyết là hiện tượng bình thường.", "Đây là cách rất quan trọng để phân biệt.",
            "Giao thông gần như không bị gián đoạn"]
    hyps = ["Mạc khác ban gia tiết là hiện tượng bình thường", "Đây là cách gác quan trọng để phong biệt",
            "Giao thông gần như không bị dáng đỏ thêm"]
    nr, nh = [m.normalize_vi(x) for x in refs], [m.normalize_vi(x) for x in hyps]
    assert m.wer(refs, hyps) == pytest.approx(jiwer.wer(nr, nh))
    assert m.cer(refs, hyps) == pytest.approx(jiwer.cer(nr, nh))


def test_cer_counts_spaces_and_diacritics(m):
    # "ban" so với "bàn": một ký tự sai trên 3; "ab" so với "a b": thêm một khoảng trắng
    assert m.cer(["bàn"], ["ban"]) == pytest.approx(1 / 3)
    assert m.cer(["ab"], ["a b"]) == pytest.approx(1 / 2)
    assert m.cer(["tôi đi"], ["tôiđi"]) == pytest.approx(1 / 6)


def test_rejects_bad_input(m):
    for fn in (m.wer, m.cer):
        with pytest.raises(ValueError):
            fn(["a"], ["a", "b"])
        with pytest.raises(ValueError):
            fn(["", "!!"], ["x", "y"])

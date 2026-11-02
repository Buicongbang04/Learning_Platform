import pytest

from testkit import Exercise

ex = Exercise(__file__)


@pytest.fixture(scope="module")
def nb():
    return ex.notebook("tokens.ipynb")


def utf8(s: str) -> bytes:
    return s.encode("utf-8")


# ---------- detokenize ----------


@pytest.mark.parametrize(
    "raw, expected",
    [
        ("Hôm nay , trời đẹp .", "Hôm nay, trời đẹp."),
        ("Bạn có khoẻ không ? Tôi khoẻ !", "Bạn có khoẻ không? Tôi khoẻ!"),
        ("Tỉ lệ là 45 % ; còn lại : 55 %", "Tỉ lệ là 45%; còn lại: 55%"),
        ("Giá ( ước tính ) là $ 20 .", "Giá (ước tính) là $20."),
        ("Xem [ 1 ] và &#91; 2 &#93; .", "Xem [1] và [2]."),
        ("I can &apos;t believe it &apos;s here .", "I can't believe it's here."),
        ("We &apos;re sure they &apos;ve gone , I &apos;m told .", "We're sure they've gone, I'm told."),
        ("Cụm từ &apos; tự do &apos; nghĩa là gì ?", "Cụm từ ' tự do ' nghĩa là gì?"),
        ("Bài hát &quot; Hà Nội &quot; rất hay .", 'Bài hát " Hà Nội " rất hay.'),
        ("Tom &amp; Jerry", "Tom & Jerry"),
        ("  nhiều    khoảng\ttrắng  ", "nhiều khoảng trắng"),
        ("", ""),
    ],
)
def test_detokenize(nb, raw, expected):
    assert nb.detokenize(raw) == expected


# ---------- token_stats, token_tax ----------


def test_token_stats_bytes(nb):
    texts = ["tôi đi học", "ok"]
    s = nb.token_stats(texts, utf8)
    # "tôi đi học": 10 ký tự, 14 byte (ô, đ 2 byte; ọ 3 byte); "ok": 2 ký tự, 2 byte
    assert s["n_texts"] == 2
    assert s["n_chars"] == 12
    assert s["n_words"] == 4
    assert s["n_tokens"] == 16
    assert s["tokens_per_word"] == pytest.approx(16 / 4)
    assert s["chars_per_token"] == pytest.approx(12 / 16)


def test_token_stats_uses_encode_not_words(nb):
    fixed = lambda s: [0] * 7  # noqa: E731  mọi văn bản là 7 token
    s = nb.token_stats(["một hai ba", "bốn"], fixed)
    assert (s["n_tokens"], s["n_words"]) == (14, 4)
    assert s["tokens_per_word"] == pytest.approx(3.5)


def test_token_stats_empty(nb):
    s = nb.token_stats([], utf8)
    assert s == {"n_texts": 0, "n_chars": 0, "n_words": 0, "n_tokens": 0,
                 "tokens_per_word": 0.0, "chars_per_token": 0.0}
    s = nb.token_stats(["", "  "], utf8)
    assert s["n_words"] == 0 and s["tokens_per_word"] == 0.0 and s["chars_per_token"] == pytest.approx(1.0)


def test_token_tax(nb):
    en = ["I go to school", "ok"]
    vi = ["tôi đi học", "được"]
    # byte: en 14 + 2 = 16, vi 14 + 8 = 22
    assert nb.token_tax(en, vi, utf8) == pytest.approx(22 / 16)
    assert nb.token_tax(vi, en, utf8) == pytest.approx(16 / 22)
    # tỉ lệ của TỔNG, không phải trung bình tỉ lệ từng cặp ((14/14 + 8/2) / 2 = 2.5)
    assert nb.token_tax(en, vi, utf8) != pytest.approx((14 / 14 + 8 / 2) / 2)


def test_token_tax_errors(nb):
    with pytest.raises(ValueError):
        nb.token_tax(["a", "b"], ["c"], utf8)
    with pytest.raises(ValueError):
        nb.token_tax(["", ""], ["c", "d"], utf8)


# ---------- ngân sách context ----------


def test_fits_in_context(nb):
    assert nb.fits_in_context(3000, 1096, 4096)
    assert not nb.fits_in_context(3000, 1097, 4096)
    assert nb.fits_in_context(0, 0, 0)


def test_truncate_to_budget_stops_at_first_overflow(nb):
    texts = ["aaaa", "bbbbbb", "cc", "d"]  # 4, 6, 2, 1 byte
    assert nb.truncate_to_budget(texts, utf8, 10) == ["aaaa", "bbbbbb"]  # đúng bằng ngân sách
    # 4 + 6 > 9: dừng ở "bbbbbb", KHÔNG nhảy qua để lấy "cc", "d"
    assert nb.truncate_to_budget(texts, utf8, 9) == ["aaaa"]
    assert nb.truncate_to_budget(texts, utf8, 3) == []
    assert nb.truncate_to_budget(texts, utf8, 100) == texts
    assert nb.truncate_to_budget([], utf8, 5) == []


def test_truncate_to_budget_counts_with_encode(nb):
    texts = ["đường", "xe"]  # "đường": 5 ký tự nhưng 9 byte
    assert nb.truncate_to_budget(texts, utf8, 9) == ["đường"]
    assert nb.truncate_to_budget(texts, list, 7) == ["đường", "xe"]


# ---------- dữ liệu thật ----------


def test_real_iwslt_counts():
    """1 268 cặp tst2013 sau detokenize: số ký tự, byte, từ khớp bảng ở mục 5 lý thuyết. Tự skip nếu chưa tải."""
    root = ex.dataset("iwslt15-en-vi")
    nb = ex.notebook("tokens.ipynb")
    en = [nb.detokenize(s) for s in (root / "tst2013.en").read_text(encoding="utf-8").splitlines()]
    vi = [nb.detokenize(s) for s in (root / "tst2013.vi").read_text(encoding="utf-8").splitlines()]
    assert len(en) == len(vi) == 1268
    s_en, s_vi = nb.token_stats(en, utf8), nb.token_stats(vi, utf8)
    assert (s_en["n_chars"], s_vi["n_chars"]) == (123_769, 133_496)
    assert (s_en["n_tokens"], s_vi["n_tokens"]) == (123_800, 178_601)
    assert (s_en["n_words"], s_vi["n_words"]) == (23_093, 30_809)
    assert nb.token_tax(en, vi, utf8) == pytest.approx(1.443, abs=1e-3)

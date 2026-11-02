import hashlib
import unicodedata

import numpy as np
import pytest

from testkit import Exercise

ex = Exercise(__file__)


@pytest.fixture(scope="module")
def nb():
    return ex.notebook("instruction_data.ipynb")


def test_normalize_text(nb):
    nfd = unicodedata.normalize("NFD", "Luật  Đất\tđai")
    assert nb.normalize_text(nfd) == "Luật Đất đai"
    assert nb.normalize_text("  a\r\nb\rc  ") == "a\nb\nc"
    assert nb.normalize_text("x  y \t z") == "x y z"
    assert nb.normalize_text("đoạn 1\n\n\n\n  đoạn 2  \n") == "đoạn 1\n\nđoạn 2"
    assert nb.normalize_text("dòng 1\n\ndòng 2") == "dòng 1\n\ndòng 2"
    assert nb.normalize_text("   ") == ""


def test_to_messages(nb):
    row = {"instruction": "Bạn là một trợ lý AI.", "input": "Câu hỏi:  2+2? ", "output": "4\r\n"}
    assert nb.to_messages(row) == [
        {"role": "system", "content": "Bạn là một trợ lý AI."},
        {"role": "user", "content": "Câu hỏi: 2+2?"},
        {"role": "assistant", "content": "4"},
    ]
    for bad in ['"', "  ", "...!!!...!!!", "Trả lời"]:
        out = nb.to_messages({"instruction": bad, "input": "hỏi", "output": "đáp"})
        assert [m["role"] for m in out] == ["user", "assistant"], f"system prompt {bad!r} phải bị bỏ"
    nfd = unicodedata.normalize("NFD", "Bạn là trợ lý tiếng Việt")
    assert nb.to_messages({"instruction": nfd, "input": "a", "output": "b"})[0]["content"] == "Bạn là trợ lý tiếng Việt"


def test_dedup_key(nb):
    a = [{"role": "system", "content": "S1"}, {"role": "user", "content": "Thủ đô?"},
         {"role": "assistant", "content": "Hà Nội"}]
    b = [{"role": "system", "content": "S2 khác"}, {"role": "user", "content": "thủ  đô?"},
         {"role": "assistant", "content": "hà\nnội"}]
    c = [{"role": "user", "content": "Thủ đô?"}, {"role": "assistant", "content": "Huế"}]
    assert nb.dedup_key(a) == nb.dedup_key(b), "khác system, khác hoa thường và khoảng trắng: vẫn trùng"
    assert nb.dedup_key(a) != nb.dedup_key(c)
    assert nb.dedup_key([{"role": "user", "content": "A"}, {"role": "assistant", "content": "B"}]) == \
        hashlib.sha1("a\x1fb".encode()).hexdigest()
    swapped = [{"role": "user", "content": "Hà Nội"}, {"role": "assistant", "content": "Thủ đô?"}]
    assert nb.dedup_key(swapped) != nb.dedup_key(a)


def test_exact_dedup(nb):
    assert nb.exact_dedup(["x", "y", "x", "z", "y", "w"]) == [0, 1, 3, 5]
    assert nb.exact_dedup([]) == []


def reference_minhash(text, num_perm=64, ngram=5, seed=0):
    p = 2**31 - 1
    
    text = " ".join(text.lower().split())
    shingles = {text} if len(text) <= ngram else {text[i: i + ngram] for i in range(len(text) - ngram + 1)}
    rng = np.random.default_rng(seed)
    a = rng.integers(1, p, num_perm, dtype=np.uint64)
    b = rng.integers(0, p, num_perm, dtype=np.uint64)
    hashes = [int.from_bytes(hashlib.blake2b(s.encode(), digest_size=8).digest(), "little") % p for s in shingles]
    return np.array([min((int(a[k]) * h + int(b[k])) % p for h in hashes) for k in range(num_perm)], dtype=np.uint64)


def test_minhash_signature_exact(nb):
    text = "Quá trình phân chia hạt nhân gọi là gì? Nguyên phân."
    sig = nb.minhash_signature(text)
    assert sig.dtype == np.uint64 and sig.shape == (64,)
    assert np.array_equal(sig, reference_minhash(text))
    assert np.array_equal(nb.minhash_signature(text, num_perm=16, ngram=3, seed=7),
                          reference_minhash(text, 16, 3, 7))
    assert np.array_equal(nb.minhash_signature("ab"), reference_minhash("ab")), "văn bản ngắn: cả văn bản là một shingle"
    assert np.array_equal(nb.minhash_signature("  QUÁ trình\n\nphân  chia "), nb.minhash_signature("quá trình phân chia"))


def test_minhash_estimates_jaccard(nb):
    rng = np.random.default_rng(1)
    words = [f"từ{k}" for k in rng.integers(0, 10_000, 400)]
    a = " ".join(words)
    b = " ".join(words[:300] + [f"khác{k}" for k in range(100)])

    def shingles(t):
        return {t[i: i + 5] for i in range(len(t) - 4)}

    true_j = len(shingles(a) & shingles(b)) / len(shingles(a) | shingles(b))
    sa, sb = nb.minhash_signature(a, num_perm=256), nb.minhash_signature(b, num_perm=256)
    assert abs(np.mean(sa == sb) - true_j) < 0.08


def test_near_duplicate_groups(nb):
    base = np.arange(16, dtype=np.uint64) * 1000
    b = base.copy()
    b[[13, 15]] += 1
    c = base.copy()
    c[[0, 1, 2, 3, 8, 9, 10, 11]] += 7
    d = b.copy()
    e = np.arange(16, dtype=np.uint64) + 5
    f = e.copy()
    f[0] += 1
    sigs = np.stack([e, base, b, c, d, f])
    groups = nb.near_duplicate_groups(sigs, bands=4, threshold=0.8)
    assert groups.tolist() == [0, 1, 1, 3, 1, 0], (
        "b khớp base 14/16 thì cùng nhóm; c trùng một band nhưng chỉ khớp 8/16 thì không; "
        "d nối bắc cầu qua b; mã nhóm là chỉ số nhỏ nhất")
    assert nb.near_duplicate_groups(sigs, bands=4, threshold=1.0).tolist() == [0, 1, 2, 3, 2, 5]


def test_group_split(nb):
    groups = [f"g{k % 4000}" for k in range(12_000)]
    is_val = nb.group_split(groups, 0.05, seed=0)
    assert is_val.dtype == bool and is_val.shape == (12_000,)
    by_group = {}
    for g, v in zip(groups, is_val):
        assert by_group.setdefault(g, v) == v, "cùng nhóm phải cùng phía"
    assert 0.04 < np.mean(list(by_group.values())) < 0.06
    expected = int.from_bytes(hashlib.sha1(b"0:g17").digest()[:8], "big") / 2**64 < 0.05
    assert bool(is_val[17]) == expected
    shuffled = groups[::-1]
    assert np.array_equal(nb.group_split(shuffled, 0.05, seed=0), is_val[::-1]), "không phụ thuộc thứ tự mẫu"
    assert not np.array_equal(nb.group_split(groups, 0.05, seed=1), is_val)
    assert nb.group_split([3, 3, 3], 1.0).all() and not nb.group_split([3, 3, 3], 0.0).any()


def test_contamination(nb):
    train = ["một hai ba bốn năm sáu bảy", "tám chín mười"]
    evals = ["Một hai ba bốn năm, khác hẳn", "hai ba bốn năm sáu bảy tám", "ngắn", "tám chín mười một"]
    out = nb.contamination(train, evals, n=3)
    assert out.shape == (4,)
    assert out[0] == pytest.approx(3 / 5)
    assert out[1] == pytest.approx(4 / 5), "n-gram phải nằm trong cùng một văn bản train, không nối qua văn bản"
    assert out[2] == 0.0
    assert out[3] == pytest.approx(1 / 2)
    nfd = unicodedata.normalize("NFD", "Luật đất đai năm nay")
    assert nb.contamination(["luật đất đai năm nay"], [nfd], n=2)[0] == 1.0

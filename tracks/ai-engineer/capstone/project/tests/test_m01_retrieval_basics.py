"""M01: chuẩn hoá, tokenizer, đọc dữ liệu, BM25, thước đo retrieval."""

import math
import unicodedata

import numpy as np
import pytest

from testkit import Exercise


def test_normalize_nfc_whitespace_lines(la):
    text = la("text")
    raw = unicodedata.normalize("NFD", "Điều 2.  Xử phạt\t người nuôi ong \n\n  1. Phạt   tiền\n   \n")
    out = text.normalize(raw)
    assert out == "Điều 2. Xử phạt người nuôi ong\n1. Phạt tiền"
    assert unicodedata.is_normalized("NFC", out)


def test_tokenize_syllables_and_bigrams(la):
    text = la("text")
    nfd = unicodedata.normalize("NFD", "Giấy phép lái xe, 100/2019/NĐ-CP!")
    assert text.tokenize(nfd) == ["giấy", "phép", "lái", "xe", "100", "2019", "nđ", "cp"]
    assert text.tokenize("Giấy phép lái xe", bigrams=True) == [
        "giấy", "phép", "lái", "xe", "giấy_phép", "phép_lái", "lái_xe",
    ]
    assert text.tokenize("Phạt", bigrams=True) == ["phạt"]
    assert text.tokenize("  ") == []


def test_split_uid(la):
    text = la("text")
    assert text.split_uid("100/2019/nđ-cp+5") == ("100/2019/nđ-cp", 5)
    assert text.split_uid("a+b+12") == ("a+b", 12)
    for bad in ["100/2019/nđ-cp", "100/2019/nđ-cp+", "x+5a"]:
        with pytest.raises(ValueError):
            text.split_uid(bad)


def test_load_corpus(la, mini):
    data = la("data")
    corpus = data.load_corpus(mini)
    assert len(corpus) == 8
    assert corpus[0].uid == "901/2099/nđ-cp+1" and corpus[0].title.startswith("Điều 1.")
    assert corpus[-1].uid == "77/2098/tt-bxd+4" and corpus[-1].text == ""


def test_load_questions_order_and_grouping(la, mini):
    data = la("data")
    qs = data.load_questions(mini, "test")
    assert [q.qid for q in qs] == ["q2", "q1", "q3"]
    assert qs[1].text.startswith("Nuôi ong mật")
    assert qs[1].relevant == {"901/2099/nđ-cp+2"}
    assert qs[2].relevant == {"77/2098/tt-bxd+3", "901/2099/nđ-cp+3"}
    assert [q.qid for q in data.load_questions(mini, "test", 2)] == ["q2", "q1"]
    assert [q.qid for q in data.load_questions(mini, "train")] == ["q4", "q5"]


def test_bm25_matches_formula(la):
    bm25 = la("bm25")
    docs = [["ong", "mật", "ong"], ["nhà", "chòi"], ["ong", "nhà", "chòi", "cây", "cao"]]
    index = bm25.BM25(docs, k1=1.5, b=0.75)
    avgdl = 10 / 3
    idf_ong = math.log(1 + (3 - 2 + 0.5) / (2 + 0.5))
    expected0 = idf_ong * 2 * 2.5 / (2 + 1.5 * (1 - 0.75 + 0.75 * 3 / avgdl))
    expected2 = idf_ong * 1 * 2.5 / (1 + 1.5 * (1 - 0.75 + 0.75 * 5 / avgdl))
    s = index.scores(["ong"])
    assert s.shape == (3,)
    np.testing.assert_allclose(s, [expected0, 0.0, expected2], rtol=1e-9)
    np.testing.assert_allclose(index.scores(["ong", "ong"]), 2 * s, rtol=1e-9)
    assert index.scores(["không_có"]).tolist() == [0.0, 0.0, 0.0]


def test_bm25_top_k_order_and_ties(la):
    bm25 = la("bm25")
    index = bm25.BM25([["a"], ["b"], ["a"], ["c"]])
    assert index.top_k(["a"], 3) == [0, 2, 1]
    assert index.top_k(["b", "a"], 2) == [1, 0]
    assert index.top_k(["z"], 2) == [0, 1]


def test_bm25_end_to_end_on_fixture(la, mini):
    data, text, bm25, metrics = la("data"), la("text"), la("bm25"), la("metrics")
    corpus = data.load_corpus(mini)
    index = bm25.BM25([text.tokenize(text.normalize(a.title + "\n" + a.text)) for a in corpus])
    qs = data.load_questions(mini, "test")
    ids = [a.uid for a in corpus]
    ret = [[ids[i] for i in index.top_k(text.tokenize(q.text), 3)] for q in qs]
    assert ret[0][0] == "77/2098/tt-bxd+2"
    assert ret[1][0] == "901/2099/nđ-cp+2"
    assert metrics.recall_at_k(ret, [set(q.relevant) for q in qs], 3) == pytest.approx(1.0)


def test_metrics_hand_example(la):
    metrics = la("metrics")
    ret = [["C", "A", "D", "B", "E"]]
    rel = [{"A", "B"}]
    assert metrics.recall_at_k(ret, rel, 3) == pytest.approx(0.5)
    assert metrics.recall_at_k(ret, rel, 5) == pytest.approx(1.0)
    assert metrics.mrr_at_k(ret, rel, 5) == pytest.approx(0.5)
    assert metrics.mrr_at_k(ret, rel, 1) == pytest.approx(0.0)
    assert metrics.ndcg_at_k(ret, rel, 5) == pytest.approx(0.6509, abs=1e-4)
    two = [["A", "X"], ["Y", "Z"]]
    assert metrics.recall_at_k(two, [{"A"}, {"Z"}], 1) == pytest.approx(0.5)
    assert metrics.mrr_at_k(two, [{"A"}, {"Z"}], 2) == pytest.approx(0.75)
    assert metrics.ndcg_at_k([["A"]], [{"A", "B", "C"}], 1) == pytest.approx(1.0)


def test_metrics_reject_bad_input(la):
    metrics = la("metrics")
    for fn in (metrics.recall_at_k, metrics.mrr_at_k, metrics.ndcg_at_k):
        with pytest.raises(ValueError):
            fn([["A"]], [{"A"}], 0)
        with pytest.raises(ValueError):
            fn([["A"], ["B"]], [{"A"}], 1)
        with pytest.raises(ValueError):
            fn([], [], 1)
        with pytest.raises(ValueError):
            fn([["A"]], [set()], 1)


def test_first_hit_rank(la):
    metrics = la("metrics")
    assert metrics.first_hit_rank(["C", "A", "B"], {"A", "B"}) == 2
    assert metrics.first_hit_rank(["C"], {"A"}) is None
    assert metrics.first_hit_rank([], {"A"}) is None


def test_pinned_set_on_real_data(la):
    root = Exercise.dataset("zalo-legal")
    data = la("data")
    pinned = data.load_questions(root, "test", 300)
    assert len(pinned) == 300
    assert sum(len(q.relevant) for q in pinned) == 301
    assert len({u.rsplit("+", 1)[0] for q in pinned for u in q.relevant}) == 144
    assert len(data.load_questions(root, "train")) == 2432

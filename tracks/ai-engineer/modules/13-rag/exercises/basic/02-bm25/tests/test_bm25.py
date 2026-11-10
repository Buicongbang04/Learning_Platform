import json
import math
import unicodedata

import numpy as np
import pytest

from testkit import Exercise

ex = Exercise(__file__)

# Corpus 3 tài liệu để tính tay. N = 3, độ dài 5, 10, 7, avgdl = 22/3.
DOCS = [
    "phạt tiền người lái xe",
    "xe ô tô chở hàng quá tải xe bị phạt",
    "cấp giấy phép xây dựng nhà ở",
]
AVGDL = 22 / 3


@pytest.fixture(scope="module")
def bm():
    return ex.module("bm25.py")


@pytest.fixture(scope="module")
def corpus():
    # DOCS đã là chữ thường, NFC, không dấu câu: tách bằng split() là đủ, test BM25 không phụ thuộc tokenize_vi
    docs = [d.split() for d in DOCS]
    assert [len(d) for d in docs] == [5, 10, 7]
    return docs


# ---------- tokenize_vi ----------


def test_tokenize_lower_and_strip_punctuation(bm):
    text = "Theo Điều 21, Nghị định 100/2019/NĐ-CP: phạt (tiền)!"
    assert bm.tokenize_vi(text) == ["theo", "điều", "21", "nghị", "định", "100", "2019", "nđ", "cp", "phạt", "tiền"]
    assert bm.tokenize_vi("  giấy\tphép\nlái   xe ") == ["giấy", "phép", "lái", "xe"]
    assert bm.tokenize_vi("...") == []


def test_tokenize_nfd_equals_nfc(bm):
    nfd = unicodedata.normalize("NFD", "luật Đất đai")
    assert nfd != "luật Đất đai"
    assert bm.tokenize_vi("Luật đất đai") == ["luật", "đất", "đai"]
    assert bm.tokenize_vi(nfd) == ["luật", "đất", "đai"]
    assert all(unicodedata.is_normalized("NFC", t) for t in bm.tokenize_vi(nfd))


# ---------- BM25 ----------


def test_scores_match_hand_computation(bm, corpus):
    model = bm.BM25(corpus)
    s = model.scores(["phạt", "xe"])
    assert isinstance(s, np.ndarray) and s.shape == (3,)
    # "phạt" và "xe" đều có trong 2/3 tài liệu: IDF = ln(1 + (3 - 2 + 0.5) / (2 + 0.5)) = ln(1.6)
    idf = math.log(1.6)
    norm0 = 1.5 * (1 - 0.75 + 0.75 * 5 / AVGDL)  # 1.14205
    norm1 = 1.5 * (1 - 0.75 + 0.75 * 10 / AVGDL)  # 1.90909
    d0 = idf * 1 * 2.5 / (1 + norm0) + idf * 1 * 2.5 / (1 + norm0)  # phạt (f=1) + xe (f=1)
    d1 = idf * 1 * 2.5 / (1 + norm1) + idf * 2 * 2.5 / (2 + norm1)  # phạt (f=1) + xe (f=2)
    assert s[0] == pytest.approx(d0, abs=1e-9)  # 1.0970907
    assert s[1] == pytest.approx(d1, abs=1e-9)  # 1.0050768
    assert s[2] == 0.0  # không chứa từ nào của câu hỏi


def test_rare_term_gets_higher_idf(bm, corpus):
    s = bm.BM25(corpus).scores(["lái"])
    # "lái" chỉ có trong 1/3 tài liệu: IDF = ln(1 + 2.5 / 1.5)
    norm0 = 1.5 * (1 - 0.75 + 0.75 * 5 / AVGDL)
    assert s[0] == pytest.approx(math.log(1 + 2.5 / 1.5) * 2.5 / (1 + norm0), abs=1e-9)  # 1.4045
    assert s[1] == 0.0 and s[2] == 0.0


def test_idf_positive_for_term_in_every_doc(bm):
    # dạng Lucene có "1 +": term có ở mọi tài liệu vẫn có IDF dương ln(1 + 0.5 / 3.5), không âm
    docs = [["xe", "máy"], ["xe", "đạp"], ["xe", "buýt"]]
    s = bm.BM25(docs).scores(["xe"])
    norm = 1.5 * (1 - 0.75 + 0.75 * 2 / 2)
    assert s == pytest.approx(np.full(3, math.log(8 / 7) * 2.5 / (1 + norm)), abs=1e-9)
    assert (s > 0).all()


def test_k1_and_b_are_used(bm, corpus):
    s = bm.BM25(corpus, k1=1.2, b=0.5).scores(["phạt", "xe"])
    idf = math.log(1.6)
    norm0 = 1.2 * (1 - 0.5 + 0.5 * 5 / AVGDL)
    norm1 = 1.2 * (1 - 0.5 + 0.5 * 10 / AVGDL)
    assert s[0] == pytest.approx(2 * idf * 2.2 / (1 + norm0), abs=1e-9)  # 1.0293292
    assert s[1] == pytest.approx(idf * 2.2 / (1 + norm1) + idf * 2 * 2.2 / (2 + norm1), abs=1e-9)  # 1.0326020


def test_b_zero_ignores_length(bm):
    docs = [["phạt", "xe"], ["phạt", "xe", "ô", "tô", "tải", "hàng", "quá", "khổ"], ["cấp", "phép"]]
    with_len = bm.BM25(docs).scores(["phạt"])
    no_len = bm.BM25(docs, b=0).scores(["phạt"])
    assert with_len[0] > with_len[1]  # b = 0.75: tài liệu dài bị phạt
    assert no_len[0] == pytest.approx(no_len[1], abs=1e-12)  # b = 0: chỉ còn tần suất
    # b = 0: f (k1 + 1) / (f + k1) với f = 1 cho đúng 1, điểm bằng IDF
    assert no_len[0] == pytest.approx(math.log(1 + 1.5 / 2.5), abs=1e-9)


def test_term_frequency_saturates(bm):
    docs = [["phạt"] * f + ["x"] * (10 - f) for f in (1, 2, 5, 10)] + [["khác"] * 10]
    s = bm.BM25(docs, b=0).scores(["phạt"])[:4]
    idf = math.log(1 + 1.5 / 4.5)
    assert s == pytest.approx([idf * f * 2.5 / (f + 1.5) for f in (1, 2, 5, 10)], abs=1e-9)
    assert s[3] < idf * 2.5  # không vượt IDF (k1 + 1)


def test_repeated_and_unknown_query_terms(bm, corpus):
    model = bm.BM25(corpus)
    once = model.scores(["lái"])
    # term lặp trong câu hỏi được cộng mỗi lần; term không có trong corpus đóng góp 0
    assert model.scores(["lái", "lái"]) == pytest.approx(2 * once, abs=1e-12)
    assert model.scores(["lái", "phà"]) == pytest.approx(once, abs=1e-12)
    assert (model.scores(["phà"]) == 0).all()
    assert (model.scores([]) == 0).all()


def test_nfd_query_matches_nfc_document(bm, corpus):
    model = bm.BM25(corpus)
    nfc = model.scores(bm.tokenize_vi("Phạt lái xe"))
    nfd = model.scores(bm.tokenize_vi(unicodedata.normalize("NFD", "Phạt lái xe")))
    assert nfc[0] > 0
    assert nfd == pytest.approx(nfc, abs=1e-12)


def test_top_k(bm, corpus):
    assert bm.BM25(corpus).top_k(["phạt", "xe"], 2) == [0, 1]
    # đổi k1, b thì thứ hạng đổi theo: 1.0326 > 1.0293
    assert bm.BM25(corpus, k1=1.2, b=0.5).top_k(["phạt", "xe"], 2) == [1, 0]
    top = bm.BM25(corpus).top_k(["giấy", "phép"], 5)  # k lớn hơn số tài liệu: trả đủ 3
    assert top[0] == 2 and sorted(top) == [0, 1, 2]
    assert all(isinstance(i, int) for i in top)


def test_top_k_ties_keep_lower_index_first(bm):
    docs = [["a", "b"], ["c", "d"], ["a", "b"], ["a", "b"]]
    assert bm.BM25(docs).top_k(["a"], 3) == [0, 2, 3]


def test_real_zalo_slice_matches_theory(bm):
    """Lát cắt của phần lý thuyết: 100 câu hỏi đầu qrels/test, các điều thuộc 60 văn bản chứa đáp án.

    Bảng tokenizer ở mục 3 lý thuyết: âm tiết, k1 = 1.5, b = 0.75 cho R@1 0.540, R@10 0.930, MRR@10 0.686
    (chính xác 0.68611).
    Tự skip nếu chưa tải dữ liệu.
    """
    root = ex.dataset("zalo-legal")
    with (root / "qrels" / "test.jsonl").open(encoding="utf-8") as f:
        qrels = [json.loads(line) for line in f]
    relevant: dict[str, set[str]] = {}
    for r in qrels:
        if r["query-id"] in relevant or len(relevant) < 100:
            relevant.setdefault(r["query-id"], set()).add(r["corpus-id"])
    laws = {cid.rsplit("+", 1)[0] for ids in relevant.values() for cid in ids}
    ids, docs = [], []
    with (root / "corpus.jsonl").open(encoding="utf-8") as f:
        for line in f:
            d = json.loads(line)
            if d["_id"].rsplit("+", 1)[0] in laws:
                ids.append(d["_id"])
                docs.append(bm.tokenize_vi(d["title"] + " " + d["text"]))
    with (root / "queries.jsonl").open(encoding="utf-8") as f:
        queries = {q["_id"]: q["text"] for q in map(json.loads, f) if q["_id"] in relevant}
    assert (len(relevant), len(laws), len(docs)) == (100, 60, 3541)

    model = bm.BM25(docs)
    r1 = r10 = mrr = 0.0
    for qid, rel in relevant.items():
        top = [ids[i] for i in model.top_k(bm.tokenize_vi(queries[qid]), 10)]
        r1 += len(rel & set(top[:1])) / len(rel)
        r10 += len(rel & set(top)) / len(rel)
        mrr += next((1 / rank for rank, d in enumerate(top, start=1) if d in rel), 0.0)
    assert r1 / 100 == pytest.approx(0.540, abs=1e-9)
    assert r10 / 100 == pytest.approx(0.930, abs=1e-9)
    assert mrr / 100 == pytest.approx(0.6861, abs=1e-3)

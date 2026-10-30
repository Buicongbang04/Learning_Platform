import unicodedata

import numpy as np
import pytest
import torch
import torch.nn.functional as F
from testkit import Exercise

ex = Exercise(__file__)
torch.set_num_threads(1)


@pytest.fixture(scope="module")
def nb():
    return ex.notebook("word2vec_wiki.ipynb")


def test_tokenize(nb):
    text = unicodedata.normalize("NFD", "Hà Nội là thủ đô.\nNăm 1010, Lý Thái Tổ dời đô! A. Ok_ok vậy")
    assert nb.tokenize(text) == [
        ["hà", "nội", "là", "thủ", "đô"],
        ["năm", "lý", "thái", "tổ", "dời", "đô"],
        ["ok", "ok", "vậy"],
    ], "NFC + lower, cắt câu theo .!?;: và xuống dòng, chỉ lấy chữ cái, bỏ câu < 2 âm tiết"


def test_find_phrases(nb):
    sents = [["hà", "nội", "đẹp"]] * 6 + [["hà", "giang", "xa"]] * 2 + [["đẹp", "và", "xa"]] * 4 + [["nội", "và"]]
    # N = 38; count(hà nội) = 6, count(hà) = 8, count(nội) = 7: score = 6 * 38 / 56 = 4.07
    # (và, xa) có score 5.07 nhưng count = 4 < min_count
    assert nb.find_phrases(sents, min_count=5, delta=0, threshold=3.0) == {("hà", "nội"), ("nội", "đẹp")}
    assert nb.find_phrases(sents, min_count=5, delta=0, threshold=4.0) == {("hà", "nội")}
    assert nb.find_phrases(sents, min_count=5, delta=0, threshold=4.1) == set()
    # delta trừ vào count(ab): (6 - 3) * 38 / 56 = 2.04
    assert nb.find_phrases(sents, min_count=5, delta=3, threshold=2.0) == {("hà", "nội")}
    assert nb.find_phrases(sents, min_count=5, delta=3, threshold=2.04) == set()
    # không đếm cặp vượt ranh giới câu: "đẹp" cuối câu và "hà" đầu câu sau không thành cặp
    assert ("đẹp", "hà") not in nb.find_phrases(sents, min_count=1, delta=0, threshold=0.0)
    assert nb.find_phrases(sents, min_count=7, delta=0, threshold=0.0) == set(), "giữ cặp có count >= min_count"
    assert nb.find_phrases(sents, min_count=6, delta=0, threshold=3.0) == {("hà", "nội"), ("nội", "đẹp")}, \
        "count(ab) = min_count vẫn được giữ"


def test_apply_phrases(nb):
    phrases = {("hà", "nội"), ("nội", "thành"), ("thủ", "đô")}
    assert nb.apply_phrases(["hà", "nội", "thành", "thủ", "đô"], phrases) == ["hà_nội", "thành", "thủ_đô"]
    assert nb.apply_phrases(["nội", "thành", "hà"], phrases) == ["nội_thành", "hà"]
    assert nb.apply_phrases([], phrases) == []


def test_build_vocab_and_flatten(nb):
    sents = [["b", "a", "c"], ["a", "b", "x"], ["a", "c", "c"]]
    words, counts = nb.build_vocab(sents, min_count=2)
    assert words == ["a", "c", "b"] and counts.tolist() == [3, 3, 2] and counts.dtype == np.int64
    ids, sent_ids = nb.flatten(sents, {w: i for i, w in enumerate(words)})
    assert ids.tolist() == [2, 0, 1, 0, 2, 0, 1, 1]
    assert sent_ids.tolist() == [0, 0, 0, 1, 1, 2, 2, 2]


def test_keep_probs(nb):
    p = nb.keep_probs(np.array([5000, 300, 100, 1]), t=1e-3)
    np.testing.assert_allclose(p, [0.033947, 0.152180, 0.286411, 1.0], atol=1e-6)


def test_make_pairs_full_window_no_subsampling(nb):
    # keep = 1 và window = 1: b luôn bằng 1, ra đúng mọi cặp kề nhau trong cùng câu
    ids = np.array([5, 6, 7, 8, 9])
    sent_ids = np.array([0, 0, 0, 1, 1])
    pairs = nb.make_pairs(ids, sent_ids, 1, np.ones(10), np.random.default_rng(0))
    assert pairs.shape[1] == 2 and pairs.dtype == np.int64
    assert sorted(map(tuple, pairs.tolist())) == [(5, 6), (6, 5), (6, 7), (7, 6), (8, 9), (9, 8)], \
        "không ghép qua ranh giới câu (7, 8)"


def test_make_pairs_dynamic_window_and_subsampling(nb):
    rng = np.random.default_rng(0)
    n = 20000
    ids = rng.integers(0, 50, n)
    sent_ids = np.arange(n) // 25
    keep = np.ones(50)
    pairs = nb.make_pairs(ids, sent_ids, 4, keep, np.random.default_rng(1))
    # không subsample, cửa sổ động đều 1..4: mỗi center trung bình (1+2+3+4)/4 = 2.5 cặp mỗi phía
    assert len(pairs) / n == pytest.approx(2 * 2.5 * (1 - 0.1), rel=0.05)
    keep_half = np.full(50, 0.5)
    half = nb.make_pairs(ids, sent_ids, 4, keep_half, np.random.default_rng(1))
    # giữ một nửa token: câu ngắn đi một nửa nên tỉ lệ cặp hơi dưới 0.5 (lời giải mẫu: 0.457)
    assert 0.40 < len(half) / len(pairs) < 0.52, "subsample phải giữ khoảng một nửa token"
    a = nb.make_pairs(ids, sent_ids, 4, keep_half, np.random.default_rng(3))
    b = nb.make_pairs(ids, sent_ids, 4, keep_half, np.random.default_rng(3))
    assert np.array_equal(a, b), "mọi số ngẫu nhiên phải lấy từ rng"


def test_make_pairs_distance_bounded(nb):
    ids = np.arange(40)                    # id = vị trí: khoảng cách cặp đọc được trực tiếp
    sent_ids = np.zeros(40, dtype=np.int64)
    pairs = nb.make_pairs(ids, sent_ids, 3, np.ones(40), np.random.default_rng(2))
    dist = np.abs(pairs[:, 0] - pairs[:, 1])
    assert dist.min() >= 1 and dist.max() <= 3
    assert {1, 2, 3} <= set(dist.tolist())


def test_sgns_init_and_loss(nb):
    torch.manual_seed(0)
    model = nb.SGNS(30, 8)
    w = model.in_emb.weight
    assert w.shape == (30, 8) and model.out_emb.weight.abs().sum().item() == 0
    assert w.abs().max().item() <= 0.5 / 8 and w.std().item() > 0.01
    with torch.no_grad():
        model.out_emb.weight.normal_()
        model.in_emb.weight.normal_()
    c = torch.tensor([0, 3, 3])
    o = torch.tensor([1, 2, 5])
    neg = torch.tensor([[4, 6], [7, 7], [0, 9]])
    v = model.in_emb.weight[c]
    ref = -(F.logsigmoid((v * model.out_emb.weight[o]).sum(1))
            + F.logsigmoid(-torch.einsum("bkd,bd->bk", model.out_emb.weight[neg], v)).sum(1)).mean()
    loss = model(c, o, neg)
    assert loss.dim() == 0 and loss.item() == pytest.approx(ref.item(), rel=1e-6), "loss trung bình trên batch"
    loss.backward()
    assert model.in_emb.weight.grad.is_sparse, "dùng nn.Embedding(..., sparse=True)"


def topic_corpus(seed: int):
    rng = np.random.default_rng(seed)
    food = "phở bún cơm bánh chè xôi nem gỏi".split()
    sport = "bóng đá chạy bơi vợt cờ võ đua".split()
    sents = [list(rng.choice(food if rng.random() < 0.5 else sport, 10)) for _ in range(600)]
    return sents, food, sport


def test_train_sgns_learns_topics(nb):
    sents, food, sport = topic_corpus(0)
    words, counts = nb.build_vocab(sents, 1)
    ids, sent_ids = nb.flatten(sents, {w: i for i, w in enumerate(words)})
    E = nb.train_sgns(ids, sent_ids, counts, dim=16, window=3, negatives=5, epochs=3, batch_size=64, lr=0.05, seed=0,
                      sample=1.0)
    assert isinstance(E, np.ndarray) and E.shape == (16, 16)
    top = {w for w, _ in nb.most_similar(E, words, "phở", 7)}
    assert top == set(food) - {"phở"}, f"láng giềng của 'phở' phải là món ăn, được {top}"
    E2 = nb.train_sgns(ids, sent_ids, counts, dim=16, window=3, negatives=5, epochs=3, batch_size=64, lr=0.05, seed=0,
                       sample=1.0)
    np.testing.assert_allclose(E, E2, err_msg="cùng seed phải ra cùng embedding")


def test_most_similar_and_analogy(nb):
    words = ["a", "b", "c", "d", "e"]
    E = np.array([[1.0, 0, 0], [10.0, 1, 0], [1.0, 0.2, 0], [-1.0, 0, 0], [3.0, 10, 0]])
    out = nb.most_similar(E, words, "a", 2)
    assert [w for w, _ in out] == ["b", "c"], "cosine, không phải tích vô hướng; bỏ chính từ đó"
    # vua - nam + nữ: dựng 4 vector để b - a + c trùng hướng d nhưng gần a, b, c hơn
    words = ["nam", "vua", "nữ", "hoàng_hậu", "khác"]
    E = np.array([[1.0, 0, 0, 0], [1.0, 1, 0, 0], [0, 0, 1.0, 0], [0, 1.0, 1, 0], [0.2, 0.2, 0.2, 1]])
    assert nb.analogy(E, words, "nam", "vua", "nữ", 1) == ["hoàng_hậu"]
    assert nb.analogy(E, words, "nam", "vua", "nữ", 2) == ["hoàng_hậu", "khác"], "bỏ a, b, c khỏi kết quả"
    pairs = [("nam", "vua"), ("nữ", "hoàng_hậu"), ("x", "y")]
    ok, total = nb.analogy_accuracy(E, words, pairs)
    assert total == 2, "chỉ tính cặp có trong vocab, mọi cặp có thứ tự khác nhau"
    assert ok == 2


# ---------- Dữ liệu thật: tự skip nếu chưa tải wikipedia-vi ----------

def test_real_wikipedia_subset(nb):
    shard = ex.dataset("wikipedia-vi") / "20231101.vi" / "train-00001-of-00004.parquet"
    articles = nb.load_articles(shard, n_articles=200, min_chars=2000, seed=0)
    assert len(articles) == 200 and all(len(a) >= 2000 for a in articles)
    sents = [s for a in articles for s in nb.tokenize(a)]
    n_tokens = sum(map(len, sents))
    # Lời giải mẫu: 17 613 câu, 270 597 âm tiết
    assert len(sents) == 17613 and n_tokens == 270597
    phrases = nb.find_phrases(sents, min_count=5, delta=5, threshold=100)
    assert ("việt", "nam") in phrases and ("của", "các") not in phrases

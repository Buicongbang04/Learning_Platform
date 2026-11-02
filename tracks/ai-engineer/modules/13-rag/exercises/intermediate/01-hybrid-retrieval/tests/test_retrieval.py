import json

import numpy as np
import pytest
from llmkit import FakeLLM
from testkit import Exercise

ex = Exercise(__file__)


@pytest.fixture(scope="module")
def nb():
    return ex.notebook("retrieval.ipynb")


def write_jsonl(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8")


@pytest.fixture
def tiny_root(tmp_path):
    """Bộ dữ liệu kiểu BEIR thu nhỏ, đúng định dạng Zalo Legal."""
    write_jsonl(tmp_path / "corpus.jsonl", [
        {"_id": "100/2019/nđ-cp+5", "title": "Điều 5. Xử phạt người điều khiển xe ô tô", "text": "1. Phạt tiền ..."},
        {"_id": "01/2009/tt-bnn+1", "title": "Điều 1. Phạm vi áp dụng", "text": "Tuần tra canh gác đê"},
        {"_id": "47/2011/tt-bca+7", "title": "Điều 7. Nhiệm vụ của Công an xã", "text": "4. Công an xã ..."},
    ])
    write_jsonl(tmp_path / "queries.jsonl", [
        {"_id": "q0", "text": "Câu không có trong qrels"},
        {"_id": "q1", "text": "Mức phạt quay đầu xe trên cao tốc?"},
        {"_id": "q2", "text": "Ai tuần tra đê?"},
        {"_id": "q3", "text": "Công an xã được xử phạt gì?"},
    ])
    write_jsonl(tmp_path / "qrels" / "test.jsonl", [
        {"query-id": "q2", "corpus-id": "01/2009/tt-bnn+1", "score": 1},
        {"query-id": "q1", "corpus-id": "100/2019/nđ-cp+5", "score": 1},
        {"query-id": "q2", "corpus-id": "47/2011/tt-bca+7", "score": 1},   # q2 có hai điều đúng, không liền nhau
        {"query-id": "q3", "corpus-id": "47/2011/tt-bca+7", "score": 1},
    ])
    write_jsonl(tmp_path / "qrels" / "train.jsonl", [
        {"query-id": "q3", "corpus-id": "100/2019/nđ-cp+5", "score": 1},
    ])
    return tmp_path


def test_load_corpus(nb, tiny_root):
    arts = nb.load_corpus(tiny_root)
    assert [a.uid for a in arts] == ["100/2019/nđ-cp+5", "01/2009/tt-bnn+1", "47/2011/tt-bca+7"]
    assert isinstance(arts[0], nb.Article)
    assert arts[1].title == "Điều 1. Phạm vi áp dụng" and arts[1].text == "Tuần tra canh gác đê"


def test_load_questions_order_and_relevant(nb, tiny_root):
    qs = nb.load_questions(tiny_root, 2)
    assert [q.qid for q in qs] == ["q2", "q1"], "thứ tự xuất hiện đầu tiên trong qrels/test.jsonl"
    assert isinstance(qs[0], nb.Question)
    assert qs[0].text == "Ai tuần tra đê?"
    assert qs[0].relevant == {"01/2009/tt-bnn+1", "47/2011/tt-bca+7"}, "gom mọi dòng của câu, kể cả không liền nhau"
    assert qs[1].relevant == {"100/2019/nđ-cp+5"}


def test_load_questions_n_larger_and_split(nb, tiny_root):
    assert [q.qid for q in nb.load_questions(tiny_root, 10)] == ["q2", "q1", "q3"]
    train = nb.load_questions(tiny_root, 10, split="train")
    assert [(q.qid, q.relevant) for q in train] == [("q3", {"100/2019/nđ-cp+5"})]


def test_pasted_basic_helpers(nb):
    assert nb.tokenize_vi("Nghị định 100/2019/NĐ-CP") == ["nghị", "định", "100", "2019", "nđ", "cp"]
    bm = nb.BM25([["đê", "điều"], ["xe", "ô", "tô"], ["xe", "máy"]])
    assert bm.top_k(["ô", "tô"], 2)[0] == 1
    retrieved, relevant = [["a", "b"], ["c", "d"]], [{"b"}, {"x"}]
    assert nb.recall_at_k(retrieved, relevant, 2) == pytest.approx(0.5)
    assert nb.mrr_at_k(retrieved, relevant, 2) == pytest.approx(0.25)


class CountingEmbed:
    def __init__(self):
        self.fake = FakeLLM(dim=64)
        self.batches: list[int] = []

    def __call__(self, texts):
        self.batches.append(len(texts))
        return self.fake.embed(texts)


def test_embed_corpus_batches_and_normalizes(nb):
    texts = [f"điều {i} quy định xử phạt {i % 7}" for i in range(70)]
    embed_fn = CountingEmbed()
    out = nb.embed_corpus(texts, embed_fn, batch_size=32)
    assert embed_fn.batches == [32, 32, 6], "gọi embed_fn theo lô 32 liên tiếp, lô cuối ngắn hơn"
    assert out.shape == (70, 64) and out.dtype == np.float32
    np.testing.assert_allclose(np.linalg.norm(out, axis=1), 1.0, rtol=1e-5)
    raw = FakeLLM(dim=64).embed(texts)
    np.testing.assert_allclose(out, raw / np.linalg.norm(raw, axis=1, keepdims=True), rtol=1e-5, atol=1e-7)

    embed_fn = CountingEmbed()
    nb.embed_corpus(texts[:5], embed_fn)
    assert embed_fn.batches == [5], "batch_size mặc định 32"


def test_embed_corpus_zero_row_stays_zero(nb):
    def embed_fn(texts):
        return np.array([[3.0, 4.0], [0.0, 0.0]], dtype=np.float32)[: len(texts)]

    out = nb.embed_corpus(["a", "b"], embed_fn)
    assert not np.isnan(out).any(), "vector 0 (embed lỗi) không được chia cho 0 thành NaN"
    np.testing.assert_allclose(out, [[0.6, 0.8], [0.0, 0.0]], rtol=1e-6)


def test_dense_search_finds_matching_doc(nb):
    fake = FakeLLM(dim=256)
    docs = ["tuần tra canh gác đê điều mùa lũ", "xử phạt nồng độ cồn người lái xe ô tô",
            "thủ tục cấp hộ chiếu phổ thông", "đăng ký kết hôn tại ủy ban nhân dân xã"]
    matrix = nb.embed_corpus(docs, fake.embed)
    q = fake.embed(["phạt nồng độ cồn khi lái ô tô"])[0]
    result = nb.dense_search(q, matrix, 2)
    assert result[0] == 1
    assert len(result) == 2 and all(isinstance(i, int) for i in result)
    assert nb.dense_search(fake.embed(["kết hôn"])[0], matrix, 1) == [3]


def test_dense_search_order_and_ties(nb):
    matrix = np.array([[1, 0], [0, 1], [1, 0], [0.6, 0.8]], dtype=np.float32)
    assert nb.dense_search(np.array([1.0, 0.0]), matrix, 4) == [0, 2, 3, 1], "bằng điểm thì chỉ số nhỏ trước"
    assert nb.dense_search(np.array([5.0, 0.0]), matrix, 2) == [0, 2], "độ dài q_vec không đổi thứ hạng"


def test_rrf_hand_table(nb):
    A, B, C, D = 0, 1, 2, 3
    assert nb.rrf_fuse([[A, B, C], [C, A, D]]) == [A, C, B, D]   # 0.03252, 0.03227, 0.01613, 0.01587


def test_rrf_k_changes_result(nb):
    # tài liệu 3 đứng hạng 4 ở cả hai danh sách; 0 và 4 đứng hạng 1 ở một danh sách
    rankings = [[0, 1, 2, 3], [4, 5, 6, 3]]
    # k = 1: tài liệu 0, 4 được 1/2; tài liệu 3 được 1/5 + 1/5 = 0.4: hạng 1 một nhánh thắng
    assert nb.rrf_fuse(rankings, k=1) == [0, 4, 3, 1, 5, 2, 6]
    # k = 60: tài liệu 3 được 2/64 = 0.031 > 1/61 = 0.016: có mặt ở cả hai nhánh thắng
    assert nb.rrf_fuse(rankings) == [3, 0, 4, 1, 5, 2, 6]


def test_rrf_ties_and_single_list(nb):
    assert nb.rrf_fuse([[5], [3]]) == [3, 5], "bằng điểm thì chỉ số nhỏ trước"
    assert nb.rrf_fuse([[9, 4, 7]]) == [9, 4, 7]
    assert nb.rrf_fuse([[], [2]]) == [2]


# ---------- Dữ liệu thật: tự skip nếu chưa tải Zalo Legal; không gọi Ollama ----------

_REAL: dict[str, object] = {}


def real_corpus(nb):
    root = ex.dataset("zalo-legal")
    if "corpus" not in _REAL:
        _REAL["corpus"] = nb.load_corpus(root)
    return root, _REAL["corpus"]


def test_load_real_corpus_and_pinned_questions(nb):
    root, arts = real_corpus(nb)
    assert len(arts) == 61425
    assert arts[0].uid == "01/2009/tt-bnn+1" and arts[0].title == "Điều 1. Phạm vi áp dụng"
    qs = nb.load_questions(root, 300)
    assert len(qs) == 300 and len({q.qid for q in qs}) == 300
    assert qs[0].qid == "268afbc1f6756c6ef1f37f66f5fb85bd"
    assert qs[0].text == "Mức phạt khi quay đầu xe ô tô trên đường cao tốc"
    assert qs[0].relevant == {"100/2019/nđ-cp+5"}
    assert sum(len(q.relevant) for q in qs) == 301
    uids = {a.uid for a in arts}
    assert all(q.relevant <= uids for q in qs)


def test_dense_search_on_cached_matrix(nb):
    root, arts = real_corpus(nb)
    cache = root / "cache"
    if not (cache / "bge-m3.npy").exists():
        pytest.skip("Chưa có cache bge-m3: chạy cell embed trong notebook một lần")
    ids = json.loads((cache / "bge-m3.ids.json").read_text(encoding="utf-8"))
    assert ids == [a.uid for a in arts]
    matrix = np.load(cache / "bge-m3.npy", mmap_mode="r")
    assert matrix.shape == (61425, 1024)
    rows = np.asarray(matrix[:2000])
    for i in (0, 777, 1999):
        top = nb.dense_search(rows[i], rows, 3)
        assert float(rows[top[0]] @ rows[i]) == pytest.approx(1.0, abs=1e-3)

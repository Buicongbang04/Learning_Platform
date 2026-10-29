import random

import pytest
import torch
from sklearn.metrics import roc_auc_score

from testkit import ROOT, Exercise

ex = Exercise(__file__)
torch.set_num_threads(2)
torch.use_deterministic_algorithms(True)


@pytest.fixture(scope="module")
def nb():
    return ex.notebook("review_embeddings.ipynb")


BAD = ["pessimo", "atraso", "defeito", "nao chegou", "horrivel", "devolver"]
GOOD = ["otimo", "recomendo", "perfeito", "chegou rapido", "excelente", "adorei"]
FILLER = ["produto", "entrega", "loja", "compra", "veio", "muito", "bem", "o", "a", "de"]


def synthetic_reviews(n: int, seed: int):
    """Review giả kiểu tiếng Bồ Đào Nha: review xấu chứa một cụm từ "xấu", review tốt chứa cụm "tốt"."""
    rng = random.Random(seed)
    texts, labels = [], []
    for _ in range(n):
        bad = rng.random() < 0.3
        words = rng.choices(FILLER, k=rng.randint(3, 10))
        words.insert(rng.randint(0, len(words)), rng.choice(BAD if bad else GOOD))
        texts.append(" ".join(words))
        labels.append(int(bad))
    return texts, torch.tensor(labels, dtype=torch.float32)


def test_tokenize(nb):
    assert nb.tokenize("Não GOSTEI!! produto péssimo, 2x") == ["nao", "gostei", "produto", "pessimo", "x"]
    assert nb.tokenize("Ótimo. Recomendo; entrega rápida :)") == ["otimo", "recomendo", "entrega", "rapida"]
    assert nb.tokenize("") == []
    assert nb.tokenize("ação\ncoração") == ["acao", "coracao"]


def test_build_vocab_order_and_specials(nb):
    texts = ["b a a", "c b a", "d"]
    vocab = nb.build_vocab(texts, min_freq=1)
    assert vocab == {"<pad>": 0, "<unk>": 1, "a": 2, "b": 3, "c": 4, "d": 5}   # tần suất giảm, hoà thì theo chữ cái
    assert nb.build_vocab(texts, min_freq=2) == {"<pad>": 0, "<unk>": 1, "a": 2, "b": 3}
    assert nb.build_vocab(texts, min_freq=1, max_size=4) == {"<pad>": 0, "<unk>": 1, "a": 2, "b": 3}


def test_build_vocab_uses_tokenize(nb):
    vocab = nb.build_vocab(["Péssimo PESSIMO pessimo"], min_freq=3)
    assert "pessimo" in vocab and len(vocab) == 3


def test_encode(nb):
    vocab = {"<pad>": 0, "<unk>": 1, "otimo": 2, "produto": 3}
    X = nb.encode(["Ótimo produto", "produto xyz otimo otimo", ""], vocab, max_len=3)
    assert X.dtype == torch.long and X.shape == (3, 3)
    assert X.tolist() == [[2, 3, 0], [3, 1, 2], [0, 0, 0]]


def test_bag_of_embeddings_is_masked_mean(nb):
    torch.manual_seed(0)
    model = nb.BagOfEmbeddings(vocab_size=10, dim=4)
    model.eval()
    X = torch.tensor([[2, 3, 0, 0], [4, 4, 5, 6], [0, 0, 0, 0]])
    out = model(X)
    assert out.shape == (3,)
    W = model.embedding.weight
    with torch.no_grad():
        means = torch.stack([W[[2, 3]].mean(0), W[[4, 4, 5, 6]].mean(0), torch.zeros(4)])
        expected = model.out(means).squeeze(-1)
    torch.testing.assert_close(out, expected)
    # thêm cột padding không đổi kết quả
    wider = torch.cat([X, torch.zeros(3, 6, dtype=torch.long)], dim=1)
    torch.testing.assert_close(model(wider), out)


def test_train_text_model_learns_and_restores_best(nb):
    texts, y = synthetic_reviews(1500, 0)
    val_texts, y_val = synthetic_reviews(500, 1)
    test_texts, y_test = synthetic_reviews(500, 2)
    vocab = nb.build_vocab(texts, min_freq=2)
    X, X_val, X_test = (nb.encode(t, vocab, max_len=16) for t in (texts, val_texts, test_texts))
    torch.manual_seed(0)
    model = nb.BagOfEmbeddings(len(vocab), dim=8)
    hist = nb.train_text_model(model, X, y, X_val, y_val, epochs=15, lr=1e-2, batch_size=64, patience=3, seed=0)
    assert {"train_loss", "val_loss", "best_epoch"} <= set(hist)
    assert hist["val_loss"][hist["best_epoch"]] == min(hist["val_loss"])
    model.eval()
    with torch.no_grad():
        val_loss = torch.nn.functional.binary_cross_entropy_with_logits(model(X_val), y_val).item()
        scores = model(X_test)
    assert val_loss == pytest.approx(min(hist["val_loss"]), rel=1e-4)    # trọng số tốt nhất được nạp lại
    assert roc_auc_score(y_test.numpy(), scores.numpy()) > 0.97


def test_train_text_model_is_reproducible(nb):
    texts, y = synthetic_reviews(300, 3)
    vocab = nb.build_vocab(texts, min_freq=1)
    X = nb.encode(texts, vocab, max_len=12)
    runs = []
    for _ in range(2):
        torch.manual_seed(1)
        model = nb.BagOfEmbeddings(len(vocab), dim=4)
        runs.append(nb.train_text_model(model, X, y, X, y, epochs=3, lr=1e-2, batch_size=32, patience=5, seed=4))
    assert runs[0]["train_loss"] == runs[1]["train_loss"]


def test_nearest_words(nb):
    vocab = {"<pad>": 0, "<unk>": 1, "otimo": 2, "excelente": 3, "pessimo": 4, "horrivel": 5}
    weight = torch.tensor([
        [1.0, 0.0],     # pad: không bao giờ được trả về
        [0.9, 0.1],     # unk: không bao giờ được trả về
        [1.0, 0.1],
        [3.0, 0.5],     # cùng hướng với otimo, dài hơn: cosine vẫn cao nhất
        [-1.0, 0.2],
        [-2.0, 0.1],
    ])
    assert nb.nearest_words(weight, vocab, "otimo", k=2) == ["excelente", "pessimo"]
    assert nb.nearest_words(weight, vocab, "pessimo", k=1) == ["horrivel"]
    with pytest.raises(KeyError):
        nb.nearest_words(weight, vocab, "inexistente")


def test_real_olist_reviews(nb):
    raw = ROOT / "data" / "raw"
    if not (raw / "olist_order_reviews_dataset.csv").exists():
        pytest.skip("Chưa tải Olist thật: uv run python data/download_olist.py")
    df = nb.load_reviews(raw)
    parts = nb.time_split(df)
    assert len(df) == 38872
    assert [len(parts[k]) for k in ("train", "val", "test")] == [17883, 8562, 12427]
    assert df.bad.mean() == pytest.approx(0.2375, abs=5e-4)
    vocab = nb.build_vocab(parts["train"].text, min_freq=2)
    assert len(vocab) == 4341

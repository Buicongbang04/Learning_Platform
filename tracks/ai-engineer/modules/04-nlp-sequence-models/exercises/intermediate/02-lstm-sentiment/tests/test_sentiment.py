import time
import unicodedata

import numpy as np
import pytest
import torch
from sklearn.metrics import f1_score
from testkit import Exercise

ex = Exercise(__file__)
torch.set_num_threads(1)


@pytest.fixture(scope="module")
def nb():
    return ex.notebook("sentiment.ipynb")


SENTS = ["thầy dạy hay", "thầy dạy chán", "phòng học nóng", "thầy nhiệt tình", "", "Thầy  DẠY hay"]


def test_tokenize_and_vocab(nb):
    assert nb.tokenize(unicodedata.normalize("NFD", "Thầy  DẠY hay")) == ["thầy", "dạy", "hay"]
    vocab = nb.build_vocab(SENTS, min_freq=2)
    assert vocab == {"<pad>": 0, "<unk>": 1, "thầy": 2, "dạy": 3, "hay": 4}, \
        "<pad>, <unk>, rồi tần suất giảm dần (thầy 4, dạy 3, hay 2), bỏ từ < min_freq"
    assert nb.build_vocab(["nóng b", "b nóng", "c"], 1) == {"<pad>": 0, "<unk>": 1, "b": 2, "nóng": 3, "c": 4}, \
        "hoà tần suất thì theo thứ tự chữ cái"


def test_encode_batch(nb):
    vocab = nb.build_vocab(SENTS, min_freq=2)
    ids, lengths = nb.encode_batch(["thầy dạy hay hay hay", "", "phòng thầy"], vocab, max_len=4)
    assert ids.dtype == torch.long and lengths.dtype == torch.long
    assert ids.tolist() == [[2, 3, 4, 4], [1, 0, 0, 0], [1, 2, 0, 0]]
    assert lengths.tolist() == [4, 1, 2]
    ids2, _ = nb.encode_batch(["thầy", "hay"], vocab, max_len=64)
    assert ids2.shape == (2, 1), "L là độ dài lớn nhất trong batch, không phải max_len"


def test_classifier_shapes(nb):
    torch.manual_seed(0)
    for bi in [True, False]:
        model = nb.LSTMClassifier(20, 8, 6, 3, bidirectional=bi)
        logits = model(torch.randint(2, 20, (5, 7)), torch.tensor([7, 3, 1, 5, 2]))
        assert logits.shape == (5, 3)


def test_padding_invariance(nb):
    torch.manual_seed(0)
    model = nb.LSTMClassifier(30, 8, 6, 3, bidirectional=True).eval()
    short = torch.tensor([[5, 6, 7]])
    alone = model(short, torch.tensor([3]))
    padded = torch.zeros(2, 12, dtype=torch.long)
    padded[0, :3] = short[0]
    padded[1] = torch.randint(2, 30, (12,))
    together = model(padded, torch.tensor([3, 12]))
    torch.testing.assert_close(together[0], alone[0], atol=1e-6, rtol=1e-5,
                               msg="logits của câu ngắn đổi khi pad thêm: dùng pack_padded_sequence")


def test_backward_direction_reads_whole_sentence(nb):
    # Chiều ngược phải đọc tới token ĐẦU: đổi token đầu câu thì logits phải đổi (kể cả khi chỉ có chiều ngược nhạy)
    torch.manual_seed(1)
    model = nb.LSTMClassifier(30, 8, 6, 3, bidirectional=True).eval()
    a = model(torch.tensor([[5, 6, 7, 8, 0, 0]]), torch.tensor([4]))
    b = model(torch.tensor([[9, 6, 7, 8, 0, 0]]), torch.tensor([4]))
    assert not torch.allclose(a, b)


def test_macro_f1(nb):
    rng = np.random.default_rng(0)
    y = rng.integers(0, 3, 200)
    p = np.where(rng.random(200) < 0.7, y, rng.integers(0, 3, 200))
    assert nb.macro_f1(y, p, 3) == pytest.approx(f1_score(y, p, average="macro"))
    p_no_neutral = np.where(p == 1, 2, p)          # không bao giờ đoán lớp 1
    assert nb.macro_f1(y, p_no_neutral, 3) == pytest.approx(
        f1_score(y, p_no_neutral, average="macro", labels=[0, 1, 2], zero_division=0))
    assert isinstance(nb.macro_f1(y, p, 3), float)


def toy_data(n: int, seed: int, noise: float = 0.0):
    """Nhãn quyết định bởi một token khoá ở vị trí ngẫu nhiên; câu dài ngắn khác nhau.

    noise > 0: tỉ lệ nhãn bị đổi ngẫu nhiên (token khoá vẫn theo nhãn thật).
    """
    rng = np.random.default_rng(seed)
    lengths = rng.integers(3, 12, n)
    ids = torch.zeros(n, 11, dtype=torch.long)
    y = rng.integers(0, 3, n)
    for i in range(n):
        ids[i, :lengths[i]] = torch.tensor(rng.integers(5, 40, lengths[i]))
        ids[i, rng.integers(0, lengths[i])] = 2 + y[i]       # token 2, 3, 4 là khoá của nhãn 0, 1, 2
    noisy = np.where(rng.random(n) < noise, rng.integers(0, 3, n), y)
    return ids, torch.tensor(lengths), torch.tensor(noisy)


def test_train_classifier_learns_and_keeps_best(nb):
    train, val = toy_data(600, 0), toy_data(200, 1)
    torch.manual_seed(0)
    model = nb.LSTMClassifier(40, 16, 24, 3, bidirectional=True, dropout=0.0)
    hist = nb.train_classifier(model, train, val, epochs=6, lr=1e-2, batch_size=32, seed=0)
    assert set(hist) >= {"train_loss", "val_f1"}
    assert len(hist["train_loss"]) == 6 and len(hist["val_f1"]) == 6
    assert all(isinstance(v, float) for v in hist["train_loss"] + hist["val_f1"])
    assert hist["train_loss"][-1] < hist["train_loss"][0]
    assert max(hist["val_f1"]) >= 0.9, f"bài khoá-token dễ: val macro-F1 phải >= 0.9, được {hist['val_f1']}"
    pred = nb.predict(model, val[0], val[1])
    assert isinstance(pred, np.ndarray) and pred.shape == (200,)
    assert nb.macro_f1(val[2].numpy(), pred, 3) == pytest.approx(max(hist["val_f1"])), \
        "sau khi train, model phải mang trọng số của epoch có val macro-F1 cao nhất"


def test_train_restores_best_epoch(nb):
    # 50% nhãn train bị đổi: val đạt đỉnh ở epoch 2 rồi tụt khi model thuộc lòng nhãn sai
    # (lời giải mẫu: 0.868 ở epoch 2, 0.669 ở epoch 8)
    train, val = toy_data(300, 11, noise=0.5), toy_data(200, 1)
    torch.manual_seed(0)
    model = nb.LSTMClassifier(40, 16, 32, 3, bidirectional=True, dropout=0.0)
    hist = nb.train_classifier(model, train, val, epochs=8, lr=1e-2, batch_size=16, seed=0)
    assert hist["val_f1"][-1] < max(hist["val_f1"]) - 0.05
    f1 = nb.macro_f1(val[2].numpy(), nb.predict(model, val[0], val[1]), 3)
    assert f1 == pytest.approx(max(hist["val_f1"])), \
        "phải nạp lại BẢN SAO trọng số của epoch tốt nhất (copy.deepcopy, state_dict trả tham chiếu)"


def test_train_loss_is_mean_over_samples(nb):
    # lr = 0: tham số đứng yên nên train loss của epoch = cross-entropy trên cả tập (50 mẫu, batch 16: batch cuối 2 mẫu)
    train, val = toy_data(50, 4), toy_data(20, 5)
    torch.manual_seed(0)
    model = nb.LSTMClassifier(40, 8, 8, 3, dropout=0.0)
    hist = nb.train_classifier(model, train, val, epochs=1, lr=0.0, batch_size=16, seed=0)
    with torch.no_grad():
        full = torch.nn.functional.cross_entropy(model(train[0], train[1]), train[2]).item()
    assert hist["train_loss"][0] == pytest.approx(full, rel=1e-5)


def test_predict_uses_eval_mode(nb):
    torch.manual_seed(0)
    model = nb.LSTMClassifier(40, 16, 16, 3, dropout=0.9)
    ids, lengths, _ = toy_data(100, 6)
    model.train()
    a = nb.predict(model, ids, lengths)
    b = nb.predict(model, ids, lengths, batch_size=7)
    assert np.array_equal(a, b), "predict phải tắt dropout (model.eval()), kết quả không phụ thuộc batch"


def test_train_is_reproducible(nb):
    train, val = toy_data(200, 2), toy_data(50, 3)
    runs = []
    for _ in range(2):
        torch.manual_seed(5)
        model = nb.LSTMClassifier(40, 8, 8, 3)
        runs.append(nb.train_classifier(model, train, val, epochs=2, lr=1e-2, batch_size=32, seed=5))
    assert runs[0] == runs[1]
    torch.manual_seed(5)
    other = nb.train_classifier(nb.LSTMClassifier(40, 8, 8, 3), train, val, epochs=2, lr=1e-2, batch_size=32, seed=6)
    assert other["train_loss"] != runs[0]["train_loss"], "seed phải điều khiển thứ tự xáo và dropout"


# ---------- Dữ liệu thật: tự skip nếu chưa tải UIT-VSFC ----------

def test_real_uit_vsfc(nb):
    root = ex.dataset("uit-vsfc")
    train_s, train_y = nb.load_split(root, "train")
    val_s, val_y = nb.load_split(root, "validation")
    assert len(train_s) == 11426 and train_y.dtype == np.int64
    assert np.bincount(train_y).tolist() == [5325, 458, 5643]
    vocab = nb.build_vocab(train_s, min_freq=2)
    assert len(vocab) == 1535
    start = time.perf_counter()
    train = (*nb.encode_batch(train_s[:4000], vocab, 64), torch.tensor(train_y[:4000]))
    val = (*nb.encode_batch(val_s, vocab, 64), torch.tensor(val_y))
    torch.manual_seed(0)
    model = nb.LSTMClassifier(len(vocab), 64, 64, 3, bidirectional=True)
    hist = nb.train_classifier(model, train, val, epochs=2, lr=2e-3, batch_size=64, seed=0)
    assert time.perf_counter() - start < 30
    acc = float(np.mean(nb.predict(model, val[0], val[1]) == val_y))
    # Lời giải mẫu: val accuracy 0.858 sau 2 epoch trên 4 000 câu
    assert acc >= 0.8, f"val accuracy {acc:.3f}"

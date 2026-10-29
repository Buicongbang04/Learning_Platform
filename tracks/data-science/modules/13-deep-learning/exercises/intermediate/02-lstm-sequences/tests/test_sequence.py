import copy

import pytest
import torch
from torch import nn

from testkit import Exercise

ex = Exercise(__file__)
torch.set_num_threads(2)
torch.use_deterministic_algorithms(True)


@pytest.fixture(scope="module")
def sq():
    return ex.module("sequence.py")


def first_token_task(n: int, seed: int, min_len: int = 10, max_len: int = 20, vocab: int = 12):
    """Chuỗi token 2..vocab-1, độ dài ngẫu nhiên; nhãn = token ĐẦU TIÊN chẵn hay lẻ.

    Model đọc từ trái sang phải phải nhớ thông tin từ bước đầu qua 10–20 bước. Trên cấu hình dưới,
    LSTM học được ở 10/10 seed, RNN thường chỉ khoảng 2/10 (xem SOLUTION.md).
    """
    g = torch.Generator().manual_seed(seed)
    lengths = torch.randint(min_len, max_len + 1, (n,), generator=g)
    seqs = [torch.randint(2, vocab, (int(L),), generator=g).tolist() for L in lengths]
    y = torch.tensor([s[0] % 2 for s in seqs])
    return seqs, y


def test_pad_sequences(sq):
    padded, lengths = sq.pad_sequences([[5, 6, 7], [8], [9, 10]])
    assert padded.dtype == torch.long and lengths.dtype == torch.long
    assert padded.tolist() == [[5, 6, 7], [8, 0, 0], [9, 10, 0]]
    assert lengths.tolist() == [3, 1, 2]
    padded, _ = sq.pad_sequences([[1], [2, 3]], pad_value=-1)
    assert padded.tolist() == [[1, -1], [2, 3]]


@pytest.mark.parametrize("cell", ["lstm", "gru", "rnn"])
def test_classifier_shapes_and_cell_type(sq, cell):
    torch.manual_seed(0)
    model = sq.SequenceClassifier(vocab_size=12, embed_dim=8, hidden_dim=16, n_classes=3, cell=cell)
    expected = {"lstm": nn.LSTM, "gru": nn.GRU, "rnn": nn.RNN}[cell]
    assert any(isinstance(m, expected) for m in model.modules())
    padded, lengths = sq.pad_sequences([[2, 3, 4], [5], [6, 7]])
    assert model(padded, lengths).shape == (3, 3)


@pytest.mark.parametrize("cell", ["lstm", "gru"])
def test_padding_does_not_change_output(sq, cell):
    torch.manual_seed(1)
    model = sq.SequenceClassifier(vocab_size=12, embed_dim=8, hidden_dim=16, n_classes=2, cell=cell)
    model.eval()
    seqs = [[2, 3, 4, 5], [6, 7], [8, 9, 10, 11, 2, 3]]
    padded, lengths = sq.pad_sequences(seqs)
    out = model(padded, lengths)
    # thêm 5 cột padding nữa: output không đổi
    longer = torch.cat([padded, torch.zeros(3, 5, dtype=torch.long)], dim=1)
    torch.testing.assert_close(model(longer, lengths), out)
    # ghi token thật vào chỗ padding: model vẫn phải bỏ qua chúng (lengths quyết định)
    garbage = padded.clone()
    garbage[1, 2:] = 9
    garbage[0, 4:] = 9
    torch.testing.assert_close(model(garbage, lengths), out)
    # mỗi chuỗi chạy riêng (không padding) cho cùng kết quả
    for i, s in enumerate(seqs):
        alone = model(torch.tensor([s]), torch.tensor([len(s)]))
        torch.testing.assert_close(alone[0], out[i])


def test_clip_gradients_matches_torch(sq):
    torch.manual_seed(2)
    model = nn.Sequential(nn.Linear(4, 8), nn.Tanh(), nn.Linear(8, 2))
    ref = copy.deepcopy(model)
    x = torch.randn(16, 4) * 50
    for m in (model, ref):
        m(x).square().sum().backward()
    norm = sq.clip_gradients(model, max_norm=1.0)
    ref_norm = nn.utils.clip_grad_norm_(ref.parameters(), max_norm=1.0)
    assert isinstance(norm, float)
    assert norm == pytest.approx(ref_norm.item(), rel=1e-5)          # norm TRƯỚC khi cắt
    for p, q in zip(model.parameters(), ref.parameters()):
        torch.testing.assert_close(p.grad, q.grad)
    total = torch.sqrt(sum(p.grad.square().sum() for p in model.parameters()))
    assert total.item() == pytest.approx(1.0, rel=1e-4)


def test_train_returns_losses_and_is_reproducible(sq):
    seqs, y = first_token_task(128, 3)
    padded, lengths = sq.pad_sequences(seqs)
    runs = []
    for _ in range(2):
        torch.manual_seed(0)
        model = sq.SequenceClassifier(12, 8, 16, 2, cell="lstm")
        runs.append(sq.train_classifier(model, padded, lengths, y, epochs=2, lr=1e-2, batch_size=32, seed=5))
    assert len(runs[0]) == 2 and all(isinstance(v, float) for v in runs[0])
    assert runs[0] == runs[1]


@pytest.mark.parametrize("seed", [0, 1])
def test_lstm_remembers_first_token(sq, seed):
    seqs, y = first_token_task(3000, 100 + seed)
    test_seqs, y_test = first_token_task(400, 200 + seed)
    padded, lengths = sq.pad_sequences(seqs)
    t_padded, t_lengths = sq.pad_sequences(test_seqs)
    torch.manual_seed(seed)
    model = sq.SequenceClassifier(12, 16, 32, 2, cell="lstm")
    losses = sq.train_classifier(model, padded, lengths, y, epochs=10, lr=3e-3, batch_size=32, clip=1.0, seed=seed)
    assert losses[-1] < losses[0]
    model.eval()
    with torch.no_grad():
        acc = (model(t_padded, t_lengths).argmax(1) == y_test).float().mean().item()
    assert acc > 0.9

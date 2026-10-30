import numpy as np
import pytest
import torch
import torch.nn.functional as F
from testkit import Exercise

ex = Exercise(__file__)
torch.set_num_threads(1)


@pytest.fixture(scope="module")
def nb():
    return ex.notebook("seq2seq.ipynb")


def make_keys(seed: int, N: int = 3, S: int = 5, D: int = 4):
    g = torch.Generator().manual_seed(seed)
    keys = torch.randn(N, S, D, generator=g)
    lengths = torch.tensor([5, 3, 1])[:N]
    mask = torch.arange(S)[None, :] < lengths[:, None]
    return keys, mask


def test_bahdanau_matches_formula(nb):
    torch.manual_seed(0)
    attn = nb.BahdanauAttention(4, 6, 7)
    assert attn.W_q.weight.shape == (7, 6) and attn.W_k.weight.shape == (7, 4) and attn.v.weight.shape == (1, 7)
    assert attn.W_q.bias is None and attn.W_k.bias is None and attn.v.bias is None
    keys, mask = make_keys(1)
    q = torch.randn(3, 6, generator=torch.Generator().manual_seed(2))
    ctx, w = attn(q, keys, mask)
    assert ctx.shape == (3, 4) and w.shape == (3, 5)
    Wq, Wk, v = attn.W_q.weight.detach(), attn.W_k.weight.detach(), attn.v.weight.detach()[0]
    for n in range(3):
        L = int(mask[n].sum())
        e = torch.stack([v @ torch.tanh(Wq @ q[n] + Wk @ keys[n, j]) for j in range(L)])
        a = torch.softmax(e, 0)
        torch.testing.assert_close(w[n, :L].detach(), a, atol=1e-6, rtol=1e-5)
        torch.testing.assert_close(ctx[n].detach(), a @ keys[n, :L], atol=1e-6, rtol=1e-5)
        assert torch.all(w[n, L:] == 0), "trọng số ở padding phải đúng bằng 0"


def test_luong_dot_and_general(nb):
    keys, mask = make_keys(3)
    q = torch.randn(3, 4, generator=torch.Generator().manual_seed(4))
    dot = nb.LuongAttention(4, 4, "dot")
    ctx, w = dot(q, keys, mask)
    for n in range(3):
        L = int(mask[n].sum())
        a = torch.softmax(keys[n, :L] @ q[n], 0)
        torch.testing.assert_close(w[n, :L], a, atol=1e-6, rtol=1e-5)
        torch.testing.assert_close(ctx[n], a @ keys[n, :L], atol=1e-6, rtol=1e-5)
        assert torch.all(w[n, L:] == 0)
    torch.manual_seed(0)
    gen = nb.LuongAttention(4, 6, "general")
    assert gen.W.weight.shape == (6, 4) and gen.W.bias is None
    q6 = torch.randn(3, 6, generator=torch.Generator().manual_seed(5))
    _, w = gen(q6, keys, mask)
    W = gen.W.weight.detach()
    a = torch.softmax(keys[0] @ W.T @ q6[0], 0)
    torch.testing.assert_close(w[0].detach(), a, atol=1e-6, rtol=1e-5)
    with pytest.raises(ValueError):
        nb.LuongAttention(4, 6, "dot")


def test_attention_gradient_ignores_padding(nb):
    keys, mask = make_keys(6)
    keys = keys.clone().requires_grad_(True)
    q = torch.randn(3, 4, generator=torch.Generator().manual_seed(7))
    ctx, _ = nb.LuongAttention(4, 4, "dot")(q, keys, mask)
    ctx.sum().backward()
    assert torch.all(keys.grad[1, 3:] == 0) and torch.all(keys.grad[2, 1:] == 0)


def toy_batch(seed: int):
    g = torch.Generator().manual_seed(seed)
    src = torch.randint(4, 12, (4, 7), generator=g)
    src_len = torch.tensor([7, 4, 2, 5])
    for i, L in enumerate(src_len):
        src[i, L:] = 0
    tgt = torch.randint(4, 12, (4, 6), generator=g)
    tgt[:, 0] = 2
    return src, src_len, tgt


@pytest.mark.parametrize("attn", ["none", "bahdanau", "luong"])
def test_forward_equals_stepwise(nb, attn):
    torch.manual_seed(0)
    model = nb.Seq2Seq(12, 13, emb=8, hidden=10, attn=attn).eval()
    src, src_len, tgt = toy_batch(1)
    with torch.no_grad():
        logits = model(src, src_len, tgt)
        keys, mask, s = model.encode(src, src_len)
        assert keys.shape == (4, 7, 20) and s.shape == (4, 10)
        # s0 = tanh(bridge([h_fwd sau token thật cuối; h_bwd sau khi đọc về token đầu]))
        last = keys[torch.arange(4), src_len - 1, :10]
        torch.testing.assert_close(s, torch.tanh(model.bridge(torch.cat([last, keys[:, 0, 10:]], -1))), atol=1e-6, rtol=1e-5)
        assert mask.tolist()[1] == [True] * 4 + [False] * 3
        steps = []
        for t in range(tgt.shape[1]):
            out, s, w = model.step(tgt[:, t], s, keys, mask)
            steps.append(out)
            if attn == "none":
                assert w is None
            else:
                assert w.shape == (4, 7) and torch.all(w[2, 2:] == 0)
    assert logits.shape == (4, 6, 13)
    torch.testing.assert_close(logits, torch.stack(steps, 1), atol=1e-5, rtol=1e-4,
                               msg="forward (teacher forcing) phải bằng gọi step lần lượt")


@pytest.mark.parametrize("attn", ["none", "luong"])
def test_encoder_ignores_padding(nb, attn):
    torch.manual_seed(0)
    model = nb.Seq2Seq(12, 13, emb=8, hidden=10, attn=attn).eval()
    src = torch.tensor([[5, 6, 7]])
    tgt = torch.tensor([[2, 8, 9]])
    padded = torch.zeros(2, 9, dtype=torch.long)
    padded[0, :3] = src[0]
    padded[1] = torch.randint(4, 12, (9,))
    with torch.no_grad():
        alone = model(src, torch.tensor([3]), tgt)
        together = model(padded, torch.tensor([3, 9]), torch.cat([tgt, tgt]))
    torch.testing.assert_close(together[0], alone[0], atol=1e-5, rtol=1e-4,
                               msg="encoder phải dùng pack_padded_sequence: câu ngắn không đọc padding")


def test_architecture_differences(nb):
    torch.manual_seed(0)
    b = nb.Seq2Seq(12, 13, emb=8, hidden=10, attn="bahdanau")
    assert isinstance(b.attn, nb.BahdanauAttention) and b.attn.W_q.weight.shape == (10, 10)
    l = nb.Seq2Seq(12, 13, emb=8, hidden=10, attn="luong")
    assert isinstance(l.attn, nb.LuongAttention) and l.attn.W.weight.shape == (10, 20)
    # Bahdanau: attention dùng state CŨ, nên weights của bước đầu chỉ phụ thuộc s0, không phụ thuộc y_prev
    src, src_len, _ = toy_batch(2)
    with torch.no_grad():
        keys, mask, s0 = b.eval().encode(src, src_len)
        _, _, w1 = b.step(torch.full((4,), 5), s0, keys, mask)
        _, _, w2 = b.step(torch.full((4,), 9), s0, keys, mask)
        torch.testing.assert_close(w1, w2, msg="Bahdanau tính attention từ s_{t-1}, trước khi đọc y_prev")
        keys, mask, s0 = l.eval().encode(src, src_len)
        _, _, w1 = l.step(torch.full((4,), 5), s0, keys, mask)
        _, _, w2 = l.step(torch.full((4,), 9), s0, keys, mask)
        assert not torch.allclose(w1, w2), "Luong tính attention từ s_t, sau khi GRU đọc y_prev"


def test_greedy_decode_stops_and_trims(nb):
    class Scripted(torch.nn.Module):
        """Model giả, sinh theo kịch bản cho trước, đếm số lần step."""

        def __init__(self, script):
            super().__init__()
            self.script, self.calls = script, 0

        def encode(self, src, src_len):
            return torch.zeros(2, 1, 1), torch.ones(2, 1, dtype=torch.bool), torch.zeros(2, 1)

        def step(self, y, s, keys, mask):
            t = int(s[0, 0])
            self.calls += 1
            logits = torch.zeros(2, 10)
            for row, seq in enumerate(self.script):
                logits[row, seq[t]] = 1
            return logits, s + 1, None

    always = Scripted([[7, 8, 3, 3, 3, 3], [9, 9, 9, 9, 9, 9]])
    out = nb.greedy_decode(always, torch.zeros(2, 1, dtype=torch.long), torch.tensor([1, 1]), max_len=5)
    assert out == [[7, 8], [9, 9, 9, 9, 9]] and always.calls == 5
    # câu 0 sinh <eos> ở bước 2 rồi sinh tiếp 8; câu 1 sinh <eos> ở bước 4: dừng sau đúng 4 bước
    late = Scripted([[7, 3, 8, 8, 8, 8, 8, 8], [9, 9, 9, 3, 9, 9, 9, 9]])
    out = nb.greedy_decode(late, torch.zeros(2, 1, dtype=torch.long), torch.tensor([1, 1]), max_len=8)
    assert out == [[7], [9, 9, 9]]
    assert late.calls == 4, "dừng khi MỌI câu đã từng sinh <eos> (cộng dồn), không chỉ ở bước hiện tại"


def test_learns_reverse_task(nb):
    torch.manual_seed(0)
    g = torch.Generator().manual_seed(0)
    model = nb.Seq2Seq(10, 10, emb=16, hidden=32, attn="luong")
    opt = torch.optim.Adam(model.parameters(), 5e-3)
    for _ in range(250):
        src, src_len, tgt = nb.reverse_batch(32, 8, 6, g)
        logits = model(src, src_len, tgt[:, :-1])
        loss = F.cross_entropy(logits.reshape(-1, 10), tgt[:, 1:].reshape(-1), ignore_index=0)
        opt.zero_grad()
        loss.backward()
        opt.step()
    src, src_len, tgt = nb.reverse_batch(200, 8, 6, g)
    pred = nb.greedy_decode(model, src, src_len, 10)
    gold = [t[1:t.index(3)] for t in tgt.tolist()]
    acc = np.mean([p == q for p, q in zip(pred, gold)])
    assert acc >= 0.8, f"đảo chuỗi dài tới 8: phải đúng >= 80% chuỗi, được {acc:.2f}"


def test_corpus_bleu(nb):
    refs = ["tôi rất tự hào về đất nước tôi .", "chúng tôi học về lịch sử ."]
    assert nb.corpus_bleu(refs, refs) == pytest.approx(100.0)
    hyps = ["tôi rất tự hào về đất nước của tôi .", "chúng tôi học lịch sử ."]
    assert nb.corpus_bleu(hyps, refs) == pytest.approx(64.39, abs=0.01)
    # tokenize="none": "tôi." và "tôi ." là token khác nhau (tokenizer 13a mặc định sẽ tách và cho 100)
    assert nb.corpus_bleu(["tôi rất tự hào về đất nước tôi ."], ["tôi rất tự hào về đất nước tôi."]) == \
        pytest.approx(72.60, abs=0.01)


def test_vocab_and_encode(nb):
    seqs = [["b", "a"], ["a", "c"], ["b", "x"]]
    itos = nb.build_vocab(seqs, 6)
    assert itos == ["<pad>", "<unk>", "<bos>", "<eos>", "a", "b"]
    assert nb.encode(["a", "zzz", "b"], {w: i for i, w in enumerate(itos)}) == [4, 1, 5]


# ---------- Dữ liệu thật: tự skip nếu chưa tải IWSLT'15 ----------

def test_read_parallel_real(nb):
    root = ex.dataset("iwslt15-en-vi")
    test = nb.read_parallel(root, "tst2013", max_len=None)
    assert len(test) == 1268
    assert test[1] == ("and i was very proud .".split(), "tôi đã rất tự hào về đất nước tôi .".split())
    short = nb.read_parallel(root, "tst2013", max_len=15)
    assert len(short) == 378, "giữ cặp mà CẢ HAI phía có 1 tới max_len token"
    assert all(1 <= len(s) <= 15 and 1 <= len(t) <= 15 for s, t in short)
    assert any("'" in w for s, _ in test for w in s), "html.unescape: &apos; thành '"

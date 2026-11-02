import pytest
import torch
import torch.nn.functional as F
from testkit import Exercise

ex = Exercise(__file__)
torch.set_num_threads(1)


@pytest.fixture(scope="module")
def nb():
    return ex.notebook("bert_gpt.ipynb")


def test_mlm_mask_statistics(nb):
    ids = torch.randint(0, 50, (400, 100), generator=torch.Generator().manual_seed(0))
    original = ids.clone()
    inputs, labels = nb.mlm_mask(ids, 0.15, 99, 50, torch.Generator().manual_seed(1))
    assert torch.equal(ids, original), "không sửa ids tại chỗ"
    selected = labels != -100
    assert selected.float().mean().item() == pytest.approx(0.15, abs=0.01)
    assert torch.equal(labels[selected], ids[selected])
    assert torch.equal(inputs[~selected], ids[~selected]), "vị trí không được chọn giữ nguyên"
    n = selected.sum().item()
    masked = (inputs[selected] == 99).sum().item() / n
    kept = (inputs[selected] == ids[selected]).sum().item() / n
    assert masked == pytest.approx(0.8, abs=0.02)
    assert kept == pytest.approx(0.1 + 0.1 / 50, abs=0.015), "10% giữ nguyên (cộng phần random trùng token cũ)"
    other = 1 - masked - kept
    assert other == pytest.approx(0.1 - 0.1 / 50, abs=0.015)
    assert inputs.max().item() <= 99 and inputs[selected & (inputs != 99)].max().item() < 50


def test_mlm_mask_uses_generator(nb):
    ids = torch.randint(0, 30, (8, 40), generator=torch.Generator().manual_seed(2))
    a = nb.mlm_mask(ids, 0.3, 31, 30, torch.Generator().manual_seed(5))
    torch.manual_seed(123)
    b = nb.mlm_mask(ids, 0.3, 31, 30, torch.Generator().manual_seed(5))
    assert torch.equal(a[0], b[0]) and torch.equal(a[1], b[1])


def test_attention_mask(nb):
    m = nb.attention_mask(4, causal=True)
    assert m.dtype == torch.bool
    assert m.tolist() == [[False, True, True, True], [False, False, True, True],
                          [False, False, False, True], [False, False, False, False]], "True = bị cấm"
    assert not nb.attention_mask(4, causal=False).any()


def make(nb, causal):
    torch.manual_seed(0)
    return nb.TinyTransformer(40, 16, 32, 2, 4, causal).eval()


def test_tiny_transformer_structure(nb):
    model = make(nb, causal=True)
    assert model.head.weight is model.tok_emb.weight, "head dùng chung trọng số với tok_emb"
    assert len(model.encoder.layers) == 2 and model.encoder.layers[0].norm_first
    assert model(torch.zeros(3, 10, dtype=torch.long)).shape == (3, 10, 40)


def test_causal_vs_bidirectional(nb):
    idx = torch.randint(0, 40, (2, 12), generator=torch.Generator().manual_seed(3))
    changed = idx.clone()
    changed[:, 8] = (changed[:, 8] + 1) % 40
    gpt, bert = make(nb, True), make(nb, False)
    with torch.no_grad():
        a, b = gpt(idx), gpt(changed)
        torch.testing.assert_close(a[:, :8], b[:, :8], msg="causal: vị trí < 8 không thấy token 8")
        a, b = bert(idx), bert(changed)
    assert not torch.allclose(a[:, :8], b[:, :8], atol=1e-6), "hai chiều: mọi vị trí thấy token 8"


def test_position_embedding_used(nb):
    bert = make(nb, False)
    with torch.no_grad():
        logits = bert(torch.full((1, 6), 7))
    assert not torch.allclose(logits[0, 0], logits[0, 5], atol=1e-5)


def test_losses_and_accuracy(nb):
    g = torch.Generator().manual_seed(4)
    logits = torch.randn(2, 5, 7, generator=g)
    ids = torch.randint(0, 7, (2, 5), generator=g)
    ref = F.cross_entropy(logits[:, :-1].reshape(-1, 7), ids[:, 1:].reshape(-1))
    torch.testing.assert_close(nb.lm_loss(logits, ids), ref, msg="logits vị trí t dự đoán token t + 1")
    labels = torch.full((2, 5), -100)
    labels[0, 1], labels[1, 3] = 2, 5
    ref = (F.cross_entropy(logits[0, 1][None], torch.tensor([2])) + F.cross_entropy(logits[1, 3][None], torch.tensor([5]))) / 2
    torch.testing.assert_close(nb.mlm_loss(logits, labels), ref)
    logits = torch.zeros(1, 4, 3)
    logits[0, 0, 1] = logits[0, 1, 2] = logits[0, 2, 0] = logits[0, 3, 1] = 5.0
    labels = torch.tensor([[1, -100, 1, 1]])
    assert nb.masked_accuracy(logits, labels) == pytest.approx(2 / 3)
    assert isinstance(nb.masked_accuracy(logits, labels), float)


def test_learns_to_fill(nb):
    torch.manual_seed(5)
    model = nb.TinyTransformer(12, 8, 32, 2, 4, causal=False)
    opt = torch.optim.AdamW(model.parameters(), lr=3e-3)
    g = torch.Generator().manual_seed(6)
    for _ in range(150):
        a = torch.randint(0, 10, (32, 1), generator=g)
        ids = torch.cat([a, (a + 1) % 10, a, (a + 1) % 10, a, (a + 1) % 10, a, (a + 1) % 10], dim=1)
        inputs, labels = nb.mlm_mask(ids, 0.25, 11, 10, g)
        loss = nb.mlm_loss(model(inputs), labels)
        opt.zero_grad()
        loss.backward()
        opt.step()
    model.eval()
    ids = torch.tensor([[3, 4, 3, 4, 3, 4, 3, 4]])
    masked = ids.clone()
    masked[0, 4] = 11
    with torch.no_grad():
        assert model(masked)[0, 4].argmax().item() == 3

import math

import pytest
import torch
import torch.nn.functional as F
from testkit import Exercise

ex = Exercise(__file__)
torch.set_num_threads(1)


@pytest.fixture(scope="module")
def G():
    return ex.module("gpt.py")


def tiny(G, **kw):
    cfg = dict(vocab_size=50, block_size=16, n_layer=2, n_head=4, n_embd=32)
    cfg.update(kw)
    torch.manual_seed(0)
    return G.GPT(G.GPTConfig(**cfg)).eval()


def test_layernorm_matches_torch(G):
    torch.manual_seed(1)
    ln = G.LayerNorm(12)
    assert {n for n, _ in ln.named_parameters()} == {"weight", "bias"}
    with torch.no_grad():
        ln.weight.copy_(torch.linspace(0.5, 1.5, 12))
        ln.bias.copy_(torch.linspace(-1, 1, 12))
    x = torch.randn(3, 4, 12) * 5 + 2
    ref = F.layer_norm(x, (12,), ln.weight, ln.bias, eps=1e-5)
    torch.testing.assert_close(ln(x), ref, atol=1e-5, rtol=1e-5, msg="phương sai lệch (chia D), eps trong căn")
    flat = torch.randn(2, 12) * 1e-3
    ref = F.layer_norm(flat, (12,), ln.weight, ln.bias, eps=1e-5)
    torch.testing.assert_close(ln(flat), ref, atol=1e-4, rtol=1e-4, msg="eps cộng vào phương sai, bên trong căn")


def test_attention_matches_sdpa(G):
    cfg = G.GPTConfig(vocab_size=10, block_size=12, n_layer=1, n_head=4, n_embd=32)
    torch.manual_seed(2)
    attn = G.CausalSelfAttention(cfg).eval()
    x = torch.randn(2, 9, 32)
    B, T, C = x.shape
    q, k, v = attn.qkv(x).split(C, dim=2)
    q, k, v = (t.view(B, T, 4, 8).transpose(1, 2) for t in (q, k, v))
    ref = attn.proj(F.scaled_dot_product_attention(q, k, v, is_causal=True).transpose(1, 2).reshape(B, T, C))
    torch.testing.assert_close(attn(x), ref, atol=1e-5, rtol=1e-4)


def test_attention_mask_is_buffer_not_state(G):
    cfg = G.GPTConfig(vocab_size=10, block_size=12, n_layer=1, n_head=2, n_embd=16)
    attn = G.CausalSelfAttention(cfg)
    assert len(list(attn.buffers())) >= 1, "mask nhân quả là buffer (đi theo .to(device))"
    assert set(attn.state_dict()) == {"qkv.weight", "qkv.bias", "proj.weight", "proj.bias"}, \
        "mask không nằm trong state_dict (persistent=False)"


def test_block_is_pre_norm(G):
    cfg = G.GPTConfig(vocab_size=10, block_size=12, n_layer=1, n_head=2, n_embd=16)
    torch.manual_seed(11)
    block = G.Block(cfg).eval()
    with torch.no_grad():
        block.ln1.bias.normal_()
        block.ln2.weight.normal_()
    x = torch.randn(2, 5, 16) * 3
    h = x + block.attn(block.ln1(x))
    torch.testing.assert_close(block(x), h + block.mlp(block.ln2(h)), atol=1e-5, rtol=1e-4)


def test_model_is_causal(G):
    model = tiny(G)
    idx = torch.randint(0, 50, (2, 12), generator=torch.Generator().manual_seed(3))
    changed = idx.clone()
    changed[:, 7] = (changed[:, 7] + 1) % 50
    a, _ = model(idx)
    b, _ = model(changed)
    torch.testing.assert_close(a[:, :7], b[:, :7], msg="logits ở vị trí < 7 không được phụ thuộc token 7")
    assert not torch.allclose(a[:, 7:], b[:, 7:])


def test_position_matters(G):
    model = tiny(G)
    logits, _ = model(torch.tensor([[5, 5, 5, 5, 5, 5]]))
    assert not torch.allclose(logits[0, 0], logits[0, 5], atol=1e-4), \
        "thiếu position embedding: chuỗi toàn một token cho cùng logits ở mọi vị trí"


def test_param_count_and_tying(G):
    model = tiny(G)
    assert model.lm_head.weight is model.tok_emb.weight, "weight tying: lm_head dùng chung tensor với tok_emb"
    d, L, V, T = 32, 2, 50, 16
    per_block = 2 * 2 * d + (d * 3 * d + 3 * d) + (d * d + d) + (d * 4 * d + 4 * d) + (4 * d * d + d)
    expected = V * d + T * d + L * per_block + 2 * d
    assert model.num_params() == expected
    assert model.num_params(non_embedding=True) == expected - V * d - T * d


def test_init(G):
    model = tiny(G, vocab_size=500, n_embd=64, n_head=4, n_layer=4)
    assert model.tok_emb.weight.std().item() == pytest.approx(0.02, rel=0.1)
    assert model.blocks[0].attn.qkv.weight.std().item() == pytest.approx(0.02, rel=0.1)
    target = 0.02 / math.sqrt(2 * 4)
    assert model.blocks[1].attn.proj.weight.std().item() == pytest.approx(target, rel=0.1)
    assert model.blocks[2].mlp.proj.weight.std().item() == pytest.approx(target, rel=0.1)
    assert torch.all(model.blocks[0].mlp.fc.bias == 0)
    idx = torch.randint(0, 500, (4, 16), generator=torch.Generator().manual_seed(4))
    targets = torch.randint(0, 500, (4, 16), generator=torch.Generator().manual_seed(40))
    _, loss = model(idx, targets)
    assert loss.item() == pytest.approx(math.log(500), abs=0.15), "khởi tạo nhỏ: loss ban đầu ≈ ln(vocab)"


def test_forward_shapes_loss_and_ignore(G):
    model = tiny(G)
    idx = torch.randint(0, 50, (3, 10), generator=torch.Generator().manual_seed(5))
    targets = torch.randint(0, 50, (3, 10), generator=torch.Generator().manual_seed(6))
    logits, loss = model(idx, targets)
    assert logits.shape == (3, 10, 50)
    torch.testing.assert_close(loss, F.cross_entropy(logits.reshape(-1, 50), targets.reshape(-1)))
    logits, none = model(idx)
    assert none is None
    masked = targets.clone()
    masked[:, :4] = -1
    _, loss2 = model(idx, masked)
    torch.testing.assert_close(loss2, F.cross_entropy(logits[:, 4:].reshape(-1, 50), targets[:, 4:].reshape(-1)))
    with pytest.raises(ValueError):
        model(torch.zeros(1, 17, dtype=torch.long))


def test_overfits_tiny_sequence(G):
    torch.manual_seed(7)
    model = G.GPT(G.GPTConfig(vocab_size=20, block_size=16, n_layer=2, n_head=2, n_embd=32)).train()
    seq = torch.tensor([[3, 1, 4, 1, 5, 9, 2, 6, 5, 3, 5, 8, 9, 7, 9, 3, 2]])
    x, y = seq[:, :-1], seq[:, 1:]
    opt = torch.optim.AdamW(model.parameters(), lr=3e-3)
    for _ in range(150):
        _, loss = model(x, y)
        opt.zero_grad()
        loss.backward()
        opt.step()
    assert loss.item() < 0.05


def test_generate_greedy_and_crop(G):
    model = tiny(G, block_size=8)
    model.train()
    start = torch.tensor([[1, 2, 3]])
    out = model.generate(start, 10, temperature=0)
    assert out.shape == (1, 13) and torch.equal(out[:, :3], start)
    assert model.training, "generate trả lại chế độ train như trước khi gọi"
    lengths = []
    handle = model.tok_emb.register_forward_hook(lambda m, i, o: lengths.append(i[0].shape[1]) and None)
    model.generate(start, 7, temperature=0)
    handle.remove()
    assert lengths == [3, 4, 5, 6, 7, 8, 8], "mỗi bước đưa vào tối đa block_size token cuối"
    model.eval()
    idx = start
    for _ in range(10):
        logits, _ = model(idx[:, -8:])
        idx = torch.cat([idx, logits[:, -1].argmax(-1, keepdim=True)], dim=1)
    assert torch.equal(out, idx), "mỗi bước chỉ đưa block_size token cuối vào model"


def test_generate_sampling(G):
    model = tiny(G)
    start = torch.tensor([[1, 2]])
    a = model.generate(start, 8, temperature=1.0, generator=torch.Generator().manual_seed(9))
    b = model.generate(start, 8, temperature=1.0, generator=torch.Generator().manual_seed(9))
    assert torch.equal(a, b), "chỉ dùng generator truyền vào"
    greedy = model.generate(start, 8, temperature=0)
    assert torch.equal(model.generate(start, 8, temperature=0.7, top_k=1, generator=torch.Generator()), greedy)


def test_hooks_see_named_submodules(G):
    model = tiny(G)
    seen = {}

    def record(name):
        def hook(module, inputs, output):
            seen[name] = tuple(output.shape)
        return hook

    handles = [model.blocks[1].attn.register_forward_hook(record("attn")),
               model.blocks[1].mlp.register_forward_hook(record("mlp")),
               model.ln_f.register_forward_hook(record("ln_f"))]
    model(torch.tensor([[1, 2, 3, 4]]))
    for h in handles:
        h.remove()
    assert seen == {"attn": (1, 4, 32), "mlp": (1, 4, 32), "ln_f": (1, 4, 32)}

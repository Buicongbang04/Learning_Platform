import importlib.util
import sys

import pytest
import torch
import torch.nn.functional as F
from testkit import ROOT, Exercise

ex = Exercise(__file__)
torch.set_num_threads(1)
GPT_FILE = ROOT / "tracks/ai-engineer/modules/05-transformers-llm-architecture/solutions/basic/01-gpt-mini/gpt.py"


@pytest.fixture(scope="module")
def nb():
    return ex.notebook("sae.ipynb")


@pytest.fixture(scope="module")
def G():
    spec = importlib.util.spec_from_file_location("m08_i03_gpt", GPT_FILE)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def tiny(G, seed=0):
    torch.manual_seed(seed)
    return G.GPT(G.GPTConfig(vocab_size=20, block_size=10, n_layer=2, n_head=2, n_embd=8)).eval()


def test_init(nb):
    sae = nb.SparseAutoencoder(6, 15, seed=3)
    params = dict(sae.named_parameters())
    assert set(params) == {"W_enc", "W_dec", "b_enc", "b_dec"}
    assert sae.W_dec.shape == (15, 6) and sae.W_enc.shape == (6, 15)
    torch.testing.assert_close(sae.W_dec.norm(dim=1), torch.ones(15))
    torch.testing.assert_close(sae.W_enc.detach(), sae.W_dec.detach().T)
    assert sae.W_enc.data_ptr() != sae.W_dec.data_ptr(), "W_enc là bản sao, không dùng chung bộ nhớ"
    W = torch.randn(15, 6, generator=torch.Generator().manual_seed(3))
    torch.testing.assert_close(sae.W_dec.detach(), W / W.norm(dim=1, keepdim=True))
    assert torch.all(sae.b_enc == 0) and torch.all(sae.b_dec == 0)


def test_encode_relu_and_bias_subtraction(nb):
    sae = nb.SparseAutoencoder(4, 7, seed=0)
    with torch.no_grad():
        sae.b_enc.copy_(torch.linspace(-0.5, 0.5, 7))
        sae.b_dec.copy_(torch.tensor([1.0, -2.0, 0.5, 3.0]))
    x = torch.randn(5, 4, generator=torch.Generator().manual_seed(1))
    f = sae.encode(x)
    ref = F.relu((x - sae.b_dec) @ sae.W_enc + sae.b_enc)
    torch.testing.assert_close(f, ref)
    shift = torch.tensor([0.3, 0.1, -0.7, 2.0])
    with torch.no_grad():
        sae.b_dec.add_(shift)
    torch.testing.assert_close(sae.encode(x + shift), f, atol=1e-5, rtol=1e-5, msg="encoder trừ b_dec trước khi nhân W_enc")


def test_encode_topk(nb):
    sae = nb.SparseAutoencoder(5, 12, k=3, seed=0)
    with torch.no_grad():
        sae.b_enc.copy_(torch.linspace(-1, 1, 12))
    x = torch.randn(20, 5, generator=torch.Generator().manual_seed(2)) * 2
    f = sae.encode(x)
    pre = (x - sae.b_dec) @ sae.W_enc + sae.b_enc
    assert ((f > 0).sum(-1) <= 3).all()
    v, i = pre.topk(3, dim=-1)
    ref = torch.zeros_like(pre).scatter(-1, i, F.relu(v))
    torch.testing.assert_close(f, ref, msg="giữ k giá trị pre lớn nhất (qua ReLU), còn lại 0")


def test_decode_forward_loss(nb):
    sae = nb.SparseAutoencoder(4, 9, l1_coeff=0.3, seed=1)
    with torch.no_grad():
        sae.W_dec.mul_(torch.linspace(0.5, 2.0, 9).unsqueeze(1))
        sae.b_dec.copy_(torch.tensor([0.2, -0.1, 0.0, 0.4]))
        sae.b_enc.fill_(0.1)
    x = torch.randn(6, 4, generator=torch.Generator().manual_seed(3))
    x_hat, f = sae(x)
    torch.testing.assert_close(x_hat, f @ sae.W_dec + sae.b_dec)
    loss, info = sae.loss(x)
    mse = (x_hat - x).pow(2).sum(-1).mean()
    l1 = (f * sae.W_dec.norm(dim=1)).sum(-1).mean()
    torch.testing.assert_close(loss, mse + 0.3 * l1, msg="mse: tổng theo chiều, trung bình theo hàng; L1 nhân norm hàng decoder")
    assert set(info) == {"mse", "l1", "l0"} and all(isinstance(v, float) for v in info.values())
    assert info["l0"] == pytest.approx((f > 0).float().sum(-1).mean().item())
    loss.backward()
    assert sae.W_enc.grad is not None and sae.b_dec.grad is not None


def test_normalize_decoder(nb):
    sae = nb.SparseAutoencoder(3, 5, seed=0)
    with torch.no_grad():
        sae.W_dec.mul_(torch.tensor([[2.0], [0.5], [3.0], [1.0], [10.0]]))
    before = sae.W_dec.detach().clone()
    ptr = sae.W_dec.data_ptr()
    sae.normalize_decoder_()
    torch.testing.assert_close(sae.W_dec.norm(dim=1), torch.ones(5))
    torch.testing.assert_close(sae.W_dec.detach(), before / before.norm(dim=1, keepdim=True))
    assert sae.W_dec.data_ptr() == ptr, "chuẩn hoá tại chỗ"


def test_activation_scale(nb):
    x = torch.randn(1000, 16, generator=torch.Generator().manual_seed(4)) * 7
    c = nb.activation_scale(x.half())
    assert isinstance(c, float)
    assert (c * x).pow(2).sum(1).mean().item() == pytest.approx(16, rel=1e-2)


def toy(n, seed=0):
    g = torch.Generator().manual_seed(seed)
    dirs = torch.randn(30, 10, generator=g)
    dirs /= dirs.norm(dim=1, keepdim=True)
    active = (torch.rand(n, 30, generator=g) < 0.05).float() * (0.5 + torch.rand(n, 30, generator=g))
    return active @ dirs, dirs


def test_train_sae_recovers_superposed_features(nb):
    X, dirs = toy(20000)
    sae = nb.SparseAutoencoder(10, 60, k=3, seed=0)
    hist = nb.train_sae(sae, X, steps=1500, batch_size=256, lr=3e-3)
    assert len(hist) == 1500 and all(isinstance(h, float) for h in hist[:3])
    assert sum(hist[-100:]) < 0.5 * sum(hist[:100])
    torch.testing.assert_close(sae.W_dec.norm(dim=1), torch.ones(60), msg="decoder chuẩn hoá sau mỗi bước")
    cos = (dirs @ sae.W_dec.detach().T).max(dim=1).values
    assert cos.mean() > 0.9, f"SAE TopK phải tìm lại các hướng thật (cosine trung bình {cos.mean():.3f})"


def test_train_sae_reproducible_and_uses_scale(nb):
    X, _ = toy(2000, seed=1)
    a = nb.SparseAutoencoder(10, 20, k=2, seed=0)
    b = nb.SparseAutoencoder(10, 20, k=2, seed=0)
    ha = nb.train_sae(a, X, steps=30, batch_size=64, lr=1e-3, scale=2.0, seed=5)
    hb = nb.train_sae(b, X * 2.0, steps=30, batch_size=64, lr=1e-3, scale=1.0, seed=5)
    assert ha == pytest.approx(hb, rel=1e-4), "x = acts[idx] * scale, cùng chỉ số batch với cùng seed"


def test_train_sae_lr_schedule(nb):
    X, _ = toy(500, seed=2)
    sae = nb.SparseAutoencoder(10, 20, k=2, seed=0)
    seen = []
    original = torch.optim.Adam.step

    def spy(self, *args, **kwargs):
        seen.append(self.param_groups[0]["lr"])
        return original(self, *args, **kwargs)

    torch.optim.Adam.step = spy
    try:
        nb.train_sae(sae, X, steps=10, batch_size=16, lr=0.01)
    finally:
        torch.optim.Adam.step = original
    assert seen[:8] == pytest.approx([0.01] * 8)
    assert seen[8] == pytest.approx(0.01) and seen[9] == pytest.approx(0.005), "giảm tuyến tính về 0 trong 20% bước cuối"


def test_sae_metrics(nb):
    sae = nb.SparseAutoencoder(4, 4, seed=0)
    with torch.no_grad():
        sae.W_dec.copy_(torch.eye(4))
        sae.W_enc.copy_(torch.eye(4))
        sae.b_enc.copy_(torch.tensor([0.0, 0.0, 0.0, -100.0]))
    x = torch.rand(50, 4, generator=torch.Generator().manual_seed(5))
    x[:, 3] = 0
    x[1:, 2] = 0
    m = nb.sae_metrics(sae, x, batch_size=7)
    assert m["fvu"] == pytest.approx(0.0, abs=1e-6)
    assert m["dead_frac"] == pytest.approx(0.25), "latent 3 không bao giờ bật; latent 2 chỉ bật ở hàng đầu vẫn là sống"
    assert m["l0"] == pytest.approx(2.02)
    with torch.no_grad():
        sae.W_dec.zero_()
        sae.b_dec.copy_(x.mean(0))
    m = nb.sae_metrics(sae, x, batch_size=8)
    assert m["fvu"] == pytest.approx(1.0, rel=1e-4), "FVU so với phương sai quanh trung bình, không phải quanh 0"
    m2 = nb.sae_metrics(sae, x / 3, scale=3.0, batch_size=50)
    assert m2["fvu"] == pytest.approx(1.0, rel=1e-3)


def test_collect_resid_pre(nb, G):
    model = tiny(G)
    ctx = torch.randint(20, (5, 7), generator=torch.Generator().manual_seed(6))
    store = {}
    h = model.blocks[1].register_forward_pre_hook(lambda m, a: store.__setitem__("x", a[0].detach()))
    with torch.no_grad():
        model(ctx)
    h.remove()
    out = nb.collect_resid_pre(model, ctx, 1, batch_size=2)
    assert out.dtype == torch.float16 and out.shape == (5 * 6, 8)
    torch.testing.assert_close(out.float(), store["x"][:, 1:].reshape(-1, 8), atol=2e-3, rtol=2e-3,
                               msg="stream trước ln1 của Block, bỏ vị trí 0, xếp theo ngữ cảnh rồi vị trí")
    assert sum(len(m._forward_pre_hooks) for m in model.modules()) == 0


def test_sae_splice(nb, G):
    model = tiny(G)
    ctx = torch.randint(20, (2, 6), generator=torch.Generator().manual_seed(7))
    with torch.no_grad():
        clean, _ = model(ctx)
    zero = nb.SparseAutoencoder(8, 8, seed=0)
    with torch.no_grad():
        zero.W_dec.zero_()
    store = {}
    h = model.blocks[1].ln1.register_forward_pre_hook(lambda m, a: store.__setitem__("x", a[0].detach().clone()))
    with torch.no_grad(), nb.sae_splice(model, 1, zero, 2.0):
        out, _ = model(ctx)
    h.remove()
    assert not torch.allclose(out, clean), "stream bị thay bằng bản tái dựng"
    assert torch.all(store["x"][:, 1:] == 0), "vị trí 1 trở đi thay bằng x_hat / scale"
    assert not torch.all(store["x"][:, 0] == 0), "vị trí 0 giữ nguyên"
    with torch.no_grad():
        after, _ = model(ctx)
    torch.testing.assert_close(after, clean, msg="gỡ hook khi ra khỏi khối with")


def test_sae_splice_scale_roundtrip(nb, G):
    model = tiny(G)
    ctx = torch.randint(20, (2, 6), generator=torch.Generator().manual_seed(8))
    with torch.no_grad():
        clean, _ = model(ctx)
    ident = nb.SparseAutoencoder(8, 16, seed=0)
    with torch.no_grad():
        ident.W_enc.zero_()
        ident.W_enc[:, :8].copy_(torch.eye(8))
        ident.W_enc[:, 8:].copy_(-torch.eye(8))
        ident.W_dec.zero_()
        ident.W_dec[:8].copy_(torch.eye(8))
        ident.W_dec[8:].copy_(-torch.eye(8))
    with torch.no_grad(), nb.sae_splice(model, 0, ident, 3.7):
        out, _ = model(ctx)
    torch.testing.assert_close(out, clean, atol=1e-5, rtol=1e-5, msg="SAE tái dựng hoàn hảo thì logits không đổi (nhân rồi chia scale)")


def test_ce_loss_recovered(nb):
    assert nb.ce_loss_recovered(3.0, 3.0, 10.0) == pytest.approx(1.0)
    assert nb.ce_loss_recovered(3.0, 10.0, 10.0) == pytest.approx(0.0)
    assert nb.ce_loss_recovered(3.0, 3.7, 10.0) == pytest.approx(0.9)

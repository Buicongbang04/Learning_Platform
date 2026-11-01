import importlib.util
import sys

import pytest
import torch

from testkit import ROOT, Exercise

ex = Exercise(__file__)
torch.set_num_threads(1)


@pytest.fixture(scope="module")
def nb():
    return ex.notebook("gptq_awq.ipynb")


@pytest.fixture(scope="module")
def gpt_mini():
    path = ROOT / "tracks/ai-engineer/modules/05-transformers-llm-architecture/solutions/basic/01-gpt-mini/gpt.py"
    spec = importlib.util.spec_from_file_location("m10_test_gpt_mini_02", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def tiny_gpt(gpt_mini):
    torch.manual_seed(0)
    return gpt_mini.GPT(gpt_mini.GPTConfig(vocab_size=50, block_size=16, n_layer=2, n_head=2, n_embd=32)).eval()


def correlated(n=512, d=32, seed=0):
    g = torch.Generator().manual_seed(seed)
    base = torch.randn(n, 4, generator=g)
    return base @ torch.randn(4, d, generator=g) + 0.1 * torch.randn(n, d, generator=g)


def test_capture_inputs(nb, gpt_mini):
    model = tiny_gpt(gpt_mini)
    names = ["blocks.0.attn.qkv", "blocks.1.mlp.proj"]
    batches = [torch.randint(0, 50, (2, 16)), torch.randint(0, 50, (3, 16))]
    outs = {n: [] for n in names}
    hooks = [model.get_submodule(n).register_forward_hook(lambda m, i, o, n=n: outs[n].append(o.reshape(-1, o.shape[-1])))
             for n in names]
    inputs = nb.capture_inputs(model, batches, names)
    for h in hooks:
        h.remove()
    assert set(inputs) == set(names)
    assert inputs["blocks.0.attn.qkv"].shape == (80, 32) and inputs["blocks.1.mlp.proj"].shape == (80, 128)
    assert inputs["blocks.0.attn.qkv"].dtype == torch.float32
    for n in names:
        layer = model.get_submodule(n)
        with torch.no_grad():
            torch.testing.assert_close(layer(inputs[n]), torch.cat(outs[n]), atol=1e-5, rtol=1e-5)
    assert all(len(model.get_submodule(n)._forward_hooks) == 0 for n in names), "phải gỡ hook"


def test_hessian(nb):
    X = torch.tensor([[1.0, 2.0], [3.0, 0.0]])
    H = nb.hessian(X, damp=0.0)
    assert H.dtype == torch.float64
    torch.testing.assert_close(H, torch.tensor([[10.0, 2.0], [2.0, 4.0]], dtype=torch.float64))
    Hd = nb.hessian(X, damp=0.1)
    torch.testing.assert_close(Hd, torch.tensor([[10.7, 2.0], [2.0, 4.7]], dtype=torch.float64))


def test_identity_hessian_equals_rtn(nb):
    torch.manual_seed(0)
    W = torch.randn(16, 64)
    for sym in (True, False):
        q = nb.gptq_quantize(W, torch.eye(64, dtype=torch.float64), 4, 16, sym)
        assert q.dtype == W.dtype and q.shape == W.shape
        torch.testing.assert_close(q, nb.rtn_quantize(W, 4, 16, sym), atol=1e-6, rtol=0)


def test_error_compensation_order_and_sign(nb):
    W = torch.tensor([[0.26, 0.46, 0.7]])
    H = torch.tensor([[1.0, 0.5, 0.0], [0.5, 1.0, 0.0], [0.0, 0.0, 1.0]], dtype=torch.float64)
    W_before = W.clone()
    q = nb.gptq_quantize(W, H, 4, 3)
    torch.testing.assert_close(q, torch.tensor([[0.3, 0.4, 0.7]]), atol=1e-6, rtol=0)
    assert torch.equal(W, W_before), "không sửa W đầu vào"
    torch.testing.assert_close(nb.rtn_quantize(W, 4, 3), torch.tensor([[0.3, 0.5, 0.7]]), atol=1e-6, rtol=0)


def test_group_params_use_updated_weights(nb):
    W = torch.tensor([[0.7, 0.26, 0.33, 0.72]])
    H = torch.eye(4, dtype=torch.float64)
    H[1, 3] = H[3, 1] = 0.5
    q = nb.gptq_quantize(W, H, 4, 2)
    torch.testing.assert_close(q, torch.tensor([[0.7, 0.3, 0.3, 0.7]]), atol=1e-6, rtol=0)


def test_gptq_lowers_output_error(nb):
    torch.manual_seed(1)
    X = correlated()
    W = torch.randn(24, 32)
    ref = X @ W.T
    e_rtn = ((X @ nb.rtn_quantize(W, 3, 16).T - ref) ** 2).mean()
    e_gptq = ((X @ nb.gptq_quantize(W, nb.hessian(X), 3, 16).T - ref) ** 2).mean()
    assert e_gptq < 0.6 * e_rtn


def test_awq_scales(nb):
    m = torch.tensor([1.0, 4.0, 16.0, 0.0])
    s = nb.awq_scales(m, 0.5)
    raw = torch.tensor([1.0, 2.0, 4.0, 1e-5 ** 0.5])
    torch.testing.assert_close(s, raw / torch.sqrt(raw.max() * raw.min()))
    torch.testing.assert_close(nb.awq_scales(m, 0.0), torch.ones(4))


def test_awq_grid_and_rtn_fallback(nb):
    torch.manual_seed(2)
    W, X = torch.randn(8, 32), torch.randn(256, 32)
    q, alpha = nb.awq_quantize(W, X, 4, 16, n_grid=1)
    assert alpha == 0.0
    torch.testing.assert_close(q, nb.rtn_quantize(W, 4, 16), atol=1e-6, rtol=0)


def test_awq_protects_salient_channels(nb):
    torch.manual_seed(3)
    X = torch.randn(512, 64) * 0.1
    X[:, :4] *= 100
    W = torch.randn(32, 64)
    ref = X @ W.T
    q, alpha = nb.awq_quantize(W, X, 3, 64, n_grid=10)
    e_rtn = ((X @ nb.rtn_quantize(W, 3, 64).T - ref) ** 2).mean()
    e_awq = ((X @ q.T - ref) ** 2).mean()
    assert alpha > 0 and e_awq < 0.5 * e_rtn
    assert alpha in [i / 10 for i in range(10)]


def test_apply_layerwise(nb, gpt_mini):
    model = tiny_gpt(gpt_mini)
    before = {k: v.clone() for k, v in model.state_dict().items()}
    names = ["blocks.0.mlp.fc", "blocks.1.attn.proj"]
    inputs = {n: torch.ones(3, model.get_submodule(n).in_features) for n in names}
    seen = []

    def fn(name, W, X):
        seen.append((name, tuple(W.shape), tuple(X.shape)))
        return torch.full_like(W, 0.5)

    q = nb.apply_layerwise(model, inputs, fn)
    assert sorted(seen) == sorted([("blocks.0.mlp.fc", (128, 32), (3, 32)), ("blocks.1.attn.proj", (32, 32), (3, 32))])
    for n in names:
        assert torch.all(q.get_submodule(n).weight == 0.5)
    assert torch.equal(q.blocks[0].attn.qkv.weight, model.blocks[0].attn.qkv.weight)
    assert q.lm_head.weight is q.tok_emb.weight
    for k, v in model.state_dict().items():
        assert torch.equal(v, before[k])


def naive_obs(nb, W, H, bits, group_size):
    """Tham chiếu chậm: ở mỗi bước nghịch đảo lại Hessian của các cột còn tự do (Optimal Brain Surgeon trực tiếp)."""
    W = W.double().clone()
    Q = torch.zeros_like(W)
    scale = zero = None
    for j in range(W.shape[1]):
        if j % group_size == 0:
            scale, zero = nb.quant_params(W[:, j:j + group_size], bits, True)
        Q[:, j] = nb.quant_column(W[:, j], scale, zero, bits)
        Hinv = torch.linalg.inv(H[j:, j:])
        err = (W[:, j] - Q[:, j]) / Hinv[0, 0]
        W[:, j:] -= err[:, None] * Hinv[0, :][None, :]
    return Q.float()


def test_dense_hessian_matches_naive_obs(nb):
    g = torch.Generator().manual_seed(5)
    for n, gs in [(4, 2), (6, 3), (6, 6)]:
        A = torch.randn(n, n, generator=g, dtype=torch.float64)
        H = A @ A.T + torch.eye(n, dtype=torch.float64)
        W = torch.randn(5, n, generator=g)
        torch.testing.assert_close(nb.gptq_quantize(W, H, 3, gs), naive_obs(nb, W, H, 3, gs), atol=1e-5, rtol=0)


def test_awq_uses_mean_abs_activation(nb):
    torch.manual_seed(6)
    W = torch.randn(8, 16)
    X = torch.randn(300, 16) * torch.linspace(0.1, 3, 16)
    X[0, 0] = 400.0
    q, alpha = nb.awq_quantize(W, X, 3, 16, n_grid=4)
    m = X.abs().mean(dim=0)
    ref = X @ W.T
    best = None
    for i in range(4):
        s = nb.awq_scales(m, i / 4)
        Wq = nb.rtn_quantize(W * s, 3, 16) / s
        err = ((X @ Wq.T - ref) ** 2).mean().item()
        if best is None or err < best[0]:
            best = (err, i / 4, Wq)
    assert alpha == best[1], "scale theo trung bình |x| của từng kênh, không theo max"
    torch.testing.assert_close(q, best[2], atol=1e-5, rtol=0)


def test_awq_tie_keeps_smallest_alpha(nb):
    torch.manual_seed(7)
    X = torch.where(torch.rand(200, 8) < 0.5, -1.0, 1.0)
    X[::2, 0] = 0.0
    X[1::2, 0] = 2.0
    W = torch.randn(4, 8)
    _, alpha = nb.awq_quantize(W, X, 4, 8, n_grid=5)
    assert alpha == 0.0, "mọi kênh cùng trung bình |x| nên mọi alpha cho cùng sai số: hoà thì giữ alpha nhỏ nhất"

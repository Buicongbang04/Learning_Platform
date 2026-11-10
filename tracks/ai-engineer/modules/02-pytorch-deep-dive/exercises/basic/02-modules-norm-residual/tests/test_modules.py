import pytest
import torch
import torch.nn.functional as F
from torch import nn

from testkit import Exercise

ex = Exercise(__file__)
torch.set_num_threads(1)


@pytest.fixture(scope="module")
def m():
    return ex.module("modules.py")


def gen(seed: int) -> torch.Generator:
    return torch.Generator().manual_seed(seed)


# ---------- RMSNorm ----------

def test_rmsnorm_matches_torch(m):
    norm = m.RMSNorm(16, eps=1e-6)
    assert isinstance(norm.weight, nn.Parameter) and torch.equal(norm.weight.data, torch.ones(16))
    with torch.no_grad():
        norm.weight.copy_(torch.rand(16, generator=gen(0)) + 0.5)
    ref = nn.RMSNorm(16, eps=1e-6)
    ref.load_state_dict(norm.state_dict())
    x = 3 + 5 * torch.randn(4, 7, 16, generator=gen(1))
    torch.testing.assert_close(norm(x), ref(x), rtol=1e-5, atol=1e-6)


def test_rmsnorm_eps_and_scale(m):
    x = torch.zeros(2, 8)
    assert torch.isfinite(m.RMSNorm(8)(x)).all(), "eps tránh chia 0"
    a = torch.randn(3, 8, generator=gen(2))
    norm = m.RMSNorm(8)
    torch.testing.assert_close(norm(10 * a), norm(a), rtol=1e-4, atol=1e-5)  # bất biến khi nhân hằng dương
    torch.testing.assert_close(norm(a).pow(2).mean(-1), torch.ones(3), rtol=1e-4, atol=1e-4)


def test_rmsnorm_keeps_dtype_and_grads(m):
    norm = m.RMSNorm(8)
    x = torch.randn(2, 8, generator=gen(3)).bfloat16()
    assert norm(x).dtype == torch.bfloat16
    x64 = torch.randn(3, 8, dtype=torch.float64, generator=gen(4), requires_grad=True)
    norm64 = m.RMSNorm(8).double()
    assert torch.autograd.gradcheck(norm64, (x64,))


# ---------- group_norm ----------

@pytest.mark.parametrize("groups", [1, 2, 4, 8])
def test_group_norm_matches_torch(m, groups):
    x = 2 + 3 * torch.randn(3, 8, 5, 6, generator=gen(5))
    w, b = torch.rand(8, generator=gen(6)) + 0.5, torch.randn(8, generator=gen(7))
    torch.testing.assert_close(m.group_norm(x, groups, w, b), F.group_norm(x, groups, w, b), rtol=1e-5, atol=1e-5)


def test_group_norm_special_cases(m):
    x = torch.randn(2, 6, 4, 4, generator=gen(8))
    torch.testing.assert_close(m.group_norm(x, 1), F.layer_norm(x, x.shape[1:]), rtol=1e-5, atol=1e-5)
    torch.testing.assert_close(m.group_norm(x, 6), F.instance_norm(x), rtol=1e-5, atol=1e-5)
    seq = torch.randn(2, 6, 9, generator=gen(9))                      # (N, C, L) cũng phải chạy
    torch.testing.assert_close(m.group_norm(seq, 3), F.group_norm(seq, 3), rtol=1e-5, atol=1e-5)
    with pytest.raises(ValueError):
        m.group_norm(x, 4)


def test_group_norm_independent_of_batch(m):
    x = torch.randn(5, 4, 3, 3, generator=gen(10))
    torch.testing.assert_close(m.group_norm(x, 2)[:1], m.group_norm(x[:1], 2), rtol=1e-6, atol=1e-6)


# ---------- Block, TinyLM ----------

def test_block_structure_and_identity_at_init(m):
    torch.manual_seed(0)
    block = m.Block(8)
    assert isinstance(block.norm, m.RMSNorm) and isinstance(block.act, nn.GELU)
    assert block.fc1.weight.shape == (32, 8) and block.fc2.weight.shape == (8, 32)
    x = torch.randn(2, 3, 8, generator=gen(11))
    torch.testing.assert_close(block(x), x)
    block2 = m.Block(8, zero_init=False)
    assert not torch.allclose(block2(x), x)
    with torch.no_grad():
        expected = x + block2.fc2(F.gelu(block2.fc1(block2.norm(x))))
    torch.testing.assert_close(block2(x), expected)


def test_block_gradient_reaches_fc2_at_zero_init(m):
    block = m.Block(8)
    x = torch.randn(4, 8, generator=gen(12), requires_grad=True)
    block(x).pow(2).sum().backward()
    assert block.fc2.weight.grad.abs().sum() > 0, "fc2 = 0 vẫn nhận gradient, nên vẫn học được"
    torch.testing.assert_close(x.grad, 2 * x.detach(), msg="lúc khởi tạo gradient đi thẳng qua đường tắt")


def test_tinylm_registers_and_ties(m):
    torch.manual_seed(0)
    lm = m.TinyLM(50, 8, 3)
    keys = set(lm.state_dict())
    assert {"embed.weight", "head.weight", "norm.weight", "blocks.2.fc2.bias"} <= keys, (
        "blocks phải là nn.ModuleList để PyTorch đăng ký tham số"
    )
    assert lm.head.weight is lm.embed.weight, "weight tying: head và embed dùng chung một Parameter"
    n_block = 8 + (8 * 32 + 32) + (32 * 8 + 8)
    assert sum(p.numel() for p in lm.parameters()) == 50 * 8 + 3 * n_block + 8
    idx = torch.randint(0, 50, (2, 5), generator=gen(13))
    logits = lm(idx)
    assert logits.shape == (2, 5, 50)
    with torch.no_grad():
        expected = lm.norm(lm.embed(idx)) @ lm.embed.weight.T      # zero_init: các block là đồng nhất
    torch.testing.assert_close(logits, expected)


def test_tinylm_to_moves_everything(m):
    lm = m.TinyLM(20, 4, 2).double()
    assert all(p.dtype == torch.float64 for p in lm.parameters())
    assert lm(torch.zeros(1, 3, dtype=torch.long)).dtype == torch.float64


# ---------- weight_decay_groups, parameter_report ----------

def test_weight_decay_groups(m):
    torch.manual_seed(0)
    lm = m.TinyLM(30, 8, 2)
    lm.blocks[0].fc1.bias.requires_grad_(False)
    groups = m.weight_decay_groups(lm, 0.1)
    assert [g["weight_decay"] for g in groups] == [0.1, 0.0]
    decay, no_decay = groups[0]["params"], groups[1]["params"]
    assert all(p.dim() >= 2 for p in decay) and all(p.dim() < 2 for p in no_decay)
    ids = [id(p) for p in decay + no_decay]
    assert len(ids) == len(set(ids)), "mỗi tham số một lần, kể cả embed/head dùng chung"
    expected = {id(p) for p in lm.parameters() if p.requires_grad}
    assert set(ids) == expected
    assert len(decay) == 1 + 2 * 2 and len(no_decay) == 2 * 3 + 1 - 1
    torch.optim.AdamW(groups, lr=1e-3)                                 # optimizer nhận được


def test_parameter_report(m):
    net = nn.Sequential(nn.Conv2d(3, 4, 3), nn.BatchNorm2d(4), nn.Flatten(), nn.Linear(4, 2))
    net[0].weight.requires_grad_(False)
    rep = m.parameter_report(net)
    total = 3 * 4 * 9 + 4 + 4 + 4 + 4 * 2 + 2
    assert rep["total"] == total
    assert rep["trainable"] == total - 3 * 4 * 9
    assert rep["buffers"] == 4 + 4 + 1                                 # running_mean, running_var, num_batches_tracked
    assert rep["bytes"] == total * 4 + 8 * 4 + 1 * 8
    lm = m.TinyLM(40, 8, 1)
    assert m.parameter_report(lm)["total"] == sum(p.numel() for p in lm.parameters())
    assert m.parameter_report(lm)["total"] < sum(t.numel() for t in lm.state_dict().values())

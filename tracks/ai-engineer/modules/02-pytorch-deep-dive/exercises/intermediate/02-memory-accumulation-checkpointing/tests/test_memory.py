import copy

import pytest
import torch
import torch.nn.functional as F
from torch import nn

from testkit import Exercise

ex = Exercise(__file__)
torch.set_num_threads(1)


@pytest.fixture(scope="module")
def nb():
    return ex.notebook("memory.ipynb")


def gen(seed):
    return torch.Generator().manual_seed(seed)


def nbytes(t):
    return t.numel() * t.element_size()


# ---------- saved_tensor_bytes ----------

def test_saved_bytes_mlp(nb):
    torch.manual_seed(0)
    mlp = nn.Sequential(nn.Linear(10, 20), nn.ReLU(), nn.Linear(20, 5))
    x = torch.randn(4, 10, generator=gen(0))
    # Linear 1 lưu input x; ReLU lưu output h, Linear 2 lưu chính h (cùng storage); trọng số không tính
    assert nb.saved_tensor_bytes(mlp, x) == 4 * 10 * 4 + 4 * 20 * 4
    assert nb.saved_tensor_bytes(mlp.double(), x.double()) == 2 * (4 * 10 * 4 + 4 * 20 * 4)


def test_saved_bytes_counts_storage_once(nb):
    class Views(nn.Module):
        def forward(self, x):
            y = x.exp()                       # exp lưu output y
            return (y[:, :2] * y[:, 2:]).sum()  # mul lưu hai view của y: cùng storage

    x = torch.randn(3, 4, generator=gen(1), requires_grad=True)
    assert nb.saved_tensor_bytes(Views(), x) == 3 * 4 * 4


def test_saved_bytes_no_grad_is_zero(nb):
    mlp = nn.Sequential(nn.Linear(5, 5), nn.ReLU())
    with torch.no_grad():
        assert nb.saved_tensor_bytes(mlp, torch.randn(2, 5)) == 0


# ---------- state_bytes ----------

def _trained(opt_factory):
    torch.manual_seed(0)
    net = nn.Sequential(nn.Linear(6, 8), nn.ReLU(), nn.Linear(8, 3))
    opt = opt_factory(net.parameters())
    F.cross_entropy(net(torch.randn(5, 6, generator=gen(2))), torch.tensor([0, 1, 2, 0, 1])).backward()
    opt.step()
    return net, opt


def test_state_bytes(nb):
    n = 6 * 8 + 8 + 8 * 3 + 3
    net, opt = _trained(lambda p: torch.optim.SGD(p, lr=0.1))
    assert nb.state_bytes(net, opt) == {"params": 4 * n, "grads": 4 * n, "optimizer": 0}
    net, opt = _trained(lambda p: torch.optim.SGD(p, lr=0.1, momentum=0.9))
    assert nb.state_bytes(net, opt)["optimizer"] == 4 * n
    net, opt = _trained(lambda p: torch.optim.AdamW(p, lr=1e-3))
    expected = sum(nbytes(v) for st in opt.state.values() for v in st.values() if torch.is_tensor(v))
    assert expected >= 8 * n
    assert nb.state_bytes(net, opt)["optimizer"] == expected
    opt.zero_grad(set_to_none=True)
    assert nb.state_bytes(net, opt)["grads"] == 0


# ---------- accumulate_step ----------

def _mlp(seed=0):
    torch.manual_seed(seed)
    return nn.Sequential(nn.Linear(6, 16), nn.Tanh(), nn.Linear(16, 4))


@pytest.mark.parametrize("micro", [4, 3, 10, 1])
def test_accumulate_matches_full_batch(nb, micro):
    x, y = torch.randn(10, 6, generator=gen(3)), torch.randint(0, 4, (10,), generator=gen(4))
    model, ref = _mlp(), _mlp()
    opt = torch.optim.SGD(model.parameters(), lr=0.5, momentum=0.9)
    opt_ref = torch.optim.SGD(ref.parameters(), lr=0.5, momentum=0.9)
    for _ in range(2):                                     # hai bước: gradient cũ phải được xoá
        loss = nb.accumulate_step(model, x, y, opt, micro)
        opt_ref.zero_grad()
        ref_loss = F.cross_entropy(ref(x), y)
        ref_loss.backward()
        opt_ref.step()
        assert isinstance(loss, float) and loss == pytest.approx(ref_loss.item(), rel=1e-5)
        for p, q in zip(model.parameters(), ref.parameters()):
            torch.testing.assert_close(p.grad, q.grad, rtol=1e-5, atol=1e-6)
            torch.testing.assert_close(p, q, rtol=1e-5, atol=1e-6)


def test_accumulate_steps_once(nb):
    model = _mlp()
    calls = []
    opt = torch.optim.SGD(model.parameters(), lr=0.1)
    opt.register_step_post_hook(lambda *a: calls.append(1))
    nb.accumulate_step(model, torch.randn(9, 6), torch.randint(0, 4, (9,)), opt, 2)
    assert len(calls) == 1


# ---------- CheckpointedSequential ----------

def _layers(seed=0, p=0.0):
    torch.manual_seed(seed)
    out = []
    for _ in range(3):
        out += [nn.Linear(12, 12), nn.ReLU()]
    if p:
        out.insert(2, nn.Dropout(p))
    return out


def test_checkpoint_structure(nb):
    layers = _layers()
    ck = nb.CheckpointedSequential(layers, 3)
    assert isinstance(ck.layers, nn.ModuleList) and len(ck.layers) == 6
    assert set(ck.state_dict()) == {f"layers.{k}" for k in nn.Sequential(*_layers()).state_dict()}


@pytest.mark.parametrize("segments", [1, 2, 3, 4, 6])
def test_checkpoint_same_output_and_grads(nb, segments):
    layers = _layers(p=0.3)
    plain = nn.Sequential(*copy.deepcopy(layers))
    ck = nb.CheckpointedSequential(layers, segments)
    x = torch.randn(5, 12, generator=gen(5))
    torch.manual_seed(11)
    out = ck(x)
    out.pow(2).sum().backward()
    torch.manual_seed(11)
    ref = plain(x)
    ref.pow(2).sum().backward()
    torch.testing.assert_close(out, ref)
    for p, q in zip(ck.parameters(), plain.parameters()):
        torch.testing.assert_close(p.grad, q.grad, msg="tính lại khi backward phải sinh đúng mask Dropout cũ")


def test_checkpoint_saves_only_segment_inputs(nb):
    x = torch.randn(4, 12, generator=gen(6))
    act = 4 * 12 * 4
    plain = nn.Sequential(*_layers())
    full = nb.saved_tensor_bytes(plain, x)
    assert full == act * 4                                   # x và output của 3 ReLU (Linear sau lưu chính tensor đó)
    # Checkpoint giữ input của từng đoạn. 6 đoạn một layer: giữ cả output Linear lẫn ReLU, NHIỀU hơn không checkpoint
    for segments, kept in [(1, 1), (2, 2), (3, 3), (6, 6)]:
        ck = nb.CheckpointedSequential(_layers(), segments)
        assert nb.saved_tensor_bytes(ck, x) == act * kept, f"{segments} đoạn: chỉ giữ input của {kept} đoạn"


def test_checkpoint_disabled_in_eval_and_no_grad(nb):
    ck = nb.CheckpointedSequential(_layers(), 1)
    x = torch.randn(4, 12, generator=gen(7))
    ck.eval()
    plain_bytes = nb.saved_tensor_bytes(nn.Sequential(*_layers()), x)
    assert nb.saved_tensor_bytes(ck, x) == plain_bytes, "eval: chạy bình thường, không checkpoint"
    ck.train()
    with torch.no_grad():
        out = ck(x)
    assert out.grad_fn is None

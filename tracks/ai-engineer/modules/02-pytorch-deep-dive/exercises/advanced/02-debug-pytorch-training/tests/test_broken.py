import inspect
import re

import pytest
import torch
import torch.nn.functional as F
from torch import nn

from testkit import Exercise

ex = Exercise(__file__)
torch.set_num_threads(2)

MEAN = torch.tensor([0.4914, 0.4822, 0.4465]).view(1, 3, 1, 1)
STD = torch.tensor([0.2470, 0.2435, 0.2616]).view(1, 3, 1, 1)
COLORS = torch.tensor([[255, 40, 40], [40, 255, 40], [40, 40, 255], [255, 255, 40], [255, 40, 255],
                       [40, 255, 255], [255, 255, 255], [160, 90, 20], [120, 120, 255], [255, 150, 120]])


@pytest.fixture(scope="module")
def nb():
    return ex.notebook("broken.ipynb")


def synthetic(n: int, seed: int) -> tuple[torch.Tensor, torch.Tensor]:
    """Ảnh (N, H, W, C) uint8: nền nhiễu tối, một ô vuông 10x10 màu của lớp ở vị trí ngẫu nhiên."""
    g = torch.Generator().manual_seed(seed)
    y = torch.randint(0, 10, (n,), generator=g)
    x = torch.randint(0, 60, (n, 32, 32, 3), generator=g, dtype=torch.uint8)
    pos = torch.randint(0, 22, (n, 2), generator=g)
    for i in range(n):
        r, c = pos[i].tolist()
        x[i, r:r + 10, c:c + 10] = COLORS[y[i]].to(torch.uint8)
    return x, y


def test_setup_unchanged(nb):
    defaults = {k: v.default for k, v in inspect.signature(nb.train).parameters.items() if v.default is not inspect._empty}
    assert defaults == {"seed": 0, "epochs": 4, "batch_size": 128, "lr": 0.2, "w": 16}, "không đổi siêu tham số mặc định"
    assert nb.DEVICE == "cpu"
    sig = inspect.signature(nb.train_step).parameters
    assert sig["accum_steps"].default == 2


def test_preprocess(nb):
    x = torch.randint(0, 256, (3, 32, 32, 3), dtype=torch.uint8, generator=torch.Generator().manual_seed(0))
    out = nb.preprocess(x)
    assert out.shape == (3, 3, 32, 32) and out.dtype == torch.float32
    expected = (x.permute(0, 3, 1, 2).float() / 255 - MEAN) / STD
    torch.testing.assert_close(out, expected)


def test_net_parameters_and_state_dict(nb):
    torch.manual_seed(0)
    net = nb.Net(16)
    n = sum(p.numel() for p in net.parameters())
    assert n == 78042, f"Net(16) phải có 78 042 tham số được PyTorch đăng ký, đang có {n}"
    net.eval()
    x = torch.randn(2, 3, 32, 32)
    torch.manual_seed(1)
    other = nb.Net(16)
    other.load_state_dict(net.state_dict())
    other.eval()
    torch.testing.assert_close(other(x), net(x), msg="state_dict phải chứa mọi layer")


def test_loss_fn(nb):
    g = torch.Generator().manual_seed(2)
    logits = (3 * torch.randn(6, 10, generator=g)).requires_grad_()
    y = torch.randint(0, 10, (6,), generator=g)
    loss = nb.loss_fn(logits, y)
    torch.testing.assert_close(loss, F.cross_entropy(logits, y))
    loss.backward()
    expected = (F.softmax(logits.detach(), 1) - F.one_hot(y, 10)) / 6
    torch.testing.assert_close(logits.grad, expected)


def test_train_step_accumulates_full_batch_gradient(nb):
    torch.manual_seed(3)
    model = nn.Sequential(nn.Flatten(), nn.Linear(12, 10))
    x, y = torch.randn(8, 3, 2, 2), torch.randint(0, 10, (8,))
    opt = torch.optim.SGD(model.parameters(), lr=0.0)       # lr 0: chỉ nhìn gradient
    for p in model.parameters():
        p.grad = torch.ones_like(p)                          # gradient cũ còn sót phải bị xoá
    loss = nb.train_step(model, x, y, opt, accum_steps=4)
    ref = nn.Sequential(nn.Flatten(), nn.Linear(12, 10))
    ref.load_state_dict(model.state_dict())
    full = F.cross_entropy(ref(x), y)
    full.backward()
    assert loss == pytest.approx(full.item(), rel=1e-5)
    for p, q in zip(model.parameters(), ref.parameters()):
        torch.testing.assert_close(p.grad, q.grad, msg="gradient sau accumulation phải bằng gradient của cả batch")


def test_train_learns_and_updates_batchnorm(nb):
    x_tr, y_tr = synthetic(1024, 0)
    x_va, y_va = synthetic(256, 1)
    hist = nb.train(x_tr, y_tr, x_va, y_va, seed=0, epochs=3, batch_size=64, lr=0.2, w=8)
    assert len(hist["loss"]) == 3 and all(isinstance(v, float) for v in hist["loss"])
    bn = hist["model"].stem[1]
    assert not torch.allclose(bn.running_var, torch.ones_like(bn.running_var)), (
        "BatchNorm phải được train ở train mode (running stats được cập nhật)"
    )
    assert hist["val_acc"][-1] >= 0.9, f"val acc trên dữ liệu tổng hợp dễ: {hist['val_acc'][-1]:.3f}"


def test_bugs_written():
    doc = ex.read("BUGS.md")
    assert "TODO" not in doc
    assert len(re.findall(r"^## Bug \d", doc, re.M)) >= 5, "mỗi bug một mục `## Bug N: ...`"
    assert len(doc.split()) >= 300

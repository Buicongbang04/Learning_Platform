import inspect
import re

import pytest
import torch
import torch.nn.functional as F
from torch import nn

from testkit import Exercise

ex = Exercise(__file__)
torch.set_num_threads(2)


@pytest.fixture(scope="module")
def nb():
    return ex.notebook("broken_ddpm.ipynb")


def test_setup_unchanged(nb):
    defaults = {k: v.default for k, v in inspect.signature(nb.train).parameters.items() if v.default is not inspect._empty}
    assert defaults == {"steps": 3000, "batch_size": 128, "lr": 2e-4, "ema_decay": 0.999, "seed": 0, "model": None}
    assert sum(p.numel() for p in nb.UNet().parameters()) == 1_045_729, "không đổi kiến trúc UNet"
    s = nb.make_schedule()
    assert s["betas"][0].item() == pytest.approx(1e-4) and s["betas"][-1].item() == pytest.approx(0.02)


def test_preprocess_postprocess(nb):
    img = torch.tensor([[[0, 255], [128, 64]]], dtype=torch.uint8)
    x = nb.preprocess(img)
    assert x.shape == (1, 1, 2, 2) and x.dtype == torch.float32
    torch.testing.assert_close(x, (img.float().unsqueeze(1) / 255) * 2 - 1, msg="model train trên ảnh trong [-1, 1]")
    y = nb.postprocess(torch.tensor([-1.5, -1.0, 0.0, 1.0, 2.0]))
    torch.testing.assert_close(y, torch.tensor([0.0, 0.0, 0.5, 1.0, 1.0]))
    torch.testing.assert_close(nb.postprocess(nb.preprocess(img)), img.float().unsqueeze(1) / 255, msg="đi vòng preprocess → postprocess")


def test_q_sample_and_loss(nb):
    s = nb.make_schedule(50)
    g = torch.Generator().manual_seed(0)
    x0 = torch.rand(4, 1, 6, 6, generator=g) * 2 - 1
    noise = torch.randn(4, 1, 6, 6, generator=g)
    t = torch.tensor([0, 10, 25, 49])
    ab = s["alpha_bars"][t].view(-1, 1, 1, 1)
    torch.testing.assert_close(nb.q_sample(x0, t, noise, s["alpha_bars"]), ab.sqrt() * x0 + (1 - ab).sqrt() * noise)

    class Tiny(nn.Module):
        def __init__(self):
            super().__init__()
            torch.manual_seed(1)
            self.conv = nn.Conv2d(1, 1, 3, padding=1)

        def forward(self, x, t):
            return self.conv(x) + t.float().view(-1, 1, 1, 1) / 50

    model = Tiny()
    loss = nb.ddpm_loss(model, x0, s, torch.Generator().manual_seed(2))
    g = torch.Generator().manual_seed(2)
    tt = torch.randint(0, 50, (4,), generator=g)
    nn_ = torch.randn(x0.shape, generator=g)
    a = s["alpha_bars"][tt].view(-1, 1, 1, 1)
    torch.testing.assert_close(loss, F.mse_loss(model(a.sqrt() * x0 + (1 - a).sqrt() * nn_, tt), nn_))


def test_ddim_sample_recovers_single_image(nb):
    s = nb.make_schedule(100)
    target = torch.linspace(-0.9, 0.9, 784).view(1, 1, 28, 28)

    class Oracle(nn.Module):
        def __init__(self):
            super().__init__()
            self.p = nn.Parameter(torch.zeros(1))

        def forward(self, x, t):
            ab = s["alpha_bars"][t].view(-1, 1, 1, 1).double()
            return ((x.double() - ab.sqrt() * target.double()) / (1 - ab).sqrt()).float()

    out = nb.ddim_sample(Oracle(), 3, s, 10, torch.Generator().manual_seed(0))
    torch.testing.assert_close(out, target.expand(3, 1, 28, 28), atol=1e-4, rtol=0)


def test_ddim_sample_is_deterministic_with_dropout_model(nb):
    """Model có dropout, đang ở chế độ train (như ngay sau khi train hoặc vừa tạo): cùng generator phải cho cùng ảnh."""
    torch.manual_seed(3)
    model = nb.UNet(ch=8, dropout=0.5)
    model.train()
    s = nb.make_schedule(100)
    a = nb.ddim_sample(model, 2, s, 5, torch.Generator().manual_seed(7))
    b = nb.ddim_sample(model, 2, s, 5, torch.Generator().manual_seed(7))
    torch.testing.assert_close(a, b, msg="DDIM eta = 0 là tất định khi cùng nhiễu ban đầu")


def test_ema_is_a_separate_average(nb):
    net = nn.Linear(3, 2)
    w0 = net.weight.detach().clone()
    ema = nb.EMA(net, 0.9)
    with torch.no_grad():
        net.weight.add_(1.0)
    w1 = net.weight.detach().clone()
    ema.update(net)
    torch.testing.assert_close(net.weight, w1, msg="update không được đổi trọng số của model")
    torch.testing.assert_close(ema.shadow["weight"], 0.9 * w0 + 0.1 * w1)


def synthetic_images(n, seed):
    """Ảnh uint8 28x28: một ô vuông sáng 8x8 ở một trong bốn góc."""
    g = torch.Generator().manual_seed(seed)
    imgs = torch.zeros(n, 28, 28, dtype=torch.uint8)
    corner = torch.randint(0, 4, (n,), generator=g)
    for i, c in enumerate(corner.tolist()):
        r, k = (2 if c < 2 else 18), (2 if c % 2 == 0 else 18)
        imgs[i, r:r + 8, k:k + 8] = 255
    return imgs


def test_train_runs_and_ema_tracks(nb):
    torch.manual_seed(0)
    small = nb.UNet(ch=8, dropout=0.0)
    init = {k: v.detach().clone() for k, v in small.state_dict().items()}
    model, ema, losses = nb.train(synthetic_images(64, 0), steps=60, batch_size=16, lr=2e-3, ema_decay=0.9, model=small)
    assert len(losses) == 60 and all(isinstance(v, float) for v in losses)
    assert sum(losses[-15:]) < sum(losses[:15])
    differs = any(not torch.equal(ema.shadow[k], v) for k, v in model.state_dict().items() if v.dtype.is_floating_point)
    assert differs, "EMA phải là trung bình trượt riêng, không trùng trọng số hiện tại"
    moved = any(not torch.equal(ema.shadow[k], v) for k, v in init.items() if v.dtype.is_floating_point)
    assert moved, "EMA phải được cập nhật trong lúc train"


def test_bugs_md_written():
    path = ex.path("BUGS.md")
    text = path.read_text(encoding="utf-8")
    assert "TODO" not in text, "BUGS.md còn TODO"
    assert len(re.findall(r"^## Bug \d+", text, re.M)) >= 5, "ít nhất 5 mục `## Bug N`"
    assert len(text.split()) >= 350, "BUGS.md cần ít nhất 350 từ"

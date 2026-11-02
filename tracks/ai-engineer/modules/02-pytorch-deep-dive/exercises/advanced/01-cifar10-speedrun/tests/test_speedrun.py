import re
from pathlib import Path

import pytest
import torch
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
    return ex.notebook("speedrun.ipynb")


def synthetic(n: int, seed: int) -> tuple[torch.Tensor, torch.Tensor]:
    """Ảnh uint8 (N, 3, 32, 32): nền nhiễu tối, một ô vuông 10x10 màu của lớp ở vị trí ngẫu nhiên."""
    g = torch.Generator().manual_seed(seed)
    y = torch.randint(0, 10, (n,), generator=g)
    x = torch.randint(0, 60, (n, 3, 32, 32), generator=g, dtype=torch.uint8)
    pos = torch.randint(0, 22, (n, 2), generator=g)
    for i in range(n):
        r, c = pos[i].tolist()
        x[i, :, r:r + 10, c:c + 10] = COLORS[y[i]].view(3, 1, 1).to(torch.uint8)
    return x, y


def test_lr_at(nb):
    total, peak = 100, 0.4
    lrs = [nb.lr_at(s, total, peak, 0.2) for s in range(total + 1)]
    assert lrs[0] == pytest.approx(0.0, abs=1e-12)
    assert lrs[10] == pytest.approx(0.2) and lrs[20] == pytest.approx(peak)
    assert lrs[60] == pytest.approx(0.2) and lrs[100] == pytest.approx(0.0, abs=1e-12)
    assert all(a <= b + 1e-12 for a, b in zip(lrs[:21], lrs[1:21])), "tăng dần trong warmup"
    assert all(a >= b - 1e-12 for a, b in zip(lrs[20:], lrs[21:])), "giảm dần sau warmup"
    assert nb.lr_at(120, total, peak, 0.2) == pytest.approx(0.0, abs=1e-12), "không âm sau bước cuối"
    assert nb.lr_at(1, 10, 1.0, 0.0) == pytest.approx(1.0 * 9 / 9), "warmup ít nhất 1 bước"


def test_predict_tta(nb):
    torch.manual_seed(0)
    model = nn.Sequential(nn.Conv2d(3, 4, 3, padding=1), nn.BatchNorm2d(4), nn.ReLU(), nn.Flatten(), nn.Linear(4 * 32 * 32, 10))
    model.train()
    model(torch.randn(16, 3, 32, 32))                     # cập nhật running stats để eval khác train
    x = torch.randn(7, 3, 32, 32, generator=torch.Generator().manual_seed(1))
    out = nb.predict_tta(model, x, batch_size=3)
    assert model.training, "trả model về chế độ cũ"
    assert out.dtype == torch.float32 and out.shape == (7, 10) and out.device.type == "cpu" and out.grad_fn is None
    model.eval()
    with torch.no_grad():
        expected = (model(x) + model(x.flip(3))) / 2
    torch.testing.assert_close(out, expected, rtol=2e-2, atol=2e-2)
    torch.testing.assert_close(nb.predict_tta(model, x.flip(3)), out, rtol=2e-2, atol=2e-2)
    assert not model.training


def test_build_model_seeded(nb):
    a, b, c = nb.build_model(0, width=8), nb.build_model(0, width=8), nb.build_model(1, width=8)
    pa, pb, pc = [torch.cat([p.detach().flatten() for p in m.parameters()]) for m in (a, b, c)]
    assert torch.equal(pa, pb) and not torch.equal(pa, pc)
    a.eval()
    assert a(torch.randn(2, 3, 32, 32)).shape == (2, 10)
    n8 = pa.numel()
    n16 = sum(p.numel() for p in nb.build_model(0, width=16).parameters())
    assert n16 > n8, "width điều khiển độ rộng"


def test_fit_learns_synthetic_on_cpu(nb):
    x_tr, y_tr = synthetic(1024, 0)
    x_va, y_va = synthetic(256, 1)
    model = nb.build_model(0, width=8)
    hist = nb.fit(model, x_tr, y_tr, epochs=3, batch_size=64)
    assert len(hist["loss"]) == 3 and all(isinstance(v, float) for v in hist["loss"]) and hist["loss"][-1] < hist["loss"][0]
    assert isinstance(hist["seconds"], float) and hist["seconds"] > 0
    model.cpu()
    acc = (nb.predict_tta(model, (x_va.float() / 255 - MEAN) / STD).argmax(1) == y_va).float().mean().item()
    assert acc >= 0.9, f"accuracy trên dữ liệu tổng hợp dễ: {acc:.3f}"


def test_report_written():
    doc = ex.read("REPORT.md")
    assert "TODO" not in doc
    assert len(doc.split()) >= 700
    assert re.search(r"^\|.*\|\s*$", doc, re.M), "có ít nhất một bảng"
    for img in re.findall(r"!\[[^\]]*\]\(([^)]+)\)", doc):
        assert (ex.target / img).exists(), f"thiếu tệp hình {img}"

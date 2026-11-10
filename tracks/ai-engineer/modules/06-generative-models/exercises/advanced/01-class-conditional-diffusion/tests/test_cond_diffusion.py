import math
import re

import numpy as np
import pytest
import torch
from torch import nn

from testkit import Exercise

ex = Exercise(__file__)
torch.set_num_threads(2)


@pytest.fixture(scope="module")
def nb():
    return ex.notebook("cond_diffusion.ipynb")


class LabelModel(nn.Module):
    """eps(x, t, y) = x * (y + 1) + t / 100: mỗi nhãn một hệ số, dễ kiểm công thức trộn."""

    def __init__(self):
        super().__init__()
        self.p = nn.Parameter(torch.zeros(1))
        self.calls = []

    def forward(self, x, t, y):
        self.calls.append(y.clone())
        return x * (y.float() + 1).view(-1, *([1] * (x.dim() - 1))) + t.float().view(-1, *([1] * (x.dim() - 1))) / 100


def test_drop_labels(nb):
    y = torch.arange(10).repeat(1000)
    out = nb.drop_labels(y, 0.1, 10, torch.Generator().manual_seed(0))
    assert out.dtype == torch.int64 and out.shape == y.shape
    assert torch.equal(y, torch.arange(10).repeat(1000)), "không sửa y tại chỗ"
    mask = torch.rand(len(y), generator=torch.Generator().manual_seed(0)) < 0.1
    assert torch.equal(out, torch.where(mask, torch.full_like(y, 10), y))
    assert torch.equal(nb.drop_labels(y, 0.0, 10, torch.Generator().manual_seed(1)), y)
    assert torch.all(nb.drop_labels(y, 1.0, 10, torch.Generator().manual_seed(1)) == 10)


@pytest.mark.parametrize("w", [0.0, 1.0, 3.0])
def test_cfg_eps_formula(nb, w):
    model = LabelModel()
    x = torch.randn(4, 3, 2, 2, generator=torch.Generator().manual_seed(2))
    t = torch.tensor([0, 5, 10, 999])
    y = torch.tensor([0, 3, 7, 9])
    out = nb.cfg_eps(model, x, t, y, w, 10)
    e_c = x * (y.float() + 1).view(-1, 1, 1, 1) + t.float().view(-1, 1, 1, 1) / 100
    e_u = x * 11 + t.float().view(-1, 1, 1, 1) / 100
    torch.testing.assert_close(out, (1 + w) * e_c - w * e_u)
    seen = torch.cat(model.calls)
    if w == 0:
        assert not torch.any(seen == 10), "w = 0: chỉ cần nhánh có điều kiện"
    else:
        assert torch.sum(seen == 10) == 4, "nhánh rỗng dùng đúng null_class cho mọi mẫu"


def single_point_oracle(alpha_bars, targets):
    """Mỗi class c là một ảnh duy nhất targets[c]; nhãn rỗng là trung bình các ảnh (đủ để kiểm khi w = 0)."""

    class Oracle(nn.Module):
        def __init__(self):
            super().__init__()
            self.p = nn.Parameter(torch.zeros(1))

        def forward(self, x, t, y):
            ab = alpha_bars.double()[t].view(-1, 1, 1, 1)
            centers = torch.cat([targets, targets.mean(0, keepdim=True)])[y]
            return ((x.double() - ab.sqrt() * centers) / (1 - ab).sqrt()).float()

    return Oracle()


def test_ddim_sample_cfg_recovers_class_images(nb):
    T = 200
    alpha_bars = torch.cumprod(1 - torch.linspace(1e-3, 0.05, T, dtype=torch.float64), 0)
    targets = torch.linspace(-0.9, 0.9, 3 * 3 * 4 * 4).view(3, 3, 4, 4).double()
    model = single_point_oracle(alpha_bars, targets)
    y = torch.tensor([0, 2, 1, 2])
    out = nb.ddim_sample_cfg(model, y, alpha_bars.float(), 20, 0.0, 3, torch.Generator().manual_seed(0), shape=(3, 4, 4))
    assert out.shape == (4, 3, 4, 4)
    torch.testing.assert_close(out.double(), targets[y], atol=1e-4, rtol=0)


def reference_ddim(model, y, abar, steps, w, null, g, shape):
    ts = torch.linspace(0, len(abar) - 1, steps).round().long().tolist()
    x = torch.randn((len(y), *shape), generator=g)
    for i in reversed(range(steps)):
        ab = abar[ts[i]]
        ab_prev = abar[ts[i - 1]] if i > 0 else torch.tensor(1.0)
        tt = torch.full((len(y),), ts[i])
        e = (1 + w) * model(x, tt, y) - w * model(x, tt, torch.full_like(y, null))
        x0 = ((x - (1 - ab).sqrt() * e) / ab.sqrt()).clamp(-1, 1)
        e = (x - ab.sqrt() * x0) / (1 - ab).sqrt()
        x = ab_prev.sqrt() * x0 + (1 - ab_prev).sqrt() * e
    return x


@pytest.mark.parametrize("w", [0.0, 2.0])
def test_ddim_sample_cfg_matches_reference(nb, w):
    torch.manual_seed(0)

    class Small(nn.Module):
        def __init__(self):
            super().__init__()
            self.conv = nn.Conv2d(3, 3, 3, padding=1)
            self.emb = nn.Embedding(4, 3)

        def forward(self, x, t, y):
            return 0.3 * torch.tanh(self.conv(x)) + 0.1 * self.emb(y)[:, :, None, None] + t.float().view(-1, 1, 1, 1) / 500

    model = Small()
    abar = torch.cumprod(1 - torch.linspace(1e-3, 0.05, 100), 0)
    y = torch.tensor([0, 1, 2])
    with torch.no_grad():
        expected = reference_ddim(model, y, abar, 9, w, 3, torch.Generator().manual_seed(4), (3, 5, 5))
    out = nb.ddim_sample_cfg(model, y, abar, 9, w, 3, torch.Generator().manual_seed(4), shape=(3, 5, 5))
    torch.testing.assert_close(out, expected, atol=1e-5, rtol=1e-4)


def scipy_free_reference_fid(a, b):
    """FID tham chiếu: căn bậc hai ma trận qua phân rã Schur của numpy (eig) thay vì cách của bạn."""
    a, b = a.double().numpy(), b.double().numpy()
    mu1, mu2 = a.mean(0), b.mean(0)
    s1, s2 = np.cov(a, rowvar=False), np.cov(b, rowvar=False)
    ev = np.linalg.eigvals(s1 @ s2)
    return float(((mu1 - mu2) ** 2).sum() + np.trace(s1) + np.trace(s2) - 2 * np.sqrt(np.clip(ev.real, 0, None)).sum())


def gaussian_features(n, d, seed, shift=0.0, scale=1.0):
    g = torch.Generator().manual_seed(seed)
    A = torch.randn(d, d, generator=torch.Generator().manual_seed(100), dtype=torch.float64) / math.sqrt(d)
    return (torch.randn(n, d, generator=g, dtype=torch.float64) @ A) * scale + shift


def test_fid_matches_reference(nb):
    a = gaussian_features(3000, 16, 1)
    b = gaussian_features(2000, 16, 2, shift=0.3, scale=1.5)
    fid = nb.fid_from_features(a, b)
    assert isinstance(fid, float)
    assert fid == pytest.approx(scipy_free_reference_fid(a, b), rel=1e-6)
    assert nb.fid_from_features(b, a) == pytest.approx(fid, rel=1e-6), "FID đối xứng"
    assert nb.fid_from_features(a, a) == pytest.approx(0.0, abs=1e-6)
    assert nb.fid_from_features(a.float(), b.float()) == pytest.approx(fid, rel=1e-4), "nhận feature float32, tính và trả cùng kết quả"


def test_fid_closed_form_on_large_gaussians(nb):
    """N(0, I) và N(m, s^2 I) trong d chiều: FID = |m|^2 + d (1 - s)^2."""
    d = 8
    g = torch.Generator().manual_seed(3)
    a = torch.randn(100_000, d, generator=g, dtype=torch.float64)
    b = 2.0 * torch.randn(100_000, d, generator=g, dtype=torch.float64) + 0.5
    assert nb.fid_from_features(a, b) == pytest.approx(d * 0.25 + d * 1.0, rel=0.02)


def reference_kid(a, b, subsets, m, g):
    a, b = a.double(), b.double()
    d = a.shape[1]
    vals = []
    for _ in range(subsets):
        x = a[torch.randperm(len(a), generator=g)[:m]]
        y = b[torch.randperm(len(b), generator=g)[:m]]
        k = lambda u, v: (u @ v.T / d + 1) ** 3
        kxx, kyy, kxy = k(x, x), k(y, y), k(x, y)
        vals.append(float((kxx.sum() - kxx.trace()) / (m * (m - 1)) + (kyy.sum() - kyy.trace()) / (m * (m - 1)) - 2 * kxy.mean()))
    return float(np.mean(vals)), float(np.std(vals))


def test_kid_matches_reference(nb):
    a = gaussian_features(600, 10, 4)
    b = gaussian_features(500, 10, 5, shift=0.2)
    out = nb.kid_from_features(a, b, subsets=7, subset_size=200, generator=torch.Generator().manual_seed(9))
    ref = reference_kid(a, b, 7, 200, torch.Generator().manual_seed(9))
    assert isinstance(out[0], float) and isinstance(out[1], float)
    assert out[0] == pytest.approx(ref[0], rel=1e-6) and out[1] == pytest.approx(ref[1], rel=1e-6)
    small = nb.kid_from_features(a[:50], b[:40], subsets=3, subset_size=1000, generator=torch.Generator().manual_seed(1))
    assert small == pytest.approx(reference_kid(a[:50], b[:40], 3, 40, torch.Generator().manual_seed(1)), rel=1e-6), "m = min(subset_size, N, M)"


def test_kid_unbiased_near_zero_for_same_distribution(nb):
    """Ước lượng không chệch: hai mẫu cùng phân phối cho KID trung bình quanh 0 (có thể âm), FID thì dương rõ."""
    a = gaussian_features(400, 32, 6)
    b = gaussian_features(400, 32, 7)
    kid, _ = nb.kid_from_features(a, b, subsets=20, subset_size=200, generator=torch.Generator().manual_seed(0))
    shifted, _ = nb.kid_from_features(a, b + 0.5, subsets=20, subset_size=200, generator=torch.Generator().manual_seed(0))
    assert abs(kid) < 0.02 and shifted > 0.1
    assert nb.fid_from_features(a, b) > 0.5, "FID của hai mẫu cùng phân phối vẫn dương: chệch theo số mẫu"


def test_report_written():
    path = ex.path("REPORT.md")
    root = path.parent
    text = path.read_text(encoding="utf-8")
    assert "TODO" not in text, "REPORT.md còn TODO"
    assert len(text.split()) >= 700, "REPORT.md cần ít nhất 700 từ"
    assert re.search(r"^\|.*\|$", text, re.M), "cần ít nhất một bảng số"
    images = re.findall(r"!\[[^\]]*\]\(([^)]+)\)", text)
    assert images, "cần ít nhất một hình (lưới ảnh sinh hoặc đường cong)"
    assert all((root / p).exists() for p in images), "tệp hình phải tồn tại cạnh REPORT.md"

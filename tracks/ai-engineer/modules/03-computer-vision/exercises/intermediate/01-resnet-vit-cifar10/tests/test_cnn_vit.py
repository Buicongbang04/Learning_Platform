import json
import math
import time

import numpy as np
import pytest
import torch
import torch.nn.functional as F
from torch import nn

from testkit import Exercise

ex = Exercise(__file__)
torch.set_num_threads(2)


@pytest.fixture(scope="module")
def nb():
    return ex.notebook("cnn_vit.ipynb")


def n_params(m: nn.Module) -> int:
    return sum(p.numel() for p in m.parameters())


def blobs(n: int, seed: int) -> tuple[torch.Tensor, torch.Tensor]:
    """10 lớp, mỗi lớp một màu nền + nhiễu: ảnh 3x32x32 nhỏ, học được, sinh trong test."""
    g = torch.Generator().manual_seed(seed)
    colors = torch.randn(10, 3, 1, 1, generator=torch.Generator().manual_seed(0))
    y = torch.randint(0, 10, (n,), generator=g)
    X = colors[y] + 0.8 * torch.randn(n, 3, 32, 32, generator=g)
    return X, y


# ---------- 1. dữ liệu ----------

def test_channel_stats(nb):
    rng = np.random.default_rng(0)
    X = rng.integers(0, 256, (20, 8, 8, 3)).astype(np.uint8)
    X[..., 2] = 255
    mean, std = nb.channel_stats(X)
    assert mean.shape == (3,) and std.shape == (3,)
    flat = X.reshape(-1, 3) / 255
    np.testing.assert_allclose(mean, flat.mean(0), atol=1e-9)
    np.testing.assert_allclose(std, flat.std(0), atol=1e-9)
    assert mean[2] == pytest.approx(1.0) and std[2] == pytest.approx(0.0)


def test_to_tensor_layout_and_normalization(nb):
    X = np.zeros((2, 4, 5, 3), np.uint8)
    X[0, 1, 2] = [255, 0, 51]            # một pixel ở hàng 1, cột 2 của ảnh 0
    t = nb.to_tensor(X, [0.0, 0.5, 0.2], [1.0, 0.5, 0.1])
    assert t.shape == (2, 3, 4, 5) and t.dtype == torch.float32
    assert t[0, :, 1, 2].tolist() == pytest.approx([1.0, -1.0, 0.0], abs=1e-6)
    assert t[0, 0, 0, 0].item() == pytest.approx(0.0) and t[0, 1, 0, 0].item() == pytest.approx(-1.0)
    assert t[1, 2].mean().item() == pytest.approx(-2.0, abs=1e-6)


def test_random_crop_flip(nb):
    x = torch.arange(2 * 3 * 6 * 6, dtype=torch.float32).reshape(2, 3, 6, 6) + 1
    x = x.repeat(16, 1, 1, 1)                                   # 32 ảnh
    out = nb.random_crop_flip(x, torch.Generator().manual_seed(0), pad=2)
    assert out.shape == x.shape
    again = nb.random_crop_flip(x, torch.Generator().manual_seed(0), pad=2)
    assert torch.equal(out, again), "cùng seed của generator phải ra cùng kết quả"
    padded = F.pad(x, (2, 2, 2, 2))
    flips = 0
    for i in range(len(x)):
        cands = [(dy, dx, f) for dy in range(5) for dx in range(5) for f in (False, True)
                 if torch.equal(out[i], (padded[i, :, dy:dy + 6, dx:dx + 6].flip(-1) if f
                                         else padded[i, :, dy:dy + 6, dx:dx + 6]))]
        assert cands, f"ảnh {i} không phải một crop (có thể lật ngang) của ảnh đã đệm 0"
        flips += any(f for _, _, f in cands) and not any(not f for _, _, f in cands)
    assert 4 <= flips <= 28, "khoảng một nửa số ảnh phải bị lật ngang"
    shifts = {tuple(int(v) for v in torch.nonzero(out[i, 0] > 0)[0]) for i in range(len(x))}
    assert len(shifts) > 3, "mỗi ảnh một độ dịch riêng"


# ---------- 2. CNN ----------

def test_lenet5(nb):
    m = nb.LeNet5()
    assert n_params(m) == 62006, "LeNet-5 cho ảnh 3x32x32: 62 006 tham số"
    assert m(torch.zeros(4, 3, 32, 32)).shape == (4, 10)


def test_basic_block_identity_and_projection(nb):
    same = nb.BasicBlock(16, 16, 1)
    assert isinstance(same.shortcut, nn.Identity) or n_params(same.shortcut) == 0
    assert same(torch.randn(2, 16, 8, 8)).shape == (2, 16, 8, 8)
    down = nb.BasicBlock(16, 32, 2)
    assert n_params(down.shortcut) == 16 * 32 + 2 * 32, "projection: conv 1x1 không bias + BN"
    assert down(torch.randn(2, 16, 8, 8)).shape == (2, 32, 4, 4)
    for conv in (same.conv1, same.conv2):
        assert conv.bias is None and conv.kernel_size == (3, 3)


def test_basic_block_residual_math(nb):
    # gamma của bn2 bằng 0 thì nhánh chính ra 0 (eval mode): block residual thành ReLU(x), plain thành 0
    torch.manual_seed(0)
    x = torch.randn(2, 8, 6, 6)
    res, plain = nb.BasicBlock(8, 8, 1, residual=True).eval(), nb.BasicBlock(8, 8, 1, residual=False).eval()
    for blk in (res, plain):
        nn.init.zeros_(blk.bn2.weight)
        nn.init.zeros_(blk.bn2.bias)
    assert torch.allclose(res(x), F.relu(x)), "ReLU cuối nằm SAU phép cộng shortcut"
    assert torch.count_nonzero(plain(x)) == 0
    # còn lại: khớp công thức
    blk = nb.BasicBlock(8, 8, 1).eval()
    with torch.no_grad():
        for bn in (blk.bn1, blk.bn2):
            bn.running_mean.uniform_(-0.5, 0.5)
            bn.running_var.uniform_(0.5, 2.0)
            bn.weight.uniform_(0.5, 1.5)
            bn.bias.uniform_(-0.2, 0.2)
    ref = F.relu(blk.bn2(blk.conv2(F.relu(blk.bn1(blk.conv1(x))))) + x)
    assert torch.allclose(blk(x), ref, atol=1e-6)


def test_resnet_cifar(nb):
    m = nb.ResNetCifar(20)
    assert n_params(m) == 272474, "ResNet-20 (shortcut projection) có 272 474 tham số"
    assert n_params(nb.ResNetCifar(56)) == 855770
    assert n_params(nb.ResNetCifar(20, residual=False)) == 272474, "plain: cùng kiến trúc, chỉ bỏ phép cộng"
    blocks = [mod for mod in m.modules() if isinstance(mod, nb.BasicBlock)]
    assert len(blocks) == 9
    assert m(torch.zeros(2, 3, 32, 32)).shape == (2, 10)
    assert m(torch.zeros(2, 3, 48, 40)).shape == (2, 10), "global average pooling: nhận ảnh cỡ bất kỳ"


# ---------- 3. ViT ----------

def test_patch_embed_is_linear_on_patches(nb):
    torch.manual_seed(1)
    pe = nb.PatchEmbed(4, 3, 24)
    x = torch.randn(2, 3, 8, 12)
    out = pe(x)
    assert out.shape == (2, 6, 24), "8x12 với patch 4: 2 x 3 = 6 patch"
    W = pe.proj.weight.reshape(24, -1)
    patch = x[1, :, 4:8, 8:12].reshape(-1)          # patch hàng 1, cột 2 → chỉ số 1*3 + 2 = 5
    assert torch.allclose(out[1, 5], W @ patch + pe.proj.bias, atol=1e-5)


def test_attention_matches_reference(nb):
    torch.manual_seed(2)
    att = nb.MultiHeadSelfAttention(32, 4)
    x = torch.randn(3, 7, 32)
    q, k, v = att.qkv(x).split(32, dim=-1)
    split = lambda t: t.reshape(3, 7, 4, 8).transpose(1, 2)
    ref = F.scaled_dot_product_attention(split(q), split(k), split(v)).transpose(1, 2).reshape(3, 7, 32)
    ref = att.proj(ref)
    assert torch.allclose(att(x), ref, atol=1e-5)


def test_attention_written_by_hand(nb):
    cells = json.loads(ex.read("cnn_vit.ipynb"))["cells"]
    src = "\n".join("".join(c["source"]) for c in cells if c["cell_type"] == "code")
    for banned in ("scaled_dot_product_attention", "MultiheadAttention"):
        assert banned not in src, f"tự viết attention, không dùng {banned}"


def test_attention_permutation_equivariant(nb):
    torch.manual_seed(3)
    att = nb.MultiHeadSelfAttention(16, 2)
    x = torch.randn(2, 5, 16)
    perm = torch.tensor([3, 0, 4, 1, 2])
    assert torch.allclose(att(x)[:, perm], att(x[:, perm]), atol=1e-5)


def test_vit_shapes_and_params(nb):
    torch.manual_seed(4)
    m = nb.ViT()
    assert m.cls_token.shape == (1, 1, 128) and m.pos_embed.shape == (1, 65, 128)
    assert n_params(m) == 811146
    assert m(torch.zeros(2, 3, 32, 32)).shape == (2, 10)
    small = nb.ViT(img_size=16, patch=8, dim=32, depth=2, heads=2, mlp_ratio=4, num_classes=5)
    assert small.pos_embed.shape == (1, 5, 32)
    assert small(torch.zeros(1, 3, 16, 16)).shape == (1, 5)


def test_vit_uses_position(nb):
    # có position embedding thì đảo vị trí các patch làm đổi output (bag-of-patches thì không)
    torch.manual_seed(5)
    m = nb.ViT(img_size=16, patch=8, dim=32, depth=1, heads=2, num_classes=3).eval()
    x = torch.randn(1, 3, 16, 16)
    swapped = torch.cat([x[..., 8:], x[..., :8]], dim=-1)
    assert not torch.allclose(m(x), m(swapped), atol=1e-4)


# ---------- 4. vòng train ----------

def test_train_learns_and_is_deterministic(nb):
    X, y = blobs(512, 1)
    Xv, yv = blobs(256, 2)
    runs = []
    for _ in range(2):
        torch.manual_seed(123)                                  # seed ngoài không được ảnh hưởng
        model = nb.LeNet5()
        hist = nb.train(model, X, y, epochs=3, lr=3e-3, batch_size=64, seed=7)
        runs.append((hist, nb.evaluate(model, Xv, yv)))
    hist, acc = runs[0]
    assert len(hist) == 3 and all(isinstance(h, float) and math.isfinite(h) for h in hist)
    assert hist[-1] < hist[0]
    assert acc >= 0.9, f"10 màu tách được: val accuracy {acc:.3f}"
    assert runs[0] == runs[1], "cùng seed phải ra cùng history và accuracy"


def test_train_loss_is_mean_over_samples(nb):
    # lr = 0, không augment, model không có BN/dropout: loss epoch = loss trên cả tập
    X, y = blobs(200, 3)
    model = nb.LeNet5()
    hist = nb.train(model, X, y, epochs=1, lr=0.0, batch_size=64, seed=0, augment=False)
    with torch.no_grad():
        full = F.cross_entropy(model(X), y).item()
    assert hist[0] == pytest.approx(full, rel=1e-5)
    assert not model.training, "train kết thúc ở chế độ eval()"


def test_evaluate_eval_mode(nb):
    X, y = blobs(100, 4)
    model = nb.ResNetCifar(8)
    nb.train(model, X, y, epochs=1, lr=1e-3, batch_size=50, seed=0)
    model.train()
    full = nb.evaluate(model, X, y)
    assert isinstance(full, float) and 0.0 <= full <= 1.0
    chunks = sum(nb.evaluate(model, X[i:i + 5], y[i:i + 5], batch_size=5) * 5 for i in range(0, 100, 5))
    assert chunks == pytest.approx(full * 100, abs=1e-6), "evaluate phải ở eval(): BatchNorm dùng running stats"


# ---------- 5. dữ liệu thật: tự skip nếu chưa tải CIFAR-10 ----------

def test_load_cifar10_real(nb):
    root = ex.dataset("cifar10")
    Xt, yt = nb.load_cifar10(root, "test")
    assert Xt.shape == (10000, 32, 32, 3) and Xt.dtype == np.uint8 and yt.dtype == np.int64
    assert np.bincount(yt).tolist() == [1000] * 10
    assert yt[:5].tolist() == [3, 8, 8, 0, 6]
    mean, std = nb.channel_stats(Xt)
    np.testing.assert_allclose(mean, [0.4942, 0.4851, 0.4504], atol=1e-4)
    np.testing.assert_allclose(std, [0.2467, 0.2429, 0.2616], atol=1e-4)
    X, y = nb.load_cifar10(root, "train", limit=8)
    assert X.shape == (8, 32, 32, 3) and y.tolist() == [0, 6, 0, 2, 7, 2, 1, 2]


def test_lenet_on_real_cifar(nb):
    root = ex.dataset("cifar10")
    X, y = nb.load_cifar10(root, "train", limit=4000)
    Xt, yt = nb.load_cifar10(root, "test", limit=2000)
    mean, std = nb.channel_stats(X)
    start = time.perf_counter()
    model = nb.LeNet5()
    nb.train(model, nb.to_tensor(X, mean, std), torch.from_numpy(y), epochs=2, lr=3e-3,
             batch_size=128, seed=0, augment=False)
    acc = nb.evaluate(model, nb.to_tensor(Xt, mean, std), torch.from_numpy(yt))
    assert time.perf_counter() - start < 60, "LeNet 2 epoch trên 4 000 ảnh chỉ mất vài giây trên CPU"
    assert acc >= 0.30, f"LeNet 2 epoch trên 4 000 ảnh: accuracy {acc:.3f} (lời giải mẫu: xem SOLUTION.md)"

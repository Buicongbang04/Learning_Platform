import re

import cv2
import numpy as np
import pytest
import torch
import torch.nn.functional as F
from torch import nn

from testkit import Exercise

ex = Exercise(__file__)
torch.set_num_threads(2)

MEAN = torch.tensor([0.485, 0.456, 0.406]).view(3, 1, 1)
STD = torch.tensor([0.229, 0.224, 0.225]).view(3, 1, 1)


@pytest.fixture(scope="module")
def nb():
    return ex.notebook("segment.ipynb")


def blob_pair(seed: int, h: int = 90, w: int = 120) -> tuple[np.ndarray, np.ndarray]:
    """Ảnh RGB có một 'người' trắng hình chữ nhật lệch tâm trên nền tối nhiễu; mask đánh dấu đúng vùng đó."""
    rng = np.random.default_rng(seed)
    image = rng.integers(0, 60, (h, w, 3)).astype(np.uint8)
    mask = np.zeros((h, w), np.uint8)
    y0, x0 = int(rng.integers(5, h // 3)), int(rng.integers(5, w // 4))
    mask[y0:y0 + h // 2, x0:x0 + w // 5] = 1
    image[mask == 1] = 255
    return image, mask


def denorm(x: torch.Tensor) -> torch.Tensor:
    return x * STD + MEAN


# ---------- 1. joint_transform ----------

def test_eval_transform_shapes_and_normalization(nb):
    image, mask = blob_pair(0)
    x, m = nb.joint_transform(image, mask, 64, train=False)
    assert x.shape == (3, 64, 64) and x.dtype == torch.float32
    assert m.shape == (64, 64) and m.dtype == torch.int64
    assert set(m.unique().tolist()) <= {0, 1}, "mask resize bằng nearest: chỉ còn 0 và 1"
    gray = np.tile((np.array([0.485, 0.456, 0.406]) * 255).round().astype(np.uint8), (40, 50, 1))
    xg, _ = nb.joint_transform(gray, np.zeros((40, 50), np.uint8), 32)
    assert xg.abs().max().item() < 0.02, "ảnh màu trung bình ImageNet phải về gần 0 sau chuẩn hoá"
    x2, m2 = nb.joint_transform(image, mask, 64, train=False)
    assert torch.equal(x, x2) and torch.equal(m, m2), "eval phải tất định"


def test_eval_transform_keeps_geometry(nb):
    image, mask = blob_pair(1, 80, 160)
    x, m = nb.joint_transform(image, mask, 64)
    ref = cv2.resize(mask, (64, 64), interpolation=cv2.INTER_NEAREST)
    assert (m.numpy() == ref).mean() > 0.97, "eval: resize thẳng cả ảnh và mask về size x size, không crop, không lật"
    bright = denorm(x)[0] > 0.6
    assert (bright.numpy() == (m.numpy() == 1)).mean() > 0.97


@pytest.mark.parametrize("seed", range(6))
def test_train_transform_moves_image_and_mask_together(nb, seed):
    image, mask = blob_pair(seed + 10)
    x, m = nb.joint_transform(image, mask, 64, train=True, generator=torch.Generator().manual_seed(seed))
    assert x.shape == (3, 64, 64) and m.shape == (64, 64) and m.dtype == torch.int64
    assert set(m.unique().tolist()) <= {0, 1}
    bright = (denorm(x).mean(0) > 0.6).numpy()
    agree = (bright == (m.numpy() == 1)).mean()
    assert agree > 0.95, f"ảnh và mask lệch nhau sau augmentation ({agree:.3f} pixel khớp): cùng crop, cùng lật"


def test_train_transform_is_random_and_seeded(nb):
    image, mask = blob_pair(3)
    outs = [nb.joint_transform(image, mask, 48, train=True, generator=torch.Generator().manual_seed(s))[1]
            for s in range(8)]
    assert len({o.numpy().tobytes() for o in outs}) > 2, "train: augmentation phải ngẫu nhiên theo generator"
    again = nb.joint_transform(image, mask, 48, train=True, generator=torch.Generator().manual_seed(5))
    first = nb.joint_transform(image, mask, 48, train=True, generator=torch.Generator().manual_seed(5))
    assert torch.equal(again[0], first[0]) and torch.equal(again[1], first[1]), "cùng seed generator, cùng kết quả"


def test_train_transform_flips_horizontally(nb):
    image, mask = blob_pair(4, 64, 64)
    centers = []
    for s in range(24):
        _, m = nb.joint_transform(image, mask, 64, train=True, generator=torch.Generator().manual_seed(s))
        cols = np.nonzero(m.numpy())[1]
        if cols.size:
            centers.append(cols.mean())
    assert min(centers) < 32 < max(centers), "có lật ngang: người ở nửa trái phải có lúc sang nửa phải"


# ---------- 2. UNet ----------

def test_unet_shapes(nb):
    torch.manual_seed(0)
    m = nb.UNet(3, 2, base=8).eval()
    assert m(torch.zeros(2, 3, 64, 96)).shape == (2, 2, 64, 96)
    assert nb.UNet(1, 5, base=4)(torch.zeros(1, 1, 32, 32)).shape == (1, 5, 32, 32)
    convs = [mod for mod in m.modules() if isinstance(mod, nn.Conv2d)]
    assert max(c.out_channels for c in convs) == 8 * 16, "đáy U-Net có 16·base kênh"
    assert any(isinstance(mod, nn.BatchNorm2d) for mod in m.modules())


def test_unet_has_skip_connections(nb):
    # Không skip thì mọi chi tiết phải đi qua đáy 1/16: đổi một pixel làm đổi cả vùng 16x16 trở lên.
    # Có skip ở độ phân giải đầy đủ: output gần pixel đó đổi mạnh hơn hẳn phần còn lại.
    torch.manual_seed(1)
    m = nb.UNet(3, 2, base=4).eval()
    x = torch.randn(1, 3, 64, 64, generator=torch.Generator().manual_seed(0)).requires_grad_()
    m(x)[0, 1, 30, 30].backward()
    g = x.grad.abs().sum(0)[0]
    near = g[28:33, 28:33].sum()
    assert near / g.sum() > 0.1, "logit ở (30, 30) phải phụ thuộc mạnh vào lân cận gần của nó (skip connection)"


# ---------- 3. dice_loss ----------

def test_dice_loss_values(nb):
    torch.manual_seed(2)
    logits = torch.randn(3, 2, 8, 8, requires_grad=True)
    target = torch.randint(0, 2, (3, 8, 8))
    loss = nb.dice_loss(logits, target)
    p = logits.softmax(1)[:, 1]
    t = target.float()
    ref = 1 - (2 * (p * t).sum() + 1) / (p.sum() + t.sum() + 1)
    assert loss.shape == () and torch.allclose(loss, ref, atol=1e-6)
    loss.backward()
    assert logits.grad is not None and logits.grad.abs().sum() > 0
    perfect = torch.where(target[:, None] == torch.arange(2).view(1, 2, 1, 1), 20.0, -20.0)
    assert nb.dice_loss(perfect, target).item() < 1e-3
    assert nb.dice_loss(-perfect, target).item() > 0.99
    assert torch.allclose(nb.dice_loss(logits, target, eps=0.0),
                          1 - 2 * (p * t).sum() / (p.sum() + t.sum()), atol=1e-6)


def test_dice_loss_is_batch_level(nb):
    # ảnh 1 có người lớn, ảnh 2 không có người: dice cả batch khác trung bình dice từng ảnh
    target = torch.zeros(2, 4, 4, dtype=torch.long)
    target[0, :2] = 1
    logits = torch.zeros(2, 2, 4, 4)
    logits[:, 1] = 2.0
    p = logits.softmax(1)[:, 1]
    t = target.float()
    ref = 1 - (2 * (p * t).sum() + 1) / (p.sum() + t.sum() + 1)
    assert nb.dice_loss(logits, target).item() == pytest.approx(ref.item(), abs=1e-6)


# ---------- 4. predict_mask ----------

class RedIsPerson(nn.Module):
    """Model giả: logit người là kênh 0 của input (R nếu input là RGB, sau chuẩn hoá) trừ 1.5, logit nền là 0.

    Như mọi model có BatchNorm/Dropout, nó chỉ đúng ở eval(): ở chế độ train nó trả rác (mọi pixel là người)."""

    def __init__(self):
        super().__init__()
        self.scale = nn.Parameter(torch.ones(1))

    def forward(self, x):
        person = self.scale * x[:, :1] - 1.5
        if self.training:
            person = torch.full_like(person, 10.0)
        return torch.cat([torch.zeros_like(person), person], 1)


class Stripes(nn.Module):
    """Model giả: logit người là sóng sin theo cột của input, bỏ qua nội dung ảnh: viền đổi lớp dày đặc."""

    def forward(self, x):
        cols = torch.arange(x.shape[-1], dtype=torch.float32)
        person = torch.sin(cols / 1.7).expand(x.shape[0], 1, x.shape[-2], x.shape[-1])
        return torch.cat([torch.zeros_like(person), person], 1)


def red_scene(h: int, w: int) -> tuple[np.ndarray, np.ndarray]:
    """Ảnh BGR: một vùng đỏ (người) và một vùng xanh dương (không phải người)."""
    img = np.zeros((h, w, 3), np.uint8)
    truth = np.zeros((h, w), np.uint8)
    img[h // 4: 3 * h // 4, w // 8: w // 3] = (0, 0, 255)          # BGR đỏ
    truth[h // 4: 3 * h // 4, w // 8: w // 3] = 1
    img[h // 4: 3 * h // 4, w // 2: 7 * w // 8] = (255, 0, 0)      # BGR xanh dương
    return img, truth


def test_predict_mask_bgr_resolution_and_mode(nb):
    model = RedIsPerson()
    model.train()
    img, truth = red_scene(150, 200)
    pred = nb.predict_mask(model, img, size=64)
    assert pred.shape == (150, 200) and pred.dtype == np.uint8, "mask đúng (H, W) của ảnh gốc, uint8"
    assert set(np.unique(pred).tolist()) <= {0, 1}
    acc = (pred == truth).mean()
    assert acc > 0.97, f"chỉ vùng đỏ là người ({acc:.3f} pixel đúng): đổi BGR → RGB và chạy ở eval()"
    assert model.training, "trả model về đúng chế độ như trước khi gọi"
    model.eval()
    nb.predict_mask(model, img, size=64)
    assert not model.training


def test_predict_mask_matches_eval_pipeline(nb):
    torch.manual_seed(3)
    model = nb.UNet(3, 2, base=4).eval()
    img, _ = red_scene(96, 128)
    rgb = img[..., ::-1].copy()
    x, _ = nb.joint_transform(rgb, np.zeros(rgb.shape[:2], np.uint8), 64)
    with torch.no_grad():
        logits = F.interpolate(model(x[None]), size=(96, 128), mode="bilinear", align_corners=False)
    ref = logits.argmax(1)[0].numpy()
    agree = (nb.predict_mask(model, img, size=64) == ref).mean()
    assert agree > 0.99, f"serve phải đi đúng pipeline eval của joint_transform ({agree:.3f} khớp)"


def test_predict_mask_interpolates_logits(nb):
    img, _ = red_scene(90, 200)
    logits = Stripes()(torch.zeros(1, 3, 64, 64))
    ref = F.interpolate(logits, size=(90, 200), mode="bilinear", align_corners=False).argmax(1)[0].numpy()
    agree = (nb.predict_mask(Stripes(), img, size=64) == ref).mean()
    assert agree > 0.98, f"nội suy logits (bilinear) về (H, W) rồi mới argmax ({agree:.3f} khớp)"


# ---------- báo cáo ----------

def test_report_written():
    doc = ex.read("REPORT.md")
    assert "TODO" not in doc
    assert len(doc.split()) >= 600, "báo cáo portfolio: ít nhất 600 từ"
    assert re.search(r"^\|.*\|\s*$", doc, re.M), "cần ít nhất một bảng (UNet từ đầu, encoder pretrain, YOLO-seg)"
    images = re.findall(r"!\[[^\]]*\]\(([^)\s]+)\)", doc)
    assert images, "chèn hình (ảnh val với mask dự đoán, đường loss), vd. ![](val_masks.jpg)"
    for img in images:
        if not img.startswith("http"):
            assert (ex.path("REPORT.md").parent / img).exists(), f"không thấy tệp hình {img}"

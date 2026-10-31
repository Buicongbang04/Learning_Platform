import io

import numpy as np
import pytest
import torch
from PIL import Image
from torch import nn
from torch.utils.data import DataLoader

from testkit import Exercise

ex = Exercise(__file__)
torch.set_num_threads(2)

MEAN = np.array([0.485, 0.456, 0.406])
STD = np.array([0.229, 0.224, 0.225])


@pytest.fixture(scope="module")
def nb():
    return ex.notebook("transfer.ipynb")


def png_bytes(arr: np.ndarray, mode: str | None = None) -> bytes:
    buf = io.BytesIO()
    Image.fromarray(arr, mode).save(buf, format="PNG")
    return buf.getvalue()


def fake_images(n: int, seed: int) -> tuple[list[bytes], np.ndarray]:
    """n ảnh 3 lớp: mỗi lớp một màu chủ đạo + nhiễu, cỡ khác nhau, có ảnh RGBA và ảnh xám."""
    rng = np.random.default_rng(seed)
    colors = np.array([[200, 40, 40], [40, 200, 40], [40, 40, 200]])
    images, labels = [], rng.integers(0, 3, n)
    for i, y in enumerate(labels):
        h, w = rng.integers(40, 90, 2)
        arr = np.clip(colors[y] + rng.normal(0, 30, (h, w, 3)), 0, 255).astype(np.uint8)
        if i % 7 == 3:
            arr = np.dstack([arr, np.full((h, w), 255, np.uint8)])          # RGBA
        images.append(png_bytes(arr))
    return images, labels.astype(np.int64)


# ---------- 1. dữ liệu ----------

def test_class_names(nb):
    ids = ["Maine_Coon_204", "american_bulldog_138", "Maine_Coon_1", "keeshond_112", "american_pit_bull_terrier_7"]
    labels = np.array([1, 0, 1, 3, 2])
    assert nb.class_names(labels, ids) == ["american_bulldog", "Maine_Coon", "american_pit_bull_terrier", "keeshond"]


def test_dataset_decodes_to_rgb(nb):
    gray = png_bytes(np.full((10, 12), 128, np.uint8))
    rgba = png_bytes(np.zeros((8, 8, 4), np.uint8))
    ds = nb.PetsDataset([gray, rgba], np.array([4, 2]), transform=lambda img: np.asarray(img))
    assert len(ds) == 2
    x, y = ds[0]
    assert x.shape == (10, 12, 3) and y == 4 and isinstance(y, int)
    assert ds[1][0].shape == (8, 8, 3)


# ---------- 2. transform ----------

def test_eval_transform(nb):
    t = nb.build_transforms(False, 64)
    img = Image.fromarray(np.tile((MEAN * 255).round().astype(np.uint8), (100, 150, 1)))
    x = t(img)
    assert x.shape == (3, 64, 64) and x.dtype == torch.float32
    assert x.abs().max().item() < 0.02, "ảnh màu trung bình ImageNet phải về gần 0 sau Normalize"
    white = t(Image.new("RGB", (80, 80), (255, 255, 255)))
    np.testing.assert_allclose(white[:, 0, 0].numpy(), (1 - MEAN) / STD, atol=1e-4)
    assert torch.equal(t(img), t(img)), "transform eval phải tất định"


def test_eval_transform_resize_then_center_crop(nb):
    # ảnh 200x100 (rộng x cao): cạnh ngắn 100 → 73 (64 / 0.875), rộng 146; center crop 64 bỏ viền
    arr = np.zeros((100, 200, 3), np.uint8)
    arr[:, :50] = 255                                    # dải trắng 50 cột bên trái: bị cắt hết
    x = nb.build_transforms(False, 64)(Image.fromarray(arr))
    assert x.shape == (3, 64, 64)
    np.testing.assert_allclose(x[0].numpy(), -MEAN[0] / STD[0], atol=1e-4)


def test_train_transform(nb):
    t = nb.build_transforms(True, 48)
    rng = np.random.default_rng(0)
    img = Image.fromarray(rng.integers(0, 256, (90, 120, 3)).astype(np.uint8))
    torch.manual_seed(0)
    outs = [t(img) for _ in range(6)]
    assert all(o.shape == (3, 48, 48) and o.dtype == torch.float32 for o in outs)
    assert not all(torch.equal(outs[0], o) for o in outs[1:]), "transform train phải ngẫu nhiên"
    assert -2.2 < float(torch.stack(outs).mean()) < 2.7


def test_train_transform_flips_only_horizontally(nb):
    # ảnh nửa trên trắng, nửa dưới đen: lật ngang/crop không bao giờ đưa màu trắng xuống đáy
    arr = np.zeros((64, 64, 3), np.uint8)
    arr[:32] = 255
    t = nb.build_transforms(True, 32)
    torch.manual_seed(1)
    for _ in range(30):
        x = t(Image.fromarray(arr))
        assert x[0, 0].mean() >= x[0, -1].mean(), "không lật dọc ảnh thú nuôi"


# ---------- 3. model ----------

def test_build_model(nb):
    m = nb.build_model(37)
    assert isinstance(m.fc, nn.Linear) and m.fc.in_features == 512 and m.fc.out_features == 37
    assert m(torch.zeros(2, 3, 64, 64)).shape == (2, 37)


def test_freeze_backbone(nb):
    m = nb.build_model(37)
    nb.freeze_backbone(m)
    trainable = sum(p.numel() for p in m.parameters() if p.requires_grad)
    assert trainable == 512 * 37 + 37
    assert all(p.requires_grad for p in m.fc.parameters())


def test_set_bn_eval_keeps_running_stats(nb):
    m = nb.build_model(5)
    nb.freeze_backbone(m)
    m.train()
    nb.set_bn_eval(m)
    before = m.bn1.running_mean.clone()
    m(torch.randn(4, 3, 64, 64) * 3 + 1)
    assert torch.equal(m.bn1.running_mean, before), "BN ở eval: running mean không đổi"
    assert m.fc.training is True or not any(isinstance(x, nn.Dropout) for x in m.modules())
    assert not any(b.training for b in m.modules() if isinstance(b, nn.BatchNorm2d))


def test_param_groups(nb):
    m = nb.build_model(10)
    groups = nb.param_groups(m, 1e-4, 1e-3, 0.05)
    assert all({"params", "lr", "weight_decay"} <= set(g) for g in groups)
    assert all(len(g["params"]) > 0 for g in groups), "bỏ nhóm rỗng"
    ids = [id(p) for g in groups for p in g["params"]]
    assert len(ids) == len(set(ids)) == len(list(m.parameters())), "mỗi tham số đúng một nhóm"
    lookup = {id(p): g for g in groups for p in g["params"]}
    assert lookup[id(m.fc.weight)]["lr"] == 1e-3 and lookup[id(m.fc.weight)]["weight_decay"] == 0.05
    assert lookup[id(m.fc.bias)]["lr"] == 1e-3 and lookup[id(m.fc.bias)]["weight_decay"] == 0.0
    assert lookup[id(m.conv1.weight)]["lr"] == 1e-4 and lookup[id(m.conv1.weight)]["weight_decay"] == 0.05
    assert lookup[id(m.bn1.weight)]["weight_decay"] == 0.0 and lookup[id(m.bn1.bias)]["lr"] == 1e-4
    torch.optim.AdamW(groups)                                 # optimizer nhận được

    nb.freeze_backbone(m)
    frozen = nb.param_groups(m, 1e-4, 1e-3, 0.05)
    assert sum(len(g["params"]) for g in frozen) == 2, "đóng băng: chỉ còn fc.weight và fc.bias"


# ---------- 4. feature, train, evaluate ----------

def loader_for(nb, n, seed, train=False, size=48):
    images, labels = fake_images(n, seed)
    ds = nb.PetsDataset(images, labels, nb.build_transforms(train, size))
    return DataLoader(ds, batch_size=16, shuffle=train, generator=torch.Generator().manual_seed(seed))


def test_extract_features(nb):
    torch.manual_seed(0)
    m = nb.build_model(3)
    fc = m.fc
    m.train()
    f, y = nb.extract_features(m, loader_for(nb, 20, 1))
    assert f.shape == (20, 512) and f.dtype == torch.float32 and y.dtype == torch.int64 and y.shape == (20,)
    assert m.fc is fc, "không được làm mất model.fc"
    assert not m.training
    f2, _ = nb.extract_features(m, loader_for(nb, 20, 1))
    assert torch.allclose(f, f2), "feature ở eval mode phải tất định"
    assert (f >= 0).all(), "feature sau ReLU + global average pooling, trước fc"


def test_train_and_evaluate(nb):
    torch.manual_seed(0)
    m = nb.build_model(3)
    nb.freeze_backbone(m)
    opt = torch.optim.AdamW(nb.param_groups(m, 1e-4, 3e-2, 0.0))
    dl = loader_for(nb, 48, 2, train=True)
    before = m.bn1.running_mean.clone()
    losses = [nb.train_one_epoch(m, dl, opt, freeze_bn=True) for _ in range(4)]
    assert all(isinstance(v, float) for v in losses)
    assert losses[-1] < losses[0]
    assert torch.equal(m.bn1.running_mean, before), "freeze_bn=True: BatchNorm không cập nhật running stats"
    acc = nb.evaluate(m, loader_for(nb, 30, 3))
    assert isinstance(acc, float) and acc >= 0.6, f"3 màu tách được bằng linear probe: accuracy {acc:.2f}"


def test_train_one_epoch_mean_over_samples(nb):
    torch.manual_seed(0)
    m = nb.build_model(3)
    nb.freeze_backbone(m)
    opt = torch.optim.SGD(nb.param_groups(m, 0.0, 0.0, 0.0), lr=0.0)
    images, labels = fake_images(37, 4)                      # batch 16: batch cuối 5 ảnh
    dl = DataLoader(nb.PetsDataset(images, labels, nb.build_transforms(False, 48)), batch_size=16)
    loss = nb.train_one_epoch(m, dl, opt, freeze_bn=True)
    m.eval()
    with torch.no_grad():
        xs = torch.stack([dl.dataset[i][0] for i in range(37)])
        full = torch.nn.functional.cross_entropy(m(xs), torch.as_tensor(labels)).item()
    assert loss == pytest.approx(full, rel=1e-4)


# ---------- 5. dữ liệu thật: tự skip nếu chưa tải Oxford-IIIT Pet ----------

def test_load_pets_real(nb):
    root = ex.dataset("oxford-pets")
    images, labels, ids = nb.load_pets(root, "test")
    assert len(images) == len(labels) == len(ids) == 3669
    assert isinstance(images[0], bytes) and labels.dtype == np.int64
    assert ids[:2] == ["newfoundland_31", "pug_57"] and labels[:2].tolist() == [22, 25]
    names = nb.class_names(labels, ids)
    assert len(names) == 37 and names[22] == "newfoundland" and names[0] == "Abyssinian"
    assert int(np.bincount(labels).min()) == 88

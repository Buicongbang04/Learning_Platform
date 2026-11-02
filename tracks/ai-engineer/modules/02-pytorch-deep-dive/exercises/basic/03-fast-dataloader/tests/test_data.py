import io

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq
import pytest
import torch
import torch.nn.functional as F
from PIL import Image

from testkit import Exercise

ex = Exercise(__file__)
torch.set_num_threads(1)

MEAN = torch.tensor([0.4914, 0.4822, 0.4465]).view(3, 1, 1)
STD = torch.tensor([0.2470, 0.2435, 0.2616]).view(3, 1, 1)


@pytest.fixture(scope="module")
def m():
    return ex.module("data.py")


def random_images(n: int, seed: int) -> np.ndarray:
    return np.random.default_rng(seed).integers(0, 256, size=(n, 32, 32, 3), dtype=np.uint8)


@pytest.fixture
def tiny_parquet(tmp_path):
    imgs = random_images(12, 0)
    rows = []
    for a in imgs:
        buf = io.BytesIO()
        Image.fromarray(a).save(buf, format="PNG")
        rows.append({"bytes": buf.getvalue(), "path": None})
    labels = np.array([3, 1, 4, 1, 5, 9, 2, 6, 5, 3, 5, 8])
    path = tmp_path / "tiny.parquet"
    pq.write_table(pa.table({"img": rows, "label": labels}), path)
    return path, imgs, labels


def crops_of(img: torch.Tensor, pad: int = 4) -> list[torch.Tensor]:
    """Mọi ảnh có thể sinh ra: cắt tại 81 vị trí của bản pad reflect, có lật và không lật."""
    padded = F.pad(img.unsqueeze(0).float(), (pad, pad, pad, pad), mode="reflect")[0]
    h, w = img.shape[1:]
    out = []
    for dy in range(2 * pad + 1):
        for dx in range(2 * pad + 1):
            c = padded[:, dy:dy + h, dx:dx + w]
            out += [c, c.flip(2)]
    return out


def is_crop(out: torch.Tensor, img: torch.Tensor) -> bool:
    return any(torch.equal(out.float(), c) for c in crops_of(img))


# ---------- decode ----------

def test_decode_fixture(m, tiny_parquet):
    path, imgs, labels = tiny_parquet
    x, y = m.decode_cifar_parquet(path)
    assert x.dtype == torch.uint8 and x.shape == (12, 3, 32, 32) and x.is_contiguous()
    assert y.dtype == torch.int64 and y.tolist() == labels.tolist()
    np.testing.assert_array_equal(x.permute(0, 2, 3, 1).numpy(), imgs, err_msg="HWC -> CHW bằng permute, không phải view")


def test_decode_real_cifar(m):
    root = ex.dataset("cifar10") / "plain_text"
    x, y = m.decode_cifar_parquet(root / "test-00000-of-00001.parquet")
    assert x.shape == (10000, 3, 32, 32)
    assert torch.bincount(y).tolist() == [1000] * 10
    assert y[:8].tolist() == [3, 8, 8, 0, 6, 6, 1, 6]


# ---------- Dataset ----------

def test_dataset_no_augment(m):
    imgs = torch.from_numpy(random_images(5, 1)).permute(0, 3, 1, 2).contiguous()
    labels = torch.arange(5)
    ds = m.CifarDataset(imgs, labels)
    assert len(ds) == 5
    x, y = ds[2]
    assert x.dtype == torch.float32 and x.shape == (3, 32, 32) and y == 2 and isinstance(y, int)
    torch.testing.assert_close(x, (imgs[2].float() / 255 - MEAN) / STD)


def test_dataset_augment_is_crop_flip(m):
    imgs = torch.from_numpy(random_images(3, 2)).permute(0, 3, 1, 2).contiguous()
    ds = m.CifarDataset(imgs, torch.zeros(3, dtype=torch.long), augment=True, seed=5)
    flips = []
    for i in range(3):
        for _ in range(4):
            x, _ = ds[i]
            raw = torch.round((x * STD + MEAN) * 255)
            assert is_crop(raw, imgs[i]), "augment = pad reflect 4, cắt 32x32, lật ngang"
            flips.append(not any(torch.equal(raw, c) for c in crops_of(imgs[i])[::2]))
    assert 0 < sum(flips) < len(flips), "lật ngang ngẫu nhiên, không phải luôn hay không bao giờ"
    a = m.CifarDataset(imgs, torch.zeros(3, dtype=torch.long), augment=True, seed=7)
    b = m.CifarDataset(imgs, torch.zeros(3, dtype=torch.long), augment=True, seed=7)
    assert all(torch.equal(a[i][0], b[i][0]) for i in range(3)), "cùng seed, cùng augmentation"


# ---------- DataLoader tái lập ----------

def _same_image_dataset(m, seed: int = 0):
    img = torch.from_numpy(random_images(1, 3)).permute(0, 3, 1, 2)
    return m.CifarDataset(img.repeat(16, 1, 1, 1).contiguous(), torch.arange(16), augment=True, seed=seed)


def test_loader_workers_get_different_streams(m):
    loader = m.make_loader(_same_image_dataset(m), batch_size=4, shuffle=False, num_workers=2, seed=0)
    batches = [x for x, _ in loader]
    assert len(batches) == 4
    # Batch 0 do worker 0 làm, batch 1 do worker 1 làm. Cùng 4 ảnh giống hệt nhau: nếu hai worker mang
    # bản sao của cùng một self.rng thì augmentation trùng nhau từng pixel.
    assert not torch.equal(batches[0], batches[1]), "mỗi worker cần dòng số ngẫu nhiên riêng (worker_init_fn)"


def test_loader_reproducible_with_workers(m):
    def run(seed):
        loader = m.make_loader(_same_image_dataset(m), batch_size=4, shuffle=True, num_workers=2, seed=seed)
        return [(x.clone(), y.clone()) for x, y in loader]

    a, b, c = run(0), run(0), run(1)
    assert all(torch.equal(xa, xb) and torch.equal(ya, yb) for (xa, ya), (xb, yb) in zip(a, b)), (
        "cùng seed: cùng thứ tự và cùng augmentation"
    )
    assert any(not torch.equal(ya, yc) for (_, ya), (_, yc) in zip(a, c)), "seed khác: thứ tự xáo khác"
    assert sorted(torch.cat([y for _, y in a]).tolist()) == list(range(16))


def test_loader_options(m):
    ds = _same_image_dataset(m)
    loader = m.make_loader(ds, batch_size=8, shuffle=False, num_workers=2, seed=0)
    assert loader.persistent_workers is True and loader.worker_init_fn is m.seed_worker
    assert loader.pin_memory == torch.cuda.is_available()
    assert m.make_loader(ds, 8, False, 0, 0).persistent_workers is False


# ---------- augment_batch ----------

def test_augment_batch_crops(m):
    x = torch.from_numpy(random_images(24, 4)).permute(0, 3, 1, 2).contiguous()
    out = m.augment_batch(x, torch.Generator().manual_seed(0))
    assert out.dtype == torch.uint8 and out.shape == x.shape
    for i in range(24):
        assert is_crop(out[i], x[i]), f"ảnh {i} không phải một crop (có thể lật) của chính nó"


def test_augment_batch_random_and_deterministic(m):
    x = torch.from_numpy(random_images(200, 5)).permute(0, 3, 1, 2).float()
    a = m.augment_batch(x, torch.Generator().manual_seed(1))
    b = m.augment_batch(x, torch.Generator().manual_seed(1))
    c = m.augment_batch(x, torch.Generator().manual_seed(2))
    assert a.dtype == torch.float32
    assert torch.equal(a, b) and not torch.equal(a, c)
    centre_noflip = sum(torch.equal(a[i], x[i]) for i in range(200))
    assert centre_noflip < 20, "vị trí cắt và lật phải ngẫu nhiên theo từng ảnh"
    padded = F.pad(x, (4, 4, 4, 4), mode="reflect")
    flipped = 0
    for i in range(200):
        ok = [torch.equal(a[i], padded[i, :, dy:dy + 32, dx:dx + 32]) for dy in range(9) for dx in range(9)]
        flipped += not any(ok)
    assert 60 <= flipped <= 140, f"lật với xác suất 0.5, đếm được {flipped}/200"

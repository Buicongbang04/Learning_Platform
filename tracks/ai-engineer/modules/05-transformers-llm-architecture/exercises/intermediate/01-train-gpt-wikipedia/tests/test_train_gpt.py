import math

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq
import pytest
import torch
import torch.nn as nn
import torch.nn.functional as F
from testkit import Exercise

ex = Exercise(__file__)
torch.set_num_threads(1)


@pytest.fixture(scope="module")
def nb():
    return ex.notebook("train_gpt.ipynb")


class PrefixMeanLM(nn.Module):
    """Model nhân quả tí hon: logits ở vị trí t phụ thuộc trung bình embedding của 0..t (ngữ cảnh có ảnh hưởng)."""

    def __init__(self, vocab: int = 23, dim: int = 8):
        super().__init__()
        torch.manual_seed(0)
        self.emb = nn.Embedding(vocab, dim)
        self.out = nn.Linear(dim, vocab)
        self.calls = []

    def forward(self, idx, targets=None):
        self.calls.append(tuple(idx.shape))
        h = self.emb(idx).cumsum(1) / torch.arange(1, idx.shape[1] + 1)[None, :, None]
        return self.out(torch.tanh(3 * h)), None


def reference_nll(model, ids, block, stride):
    total, count, scored, start = 0.0, 0, 0, 0
    n = len(ids)
    while scored < n - 1:
        end = min(start + block, n - 1)
        logits = model(ids[start:end][None])[0][0]
        nll = F.cross_entropy(logits, ids[start + 1:end + 1], reduction="none")
        k = end - scored
        total += nll[-k:].sum().item()
        count += k
        scored, start = end, start + stride
    return total, count


def test_long_articles_and_split(nb, tmp_path):
    texts = ["a" * 5, "Hoa\u0300" * 3, "x" * 12, "ngắn", "y" * 10]
    path = tmp_path / "t.parquet"
    pq.write_table(pa.table({"id": list(range(5)), "text": texts}), path)
    arts = nb.long_articles(path, 10)
    assert arts == ["Ho\u00e0" * 3, "x" * 12, "y" * 10], "lọc theo độ dài gốc (NFD dài hơn), rồi NFC, giữ thứ tự"
    items = [f"bài {i}" for i in range(10)]
    train, val = nb.split_articles(items, 6, 3, seed=0)
    perm = np.random.RandomState(0).permutation(10)
    assert train == [items[i] for i in perm[:6]] and val == [items[i] for i in perm[6:9]]


def test_split_matches_module04_on_real_data(nb):
    root = ex.dataset("wikipedia-vi")
    arts = nb.long_articles(root / "20231101.vi/train-00002-of-00004.parquet", 2000)
    assert len(arts) == 5413
    train, val = nb.split_articles(arts, 1000, 100, seed=0)
    assert len("\n\n".join(train)) == 6_432_422 and len("\n\n".join(val)) == 664_568, \
        "đúng tập train/validation của module 04 (Advanced 02)"


def test_get_batch(nb):
    data = torch.arange(100, 140)
    g = torch.Generator().manual_seed(3)
    x, y = nb.get_batch(data, 5, 8, g)
    starts = torch.randint(40 - 8, (5,), generator=torch.Generator().manual_seed(3))
    assert x.shape == (5, 8) and x.dtype == torch.long
    for b, s in enumerate(starts.tolist()):
        assert x[b].tolist() == list(range(100 + s, 108 + s)) and y[b].tolist() == list(range(101 + s, 109 + s))
    seen = set()
    g = torch.Generator().manual_seed(4)
    for _ in range(300):
        x, y = nb.get_batch(torch.arange(12), 4, 8, g)
        seen.update(x[:, 0].tolist())
    assert seen == {0, 1, 2, 3}, "vị trí bắt đầu phủ 0 .. len - block_size - 1, y không vượt ra ngoài"


def test_lr_schedule(nb):
    lrs = [nb.lr_at(s, 1e-3, 10, 110, 1e-4) for s in range(130)]
    assert lrs[0] == pytest.approx(1e-4) and lrs[9] == pytest.approx(1e-3)
    assert lrs[10] == pytest.approx(1e-3)
    assert lrs[60] == pytest.approx(1e-4 + 0.5 * 9e-4)
    assert lrs[109] == pytest.approx(1e-4, abs=1e-6) and lrs[125] == pytest.approx(1e-4)
    assert all(a >= b - 1e-12 for a, b in zip(lrs[10:110], lrs[11:111])), "giảm đơn điệu sau warmup"


def test_configure_optimizer(nb):
    model = nn.Sequential(nn.Embedding(10, 4), nn.LayerNorm(4), nn.Linear(4, 10))
    model[2].weight = model[0].weight
    opt = nb.configure_optimizer(model, 3e-4, 0.1)
    assert isinstance(opt, torch.optim.AdamW)
    assert opt.defaults["betas"] == (0.9, 0.95) and opt.defaults["lr"] == 3e-4
    by_decay = {g["weight_decay"]: {id(p) for p in g["params"]} for g in opt.param_groups}
    assert by_decay[0.1] == {id(model[0].weight)}, "chỉ ma trận chịu weight decay; tham số dùng chung đếm một lần"
    assert by_decay[0.0] == {id(model[1].weight), id(model[1].bias), id(model[2].bias)}


def test_sliding_windows(nb):
    w = nb.sliding_windows(21, 8, 4)
    assert w[0] == (0, 8, 8)
    assert w[1] == (4, 12, 4)
    assert w[-1][1] == 20
    assert sum(k for _, _, k in w) == 20, "mỗi target x_1..x_{n-1} được tính đúng một lần"
    for s, e, k in w[1:]:
        assert e - k - s >= 8 - 4, "mọi target (trừ cửa sổ đầu) có ít nhất block - stride token ngữ cảnh"
    assert nb.sliding_windows(17, 8, 8) == [(0, 8, 8), (8, 16, 8)]
    assert nb.sliding_windows(5, 8, 4) == [(0, 4, 4)]


@pytest.mark.parametrize("n,block,stride,batch", [(57, 8, 4, 3), (40, 16, 16, 32), (30, 8, 2, 5)])
def test_evaluate_nll_matches_reference(nb, n, block, stride, batch):
    model = PrefixMeanLM().train()
    ids = torch.randint(0, 23, (n,), generator=torch.Generator().manual_seed(n))
    total, count = nb.evaluate_nll(model, ids, block, stride, batch_size=batch)
    assert model.training, "trả lại chế độ train"
    ref_total, ref_count = reference_nll(model, ids, block, stride)
    assert count == ref_count == n - 1
    assert total == pytest.approx(ref_total, rel=1e-5)


def test_evaluate_nll_batches_windows(nb):
    model = PrefixMeanLM()
    ids = torch.randint(0, 23, (200,), generator=torch.Generator().manual_seed(1))
    nb.evaluate_nll(model, ids, 16, 8, batch_size=32)
    assert len(model.calls) <= 3 and max(c[0] for c in model.calls) > 1, "gom các cửa sổ cùng độ dài thành batch"


def test_nll_to_metrics(nb):
    m = nb.nll_to_metrics(1000 * math.log(50), 1000, 4000)
    assert m["ppl"] == pytest.approx(50.0)
    assert m["bits_per_token"] == pytest.approx(math.log2(50))
    assert m["bpc"] == pytest.approx(math.log2(50) / 4)

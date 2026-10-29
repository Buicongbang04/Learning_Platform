import pytest
import torch
from torch import nn

from testkit import Exercise

ex = Exercise(__file__)
torch.set_num_threads(2)
torch.use_deterministic_algorithms(True)


@pytest.fixture(scope="module")
def nb():
    return ex.notebook("fashion_cnn.ipynb")


def stripes(n: int, seed: int, size: int = 8, noise: float = 0.35):
    """Ảnh giả uint8 (n, size, size), 4 lớp: vạch ngang, vạch dọc, chéo chính, chéo phụ.

    Vị trí vạch ngẫu nhiên nên model phải nhận ra HÌNH, không phải pixel cố định.
    """
    g = torch.Generator().manual_seed(seed)
    y = torch.randint(0, 4, (n,), generator=g)
    img = torch.zeros(n, size, size)
    pos = torch.randint(1, size - 1, (n,), generator=g)
    idx = torch.arange(size)
    for i in range(n):
        p, c = pos[i].item(), y[i].item()
        if c == 0:
            img[i, p, :] = 1
        elif c == 1:
            img[i, :, p] = 1
        else:
            off = p - size // 2
            rows = idx
            cols = (idx + off) % size if c == 2 else (size - 1 - idx + off) % size
            img[i, rows, cols] = 1
    img = img + noise * torch.randn(n, size, size, generator=g)
    return (img.clamp(0, 1) * 255).round().to(torch.uint8), y


def test_standardize_shapes_and_stats(nb):
    raw, _ = stripes(200, 0)
    X, mean, std = nb.standardize(raw)
    assert X.shape == (200, 1, 8, 8) and X.dtype == torch.float32
    assert isinstance(mean, float) and isinstance(std, float)
    assert X.mean().item() == pytest.approx(0.0, abs=1e-4)
    assert X.std().item() == pytest.approx(1.0, abs=1e-3)
    pixels = raw.float() / 255
    assert mean == pytest.approx(pixels.mean().item(), rel=1e-5)


def test_standardize_reuses_train_statistics(nb):
    raw_tr, _ = stripes(200, 1)
    raw_te, _ = stripes(50, 2, noise=0.1)
    _, mean, std = nb.standardize(raw_tr)
    X_te, mean2, std2 = nb.standardize(raw_te, mean, std)
    assert (mean2, std2) == (mean, std)
    expected = ((raw_te.float() / 255) - mean) / std
    torch.testing.assert_close(X_te, expected.unsqueeze(1))


@pytest.mark.parametrize("size", [8, 28])
def test_models_output_logits(nb, size):
    x = torch.randn(5, 1, size, size)
    for model in (nb.build_mlp(size, 10), nb.build_cnn(size, 10)):
        model.eval()
        assert model(x).shape == (5, 10)


def test_build_cnn_rejects_bad_size(nb):
    with pytest.raises(ValueError):
        nb.build_cnn(30, 10)


def test_build_cnn_uses_convolutions(nb):
    model = nb.build_cnn(28, 10)
    assert sum(isinstance(m, nn.Conv2d) for m in model.modules()) >= 2
    assert any(isinstance(m, nn.Dropout) for m in model.modules())


def test_count_params(nb):
    model = nn.Sequential(nn.Conv2d(1, 4, 3), nn.Flatten(), nn.Linear(4 * 6 * 6, 3))
    assert nb.count_params(model) == (1 * 4 * 9 + 4) + (144 * 3 + 3)
    model[0].weight.requires_grad_(False)
    assert nb.count_params(model) == 4 + 144 * 3 + 3        # chỉ đếm tham số train được


def test_train_model_is_deterministic(nb):
    raw, y = stripes(256, 3)
    X, _, _ = nb.standardize(raw)
    losses = []
    for _ in range(2):
        torch.manual_seed(0)
        model = nb.build_cnn(8, 4)
        losses.append(nb.train_model(model, X, y, epochs=2, lr=1e-3, batch_size=32, seed=7))
    assert len(losses[0]) == 2 and all(isinstance(v, float) for v in losses[0])
    assert losses[0] == losses[1]


def test_predict_is_eval_mode_and_batched(nb):
    raw, y = stripes(300, 4)
    X, _, _ = nb.standardize(raw)
    torch.manual_seed(1)
    model = nb.build_cnn(8, 4)
    model.train()
    p1 = nb.predict(model, X, batch_size=64)
    p2 = nb.predict(model, X, batch_size=300)
    assert p1.shape == (300,) and p1.dtype == torch.long
    assert torch.equal(p1, p2)                              # dropout tắt, không phụ thuộc cỡ batch


def test_cnn_learns_shapes_on_8x8(nb):
    raw_tr, y_tr = stripes(2000, 10)
    raw_te, y_te = stripes(600, 11)
    X_tr, mean, std = nb.standardize(raw_tr)
    X_te, _, _ = nb.standardize(raw_te, mean, std)
    torch.manual_seed(0)
    model = nb.build_cnn(8, 4)
    losses = nb.train_model(model, X_tr, y_tr, epochs=8, lr=3e-3, batch_size=64, seed=0)
    assert losses[-1] < losses[0]
    acc = (nb.predict(model, X_te) == y_te).float().mean().item()
    assert acc > 0.9


def test_confusion_matrix(nb):
    y_true = torch.tensor([0, 0, 1, 2, 2, 2])
    y_pred = torch.tensor([0, 1, 1, 2, 0, 2])
    cm = nb.confusion_matrix(y_true, y_pred, 3)
    assert cm.tolist() == [[1, 1, 0], [0, 1, 0], [1, 0, 2]]   # hàng = nhãn thật, cột = dự đoán
    assert cm.sum().item() == 6

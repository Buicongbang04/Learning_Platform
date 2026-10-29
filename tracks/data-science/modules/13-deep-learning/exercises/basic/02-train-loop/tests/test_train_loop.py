import copy

import pytest
import torch
from torch import nn
from torch.utils.data import DataLoader, TensorDataset

from testkit import Exercise

ex = Exercise(__file__)
torch.set_num_threads(1)
torch.use_deterministic_algorithms(True)


@pytest.fixture(scope="module")
def tl():
    return ex.module("train_loop.py")


def blobs(n: int, seed: int, n_classes: int = 3, noise: float = 0.6):
    """n điểm 2 chiều quanh n_classes tâm cố định."""
    g = torch.Generator().manual_seed(seed)
    centers = torch.tensor([[2.0, 0.0], [-1.0, 1.7], [-1.0, -1.7]])[:n_classes]
    y = torch.randint(0, n_classes, (n,), generator=g)
    X = centers[y] + noise * torch.randn(n, 2, generator=g)
    return X, y


def loader(X, y, batch_size=16, shuffle=False, seed=0):
    g = torch.Generator().manual_seed(seed)
    return DataLoader(TensorDataset(X, y), batch_size=batch_size, shuffle=shuffle, generator=g)


def small_mlp(seed: int = 0, dropout: float = 0.0):
    torch.manual_seed(seed)
    return nn.Sequential(nn.Linear(2, 16), nn.ReLU(), nn.Dropout(dropout), nn.Linear(16, 3))


class ModeSpy:
    """Ghi lại model.training và torch.is_grad_enabled() ở mỗi lần forward."""

    def __init__(self, model):
        self.calls = []
        model.register_forward_hook(lambda m, i, o: self.calls.append((m.training, torch.is_grad_enabled())))


def test_train_one_epoch_returns_per_sample_mean(tl):
    X, y = blobs(50, 0)                  # 50 = 3 batch 16 + 1 batch 2: batch cuối lệch cỡ
    model = small_mlp()
    loss_fn = nn.CrossEntropyLoss()
    with torch.no_grad():
        expected = loss_fn(model(X), y).item()
    opt = torch.optim.SGD(model.parameters(), lr=0.0)   # lr = 0: tham số không đổi trong epoch
    got = tl.train_one_epoch(model, loader(X, y), loss_fn, opt)
    assert isinstance(got, float)
    assert got == pytest.approx(expected, rel=1e-5)     # không phải trung bình của các batch


def test_train_one_epoch_puts_model_in_train_mode(tl):
    X, y = blobs(32, 1)
    model = small_mlp(dropout=0.5)
    model.eval()
    spy = ModeSpy(model)
    tl.train_one_epoch(model, loader(X, y), nn.CrossEntropyLoss(), torch.optim.SGD(model.parameters(), lr=0.1))
    assert spy.calls and all(training and grad for training, grad in spy.calls)


def test_train_one_epoch_matches_reference_steps(tl):
    X, y = blobs(48, 2)
    model = small_mlp(3)
    ref = copy.deepcopy(model)
    loss_fn = nn.CrossEntropyLoss()
    tl.train_one_epoch(model, loader(X, y), loss_fn, torch.optim.SGD(model.parameters(), lr=0.5, momentum=0.9))
    opt = torch.optim.SGD(ref.parameters(), lr=0.5, momentum=0.9)
    for xb, yb in loader(X, y):          # vòng chuẩn: zero_grad, forward, backward, step
        opt.zero_grad()
        loss_fn(ref(xb), yb).backward()
        opt.step()
    for p, q in zip(model.parameters(), ref.parameters()):
        torch.testing.assert_close(p, q)


def test_evaluate_uses_eval_mode_and_no_grad(tl):
    X, y = blobs(40, 3)
    model = small_mlp(dropout=0.5)
    spy = ModeSpy(model)
    out1 = tl.evaluate(model, loader(X, y), nn.CrossEntropyLoss())
    out2 = tl.evaluate(model, loader(X, y), nn.CrossEntropyLoss())
    assert spy.calls and all(not training and not grad for training, grad in spy.calls)
    assert out1 == out2                  # dropout tắt: đánh giá hai lần ra y hệt


def test_evaluate_values(tl):
    X, y = blobs(50, 4)
    model = small_mlp(5)
    loss_fn = nn.CrossEntropyLoss()
    out = tl.evaluate(model, loader(X, y, batch_size=16), loss_fn)
    with torch.no_grad():
        logits = model(X)
    assert set(out) == {"loss", "accuracy"}
    assert isinstance(out["loss"], float) and isinstance(out["accuracy"], float)
    assert out["loss"] == pytest.approx(loss_fn(logits, y).item(), rel=1e-5)
    assert out["accuracy"] == pytest.approx((logits.argmax(1) == y).float().mean().item())


def test_fit_learns_separable_blobs(tl):
    X, y = blobs(300, 5, noise=0.4)
    Xv, yv = blobs(200, 6, noise=0.4)
    model = small_mlp(7)
    opt = torch.optim.Adam(model.parameters(), lr=0.02)
    hist = tl.fit(model, loader(X, y, 32, shuffle=True), loader(Xv, yv, 64), nn.CrossEntropyLoss(), opt,
                  max_epochs=30, patience=5)
    assert {"train_loss", "val_loss", "best_epoch"} <= set(hist)
    assert tl.evaluate(model, loader(Xv, yv, 64), nn.CrossEntropyLoss())["accuracy"] > 0.95


def _overfit_setup(seed):
    # 24 điểm train với nhãn ngẫu nhiên + model rộng: train loss giảm mãi, val loss tăng sớm
    g = torch.Generator().manual_seed(seed)
    X = torch.randn(24, 2, generator=g)
    y = torch.randint(0, 3, (24,), generator=g)
    Xv, yv = blobs(200, seed + 100)
    torch.manual_seed(seed)
    model = nn.Sequential(nn.Linear(2, 128), nn.ReLU(), nn.Linear(128, 128), nn.ReLU(), nn.Linear(128, 3))
    opt = torch.optim.Adam(model.parameters(), lr=0.01)
    return model, opt, loader(X, y, 8, shuffle=True, seed=seed), loader(Xv, yv, 50)


@pytest.mark.parametrize("seed", [0, 2, 4])
def test_fit_early_stopping_and_restores_best(tl, seed):
    model, opt, tr, va = _overfit_setup(seed)
    hist = tl.fit(model, tr, va, nn.CrossEntropyLoss(), opt, max_epochs=200, patience=4)
    val = hist["val_loss"]
    assert len(hist["train_loss"]) == len(val)
    best = hist["best_epoch"]
    assert best == min(range(len(val)), key=val.__getitem__)       # epoch đánh số từ 0
    assert len(val) == best + 1 + 4                                # dừng đúng sau 4 epoch không cải thiện
    assert len(val) < 200
    # model sau fit mang trọng số của epoch tốt nhất, không phải epoch cuối
    restored = tl.evaluate(model, va, nn.CrossEntropyLoss())["loss"]
    assert restored == pytest.approx(val[best], rel=1e-5)


def test_fit_runs_max_epochs_when_patience_never_triggers(tl):
    X, y = blobs(100, 8)
    model = small_mlp(9)
    opt = torch.optim.SGD(model.parameters(), lr=0.05)
    hist = tl.fit(model, loader(X, y), loader(X, y), nn.CrossEntropyLoss(), opt, max_epochs=3, patience=10)
    assert len(hist["val_loss"]) == 3

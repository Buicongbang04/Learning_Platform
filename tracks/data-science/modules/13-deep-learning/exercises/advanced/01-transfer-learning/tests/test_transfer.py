import pytest
import torch
from torch import nn

from testkit import Exercise

ex = Exercise(__file__)
torch.set_num_threads(2)
torch.use_deterministic_algorithms(True)


@pytest.fixture(scope="module")
def tf():
    return ex.module("transfer.py")


def small_cnn(n_classes=5, seed=0):
    torch.manual_seed(seed)
    return nn.Sequential(
        nn.Conv2d(1, 8, 3, padding=1), nn.ReLU(), nn.MaxPool2d(2),
        nn.Conv2d(8, 16, 3, padding=1), nn.ReLU(), nn.MaxPool2d(2),
        nn.Flatten(), nn.Linear(16 * 2 * 2, 32), nn.ReLU(), nn.Linear(32, n_classes),
    )


def test_select_classes_remaps_labels(tf):
    X = torch.arange(8).float().view(8, 1, 1, 1)
    y = torch.tensor([5, 0, 7, 5, 9, 7, 1, 9])
    Xs, ys = tf.select_classes(X, y, classes=[7, 5, 9])
    assert Xs.flatten().tolist() == [0, 2, 3, 4, 5, 7]          # giữ thứ tự gốc
    assert ys.tolist() == [1, 0, 1, 2, 0, 2]                    # nhãn mới = vị trí trong `classes`
    assert ys.dtype == torch.long


def test_few_shot_indices(tf):
    y = torch.tensor([0, 1, 2] * 20)
    idx = tf.few_shot_indices(y, n_per_class=4, seed=0)
    assert idx.dtype == torch.long and len(idx) == 12
    assert len(set(idx.tolist())) == 12
    assert torch.bincount(y[idx]).tolist() == [4, 4, 4]
    assert torch.equal(idx, tf.few_shot_indices(y, 4, seed=0))
    assert not torch.equal(idx, tf.few_shot_indices(y, 4, seed=1))
    with pytest.raises(ValueError):
        tf.few_shot_indices(y, n_per_class=21, seed=0)


def test_replace_head_keeps_backbone(tf):
    model = small_cnn(5)
    before = {k: v.clone() for k, v in model.state_dict().items() if not k.startswith("9.")}
    out = tf.replace_head(model, 3)
    assert out is model
    assert isinstance(model[-1], nn.Linear)
    assert (model[-1].in_features, model[-1].out_features) == (32, 3)
    after = model.state_dict()
    for k, v in before.items():
        torch.testing.assert_close(after[k], v)
    assert model(torch.randn(2, 1, 8, 8)).shape == (2, 3)


def test_freeze_backbone(tf):
    model = small_cnn()
    tf.freeze_backbone(model)
    head = set(map(id, model[-1].parameters()))
    for p in model.parameters():
        assert p.requires_grad == (id(p) in head)


def test_make_optimizer_groups(tf):
    model = small_cnn()
    opt = tf.make_optimizer(model, head_lr=1e-2, backbone_lr=1e-4, weight_decay=0.01)
    assert isinstance(opt, torch.optim.AdamW)
    lrs = sorted(g["lr"] for g in opt.param_groups)
    assert lrs == [1e-4, 1e-2]
    head_group = next(g for g in opt.param_groups if g["lr"] == 1e-2)
    assert set(map(id, head_group["params"])) == set(map(id, model[-1].parameters()))
    n_opt = sum(p.numel() for g in opt.param_groups for p in g["params"])
    assert n_opt == sum(p.numel() for p in model.parameters())
    assert all(g["weight_decay"] == 0.01 for g in opt.param_groups)


def test_make_optimizer_skips_frozen(tf):
    model = small_cnn()
    tf.freeze_backbone(model)
    opt = tf.make_optimizer(model, head_lr=1e-2, backbone_lr=1e-4)
    params = [p for g in opt.param_groups for p in g["params"]]
    assert set(map(id, params)) == set(map(id, model[-1].parameters()))
    assert [g["lr"] for g in opt.param_groups if g["params"]] == [1e-2]


def test_fine_tune_frozen_backbone_does_not_move(tf):
    model = small_cnn()
    tf.replace_head(model, 2)
    tf.freeze_backbone(model)
    backbone = {k: v.clone() for k, v in model.state_dict().items() if not k.startswith("9.")}
    head_before = model[-1].weight.clone()
    g = torch.Generator().manual_seed(0)
    X, y = torch.randn(64, 1, 8, 8, generator=g), torch.randint(0, 2, (64,), generator=g)
    opt = tf.make_optimizer(model, head_lr=1e-2, backbone_lr=1e-3, weight_decay=0.1)
    losses = tf.fine_tune(model, X, y, epochs=3, optimizer=opt, batch_size=16, seed=0)
    assert len(losses) == 3 and all(isinstance(v, float) for v in losses)
    for k, v in model.state_dict().items():
        if k in backbone:
            torch.testing.assert_close(v, backbone[k])          # weight decay cũng không được chạm vào
    assert not torch.allclose(model[-1].weight, head_before)


def test_pretrained_features_help_few_shot(tf):
    """Nguồn: phân biệt vạch ngang/dọc. Đích: 2 lớp mới (chéo chính/chéo phụ), chỉ 6 ảnh mỗi lớp.

    Backbone đã học "phát hiện đường thẳng" nên linear probe trên nó phải tốt hơn hẳn đoán mò.
    """
    def lines(n, kinds, seed):
        g = torch.Generator().manual_seed(seed)
        y = torch.randint(0, len(kinds), (n,), generator=g)
        img = 0.3 * torch.randn(n, 1, 8, 8, generator=g)
        pos = torch.randint(1, 7, (n,), generator=g)
        r = torch.arange(8)
        for i in range(n):
            k, p = kinds[y[i]], pos[i].item()
            if k == "h":
                img[i, 0, p, :] += 1
            elif k == "v":
                img[i, 0, :, p] += 1
            elif k == "d":
                img[i, 0, r, (r + p - 4) % 8] += 1
            else:
                img[i, 0, r, (7 - r + p - 4) % 8] += 1
        return img, y

    Xs, ys = lines(1500, ["h", "v", "d", "a"], 0)
    model = small_cnn(4, seed=1)
    opt = tf.make_optimizer(model, head_lr=3e-3, backbone_lr=3e-3)
    tf.fine_tune(model, Xs, ys, epochs=6, optimizer=opt, batch_size=64, seed=0)
    Xt, yt = lines(400, ["d", "a"], 1)
    idx = tf.few_shot_indices(yt[:200], n_per_class=6, seed=0)
    tf.replace_head(model, 2)
    tf.freeze_backbone(model)
    opt = tf.make_optimizer(model, head_lr=1e-2, backbone_lr=0.0)
    tf.fine_tune(model, Xt[idx], yt[idx], epochs=60, optimizer=opt, batch_size=12, seed=0)
    model.eval()
    with torch.no_grad():
        acc = (model(Xt[200:]).argmax(1) == yt[200:]).float().mean().item()
    assert acc > 0.9                     # backbone ngẫu nhiên: 0.60–0.82 trên 10 seed


def test_report_written():
    doc = ex.read("REPORT.md")
    assert "TODO" not in doc
    assert len(doc.split()) >= 400

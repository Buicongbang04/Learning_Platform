import math

import pytest
import torch
import torch.nn.functional as F
from torch import nn

from testkit import Exercise

ex = Exercise(__file__)
torch.set_num_threads(1)


@pytest.fixture(scope="module")
def nb():
    return ex.notebook("amp.ipynb")


# ---------- cast_report ----------

def test_cast_report_fp16(nb):
    t = torch.tensor([1e-9, -1e-9, 1.0, -2.0, 1e5, 0.0, float("inf"), float("nan"), 1.0 + 2**-12])
    r = nb.cast_report(t, torch.float16)
    assert set(r) == {"underflow", "overflow", "rel_err"} and all(isinstance(v, float) for v in r.values())
    assert r["underflow"] == pytest.approx(2 / 6), "chỉ đếm trên phần tử hữu hạn, khác 0 (6 phần tử)"
    assert r["overflow"] == pytest.approx(1 / 6)
    # còn lại 1.0, -2.0 (chính xác) và 1 + 2^-12 (làm tròn về 1): trung vị sai số tương đối là 0
    assert r["rel_err"] == pytest.approx(0.0, abs=1e-12)


def test_cast_report_rel_err_and_bf16(nb):
    t = torch.tensor([3.14159265, 1e-9, 7e4], dtype=torch.float64)
    r = nb.cast_report(t, torch.bfloat16)
    assert r["underflow"] == 0.0 and r["overflow"] == 0.0
    expected = sorted(abs(t.to(torch.bfloat16).double() - t) / t)[1].item()
    assert r["rel_err"] == pytest.approx(expected, rel=1e-6)
    assert nb.cast_report(torch.zeros(4), torch.float16) == {"underflow": 0.0, "overflow": 0.0, "rel_err": 0.0}


# ---------- DynamicLossScaler ----------

def _toy(seed=0):
    torch.manual_seed(seed)
    lin = nn.Linear(4, 2)
    return lin, torch.optim.SGD(lin.parameters(), lr=0.1, momentum=0.9)


def _manual_loop(scaler, inf_at, steps=9):
    lin, opt = _toy()
    trace = []
    g = torch.Generator().manual_seed(1)
    for t in range(steps):
        x = torch.randn(8, 4, generator=g)
        if t in inf_at:
            x[0, 0] = float("inf")
        loss = F.cross_entropy(lin(x), torch.randint(0, 2, (8,), generator=g))
        opt.zero_grad()
        scaler.scale(loss).backward()
        scaler.step(opt)
        scaler.update()
        trace.append(scaler.get_scale())
    return trace, [p.detach().clone() for p in lin.parameters()]


@pytest.mark.parametrize("inf_at", [(), (2, 6), (0, 1, 2)])
def test_scaler_matches_gradscaler(nb, inf_at):
    mine, p_mine = _manual_loop(nb.DynamicLossScaler(init_scale=8.0, growth_interval=3), inf_at)
    ref, p_ref = _manual_loop(torch.amp.GradScaler("cpu", init_scale=8.0, growth_interval=3), inf_at)
    assert mine == ref, "chuỗi scale khác torch.amp.GradScaler"
    for a, b in zip(p_mine, p_ref):
        torch.testing.assert_close(a, b)


def test_scaler_defaults_and_scale(nb):
    s = nb.DynamicLossScaler()
    assert s.get_scale() == 65536.0 and isinstance(s.get_scale(), float)
    torch.testing.assert_close(s.scale(torch.tensor(0.5)), torch.tensor(32768.0))


def test_scaler_unscale_once_and_skip(nb):
    lin, opt = _toy()
    s = nb.DynamicLossScaler(init_scale=4.0, backoff_factor=0.25)
    s.scale(lin(torch.ones(1, 4)).sum()).backward()
    expected = [p.grad.clone() / 4 for p in lin.parameters()]
    s.unscale_(opt)
    s.unscale_(opt)                                              # lần hai không chia nữa
    for p, e in zip(lin.parameters(), expected):
        torch.testing.assert_close(p.grad, e)
    before = [p.detach().clone() for p in lin.parameters()]
    lin.weight.grad[0, 0] = float("nan")
    s2 = nb.DynamicLossScaler(init_scale=4.0, backoff_factor=0.25)
    s2.step(opt)                                                 # chưa unscale: step tự unscale và thấy NaN
    s2.update()
    for p, b in zip(lin.parameters(), before):
        assert torch.equal(p.detach(), b), "có NaN thì bỏ qua optimizer.step()"
    assert s2.get_scale() == 1.0


# ---------- train_step ----------

def _model(seed=0):
    torch.manual_seed(seed)
    return nn.Sequential(nn.Linear(6, 16), nn.ReLU(), nn.Linear(16, 3))


def _batch(seed):
    g = torch.Generator().manual_seed(seed)
    return torch.randn(10, 6, generator=g), torch.randint(0, 3, (10,), generator=g)


def test_train_step_fp32_matches_manual(nb):
    model, ref = _model(), _model()
    opt = torch.optim.SGD(model.parameters(), lr=0.1, momentum=0.9)
    opt_ref = torch.optim.SGD(ref.parameters(), lr=0.1, momentum=0.9)
    scaler = torch.amp.GradScaler("cpu", enabled=False)
    for seed in (1, 2):                                          # hai bước: gradient phải được xoá giữa hai bước
        x, y = _batch(seed)
        info = nb.train_step(model, x, y, opt, scaler, None)
        opt_ref.zero_grad()
        loss = F.cross_entropy(ref(x), y)
        loss.backward()
        norm = torch.cat([p.grad.flatten() for p in ref.parameters()]).norm().item()
        opt_ref.step()
        assert isinstance(info["loss"], float) and info["loss"] == pytest.approx(loss.item(), rel=1e-6)
        assert info["grad_norm"] == pytest.approx(norm, rel=1e-5) and info["stepped"] is True
    for a, b in zip(model.parameters(), ref.parameters()):
        torch.testing.assert_close(a, b)


def test_train_step_uses_autocast(nb):
    model = _model()
    seen = []
    model[2].register_forward_hook(lambda m, i, o: seen.append(o.dtype))
    opt = torch.optim.SGD(model.parameters(), lr=0.1)
    x, y = _batch(3)
    fp32_loss = F.cross_entropy(_model()(x), y).item()
    info = nb.train_step(model, x, y, opt, torch.amp.GradScaler("cpu", enabled=False), torch.bfloat16)
    assert seen == [torch.bfloat16], "forward phải chạy trong torch.autocast(dtype=amp_dtype)"
    assert info["loss"] == pytest.approx(fp32_loss, rel=2e-2)
    assert all(p.dtype == torch.float32 for p in model.parameters()), "autocast không đổi dtype của tham số"


def test_train_step_clips_after_unscale(nb):
    model = _model()
    with torch.no_grad():
        model[2].weight.mul_(50)                                 # gradient lớn để clip có tác dụng
    ref = _model()
    ref.load_state_dict(model.state_dict())
    x, y = _batch(4)
    F.cross_entropy(ref(x), y).backward()
    true_norm = torch.cat([p.grad.flatten() for p in ref.parameters()]).norm().item()
    assert true_norm > 1.0
    before = torch.cat([p.detach().flatten() for p in model.parameters()])
    opt = torch.optim.SGD(model.parameters(), lr=1.0)
    info = nb.train_step(model, x, y, opt, torch.amp.GradScaler("cpu", init_scale=1024.0), None, max_norm=0.5)
    after = torch.cat([p.detach().flatten() for p in model.parameters()])
    assert info["grad_norm"] == pytest.approx(true_norm, rel=1e-4), "norm đo SAU unscale_, TRƯỚC khi clip"
    assert (after - before).norm().item() == pytest.approx(0.5, rel=1e-3), "clip gradient đã unscale về max_norm"


def test_train_step_skips_non_finite(nb):
    for scaler in (torch.amp.GradScaler("cpu", init_scale=256.0), nb.DynamicLossScaler(init_scale=256.0)):
        model = _model()
        opt = torch.optim.SGD(model.parameters(), lr=0.1)
        x, y = _batch(5)
        x[0, 0] = float("inf")
        before = [p.detach().clone() for p in model.parameters()]
        info = nb.train_step(model, x, y, opt, scaler, None, max_norm=1.0)
        assert info["stepped"] is False and not math.isfinite(info["grad_norm"])
        assert all(torch.equal(p.detach(), b) for p, b in zip(model.parameters(), before))
        assert scaler.get_scale() == 128.0
        info = nb.train_step(model, *_batch(6), opt, scaler, None)
        assert info["stepped"] is True

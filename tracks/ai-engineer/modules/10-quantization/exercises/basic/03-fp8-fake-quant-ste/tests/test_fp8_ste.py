import pytest
import torch

from testkit import Exercise

ex = Exercise(__file__)


@pytest.fixture(scope="module")
def F8():
    return ex.module("fp8_ste.py")


def sweep() -> torch.Tensor:
    torch.manual_seed(0)
    mags = torch.exp2(torch.empty(200_000).uniform_(-20, 17))
    signs = torch.where(torch.rand(200_000) < 0.5, -1.0, 1.0)
    return torch.cat([mags * signs, torch.linspace(-3, 3, 60_001)])


def test_no_builtin_fp8_dtype():
    src = ex.read("fp8_ste.py")
    assert "float8" not in src, "tự dựng lưới fp8, không ép kiểu sang torch.float8_*"


def test_e4m3_matches_hardware_definition(F8):
    x = sweep()
    ref = x.clamp(-448, 448).to(torch.float8_e4m3fn).float()
    out = F8.fp8_round(x, "e4m3")
    assert out.dtype == torch.float32 and out.shape == x.shape
    assert torch.equal(out, ref)


def test_e5m2_matches_hardware_definition(F8):
    x = sweep()
    x = x[x.abs() < 57344]
    assert torch.equal(F8.fp8_round(x, "e5m2"), x.to(torch.float8_e5m2).float())


def test_ties_subnormals_and_saturation(F8):
    x = torch.tensor([1.0625, 1.1875, 2.0**-10, 3 * 2.0**-10, 2.0**-9, 500.0, -1e9, 0.0, -0.0])
    out = F8.fp8_round(x, "e4m3").tolist()
    assert out[:2] == [1.0, 1.25], "hoà thì về mantissa chẵn"
    assert out[2:5] == [0.0, 2.0**-8, 2.0**-9], "subnormal: bước nhỏ nhất 2^-9"
    assert out[5:7] == [448.0, -448.0], "bão hoà, không ra inf/nan"
    assert out[7] == 0.0
    assert F8.fp8_round(torch.tensor([1e6, -70000.0]), "e5m2").tolist() == [57344.0, -57344.0]


def test_number_of_representable_values(F8):
    x = torch.exp2(torch.linspace(-20, 17, 2_000_001))
    assert torch.unique(F8.fp8_round(x, "e4m3")).numel() == 127, "E4M3: 126 số dương khác 0 cộng số 0"
    assert torch.unique(F8.fp8_round(x, "e5m2")).numel() == 124, "E5M2: 123 số dương hữu hạn khác 0 cộng số 0"


def test_relative_error_in_normal_range(F8):
    x = torch.exp2(torch.empty(50_000).uniform_(-5, 8))
    rel = ((F8.fp8_round(x, "e4m3") - x).abs() / x).max()
    assert rel <= 2.0**-4 + 1e-7
    rel5 = ((F8.fp8_round(x, "e5m2") - x).abs() / x).max()
    assert 2.0**-4 < rel5 <= 2.0**-3 + 1e-7, "E5M2 ít hơn một bit mantissa: sai số tương đối gấp đôi"


def test_fake_quant_forward(F8):
    x = torch.tensor([-1.0, -0.7, 0.33, 0.25, 0.75, 0.05])
    y = F8.fake_quant(x, torch.tensor(0.1), 4)
    torch.testing.assert_close(y, torch.tensor([-0.7, -0.7, 0.3, 0.2, 0.7, 0.0]))


def test_ste_gradient_is_clipped_identity(F8):
    x = torch.tensor([-1.0, -0.7, 0.33, 0.25, 0.75, 0.05], requires_grad=True)
    scale = torch.tensor(0.1, requires_grad=True)
    y = F8.fake_quant(x, scale, 4)
    (y * torch.arange(1.0, 7.0)).sum().backward()
    assert x.grad is not None, "phải có gradient theo x (round có đạo hàm 0 ở mọi nơi)"
    torch.testing.assert_close(x.grad, torch.tensor([0.0, 2.0, 3.0, 4.0, 0.0, 6.0]))
    assert scale.grad is None or torch.all(scale.grad == 0)


def test_per_channel_scale(F8):
    w = torch.tensor([[0.5, -1.4, 0.2], [0.0, 0.0, 0.0], [3.5, 1.0, -0.7]], requires_grad=True)
    s = F8.absmax_scale_per_channel(w, 8)
    assert s.shape == (3, 1) and not s.requires_grad
    torch.testing.assert_close(s.flatten(), torch.tensor([1.4 / 127, 1.0, 3.5 / 127]))


def test_ste_lets_quantized_weights_learn(F8):
    torch.manual_seed(0)
    target = torch.randn(4, 16)
    X = torch.randn(256, 16)
    Y = X @ target.T
    w = torch.zeros(4, 16).normal_(0, 0.1).requires_grad_(True)
    opt = torch.optim.SGD([w], lr=0.1)
    losses = []
    for _ in range(100):
        wq = F8.fake_quant(w, F8.absmax_scale_per_channel(w, 4), 4)
        loss = ((X @ wq.T - Y) ** 2).mean()
        opt.zero_grad()
        loss.backward()
        opt.step()
        losses.append(loss.item())
    assert losses[-1] < 0.1 * losses[0], "STE truyền gradient qua phép làm tròn nên trọng số lượng tử vẫn học được"

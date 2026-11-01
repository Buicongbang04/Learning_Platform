import math

import pytest
import torch

from testkit import Exercise

ex = Exercise(__file__)


@pytest.fixture(scope="module")
def Q():
    return ex.module("quant.py")


def test_absmax_rounding_and_dtype(Q):
    x = torch.tensor([31.75, -3.125, 0.375, 0.625, 0.0])
    q, scale = Q.absmax_quantize(x, bits=8)
    assert q.dtype == torch.int8
    assert scale.dim() == 0 and float(scale) == 0.25, "scale = max|x| / 127"
    assert q.tolist() == [127, -12, 2, 2, 0], "làm tròn bằng torch.round: -12.5 -> -12, 1.5 -> 2, 2.5 -> 2"
    torch.testing.assert_close(Q.absmax_dequantize(q, scale), torch.tensor([31.75, -3.0, 0.5, 0.5, 0.0]))


def test_absmax_bits_set_code_range(Q):
    torch.manual_seed(0)
    x = torch.randn(1000)
    q, scale = Q.absmax_quantize(x, bits=4)
    assert int(q.max()) == 7 or int(q.min()) == -7
    assert int(q.abs().max()) == 7, "4 bit đối xứng: mã trong -7..7"
    assert math.isclose(float(scale), float(x.abs().max()) / 7, rel_tol=1e-6)


def test_absmax_per_channel_axis(Q):
    x = torch.tensor([[1.0, -2.0, 0.5, 0.0], [10.0, 0.0, -40.0, 5.0], [0.1, 0.2, -0.3, 0.05]])
    q0, s0 = Q.absmax_quantize(x, axis=0)
    assert s0.shape == (3, 1), "axis=0: một scale cho mỗi hàng, giữ số chiều để broadcast"
    torch.testing.assert_close(s0.flatten(), torch.tensor([2.0, 40.0, 0.3]) / 127)
    assert q0.abs().amax(dim=1).tolist() == [127, 127, 127], "mỗi hàng dùng hết dải mã"
    q1, s1 = Q.absmax_quantize(x, axis=1)
    assert s1.shape == (1, 4)
    torch.testing.assert_close(s1.flatten(), torch.tensor([10.0, 2.0, 40.0, 5.0]) / 127)
    _, sneg = Q.absmax_quantize(x, axis=-1)
    torch.testing.assert_close(sneg, s1)
    x3 = torch.randn(2, 3, 5)
    _, s3 = Q.absmax_quantize(x3, axis=1)
    assert s3.shape == (1, 3, 1)
    torch.testing.assert_close(s3.flatten(), x3.abs().amax(dim=(0, 2)) / 127)


def test_zero_channel_is_safe(Q):
    x = torch.tensor([[0.0, 0.0, 0.0], [1.0, -1.0, 0.5]])
    q, s = Q.absmax_quantize(x, axis=0)
    assert float(s[0, 0]) == 1.0 and q[0].tolist() == [0, 0, 0]
    assert torch.isfinite(Q.absmax_dequantize(q, s)).all()
    qz, sz, zp = Q.zeropoint_quantize(x, axis=0)
    assert float(sz[0, 0]) == 1.0
    assert torch.isfinite(Q.zeropoint_dequantize(qz, sz, zp)).all()


def test_zeropoint_range_contains_zero(Q):
    x = torch.tensor([2.0, 4.0, 10.0])
    q, scale, zp = Q.zeropoint_quantize(x)
    assert q.dtype == torch.uint8 and zp.dtype == torch.int32
    assert math.isclose(float(scale), 10 / 255, rel_tol=1e-6), "khoảng lượng tử phải chứa 0: lo = min(x_min, 0)"
    assert int(zp) == 0 and int(q[-1]) == 255
    xn = torch.tensor([-1.0, -0.25, 0.0, 3.0])
    qn, sn, zn = Q.zeropoint_quantize(xn)
    assert math.isclose(float(sn), 4 / 255, rel_tol=1e-6)
    assert int(zn) == round(1 / (4 / 255))
    deq = Q.zeropoint_dequantize(qn, sn, zn)
    assert float(deq[2]) == 0.0, "số 0 phải giải lượng tử ra đúng 0 (zero_point là số nguyên)"


def test_zeropoint_clamps_instead_of_wrapping(Q):
    x = torch.tensor([-1.5, 0.0, 253.5])
    q, scale, zp = Q.zeropoint_quantize(x)
    assert float(scale) == 1.0 and int(zp) == 2
    assert q.tolist() == [0, 2, 255], "round(253.5) + 2 = 256 phải kẹp về 255, không quay vòng uint8 về 0"


@pytest.mark.filterwarnings("ignore:torch.quantize_per_tensor")
def test_zeropoint_matches_torch_quantize(Q):
    torch.manual_seed(1)
    x = torch.randn(64, 32) * 3 + 1
    q, scale, zp = Q.zeropoint_quantize(x)
    ref = torch.quantize_per_tensor(x, float(scale), int(zp), torch.quint8).int_repr()
    assert torch.equal(q, ref)
    qc, sc, zc = Q.zeropoint_quantize(x, axis=0)
    assert sc.shape == (64, 1) and zc.shape == (64, 1)
    refc = torch.quantize_per_channel(x, sc.flatten().double(), zc.flatten().long(), 0, torch.quint8).int_repr()
    assert torch.equal(qc, refc)


def test_asymmetric_beats_symmetric_on_skewed_data(Q):
    torch.manual_seed(2)
    x = torch.rand(10_000) * 4 + 0.5
    sym = Q.absmax_dequantize(*Q.absmax_quantize(x, bits=4))
    asym = Q.zeropoint_dequantize(*Q.zeropoint_quantize(x, bits=4))
    assert Q.sqnr_db(x, asym) > Q.sqnr_db(x, sym) + 4, "dữ liệu toàn dương: zero-point dùng cả 16 mã, absmax bỏ phí nửa âm"


def test_per_channel_beats_per_tensor(Q):
    torch.manual_seed(3)
    w = torch.randn(16, 64) * torch.logspace(-2, 0, 16)[:, None]
    per_tensor = Q.absmax_dequantize(*Q.absmax_quantize(w))
    per_channel = Q.absmax_dequantize(*Q.absmax_quantize(w, axis=0))
    assert Q.sqnr_db(w, per_channel) > Q.sqnr_db(w, per_tensor) + 3


def test_sqnr_value_and_six_db_per_bit(Q):
    assert math.isclose(Q.sqnr_db(torch.tensor([1.0, 1.0]), torch.tensor([1.0, 0.9])), 10 * math.log10(2 / 0.01), rel_tol=1e-4)
    assert Q.sqnr_db(torch.ones(3), torch.ones(3)) == math.inf
    torch.manual_seed(4)
    x = torch.rand(200_000) * 2 - 1
    s8 = Q.sqnr_db(x, Q.absmax_dequantize(*Q.absmax_quantize(x, bits=8)))
    s4 = Q.sqnr_db(x, Q.absmax_dequantize(*Q.absmax_quantize(x, bits=4)))
    assert 22 < s8 - s4 < 26, "mỗi bit thêm khoảng 6 dB"

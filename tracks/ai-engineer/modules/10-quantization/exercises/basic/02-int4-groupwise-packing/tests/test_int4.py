import pytest
import torch

from testkit import Exercise

ex = Exercise(__file__)


@pytest.fixture(scope="module")
def I():
    return ex.module("int4.py")


def test_symmetric_codes_scales_zeros(I):
    w = torch.tensor([[0.7, -0.35, 0.1, 0.0, 1.4, 0.2, -0.2, 0.0]])
    codes, scales, zeros = I.quantize_groupwise(w, bits=4, group_size=4, symmetric=True)
    assert codes.dtype == torch.uint8 and zeros.dtype == torch.int32
    assert scales.shape == (1, 2) and zeros.shape == (1, 2)
    torch.testing.assert_close(scales, torch.tensor([[0.1, 0.2]]))
    assert zeros.tolist() == [[8, 8]], "đối xứng: zero là hằng 2^(bits-1)"
    assert codes.tolist() == [[15, 4, 9, 8, 15, 9, 7, 8]], "-0.35/0.1 = -3.5 làm tròn về -4 (số chẵn); cộng 8"


def test_groups_are_contiguous_columns_of_one_row(I):
    w = torch.ones(2, 8) * 0.5
    w[0, 5] = 50.0
    codes, scales, _ = I.quantize_groupwise(w, bits=4, group_size=4)
    assert scales.shape == (2, 2)
    torch.testing.assert_close(scales[0, 0], torch.tensor(0.5 / 7)), "ngoại lai ở cột 5 không được ảnh hưởng nhóm cột 0-3"
    torch.testing.assert_close(scales[0, 1], torch.tensor(50.0 / 7))
    torch.testing.assert_close(scales[1], torch.full((2,), 0.5 / 7))
    deq = I.dequantize_groupwise(codes, *I.quantize_groupwise(w, bits=4, group_size=4)[1:], group_size=4)
    torch.testing.assert_close(deq[0, :4], w[0, :4])
    torch.testing.assert_close(deq[1], w[1])


def test_group_size_must_divide(I):
    with pytest.raises(ValueError):
        I.quantize_groupwise(torch.randn(4, 10), group_size=4)


def test_asymmetric_matches_definition(I):
    w = torch.tensor([[0.0, 1.0, 2.0, 3.0, -1.5, 0.0, 0.0, 6.0]])
    codes, scales, zeros = I.quantize_groupwise(w, bits=4, group_size=4, symmetric=False)
    torch.testing.assert_close(scales, torch.tensor([[3.0 / 15, 7.5 / 15]]))
    assert zeros.tolist() == [[0, 3]]
    assert codes[0, :4].tolist() == [0, 5, 10, 15]
    assert int(codes[0, 4]) == 0 and int(codes[0, 7]) == 15
    deq = I.dequantize_groupwise(codes, scales, zeros, 4)
    assert float(deq[0, 5]) == 0.0, "số 0 giải lượng tử ra đúng 0"
    _, s_pos, z_pos = I.quantize_groupwise(torch.tensor([[2.0, 4.0, 6.0, 8.0]]), bits=4, group_size=4, symmetric=False)
    torch.testing.assert_close(s_pos, torch.tensor([[8.0 / 15]])), "khoảng của nhóm phải chứa 0"
    assert z_pos.tolist() == [[0]]


def test_roundtrip_error_bounded_by_half_step(I):
    torch.manual_seed(0)
    w = torch.randn(16, 256)
    for symmetric in (True, False):
        codes, scales, zeros = I.quantize_groupwise(w, bits=4, group_size=64, symmetric=symmetric)
        deq = I.dequantize_groupwise(codes, scales, zeros, 64)
        assert deq.shape == w.shape and deq.dtype == w.dtype
        step = scales.repeat_interleave(64, dim=1)
        assert torch.all((deq - w).abs() <= step / 2 + 1e-6)
        assert int(codes.max()) <= 15


def test_smaller_groups_lower_error(I):
    torch.manual_seed(1)
    w = torch.randn(64, 512) * torch.exp(torch.randn(1, 512))
    errs = []
    for g in (512, 128, 32):
        deq = I.dequantize_groupwise(*I.quantize_groupwise(w, group_size=g), group_size=g)
        errs.append(float(((deq - w) ** 2).mean()))
    assert errs[0] > errs[1] > errs[2]


def test_pack_bit_order(I):
    codes = torch.tensor([[1, 2, 15, 0, 10, 11]], dtype=torch.uint8)
    packed = I.pack_int4(codes)
    assert packed.dtype == torch.uint8 and packed.shape == (1, 3)
    assert packed.tolist() == [[0x21, 0x0F, 0xBA]], "phần tử 2i ở 4 bit thấp, 2i+1 ở 4 bit cao"


def test_unpack_inverts_pack(I):
    torch.manual_seed(2)
    codes = torch.randint(0, 16, (5, 3, 32), dtype=torch.uint8)
    packed = I.pack_int4(codes)
    assert packed.shape == (5, 3, 16)
    out = I.unpack_int4(packed)
    assert out.dtype == torch.uint8 and torch.equal(out, codes)
    assert I.unpack_int4(torch.tensor([0xA5], dtype=torch.uint8)).tolist() == [5, 10]


def test_pack_rejects_bad_input(I):
    with pytest.raises(ValueError):
        I.pack_int4(torch.zeros(3, dtype=torch.uint8))
    with pytest.raises(ValueError):
        I.pack_int4(torch.tensor([16, 0], dtype=torch.uint8))


def test_bits_per_weight(I):
    assert I.bits_per_weight(4, 128) == pytest.approx(4.125)
    assert I.bits_per_weight(4, 32, scale_bits=16, zero_bits=4) == pytest.approx(4.625)
    assert I.bits_per_weight(8, 4096) == pytest.approx(8 + 16 / 4096)

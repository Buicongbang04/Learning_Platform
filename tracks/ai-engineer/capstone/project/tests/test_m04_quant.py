"""M04: bit mỗi tham số và Pareto front."""

import pytest


def test_bits_per_weight(la):
    quant = la("quant")
    assert quant.bits_per_weight(1_000_000_000, 2_000_000_000) == pytest.approx(4.0)
    assert quant.bits_per_weight(3, 4) == pytest.approx(6.0)
    with pytest.raises(ValueError):
        quant.bits_per_weight(10, 0)


def test_pareto_front(la):
    quant = la("quant")
    rows = [
        {"name": "fp16", "bpc": 1.00, "vram": 6.0, "tok_s": 40},
        {"name": "q8", "bpc": 1.01, "vram": 3.5, "tok_s": 60},
        {"name": "q4", "bpc": 1.08, "vram": 2.2, "tok_s": 70},
        {"name": "q4-chậm", "bpc": 1.09, "vram": 2.3, "tok_s": 50},
        {"name": "q3", "bpc": 1.30, "vram": 1.9, "tok_s": 65},
        {"name": "q8-bản-sao", "bpc": 1.01, "vram": 3.5, "tok_s": 60},
    ]
    objectives = {"bpc": "min", "vram": "min", "tok_s": "max"}
    assert quant.pareto_front(rows, objectives) == [0, 1, 2, 4, 5]
    assert quant.pareto_front(rows, {"bpc": "min"}) == [0]
    with pytest.raises(ValueError):
        quant.pareto_front(rows, {"bpc": "lower"})

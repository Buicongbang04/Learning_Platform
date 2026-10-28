import math

import pytest

from testkit import Exercise

ex = Exercise(__file__)


def m():
    return ex.module("cost.py")


def test_storage_cost():
    assert m().storage_cost(1000) == pytest.approx(23.0)
    assert m().storage_cost(1000, 0.0125, months=12) == pytest.approx(150.0)
    assert m().storage_cost(0) == 0


@pytest.mark.parametrize(
    "gb, expected",
    [
        (0, 0.0),
        (50, 0.0),
        (100, 0.0),
        (101, 0.09),
        (1124, 92.16),
        (10 * 1024, (10 * 1024 - 100) * 0.09),
        (10 * 1024 + 1000, (10 * 1024 - 100) * 0.09 + 1000 * 0.085),
        (200 * 1024, (10240 - 100) * 0.09 + 40 * 1024 * 0.085 + 100 * 1024 * 0.07 + 50 * 1024 * 0.05),
    ],
)
def test_egress_default_tiers(gb, expected):
    assert m().egress_cost(gb) == pytest.approx(expected)


def test_egress_custom_tiers():
    tiers = [(10, 1.0), (20, 0.5), (math.inf, 0.1)]
    assert m().egress_cost(5, tiers) == pytest.approx(5.0)
    assert m().egress_cost(15, tiers) == pytest.approx(12.5)
    assert m().egress_cost(30, tiers) == pytest.approx(16.0)


def test_scan_cost():
    assert m().scan_cost(0.5) == 0
    assert m().scan_cost(1.0) == 0
    assert m().scan_cost(3) == pytest.approx(12.5)
    assert m().scan_cost(3, price_per_tb=5, free_tb=0) == pytest.approx(15)


def test_monthly_bill():
    bill = m().monthly_bill(storage_gb=2048, egress_gb=1124, scanned_tb=11)
    assert set(bill) == {"storage", "egress", "scan", "total"}
    assert bill["storage"] == 47.10
    assert bill["egress"] == 92.16
    assert bill["scan"] == 62.5
    assert bill["total"] == pytest.approx(201.76)
    assert bill["total"] == round(bill["storage"] + bill["egress"] + bill["scan"], 2)


def test_monthly_bill_rounding():
    bill = m().monthly_bill(storage_gb=1, egress_gb=0, scanned_tb=0, storage_price=0.0125)
    assert bill["storage"] == 0.01
    assert bill["total"] == 0.01


@pytest.mark.parametrize(
    "call",
    [
        lambda mod: mod.storage_cost(-1),
        lambda mod: mod.storage_cost(1, months=-1),
        lambda mod: mod.egress_cost(-5),
        lambda mod: mod.scan_cost(-0.1),
    ],
)
def test_negative_raises(call):
    with pytest.raises(ValueError):
        call(m())

import pytest

from roman import to_roman


def test_example():
    assert to_roman(1994) == "MCMXCIV"


def test_small():
    assert [to_roman(i) for i in range(1, 11)] == ["I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X"]


def test_subtractive():
    assert to_roman(40) == "XL" and to_roman(90) == "XC" and to_roman(400) == "CD" and to_roman(900) == "CM"


def test_limits():
    assert to_roman(3999) == "MMMCMXCIX"
    for bad in (0, -3, 4000):
        with pytest.raises(ValueError):
            to_roman(bad)

from money import format_vnd


def test_basic():
    assert format_vnd(1234567) == "1.234.567 ₫"


def test_small():
    assert format_vnd(0) == "0 ₫"
    assert format_vnd(999) == "999 ₫"
    assert format_vnd(1000) == "1.000 ₫"


def test_negative():
    assert format_vnd(-5000) == "-5.000 ₫"
    assert format_vnd(-999) == "-999 ₫"


def test_large():
    assert format_vnd(1000000000) == "1.000.000.000 ₫"

from money import format_vnd


def test_basic():
    assert format_vnd(1234567) == "1.234.567 ₫"

from phone import normalize_phone


def test_plus84():
    assert normalize_phone("+84 912 345 678") == "0912345678"


def test_formats():
    assert normalize_phone("0912.345.678") == "0912345678"
    assert normalize_phone("84-388-123-456") == "0388123456"
    assert normalize_phone("0 7 0 1 2 3 4 5 6 7") == "0701234567"


def test_invalid():
    assert normalize_phone("091234567") is None
    assert normalize_phone("0212345678") is None
    assert normalize_phone("09123456789") is None
    assert normalize_phone("abc") is None

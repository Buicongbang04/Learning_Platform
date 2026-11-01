from phone import normalize_phone


def test_plus84():
    assert normalize_phone("+84 912 345 678") == "0912345678"

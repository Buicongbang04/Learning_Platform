from cccd import is_valid_cccd


def test_valid():
    assert is_valid_cccd("001203012345")
    assert is_valid_cccd(" 079095001234 ")


def test_length_and_digits():
    assert not is_valid_cccd("00120301234")
    assert not is_valid_cccd("0012030123456")
    assert not is_valid_cccd("00120301234a")


def test_province():
    assert not is_valid_cccd("003203012345")
    assert not is_valid_cccd("099203012345")


def test_century_digit():
    assert not is_valid_cccd("001403012345")
    assert is_valid_cccd("001303012345")

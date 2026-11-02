from cccd import is_valid_cccd


def test_valid():
    assert is_valid_cccd("001203012345")

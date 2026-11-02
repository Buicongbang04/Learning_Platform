from rle import encode


def test_encode():
    assert encode("aaabcc") == "a3b1c2"

from rle import decode, encode


def test_encode():
    assert encode("aaabcc") == "a3b1c2"
    assert encode("") == ""


def test_decode():
    assert decode("a3b1c2") == "aaabcc"


def test_long_runs():
    assert encode("z" * 12) == "z12"
    assert decode("z12x1") == "z" * 12 + "x"


def test_roundtrip():
    for s in ["", "a", "abc", "aabbbaaaa", "q" * 30 + "w"]:
        assert decode(encode(s)) == s

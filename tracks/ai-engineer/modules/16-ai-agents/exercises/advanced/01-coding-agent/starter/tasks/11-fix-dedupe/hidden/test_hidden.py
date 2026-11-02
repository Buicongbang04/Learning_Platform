from dedupe import dedupe


def test_order_kept():
    assert dedupe([3, 1, 3, 2, 1]) == [3, 1, 2]
    assert dedupe(["b", "a", "b"]) == ["b", "a"]


def test_key_keeps_first():
    assert dedupe(["An", "an", "Bình", "AN"], key=str.lower) == ["An", "Bình"]


def test_empty():
    assert dedupe([]) == []

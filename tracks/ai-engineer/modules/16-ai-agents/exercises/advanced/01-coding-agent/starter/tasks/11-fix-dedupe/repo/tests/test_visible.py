from dedupe import dedupe


def test_order_kept():
    assert dedupe([3, 1, 3, 2, 1]) == [3, 1, 2]

from intervals import merge


def test_example():
    assert merge([(1, 3), (2, 6), (8, 10)]) == [(1, 6), (8, 10)]


def test_unsorted_and_touching():
    assert merge([(5, 7), (1, 2), (2, 4)]) == [(1, 4), (5, 7)]


def test_contained():
    assert merge([(1, 10), (2, 3), (4, 5)]) == [(1, 10)]


def test_empty_and_single():
    assert merge([]) == []
    assert merge([(3, 3)]) == [(3, 3)]

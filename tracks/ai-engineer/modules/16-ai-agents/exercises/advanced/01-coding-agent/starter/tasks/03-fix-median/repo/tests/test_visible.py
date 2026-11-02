from stats import median


def test_even_length():
    assert median([4, 1, 3, 2]) == 2.5

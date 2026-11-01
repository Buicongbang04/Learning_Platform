import pytest

from stats import median


def test_odd_length():
    assert median([3, 1, 2]) == 2


def test_even_length():
    assert median([4, 1, 3, 2]) == 2.5
    assert median([1, 2]) == 1.5


def test_single_and_unsorted():
    assert median([7]) == 7
    assert median([10, -1, 5, 3, 8, 0]) == 4.0


def test_empty():
    with pytest.raises(ValueError):
        median([])


def test_input_not_mutated():
    data = [3, 1, 2]
    median(data)
    assert data == [3, 1, 2]

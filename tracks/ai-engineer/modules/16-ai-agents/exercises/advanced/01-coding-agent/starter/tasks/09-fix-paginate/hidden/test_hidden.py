import pytest

from pages import paginate


def test_first_page():
    assert paginate(list(range(10)), 1, 3) == [0, 1, 2]


def test_last_partial_page():
    assert paginate(list(range(10)), 4, 3) == [9]


def test_out_of_range():
    assert paginate(list(range(10)), 5, 3) == []


def test_invalid():
    for page, size in [(0, 3), (-1, 3), (1, 0)]:
        with pytest.raises(ValueError):
            paginate([1, 2], page, size)

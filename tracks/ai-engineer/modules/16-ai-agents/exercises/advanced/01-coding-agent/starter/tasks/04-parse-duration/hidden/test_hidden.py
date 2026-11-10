import pytest

from duration import parse_duration


def test_hours_minutes():
    assert parse_duration("1h30m") == 5400


def test_single_units():
    assert parse_duration("45s") == 45
    assert parse_duration("2h") == 7200
    assert parse_duration("10m") == 600


def test_skip_middle():
    assert parse_duration("2h5s") == 7205


@pytest.mark.parametrize("bad", ["", "abc", "5", "1m2h", "1h1h", "h", "-1h"])
def test_invalid(bad):
    with pytest.raises(ValueError):
        parse_duration(bad)

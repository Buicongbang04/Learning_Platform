from words import word_count


def test_case_insensitive():
    assert word_count("Xe xe XE") == {"xe": 3}


def test_whitespace():
    assert word_count("một  hai\nhai\tba") == {"một": 1, "hai": 2, "ba": 1}


def test_punctuation():
    assert word_count("Chào, chào! Bạn khỏe?") == {"chào": 2, "bạn": 1, "khỏe": 1}


def test_empty():
    assert word_count("   ") == {}

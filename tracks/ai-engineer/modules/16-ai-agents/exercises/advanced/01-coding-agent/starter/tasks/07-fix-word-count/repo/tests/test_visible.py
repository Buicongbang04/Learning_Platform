from words import word_count


def test_case_insensitive():
    assert word_count("Xe xe XE") == {"xe": 3}

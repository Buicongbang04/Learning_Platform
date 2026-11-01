from slug import slugify


def test_basic():
    assert slugify("Tiếng Việt có dấu!") == "tieng-viet-co-dau"

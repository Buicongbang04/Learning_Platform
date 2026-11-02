from slug import slugify


def test_basic():
    assert slugify("Tiếng Việt có dấu!") == "tieng-viet-co-dau"


def test_d_stroke():
    assert slugify("Đường Điện Biên Phủ") == "duong-dien-bien-phu"


def test_collapse_and_trim():
    assert slugify("  Xin   chào -- thế giới  ") == "xin-chao-the-gioi"
    assert slugify("---") == ""


def test_numbers_kept():
    assert slugify("Nghị định 100/2019/NĐ-CP") == "nghi-dinh-100-2019-nd-cp"

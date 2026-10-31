import pytest

from testkit import Exercise

ex = Exercise(__file__)
FILLERS = ["a b c", "d e", "f g h i", "j"]
NEEDLE = "KIM"


def words(text: str) -> int:
    return len(text.split())


@pytest.fixture(scope="module")
def nb():
    return ex.notebook("needle.ipynb")


def test_haystack_takes_fillers_until_target(nb):
    # 3 + 2 + 4 = 9 >= 9: dừng sau 3 đoạn
    out = nb.build_haystack(FILLERS, NEEDLE, 0.0, 9, words)
    assert out == "KIM\n\na b c\n\nd e\n\nf g h i"
    assert nb.build_haystack(FILLERS, NEEDLE, 1.0, 9, words) == "a b c\n\nd e\n\nf g h i\n\nKIM"


def test_haystack_depth_positions(nb):
    # 4 đoạn (3 + 2 + 4 + 1 = 10 >= 10); vị trí chèn = round(depth * 4)
    assert nb.build_haystack(FILLERS, NEEDLE, 0.25, 10, words).split("\n\n") == ["a b c", "KIM", "d e", "f g h i", "j"]
    assert nb.build_haystack(FILLERS, NEEDLE, 0.5, 10, words).split("\n\n") == ["a b c", "d e", "KIM", "f g h i", "j"]
    assert nb.build_haystack(FILLERS, NEEDLE, 0.75, 10, words).split("\n\n") == ["a b c", "d e", "f g h i", "KIM", "j"]


def test_haystack_cycles_fillers(nb):
    paras = nb.build_haystack(["x y"], NEEDLE, 1.0, 7, words).split("\n\n")
    assert paras == ["x y"] * 4 + ["KIM"]
    out = nb.build_haystack(FILLERS, NEEDLE, 0.0, 15, words).split("\n\n")
    assert out[1:] == ["a b c", "d e", "f g h i", "j", "a b c", "d e"], "hết đoạn thì quay lại đoạn đầu"


def test_haystack_counts_paragraphs_not_needle(nb):
    calls = []

    def counting(text):
        calls.append(text)
        return words(text)

    nb.build_haystack(FILLERS, NEEDLE, 0.5, 5, counting)
    assert NEEDLE not in calls, "chỉ đếm token của đoạn filler"
    assert all("\n\n" not in c for c in calls), "đếm từng đoạn, không đếm lại cả văn bản"


def test_haystack_errors(nb):
    with pytest.raises(ValueError):
        nb.build_haystack(FILLERS, NEEDLE, 1.5, 10, words)
    with pytest.raises(ValueError):
        nb.build_haystack(FILLERS, NEEDLE, -0.1, 10, words)
    with pytest.raises(ValueError):
        nb.build_haystack([], NEEDLE, 0.5, 10, words)


@pytest.mark.parametrize("reply, found", [
    ("7429", True),
    ("Mã số mở kho lưu trữ là 7429.", True),
    ("Mã số: 7.429", True),
    ("7 429", True),
    ("Mã số là 17429", False),
    ("74290", False),
    ("742", False),
    ("Không tìm thấy mã số trong văn bản.", False),
])
def test_needle_found(nb, reply, found):
    assert nb.needle_found(reply, "7429") is found

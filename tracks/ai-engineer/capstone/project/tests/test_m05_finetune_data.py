"""M05: dữ liệu fine-tune không rò rỉ sang tập đánh giá."""

import unicodedata

import pytest


def test_check_no_leak(la, mini):
    data, ft = la("data"), la("finetune_data")
    train, test = data.load_questions(mini, "train"), data.load_questions(mini, "test")
    ft.check_no_leak(train, test)
    with pytest.raises(ValueError, match="1"):
        ft.check_no_leak(train + [test[0]], test)
    twin = data.Question("khác-id", "  " + unicodedata.normalize("NFD", test[1].text.upper()) + " ", frozenset({"x"}))
    with pytest.raises(ValueError):
        ft.check_no_leak(train + [twin], test)


def test_hard_negatives(la):
    ft = la("finetune_data")
    ranking = ["A+1", "B+2", "A+1", "C+3", "B+5", "D+1", "E+9"]
    assert ft.hard_negatives(ranking, {"B+2"}, 3) == ["A+1", "C+3", "B+5"]
    assert ft.hard_negatives(ranking, {"B+2"}, 3, skip_same_law=True) == ["A+1", "C+3", "D+1"]
    assert ft.hard_negatives(ranking, {"B+2"}, 0) == []
    assert ft.hard_negatives(["B+2"], {"B+2"}, 2) == []


def test_training_pairs(la, mini):
    data, ft = la("data"), la("finetune_data")
    articles = {a.uid: a for a in data.load_corpus(mini)}
    qs = data.load_questions(mini, "test")
    pairs = ft.training_pairs(qs, articles)
    assert len(pairs) == 4
    assert pairs[0][0] == qs[0].text and pairs[0][1].startswith("Điều 2. Chiều cao tối đa của nhà chòi\nNhà chòi")
    assert [p[1].split("\n")[0] for p in pairs[2:]] == ["Điều 3. Hồ sơ xin giấy phép", "Điều 3. Thẩm quyền xử phạt"]
    ghost = data.Question("g", "?", frozenset({"không/có+1"}))
    assert ft.training_pairs([ghost], articles) == []

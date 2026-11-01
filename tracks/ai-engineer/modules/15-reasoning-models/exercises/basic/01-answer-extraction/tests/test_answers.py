import pytest

from testkit import Exercise

ex = Exercise(__file__)


@pytest.fixture(scope="module")
def ans():
    return ex.module("answers.py")


@pytest.mark.parametrize("text, expected", [
    ("18", "18"), (" 007 ", "7"), ("+5", "5"), ("-3", "-3"), ("−3", "-3"), ("12.", "12"),
    ("1,234", "1234"), ("1,000,000", "1000000"), ("$1,234.50", "2469/2"), ("3.50", "7/2"), ("2.0", "2"),
    ("3/4", "3/4"), ("6/4", "3/2"), ("50%", "50"), ("\\$18", "18"),
])
def test_normalize_accepts_one_number(ans, text, expected):
    assert ans.normalize_number(text) == expected


@pytest.mark.parametrize("text", ["", "two", "12 eggs", "1,2", "1,0000", "3 4", "10/0", "1.2.3", "-", "$"])
def test_normalize_rejects_non_numbers(ans, text):
    assert ans.normalize_number(text) is None


def test_equal_values_have_equal_form(ans):
    forms = {ans.normalize_number(t) for t in ["2.5", "2.50", "5/2", "$2.50", "10/4"]}
    assert len(forms) == 1, "cùng một giá trị phải có đúng một dạng chuẩn để so bằng =="
    assert ans.normalize_number("0.1") != ans.normalize_number("0.10000001")


def test_gold_answer(ans):
    assert ans.gold_answer("Janet sells 16 - 3 - 4 = <<16-3-4=9>>9 duck eggs.\n#### 18") == "18"
    assert ans.gold_answer("She pays 1,000 + 600 = <<1000+600=1600>>1600\n#### 1,600") == "1600"
    assert ans.gold_answer("The change is 5 - 15 = <<5-15=-10>>-10\n#### -10") == "-10"


@pytest.mark.parametrize("completion, expected", [
    ("<think>16 - 3 - 4 = 9, and 9 * 2 = 18</think>\n<answer>18</answer>", "18"),
    ("First 12 eggs... <answer>7</answer> then I double check: 9", "7"),
    ("<answer>5</answer> wait, no. <answer>6</answer>", "6"),
    ("<think>half of 36</think><answer>36 / 2 = 18</answer>", "18"),
    ("So the total is 40.\nTherefore \\boxed{1,000} dollars, i.e. 100,000 cents", "1000"),
    ("2 + 3 = 5\n#### 5 dollars, then 7 more", "5"),
    ("x = 5. The answer is: 7. Check: 7 + 2 = 9.", "7"),
    ("Answer: $1,250.00 in total over 3 months", "1250"),
    ("She makes $18 every day.", "18"),
    ("The temperature fell from 3 degrees to -4 degrees.", "-4"),
    ("He reads pages 3-4 today.", "4"),
    ("Each slice is 3/4 of a pizza.", "3/4"),
    ("It costs 2.5.", "5/2"),
    ("I am not sure.", None),
])
def test_extract_answer_priority_and_edge_cases(ans, completion, expected):
    assert ans.extract_answer(completion) == expected


def test_extract_falls_through_empty_tag(ans):
    assert ans.extract_answer("Total 42 apples. <answer>forty-two</answer>") == "42"


def test_is_correct_compares_values(ans):
    assert ans.is_correct("so the cost is $3.50", "7/2")
    assert ans.is_correct("#### 1,600", "1600")
    assert not ans.is_correct("The answer is 16.", "18")
    assert not ans.is_correct("no idea", "18")


@pytest.mark.parametrize("completion, expected", [
    ("Janet sells 16 - 3 - 4 = 9 eggs, 9 * 2 = 18.\nThe answer is \\boxed{18}.", 1.0),
    ("She earns 9 * 2 dollars, so $\\boxed{\\$18}$", 1.0),
    ("Total per day:\n\\[\n\\boxed{1,800}\n\\]\n", 1.0),
    ("\\boxed{18}", 0.0),
    ("We get \\boxed{18} dollars per day.", 0.0),
    ("Step one gives \\boxed{9}, then \\boxed{18}", 0.0),
    ("So it is \\boxed{18} \\boxed{18}", 0.0),
    ("Answer: \\boxed{eighteen}", 0.0),
    ("Answer: \\boxed{17 or 18}", 0.0),
    ("The answer is 18.", 0.0),
    ("Answer: \\boxed{18}\n\nHope this helps!", 0.0),
    ("The total is \\boxed{18} (= 20 - 2)", 0.0),
])
def test_format_reward(ans, completion, expected):
    assert ans.format_reward(completion) == expected


def test_correctness_reward_needs_box_and_one_number(ans):
    assert ans.correctness_reward("9 * 2 = 18, so \\boxed{18}", "18") == 1.0
    assert ans.correctness_reward("cost: \\boxed{\\$18.00} per day, nice", "18") == 1.0
    assert ans.correctness_reward("\\boxed{17}, no wait: \\boxed{18}", "18") == 1.0
    assert ans.correctness_reward("The answer is 18.", "18") == 0.0, "không có \\boxed thì không có điểm đúng"
    assert ans.correctness_reward("\\boxed{17 or 18}", "18") == 0.0, "liệt kê nhiều số là lách reward"
    assert ans.correctness_reward("\\boxed{18}, no wait: \\boxed{17}", "18") == 0.0


def test_total_reward(ans):
    good = "Half of 36 is 18, so \\boxed{18}."
    assert ans.total_reward(good, "18") == pytest.approx(1.2)
    assert ans.total_reward(good, "17") == pytest.approx(0.2)
    assert ans.total_reward(good, "18", format_weight=0.5) == pytest.approx(1.5)
    assert ans.total_reward("\\boxed{18} dollars", "18") == pytest.approx(1.0)
    assert ans.total_reward("The answer is 18", "18") == 0.0


def test_real_gsm8k_answers(ans):
    import pandas as pd

    root = ex.dataset("gsm8k") / "main"
    test = pd.read_parquet(root / "test-00000-of-00001.parquet")
    train = pd.read_parquet(root / "train-00000-of-00001.parquet")
    golds = [ans.gold_answer(a) for a in pd.concat([train.answer, test.answer])]
    assert len(golds) == 7473 + 1319
    assert sum(g.startswith("-") for g in golds) == 5
    assert all("/" not in g for g in golds), "đáp số GSM8K đều là số nguyên"
    assert ans.gold_answer(test.answer[0]) == "18"
    # lời giải mẫu của chính GSM8K: đáp số phải đọc ra đúng gold ở mọi câu
    assert all(ans.extract_answer(a) == ans.gold_answer(a) for a in test.answer)

import pytest

from testkit import Exercise

ex = Exercise(__file__)


@pytest.fixture(scope="module")
def nb():
    return ex.notebook("rft.ipynb")


GOOD_LONG = "First, 3 * 12 = 36 cookies.\nThen 36 - 20 = 16 cookies are left.\nSo the answer is \\boxed{16}."
GOOD_SHORT = "36 - 20 = 16, so \\boxed{16}."
GOOD_SHORT_SPACED = "36 - 20  = 16,\n so   \\boxed{16}. "
WRONG = "36 - 20 = 14, so \\boxed{14}."
BAD_FORMAT = "36 - 20 = 16, so \\boxed{16} cookies left."
NO_BOX = "The answer is 16."


def test_pasted_rewards(nb):
    assert nb.correctness_reward(GOOD_SHORT, "16") == 1.0
    assert nb.format_reward(BAD_FORMAT) == 0.0
    assert nb.normalize_number("1,600") == "1600"


def test_select_traces_filters_and_orders(nb):
    samples = [GOOD_LONG, WRONG, BAD_FORMAT, NO_BOX, GOOD_SHORT]
    assert nb.select_traces(samples, "16", max_keep=2) == [GOOD_SHORT, GOOD_LONG]
    assert nb.select_traces(samples, "16", max_keep=1) == [GOOD_SHORT]
    assert nb.select_traces(samples, "14") == [WRONG], "đúng đáp số theo gold được truyền vào"
    assert nb.select_traces([WRONG, NO_BOX, BAD_FORMAT], "16") == []


def test_select_traces_dedupes_on_whitespace(nb):
    out = nb.select_traces([GOOD_SHORT_SPACED, GOOD_LONG, GOOD_SHORT], "16", max_keep=3)
    assert len(out) == 2, "hai lời giải chỉ khác khoảng trắng là một"
    assert out[0] == GOOD_SHORT_SPACED, "giữ bản xuất hiện đầu, nguyên văn"
    assert out[1] == GOOD_LONG


def test_select_traces_stable_for_equal_length(nb):
    a = "We get 4 * 4 = 16, so \\boxed{16}."
    b = "We get 8 + 8 = 16, so \\boxed{16}."
    assert len(a) == len(b)
    assert nb.select_traces([b, a], "16", max_keep=2) == [b, a]


def test_word_ngrams(nb):
    grams = nb.word_ngrams("Tom has 3 apples. TOM has 3 pears!", 3)
    assert ("tom", "has", "3") in grams
    assert ("3", "apples", "tom") in grams, "bỏ dấu câu, chữ thường"
    assert len(grams) == 5
    assert nb.word_ngrams("too short", 3) == set()


def test_contaminated(nb):
    eval_qs = ["Kyle bought a book for $19.50 with a 25% discount. What was the original price of the book?"]
    train_qs = [
        "Venny spent $15000 on a car at 40% of the original price. What was the original price of the car?",
        "Kyle bought a book for $19.50 with a 25% discount. What was the original price?",
        "Completely different question about trains and speed.",
    ]
    assert nb.contaminated(train_qs, eval_qs, n=13) == {1}
    assert nb.contaminated(train_qs, eval_qs, n=6) == {0, 1}, "n nhỏ bắt cả cụm từ chung của đề toán"
    assert nb.contaminated(train_qs, [], n=13) == set()


def test_to_sft_record(nb):
    rec = nb.to_sft_record("How many?", GOOD_SHORT)
    assert rec == {"prompt": [{"role": "system", "content": nb.SYSTEM_COT}, {"role": "user", "content": "How many?"}],
                   "completion": [{"role": "assistant", "content": GOOD_SHORT}]}
    assert nb.to_sft_record("Q", "A", system="S")["prompt"][0] == {"role": "system", "content": "S"}


def test_real_gsm8k_contamination(nb):
    import pandas as pd

    root = ex.dataset("gsm8k") / "main"
    train = pd.read_parquet(root / "train-00000-of-00001.parquet")
    test = pd.read_parquet(root / "test-00000-of-00001.parquet").iloc[:500]
    assert nb.contaminated(list(train.question), list(test.question), 13) == set()
    assert len(nb.contaminated(list(train.question), list(test.question), 8)) > 20

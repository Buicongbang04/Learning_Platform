import numpy as np
import pytest

from testkit import Exercise

ex = Exercise(__file__)


@pytest.fixture(scope="module")
def nb():
    return ex.notebook("grpo_trl.ipynb")


def conv(text):
    return [{"role": "assistant", "content": text}]


def test_pasted(nb):
    assert nb.normalize_number("1,600") == "1600"
    assert nb.extract_answer("pages 3-4") == "4"
    assert nb.correctness_reward("\\boxed{17 or 18}", "18") == 0.0
    assert nb.format_reward("So 9 * 2 = 18 and \\boxed{18}.") == 1.0
    a = np.array([True, False] * 50)
    assert nb.paired_bootstrap(a, a.copy(), n_boot=200) == (0.0, 0.0, 0.0)


def test_build_rows(nb):
    rows = nb.build_rows(["Q1?", "Q2?"], ["work <<1+1=2>>\n#### 1,600", "x\n#### -3"])
    assert rows == [
        {"prompt": [{"role": "system", "content": nb.SYSTEM_COT}, {"role": "user", "content": "Q1?"}], "answer": "1600"},
        {"prompt": [{"role": "system", "content": nb.SYSTEM_COT}, {"role": "user", "content": "Q2?"}], "answer": "-3"},
    ]


def test_trl_reward_functions(nb):
    completions = [conv("9 * 2 = 18, so \\boxed{18}."), conv("\\boxed{18} dollars"), conv("I think 18."),
                   conv("Maybe \\boxed{17 or 18}")]
    answer = ["18", "18", "18", "18"]
    assert nb.reward_correct(completions, answer=answer, prompts=None, completion_ids=None) == [1.0, 1.0, 0.0, 0.0]
    assert nb.reward_format(completions, answer=answer, prompts=None) == [1.0, 0.0, 0.0, 0.0]
    assert nb.reward_correct([conv("ok \\boxed{5}")], answer=["6"]) == [0.0]

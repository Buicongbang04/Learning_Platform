import pytest

from testkit import Exercise

ex = Exercise(__file__)


@pytest.fixture(scope="module")
def nb():
    return ex.notebook("distill.ipynb")


def result(acc, correct):
    return {"accuracy": acc, "boxed_correct": acc - 0.01, "format": 0.9, "mean_tokens": 250.0, "correct": correct}


def test_pasted(nb):
    assert nb.normalize_number("$2.50") == "5/2"
    assert nb.select_traces(["\\boxed{3}.", "So 1 + 2 = 3, \\boxed{3}.", "Hmm \\boxed{4}."], "3") == \
        ["So 1 + 2 = 3, \\boxed{3}."]
    assert nb.to_sft_record("Q", "A")["completion"] == [{"role": "assistant", "content": "A"}]


def test_compare_table(nb):
    base = [True, False, False, True] * 50
    better = [True, True, False, True] * 50
    worse = [False, False, False, True] * 50
    results = {"base": result(0.5, base), "distill": result(0.75, better), "rft": result(0.25, worse)}
    table = nb.compare_table(results)
    assert list(table.columns) == ["method", "accuracy", "boxed_correct", "format", "mean_tokens", "delta", "lo", "hi"]
    assert list(table["method"]) == ["base", "distill", "rft"]
    rows = {r["method"]: r for r in table.to_dict("records")}
    assert (rows["base"]["delta"], rows["base"]["lo"], rows["base"]["hi"]) == (0.0, 0.0, 0.0)
    assert rows["distill"]["delta"] == pytest.approx(0.25)
    assert rows["distill"]["lo"] > 0, "cải thiện ở 50 câu trên 200, không câu nào tệ đi: khoảng tin cậy không chứa 0"
    assert rows["rft"]["delta"] == pytest.approx(-0.25) and rows["rft"]["hi"] < 0
    assert (rows["distill"]["delta"], rows["distill"]["lo"], rows["distill"]["hi"]) == \
        nb.paired_bootstrap(base, better, seed=0)


def test_compare_table_checks_inputs(nb):
    results = {"base": result(0.5, [True, False] * 10), "other": result(0.5, [True] * 30)}
    with pytest.raises(ValueError):
        nb.compare_table(results)
    with pytest.raises(KeyError):
        nb.compare_table({"a": result(0.5, [True])}, base="base")

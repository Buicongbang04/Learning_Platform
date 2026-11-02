import numpy as np
import pytest

from testkit import Exercise

ex = Exercise(__file__)

QUESTION = "A baker makes 3 trays of 12 cookies and sells 20. How many cookies are left?"


@pytest.fixture(scope="module")
def nb():
    return ex.notebook("ttc.ipynb")


# ---------- Dán từ Basic 01, 02 ----------

def test_pasted_helpers(nb):
    assert nb.normalize_number("$1,234.50") == "2469/2"
    assert nb.extract_answer("So 36 - 20 = 16.\nThe answer is \\boxed{16} cookies, 3 trays") == "16"
    assert nb.extract_answer("pages 3-4") == "4"
    assert nb.majority_vote(["2", "10", "1"]) == "2"
    assert nb.majority_vote([None, None]) is None
    assert nb.best_of_n(["1", "2"], [0.5, 0.5]) == "1"
    assert nb.pass_at_k(4, 2, 2) == pytest.approx(5 / 6)


# ---------- Prompt ----------

def test_build_messages(nb):
    direct = nb.build_messages(QUESTION, "direct")
    cot = nb.build_messages(QUESTION, "cot")
    for msgs, system in ((direct, nb.SYSTEM_DIRECT), (cot, nb.SYSTEM_COT)):
        assert [m["role"] for m in msgs] == ["system", "user"]
        assert msgs[0]["content"] == system
        assert msgs[1]["content"] == QUESTION, "câu hỏi giữ nguyên, không thêm chữ"
    assert "boxed" in nb.SYSTEM_COT and "step" in nb.SYSTEM_COT.lower()
    with pytest.raises(ValueError):
        nb.build_messages(QUESTION, "few_shot")


# ---------- Bảng scaling ----------

def _fixture():
    answers = [["1", "2", "2", "2", "1", "1"], ["5", None, "5", "6", "6", "6"]]
    tokens = [[100, 120, 80, 90, 110, 100], [200, 10, 210, 190, 205, 195]]
    logprobs = [[-0.1, -0.5, -0.2, -0.3, -0.4, -0.05], [-0.3, -2.0, -0.2, -0.1, -0.4, -0.6]]
    return answers, tokens, logprobs, ["2", "5"]


def test_scaling_table_columns_and_values(nb):
    answers, tokens, logprobs, golds = _fixture()
    table = nb.scaling_table(answers, tokens, logprobs, golds, ks=[1, 2, 3, 6])
    assert list(table.columns) == ["k", "maj", "pass", "bon_logprob", "tokens"]
    assert list(table["k"]) == [1, 2, 3, 6]
    row = {int(r["k"]): r for r in table.to_dict("records")}
    assert row[1]["maj"] == pytest.approx((3 / 6 + 2 / 6) / 2)
    assert row[2]["maj"] == pytest.approx((1 / 3 + 2 / 3) / 2)
    assert row[6]["maj"] == pytest.approx(0.0)
    assert row[1]["bon_logprob"] == pytest.approx(row[1]["maj"]), "k = 1: chọn theo verifier hay bỏ phiếu đều là chính lời giải đó"
    # k = 2, câu 1: (1,2)->-0.1 thắng: "1"; (2,2)->"2"; (1,1)->"1" => 1/3. câu 2: (5,None)->5; (5,6)->6 (-0.1); (6,6)->6 => 1/3
    assert row[2]["bon_logprob"] == pytest.approx(1 / 3)
    # k = 6: câu 1 logprob cao nhất -0.05 ở "1"; câu 2 -0.1 ở "6"
    assert row[6]["bon_logprob"] == pytest.approx(0.0)
    assert row[2]["pass"] == pytest.approx((nb.pass_at_k(6, 3, 2) + nb.pass_at_k(6, 2, 2)) / 2)
    assert row[1]["tokens"] == pytest.approx((600 / 6 + 1010 / 6) / 2)
    assert row[2]["tokens"] == pytest.approx(2 * row[1]["tokens"])
    assert row[6]["tokens"] == pytest.approx(600 / 2 + 1010 / 2)


def test_scaling_table_tokens_count_used_blocks_only(nb):
    answers = [["1", "1", "2", "2", "3"]]
    tokens = [[10, 20, 30, 40, 1000]]
    logprobs = [[0.0] * 5]
    table = nb.scaling_table(answers, tokens, logprobs, ["1"], ks=[2])
    assert table["tokens"].iloc[0] == pytest.approx(50.0), "khối (10, 20) và (30, 40); lời giải thứ 5 không thuộc khối nào"
    assert table["maj"].iloc[0] == pytest.approx(0.5)


# ---------- Bootstrap theo cặp ----------

def test_paired_bootstrap_basic(nb):
    a = np.array([1, 0, 1, 0, 1, 0, 0, 1, 0, 0] * 20, dtype=bool)
    b = a.copy()
    diff, lo, hi = nb.paired_bootstrap(a, b, n_boot=500, seed=0)
    assert (diff, lo, hi) == (0.0, 0.0, 0.0), "hai cột giống hệt: hiệu và mọi mẫu bootstrap đều 0"
    b[:30] = True
    diff, lo, hi = nb.paired_bootstrap(a, b, n_boot=2000, seed=0)
    assert diff == pytest.approx(b.mean() - a.mean())
    assert lo <= diff <= hi
    assert nb.paired_bootstrap(a, b, n_boot=2000, seed=0) == (diff, lo, hi), "cùng seed, cùng kết quả"
    assert all(isinstance(x, float) for x in (diff, lo, hi))


def test_paired_bootstrap_width_and_pairing(nb):
    rng = np.random.default_rng(1)
    n = 400
    a = rng.random(n) < 0.5
    flip = rng.random(n) < 0.1
    b = np.where(flip, ~a, a)
    diff, lo, hi = nb.paired_bootstrap(a, b, n_boot=4000, seed=0)
    d = b.astype(float) - a.astype(float)
    expected_half = 1.96 * d.std() / np.sqrt(n)
    assert (hi - lo) / 2 == pytest.approx(expected_half, rel=0.2), "khoảng tin cậy theo cặp: dựa trên phân phối của hiệu từng câu"
    unpaired_half = 1.96 * np.sqrt(a.var() / n + b.var() / n)
    assert (hi - lo) / 2 < 0.6 * unpaired_half, "lấy mẫu lại cùng chỉ số cho cả hai cột thì khoảng hẹp hơn hẳn"

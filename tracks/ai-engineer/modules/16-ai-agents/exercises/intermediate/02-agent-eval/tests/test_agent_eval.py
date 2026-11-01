import math

import pytest

from testkit import Exercise

ex = Exercise(__file__)


@pytest.fixture(scope="module")
def nb():
    return ex.notebook("agent_eval.ipynb")


@pytest.mark.parametrize("text, numbers", [
    ("Tổng là 165.000 đồng.", [165000.0]),
    ("Tổng là 165,000 đồng.", [165000.0]),
    ("Giá 1.234.567 ₫ và 1 000 000 đ", [1234567.0, 1000000.0]),
    ("Khoảng 5,31 USD, tức 2.84 hay 0.8", [5.31, 2.84, 0.8]),
    ("Mã sách B19, năm 1988, còn 120 cuốn", [19.0, 1988.0, 120.0]),
    ("Đơn hàng là 2,3 triệu đồng", [2300000.0]),
    ("Giảm 15 nghìn, còn 90ngàn", [15000.0, 90000.0]),
    ("Không có số nào.", []),
    ("", []),
])
def test_numbers_in(nb, text, numbers):
    assert nb.numbers_in(text) == pytest.approx(numbers)


def test_numbers_in_returns_floats_in_order(nb):
    out = nb.numbers_in("3 cuốn giá 55.000 là 165.000")
    assert out == [3.0, 55000.0, 165000.0] and all(isinstance(x, float) for x in out)


def test_check_answer(nb):
    assert nb.check_answer("Mua 3 cuốn hết 165.000 đồng.", [165000])
    assert nb.check_answer("Giá khoảng 5,31 USD", [5.31])
    assert nb.check_answer("Giá khoảng 5,31 USD", [135000 / 25400]), "làm tròn 2 chữ số vẫn khớp (sai lệch <= 0.01)"
    assert nb.check_answer("Giá khoảng 5,3 USD", [135000 / 25400]) is False
    assert nb.check_answer("Giá khoảng 5.315 đô", [5.31]) is False, "5.315 là 5315 theo quy ước hàng nghìn"
    assert nb.check_answer("Đơn DH03 của chị Hà, tổng 272.000 đ", ["hà", 272000])
    assert nb.check_answer("Đơn DH03 tổng 272.000 đ", ["Hà", 272000]) is False, "mọi phần tử phải đạt"
    assert nb.check_answer("Tác giả là NGUYỄN TUÂN.", ["Nguyễn Tuân"])
    assert nb.check_answer("Tổng 165.001 đồng", [165000]) is False
    assert nb.check_answer(None, [1]) is False and nb.check_answer("", ["x"]) is False


def test_wilson_interval(nb):
    lo, hi = nb.wilson_interval(17, 24)
    assert lo == pytest.approx(0.5081, abs=1e-3) and hi == pytest.approx(0.8509, abs=1e-3)
    lo, hi = nb.wilson_interval(0, 10)
    assert lo == pytest.approx(0.0, abs=1e-9) and hi == pytest.approx(0.2775, abs=1e-3)
    lo, hi = nb.wilson_interval(10, 10)
    assert hi == pytest.approx(1.0, abs=1e-9) and lo == pytest.approx(0.7225, abs=1e-3)
    assert nb.wilson_interval(0, 0) == (0.0, 1.0)
    lo99, hi99 = nb.wilson_interval(17, 24, z=2.576)
    assert lo99 < 0.5081 and hi99 > 0.8509


def test_discordant(nb):
    a = {"t1": True, "t2": True, "t3": False, "t4": False, "t5": True}
    b = {"t1": True, "t2": False, "t3": True, "t4": False, "t5": False}
    assert nb.discordant(a, b) == (["t2", "t5"], ["t3"])
    assert nb.discordant(b, a) == (["t3"], ["t2", "t5"])
    with pytest.raises(ValueError):
        nb.discordant(a, {"t1": True})


def step(kind, observation=None, ok=None, args=None):
    return {"index": 0, "kind": kind, "reply": "", "tool": "x", "args": args if args is not None else {},
            "observation": observation, "ok": ok, "seconds": 0.1}


def row(ok=False, stopped="answer", answer="", question="Câu hỏi?", steps=()):
    return {"ok": ok, "stopped": stopped, "answer": answer, "question": question, "steps": list(steps)}


def test_classify_failure_order(nb):
    c = nb.classify_failure
    assert c(row(ok=True, stopped="max_steps")) == "ok"
    assert c(row(stopped="max_steps", steps=[step("action", "ERROR: x", False)])) == "no_answer"
    assert c(row(stopped="format_error")) == "no_answer"
    assert c(row(answer="Giá là 99.000 đồng", steps=[step("final")])) == "no_tool"
    obs = '[{"id": "B02", "price": 55000}]'
    assert c(row(answer="3 cuốn hết 150.000 đồng", question="Mua 3 cuốn Tắt đèn?",
                 steps=[step("action", obs, True), step("final")])) == "hallucinated_number"
    assert c(row(answer="3 cuốn giá 55.000 đồng", question="Mua 3 cuốn Tắt đèn?",
                 steps=[step("action", obs, True), step("action", "ERROR: calculator lỗi", False),
                        step("final")])) == "tool_error", "số đều có nguồn (3 trong câu hỏi, 55000 trong observation)"
    assert c(row(answer="3 cuốn giá 55.000 đồng", question="Mua 3 cuốn?",
                 steps=[step("action", obs, True), step("final")])) == "wrong_other"


def test_classify_hallucination_checks_every_observation(nb):
    steps = [step("action", '{"price": 110000}', True), step("action", "330000", True), step("final")]
    assert nb.classify_failure(row(answer="Tổng 330.000 đồng", steps=steps)) == "wrong_other"
    assert nb.classify_failure(row(answer="Tổng 330.000 đồng, giảm còn 300.000", steps=steps)) == "hallucinated_number"
    assert nb.classify_failure(row(answer="Khoảng 5,31 USD", steps=[step("action", "5.3150", True)])) == "wrong_other"
    assert nb.classify_failure(row(answer="Khoảng 5,31 USD", steps=[step("action", "5.315", True)])) \
        == "hallucinated_number", "5.315 trong observation là 5315 theo quy ước hàng nghìn, không khớp 5,31"


def test_every_task_has_a_passing_answer(nb):
    import bookstore

    assert len(bookstore.TASKS) == 24 and len({t[0] for t in bookstore.TASKS}) == 24
    for task_id, group, question, expected in bookstore.TASKS:
        parts = [e if isinstance(e, str) else (f"{e:,.0f}".replace(",", ".") if float(e).is_integer()
                                                else f"{e:.2f}".replace(".", ",")) for e in expected]
        answer = "Kết quả: " + "; ".join(parts) + "."
        assert nb.check_answer(answer, expected), (task_id, answer)
        assert not nb.check_answer("Tôi không biết.", expected) or expected == ["không"], task_id
    assert math.isclose(bookstore.calculator("2 * 110000 + 79000"), 299000)


def test_classify_hallucination_in_tool_arguments(nb):
    order = '{"id": "DH01", "items": [{"book_id": "B05", "quantity": 2}, {"book_id": "B13", "quantity": 1}]}'
    laundered = [step("action", order, True, {"order_id": "DH01"}),
                 step("action", "1150000", True, {"expression": "350000 * 2 + 450000"}), step("final")]
    r = row(answer="Tổng tiền đơn DH01 là 1.150.000 đồng.", question="Tổng tiền đơn hàng DH01?", steps=laundered)
    assert nb.classify_failure(r) == "hallucinated_number", "giá bịa đi qua calculator vẫn là số bịa"
    honest = [step("action", order, True, {"order_id": "DH01"}),
              step("action", '{"price": 110000}', True, {"book_id": "B05"}),
              step("action", "220000", True, {"expression": "2 * 110000"}), step("final")]
    r = row(answer="Tổng là 220.000 đồng.", question="Tổng tiền đơn hàng DH01?", steps=honest)
    assert nb.classify_failure(r) == "wrong_other", "mọi số trong tham số đều đã thấy ở observation trước đó"
    guessed = [step("action", "ERROR: không có sách", False, {"book_id": "B07"}), step("final")]
    r = row(answer="Không rõ.", question="Giá cuốn Số đỏ?", steps=guessed)
    assert nb.classify_failure(r) == "hallucinated_number", "đoán mã sách trước khi tra là dùng số không có nguồn"
    late = [step("action", '{"price": 72000}', True, {"query": "Số đỏ"}),
            step("action", "72000", True, {"expression": "72000"}), step("final")]
    assert nb.classify_failure(row(answer="Giá 72.000 đồng.", question="Giá Số đỏ?", steps=late)) == "wrong_other"


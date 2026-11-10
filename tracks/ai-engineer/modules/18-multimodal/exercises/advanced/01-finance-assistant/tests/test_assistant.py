import json

import pytest
from llmkit import FakeLLM, LLMError

from testkit import Exercise

ex = Exercise(__file__)


@pytest.fixture(scope="module")
def nb():
    return ex.notebook("assistant.ipynb")


class SchemaLLM(FakeLLM):
    def __init__(self, replies):
        super().__init__(replies)
        self.schemas = []

    def chat(self, messages, *, model=None, temperature=0.0, json_schema=None):
        self.schemas.append(json_schema)
        return super().chat(messages, model=model, temperature=temperature, json_schema=json_schema)


class BrokenLLM:
    def __init__(self):
        self.calls = 0

    def chat(self, messages, **kwargs):
        self.calls += 1
        raise LLMError("Ollama tắt")


RULES = {"đồ uống": ["TEA", "COFFEE", "ES"], "ăn uống": ["NASI", "AYAM", "DONUT"]}


def test_parse_amount_pasted(nb):
    assert nb.parse_amount("60.000") == 60000 and nb.parse_amount("24,000") == 24000
    assert nb.parse_amount("1.234,50") == pytest.approx(1234.5) and nb.parse_amount("x") is None


def test_expenses_from_receipt(nb):
    pred = {"items": [{"name": " ICE TEA ", "quantity": 2, "amount": "16.000"}, {"name": "DISC", "amount": "-5.000"},
                      {"name": "", "amount": "9,000"}, "rác", {"name": "NOTE"}], "total": "20.000"}
    out = nb.expenses_from_receipt(pred, "2026-10-03", "Quán A")
    assert [(e.item, e.amount, e.date, e.merchant, e.category) for e in out] == [
        ("ICE TEA", 16000.0, "2026-10-03", "Quán A", "khác"), ("(không tên)", 9000.0, "2026-10-03", "Quán A", "khác")]
    only_total = nb.expenses_from_receipt({"items": [{"name": "X", "amount": "?"}], "total": "75.500"}, "2026-10-05", "B")
    assert [(e.item, e.amount) for e in only_total] == [("(tổng hoá đơn)", 75500.0)]
    assert nb.expenses_from_receipt(None, "2026-10-05", "B") == []
    assert nb.expenses_from_receipt({"items": [], "total": None}, "2026-10-05", "B") == []


def test_categorize_rules_whole_words_without_llm(nb):
    fake = SchemaLLM([])
    assert nb.categorize("Ice Tea (L)", RULES, fake) == "đồ uống"
    assert nb.categorize("NASI-GORENG", RULES, fake) == "ăn uống"
    assert nb.categorize("ES TEH MANIS", RULES, fake) == "đồ uống", "từ khoá đầu tiên theo thứ tự dict"
    assert fake.calls == [], "khớp luật thì không gọi LLM"


def test_categorize_llm_fallback(nb):
    fake = SchemaLLM([json.dumps({"category": "mua sắm"})])
    assert nb.categorize("TESTER LIPSTICK", RULES, fake) == "mua sắm", "'TES' trong 'TESTER' không phải từ 'TEA'/'ES'"
    assert len(fake.calls) == 1
    schema = fake.schemas[0]
    assert schema is not None and set(schema["properties"]["category"]["enum"]) == set(nb.CATEGORIES)
    assert "TESTER LIPSTICK" in json.dumps(fake.calls[0], ensure_ascii=False)
    for reply in ["không phải json", json.dumps({"category": "du lịch"}), json.dumps(["mua sắm"])]:
        assert nb.categorize("VE XEM PHIM", RULES, SchemaLLM([reply])) == "khác"
    broken = BrokenLLM()
    assert nb.categorize("VE XEM PHIM", RULES, broken) == "khác" and broken.calls == 1


def test_monthly_summary(nb):
    E = nb.Expense
    xs = [E("2026-10-03", "A", "ICE TEA", 16000, "đồ uống"), E("2026-10-03", "A", "NASI", 25000, "ăn uống"),
          E("2026-10-05", "B", "COFFEE", 45000, "đồ uống"), E("2026-10-05", "A", "DONUT", 25000, "ăn uống"),
          E("2026-09-30", "A", "STEAK", 300000, "ăn uống"), E("2026-10-31", "C", "VE", 90000, "giải trí")]
    s = nb.monthly_summary(xs, "2026-10")
    assert s["month"] == "2026-10" and s["total"] == pytest.approx(201000)
    assert list(s["by_category"].items()) == [("giải trí", 90000), ("đồ uống", 61000), ("ăn uống", 50000)]
    assert s["n_receipts"] == 4
    assert s["top_items"] == [("VE", 90000), ("COFFEE", 45000), ("NASI", 25000)]
    empty = nb.monthly_summary(xs, "2026-08")
    assert empty["total"] == 0 and empty["by_category"] == {} and empty["n_receipts"] == 0 and empty["top_items"] == []


def test_monthly_summary_category_ties(nb):
    E = nb.Expense
    s = nb.monthly_summary([E("2026-10-01", "A", "y", 10, "đi lại"), E("2026-10-01", "A", "x", 10, "mua sắm")], "2026-10")
    assert list(s["by_category"]) == sorted(["mua sắm", "đi lại"]), "hoà tiền thì theo tên nhóm"


@pytest.mark.parametrize("text, masked", [
    ("Gọi 0912 345 678 nhé", "Gọi [PHONE] nhé"),
    ("số +84 912.345.678", "số [PHONE]"),
    ("thẻ 4111 1111 1111 1111 hết hạn", "thẻ [CARD] hết hạn"),
    ("thẻ 4111-1111-1111-1112 sai", "thẻ 4111-1111-1111-1112 sai"),
    ("mail thu.ha@vi-du.vn, gọi 0987654321", "mail [EMAIL], gọi [PHONE]"),
    ("mã đơn 123456789012 và 75.000 đồng", "mã đơn 123456789012 và 75.000 đồng"),
])
def test_mask_pii(nb, text, masked):
    assert nb.mask_pii(text) == masked


def test_route(nb):
    fake = SchemaLLM([json.dumps({"intent": "by_category", "month": "2026-09", "category": "đồ uống"})])
    assert nb.route("Tháng chín tôi tiêu bao nhiêu cho đồ uống?", fake) == \
        {"intent": "by_category", "month": "2026-09", "category": "đồ uống"}
    assert len(fake.calls) == 1 and fake.schemas[0] is not None
    assert "Tháng chín tôi tiêu bao nhiêu cho đồ uống?" in json.dumps(fake.calls[0], ensure_ascii=False)
    odd = SchemaLLM([json.dumps({"intent": "total", "month": "2026-13", "category": "xăng"})])
    assert nb.route("?", odd) == {"intent": "total", "month": None, "category": None}
    other = {"intent": "other", "month": None, "category": None}
    assert nb.route("?", SchemaLLM([json.dumps({"intent": "weather"})])) == other
    assert nb.route("?", SchemaLLM(["{không phải json"])) == other
    assert nb.route("?", BrokenLLM()) == other


def test_format_vnd(nb):
    assert nb.format_vnd(1250000) == "1.250.000 đồng"
    assert nb.format_vnd(999.6) == "1.000 đồng"
    assert nb.format_vnd(0) == "0 đồng"

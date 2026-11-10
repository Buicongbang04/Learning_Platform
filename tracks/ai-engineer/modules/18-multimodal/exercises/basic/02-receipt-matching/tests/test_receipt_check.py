import math

import pytest

from testkit import Exercise

ex = Exercise(__file__)

# gt_parse kiểu CORD, tự viết: menu là dict khi một dòng, list khi nhiều dòng; "sub" là món kèm
GT_ONE = {"menu": {"nm": "JASMINE MT ( L )", "cnt": "1", "price": "24,000",
                   "sub": {"nm": "COCONUT JELLY ( L )", "price": "4,000"}},
          "sub_total": {"subtotal_price": "28,000"},
          "total": {"total_price": "28,000", "cashprice": "100,000", "changeprice": "72,000"}}
GT_MANY = {"menu": [{"nm": "ICE BLACKCOFFE", "cnt": "2", "price": "82,000"},
                    {"nm": "AVOCADO COFFEE", "cnt": "1X", "price": "61,000"},
                    {"nm": "CHIKEN KATSU FF", "price": "51,000"},
                    {"nm": "NOTE: LESS SUGAR"}],
           "total": {"total_price": "174,600"}}
GT_NO_TOTAL = {"menu": [{"nm": "TICKET CP", "cnt": "2", "price": "60.000"}], "sub_total": {"subtotal_price": "60.000"}}


@pytest.fixture(scope="module")
def m():
    return ex.module("receipt_check.py")


@pytest.mark.parametrize("text, value", [
    ("60.000", 60000), ("24,000", 24000), ("17500", 17500), ("Rp 1.250.000", 1250000), ("1,250,000đ", 1250000),
    ("60.000 VND", 60000), ("@11000", 11000), ("5.455", 5455), ("2.00", 2.0), ("12.5", 12.5),
    ("1.234,50", 1234.5), ("1,234.50", 1234.5), ("-60.000", -60000), ("(5.000)", -5000), ("2.000,-", 2000),
    (95000, 95000), (12.5, 12.5),
])
def test_parse_amount(m, text, value):
    assert m.parse_amount(text) == pytest.approx(value)


@pytest.mark.parametrize("text", ["", "abc", None, "1.000.5"])
def test_parse_amount_none(m, text):
    assert m.parse_amount(text) is None


def test_gold_from_cord_flattens_menu_and_sub(m):
    g = m.gold_from_cord(GT_ONE)
    assert g["total"] == pytest.approx(28000)
    assert [(i["name"], i["quantity"], i["amount"]) for i in g["items"]] == [
        ("JASMINE MT ( L )", 1.0, 24000.0), ("COCONUT JELLY ( L )", 1.0, 4000.0)]


def test_gold_from_cord_list_quantities_and_unpriced(m):
    g = m.gold_from_cord(GT_MANY)
    assert [(i["quantity"], i["amount"]) for i in g["items"]] == [(2.0, 82000.0), (1.0, 61000.0), (1.0, 51000.0)]
    assert g["total"] == pytest.approx(174600)
    assert m.gold_from_cord(GT_NO_TOTAL)["total"] is None
    assert m.gold_from_cord({"total": {"total_price": "5.000"}}) == {"items": [], "total": 5000.0}


def test_match_items_needs_amount_and_name(m):
    gold = m.gold_from_cord(GT_MANY)["items"]
    pred = [{"name": "ICE BLACK COFFEE", "quantity": 2, "amount": "82.000"},   # tên viết khác, tiền đúng
            {"name": "AVOCADO COFFEE", "quantity": 1, "amount": "16,000"},     # tên đúng, tiền sai
            {"name": "SERVICE CHARGE", "quantity": 1, "amount": "51.000"},     # tiền trùng, tên khác hẳn
            {"name": "CHICKEN KATSU", "quantity": 1, "amount": "51,000"}]
    assert m.match_items(pred[:3], gold) == [(0, 0)], "trùng số tiền mà tên khác hẳn thì không ghép"
    assert m.match_items(pred, gold) == [(0, 0), (3, 2)]


def test_match_items_is_one_to_one(m):
    gold = [{"name": "TEH MANIS", "quantity": 1.0, "amount": 8000.0}, {"name": "TEH MANIS", "quantity": 1.0, "amount": 8000.0}]
    once = [{"name": "TEH MANIS", "quantity": 1, "amount": "8.000"}]
    thrice = once * 3
    assert m.match_items(once, gold) == [(0, 0)] or m.match_items(once, gold) == [(0, 1)]
    pairs = m.match_items(thrice, gold)
    assert len(pairs) == 2
    assert len({i for i, _ in pairs}) == 2 and len({j for _, j in pairs}) == 2


def test_match_prefers_most_similar_name(m):
    gold = [{"name": "NASI GORENG", "quantity": 1.0, "amount": 25000.0},
            {"name": "NASI GORENG SPECIAL", "quantity": 1.0, "amount": 25000.0}]
    pred = [{"name": "NASI GORENG SPECIAL", "quantity": 1, "amount": "25,000"}]
    assert m.match_items(pred, gold) == [(0, 1)]


def test_score_receipt(m):
    gold = m.gold_from_cord(GT_MANY)
    pred = {"items": [{"name": "ICE BLACKCOFFEE", "quantity": 1, "amount": "82,000"},
                      {"name": "AVOCADO COFFEE", "quantity": 1, "amount": "61,000"},
                      {"name": "CHIKEN KATSU FF", "quantity": 1, "amount": "51,000"},
                      {"name": "TAX", "quantity": 1, "amount": "19,400"}],
            "total": "174.600"}
    assert m.score_receipt(pred, gold) == {"total_ok": True, "n_pred": 4, "n_gold": 3, "n_match": 3, "qty_ok": 2}
    wrong_total = dict(pred, total="194,000")
    assert m.score_receipt(wrong_total, gold)["total_ok"] is False
    assert m.score_receipt(pred, m.gold_from_cord(GT_NO_TOTAL))["total_ok"] is None
    assert m.score_receipt(None, gold) == {"total_ok": False, "n_pred": 0, "n_gold": 3, "n_match": 0, "qty_ok": 0}


def test_aggregate_is_micro(m):
    scores = [{"total_ok": True, "n_pred": 4, "n_gold": 3, "n_match": 3, "qty_ok": 2},
              {"total_ok": None, "n_pred": 1, "n_gold": 1, "n_match": 0, "qty_ok": 0},
              {"total_ok": False, "n_pred": 0, "n_gold": 6, "n_match": 0, "qty_ok": 0}]
    a = m.aggregate(scores)
    assert a["receipts"] == 3
    assert a["total_acc"] == pytest.approx(0.5), "chỉ tính hoá đơn có nhãn tổng"
    assert a["item_precision"] == pytest.approx(3 / 5)
    assert a["item_recall"] == pytest.approx(3 / 10)
    assert a["item_f1"] == pytest.approx(2 * 0.6 * 0.3 / 0.9)
    assert a["qty_acc"] == pytest.approx(2 / 3)
    empty = m.aggregate([{"total_ok": None, "n_pred": 0, "n_gold": 0, "n_match": 0, "qty_ok": 0}])
    assert empty["item_f1"] == 0.0 and math.isnan(empty["total_acc"])
    with pytest.raises(ValueError):
        m.aggregate([])

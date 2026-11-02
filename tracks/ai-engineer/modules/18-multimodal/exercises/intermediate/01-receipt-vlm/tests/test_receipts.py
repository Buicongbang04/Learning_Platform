import base64
import io
import json

import pytest
from PIL import Image

from testkit import Exercise

ex = Exercise(__file__)


@pytest.fixture(scope="module")
def nb():
    return ex.notebook("receipts.ipynb")


def quad(x1, y1, x3, y3):
    return {"x1": x1, "y1": y1, "x2": x3, "y2": y1, "x3": x3, "y3": y3, "x4": x1, "y4": y3}


# ---------- bộ chấm dán từ Basic 02 ----------

def test_checker_pasted(nb):
    assert nb.parse_amount("60.000") == 60000 and nb.parse_amount("1,234.50") == pytest.approx(1234.5)
    assert nb.parse_amount("abc") is None
    gold = nb.gold_from_cord({"menu": {"nm": "TEA", "cnt": "2", "price": "16.000", "sub": {"nm": "ICE", "price": "1.000"}},
                              "total": {"total_price": "17.000"}})
    assert [i["amount"] for i in gold["items"]] == [16000, 1000] and gold["total"] == 17000
    pred = {"items": [{"name": "TEA", "quantity": 2, "amount": "16,000"}, {"name": "TAX", "quantity": 1, "amount": "1,000"}],
            "total": "17,000"}
    s = nb.score_receipt(pred, gold)
    assert s == {"total_ok": True, "n_pred": 2, "n_gold": 2, "n_match": 1, "qty_ok": 1}
    agg = nb.aggregate([s, nb.score_receipt(None, gold)])
    assert agg["item_precision"] == pytest.approx(0.5) and agg["item_recall"] == pytest.approx(0.25)
    assert agg["total_acc"] == pytest.approx(0.5)


# ---------- ảnh và message ----------

def test_resize_for_vlm(nb):
    big = Image.new("RGB", (2000, 1000), "white")
    out = nb.resize_for_vlm(big, 1000)
    assert out.size == (1000, 500)
    tall = nb.resize_for_vlm(Image.new("RGB", (864, 1296)), 512)
    assert tall.size == (341, 512)
    small = Image.new("RGB", (300, 600))
    assert nb.resize_for_vlm(small, 1024).size == (300, 600), "không phóng to"
    assert nb.resize_for_vlm(big, None).size == (2000, 1000)


def test_encode_jpeg_b64(nb):
    img = Image.new("RGBA", (64, 40), (255, 0, 0, 128))
    b64 = nb.encode_jpeg_b64(img)
    assert isinstance(b64, str)
    raw = base64.b64decode(b64)
    assert raw[:2] == b"\xff\xd8", "phải là JPEG"
    back = Image.open(io.BytesIO(raw))
    assert back.size == (64, 40) and back.mode == "RGB"


def test_vlm_messages(nb):
    msgs = nb.vlm_messages("Đọc hoá đơn", "QUJD")
    assert msgs == [{"role": "user", "content": "Đọc hoá đơn", "images": ["QUJD"]},
                    {"role": "assistant", "content": "{"}]


# ---------- đọc câu trả lời ----------

def test_parse_reply_after_prefill(nb):
    text = ' "items": [{"name": "TEA", "quantity": 1, "amount": "8.000"}], "total": "8.000" }'
    assert nb.parse_reply(text) == {"items": [{"name": "TEA", "quantity": 1, "amount": "8.000"}], "total": "8.000"}


def test_parse_reply_variants(nb):
    assert nb.parse_reply('{"items": [], "total": "5"}') == {"items": [], "total": "5"}
    fenced = '```json\n{"items": [1, {"name": "A", "amount": "2"}], "total": null}\n```'
    assert nb.parse_reply(fenced) == {"items": [{"name": "A", "amount": "2"}], "total": None}
    trailing = ' "items": [], "total": "1"} Hope this helps! {}'
    assert nb.parse_reply(trailing) is None or nb.parse_reply(trailing)["total"] == "1"
    assert nb.parse_reply(' "items": [], "total": "1"}\n') == {"items": [], "total": "1"}


@pytest.mark.parametrize("text", ["", "Sorry, I cannot read this.", ' "items": "none"}', ' "total": "5"}',
                                  ' "items": [{"name": "A"', "[1, 2]"])
def test_parse_reply_rejects(nb, text):
    assert nb.parse_reply(text) is None


def test_ocr_lines(nb):
    gt = {"valid_line": [
        {"words": [{"text": "82,000", "row_id": 7, "quad": quad(300, 101, 360, 119)},
                   {"text": "COFFEE", "row_id": 7, "quad": quad(120, 100, 200, 120)}]},
        {"words": [{"text": "ICE", "row_id": 7, "quad": quad(50, 102, 100, 118)}]},
        {"words": [{"text": "TOTAL", "row_id": 9, "quad": quad(50, 200, 120, 220)},
                   {"text": "82,000", "row_id": 9, "quad": quad(300, 199, 360, 221)}]},
        {"words": [{"text": "KOPI", "row_id": 12, "quad": quad(150, 20, 220, 40)},
                   {"text": "TOKO", "row_id": 12, "quad": quad(60, 22, 140, 38)}]},
    ]}
    assert nb.ocr_lines(gt) == "TOKO KOPI\nICE COFFEE 82,000\nTOTAL 82,000"

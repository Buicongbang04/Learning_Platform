import pandas as pd
import pytest

from testkit import Exercise

ex = Exercise(__file__)


@pytest.fixture(scope="module")
def pii():
    return ex.module("pii.py")


def types(found):
    return [(d["type"], d["value"]) for d in found]


def test_luhn(pii):
    assert pii.luhn_ok("4111 1111 1111 1111")
    assert pii.luhn_ok("5500-0000-0000-0004")
    assert not pii.luhn_ok("4111 1111 1111 1112")
    assert not pii.luhn_ok("4111")


def test_cpf(pii):
    assert pii.cpf_ok("529.982.247-25")
    assert pii.cpf_ok("12345678909")
    assert not pii.cpf_ok("529.982.247-26")
    assert not pii.cpf_ok("111.111.111-11")
    assert not pii.cpf_ok("1234567890")


def test_detect_mixed(pii):
    text = ("Cliente maria.silva2@gmail.com, CPF 529.982.247-25, cartao 4111 1111 1111 1111, "
            "goi 0912 345 678 hoac +84 987.654.321")
    assert types(pii.detect(text)) == [
        ("email", "maria.silva2@gmail.com"),
        ("cpf", "529.982.247-25"),
        ("card", "4111 1111 1111 1111"),
        ("phone", "0912 345 678"),
        ("phone", "+84 987.654.321"),
    ]
    d = pii.detect(text)[1]
    assert text[d["start"]:d["end"]] == "529.982.247-25"


def test_detect_rejects_invalid(pii):
    text = "pedido 529.982.247-26 cartao 4111 1111 1111 1112 tel 0212345678 id 123456789012345678901"
    assert pii.detect(text) == []


def test_detect_no_overlap(pii):
    # 11 chữ số liền là CPF hợp lệ, không được báo thêm là phone
    assert types(pii.detect("cpf 12345678909.")) == [("cpf", "12345678909")]
    # chữ số trong email không phải phone
    assert types(pii.detect("0912345678@vnmail.vn")) == [("email", "0912345678@vnmail.vn")]


def test_redact(pii):
    text = "Email a@b.com, sdt 0912345678, the 4111-1111-1111-1111, cpf 52998224725."
    assert pii.redact(text) == "Email [EMAIL], sdt [PHONE], the [CARD], cpf [CPF]."
    assert pii.redact("khong co gi") == "khong co gi"


def test_scan_dataframe(pii):
    df = pd.DataFrame({
        "customer_id": ["c1", "c2", "c3", "c4", "c5"],
        "contact": ["a@x.com", "b@y.com", None, "c@z.com", "d@w.com"],
        "phone": ["0912345678", "0987654321", "0356789012", "n/a", "0779999999"],
        "doc": ["529.982.247-25", "123.456.789-09", "000", "x", "y"],
        "review_comment_message": ["otimo", "chegou rapido", "liga 0912345678", "ruim", "bom"],
        "price": [10.0, 20.0, 30.0, 40.0, 50.0],
    })
    tags = pii.scan_dataframe(df)
    assert tags == {"contact": {"email"}, "phone": {"phone"}, "doc": {"cpf"}}
    tags_low = pii.scan_dataframe(df, threshold=0.1)
    assert tags_low["review_comment_message"] == {"phone"}
    assert "customer_id" not in tags_low and "price" not in tags_low

import pytest

from testkit import Exercise

ex = Exercise(__file__)

EXPECTED = {
    "cname_answer.txt": {
        "qname": "shop.olist-shop.com.br",
        "qtype": "A",
        "status": "NOERROR",
        "kind": "answer",
        "authoritative": False,
        "cname_chain": ["shop.olist-shop.com.br", "shop-lb.cdn.example.net"],
        "answers": ["198.51.100.20", "198.51.100.21"],
        "ttl": 20,
        "missing_glue": [],
        "ede": None,
    },
    "nxdomain.txt": {
        "qname": "api-v2.olist-shop.com.br",
        "qtype": "A",
        "status": "NXDOMAIN",
        "kind": "nxdomain",
        "authoritative": False,
        "cname_chain": ["api-v2.olist-shop.com.br"],
        "answers": [],
        "ttl": 300,
        "missing_glue": [],
        "ede": None,
    },
    "nodata_aaaa.txt": {
        "qname": "api.olist-shop.com.br",
        "qtype": "AAAA",
        "status": "NOERROR",
        "kind": "nodata",
        "authoritative": False,
        "cname_chain": ["api.olist-shop.com.br"],
        "answers": [],
        "ttl": 60,
        "missing_glue": [],
        "ede": None,
    },
    "cname_to_nxdomain.txt": {
        "qname": "promo.olist-shop.com.br",
        "qtype": "A",
        "status": "NXDOMAIN",
        "kind": "nxdomain",
        "authoritative": False,
        "cname_chain": ["promo.olist-shop.com.br", "black-friday-2025.pages.example.org"],
        "answers": [],
        "ttl": 600,
        "missing_glue": [],
        "ede": None,
    },
    "servfail_dnssec.txt": {
        "qname": "olist-shop.com.br",
        "qtype": "A",
        "status": "SERVFAIL",
        "kind": "servfail",
        "authoritative": False,
        "cname_chain": ["olist-shop.com.br"],
        "answers": [],
        "ttl": None,
        "missing_glue": [],
        "ede": 6,
    },
    "refused.txt": {
        "qname": "www.example.com",
        "qtype": "A",
        "status": "REFUSED",
        "kind": "refused",
        "authoritative": False,
        "cname_chain": ["www.example.com"],
        "answers": [],
        "ttl": None,
        "missing_glue": [],
        "ede": None,
    },
    "referral_glue_ok.txt": {
        "qname": "olist-shop.com.br",
        "qtype": "NS",
        "status": "NOERROR",
        "kind": "referral",
        "authoritative": False,
        "cname_chain": ["olist-shop.com.br"],
        "answers": [],
        "ttl": None,
        "missing_glue": [],
        "ede": None,
    },
    "referral_missing_glue.txt": {
        "qname": "olist-shop.com.br",
        "qtype": "NS",
        "status": "NOERROR",
        "kind": "referral",
        "authoritative": False,
        "cname_chain": ["olist-shop.com.br"],
        "answers": [],
        "ttl": None,
        "missing_glue": ["ns2.olist-shop.com.br"],
        "ede": None,
    },
    "mx_authoritative.txt": {
        "qname": "olist-shop.com.br",
        "qtype": "MX",
        "status": "NOERROR",
        "kind": "answer",
        "authoritative": True,
        "cname_chain": ["olist-shop.com.br"],
        "answers": ["10 mx1.olist-shop.com.br.", "20 mx2.olist-shop.com.br."],
        "ttl": 3600,
        "missing_glue": [],
        "ede": None,
    },
}


def triage(name: str) -> dict:
    text = (ex.fixtures / name).read_text(encoding="utf-8")
    return ex.module("dig_triage.py").triage(text)


@pytest.mark.parametrize("name", sorted(EXPECTED))
def test_triage_fixture(name):
    result = triage(name)
    expected = EXPECTED[name]
    wrong = {k: (result.get(k), v) for k, v in expected.items() if result.get(k) != v}
    assert not wrong, f"{name}: khoá sai (của bạn, đúng): {wrong}"


def test_nxdomain_differs_from_nodata():
    assert triage("nxdomain.txt")["kind"] == "nxdomain"
    assert triage("nodata_aaaa.txt")["kind"] == "nodata"


def test_negative_ttl_is_min_of_soa_ttl_and_minimum():
    assert triage("nxdomain.txt")["ttl"] == 300
    assert triage("nodata_aaaa.txt")["ttl"] == 60


def test_status_of_final_name_wins_over_cname_in_answer():
    result = triage("cname_to_nxdomain.txt")
    assert result["kind"] == "nxdomain"
    assert result["cname_chain"][-1] == "black-friday-2025.pages.example.org"


def test_referral_is_not_nodata():
    assert triage("referral_glue_ok.txt")["kind"] == "referral"


def test_trailing_dot_and_case_normalised():
    lowered = (ex.fixtures / "cname_answer.txt").read_text(encoding="utf-8").replace("shop-lb.cdn.example.net.", "SHOP-LB.CDN.Example.NET.")
    result = ex.module("dig_triage.py").triage(lowered)
    assert result["cname_chain"] == ["shop.olist-shop.com.br", "shop-lb.cdn.example.net"]
    assert result["answers"] == ["198.51.100.20", "198.51.100.21"]

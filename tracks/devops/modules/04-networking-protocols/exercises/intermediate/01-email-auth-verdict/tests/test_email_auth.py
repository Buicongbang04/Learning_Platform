import importlib.util
from pathlib import Path

import pytest

from testkit import Exercise

ex = Exercise(__file__)
FIXTURES = Path(__file__).parent / "fixtures"
KEYS = ("from_domain", "spf_domain", "spf", "spf_aligned", "dkim_aligned", "dmarc", "policy", "disposition", "fallback")
EXPECTED = {
    "01-order-confirmation.eml": ("olist-shop.com.br", "olist-shop.com.br", "pass", True, True, "pass", "reject", "deliver", "deliver"),
    "02-esp-newsletter.eml": ("olist-shop.com.br", "bounces.olist-shop.com.br", "pass", True, False, "pass", "reject", "deliver", "deliver"),
    "03-forwarded-alumni.eml": ("olist-shop.com.br", "olist-shop.com.br", "fail", False, True, "pass", "reject", "deliver", "deliver"),
    "04-forwarded-mailing-list.eml": ("olist-shop.com.br", "bounces.olist-shop.com.br", "fail", False, False, "fail", "reject", "reject", "reject"),
    "05-spoofed-from.eml": ("olist-shop.com.br", "cheap-deals.example", "pass", False, False, "fail", "reject", "reject", "reject"),
    "06-forged-auth-results.eml": ("olist-shop.com.br", "mail.cheap-deals.example", "none", False, False, "fail", "reject", "reject", "reject"),
    "07-lookalike-domain.eml": ("olist-shop-br.com", "olist-shop-br.com", "pass", True, True, "pass", "none", "deliver", "deliver"),
    "08-promo-subdomain-sp.eml": ("promo.olist-shop.com.br", "promo.olist-shop.com.br", "none", False, False, "fail", "quarantine", "quarantine", "quarantine"),
    "09-news-pct.eml": ("news.olist-shop.com.br", "esp-mail.example", "pass", False, False, "fail", "quarantine", "quarantine", "deliver"),
    "10-pay-strict.eml": ("pay.olist-shop.com.br", "bounces.olist-shop.com.br", "pass", False, False, "fail", "reject", "reject", "reject"),
    "11-news-relaxed-dkim.eml": ("news.olist-shop.com.br", "esp-mail.example", "pass", False, True, "pass", "quarantine", "deliver", "deliver"),
    "12-toomany-permerror.eml": ("toomany.example", "toomany.example", "permerror", False, True, "pass", "reject", "deliver", "deliver"),
    "13-no-dmarc-seller.eml": ("small-seller.com.br", "small-seller.com.br", "pass", True, False, "none", None, "deliver", "deliver"),
}


@pytest.fixture(scope="module")
def auth():
    return ex.module("email_auth.py")


@pytest.fixture(scope="module")
def suffixes(auth):
    return auth.load_suffixes(FIXTURES / "public_suffixes.txt")


@pytest.fixture(scope="module")
def records(auth):
    return auth.load_records(FIXTURES / "zones")


def txt(*pairs: tuple[str, str], extra: dict | None = None) -> dict:
    records: dict = {}
    for name, value in pairs:
        records.setdefault((name, "TXT"), []).append(value)
    records.update(extra or {})
    return records


@pytest.mark.parametrize(
    "domain,org",
    [
        ("olist-shop.com.br", "olist-shop.com.br"),
        ("news.olist-shop.com.br", "olist-shop.com.br"),
        ("a.b.olist-shop.com.br", "olist-shop.com.br"),
        ("News.Olist-Shop.COM.BR.", "olist-shop.com.br"),
        ("mail.cheap-deals.example", "cheap-deals.example"),
        ("shop.example.co.uk", "example.co.uk"),
        ("com.br", "com.br"),
        ("deep.mail.unlisted-tld", "mail.unlisted-tld"),
    ],
)
def test_org_domain(auth, suffixes, domain, org):
    assert auth.org_domain(domain, suffixes) == org


@pytest.mark.parametrize(
    "a,b,mode,expected",
    [
        ("bounces.olist-shop.com.br", "olist-shop.com.br", "r", True),
        ("bounces.olist-shop.com.br", "olist-shop.com.br", "s", False),
        ("OLIST-SHOP.com.br", "olist-shop.com.br", "s", True),
        ("evil-shop.com.br", "olist-shop.com.br", "r", False),
        ("olist-shop-br.com", "olist-shop.com.br", "r", False),
    ],
)
def test_aligned(auth, suffixes, a, b, mode, expected):
    assert auth.aligned(a, b, mode, suffixes) is expected


SPF_CASES = {
    "cidr-inside": ("203.0.113.15", "s.example", txt(("s.example", "v=spf1 ip4:203.0.113.0/28 -all")), "pass"),
    "cidr-outside": ("203.0.113.16", "s.example", txt(("s.example", "v=spf1 ip4:203.0.113.0/28 -all")), "fail"),
    "ip4-no-prefix": ("203.0.113.9", "s.example", txt(("s.example", "v=spf1 ip4:203.0.113.9 -all")), "pass"),
    "softfail": ("192.0.2.1", "s.example", txt(("s.example", "v=spf1 ip4:203.0.113.9 ~all")), "softfail"),
    "neutral-all": ("192.0.2.1", "s.example", txt(("s.example", "v=spf1 ip4:203.0.113.9 ?all")), "neutral"),
    "no-all": ("192.0.2.1", "s.example", txt(("s.example", "v=spf1 ip4:203.0.113.9")), "neutral"),
    "qualified-ip": ("192.0.2.1", "s.example", txt(("s.example", "v=spf1 -ip4:192.0.2.0/24 +all")), "fail"),
    "no-record": ("192.0.2.1", "s.example", txt(("s.example", "google-site-verification=abc")), "none"),
    "spf10-is-not-spf": ("192.0.2.1", "s.example", txt(("s.example", "v=spf10 +all")), "none"),
    "two-records": ("192.0.2.1", "s.example", txt(("s.example", "v=spf1 -all"), ("s.example", "v=spf1 +all")), "permerror"),
    "include-softfail-is-no-match": (
        "192.0.2.1",
        "s.example",
        txt(("s.example", "v=spf1 include:esp.example -all"), ("esp.example", "v=spf1 ip4:198.51.100.0/24 ~all")),
        "fail",
    ),
    "include-pass": (
        "198.51.100.7",
        "s.example",
        txt(("s.example", "v=spf1 include:esp.example -all"), ("esp.example", "v=spf1 ip4:198.51.100.0/24 ~all")),
        "pass",
    ),
    "include-fail-then-match": (
        "203.0.113.9",
        "s.example",
        txt(("s.example", "v=spf1 include:esp.example ip4:203.0.113.9 -all"), ("esp.example", "v=spf1 -all")),
        "pass",
    ),
    "include-missing": ("192.0.2.1", "s.example", txt(("s.example", "v=spf1 include:gone.example -all")), "permerror"),
    "redirect": ("198.51.100.7", "s.example", txt(("s.example", "v=spf1 redirect=esp.example"), ("esp.example", "v=spf1 ip4:198.51.100.0/24 -all")), "pass"),
    "redirect-fail": ("192.0.2.1", "s.example", txt(("s.example", "v=spf1 redirect=esp.example"), ("esp.example", "v=spf1 ip4:198.51.100.0/24 -all")), "fail"),
    "redirect-ignored-with-all": ("198.51.100.7", "s.example", txt(("s.example", "v=spf1 ~all redirect=esp.example"), ("esp.example", "v=spf1 +all")), "softfail"),
    "redirect-missing": ("192.0.2.1", "s.example", txt(("s.example", "v=spf1 redirect=gone.example")), "permerror"),
    "a-mechanism": ("203.0.113.200", "s.example", txt(("s.example", "v=spf1 a -all"), extra={("s.example", "A"): ["203.0.113.200"]}), "pass"),
    "a-prefix": ("203.0.113.7", "s.example", txt(("s.example", "v=spf1 a/24 -all"), extra={("s.example", "A"): ["203.0.113.200"]}), "pass"),
    "a-other-domain": ("192.0.2.5", "s.example", txt(("s.example", "v=spf1 a:relay.example -all"), extra={("relay.example", "A"): ["192.0.2.5"]}), "pass"),
    "mx-mechanism": (
        "203.0.113.25",
        "s.example",
        txt(("s.example", "v=spf1 mx -all"), extra={("s.example", "MX"): ["10 mx1.s.example."], ("mx1.s.example", "A"): ["203.0.113.25"]}),
        "pass",
    ),
    "ip6": ("2001:db8:25::7", "s.example", txt(("s.example", "v=spf1 ip6:2001:db8:25::/48 -all")), "pass"),
    "ip6-vs-ipv4-client": ("192.0.2.1", "s.example", txt(("s.example", "v=spf1 ip6:2001:db8:25::/48 -all")), "fail"),
    "unknown-mechanism": ("192.0.2.1", "s.example", txt(("s.example", "v=spf1 foo:bar.example -all")), "permerror"),
    "exp-modifier-ignored": ("192.0.2.1", "s.example", txt(("s.example", "v=spf1 exp=why.example -all")), "fail"),
}


def chain(count: int) -> dict:
    includes = " ".join(f"include:i{n}.example" for n in range(count))
    records = txt(("s.example", f"v=spf1 {includes} ip4:192.0.2.1 -all"))
    for n in range(count):
        records[(f"i{n}.example", "TXT")] = [f"v=spf1 ip4:198.51.100.{n} -all"]
    return records


@pytest.mark.parametrize("case", sorted(SPF_CASES))
def test_spf_check(auth, case):
    ip, domain, records, expected = SPF_CASES[case]
    assert auth.spf_check(ip, domain, records) == expected


def test_spf_lookup_limit_ten_is_ok_eleven_is_permerror(auth):
    assert auth.spf_check("192.0.2.1", "s.example", chain(10)) == "pass"
    assert auth.spf_check("192.0.2.1", "s.example", chain(11)) == "permerror"


def test_spf_limit_counts_only_evaluated_terms(auth, records):
    assert auth.spf_check("192.0.2.21", "toomany.example", records) == "pass"
    assert auth.spf_check("192.0.2.12", "toomany.example", records) == "permerror"


def test_load_records_reads_zone_files(auth, records):
    assert "v=spf1 ip4:198.51.100.0/24 ip4:192.0.2.128/25 ~all" in records[("_spf.esp-mail.example", "TXT")]
    assert records[("mx1.olist-shop.com.br", "A")] == ["203.0.113.25"]


@pytest.mark.parametrize("name", sorted(EXPECTED))
def test_message_verdict(auth, records, suffixes, name):
    raw = (FIXTURES / "messages" / name).read_text(encoding="utf-8")
    result = auth.evaluate(raw, records, suffixes)
    expected = dict(zip(KEYS, EXPECTED[name]))
    wrong = {k: (result.get(k), v) for k, v in expected.items() if result.get(k) != v}
    assert not wrong, f"{name}: khoá sai (của bạn, đúng): {wrong}"


def load_naive():
    spec = importlib.util.spec_from_file_location("naive_email_auth_m04", FIXTURES / "naive_email_auth.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_cases_catch_naive_shortcuts(records, suffixes):
    """Bản ngây thơ lấy hai nhãn cuối làm organizational domain và tin mọi Authentication-Results: test phải bắt được."""
    naive = load_naive()
    assert naive.aligned("evil-shop.com.br", "olist-shop.com.br", "r", suffixes) is True
    raw = (FIXTURES / "messages" / "06-forged-auth-results.eml").read_text(encoding="utf-8")
    assert naive.evaluate(raw, records, suffixes)["dmarc"] == "pass"
    assert EXPECTED["06-forged-auth-results.eml"][KEYS.index("dmarc")] == "fail"

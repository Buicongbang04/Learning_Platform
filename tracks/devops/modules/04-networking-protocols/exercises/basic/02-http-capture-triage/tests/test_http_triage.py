import pytest

from testkit import Exercise

ex = Exercise(__file__)

KEYS = ("method", "version", "status", "retry_safe", "retry_after", "cache", "ttl", "keep_alive")
EXPECTED = {
    "static_asset_h2.txt": ("GET", "HTTP/2", 200, False, None, "fresh", 31534800, True),
    "api_orders_private.txt": ("GET", "HTTP/1.1", 200, False, None, "private", None, True),
    "api_auth_no_cc_public.txt": ("GET", "HTTP/1.1", 200, False, None, "private", None, True),
    "catalog_s_maxage.txt": ("GET", "HTTP/2", 200, False, None, "fresh", 500, True),
    "legacy_expires_http10.txt": ("GET", "HTTP/1.0", 200, False, None, "fresh", 300, False),
    "checkout_503_no_store.txt": ("POST", "HTTP/1.1", 503, False, 120, "no-store", None, False),
    "payment_429_http_date.txt": ("POST", "HTTP/1.1", 429, True, 30, "none", None, True),
    "order_502_gateway.txt": ("GET", "HTTP/1.1", 502, True, None, "none", None, True),
    "index_no_cache_etag.txt": ("GET", "HTTP/2", 200, False, None, "revalidate", None, True),
    "banner_stale_age.txt": ("HEAD", "HTTP/1.1", 200, False, None, "stale", 0, True),
}


def analyze(text: str) -> dict:
    return ex.module("http_triage.py").analyze(text)


def fixture(name: str) -> str:
    return (ex.fixtures / name).read_text(encoding="utf-8")


@pytest.mark.parametrize("name", sorted(EXPECTED))
def test_capture(name):
    result = analyze(fixture(name))
    expected = dict(zip(KEYS, EXPECTED[name]))
    wrong = {k: (result.get(k), v) for k, v in expected.items() if result.get(k) != v}
    assert not wrong, f"{name}: khoá sai (của bạn, đúng): {wrong}"


def test_authorization_makes_response_private_unless_public():
    text = fixture("api_auth_no_cc_public.txt").replace("Cache-Control: max-age=300", "Cache-Control: public, max-age=300")
    result = analyze(text)
    assert (result["cache"], result["ttl"]) == ("fresh", 300)


def test_s_maxage_wins_over_max_age_and_expires():
    text = fixture("catalog_s_maxage.txt").replace("< age: 100\n", "< expires: Sun, 01 Nov 2026 09:01:50 GMT\n")
    assert analyze(text)["ttl"] == 600


def test_post_without_idempotency_key_is_not_retry_safe():
    text = fixture("payment_429_http_date.txt").replace("> Idempotency-Key: 6f1d2c9e-order-81d3-payment\n", "")
    assert analyze(text)["retry_safe"] is False


def test_500_is_not_retry_safe():
    text = fixture("order_502_gateway.txt").replace("502 Bad Gateway", "500 Internal Server Error")
    assert analyze(text)["retry_safe"] is False


def test_http10_keep_alive_must_be_explicit():
    text = fixture("legacy_expires_http10.txt").replace("< Content-Length: 50211\n", "< Content-Length: 50211\n< Connection: keep-alive\n")
    assert analyze(text)["keep_alive"] is True


def test_retry_after_date_in_past_is_zero():
    text = fixture("payment_429_http_date.txt").replace("09:10:30 GMT", "09:09:00 GMT")
    assert analyze(text)["retry_after"] == 0

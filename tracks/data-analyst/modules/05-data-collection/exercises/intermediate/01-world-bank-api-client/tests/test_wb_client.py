"""Test với World Bank API giả (httpx.MockTransport): không gọi mạng. Cấu trúc response giống API thật
(https://api.worldbank.org/v2): JSON là mảng [metadata, danh sách bản ghi]."""
import math

import httpx
import numpy as np
import pandas as pd
import pytest

from testkit import Exercise

ex = Exercise(__file__)
BASE = "https://api.worldbank.org/v2"


@pytest.fixture(scope="module")
def nb():
    return ex.notebook("wb_client.ipynb")


def rec(iso3, country, year, value, indicator="NY.GDP.PCAP.CD"):
    return {"indicator": {"id": indicator, "value": indicator}, "country": {"id": iso3[:2], "value": country},
            "countryiso3code": iso3, "date": str(year), "value": value, "unit": "", "obs_status": "", "decimal": 1}


def client_for(handler):
    return httpx.Client(base_url=BASE, transport=httpx.MockTransport(handler))


def paged_server(records, calls, total=None):
    def handler(request):
        calls.append(request)
        per_page = int(request.url.params["per_page"])
        page = int(request.url.params["page"])
        pages = math.ceil(len(records) / per_page)
        meta = {"page": page, "pages": pages, "per_page": per_page,
                "total": len(records) if total is None else total, "sourceid": "2", "lastupdated": "2026-10-08"}
        return httpx.Response(200, json=[meta, records[(page - 1) * per_page: page * per_page]])
    return handler


def sequence_server(responses, calls):
    """Trả lần lượt từng phần tử của responses (Response hoặc Exception)."""
    def handler(request):
        calls.append(request)
        item = responses[len(calls) - 1]
        if isinstance(item, Exception):
            raise item
        return item
    return handler


OK = httpx.Response(200, json=[{"page": 1, "pages": 1, "per_page": 50, "total": 0}, []])


def test_get_json_returns_body(nb):
    calls = []
    client = client_for(sequence_server([OK], calls))
    body = nb.get_json(client, "/country/VNM/indicator/X", {"format": "json"}, sleep=lambda s: None)
    assert body[0]["pages"] == 1
    assert calls[0].url.path == "/v2/country/VNM/indicator/X"
    assert calls[0].url.params["format"] == "json"


def test_get_json_retries_5xx_and_429_with_retry_after(nb):
    calls, sleeps = [], []
    responses = [httpx.Response(503), httpx.Response(429, headers={"Retry-After": "7"}), OK]
    body = nb.get_json(client_for(sequence_server(responses, calls)), "/x", {}, sleep=sleeps.append)
    assert len(calls) == 3
    assert sleeps == [1, 7]
    assert body[0]["total"] == 0


def test_get_json_retries_network_error(nb):
    calls, sleeps = [], []
    responses = [httpx.ConnectError("mất mạng"), OK]
    nb.get_json(client_for(sequence_server(responses, calls)), "/x", {}, sleep=sleeps.append)
    assert len(calls) == 2
    assert sleeps == [1]


def test_get_json_gives_up(nb):
    calls, sleeps = [], []
    responses = [httpx.Response(503)] * 3
    with pytest.raises(nb.ApiError):
        nb.get_json(client_for(sequence_server(responses, calls)), "/x", {}, max_retries=2, sleep=sleeps.append)
    assert len(calls) == 3
    assert sleeps == [1, 2]


def test_get_json_does_not_retry_client_error(nb):
    calls, sleeps = [], []
    with pytest.raises(nb.ApiError):
        nb.get_json(client_for(sequence_server([httpx.Response(400, text="bad")], calls)), "/x", {},
                    sleep=sleeps.append)
    assert len(calls) == 1 and sleeps == []


def test_get_json_error_inside_http_200(nb):
    calls, sleeps = [], []
    body = [{"message": [{"id": "120", "key": "Invalid value", "value": "The provided parameter value is not valid"}]}]
    with pytest.raises(nb.ApiError, match="Invalid value"):
        nb.get_json(client_for(sequence_server([httpx.Response(200, json=body)], calls)), "/x", {},
                    sleep=sleeps.append)
    assert len(calls) == 1 and sleeps == []


SEVEN = [rec("VNM", "Viet Nam", y, 2000.0 + y) for y in range(2017, 2024)]


def test_fetch_indicator_follows_pages(nb):
    calls = []
    client = client_for(paged_server(SEVEN, calls))
    out = nb.fetch_indicator(client, "NY.GDP.PCAP.CD", ["VNM", "THA"], 2015, 2023, per_page=3,
                             sleep=lambda s: None)
    assert out == SEVEN
    assert [c.url.params["page"] for c in calls] == ["1", "2", "3"]
    first = calls[0]
    assert first.url.path == "/v2/country/VNM;THA/indicator/NY.GDP.PCAP.CD"
    assert first.url.params["format"] == "json"
    assert first.url.params["date"] == "2015:2023"
    assert first.url.params["per_page"] == "3"


def test_fetch_indicator_no_data(nb):
    calls = []
    empty = httpx.Response(200, json=[{"page": 0, "pages": 0, "per_page": 50, "total": 0}, None])
    out = nb.fetch_indicator(client_for(sequence_server([empty], calls)), "X", ["VNM"], 2015, 2023,
                             sleep=lambda s: None)
    assert out == [] and len(calls) == 1


def test_fetch_indicator_checks_total(nb):
    calls = []
    client = client_for(paged_server(SEVEN, calls, total=8))
    with pytest.raises(nb.ApiError):
        nb.fetch_indicator(client, "X", ["VNM"], 2015, 2023, per_page=5, sleep=lambda s: None)


def test_to_tidy(nb):
    records = [rec("THA", "Thailand", 2023, 7210.5), rec("VNM", "Viet Nam", 2023, None),
               rec("VNM", "Viet Nam", 2022, 4100.0), rec("", "East Asia & Pacific", 2023, 13000.0)]
    out = nb.to_tidy(records)
    assert list(out.columns) == ["iso3", "country", "indicator", "year", "value"]
    assert out["iso3"].tolist() == ["THA", "VNM", "VNM"]
    assert out["year"].tolist() == [2023, 2022, 2023]
    assert pd.api.types.is_integer_dtype(out["year"]) and pd.api.types.is_float_dtype(out["value"])
    assert out["value"].iloc[0] == 7210.5 and np.isnan(out["value"].iloc[2])
    assert list(out.index) == [0, 1, 2]


def test_online_population(nb):
    tidy = pd.DataFrame([
        ("VNM", "Viet Nam", "SP.POP.TOTL", 2023, 100e6), ("VNM", "Viet Nam", "IT.NET.USER.ZS", 2023, 78.0),
        ("VNM", "Viet Nam", "NY.GDP.PCAP.CD", 2023, 4300.0),
        ("MMR", "Myanmar", "SP.POP.TOTL", 2023, 54e6), ("MMR", "Myanmar", "IT.NET.USER.ZS", 2023, np.nan),
        ("MMR", "Myanmar", "NY.GDP.PCAP.CD", 2023, 1200.0),
        ("IDN", "Indonesia", "SP.POP.TOTL", 2023, 280e6), ("IDN", "Indonesia", "IT.NET.USER.ZS", 2023, 70.0),
        ("IDN", "Indonesia", "NY.GDP.PCAP.CD", 2023, 4900.0),
        ("IDN", "Indonesia", "SP.POP.TOTL", 2022, 1.0),
    ], columns=["iso3", "country", "indicator", "year", "value"])
    before = tidy.copy()
    out = nb.online_population(tidy, 2023)
    pd.testing.assert_frame_equal(tidy, before)
    assert list(out.columns) == ["country", "population", "internet_pct", "gdp_per_capita", "online_population"]
    assert list(out.index) == ["IDN", "VNM", "MMR"]
    assert out.index.name == "iso3"
    assert out.loc["IDN", "online_population"] == pytest.approx(196e6)
    assert out.loc["VNM", "online_population"] == pytest.approx(78e6)
    assert np.isnan(out.loc["MMR", "online_population"])


def test_redact(nb):
    url = "https://api.example.com/v1/weather?city=hanoi&api_key=SECRET123&token=abc&page=2"
    assert nb.redact(url) == "https://api.example.com/v1/weather?city=hanoi&api_key=***&token=***&page=2"
    clean = "https://api.worldbank.org/v2/country/VNM/indicator/SP.POP.TOTL?format=json&page=1"
    assert nb.redact(clean) == clean

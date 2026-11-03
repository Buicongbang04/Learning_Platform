import uuid

import pytest
from fastapi.testclient import TestClient
from prometheus_client.parser import text_string_to_metric_families

from testkit import Exercise

ex = Exercise(__file__)
ALLOWED_LABELS = {"method", "route", "status", "le", "version"}
LATENCY_LE = {"0.005", "0.01", "0.025", "0.05", "0.1", "0.25", "0.5", "1.0", "2.5", "+Inf"}
PREDICTION_LE = {"60.0", "120.0", "300.0", "600.0", "900.0", "1200.0", "1800.0", "3600.0", "+Inf"}


@pytest.fixture(scope="module")
def mod():
    return ex.module("app.py")


class Broken:
    version = "9"

    def predict(self, km):
        raise RuntimeError("model crashed")


def flaky(mod):
    class Flaky:
        version = "4"

        def predict(self, km):
            raise mod.ModelError("model unavailable")

    return Flaky()


def client_for(mod, model=None):
    return TestClient(mod.create_app(model), raise_server_exceptions=False)


def scrape(client):
    response = client.get("/metrics")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/plain")
    samples = {}
    for family in text_string_to_metric_families(response.text):
        for sample in family.samples:
            samples[(sample.name, tuple(sorted(sample.labels.items())))] = sample.value
    return samples, response.text


def value(samples, name, **labels):
    return samples.get((name, tuple(sorted(labels.items()))))


def test_counter_by_route_and_status(mod):
    client = client_for(mod)
    for _ in range(3):
        assert client.post("/predict", json={"trip_distance_km": 5}).status_code == 200
    assert client.post("/predict", json={"trip_distance_km": -1}).status_code == 422
    samples, _ = scrape(client)
    assert value(samples, "http_requests_total", method="POST", route="/predict", status="200") == 3
    assert value(samples, "http_requests_total", method="POST", route="/predict", status="422") == 1


def test_server_error_is_counted_as_500(mod):
    client = client_for(mod, Broken())
    assert client.post("/predict", json={"trip_distance_km": 5}).status_code == 500
    samples, _ = scrape(client)
    assert value(samples, "http_requests_total", method="POST", route="/predict", status="500") == 1


def test_latency_histogram_has_agreed_buckets(mod):
    client = client_for(mod)
    for _ in range(4):
        client.post("/predict", json={"trip_distance_km": 2})
    samples, _ = scrape(client)
    les = {dict(labels)["le"] for (name, labels) in samples
           if name == "http_request_duration_seconds_bucket" and dict(labels).get("route") == "/predict"}
    assert les == LATENCY_LE
    assert value(samples, "http_request_duration_seconds_count", method="POST", route="/predict") == 4
    assert value(samples, "http_request_duration_seconds_sum", method="POST", route="/predict") > 0


def test_model_info_metric(mod):
    client = client_for(mod)
    samples, _ = scrape(client)
    assert value(samples, "eta_model_info", version="3") == 1.0
    other, _ = scrape(client_for(mod, Broken()))
    assert value(other, "eta_model_info", version="9") == 1.0


def test_prediction_distribution_and_fallback_ratio(mod):
    client = client_for(mod, flaky(mod))
    for km in (1, 2, 3):
        body = client.post("/predict", json={"trip_distance_km": km}).json()
        assert body["fallback"] is True
        assert body["eta_seconds"] == 240.0 + 150.0 * km
    samples, _ = scrape(client)
    assert value(samples, "eta_fallback_total") == 3
    assert value(samples, "eta_prediction_seconds_count") == 3
    les = {dict(labels)["le"] for (name, labels) in samples if name == "eta_prediction_seconds_bucket"}
    assert les == PREDICTION_LE
    healthy, _ = scrape_after(mod, 2)
    assert value(healthy, "eta_fallback_total") == 0
    assert value(healthy, "eta_prediction_seconds_count") == 2


def scrape_after(mod, calls):
    client = client_for(mod)
    for _ in range(calls):
        client.post("/predict", json={"trip_distance_km": 4})
    return scrape(client)


def test_labels_stay_low_cardinality(mod):
    client = client_for(mod)
    ids = [uuid.uuid4().hex for _ in range(40)]
    for request_id in ids:
        client.post("/predict", json={"trip_distance_km": 3}, headers={"X-Request-ID": request_id})
        client.get(f"/does-not-exist/{request_id}")
    samples, text = scrape(client)
    for request_id in ids:
        assert request_id not in text
    names = {key for (_, labels) in samples for key, _ in labels}
    assert names <= ALLOWED_LABELS, names - ALLOWED_LABELS
    routes = {dict(labels)["route"] for (_, labels) in samples if "route" in dict(labels)}
    assert routes <= {"/predict", "/health", "unmatched"}
    assert value(samples, "http_requests_total", method="GET", route="unmatched", status="404") == 40
    series = [key for key in samples if key[0] == "http_requests_total"]
    assert len(series) <= 6


def test_metrics_endpoint_is_not_measured(mod):
    client = client_for(mod)
    for _ in range(3):
        client.get("/metrics")
    client.get("/health")
    samples, _ = scrape(client)
    assert not [key for key in samples if dict(key[1]).get("route") == "/metrics"]
    assert value(samples, "http_requests_total", method="GET", route="/health", status="200") == 1


def test_apps_do_not_share_a_registry(mod):
    first, second = client_for(mod), client_for(mod)
    first.post("/predict", json={"trip_distance_km": 1})
    samples, _ = scrape(second)
    assert value(samples, "http_requests_total", method="POST", route="/predict", status="200") is None

from prometheus_client.parser import text_string_to_metric_families

from quillo_support import AUTH, upload

TEXT = "This agreement is governed by the law of the State of New York. " * 3


def samples(client) -> dict[tuple, float]:
    response = client.get("/metrics")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/plain")
    found = {}
    for family in text_string_to_metric_families(response.text):
        for sample in family.samples:
            found[(sample.name, tuple(sorted(sample.labels.items())))] = sample.value
    return found


def test_metrics_exposed(client):
    upload(client, "nda.txt", TEXT)
    upload(client, "b.txt", TEXT + " Second.")
    assert client.post("/api/ask", headers=AUTH, json={"question": "Which law?"}).status_code == 200
    assert client.post("/api/ask", json={"question": "Which law?"}).status_code == 401
    client.get("/no/such/page/123")
    found = samples(client)
    assert found[("quillo_requests_total", (("route", "/api/ask"), ("status", "200")))] == 1
    assert found[("quillo_requests_total", (("route", "/api/ask"), ("status", "401")))] == 1
    assert found[("quillo_requests_total", (("route", "/api/documents"), ("status", "201")))] == 2
    assert found[("quillo_requests_total", (("route", "unmatched"), ("status", "404")))] == 1
    assert not any("/no/such" in str(labels) for _, labels in found)
    assert found[("quillo_ask_seconds_count", ())] == 1
    assert found[("quillo_ask_seconds_bucket", (("le", "+Inf"),))] == 1
    assert found[("quillo_documents", ())] == 2
    assert found[("quillo_chunks", ())] == 2
    assert found[("quillo_model_up", (("kind", "llm"),))] == 1
    assert found[("quillo_model_up", (("kind", "embed"),))] == 1


def test_metrics_need_no_auth_and_report_model_down(database_url, fake_llm):
    import testkit
    from fastapi.testclient import TestClient

    from quillo.app import create_app
    from quillo_support import make_settings

    dead = f"http://127.0.0.1:{testkit.free_port()}"
    with TestClient(create_app(make_settings(database_url, dead, embed_url=fake_llm.url))) as client:
        found = samples(client)
    assert found[("quillo_model_up", (("kind", "llm"),))] == 0
    assert found[("quillo_model_up", (("kind", "embed"),))] == 1
    assert found[("quillo_documents", ())] == 0

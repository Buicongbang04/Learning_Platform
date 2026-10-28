import hashlib
import hmac
import json
from datetime import datetime

import pandas as pd
import pytest

from testkit import Exercise

ex = Exercise(__file__)
KEY = b"pipeline-key"


@pytest.fixture(scope="module")
def pl():
    return ex.module("pipeline.py")


def customers():
    return pd.DataFrame({
        "customer_id": ["c1", "c2", "c3", "c4"],
        "customer_unique_id": ["U1", "U1", "U2", "U3"],
        "email": ["ana@gmail.com", "ana@gmail.com", "joao@uol.com.br", "lia@gmail.com"],
        "cpf": ["529.982.247-25", "529.982.247-25", "123.456.789-09", "987.654.321-00"],
        "customer_state": ["SP", "SP", "RJ", "MG"],
    })


def orders(n_bad=1):
    rows = [(f"o{i}", f"c{(i % 4) + 1}", "delivered", 10.0 + i) for i in range(1, 21)]
    bad = [("o1", "c1", "delivered", 5.0), (None, "c2", "shipped", 1.0), ("ox", "c3", "lost", 1.0),
           ("oy", "c4", "shipped", -3.0)]
    rows += bad[:n_bad]
    return pd.DataFrame(rows, columns=["order_id", "customer_id", "order_status", "price"])


def collect():
    events = []
    return events, events.append


def test_happy_path(pl):
    events, emit = collect()
    out, quarantine = pl.run(orders(n_bad=1), customers(), KEY, emit)
    assert list(out.columns) == pl.OUTPUT_COLUMNS
    # o1 trùng nên cả 2 dòng o1 bị quarantine
    assert len(quarantine) == 2 and len(out) == 19
    assert "o1" not in set(out["order_id"])
    expected_key = hmac.new(KEY, b"U1", hashlib.sha256).hexdigest()
    assert expected_key in set(out["customer_key"])
    for col in ["email", "cpf", "customer_unique_id", "customer_id"]:
        assert col not in out.columns

    assert [e["eventType"] for e in events] == ["START", "COMPLETE"]
    assert len({e["run"]["runId"] for e in events}) == 1
    for e in events:
        json.dumps(e)
        assert datetime.fromisoformat(e["eventTime"]).tzinfo is not None
        assert e["job"] == {"namespace": "olist", "name": "build_orders_enriched"}
        assert [i["name"] for i in e["inputs"]] == ["raw.orders", "raw.customers"]
    done = events[-1]
    output = done["outputs"][0]
    assert output["name"] == "mart.orders_enriched"
    assert [f["name"] for f in output["facets"]["schema"]["fields"]] == pl.OUTPUT_COLUMNS
    assert output["facets"]["dataQualityMetrics"] == {"rowCount": 19, "invalidRowCount": 2}


def test_run_id_passthrough(pl):
    events, emit = collect()
    pl.run(orders(n_bad=0), customers(), KEY, emit, run_id="11111111-2222-3333-4444-555555555555")
    assert {e["run"]["runId"] for e in events} == {"11111111-2222-3333-4444-555555555555"}


def test_quality_gate_fails(pl):
    events, emit = collect()
    with pytest.raises(pl.QualityGateError):
        pl.run(orders(n_bad=4), customers(), KEY, emit, max_invalid_ratio=0.1)
    assert [e["eventType"] for e in events] == ["START", "FAIL"]
    assert events[-1]["run"]["facets"]["errorMessage"]["message"]


def test_unexpected_error_emits_fail(pl):
    events, emit = collect()
    with pytest.raises(Exception):
        pl.run(orders(n_bad=0), customers().drop(columns=["customer_state"]), KEY, emit)
    assert [e["eventType"] for e in events] == ["START", "FAIL"]


def test_no_pii_in_events(pl):
    events, emit = collect()
    pl.run(orders(n_bad=2), customers(), KEY, emit, max_invalid_ratio=0.5)
    dump = json.dumps(events)
    for raw in ["ana@gmail.com", "529.982.247-25", "joao@uol.com.br", "\"U1\""]:
        assert raw not in dump

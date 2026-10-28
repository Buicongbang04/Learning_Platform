from datetime import datetime

import pytest

from testkit import Exercise

ex = Exercise(__file__)

ANALYST = {"id": "bruno", "clearance": "low", "pii_access": False, "region": "BR"}
SUPPORT = {"id": "carla", "clearance": "medium", "pii_access": True, "region": "BR"}
SUPPORT_EU = {"id": "eva", "clearance": "medium", "pii_access": True, "region": "EU"}
FRAUD = {"id": "diego", "clearance": "high", "pii_access": True, "region": "BR"}

LINEAGE = {
    "reporting.customers_by_state": {
        "customer_state": {"sources": [("mart.dim_customers", "customer_state")], "transform": "identity"},
        "n_customers": {"sources": [("mart.dim_customers", "customer_key")], "transform": "aggregate"},
        "leaked_email": {"sources": [("mart.dim_customers", "email_copy")], "transform": "identity"},
    },
    "mart.dim_customers": {
        "customer_key": {"sources": [("customers", "customer_unique_id")], "transform": "hmac"},
        "customer_state": {"sources": [("customers", "customer_state")], "transform": "identity"},
        "zip3": {"sources": [("customers", "customer_zip_code_prefix")], "transform": "generalize"},
        "email_copy": {"sources": [("customers", "email")], "transform": "identity"},
        "contact": {"sources": [("customers", "email"), ("customers", "cpf")], "transform": "identity"},
    },
}


@pytest.fixture(scope="module")
def abac():
    return ex.module("abac.py")


@pytest.fixture()
def engine(abac):
    return abac.PolicyEngine(abac.CATALOG, abac.TABLE_META)


@pytest.mark.parametrize("user,table,column,purpose,effect,rule", [
    (ANALYST, "customers", "email", "analytics", "mask", "pii"),
    (SUPPORT, "customers", "email", "support", "allow", "pii"),
    (SUPPORT_EU, "customers", "email", "support", "mask", "pii"),
    (SUPPORT, "customers", "email", "marketing", "mask", "pii"),
    (SUPPORT, "customers", "cpf", "support", "deny", "restricted"),
    (FRAUD, "customers", "cpf", "fraud", "allow", "restricted"),
    (FRAUD, "customers", "cpf", "analytics", "deny", "restricted"),
    (ANALYST, "customers", "customer_state", "analytics", "allow", "default"),
    (ANALYST, "customers", "customer_zip_code_prefix", "marketing", "mask", "quasi_identifier"),
    (ANALYST, "customers", "customer_zip_code_prefix", "analytics", "allow", "default"),
    (ANALYST, "customers", "email", "training", "deny", "invalid_purpose"),
    (ANALYST, "customers", "password", "analytics", "deny", "unknown_resource"),
    (ANALYST, "payments", "value", "analytics", "deny", "unknown_resource"),
])
def test_evaluate(engine, user, table, column, purpose, effect, rule):
    d = engine.evaluate(user, table, column, purpose)
    assert (d.effect, d.rule) == (effect, rule)
    assert d.reason


def test_audit(engine):
    engine.evaluate(ANALYST, "customers", "email", "analytics")
    engine.evaluate(ANALYST, "customers", "customer_state", "analytics")
    assert len(engine.audit) == 2
    entry = engine.audit[0]
    assert {k: entry[k] for k in ["user", "table", "column", "purpose", "effect", "rule"]} == {
        "user": "bruno", "table": "customers", "column": "email", "purpose": "analytics",
        "effect": "mask", "rule": "pii"}
    datetime.fromisoformat(entry["at"])
    assert engine.audit[1]["effect"] == "allow"


def test_authorize_query(engine):
    res = engine.authorize_query(ANALYST, "customers", ["customer_state", "email"], "analytics")
    assert {c: d.effect for c, d in res.items()} == {"customer_state": "allow", "email": "mask"}
    with pytest.raises(PermissionError, match="cpf"):
        engine.authorize_query(ANALYST, "customers", ["cpf", "customer_state"], "analytics")
    assert len(engine.audit) == 4


def test_propagate_tags(abac):
    before = {t: {c: set(tags) for c, tags in cols.items()} for t, cols in abac.CATALOG.items()}
    cat = abac.propagate_tags(abac.CATALOG, LINEAGE)
    assert abac.CATALOG == before  # không sửa đầu vào
    dim = cat["mart.dim_customers"]
    assert dim["customer_key"] == {"identifier", "pseudonymized"}
    assert dim["customer_state"] == set()
    assert dim["zip3"] == {"quasi_identifier"}
    assert dim["email_copy"] == {"pii", "pii:email"}
    assert dim["contact"] == {"pii", "pii:email", "pii:national_id", "restricted"}
    rep = cat["reporting.customers_by_state"]
    assert rep == {"customer_state": set(), "n_customers": set(), "leaked_email": {"pii", "pii:email"}}
    assert cat["customers"] == abac.CATALOG["customers"]


def test_policy_on_derived_tables(abac):
    cat = abac.propagate_tags(abac.CATALOG, LINEAGE)
    eng = abac.PolicyEngine(cat, abac.TABLE_META)
    assert eng.evaluate(ANALYST, "reporting.customers_by_state", "leaked_email", "analytics").effect == "mask"
    # bảng dẫn xuất chưa khai báo region -> PII luôn bị mask (fail closed)
    assert eng.evaluate(SUPPORT, "reporting.customers_by_state", "leaked_email", "support").effect == "mask"
    assert eng.evaluate(ANALYST, "mart.dim_customers", "customer_key", "analytics").effect == "allow"
    d = eng.evaluate(ANALYST, "mart.dim_customers", "customer_key", "marketing")
    assert (d.effect, d.rule) == ("mask", "pseudonymized")
    assert eng.evaluate(FRAUD, "mart.dim_customers", "contact", "support").effect == "deny"


def test_propagate_errors(abac):
    with pytest.raises(ValueError):
        abac.propagate_tags(abac.CATALOG, {"t": {"c": {"sources": [("customers", "email")], "transform": "rot13"}}})
    with pytest.raises(ValueError):
        abac.propagate_tags(abac.CATALOG, {"t": {"c": {"sources": [("customers", "nope")], "transform": "identity"}}})
    with pytest.raises(ValueError):
        abac.propagate_tags(abac.CATALOG, {
            "a": {"x": {"sources": [("b", "y")], "transform": "identity"}},
            "b": {"y": {"sources": [("a", "x")], "transform": "identity"}},
        })

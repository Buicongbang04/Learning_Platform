import os

os.environ.setdefault("MLFLOW_DISABLE_AGENT_HINT", "1")

import pytest
from mlflow import MlflowClient

import mlopskit
from testkit import Exercise

ex = Exercise(__file__)
CARD = (
    "# pricing-tip-amount\n\n## Intended use\n\nGợi ý tiền tip.\n\n## Training data\n\nNYC TLC 2019-01.\n\n"
    "## Metrics\n\nMAE 1.12 USD.\n\n## Limitations\n\nKhông dùng cho chuyến trả tiền mặt.\n"
)
TAGS = {"owner": "lan.nguyen@example.com", "team": "pricing", "cost_center": "CC-2041"}
BASE = {"name": "pricing-tip-amount", "tags": TAGS, "model_card": CARD, "requested_by": {"user": "lan", "team": "pricing"}}


def case(**changes):
    request = {**BASE, "tags": dict(TAGS)}
    for key, value in changes.items():
        if key.startswith("tag_"):
            tag = key[4:]
            if value is None:
                request["tags"].pop(tag, None)
            else:
                request["tags"][tag] = value
        else:
            request[key] = value
    return request


CASES = {
    "compliant": (case(), []),
    "platform-may-register-for-a-team": (case(requested_by={"user": "ops", "team": "platform"}), []),
    "no-requester-skips-permission": (case(requested_by=None), []),
    "name-uppercase": (case(name="Pricing-Tip-Amount"), ["name"]),
    "name-underscore": (case(name="pricing_tip_amount"), ["name"]),
    "name-no-team-prefix": (case(name="tip-amount"), ["name"]),
    "name-unknown-team": (case(name="growth-tip-amount"), ["name"]),
    "name-team-only": (case(name="pricing"), ["name"]),
    "name-too-long": (case(name="pricing-" + "a" * 57), ["name"]),
    "name-64-chars-ok": (case(name="pricing-" + "a" * 56), []),
    "owner-missing": (case(tag_owner=None), ["tag-missing:owner"]),
    "owner-blank": (case(tag_owner="   "), ["tag-missing:owner"]),
    "owner-not-email": (case(tag_owner="lan"), ["tag-invalid:owner"]),
    "cost-center-format": (case(tag_cost_center="2041"), ["tag-invalid:cost_center"]),
    "cost-center-missing": (case(tag_cost_center=None), ["tag-missing:cost_center"]),
    "team-tag-unknown": (case(tag_team="growth"), ["tag-invalid:team"]),
    "team-tag-differs-from-name": (case(tag_team="fraud"), ["team-mismatch"]),
    "other-team-registers": (case(requested_by={"user": "minh", "team": "fraud"}), ["permission"]),
    "card-missing": (case(model_card=None), ["model-card-missing"]),
    "card-blank": (case(model_card="  \n"), ["model-card-missing"]),
    "card-without-limitations": (case(model_card=CARD.split("## Limitations")[0]), ["model-card-section:Limitations"]),
    "card-headings-case-insensitive": (case(model_card=CARD.replace("## Metrics", "## metrics  ")), []),
    "card-h3-does-not-count": (case(model_card=CARD.replace("## Metrics", "### Metrics")), ["model-card-section:Metrics"]),
    "many-problems": (
        case(name="growth-x", tag_owner=None, tag_cost_center="cc-1", model_card="# x\n"),
        ["model-card-section:Intended use", "model-card-section:Limitations", "model-card-section:Metrics",
         "model-card-section:Training data", "name", "tag-invalid:cost_center", "tag-missing:owner"],
    ),
}


@pytest.fixture(scope="module")
def gate():
    return ex.module("registry_gate.py")


@pytest.mark.parametrize("name", list(CASES))
def test_check_request_table(gate, name):
    request, expected = CASES[name]
    got = gate.check_request(request)
    assert got == expected, f"ca {name}: kết quả {got}"


def test_check_request_does_not_mutate_input(gate):
    request = case(tag_owner=" lan.nguyen@example.com ")
    snapshot = {**request, "tags": dict(request["tags"])}
    gate.check_request(request)
    assert request == snapshot


@pytest.fixture
def client(tmp_path):
    return MlflowClient(mlopskit.mlflow_local(tmp_path))


def test_register_compliant_model(gate, client):
    version, violations = gate.register_if_allowed(client, case(), "file:///models/tip-amount")
    assert violations == [] and version == "1"
    stored = client.get_model_version("pricing-tip-amount", "1")
    assert {k: stored.tags.get(k) for k in TAGS} == TAGS
    assert stored.description == CARD
    assert {k: client.get_registered_model("pricing-tip-amount").tags.get(k) for k in TAGS} == TAGS
    second, _ = gate.register_if_allowed(client, case(), "file:///models/tip-amount-v2")
    assert second == "2"


def test_register_rejected_leaves_registry_untouched(gate, client):
    version, violations = gate.register_if_allowed(client, case(requested_by={"user": "minh", "team": "fraud"}), "file:///m")
    assert version is None and violations == ["permission"]
    assert client.search_registered_models() == []


def test_audit_finds_versions_registered_around_the_gate(gate, client):
    gate.register_if_allowed(client, case(), "file:///m1")
    client.create_registered_model("search-ranker")
    client.create_model_version("search-ranker", "file:///m2", tags={"team": "search", "owner": "an@example.com"}, description=CARD)
    client.create_registered_model("legacy_model")
    client.create_model_version("legacy_model", "file:///m3", tags=TAGS, description=CARD)
    client.create_model_version("pricing-tip-amount", "file:///m4", tags={**TAGS, "team": "ads"}, description=CARD)
    report = gate.audit_registry(client)
    expected = {
        "search-ranker/1": ["tag-missing:cost_center"],
        "legacy_model/1": ["name"],
        "pricing-tip-amount/2": ["team-mismatch"],
    }
    assert report == expected, f"báo cáo audit: {report}"

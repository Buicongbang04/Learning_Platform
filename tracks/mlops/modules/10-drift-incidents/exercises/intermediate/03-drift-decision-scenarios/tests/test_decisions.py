import json
from pathlib import Path

import pytest
import yaml

from testkit import Exercise

ex = Exercise(__file__)
FIXTURE = Path(__file__).parent / "fixtures" / "scenarios.json"
SCENARIOS = json.loads(FIXTURE.read_text(encoding="utf-8"))
EXPECTED = {"holiday-week": "keep", "bad-release": "rollback", "covid-lockdown": "retrain"}
VALID = {"retrain", "rollback", "keep"}


def submitted():
    data = yaml.safe_load(ex.path("decisions.yaml").read_text(encoding="utf-8"))
    assert isinstance(data, dict), "decisions.yaml phải là mapping {id tình huống: {decision, reasons, evidence}}"
    return data


def test_scenario_data_is_unchanged():
    assert json.loads(ex.path("scenarios.json").read_text(encoding="utf-8")) == SCENARIOS


def test_every_scenario_is_answered():
    assert set(submitted()) == set(SCENARIOS)


@pytest.mark.parametrize("scenario", list(EXPECTED))
def test_decision_is_valid_and_correct(scenario):
    entry = submitted().get(scenario)
    assert isinstance(entry, dict), f"thiếu mục {scenario}"
    assert entry.get("decision") in VALID, f"decision phải là một trong {sorted(VALID)}"
    assert entry["decision"] == EXPECTED[scenario]


@pytest.mark.parametrize("scenario", list(EXPECTED))
def test_reasons_are_written(scenario):
    reasons = submitted()[scenario].get("reasons")
    assert isinstance(reasons, list) and len(reasons) >= 2
    assert all(isinstance(r, str) and len(r.strip()) >= 30 for r in reasons)


@pytest.mark.parametrize("scenario", list(EXPECTED))
def test_evidence_cites_real_numbers_including_quality(scenario):
    data = SCENARIOS[scenario]
    evidence = submitted()[scenario].get("evidence")
    assert isinstance(evidence, dict) and len(evidence) >= 2, "evidence cần ít nhất 2 mục"
    for key, value in evidence.items():
        assert key in data["metrics"], f"{key} không có trong metrics của {scenario}"
        assert isinstance(value, (int, float)) and not isinstance(value, bool), f"{key} phải là số"
        assert value == pytest.approx(data["metrics"][key], rel=0.01, abs=0.005), f"{key} lệch số trong scenarios.json"
    assert set(evidence) & set(data["quality_keys"]), "evidence phải có ít nhất một số đo chất lượng (nhãn)"


def test_decisions_are_not_one_reflex():
    decisions = {e.get("decision") for e in submitted().values() if isinstance(e, dict)}
    assert len(decisions) >= 3, "ba tình huống có ba quyết định khác nhau"

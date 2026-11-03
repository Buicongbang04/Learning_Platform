from pathlib import Path

import yaml

from testkit import Exercise

ex = Exercise(__file__)
SYSTEMS = yaml.safe_load((Path(__file__).parent / "fixtures" / "systems.yaml").read_text(encoding="utf-8"))
NEXT = {
    0: "training_triggered_automatically",
    1: "pipeline_cicd",
}


def google_level(facts: dict) -> int:
    if not facts["training_triggered_automatically"]:
        return 0
    return 2 if facts["pipeline_cicd"] else 1


def microsoft_level(facts: dict) -> int:
    if facts["monitoring_triggers_retraining"] and facts["deploy_automated"]:
        return 4
    if facts["deploy_automated"] and facts["model_validation_gate"]:
        return 3
    if facts["training_triggered_automatically"] and facts["experiment_tracking_registry"]:
        return 2
    if facts["ci_tests_code"]:
        return 1
    return 0


def load_answers() -> dict:
    data = yaml.safe_load(ex.read("classification.yaml"))
    assert isinstance(data, dict), "classification.yaml phải là mapping system-id -> trả lời"
    return data


def test_fixtures_match_rubric():
    got = {s["id"]: (google_level(s["facts"]), microsoft_level(s["facts"])) for s in SYSTEMS}
    assert got == {"quote-pricing": (0, 1), "recsys-ranking": (1, 2), "fraud-scoring": (2, 4)}


def test_every_system_answered():
    answers = load_answers()
    assert set(answers) == {s["id"] for s in SYSTEMS}
    for s in SYSTEMS:
        assert set(answers[s["id"]]) >= {"google_level", "microsoft_level", "blocker", "rationale"}


def test_google_levels():
    answers = load_answers()
    for s in SYSTEMS:
        assert answers[s["id"]].get("google_level") == google_level(s["facts"]), f"{s['id']}: sai google_level"


def test_microsoft_levels():
    answers = load_answers()
    for s in SYSTEMS:
        assert answers[s["id"]].get("microsoft_level") == microsoft_level(s["facts"]), f"{s['id']}: sai microsoft_level"


def test_blockers():
    answers = load_answers()
    for s in SYSTEMS:
        want = NEXT.get(google_level(s["facts"]))
        assert answers[s["id"]].get("blocker") == want, f"{s['id']}: blocker phải là {want}"


def test_rationale_cites_facts():
    answers = load_answers()
    for s in SYSTEMS:
        text = str(answers[s["id"]].get("rationale") or "")
        assert len(text.strip()) >= 60, f"{s['id']}: rationale cần ít nhất 60 ký tự"

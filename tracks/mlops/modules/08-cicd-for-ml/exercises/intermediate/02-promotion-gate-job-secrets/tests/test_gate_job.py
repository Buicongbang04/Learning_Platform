import base64
import json

import pytest

import cikit
from testkit import Exercise

ex = Exercise(__file__)

TOKEN = "tok-7f3a91c2e5b84d06"
WORKFLOW = ".github/workflows/ct.yml"


@pytest.fixture(scope="module")
def gate():
    return ex.module("gate.py")


@pytest.mark.parametrize(
    "challenger,champion,policy,expected",
    [
        ({"mae": 190.0}, {"mae": 200.0}, 0.01, True),
        ({"mae": 198.0}, {"mae": 200.0}, 0.01, True),
        ({"mae": 198.5}, {"mae": 200.0}, 0.01, False),
        ({"mae": 200.0}, {"mae": 200.0}, 0.0, True),
        ({"mae": 210.0}, {"mae": 200.0}, 0.01, False),
        ({"mae": 500.0}, None, 0.01, True),
        ({"mae": float("nan")}, None, 0.01, False),
        ({"mae": float("nan")}, {"mae": 200.0}, 0.01, False),
        ({}, {"mae": 200.0}, 0.01, False),
        ({"mae": 100.0}, {"mae": float("nan")}, 0.01, False),
        ({"mae": float("inf")}, None, 0.01, False),
    ],
)
def test_decide_cases(gate, challenger, champion, policy, expected):
    passed, reason = gate.decide(challenger, champion, policy)
    assert passed is expected, reason
    assert isinstance(reason, str) and reason


def test_decide_reason_has_both_numbers_when_rejecting(gate):
    passed, reason = gate.decide({"mae": 210.0}, {"mae": 200.0}, 0.01)
    assert not passed and "210" in reason and "200" in reason


@pytest.fixture(scope="module")
def trained_mae(tmp_path_factory):
    repo = cikit.make_repo(tmp_path_factory.mktemp("probe"), {"gate.py": "print('stub')\n"}, data=True)
    cikit.write_workflow(repo, "ct.yml", "name: p\non: push\njobs:\n  t:\n    runs-on: ubuntu-latest\n    steps:\n      - run: python train.py\n")
    cikit.commit_all(repo)
    result = cikit.run_ci(repo)
    assert result.returncode == 0, cikit.log(result)[-1500:]
    return json.loads((repo / "models" / "metrics.json").read_text())["mae"]


@pytest.fixture
def pipeline(tmp_path, trained_mae):
    def build(champion_factor):
        repo = cikit.make_repo(tmp_path, {"gate.py": ex.read("gate.py")}, data=True)
        cikit.write_workflow(repo, "ct.yml", ex.read("ct.yml"))
        if champion_factor is not None:
            (repo / "champion").mkdir()
            (repo / "champion" / "metrics.json").write_text(json.dumps({"mae": trained_mae * champion_factor}))
        cikit.commit_all(repo)
        return repo

    return build


def secret_leaks(text):
    forms = [TOKEN, base64.b64encode(TOKEN.encode()).decode(), TOKEN[:10]]
    return [form for form in forms if form in text]


def test_better_challenger_deploys_and_keeps_the_secret_out_of_the_log(pipeline):
    repo = pipeline(1.5)
    result = cikit.run_ci(repo, "-s", f"REGISTRY_TOKEN={TOKEN}")
    text = cikit.log(result)
    assert result.returncode == 0, text[-2500:]
    assert "GATE PASSED" in text and "DEPLOYED" in text
    assert (repo / "registry" / "model.json").read_text() == (repo / "models" / "model.json").read_text()
    assert secret_leaks(text) == [], f"Log lộ secret dưới dạng: {secret_leaks(text)}"


def test_worse_challenger_fails_the_gate_and_deploy_never_runs(pipeline):
    repo = pipeline(0.5)
    result = cikit.run_ci(repo, "-s", f"REGISTRY_TOKEN={TOKEN}")
    text = cikit.log(result)
    assert result.returncode != 0, "Challenger tệ hơn mà pipeline vẫn xanh"
    assert "GATE FAILED" in text
    assert "DEPLOYED" not in text and "[ct/deploy]" not in text, "Job deploy đã chạy dù cổng đỏ"
    assert not (repo / "registry").exists()
    assert secret_leaks(text) == []


def test_first_model_without_champion_passes_the_gate(pipeline):
    repo = pipeline(None)
    result = cikit.run_ci(repo, "-s", f"REGISTRY_TOKEN={TOKEN}")
    assert result.returncode == 0, cikit.log(result)[-2000:]
    assert (repo / "registry" / "model.json").is_file()


def test_deploy_refuses_to_run_without_the_secret(pipeline):
    repo = pipeline(1.5)
    result = cikit.run_ci(repo)
    assert result.returncode != 0, "Thiếu REGISTRY_TOKEN mà deploy vẫn xanh"
    assert not (repo / "registry" / "model.json").exists()


def test_deploy_job_needs_the_gate(pipeline):
    repo = pipeline(1.5)
    workflow = cikit.load_workflow(repo / WORKFLOW)
    needs = workflow["jobs"]["deploy"].get("needs")
    assert needs in ("gate", ["gate"]), "deploy phải needs gate"
    assert workflow["jobs"]["gate"].get("needs") in ("train", ["train"]), "gate phải needs train"

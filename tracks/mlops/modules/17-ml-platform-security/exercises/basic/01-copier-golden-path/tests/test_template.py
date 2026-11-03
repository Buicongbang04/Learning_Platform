import shutil
import sys
from pathlib import Path

import pytest
import yaml

import testkit
from testkit import Exercise

ex = Exercise(__file__)
VALID = {
    "project_name": "Tip Amount",
    "team": "pricing",
    "owner": "lan.nguyen@example.com",
    "cost_center": "CC-2041",
}
ENV = {"PYTHONDONTWRITEBYTECODE": "1", "NO_COLOR": "1"}


def sandboxed(cmd, tmp_path, cwd, timeout=120):
    return testkit.run_sandboxed([str(c) for c in cmd], writable=[tmp_path], cwd=cwd, env=ENV, timeout=timeout)


def render(tmp_path, answers, name="out"):
    template = tmp_path / "template"
    if not template.exists():
        shutil.copytree(ex.path("template"), template)
    dst = tmp_path / name
    args = [sys.executable, "-m", "copier", "copy", "--defaults", "--quiet"]
    for key, value in answers.items():
        args += ["--data", f"{key}={value}"]
    result = sandboxed([*args, template, dst], tmp_path, tmp_path)
    return result, dst


def run_project_tests(tmp_path, dst):
    return sandboxed([sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider"], tmp_path, dst, timeout=180)


def metadata(dst):
    return yaml.safe_load((dst / "mlproject.yaml").read_text(encoding="utf-8"))


def rendered(tmp_path):
    result, dst = render(tmp_path, VALID)
    assert result.returncode == 0, result.stderr[-2000:]
    return dst


def test_metadata_carries_answers_and_required_tags(tmp_path):
    project = rendered(tmp_path)
    assert (project / "mlproject.yaml").is_file()
    meta = metadata(project)
    assert meta["name"] == "tip-amount"
    assert meta["registry_name"] == "pricing-tip-amount"
    assert meta["model_kind"] == "regression"
    assert meta["tags"] == {"owner": VALID["owner"], "team": "pricing", "cost_center": "CC-2041"}


def test_answers_file_recorded_for_copier_update(tmp_path):
    project = rendered(tmp_path)
    answers_file = project / ".copier-answers.yml"
    assert answers_file.is_file()
    answers = yaml.safe_load(answers_file.read_text(encoding="utf-8"))
    assert answers.get("_src_path")
    for key in ("team", "owner", "cost_center"):
        assert answers.get(key) == VALID[key]


def test_generated_project_passes_its_own_tests(tmp_path):
    project = rendered(tmp_path)
    result = run_project_tests(tmp_path, project)
    assert result.returncode == 0, (result.stdout + result.stderr)[-3000:]
    passed = [line for line in result.stdout.splitlines() if " passed" in line]
    assert passed and int(passed[-1].split(" passed")[0].split()[-1]) >= 2


@pytest.mark.parametrize("tag", ["owner", "team", "cost_center"])
def test_generated_tests_catch_a_missing_tag(tmp_path, tag):
    project = rendered(tmp_path)
    meta = metadata(project)
    del meta["tags"][tag]
    (project / "mlproject.yaml").write_text(yaml.safe_dump(meta), encoding="utf-8")
    result = run_project_tests(tmp_path, project)
    assert result.returncode != 0


def test_slug_defaults_from_project_name(tmp_path):
    result, dst = render(tmp_path, {**VALID, "project_name": "Trip Duration"})
    assert result.returncode == 0, result.stderr[-2000:]
    assert metadata(dst)["registry_name"] == "pricing-trip-duration"


def test_classification_variant(tmp_path):
    result, dst = render(tmp_path, {**VALID, "model_kind": "classification", "team": "fraud", "project_name": "Card Fraud"})
    assert result.returncode == 0, result.stderr[-2000:]
    assert metadata(dst)["registry_name"] == "fraud-card-fraud"
    tests = run_project_tests(tmp_path, dst)
    assert tests.returncode == 0, (tests.stdout + tests.stderr)[-3000:]
    probe = (
        "import numpy as np; from model import train; rng = np.random.default_rng(1); X = rng.normal(size=(100, 2)); "
        "y = (X[:, 0] > 0).astype(int); print(sorted(set(train(X, y).predict(X).tolist())))"
    )
    result = sandboxed([sys.executable, "-c", probe], tmp_path, dst)
    assert result.returncode == 0, result.stderr[-2000:]
    assert result.stdout.strip() == "[0, 1]"


BAD = {
    "owner-not-email": {"owner": "lan"},
    "owner-empty": {"owner": ""},
    "cost-center-no-prefix": {"cost_center": "2041"},
    "cost-center-too-long": {"cost_center": "CC-20411"},
    "slug-underscore": {"project_slug": "tip_amount"},
    "slug-uppercase": {"project_slug": "Tip-Amount"},
    "team-unknown": {"team": "marketing"},
}


@pytest.mark.parametrize("case", sorted(BAD))
def test_invalid_answer_is_rejected(tmp_path, case):
    result, dst = render(tmp_path, {**VALID, **BAD[case]})
    rejected = result.returncode != 0 and not (dst / "mlproject.yaml").exists()
    assert rejected, f"ca {case}: copier vẫn sinh dự án"


@pytest.mark.parametrize("missing", ["owner", "cost_center"])
def test_required_answer_has_no_default(tmp_path, missing):
    answers = {k: v for k, v in VALID.items() if k != missing}
    result, dst = render(tmp_path, answers)
    rejected = result.returncode != 0 and not (dst / "mlproject.yaml").exists()
    assert rejected, f"thiếu {missing} mà copier vẫn sinh dự án"


def test_template_runs_without_trust(tmp_path):
    config = yaml.safe_load((ex.path("template") / "copier.yml").read_text(encoding="utf-8"))
    unsafe = {"_tasks", "_migrations", "_jinja_extensions"} & set(config)
    assert not unsafe

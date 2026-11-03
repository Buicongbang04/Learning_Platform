import sys

import pytest

import cikit
import testkit
from testkit import Exercise

ex = Exercise(__file__)


@pytest.fixture
def workflow():
    return cikit.load_workflow(ex.path("ci.yml"))


def prepare(tmp_path, mutate=None):
    repo = cikit.make_repo(tmp_path, tools=True)
    cikit.write_workflow(repo, "ci.yml", ex.read("ci.yml"))
    if mutate:
        mutate(repo)
    cikit.commit_all(repo)
    return repo


def test_workflow_structure(workflow):
    jobs = workflow["jobs"]
    assert {"lint", "test", "build"} <= set(jobs), f"Cần ba job lint, test, build; đang có {sorted(jobs)}"
    assert {"push", "pull_request"} <= set(cikit.events(workflow))
    for name, job in jobs.items():
        assert job.get("runs-on") == "ubuntu-latest", f"{name}: runs-on phải là ubuntu-latest"
        assert all("uses" not in step for step in job["steps"]), f"{name}: chỉ dùng bước run, không dùng uses"
    needs = jobs["build"].get("needs")
    needs = [needs] if isinstance(needs, str) else needs or []
    assert {"lint", "test"} <= set(needs), "build phải needs cả lint và test"


def test_good_repo_is_green_and_builds_the_package(tmp_path):
    repo = prepare(tmp_path)
    result = cikit.run_ci(repo)
    assert result.returncode == 0, cikit.log(result)[-2500:]
    package = repo / "dist" / "etalite.pyz"
    assert package.is_file(), "Job build phải tạo dist/etalite.pyz"
    run = testkit.run_sandboxed([sys.executable, str(package)], writable=[repo], cwd=repo, env={})
    assert run.stdout.strip() == "etalite 1.0 40", run.stdout + run.stderr


def test_failing_unit_test_turns_the_pipeline_red(tmp_path):
    def break_test(repo):
        path = repo / "tests" / "test_model.py"
        path.write_text(path.read_text().replace("== 0.5", "== 99"))

    result = cikit.run_ci(prepare(tmp_path, break_test))
    assert result.returncode != 0, "Test hỏng mà pipeline vẫn xanh"
    assert "Job failed" in cikit.log(result)
    assert not (tmp_path / "repo" / "dist" / "etalite.pyz").exists(), "build không được chạy khi test đỏ"


def test_lint_violation_turns_the_pipeline_red(tmp_path):
    def add_unused_import(repo):
        path = repo / "src" / "etalite" / "model.py"
        path.write_text("import os\n\n\n" + path.read_text())

    result = cikit.run_ci(prepare(tmp_path, add_unused_import))
    assert result.returncode != 0, "Lỗi lint mà pipeline vẫn xanh"
    assert not (tmp_path / "repo" / "dist" / "etalite.pyz").exists(), "build không được chạy khi lint đỏ"

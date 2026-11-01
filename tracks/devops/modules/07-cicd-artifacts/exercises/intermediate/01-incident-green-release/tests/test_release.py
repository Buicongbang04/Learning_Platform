import re
import shutil
from pathlib import Path

import pytest
import yaml

import testkit
from testkit import ROOT, Exercise, run_sandboxed

ex = Exercise(__file__)
APP = ROOT / "tracks" / "devops" / "sample-app"
FIXTURES = Path(__file__).parent / "fixtures"
WORKFLOW = ".github/workflows/release.yml"
SETUP_STEPS = ("Cài uv", "Cài Python và dependency")
SHA_TAG = re.compile(r"^sha-[0-9a-f]{12}$")
NETWORK = re.compile(
    r"ENOTFOUND|EAI_AGAIN|ECONNREFUSED|ECONNRESET|ETIMEDOUT|UND_ERR_CONNECT|dns error|error sending request|"
    r"Failed to fetch|Could not connect|Network is unreachable|Temporary failure in name resolution"
)
FAILED_STEP = re.compile(r"❌\s+Failure - Main (.+?) \[[0-9.]+\D*\]")
CANARY = "def test_devops_ex_canary_red():\n    assert 1 + 1 == 3, 'test đỏ do harness cài vào'\n"


def assemble(dest: Path, workflow: Path, *, canary: bool) -> Path:
    for name in ("olist_shop", "tests"):
        shutil.copytree(APP / name, dest / name, ignore=shutil.ignore_patterns("__pycache__", "*.db"))
    for name in ("conftest.py", "requirements.txt", "compose.yaml", ".dockerignore", "Dockerfile"):
        shutil.copyfile(APP / name, dest / name)
    shutil.copyfile(FIXTURES / "repo" / "requirements-dev.txt", dest / "requirements-dev.txt")
    target = dest / WORKFLOW
    target.parent.mkdir(parents=True)
    shutil.copyfile(workflow, target)
    if canary:
        (dest / "tests" / "test_devops_ex_canary.py").write_text(CANARY, encoding="utf-8")
    return dest


def run_release(dest: Path):
    result = testkit.act_run(dest, event="push", timeout=600)
    text = f"{result.stdout}\n{result.stderr}"
    if any(s.strip() in SETUP_STEPS for s in FAILED_STEP.findall(text)) and NETWORK.search(text):
        pytest.skip("Bước cài uv/Python trong job cần mạng (github.com, pypi.org) và đang lỗi mạng. Kiểm kết nối rồi chạy lại.")
    return result


def tail(result) -> str:
    text = f"{result.stdout}\n{result.stderr}".strip()
    return "Output cuối của act:\n" + "\n".join(text.splitlines()[-40:])


def summary(result) -> str:
    return testkit.act_outputs(result).get("test", {}).get("summary", "")


def structure_problems(doc: dict) -> list[str]:
    jobs = doc.get("jobs") if isinstance(doc.get("jobs"), dict) else {}
    test, publish = jobs.get("test"), jobs.get("publish")
    if not isinstance(test, dict) or not isinstance(publish, dict):
        return ["Phải giữ hai job test và publish"]
    found = []
    needs = publish.get("needs")
    if "test" not in ([needs] if isinstance(needs, str) else needs or []):
        found.append("Job publish phải giữ needs: test")
    if publish.get("permissions") != {"contents": "read", "packages": "write"}:
        found.append("Job publish phải giữ permissions contents: read, packages: write")
    for name, job in (("test", test), ("publish", publish)):
        if job.get("continue-on-error") not in (None, False):
            found.append(f"Job {name} không được continue-on-error")
        for step in job.get("steps") or []:
            if isinstance(step, dict) and step.get("continue-on-error") not in (None, False):
                found.append(f"Job {name}, bước {step.get('name')}: không được continue-on-error")
    if not any(isinstance(s, dict) and "always()" in str(s.get("if", "")) and "devops-ex-output summary=" in str(s.get("run", ""))
               for s in test.get("steps") or []):
        found.append("Job test phải giữ bước tóm tắt có if: always() và in devops-ex-output summary=...")
    return found


@pytest.fixture(scope="module")
def red(tmp_path_factory):
    return run_release(assemble(tmp_path_factory.mktemp("red"), ex.path(WORKFLOW), canary=True))


@pytest.fixture(scope="module")
def green(tmp_path_factory):
    return run_release(assemble(tmp_path_factory.mktemp("green"), ex.path(WORKFLOW), canary=False))


def test_structure_kept():
    found = structure_problems(yaml.safe_load(ex.read(WORKFLOW)) or {})
    assert not found, "\n".join(found)


def test_red_tests_stop_the_release(red):
    jobs = testkit.act_job_results(red)
    assert jobs.get("test") is False, f"Có test đỏ mà job test vẫn xanh. {tail(red)}"
    assert jobs.get("publish") is not True, "Job publish vẫn chạy dù có test đỏ"
    assert "tag" not in testkit.act_outputs(red).get("publish", {}), "Job publish vẫn tính tag dù có test đỏ"
    assert "1 failed" in summary(red), f"Bước tóm tắt phải vẫn báo kết quả pytest khi test đỏ, nhận {summary(red)!r}. {tail(red)}"


def test_green_tests_publish(green):
    jobs = testkit.act_job_results(green)
    assert jobs.get("test") is True and jobs.get("publish") is True, f"Code đúng mà release không xanh: {jobs}. {tail(green)}"
    assert SHA_TAG.fullmatch(testkit.act_outputs(green).get("publish", {}).get("tag", "")), "Job publish không in tag sha-<12 hex>"
    text = summary(green)
    assert "passed" in text and "failed" not in text, f"Tóm tắt khi mọi test xanh phải có 'passed', nhận {text!r}"


def test_incident_workflow_reproduces_symptom(tmp_path):
    result = run_release(assemble(tmp_path / "repo", FIXTURES / "incident" / "release.yml", canary=True))
    jobs = testkit.act_job_results(result)
    assert "1 failed" in summary(result), f"Bản lúc sự cố phải báo test đỏ trong tóm tắt. {tail(result)}"
    assert jobs.get("test") is True and jobs.get("publish") is True, f"Bản lúc sự cố phải tái hiện CI xanh: {jobs}"
    assert SHA_TAG.fullmatch(testkit.act_outputs(result).get("publish", {}).get("tag", ""))


def test_checks_catch_bypasses():
    doc = yaml.safe_load((FIXTURES / "incident" / "release.yml").read_text(encoding="utf-8"))
    doc["jobs"]["publish"]["needs"] = []
    doc["jobs"]["test"]["steps"][-2]["continue-on-error"] = True
    doc["jobs"]["test"]["steps"].pop()
    found = "\n".join(structure_problems(doc))
    assert "needs: test" in found and "continue-on-error" in found and "bước tóm tắt" in found, found


def test_actionlint(tmp_path):
    ex.require_tool("actionlint", "1.7")
    target = tmp_path / WORKFLOW
    target.parent.mkdir(parents=True)
    shutil.copyfile(ex.path(WORKFLOW), target)
    result = run_sandboxed(["actionlint", "-no-color", "-shellcheck=", "-pyflakes=", WORKFLOW], writable=[tmp_path],
                           cwd=tmp_path, env={}, timeout=60)
    assert result.returncode == 0, f"actionlint báo lỗi:\n{result.stdout}{result.stderr}"

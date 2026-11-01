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
WORKFLOW = ".github/workflows/worker-ci.yml"
JOB = "worker-tests"
SETUP_STEPS = ("Cài uv", "Cài Python và dependency")
PINNED = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_./-]+@[0-9a-f]{40}$")
UNTRUSTED = re.compile(r"\$\{\{[^}]*\bgithub\.(?:event\.|head_ref\b)")
NETWORK = re.compile(
    r"ENOTFOUND|EAI_AGAIN|ECONNREFUSED|ECONNRESET|ETIMEDOUT|UND_ERR_CONNECT|dns error|error sending request|"
    r"Failed to fetch|Could not connect|Network is unreachable|Temporary failure in name resolution"
)
FAILED_STEP = re.compile(r"❌\s+Failure - Main (.+?) \[[0-9.]+\D*\]")


def load(path: Path) -> dict:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    return data if isinstance(data, dict) else {}


def triggers(doc: dict) -> dict:
    on = doc.get("on", doc.get(True))
    if isinstance(on, str):
        return {on: None}
    if isinstance(on, list):
        return {name: None for name in on}
    return on if isinstance(on, dict) else {}


def steps(job: dict) -> list[dict]:
    return [s for s in (job.get("steps") or []) if isinstance(s, dict)]


def read_only(permissions) -> bool:
    return permissions == {} or (isinstance(permissions, dict) and set(permissions) <= {"contents"}
                                 and all(v == "read" for v in permissions.values()))


def hardening_problems(doc: dict) -> list[str]:
    found = []
    on = triggers(doc)
    if "pull_request_target" in on:
        found.append("Không dùng pull_request_target: workflow chạy với quyền và secret của repo gốc trên code của PR")
    push = on.get("push") if isinstance(on.get("push"), dict) else {}
    if push.get("branches") != ["main"]:
        found.append("on.push phải giới hạn branches: [main]")
    if "pull_request" not in on:
        found.append("Cần trigger pull_request để PR vẫn được kiểm")
    if "permissions" not in doc or not read_only(doc.get("permissions")):
        found.append(f"permissions cấp workflow phải là {{}} hoặc contents: read, đang là {doc.get('permissions', '(không khai báo)')!r}")
    jobs = doc.get("jobs") if isinstance(doc.get("jobs"), dict) else {}
    if JOB not in jobs:
        found.append(f"Phải giữ job {JOB}")
    top = doc.get("concurrency") if isinstance(doc.get("concurrency"), dict) else {}
    for name, job in jobs.items():
        if not isinstance(job, dict):
            continue
        if "permissions" in job and not read_only(job["permissions"]):
            found.append(f"Job {name}: không cần quyền ghi nào, đang là {job['permissions']!r}")
        limit = job.get("timeout-minutes")
        if not isinstance(limit, int) or not 1 <= limit <= 30:
            found.append(f"Job {name}: cần timeout-minutes từ 1 tới 30")
        concurrency = job.get("concurrency") if isinstance(job.get("concurrency"), dict) else top
        if not concurrency.get("group") or not concurrency.get("cancel-in-progress"):
            found.append(f"Job {name}: cần concurrency có group và cancel-in-progress")
        for index, step in enumerate(steps(job), 1):
            where = f"Job {name}, bước {index} ({step.get('name') or step.get('uses') or 'run'})"
            uses = str(step.get("uses", ""))
            if uses and not PINNED.match(uses):
                found.append(f"{where}: {uses} phải ghim theo commit SHA đủ 40 ký tự")
            if uses.split("@")[0] == "actions/checkout":
                options = step.get("with") or {}
                if options.get("persist-credentials") is not False:
                    found.append(f"{where}: checkout cần persist-credentials: false")
                if "github.event" in str(options.get("ref", "")):
                    found.append(f"{where}: checkout không được lấy ref từ dữ liệu của sự kiện")
            if UNTRUSTED.search(str(step.get("run", ""))):
                found.append(f"{where}: run: chèn thẳng github.event.* hoặc github.head_ref, phải đưa qua env:")
    return found


def assemble(dest: Path, workflow: Path) -> Path:
    for name in ("olist_shop", "tests"):
        shutil.copytree(APP / name, dest / name, ignore=shutil.ignore_patterns("__pycache__", "*.db"))
    for name in ("conftest.py", "requirements.txt", "compose.yaml"):
        shutil.copyfile(APP / name, dest / name)
    shutil.copyfile(FIXTURES / "repo" / "requirements-dev.txt", dest / "requirements-dev.txt")
    target = dest / WORKFLOW
    target.parent.mkdir(parents=True)
    shutil.copyfile(workflow, target)
    return dest


def tail(result) -> str:
    text = f"{result.stdout}\n{result.stderr}".strip()
    return "Output cuối của act:\n" + "\n".join(text.splitlines()[-40:])


def test_workflow_is_hardened():
    found = hardening_problems(load(ex.path(WORKFLOW)))
    assert not found, "\n".join(found)


def test_checks_catch_starter():
    found = "\n".join(hardening_problems(load(FIXTURES / "worker-ci.starter.yml")))
    for needle in ("pull_request_target", "branches: [main]", "Cần trigger pull_request", "permissions cấp workflow",
                   "timeout-minutes", "concurrency", "actions/checkout@v7 phải ghim", "actions/upload-artifact@v7 phải ghim",
                   "persist-credentials", "Lấy code của PR): run: chèn thẳng"):
        assert needle in found, found


def test_actionlint(tmp_path):
    ex.require_tool("actionlint", "1.7")
    target = tmp_path / WORKFLOW
    target.parent.mkdir(parents=True)
    shutil.copyfile(ex.path(WORKFLOW), target)
    result = run_sandboxed(["actionlint", "-no-color", "-shellcheck=", "-pyflakes=", WORKFLOW], writable=[tmp_path],
                           cwd=tmp_path, env={}, timeout=60)
    assert result.returncode == 0, f"actionlint báo lỗi:\n{result.stdout}{result.stderr}"


def test_hardened_workflow_still_runs_worker_tests(tmp_path):
    result = testkit.act_run(assemble(tmp_path / "repo", ex.path(WORKFLOW)), event="push", timeout=600)
    text = f"{result.stdout}\n{result.stderr}"
    if any(s.strip() in SETUP_STEPS for s in FAILED_STEP.findall(text)) and NETWORK.search(text):
        pytest.skip("Bước cài uv/Python trong job cần mạng (github.com, pypi.org) và đang lỗi mạng. Kiểm kết nối rồi chạy lại.")
    assert testkit.act_job_results(result).get(JOB) is True, f"Job {JOB} không xanh khi push lên main. {tail(result)}"
    assert re.search(r"\|\s+\d+ passed", text), f"Không thấy pytest chạy test của worker. {tail(result)}"

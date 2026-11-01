import re
import shutil
from pathlib import Path

import httpx
import pytest
import yaml

import testkit
from testkit import ROOT, REGISTRY_MANIFEST_TYPES, DockerLab, Exercise, build_failed_on_network, run_sandboxed

ex = Exercise(__file__)
APP = ROOT / "tracks" / "devops" / "sample-app"
FIXTURES = Path(__file__).parent / "fixtures"
WORKFLOW = ".github/workflows/ci.yml"
SETUP_STEPS = ("Cài uv", "Cài Python và dependency")
SHA_TAG = re.compile(r"^sha-[0-9a-f]{12}$")
STEP_OUTPUT = re.compile(r"steps\.([A-Za-z0-9_-]+)\.outputs\.tag")
NETWORK = re.compile(
    r"ENOTFOUND|EAI_AGAIN|ECONNREFUSED|ECONNRESET|ETIMEDOUT|UND_ERR_CONNECT|dns error|error sending request|"
    r"Failed to fetch|Could not connect|Network is unreachable|Temporary failure in name resolution"
)
FAILED_STEP = re.compile(r"❌\s+Failure - Main (.+?) \[[0-9.]+\D*\]")
CANARY = "def test_devops_ex_canary_red():\n    assert 1 + 1 == 3, 'test đỏ do harness cài vào'\n"
ACT_TIMEOUT = 600


def assemble(dest: Path, workflow: Path, *, canary: bool = False) -> Path:
    for name in ("olist_shop", "tests"):
        shutil.copytree(APP / name, dest / name, ignore=shutil.ignore_patterns("__pycache__", "*.db"))
    for name in ("conftest.py", "requirements.txt", "compose.yaml", ".dockerignore"):
        shutil.copyfile(APP / name, dest / name)
    for item in (FIXTURES / "repo").iterdir():
        shutil.copyfile(item, dest / item.name)
    target = dest / WORKFLOW
    target.parent.mkdir(parents=True)
    shutil.copyfile(workflow, target)
    if canary:
        (dest / "tests" / "test_devops_ex_canary.py").write_text(CANARY, encoding="utf-8")
    return dest


def run_workflow(dest: Path) -> object:
    result = testkit.act_run(dest, event="push", timeout=ACT_TIMEOUT)
    text = f"{result.stdout}\n{result.stderr}"
    failed = [step.strip() for step in FAILED_STEP.findall(text)]
    if any(step in SETUP_STEPS for step in failed) and NETWORK.search(text):
        pytest.skip("Bước cài uv/Python trong job cần mạng (github.com, pypi.org) và đang lỗi mạng. Kiểm kết nối rồi chạy lại.")
    return result


def tail(result) -> str:
    text = f"{result.stdout}\n{result.stderr}".strip()
    return "Output cuối của act:\n" + "\n".join(text.splitlines()[-40:])


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


def uses_step(job: dict, action: str) -> dict | None:
    return next((s for s in steps(job) if str(s.get("uses", "")).split("@")[0] == action), None)


def guarded(step: dict) -> bool:
    return "!env.ACT" in re.sub(r"\s+", "", str(step.get("if", "")))


def has_write(permissions) -> bool:
    if permissions == "write-all":
        return True
    return isinstance(permissions, dict) and any(str(v) == "write" for v in permissions.values())


def structure_problems(doc: dict) -> list[str]:
    found = []
    on = triggers(doc)
    if set(on) - {"push", "pull_request", "workflow_dispatch"}:
        found.append(f"Trigger chỉ được push, pull_request, workflow_dispatch; đang có {sorted(map(str, on))}")
    push = on.get("push") if isinstance(on.get("push"), dict) else {}
    if push.get("branches") != ["main"]:
        found.append("on.push phải giới hạn branches: [main]")
    if "pull_request" not in on:
        found.append("Thiếu trigger pull_request")
    if doc.get("permissions") != {"contents": "read"}:
        found.append(f"permissions cấp workflow phải đúng bằng contents: read, đang là {doc.get('permissions')!r}")
    concurrency = doc.get("concurrency") if isinstance(doc.get("concurrency"), dict) else {}
    if "github.ref" not in str(concurrency.get("group", "")) or not concurrency.get("cancel-in-progress"):
        found.append("concurrency cấp workflow cần group chứa github.ref và cancel-in-progress")
    jobs = doc.get("jobs") if isinstance(doc.get("jobs"), dict) else {}
    test, image = jobs.get("test"), jobs.get("image")
    for name, job in (("test", test), ("image", image)):
        if not isinstance(job, dict):
            found.append(f"Thiếu job {name}")
            continue
        limit = job.get("timeout-minutes")
        if not isinstance(limit, int) or not 1 <= limit <= 30:
            found.append(f"Job {name} cần timeout-minutes từ 1 tới 30")
    if isinstance(test, dict):
        if has_write(test.get("permissions")):
            found.append("Job test không được có quyền write")
        names = [s.get("name") for s in steps(test)]
        if any(name not in names for name in SETUP_STEPS):
            found.append(f"Job test phải giữ hai bước có sẵn {SETUP_STEPS}")
        if not any("pytest" in str(s.get("run", "")) for s in steps(test)):
            found.append("Job test thiếu bước run: chạy pytest")
    if isinstance(image, dict):
        found += image_problems(image)
    return found


def image_problems(image: dict) -> list[str]:
    found = []
    needs = image.get("needs")
    if "test" not in ([needs] if isinstance(needs, str) else needs or []):
        found.append("Job image phải needs: test")
    if image.get("permissions") != {"contents": "read", "packages": "write"}:
        found.append(f"Job image cần đúng permissions contents: read, packages: write; đang là {image.get('permissions')!r}")
    match = STEP_OUTPUT.search(str((image.get("outputs") or {}).get("tag", "")))
    meta = next((s for s in steps(image) if match and s.get("id") == match.group(1)), None)
    if meta is None:
        found.append("Job image cần outputs.tag lấy từ steps.<id>.outputs.tag của một bước trong job")
        return found
    script = str(meta.get("run", ""))
    if "GITHUB_SHA" not in script and "github.sha" not in script:
        found.append(f"Bước {meta['id']} phải tính tag từ GITHUB_SHA")
    if re.search(r"\bdate\b|run_number|run_id|run_attempt|latest", script):
        found.append(f"Bước {meta['id']} không được dùng date, run_number, run_id hay latest cho tag")
    if "GITHUB_OUTPUT" not in script:
        found.append(f"Bước {meta['id']} phải ghi tag vào $GITHUB_OUTPUT")
    ref = f"steps.{meta['id']}.outputs.tag"
    login = uses_step(image, "docker/login-action")
    if login is None or not guarded(login):
        found.append("Thiếu bước docker/login-action có if: ${{ !env.ACT ... }}")
    else:
        if (login.get("with") or {}).get("registry") != "ghcr.io":
            found.append("docker/login-action phải đăng nhập registry: ghcr.io")
        if "secrets.GITHUB_TOKEN" not in str((login.get("with") or {}).get("password", "")):
            found.append("docker/login-action phải dùng password: ${{ secrets.GITHUB_TOKEN }}")
    build = uses_step(image, "docker/build-push-action")
    if build is None or not guarded(build):
        found.append("Thiếu bước docker/build-push-action có if: ${{ !env.ACT ... }}")
        return found
    options = build.get("with") or {}
    if str(options.get("context", "")) != ".":
        found.append("docker/build-push-action cần context: .")
    if ref not in str(options.get("tags", "")) or "latest" in str(options.get("tags", "")):
        found.append(f"tags của docker/build-push-action phải dùng {ref} và không có latest")
    if not re.search(rf"APP_VERSION=\$\{{\{{\s*{re.escape(ref)}\s*\}}\}}", str(options.get("build-args", ""))):
        found.append(f"build-args phải có APP_VERSION=${{{{ {ref} }}}}")
    if "github.event_name" not in str(options.get("push", "")):
        found.append("push của docker/build-push-action phải là biểu thức theo github.event_name (không push từ pull_request)")
    return found


@pytest.fixture(scope="module")
def workflow_doc():
    return load(ex.path(WORKFLOW))


@pytest.fixture(scope="module")
def green(tmp_path_factory):
    return run_workflow(assemble(tmp_path_factory.mktemp("green"), ex.path(WORKFLOW)))


@pytest.fixture(scope="module")
def red(tmp_path_factory):
    return run_workflow(assemble(tmp_path_factory.mktemp("red"), ex.path(WORKFLOW), canary=True))


def test_workflow_structure(workflow_doc):
    found = structure_problems(workflow_doc)
    assert not found, "\n".join(found)


def test_checks_catch_starter():
    found = "\n".join(structure_problems(load(FIXTURES / "ci.starter.yml")))
    for needle in ("branches: [main]", "pull_request", "contents: read", "concurrency", "Thiếu job image",
                   "timeout-minutes", "pytest"):
        assert needle in found, found


def test_checks_catch_unsafe_image_job():
    unsafe = {
        "needs": [], "permissions": "write-all", "outputs": {"tag": "${{ steps.meta.outputs.tag }}"},
        "steps": [
            {"id": "meta", "run": 'echo "tag=$(date +%s)" >> "$GITHUB_OUTPUT"'},
            {"uses": "docker/login-action@v4", "with": {"registry": "docker.io", "password": "${{ secrets.PAT }}"},
             "if": "${{ !env.ACT }}"},
            {"uses": "docker/build-push-action@v7", "if": "${{ !env.ACT }}",
             "with": {"context": ".", "tags": "olist-api:latest", "push": True}},
        ],
    }
    found = "\n".join(image_problems(unsafe))
    for needle in ("needs: test", "packages: write", "GITHUB_SHA", "date", "ghcr.io", "GITHUB_TOKEN", "không có latest",
                   "APP_VERSION", "github.event_name"):
        assert needle in found, found


def test_actionlint(tmp_path):
    ex.require_tool("actionlint", "1.7")
    target = tmp_path / WORKFLOW
    target.parent.mkdir(parents=True)
    shutil.copyfile(ex.path(WORKFLOW), target)
    result = run_sandboxed(["actionlint", "-no-color", "-shellcheck=", "-pyflakes=", WORKFLOW], writable=[tmp_path],
                           cwd=tmp_path, env={}, timeout=60)
    assert result.returncode == 0, f"actionlint báo lỗi:\n{result.stdout}{result.stderr}"


def test_green_run_passes_tests_and_emits_tag(green):
    jobs = testkit.act_job_results(green)
    assert jobs.get("test") is True, f"Job test không xanh trên code đúng. {tail(green)}"
    assert jobs.get("image") is True, f"Job image không chạy hoặc lỗi. {tail(green)}"
    outputs = testkit.act_outputs(green).get("image", {})
    tag, revision = outputs.get("tag", ""), outputs.get("revision", "")
    assert re.fullmatch(r"[0-9a-f]{40}", revision), f"Job image phải in 'devops-ex-output revision=<GITHUB_SHA>', nhận {outputs}"
    assert SHA_TAG.fullmatch(tag), f"Tag phải dạng sha-<12 ký tự hex>, nhận {tag!r}"
    assert tag == f"sha-{revision[:12]}", f"Tag {tag} không khớp 12 ký tự đầu của commit {revision}"


def test_red_test_blocks_image(red):
    jobs = testkit.act_job_results(red)
    assert jobs.get("test") is False, f"Harness cài một test đỏ mà job test vẫn không fail. {tail(red)}"
    assert jobs.get("image") is not True, "Job image vẫn chạy dù job test fail"
    assert "tag" not in testkit.act_outputs(red).get("image", {}), "Job image vẫn tính tag dù job test fail"


def registry_digest(client: httpx.Client, ref: str) -> str:
    address, rest = ref.split("/", 1)
    repo, tag = rest.rsplit(":", 1)
    response = client.head(f"http://{address}/v2/{repo}/manifests/{tag}", headers={"Accept": ", ".join(REGISTRY_MANIFEST_TYPES)})
    assert response.status_code == 200, f"Registry không có {ref} (HTTP {response.status_code})"
    digest = response.headers.get("docker-content-digest", "")
    assert re.fullmatch(r"sha256:[0-9a-f]{64}", digest), f"Registry không trả digest hợp lệ cho {ref}: {digest!r}"
    by_digest = client.head(f"http://{address}/v2/{repo}/manifests/{digest}", headers={"Accept": ", ".join(REGISTRY_MANIFEST_TYPES)})
    assert by_digest.status_code == 200, f"Registry không tìm thấy manifest theo digest {digest}"
    return f"{address}/{repo}@{digest}"


def test_harness_builds_pushes_and_runs_by_digest(green, tmp_path):
    tag = testkit.act_outputs(green).get("image", {}).get("tag", "")
    if not SHA_TAG.fullmatch(tag):
        pytest.fail(f"Workflow chưa in tag hợp lệ (devops-ex-output tag=sha-<12 hex>), nhận {tag!r}")
    ex.require_registry()
    ex.require_image("python:3.12.16-slim-trixie")
    repo = assemble(tmp_path / "repo", ex.path(WORKFLOW))
    with DockerLab() as lab:
        try:
            image = lab.build(repo, "olist-api", build_args={"APP_VERSION": tag})
        except pytest.fail.Exception as error:
            if build_failed_on_network(str(error)):
                pytest.skip("Build image cần mạng ở lần đầu để tải gói pip. Kiểm kết nối rồi chạy lại.")
            raise
        ref = lab.push(image, "olist-api", tag=tag)
        with httpx.Client(trust_env=False, timeout=10) as client:
            pinned = registry_digest(client, ref)
        lab.start("api", pinned, ports=[8000], env={"DATABASE_URL": "sqlite:////tmp/olist.db"})
        url = f"http://127.0.0.1:{lab.port('api', 8000)}/healthz"
        lab.wait_http("api", url, timeout=90)
        body = httpx.get(url, timeout=10).json()
        assert body == {"status": "ok", "version": tag}, f"/healthz của image chạy theo digest trả {body}"

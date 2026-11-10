"""M04: .github/workflows/ci.yml và ci/smoke-test.sh, dùng lại container/ của M03. Hợp đồng đầy đủ ở
capstone/milestones/m04-cicd-pipeline.md."""

import json
import re
import secrets
import shutil
import subprocess
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import httpx
import pytest
import yaml

import testkit
from olist_stack import COMPOSE, DOCKERFILE, TARGETS, assemble, build_targets, missing
from testkit import ROOT, REGISTRY_MANIFEST_TYPES, DockerLab, Exercise, free_port, run_sandboxed

DOC = "m04-cicd-pipeline.md"
FIXTURES = Path(__file__).parent / "fixtures"
WORKFLOW = ".github/workflows/ci.yml"
SMOKE = "ci/smoke-test.sh"
SETUP_STEPS = ("Cài uv", "Cài Python và dependency")
MODULE07_STARTER = (ROOT / "tracks" / "devops" / "modules" / "07-cicd-artifacts" / "exercises" / "basic" / "01-olist-ci-image"
                    / "starter" / ".github" / "workflows" / "ci.yml")
TRIVY_ACTION_INPUTS = {"image-ref", "trivy-config", "version", "format", "output", "cache", "cache-dir", "hide-progress",
                       "timeout", "scan-type"}
TRIVY_ACTION_FORMATS = {"table", "json"}
SHA_TAG = re.compile(r"^sha-[0-9a-f]{12}$")
SHA_PIN = re.compile(r"^[^@\s]+@[0-9a-f]{40}$")
STEP_OUTPUT = re.compile(r"steps\.([A-Za-z0-9_-]+)\.outputs\.([A-Za-z0-9_-]+)")
CANARY = "def test_devops_ex_canary_red():\n    assert 1 + 1 == 3, 'test đỏ do harness cài vào'\n"
ACT_TIMEOUT = 900
BASH = shutil.which("bash")


def require_file(path: Path) -> Path:
    if not path.is_file():
        pytest.fail(missing(path, DOC), pytrace=False)
    return path


def load(path: Path) -> dict:
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as error:
        pytest.fail(f"{path.name} không phải YAML hợp lệ: {error}", pytrace=False)
    return data if isinstance(data, dict) else {}


def compact(value) -> str:
    text = re.sub(r"\s+", "", str(value or ""))
    return text[3:-2] if text.startswith("${{") and text.endswith("}}") else text


def triggers(doc: dict) -> dict:
    on = doc.get("on", doc.get(True))
    if isinstance(on, str):
        return {on: None}
    if isinstance(on, list):
        return {name: None for name in on}
    return on if isinstance(on, dict) else {}


def steps(job: dict) -> list[dict]:
    return [s for s in (job.get("steps") or []) if isinstance(s, dict)]


def action(step: dict) -> str:
    return str(step.get("uses", "")).split("@")[0]


def guarded(step: dict) -> bool:
    return testkit.act_skipped_locally(step.get("if"))


def has_write(permissions) -> bool:
    if permissions == "write-all":
        return True
    return isinstance(permissions, dict) and any(str(v) == "write" for v in permissions.values())


def timeout_ok(job: dict) -> bool:
    limit = job.get("timeout-minutes")
    return isinstance(limit, int) and 1 <= limit <= 30


def needs(job: dict) -> list:
    value = job.get("needs")
    return [value] if isinstance(value, str) else list(value or [])


def text_of(step: dict) -> str:
    return f"{step.get('run', '')}\n{json.dumps(step.get('env') or {})}"


def output_step(job: dict, key: str) -> tuple[str, str] | None:
    match = STEP_OUTPUT.search(str((job.get("outputs") or {}).get(key, "")))
    return (match.group(1), match.group(2)) if match else None


def trivy_input_problems(target: str, options: dict) -> list[str]:
    found = []
    extra = sorted(set(map(str, options)) - TRIVY_ACTION_INPUTS)
    if extra:
        found.append(f"trivy-action {target}: input {', '.join(extra)} không được dùng; chỉ được "
                     f"{', '.join(sorted(TRIVY_ACTION_INPUTS))}, chính sách chỉ đến từ container/trivy.yaml")
    if "format" in options and str(options["format"]) not in TRIVY_ACTION_FORMATS:
        found.append(f"trivy-action {target}: format chỉ được {', '.join(sorted(TRIVY_ACTION_FORMATS))} (sarif và SBOM "
                     f"đổi cách gate quyết định), đang là {options['format']}")
    if "scan-type" in options and str(options["scan-type"]) != "image":
        found.append(f"trivy-action {target}: scan-type phải là image")
    return found


def build_problems(job: dict) -> list[str]:
    found = []
    if "test" not in needs(job):
        found.append("Job build phải needs: test")
    if job.get("permissions") not in ({"contents": "read"}, {"contents": "read", "packages": "write"}):
        found.append(f"Job build chỉ được contents: read (thêm packages: write nếu đẩy GHCR), đang là {job.get('permissions')!r}")
    tag_ref = output_step(job, "tag")
    all_steps = steps(job)
    ids = {s.get("id"): i for i, s in enumerate(all_steps) if s.get("id")}
    if tag_ref is None or tag_ref[0] not in ids:
        found.append("Job build cần outputs.tag lấy từ steps.<id>.outputs.tag của một bước trong job")
        return found
    meta_id = tag_ref[0]
    meta = all_steps[ids[meta_id]]
    script = str(meta.get("run", ""))
    if "GITHUB_SHA" not in script and "github.sha" not in script:
        found.append(f"Bước {meta_id} phải tính tag từ GITHUB_SHA")
    if re.search(r"\bdate\b|run_number|run_id|run_attempt|latest", script):
        found.append(f"Bước {meta_id} không được dùng date, run_number, run_id, run_attempt hay latest cho tag")
    for needle in ("GITHUB_OUTPUT", "devops-ex-output tag=", "devops-ex-output revision="):
        if needle not in script:
            found.append(f"Bước {meta_id} phải có {needle}")
    tag_expr = f"steps.{meta_id}.outputs.tag"
    built_at, scanned_at = {}, {}
    for index, step in enumerate(all_steps):
        options = step.get("with") or {}
        if action(step) == "docker/build-push-action":
            target = str(options.get("target", ""))
            where = f"docker/build-push-action target {target or '(không có)'}"
            if not guarded(step):
                found.append(f"{where}: cần if: ${{{{ !env.ACT }}}}")
            if target not in TARGETS:
                found.append(f"{where}: target phải là api hoặc worker")
                continue
            built_at[target] = index
            if str(options.get("file", "")) != DOCKERFILE or str(options.get("context", "")) != ".":
                found.append(f"{where}: cần context: . và file: {DOCKERFILE}")
            if str(options.get("load", "")).lower() != "true" or str(options.get("push", "false")).lower() != "false":
                found.append(f"{where}: cần load: true và không push (push chỉ sau khi quét)")
            tags = str(options.get("tags", ""))
            if "env.REGISTRY" not in tags or tag_expr not in tags or f"/{target}:" not in tags or "latest" in tags:
                found.append(f"{where}: tags phải là ${{{{ env.REGISTRY }}}}/<tên>/{target}:${{{{ {tag_expr} }}}}, không latest")
            args = compact(options.get("build-args", ""))
            if f"APP_VERSION=${{{{{tag_expr}}}}}" not in args:
                found.append(f"{where}: build-args cần APP_VERSION=${{{{ {tag_expr} }}}}")
            if not re.search(r"GIT_COMMIT=\$\{\{(github\.sha|steps\.[\w-]+\.outputs\.revision)\}\}", args):
                found.append(f"{where}: build-args cần GIT_COMMIT=${{{{ github.sha }}}}")
        if action(step) == "aquasecurity/trivy-action":
            ref = str(options.get("image-ref", ""))
            target = next((t for t in TARGETS if f"/{t}:" in ref), None)
            if target is None or tag_expr not in ref:
                found.append(f"trivy-action: image-ref phải trỏ image api hoặc worker vừa build (dùng {tag_expr})")
                continue
            scanned_at[target] = index
            if not guarded(step):
                found.append(f"trivy-action {target}: cần if: ${{{{ !env.ACT }}}}")
            if str(options.get("trivy-config", "")) != "container/trivy.yaml":
                found.append(f"trivy-action {target}: cần trivy-config: container/trivy.yaml (cùng chính sách M03)")
            found += trivy_input_problems(target, options)
    for target in TARGETS:
        if target not in built_at:
            found.append(f"Thiếu bước docker/build-push-action target {target}")
        if target not in scanned_at:
            found.append(f"Thiếu bước aquasecurity/trivy-action quét image {target}")
        elif target in built_at and scanned_at[target] < built_at[target]:
            found.append(f"Bước quét {target} phải đứng sau bước build {target}")
    pushes = [i for i, s in enumerate(all_steps) if "docker push" in str(s.get("run", ""))]
    if not pushes:
        found.append("Thiếu bước run: docker push")
        return found
    for index in pushes:
        push = all_steps[index]
        name = push.get("name") or push.get("id") or f"bước {index + 1}"
        if not guarded(push) or "github.event_name=='push'" not in compact(push.get("if")):
            found.append(f"Bước docker push ({name}) cần if: ${{{{ !env.ACT && github.event_name == 'push' }}}} "
                         "(pull request không push)")
        script = str(push.get("run", ""))
        if "GITHUB_OUTPUT" not in script or "digest" not in script.lower() and "@sha256" not in script:
            found.append(f"Bước docker push ({name}) phải ghi tham chiếu <repo>@sha256:<digest> vào $GITHUB_OUTPUT")
    if min(pushes) < max(scanned_at.values(), default=len(all_steps)):
        found.append("docker push phải đứng sau mọi bước quét trivy: image chưa qua gate không lên registry")
    push_ids = {all_steps[i].get("id") for i in pushes} - {None}
    for key in ("api_image", "worker_image"):
        ref = output_step(job, key)
        if ref is None or ref[0] not in push_ids:
            found.append(f"Job build cần outputs.{key} lấy từ steps.<id của một bước docker push>.outputs.*")
    return found


def deploy_problems(job: dict) -> list[str]:
    found = []
    if "build" not in needs(job):
        found.append("Job deploy-staging phải needs: build")
    environment = job.get("environment")
    if (environment.get("name") if isinstance(environment, dict) else environment) != "staging":
        found.append("Job deploy-staging cần environment: staging")
    if "github.event_name=='push'" not in compact(job.get("if")):
        found.append("Job deploy-staging chỉ chạy khi push lên main: if: github.event_name == 'push'")
    concurrency = job.get("concurrency")
    group = concurrency.get("group") if isinstance(concurrency, dict) else concurrency
    cancel = concurrency.get("cancel-in-progress") if isinstance(concurrency, dict) else None
    if "staging" not in str(group or "") or cancel not in (None, False, "false"):
        found.append("Job deploy-staging cần concurrency group chứa staging và không cancel-in-progress (deploy dở bị huỷ "
                     "là staging nửa cũ nửa mới)")
    if job.get("permissions") != {"contents": "read"}:
        found.append(f"Job deploy-staging chỉ được permissions contents: read, đang là {job.get('permissions')!r}")
    all_steps = steps(job)
    deploy = next((i for i, s in enumerate(all_steps) if "docker compose" in str(s.get("run", ""))), None)
    if deploy is None:
        found.append("Thiếu bước run: docker compose ... up deploy staging")
    else:
        step = all_steps[deploy]
        run, env = str(step.get("run", "")), step.get("env") or {}
        if not guarded(step):
            found.append("Bước deploy cần if: ${{ !env.ACT }}")
        if COMPOSE not in run or not re.search(r"\bup\b", run) or "--wait" not in run:
            found.append(f"Bước deploy phải chạy docker compose -f {COMPOSE} ... up -d --wait")
        for var, key in (("OLIST_API_IMAGE", "api_image"), ("OLIST_WORKER_IMAGE", "worker_image")):
            if f"needs.build.outputs.{key}" not in compact(env.get(var)):
                found.append(f"Bước deploy cần env {var}: ${{{{ needs.build.outputs.{key} }}}} (image theo digest)")
        if "secrets." not in str(env.get("POSTGRES_PASSWORD", "")):
            found.append("Bước deploy lấy POSTGRES_PASSWORD từ secrets.*")
    smoke = next((i for i, s in enumerate(all_steps) if SMOKE in str(s.get("run", ""))), None)
    if smoke is None:
        found.append(f"Thiếu bước chạy {SMOKE} sau deploy")
    elif not guarded(all_steps[smoke]) or "needs.build.outputs.tag" not in compact(text_of(all_steps[smoke])) or (
            deploy is not None and smoke < deploy):
        found.append(f"Bước {SMOKE} cần if: ${{{{ !env.ACT }}}}, đứng sau bước deploy và nhận version needs.build.outputs.tag")
    return found


def setup_problems(test: dict) -> list[str]:
    reference = yaml.safe_load(MODULE07_STARTER.read_text(encoding="utf-8"))["jobs"]["test"]
    want = {s.get("name"): str(s.get("run", "")).strip() for s in steps(reference) if s.get("name") in SETUP_STEPS}
    have = {s.get("name"): str(s.get("run", "")).strip() for s in steps(test) if s.get("name") in SETUP_STEPS}
    found = [f"Job test phải giữ nguyên bước '{name}' của starter module 07 Basic 01 (cùng tên, cùng run:)"
             for name in SETUP_STEPS if have.get(name) != want[name]]
    env = test.get("env") if isinstance(test.get("env"), dict) else {}
    lacking = sorted(k for k, v in (reference.get("env") or {}).items() if str(env.get(k)) != str(v))
    if lacking:
        found.append(f"Job test phải có env của starter module 07 Basic 01 với đúng giá trị: {', '.join(lacking)}")
    return found


def structure_problems(doc: dict) -> list[str]:
    found = []
    on = triggers(doc)
    if set(map(str, on)) - {"push", "pull_request", "workflow_dispatch"}:
        found.append(f"Trigger chỉ được push, pull_request, workflow_dispatch; đang có {sorted(map(str, on))}")
    push = on.get("push") if isinstance(on.get("push"), dict) else {}
    if push.get("branches") != ["main"] or "pull_request" not in on:
        found.append("Trigger cần push với branches: [main] và pull_request")
    if doc.get("permissions") != {"contents": "read"}:
        found.append(f"permissions cấp workflow phải đúng bằng contents: read, đang là {doc.get('permissions')!r}")
    concurrency = doc.get("concurrency") if isinstance(doc.get("concurrency"), dict) else {}
    if "github.ref" not in str(concurrency.get("group", "")):
        found.append("concurrency cấp workflow cần group chứa github.ref")
    if compact(concurrency.get("cancel-in-progress")) != "github.event_name=='pull_request'":
        found.append("concurrency cấp workflow: cancel-in-progress phải đúng bằng ${{ github.event_name == 'pull_request' }} "
                     "(huỷ bản chạy cũ của PR, không bao giờ huỷ pipeline của main đang deploy)")
    if not isinstance(doc.get("env"), dict) or not doc["env"].get("REGISTRY"):
        found.append("Cần env cấp workflow REGISTRY (địa chỉ registry, vd. localhost:15000)")
    jobs = doc.get("jobs") if isinstance(doc.get("jobs"), dict) else {}
    for job_id, job in jobs.items():
        for step in steps(job) if isinstance(job, dict) else []:
            if step.get("uses") and not SHA_PIN.match(str(step["uses"])):
                found.append(f"Job {job_id}: {step['uses']} phải ghim theo commit SHA đủ 40 ký tự")
    for name in ("test", "build", "deploy-staging"):
        if not isinstance(jobs.get(name), dict):
            found.append(f"Thiếu job {name}")
        elif not timeout_ok(jobs[name]):
            found.append(f"Job {name} cần timeout-minutes từ 1 tới 30")
    test = jobs.get("test")
    if isinstance(test, dict):
        if has_write(test.get("permissions")):
            found.append("Job test không được có quyền write")
        found += setup_problems(test)
        if not any("pytest" in str(s.get("run", "")) for s in steps(test)):
            found.append("Job test thiếu bước run: chạy pytest")
    if isinstance(jobs.get("build"), dict):
        found += build_problems(jobs["build"])
    if isinstance(jobs.get("deploy-staging"), dict):
        found += deploy_problems(jobs["deploy-staging"])
    return found


def repo(dest: Path, project_root: Path, *, canary: bool = False) -> Path:
    assemble(dest, project_root, dotenv=False, extra={"requirements-dev.txt": FIXTURES / "repo" / "requirements-dev.txt"})
    if canary:
        (dest / "tests" / "test_devops_ex_canary.py").write_text(CANARY, encoding="utf-8")
    return dest


def run_workflow(dest: Path):
    result = testkit.act_run(dest, event="push", timeout=ACT_TIMEOUT)
    if testkit.act_failed_on_network(result, SETUP_STEPS):
        pytest.skip(f"Bước cài uv/Python lỗi vì mạng dù image runner {testkit.ACT_IMAGE} đã có sẵn uv, Python và wheel: "
                    "workflow tải thêm thứ không có trong image (đổi UV_VERSION, PYTHON_VERSION hay requirements).")
    return result


def tail(result) -> str:
    text = f"{result.stdout}\n{result.stderr}".strip()
    return "Output cuối của act:\n" + "\n".join(text.splitlines()[-40:])


def registry_digest(client: httpx.Client, ref: str) -> str:
    address, rest = ref.split("/", 1)
    name, tag = rest.rsplit(":", 1)
    accept = {"Accept": ", ".join(REGISTRY_MANIFEST_TYPES)}
    response = client.head(f"http://{address}/v2/{name}/manifests/{tag}", headers=accept)
    digest = response.headers.get("docker-content-digest", "")
    assert response.status_code == 200 and re.fullmatch(r"sha256:[0-9a-f]{64}", digest), (
        f"Registry không có {ref} (HTTP {response.status_code}, digest {digest!r})")
    return f"{address}/{name}@{digest}"


class Stub:
    """API giả chỉ có /healthz và /readyz để chấm smoke-test.sh không cần Docker."""

    def __init__(self, version: str, ready: bool = True, ready_after: float = 0.0) -> None:
        self.version, self.ready, self.ready_after = version, ready, ready_after
        self.started = time.monotonic()
        stub = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def do_GET(self):
                if self.path == "/healthz":
                    status, body = 200, {"status": "ok", "version": stub.version}
                elif self.path == "/readyz":
                    up = stub.ready and time.monotonic() - stub.started >= stub.ready_after
                    status, body = (200, {"db": "ok", "redis": "ok"}) if up else (503, {"db": "ok", "redis": "error"})
                else:
                    status, body = 404, {"error": "not found"}
                data = json.dumps(body).encode()
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.url = f"http://127.0.0.1:{self.server.server_address[1]}"

    def __enter__(self) -> "Stub":
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        return self

    def __exit__(self, *exc) -> None:
        self.server.shutdown()
        self.server.server_close()


def smoke(script: Path, tmp: Path, *args: str, timeout: str = "3") -> tuple[subprocess.CompletedProcess, float]:
    start = time.monotonic()
    result = run_sandboxed([BASH, script, *args], writable=[tmp], cwd=tmp, env={"SMOKE_TIMEOUT": timeout}, timeout=90)
    return result, time.monotonic() - start


def lines_of(result) -> list[str]:
    return f"{result.stdout}\n{result.stderr}".splitlines()


@pytest.fixture
def smoke_tools():
    if BASH is None:
        pytest.skip("Cần bash")
    Exercise.require_tool("curl", min_version="7.68")
    Exercise.require_tool("jq", min_version="1.6")


class Run:
    def __init__(self, result=None, error: str = "") -> None:
        self.result, self.error = result, error

    def require(self):
        if self.error:
            pytest.fail(self.error, pytrace=False)
        return self.result


def pipeline(project_root: Path, dest: Path, *, canary: bool = False) -> Run:
    workflow = project_root / WORKFLOW
    if not workflow.is_file():
        return Run(error=missing(workflow, DOC))
    try:
        return Run(run_workflow(repo(dest, project_root, canary=canary)))
    except pytest.fail.Exception as error:
        return Run(error=str(error))


@pytest.fixture(scope="module")
def green(project_root, tmp_path_factory):
    return pipeline(project_root, tmp_path_factory.mktemp("green"))


@pytest.fixture(scope="module")
def red(project_root, tmp_path_factory):
    return pipeline(project_root, tmp_path_factory.mktemp("red"), canary=True)


def test_m04_workflow_structure(project_root):
    found = structure_problems(load(require_file(project_root / WORKFLOW)))
    assert not found, "\n".join(found)


def test_m04_checks_catch_defective_workflow():
    found = "\n".join(structure_problems(load(FIXTURES / "defective" / "ci.yml")))
    for needle in ("cancel-in-progress phải đúng", "REGISTRY", "40 ký tự", "needs: test", "load: true", "không latest",
                   "GIT_COMMIT", "trivy-action quét image worker", "Bước quét api phải đứng sau", "docker push phải đứng sau",
                   "environment: staging", "không cancel-in-progress", "needs.build.outputs.api_image", "secrets.*",
                   SMOKE, "giữ nguyên bước 'Cài uv'", "env của starter", "chính sách chỉ đến từ"):
        assert needle in found, found


PER_TARGET_PUSH = """
needs: test
permissions: {contents: read}
outputs:
  tag: ${{ steps.meta.outputs.tag }}
  api_image: ${{ steps.push-api.outputs.ref }}
  worker_image: ${{ steps.push-worker.outputs.ref }}
steps:
  - id: meta
    run: |
      echo "tag=sha-${GITHUB_SHA::12}" >> "$GITHUB_OUTPUT"
      echo "devops-ex-output tag=sha-${GITHUB_SHA::12}"
      echo "devops-ex-output revision=${GITHUB_SHA}"
""" + "".join(f"""
  - uses: docker/build-push-action@c3c9e263c25d99ce0380d002d59b67737d91b0dc
    if: ${{{{ !env.ACT }}}}
    with:
      context: .
      file: container/Dockerfile
      target: {t}
      load: true
      tags: ${{{{ env.REGISTRY }}}}/olist-shop/{t}:${{{{ steps.meta.outputs.tag }}}}
      build-args: |
        APP_VERSION=${{{{ steps.meta.outputs.tag }}}}
        GIT_COMMIT=${{{{ github.sha }}}}
  - uses: aquasecurity/trivy-action@ed142fd0673e97e23eac54620cfb913e5ce36c25
    if: ${{{{ !env.ACT }}}}
    with:
      image-ref: ${{{{ env.REGISTRY }}}}/olist-shop/{t}:${{{{ steps.meta.outputs.tag }}}}
      trivy-config: container/trivy.yaml
""" for t in TARGETS) + "".join(f"""
  - id: push-{t}
    if: ${{{{ !env.ACT && github.event_name == 'push' }}}}
    run: |
      docker push "$REGISTRY/olist-shop/{t}:$TAG"
      echo "ref=$(docker image inspect --format '{{{{index .RepoDigests 0}}}}' "$REGISTRY/olist-shop/{t}:$TAG")" >> "$GITHUB_OUTPUT"
""" for t in TARGETS)


@pytest.mark.parametrize("options,needle", [
    ({"scanners": "secret"}, "scanners"),
    ({"pkg-types": "os"}, "pkg-types"),
    ({"ignore-policy": "policy.rego"}, "ignore-policy"),
    ({"severity": "CRITICAL"}, "severity"),
    ({"format": "sarif"}, "format chỉ được"),
    ({"format": "cyclonedx"}, "format chỉ được"),
    ({"scan-type": "fs"}, "scan-type"),
])
def test_m04_trivy_action_inputs_allowlist(options, needle):
    base = {"image-ref": "r/api:t", "trivy-config": "container/trivy.yaml", "version": "v0.76.1"}
    assert trivy_input_problems("api", base) == []
    assert trivy_input_problems("api", {**base, "format": "json", "output": "trivy.json"}) == []
    assert any(needle in p for p in trivy_input_problems("api", {**base, **options}))


def test_m04_push_step_per_target_accepted():
    job = yaml.safe_load(PER_TARGET_PUSH)
    assert build_problems(job) == []
    job["steps"][-1]["if"] = "${{ !env.ACT }}"
    assert any("push-worker" in p for p in build_problems(job))


def test_m04_actionlint(project_root, tmp_path):
    workflow = require_file(project_root / WORKFLOW)
    Exercise.require_tool("actionlint", "1.7")
    target = tmp_path / WORKFLOW
    target.parent.mkdir(parents=True)
    shutil.copyfile(workflow, target)
    result = run_sandboxed(["actionlint", "-no-color", "-shellcheck=", "-pyflakes=", WORKFLOW], writable=[tmp_path],
                           cwd=tmp_path, env={}, timeout=60)
    assert result.returncode == 0, f"actionlint báo lỗi:\n{result.stdout}{result.stderr}"


def test_m04_green_pipeline(green):
    green = green.require()
    jobs = testkit.act_job_results(green)
    for name in ("test", "build", "deploy-staging"):
        assert jobs.get(name) is True, f"Job {name} phải xanh trên code đúng, nhận {jobs}. {tail(green)}"
    outputs = testkit.act_outputs(green).get("build", {})
    tag, revision = outputs.get("tag", ""), outputs.get("revision", "")
    assert re.fullmatch(r"[0-9a-f]{40}", revision), f"Job build phải in 'devops-ex-output revision=<GITHUB_SHA>', nhận {outputs}"
    assert tag == f"sha-{revision[:12]}", f"Tag phải là sha-<12 ký tự đầu của commit {revision}>, nhận {tag!r}"


def test_m04_red_test_blocks_pipeline(red):
    red = red.require()
    jobs = testkit.act_job_results(red)
    assert jobs.get("test") is False, f"Harness cài một test đỏ mà job test không fail. {tail(red)}"
    for name in ("build", "deploy-staging"):
        assert jobs.get(name) is not True, f"Job {name} vẫn chạy dù job test fail"
    assert "tag" not in testkit.act_outputs(red).get("build", {}), "Job build vẫn tính tag dù job test fail"


@pytest.mark.parametrize("args", [(), ("http://127.0.0.1:1",), ("a", "b", "c"), ("", "sha-3f9c2a1b7d10"),
                                  ("http://127.0.0.1:1", "")])
def test_m04_smoke_usage(project_root, tmp_path, smoke_tools, args):
    result, _ = smoke(require_file(project_root / SMOKE), tmp_path, *args)
    assert result.returncode == 2 and result.stderr.startswith("Usage:"), (
        f"Sai số tham số phải exit 2 và stderr bắt đầu bằng Usage:, nhận {result.returncode}\n{result.stderr}")


def test_m04_smoke_passes_on_expected_version(project_root, tmp_path, smoke_tools):
    script = require_file(project_root / SMOKE)
    with Stub("sha-3f9c2a1b7d10", ready_after=2) as stub:
        result, _ = smoke(script, tmp_path, stub.url, "sha-3f9c2a1b7d10", timeout="20")
    assert result.returncode == 0, f"API trả đúng version và sẵn sàng sau 2 giây: phải exit 0\n{result.stdout}{result.stderr}"
    assert any(line.startswith("OK") for line in lines_of(result)), "Thành công phải in một dòng bắt đầu bằng OK"


@pytest.mark.parametrize("case", ["wrong-version", "not-ready", "unreachable"])
def test_m04_smoke_fails(project_root, tmp_path, smoke_tools, case):
    script = require_file(project_root / SMOKE)
    if case == "unreachable":
        result, waited = smoke(script, tmp_path, f"http://127.0.0.1:{free_port()}", "sha-3f9c2a1b7d10")
        clue = ""
    else:
        with Stub("sha-000000000000" if case == "wrong-version" else "sha-3f9c2a1b7d10", ready=case != "not-ready") as stub:
            result, waited = smoke(script, tmp_path, stub.url, "sha-3f9c2a1b7d10")
        clue = "sha-000000000000" if case == "wrong-version" else "readyz"
    assert result.returncode == 1, f"{case}: phải exit 1, nhận {result.returncode}\n{result.stdout}{result.stderr}"
    assert waited < 3 + 20, f"{case}: SMOKE_TIMEOUT=3 mà script chạy {waited:.0f} giây"
    fails = [line for line in lines_of(result) if line.startswith("FAIL")]
    assert fails and clue in fails[-1], f"{case}: dòng FAIL cuối phải nêu {clue or 'lý do'}, nhận {fails}"


def test_m04_shellcheck_smoke(project_root):
    script = require_file(project_root / SMOKE)
    Exercise.require_tool("shellcheck", min_version="0.9.0")
    try:
        result = subprocess.run(["shellcheck", "--norc", "-S", "style", str(script)], capture_output=True, text=True,
                                timeout=60)
    except subprocess.TimeoutExpired:
        pytest.fail("shellcheck chạy quá 60 giây với smoke-test.sh", pytrace=False)
    assert result.returncode == 0, result.stdout


def test_m04_staging_deploy_by_digest(green, project_root, tmp_path, smoke_tools):
    green = green.require()
    outputs = testkit.act_outputs(green).get("build", {})
    tag, revision = outputs.get("tag", ""), outputs.get("revision", "")
    if not SHA_TAG.fullmatch(tag):
        pytest.fail(f"Workflow chưa in tag hợp lệ (devops-ex-output tag=sha-<12 hex>), nhận {tag!r}")
    for rel in (DOCKERFILE, COMPOSE, SMOKE):
        require_file(project_root / rel)
    Exercise.require_registry()
    root = repo(tmp_path / "repo", project_root)
    with DockerLab() as lab:
        images = build_targets(lab, root, {"APP_VERSION": tag, "GIT_COMMIT": revision})
        with httpx.Client(trust_env=False, timeout=10) as client:
            pinned = {t: registry_digest(client, lab.push(images[t], t, tag=tag)) for t in TARGETS}
        for target in TARGETS:
            labels = lab.image_inspect(pinned[target])["Config"].get("Labels") or {}
            assert labels.get("org.opencontainers.image.revision") == revision, (
                f"Image {target} theo digest phải mang nhãn revision {revision}, nhận {labels}")
        project = lab.compose(root / COMPOSE, timeout=180, env={
            "OLIST_API_IMAGE": pinned["api"], "OLIST_WORKER_IMAGE": pinned["worker"],
            "POSTGRES_PASSWORD": secrets.token_hex(12)})
        url = f"http://127.0.0.1:{project.port('api', 8000)}"
        script = root / SMOKE
        result, _ = smoke(script, tmp_path, url, tag, timeout="60")
        assert result.returncode == 0, f"smoke-test.sh trên staging (version {tag}) phải exit 0:\n{result.stdout}{result.stderr}"
        wrong, _ = smoke(script, tmp_path, url, "sha-000000000000", timeout="3")
        assert wrong.returncode == 1, f"smoke-test.sh với version sai phải exit 1, nhận {wrong.returncode}"
        assert httpx.get(url + "/healthz", timeout=10).json().get("version") == tag

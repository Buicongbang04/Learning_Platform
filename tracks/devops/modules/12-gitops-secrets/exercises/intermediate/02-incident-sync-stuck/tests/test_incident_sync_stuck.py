import json
import shutil
import time

import pytest
import yaml

from testkit import KUBE_IMAGES, KUBECTL_MIN_VERSION, Exercise, KubeLab, run_sandboxed

ex = Exercise(__file__)
APP = "olist-shop"
INCIDENT = ex.fixtures / "incident"
PHASES = {"PreSync": 0, "Sync": 1, "PostSync": 2}
HOOK = "argocd.argoproj.io/hook"
WAVE = "argocd.argoproj.io/sync-wave"
DELETE_POLICY = "argocd.argoproj.io/hook-delete-policy"
HEALTHZ = ("import json, urllib.request; "
           "print(json.load(urllib.request.urlopen('http://127.0.0.1:8000/healthz', timeout=5))['version'])")


def render(path, tmp_path) -> list[dict]:
    ex.require_tool("kubectl", KUBECTL_MIN_VERSION)
    result = run_sandboxed(["kubectl", "kustomize", str(path)], writable=[tmp_path], cwd=tmp_path, env={}, readonly=[path])
    assert result.returncode == 0, f"kubectl kustomize lỗi:\n{result.stderr[-1500:]}"
    return [d for d in yaml.safe_load_all(result.stdout) if d]


def find(docs, kind: str, name: str) -> dict:
    found = [d for d in docs if d["kind"] == kind and d["metadata"]["name"] == name]
    assert found, f"Không thấy {kind} {name} trong manifest đã render"
    return found[0]


def order(doc: dict) -> tuple[int, int]:
    annotations = doc["metadata"].get("annotations") or {}
    phase = annotations.get(HOOK, "Sync").split(",")[0].strip()
    return PHASES.get(phase, 1), int(annotations.get(WAVE, "0"))


def application(path) -> dict:
    docs = [d for d in yaml.safe_load_all(path.read_text(encoding="utf-8")) if d]
    assert len(docs) == 1 and docs[0].get("kind") == "Application", "application.yaml chứa đúng một Application"
    return docs[0]


def bump_version(repo) -> None:
    path = repo / "shop" / "kustomization.yaml"
    kustomization = yaml.safe_load(path.read_text(encoding="utf-8"))
    generators = [g for g in kustomization.get("configMapGenerator") or [] if g.get("name") == "olist-config"]
    literals = generators[0]["literals"] if generators else []
    if "APP_VERSION=1.0" not in literals:
        raise ValueError("Giữ configMapGenerator olist-config có literal APP_VERSION=1.0 (test đẩy commit đổi sang 1.1)")
    literals[literals.index("APP_VERSION=1.0")] = "APP_VERSION=1.1"
    path.write_text(yaml.safe_dump(kustomization, sort_keys=False), encoding="utf-8")


def start(lab, tmp, source, app_file):
    repo = tmp / "repo"
    shutil.copytree(source, repo)
    project = lab.argocd_project()
    lab.gitops_repo(repo)
    text = json.dumps(application(app_file))
    for placeholder, value in (("LAB_REPO_URL", lab.repo_url), ("LAB_NAMESPACE", lab.namespace), ("LAB_PROJECT", project)):
        text = text.replace(placeholder, value)
    manifest = tmp / "application.json"
    manifest.write_text(text, encoding="utf-8")
    lab.apply_learner(manifest)
    return repo


def app_status(lab) -> dict:
    result = lab.kubectl("get", "applications.argoproj.io", APP, "-o", "json", check=False)
    return (json.loads(result.stdout).get("status") or {}) if result.returncode == 0 else {}


def hook_result(status: dict) -> list[dict]:
    resources = ((status.get("operationState") or {}).get("syncResult") or {}).get("resources") or []
    return [r for r in resources if r.get("kind") == "Job" and r.get("name") == "migrate"]


def migrate_broken(lab) -> str:
    job = json.loads(lab.kubectl("get", "job", "migrate", "-o", "json", check=False).stdout or "{}")
    if (job.get("status") or {}).get("failed", 0) >= 1:
        return "Failed"
    pods = json.loads(lab.kubectl("get", "pods", "-l", "job-name=migrate", "-o", "json", check=False).stdout or "{}")
    for pod in pods.get("items") or []:
        for container in (pod.get("status") or {}).get("containerStatuses") or []:
            reason = ((container.get("state") or {}).get("waiting") or {}).get("reason", "")
            if reason and reason not in ("ContainerCreating", "PodInitializing"):
                return reason
    return ""


def version(lab) -> str:
    lab.kubectl("rollout", "status", "deployment/api", "--timeout=120s", check=False, timeout=150)
    result = lab.kubectl("exec", "deployment/api", "-c", "api", "--", "python", "-c", HEALTHZ, check=False)
    return result.stdout.strip() if result.returncode == 0 else f"exec lỗi: {result.stderr.strip()[-300:]}"


@pytest.fixture(scope="module")
def fixed(tmp_path_factory):
    ex.require_cluster()
    ex.require_argocd()
    ex.require_kind_images(KUBE_IMAGES["olist"], KUBE_IMAGES["postgres"], KUBE_IMAGES["redis"])
    tmp = tmp_path_factory.mktemp("fixed")
    state: dict = {}
    try:
        quick = bool(order_problems(render(ex.path("gitops/shop"), tmp)))
    except AssertionError:
        quick = True
    with KubeLab() as lab:
        repo = start(lab, tmp, ex.path("gitops"), ex.path("application.yaml"))
        started = time.monotonic()
        try:
            state["first"] = lab.argocd_wait(APP, timeout=60 if quick else 240)
            state["seconds"] = time.monotonic() - started
            state["first_revision"] = lab.gitops_revision
            bump_version(repo)
            lab.gitops_repo(repo)
            state["second"] = lab.argocd_wait(APP, timeout=240)
            state["version"] = version(lab)
        except (pytest.fail.Exception, ValueError) as error:
            state["error"] = str(error)
        yield lab, state


@pytest.fixture(scope="module")
def incident(tmp_path_factory):
    ex.require_cluster()
    ex.require_argocd()
    ex.require_kind_images(KUBE_IMAGES["olist"], KUBE_IMAGES["postgres"], KUBE_IMAGES["redis"])
    tmp = tmp_path_factory.mktemp("incident")
    state: dict = {}
    with KubeLab() as lab:
        repo = start(lab, tmp, INCIDENT / "gitops", INCIDENT / "application.yaml")
        state["first_revision"] = lab.gitops_revision
        deadline = time.monotonic() + 90
        broken = ""
        while time.monotonic() < deadline:
            status = app_status(lab)
            broken = migrate_broken(lab)
            if (status.get("operationState") or {}).get("phase") == "Running" and broken:
                break
            time.sleep(3)
        state["stuck"] = app_status(lab)
        state["migrate"] = broken
        bump_version(repo)
        lab.gitops_repo(repo)
        time.sleep(25)
        state["after_commit"] = app_status(lab)
        state["api"] = lab.kubectl("get", "deployment", "api", "--ignore-not-found", "-o", "name").stdout.strip()
        yield lab, state


def order_problems(docs) -> list[str]:
    postgres, migrate, api = find(docs, "Deployment", "postgres"), find(docs, "Job", "migrate"), find(docs, "Deployment", "api")
    found = []
    if HOOK not in (migrate["metadata"].get("annotations") or {}):
        found.append("migrate vẫn là hook của ArgoCD (chạy lại mỗi lần sync)")
    if not order(postgres) < order(migrate):
        found.append(f"migrate (phase, wave) {order(migrate)} phải chạy sau postgres {order(postgres)}: lúc migrate chạy, "
                     "postgres phải đã có")
    if not order(migrate) < order(api):
        found.append(f"api {order(api)} chỉ được tạo sau khi migrate {order(migrate)} xong")
    return found


def test_migration_runs_after_database_before_api(tmp_path):
    problems = order_problems(render(ex.path("gitops/shop"), tmp_path))
    assert not problems, "\n".join(problems)


def test_migration_fails_fast_and_reruns(tmp_path):
    migrate = find(render(ex.path("gitops/shop"), tmp_path), "Job", "migrate")
    spec = migrate["spec"]
    assert spec.get("backoffLimit") is not None and spec["backoffLimit"] <= 2, "backoffLimit tối đa 2 (mặc định 6, kéo hơn 6 phút)"
    deadline = spec.get("activeDeadlineSeconds")
    assert deadline is not None and 0 < deadline <= 300, "activeDeadlineSeconds tối đa 300 để hook hỏng thì sync fail, không treo"
    policies = (migrate["metadata"].get("annotations") or {}).get(DELETE_POLICY, "")
    assert "BeforeHookCreation" in policies, "Job hook tên cố định cần BeforeHookCreation để lần sync sau tạo lại được"


def test_application_retries_bounded():
    retry = (application(ex.path("application.yaml"))["spec"].get("syncPolicy") or {}).get("retry") or {}
    assert 1 <= int(retry.get("limit", 0)) <= 5, "syncPolicy.retry.limit từ 1 tới 5: sync lỗi được thử lại, nhưng có giới hạn"
    assert (retry.get("backoff") or {}).get("duration"), "retry.backoff.duration"


def test_fresh_namespace_syncs(fixed):
    _, state = fixed
    assert isinstance(state.get("first"), dict), f"Namespace trống chưa sync được: {state.get('error')}"
    hooks = hook_result(state["first"])
    assert hooks and all(h.get("hookPhase") == "Succeeded" for h in hooks), f"Hook migrate phải Succeeded: {hooks}"


def test_next_commit_deploys(fixed):
    _, state = fixed
    assert isinstance(state.get("second"), dict), f"Commit tiếp theo chưa được sync: {state.get('error')}"
    assert state["second"]["sync"]["revision"] != state["first_revision"]
    assert state.get("version") == "1.1", f"/healthz sau commit thứ hai: {state.get('version')}"


def test_incident_reproduces_symptoms(incident):
    _, state = incident
    operation = state["stuck"].get("operationState") or {}
    assert operation.get("phase") == "Running" and "migrate" in (operation.get("message") or ""), \
        f"Bản lúc sự cố phải kẹt ở hook migrate (triệu chứng 1): {operation.get('phase')}: {operation.get('message')}"
    assert state["migrate"], "Pod migrate phải lỗi hay kẹt (triệu chứng 2)"
    after = state["after_commit"].get("operationState") or {}
    assert after.get("phase") == "Running" and (after.get("operation") or {}).get("sync", {}).get("revision") == state["first_revision"], \
        "Commit mới không được sync khi thao tác cũ còn kẹt (triệu chứng 3)"
    assert state["api"] == "", "Lúc sự cố chưa có Deployment api"

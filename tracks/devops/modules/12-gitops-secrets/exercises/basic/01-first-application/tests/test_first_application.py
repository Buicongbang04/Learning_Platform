import json
import shutil
import time

import pytest
import yaml

from testkit import KUBE_IMAGES, KUBECTL_MIN_VERSION, Exercise, KubeLab, run_sandboxed

ex = Exercise(__file__)
APP = "olist-shop"
IN_CLUSTER = "https://kubernetes.default.svc"
HEALTHZ = ("import json, urllib.request; "
           "print(json.load(urllib.request.urlopen('http://127.0.0.1:8000/healthz', timeout=5))['version'])")


def application() -> dict:
    docs = [d for d in yaml.safe_load_all(ex.read("application.yaml")) if d]
    assert len(docs) == 1 and isinstance(docs[0], dict), "application.yaml chứa đúng một object Application"
    return docs[0]


def spec_problems(app: dict) -> list[str]:
    found = []
    spec = app.get("spec") or {}
    source = spec.get("source") or {}
    destination = spec.get("destination") or {}
    automated = (spec.get("syncPolicy") or {}).get("automated")
    if app.get("kind") != "Application" or app.get("apiVersion") != "argoproj.io/v1alpha1":
        found.append("Cần apiVersion argoproj.io/v1alpha1, kind Application")
    if (app.get("metadata") or {}).get("name") != APP:
        found.append(f"metadata.name phải là {APP}")
    if spec.get("project") != "LAB_PROJECT":
        found.append("spec.project giữ placeholder LAB_PROJECT (test thay bằng AppProject của lab)")
    if source.get("repoURL") != "LAB_REPO_URL":
        found.append("spec.source.repoURL giữ placeholder LAB_REPO_URL")
    if source.get("targetRevision") not in ("main", "HEAD"):
        found.append("spec.source.targetRevision theo nhánh main")
    if source.get("path") != "shop":
        found.append(f"spec.source.path phải trỏ thư mục Kustomize của Olist Shop trong repo (shop), đang là {source.get('path')!r}")
    if "plugin" in source or "helm" in source:
        found.append("Bài này dùng Kustomize thuần của ArgoCD, không plugin hay Helm")
    if destination != {"server": IN_CLUSTER, "namespace": "LAB_NAMESPACE"}:
        found.append(f"spec.destination phải là server {IN_CLUSTER}, namespace LAB_NAMESPACE")
    if not isinstance(automated, dict):
        found.append("Chưa bật sync tự động (spec.syncPolicy.automated)")
    else:
        if automated.get("prune") is not True:
            found.append("Chưa bật prune: object bị xoá khỏi Git sẽ còn mãi trên cluster")
        if automated.get("selfHeal") is not True:
            found.append("Chưa bật selfHeal: sửa tay trên cluster sẽ không bị đưa về trạng thái của Git")
    return found


def render(path, tmp_path) -> list[dict]:
    ex.require_tool("kubectl", KUBECTL_MIN_VERSION)
    result = run_sandboxed(["kubectl", "kustomize", str(path)], writable=[tmp_path], cwd=tmp_path, env={}, readonly=[path])
    assert result.returncode == 0, f"kubectl kustomize {path.name} lỗi:\n{result.stderr[-1500:]}"
    return [d for d in yaml.safe_load_all(result.stdout) if d]


def second_commit(repo) -> None:
    path = repo / "shop" / "kustomization.yaml"
    kustomization = yaml.safe_load(path.read_text(encoding="utf-8"))
    resources = kustomization.get("resources") or []
    generators = [g for g in kustomization.get("configMapGenerator") or [] if g.get("name") == "olist-config"]
    if "legacy-flags.yaml" not in resources or not generators or "APP_VERSION=1.0" not in (generators[0].get("literals") or []):
        raise ValueError("kustomization.yaml cần resources có legacy-flags.yaml và configMapGenerator olist-config có literal "
                         "APP_VERSION=1.0 để test đóng vai đồng nghiệp sửa ở commit thứ hai")
    resources.remove("legacy-flags.yaml")
    literals = generators[0]["literals"]
    literals[literals.index("APP_VERSION=1.0")] = "APP_VERSION=1.1"
    path.write_text(yaml.safe_dump(kustomization, sort_keys=False), encoding="utf-8")
    (repo / "shop" / "legacy-flags.yaml").unlink()


def wait_app(lab, state: dict, key: str, timeout: float = 180) -> bool:
    try:
        state[key] = lab.argocd_wait(APP, timeout=timeout)
        return True
    except pytest.fail.Exception as error:
        state[key] = str(error)
        return False


def version(lab) -> str:
    rollout = lab.kubectl("rollout", "status", "deployment/api", "--timeout=120s", check=False, timeout=150)
    if rollout.returncode != 0:
        return f"rollout lỗi: {rollout.stderr.strip()[-300:]}"
    result = lab.kubectl("exec", "deployment/api", "-c", "api", "--", "python", "-c", HEALTHZ, check=False)
    return result.stdout.strip() if result.returncode == 0 else f"exec lỗi: {result.stderr.strip()[-300:]}"


def replicas(lab) -> int | None:
    result = lab.kubectl("get", "deployment", "api", "-o", "jsonpath={.spec.replicas}", check=False)
    return int(result.stdout) if result.returncode == 0 and result.stdout.strip().isdigit() else None


@pytest.fixture(scope="module")
def synced(tmp_path_factory):
    ex.require_cluster()
    ex.require_argocd()
    ex.require_kind_images(KUBE_IMAGES["olist"], KUBE_IMAGES["redis"])
    app = application()
    problems = spec_problems(app)
    tmp = tmp_path_factory.mktemp("gitops")
    repo = tmp / "repo"
    shutil.copytree(ex.path("gitops"), repo)
    state: dict = {"problems": problems}
    with KubeLab() as lab:
        project = lab.argocd_project()
        lab.gitops_repo(repo)
        text = json.dumps(app)
        for placeholder, value in (("LAB_REPO_URL", lab.repo_url), ("LAB_NAMESPACE", lab.namespace), ("LAB_PROJECT", project)):
            text = text.replace(placeholder, value)
        manifest = tmp / "application.json"
        manifest.write_text(text, encoding="utf-8")
        try:
            state["applied"] = lab.apply_learner(manifest, check=False)
        except pytest.fail.Exception as error:
            state["applied"] = str(error)
        if problems or not hasattr(state["applied"], "returncode") or state["applied"].returncode != 0:
            yield lab, state
            return
        if wait_app(lab, state, "first"):
            state["version1"] = version(lab)
            state["first_revision"] = lab.gitops_revision
            try:
                second_commit(repo)
            except ValueError as error:
                state["second"] = str(error)
            else:
                lab.gitops_repo(repo)
                if wait_app(lab, state, "second"):
                    state["version2"] = version(lab)
                    state["legacy"] = lab.kubectl("get", "configmap", "legacy-flags", "--ignore-not-found", "-o", "name").stdout.strip()
                    desired = replicas(lab)
                    state["desired"] = desired
                    lab.kubectl("scale", "deployment/api", f"--replicas={(desired or 1) + 2}")
                    deadline = time.monotonic() + 90
                    healed = None
                    while time.monotonic() < deadline:
                        healed = replicas(lab)
                        if healed == desired:
                            break
                        time.sleep(3)
                    state["healed"] = healed
        yield lab, state


def test_application_spec():
    problems = spec_problems(application())
    assert not problems, "\n".join(problems)


def test_kustomization_renders(tmp_path):
    docs = render(ex.path("gitops/shop"), tmp_path)
    kinds = {(d["kind"], d["metadata"]["name"]) for d in docs}
    for wanted in (("Deployment", "api"), ("Deployment", "redis"), ("Service", "api"), ("Service", "redis"),
                   ("ConfigMap", "legacy-flags")):
        assert wanted in kinds, f"Kustomize phải render {wanted[0]} {wanted[1]}"
    config = [d for d in docs if d["kind"] == "ConfigMap" and d["metadata"]["name"].startswith("olist-config-")]
    assert config, "configMapGenerator olist-config (tên có hậu tố hash để đổi config là rollout)"
    assert config[0]["data"].get("APP_VERSION") == "1.0"
    for doc in docs:
        assert not doc["metadata"].get("namespace"), "Không ghi namespace trong manifest: ArgoCD đặt theo destination"
        for container in (doc.get("spec", {}).get("template", {}).get("spec", {}).get("containers") or []):
            assert container["image"] in (KUBE_IMAGES["olist"], KUBE_IMAGES["redis"]), \
                f"Dùng đúng image đã nạp vào cluster: {container['image']}"


def test_first_sync_healthy(synced):
    _, state = synced
    assert not state["problems"], "Application chưa đúng, test không chờ sync:\n" + "\n".join(state["problems"])
    applied = state["applied"]
    assert hasattr(applied, "returncode") and applied.returncode == 0, f"Không apply được Application: {str(applied)[-1500:]}"
    assert isinstance(state.get("first"), dict), state.get("first")


def test_api_serves_version_from_git(synced):
    _, state = synced
    assert state.get("version1") == "1.0", f"/healthz của api sau sync đầu: {state.get('version1')}"


def test_new_commit_reconciled_and_pruned(synced):
    _, state = synced
    assert isinstance(state.get("second"), dict), f"Commit thứ hai chưa được sync: {state.get('second')}"
    assert state["second"]["sync"]["revision"] != state["first_revision"]
    assert state.get("version2") == "1.1", f"api phải rollout theo config mới trong Git: {state.get('version2')}"
    assert state.get("legacy") == "", "ConfigMap legacy-flags đã bị xoá khỏi Git mà vẫn còn trên cluster (prune)"


def test_drift_self_healed(synced):
    _, state = synced
    assert "desired" in state, "Chưa tới bước thử drift (các bước trước chưa đạt)"
    assert state.get("healed") == state["desired"], \
        f"kubectl scale tay lên {(state['desired'] or 1) + 2} mà sau 90 giây replicas vẫn là {state.get('healed')} (self-heal)"

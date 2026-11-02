import json
import re
import subprocess

import pytest
import yaml

from testkit import HELM_MIN_VERSION, KUBE_IMAGES, Exercise, KubeLab, run_sandboxed

ex = Exercise(__file__)
DEPS = ex.fixtures / "deps.yaml"
RELEASE = "shop"
FULLNAME = "shop-olist-api"
PASSWORD = "olist-k8s-lab"


def helm_offline(tmp_path, *args):
    ex.require_tool("helm", HELM_MIN_VERSION)
    home = tmp_path / "home"
    home.mkdir(exist_ok=True)
    env = {"HELM_CACHE_HOME": str(home / "cache"), "HELM_CONFIG_HOME": str(home / "config"),
           "HELM_DATA_HOME": str(home / "data"), "KUBECONFIG": "/dev/null"}
    return run_sandboxed(["helm", *args], writable=[home], readonly=[ex.path("olist-api")], cwd=home, env=env, timeout=60)


def render(tmp_path, *args) -> list[dict]:
    result = helm_offline(tmp_path, "template", RELEASE, str(ex.path("olist-api")), *args)
    assert result.returncode == 0, f"helm template lỗi:\n{result.stderr[-1500:]}"
    return [doc for doc in yaml.safe_load_all(result.stdout) if doc]


def find(docs, kind, name=FULLNAME):
    found = [d for d in docs if d["kind"] == kind and d["metadata"]["name"] == name]
    assert found, f"helm template không có {kind} {name}; có {[(d['kind'], d['metadata']['name']) for d in docs]}"
    return found[0]


def is_test_hook(doc) -> bool:
    return (doc["metadata"].get("annotations") or {}).get("helm.sh/hook") == "test"


def test_lint_strict(tmp_path):
    result = helm_offline(tmp_path, "lint", "--strict", str(ex.path("olist-api")))
    assert result.returncode == 0, result.stdout[-1500:] + result.stderr[-500:]


def test_default_render_objects_and_names(tmp_path):
    docs = [d for d in render(tmp_path) if not is_test_hook(d)]
    kinds = sorted((d["kind"], d["metadata"]["name"]) for d in docs)
    assert kinds == [("ConfigMap", FULLNAME), ("Deployment", FULLNAME), ("Service", FULLNAME)], kinds


def test_standard_labels_and_stable_selector(tmp_path):
    docs = render(tmp_path)
    for doc in docs:
        labels = doc["metadata"].get("labels") or {}
        for key, value in (("app.kubernetes.io/name", "olist-api"), ("app.kubernetes.io/instance", RELEASE),
                           ("app.kubernetes.io/managed-by", "Helm"), ("helm.sh/chart", "olist-api-0.1.0")):
            assert labels.get(key) == value, f"{doc['kind']} {doc['metadata']['name']}: nhãn {key} phải là {value}"
    selector = {"app.kubernetes.io/name": "olist-api", "app.kubernetes.io/instance": RELEASE}
    deployment = find(docs, "Deployment")
    assert deployment["spec"]["selector"]["matchLabels"] == selector, "selector chỉ gồm name và instance (selector bất biến)"
    assert find(docs, "Service")["spec"]["selector"] == selector


def test_values_drive_render(tmp_path):
    docs = render(tmp_path, "--set", "replicaCount=3", "--set", "image.tag=1.1")
    deployment = find(docs, "Deployment")
    assert deployment["spec"]["replicas"] == 3, "replicas lấy từ values.replicaCount"
    images = [c["image"] for c in deployment["spec"]["template"]["spec"]["containers"]]
    assert images == ["devops-track/olist-shop:1.1"], images
    default = find(render(tmp_path), "Deployment")
    assert [c["image"] for c in default["spec"]["template"]["spec"]["containers"]] == ["devops-track/olist-shop:1.0"], \
        "Mặc định dùng appVersion 1.0 làm tag"


def test_config_change_rolls_pods(tmp_path):
    before = find(render(tmp_path), "Deployment")["spec"]["template"]["metadata"].get("annotations") or {}
    docs = render(tmp_path, "--set", "config.logLevel=DEBUG")
    after = find(docs, "Deployment")["spec"]["template"]["metadata"].get("annotations") or {}
    assert find(docs, "ConfigMap")["data"].get("LOG_LEVEL") == "DEBUG"
    assert before.get("checksum/config") and before.get("checksum/config") != after.get("checksum/config"), \
        "Pod template cần annotation checksum/config đổi theo nội dung ConfigMap"


def test_secret_not_rendered_and_probes(tmp_path):
    docs = render(tmp_path)
    assert PASSWORD not in json.dumps(docs), "Mật khẩu không được nằm trong chart; lấy DATABASE_URL từ Secret có sẵn"
    container = find(docs, "Deployment")["spec"]["template"]["spec"]["containers"][0]
    refs = [e["valueFrom"]["secretKeyRef"] for e in container.get("env") or [] if "secretKeyRef" in (e.get("valueFrom") or {})]
    assert {"name": "olist-db", "key": "DATABASE_URL"} in refs, "DATABASE_URL lấy từ secretKeyRef olist-db/DATABASE_URL"
    assert (container.get("readinessProbe") or {}).get("httpGet", {}).get("path") == "/readyz"
    assert (container.get("livenessProbe") or {}).get("httpGet", {}).get("path") == "/healthz"


def restricted_gaps(docs) -> list[str]:
    gaps = []
    for doc in docs:
        spec = doc["spec"]["template"]["spec"] if doc["kind"] == "Deployment" else doc.get("spec", {})
        if "containers" not in spec:
            continue
        pod = spec.get("securityContext") or {}
        name = f"{doc['kind']} {doc['metadata']['name']}"
        if pod.get("runAsNonRoot") is not True:
            gaps.append(f"{name}: runAsNonRoot")
        if (pod.get("seccompProfile") or {}).get("type") != "RuntimeDefault":
            gaps.append(f"{name}: seccompProfile")
        for container in spec["containers"]:
            context = container.get("securityContext") or {}
            if context.get("allowPrivilegeEscalation") is not False:
                gaps.append(f"{name}, container {container['name']}: allowPrivilegeEscalation: false")
            if (context.get("capabilities") or {}).get("drop") != ["ALL"]:
                gaps.append(f"{name}, container {container['name']}: capabilities.drop [ALL]")
    return gaps


def test_restricted_security_context(tmp_path):
    gaps = restricted_gaps(render(tmp_path))
    assert not gaps, "Chưa đạt Pod Security restricted:\n" + "\n".join(gaps)


def test_has_helm_test_hook(tmp_path):
    hooks = [d for d in render(tmp_path) if is_test_hook(d)]
    assert hooks and all(d["kind"] == "Pod" for d in hooks), "Cần một Pod có annotation helm.sh/hook: test"
    assert any(f"{FULLNAME}:8000/readyz" in json.dumps(d) for d in hooks), "Pod test gọi /readyz qua Service của release"


@pytest.fixture(scope="module")
def installed(tmp_path_factory):
    ex.require_cluster()
    ex.require_tool("helm", HELM_MIN_VERSION)
    ex.require_kind_images(KUBE_IMAGES["olist"], KUBE_IMAGES["postgres"], KUBE_IMAGES["redis"])
    with KubeLab(pod_security="restricted") as lab:
        lab.apply_learner(DEPS)
        for target in ("deployment/postgres", "deployment/redis"):
            lab.kubectl("rollout", "status", target, "--timeout=180s")
        chart = ex.path("olist-api")
        rendered = helm_offline(tmp_path_factory.mktemp("render"), "template", RELEASE, str(chart))
        gaps = restricted_gaps([d for d in yaml.safe_load_all(rendered.stdout) if d]) if rendered.returncode == 0 else ["helm template lỗi"]
        if gaps:
            state = {"install": subprocess.CompletedProcess([], 1, "", "Không cài (khỏi chờ hết giờ): chart chưa render được hay pod chưa "
                                                                       "đạt restricted:\n" + "\n".join(gaps))}
        else:
            try:
                state = {"install": lab.helm_install(RELEASE, chart, "--wait", "--timeout", "120s", check=False)}
            except pytest.fail.Exception as error:
                state = {"install": subprocess.CompletedProcess([], 1, "", str(error))}
        state["test"] = lab.helm("test", RELEASE, "--timeout", "120s", check=False) if state["install"].returncode == 0 else None
        yield lab, chart, state


def test_installs_in_restricted_namespace(installed):
    lab, _, state = installed
    assert state["install"].returncode == 0, state["install"].stderr[-1500:]
    ready = lab.kubectl("get", "deployment", FULLNAME, "-o", "jsonpath={.status.readyReplicas}").stdout
    assert ready == "2", f"Deployment {FULLNAME} cần 2 pod ready, đang {ready or 0}"


def test_helm_test_passes(installed):
    _, _, state = installed
    assert state["test"] is not None, "Chưa cài được release nên không chạy helm test"
    assert state["test"].returncode == 0, state["test"].stdout[-1000:] + state["test"].stderr[-1000:]
    assert re.search(r"Phase:\s+Succeeded", state["test"].stdout), state["test"].stdout[-1000:]


def checksum(lab) -> str:
    deployment = json.loads(lab.kubectl("get", "deployment", FULLNAME, "-o", "json").stdout)
    return (deployment["spec"]["template"]["metadata"].get("annotations") or {}).get("checksum/config", "")


def test_upgrade_then_rollback(installed):
    lab, chart, state = installed
    assert state["install"].returncode == 0, "Chưa cài được release"
    first = checksum(lab)
    lab.helm_install(RELEASE, chart, "--set", "config.logLevel=DEBUG", "--wait", "--timeout", "180s")
    assert lab.kubectl("get", "configmap", FULLNAME, "-o", "jsonpath={.data.LOG_LEVEL}").stdout == "DEBUG"
    assert checksum(lab) != first, "Đổi cấu hình phải đổi pod template để Deployment rollout"
    lab.helm("rollback", RELEASE, "1", "--wait", "--timeout", "180s")
    history = json.loads(lab.helm("history", RELEASE, "-o", "json").stdout)
    assert [h["revision"] for h in history] == [1, 2, 3] and history[-1]["status"] == "deployed", history
    assert lab.kubectl("get", "configmap", FULLNAME, "-o", "jsonpath={.data.LOG_LEVEL}").stdout == "INFO"
    assert checksum(lab) == first, "Rollback về revision 1 đưa pod template về đúng bản đầu"
    lab.kubectl("rollout", "status", f"deployment/{FULLNAME}", "--timeout=180s")

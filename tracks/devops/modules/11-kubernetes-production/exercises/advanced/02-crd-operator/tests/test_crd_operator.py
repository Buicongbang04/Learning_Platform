import json
import shutil
import subprocess
import time

import pytest
import yaml

from testkit import KUBE_IMAGES, Exercise, KubeLab

ex = Exercise(__file__)
PLACEHOLDER = "lab.olist.test"
OPERATOR_SA = "storefront-operator"
WAIT = 90


def get_json(lab, *args):
    result = lab.kubectl("get", *args, "-o", "json", check=False)
    return json.loads(result.stdout) if result.returncode == 0 and result.stdout.strip() else None


def stage(lab, tmp_path):
    staged = tmp_path / "work"
    shutil.copytree(ex.path("operator"), staged / "operator", ignore=shutil.ignore_patterns("__pycache__"))
    for path in (staged / "operator").iterdir():
        path.write_text(path.read_text(encoding="utf-8").replace(PLACEHOLDER, lab.api_group), encoding="utf-8")
    docs = [d for d in yaml.safe_load_all(ex.read("crd.yaml").replace(PLACEHOLDER, lab.api_group)) if d]
    for doc in docs:
        doc.setdefault("metadata", {}).setdefault("labels", {})["devops-ex"] = lab.id
    (staged / "crd.json").write_text(json.dumps({"apiVersion": "v1", "kind": "List", "items": docs}), encoding="utf-8")
    return staged


def storefront(lab, name: str, replicas, message, **extra) -> dict:
    return {"apiVersion": f"{lab.api_group}/v1", "kind": "Storefront", "metadata": {"name": name},
            "spec": {"replicas": replicas, "message": message, **extra}}


def wait_for(check, timeout: float = WAIT):
    deadline = time.monotonic() + timeout
    value = check()
    while not value and time.monotonic() < deadline:
        time.sleep(3)
        value = check()
    return value


def apply(lab, path):
    try:
        return lab.apply_learner(path, check=False)
    except pytest.fail.Exception as error:
        return subprocess.CompletedProcess([], 1, "", str(error))


@pytest.fixture(scope="module")
def operator(tmp_path_factory):
    ex.require_cluster()
    ex.require_kind_images(KUBE_IMAGES["olist"], KUBE_IMAGES["nginx"])
    with KubeLab(allow=("CustomResourceDefinition",)) as lab:
        staged = stage(lab, tmp_path_factory.mktemp("crd"))
        state = {"crd": apply(lab, staged / "crd.json")}
        if state["crd"].returncode == 0:
            lab.kubectl("wait", "--for=condition=Established", f"crd/storefronts.{lab.api_group}", "--timeout=60s")
            wait_for(lambda: lab.kubectl("get", "storefronts", check=False).returncode == 0, 30)
        state["operator"] = apply(lab, staged / "operator")
        if state["operator"].returncode == 0:
            state["rollout"] = lab.kubectl("rollout", "status", "deployment/storefront-operator", "--timeout=120s",
                                           check=False, timeout=150)
        yield lab, state


def test_crd_and_operator_apply(operator):
    _, state = operator
    assert state["crd"].returncode == 0, state["crd"].stderr[-1500:]
    assert state["operator"].returncode == 0, state["operator"].stderr[-1500:]
    assert state["rollout"].returncode == 0, state["rollout"].stdout[-500:]


@pytest.mark.parametrize("spec,needle", [
    ({"replicas": 0, "message": "Olist"}, "replicas"),
    ({"replicas": 6, "message": "Olist"}, "replicas"),
    ({"replicas": "two", "message": "Olist"}, "replicas"),
    ({"replicas": 1, "message": ""}, "message"),
    ({"replicas": 1, "message": "x" * 81}, "message"),
    ({"replicas": 1}, "message"),
    ({"replicas": 2, "message": "Olist", "maintenance": True}, "maintenance"),
])
def test_schema_rejects_bad_specs(operator, spec, needle):
    lab, state = operator
    assert state["crd"].returncode == 0, "Chưa tạo được CRD"
    doc = {"apiVersion": f"{lab.api_group}/v1", "kind": "Storefront", "metadata": {"name": "bad"}, "spec": spec}
    result = lab.kubectl("apply", "--dry-run=server", "-f", "-", input=json.dumps(doc), check=False)
    assert result.returncode != 0 and needle in result.stderr, f"API server phải từ chối {spec}: {result.stderr[-300:]}"


def test_schema_accepts_and_defaults(operator):
    lab, state = operator
    assert state["crd"].returncode == 0, "Chưa tạo được CRD"
    result = lab.kubectl("apply", "--dry-run=server", "-o", "json", "-f", "-",
                         input=json.dumps(storefront(lab, "ok", 1, "Olist", maintenance=True)), check=False)
    assert result.returncode == 0, result.stderr[-300:]
    result = lab.kubectl("apply", "--dry-run=server", "-o", "json", "-f", "-", input=json.dumps(storefront(lab, "ok", 2, "Olist")),
                         check=False)
    assert result.returncode == 0 and json.loads(result.stdout)["spec"].get("maintenance") is False, \
        "spec.maintenance mặc định false (default trong schema)"


@pytest.fixture(scope="module")
def reconciled(operator):
    lab, state = operator
    if state["crd"].returncode != 0 or state["operator"].returncode != 0:
        return lab, None
    created = lab.kubectl("apply", "-f", "-", input=json.dumps(storefront(lab, "spring-sale", 2, "Olist Spring Sale")), check=False)
    if created.returncode != 0:
        return lab, None
    found = wait_for(lambda: (get_json(lab, "deployment", "spring-sale-web") or {}).get("status", {}).get("readyReplicas") == 2)
    return lab, found


def test_operator_creates_owned_workload(reconciled):
    lab, found = reconciled
    assert found, "Operator chưa tạo Deployment spring-sale-web với 2 pod ready sau 90 giây"
    deployment = get_json(lab, "deployment", "spring-sale-web")
    sf = get_json(lab, "storefront", "spring-sale")
    owners = deployment["metadata"].get("ownerReferences") or []
    assert any(o["kind"] == "Storefront" and o["uid"] == sf["metadata"]["uid"] and o.get("controller") for o in owners), \
        "Deployment cần ownerReference (controller: true) trỏ về Storefront"
    page = lab.kubectl("exec", "deployment/spring-sale-web", "--", "wget", "-qO-", "http://127.0.0.1/", check=False)
    assert "Olist Spring Sale" in page.stdout, page.stdout + page.stderr[-200:]


def test_status_and_printer_columns(reconciled):
    lab, found = reconciled
    assert found, "Operator chưa chạy được"
    ok = wait_for(lambda: (get_json(lab, "storefront", "spring-sale") or {}).get("status", {}).get("phase") == "Ready")
    sf = get_json(lab, "storefront", "spring-sale")
    assert ok and sf["status"].get("readyReplicas") == 2, f"status: {sf.get('status')}"
    assert sf["status"].get("observedGeneration") == sf["metadata"]["generation"]
    table = lab.kubectl("get", "storefronts").stdout.splitlines()[0].split()
    assert table[:5] == ["NAME", "REPLICAS", "READY", "PHASE", "AGE"], table


def test_spec_change_is_reconciled(reconciled):
    lab, found = reconciled
    assert found, "Operator chưa chạy được"
    lab.kubectl("patch", "storefront", "spring-sale", "--type=merge", "-p",
                json.dumps({"spec": {"replicas": 3, "message": "Olist Flash Sale"}}))
    scaled = wait_for(lambda: (get_json(lab, "deployment", "spring-sale-web") or {}).get("spec", {}).get("replicas") == 3)
    assert scaled, "Đổi spec.replicas thì Deployment phải theo"
    content = wait_for(lambda: "Olist Flash Sale" in json.dumps((get_json(lab, "configmap", "spring-sale-web") or {}).get("data")))
    assert content, "Đổi spec.message thì nội dung trang phải theo"
    ready = wait_for(lambda: (get_json(lab, "storefront", "spring-sale") or {}).get("status", {}).get("readyReplicas") == 3)
    assert ready, "status.readyReplicas phải lên 3"


def test_drift_is_repaired(reconciled):
    lab, found = reconciled
    assert found, "Operator chưa chạy được"
    lab.kubectl("delete", "deployment", "spring-sale-web", "--wait=true")
    assert wait_for(lambda: get_json(lab, "deployment", "spring-sale-web") is not None), \
        "Xoá tay Deployment thì operator phải tạo lại (reconcile theo trạng thái, không theo sự kiện)"


def test_delete_cascades(reconciled):
    lab, found = reconciled
    assert found, "Operator chưa chạy được"
    lab.kubectl("delete", "storefront", "spring-sale", "--wait=true")
    gone = wait_for(lambda: get_json(lab, "deployment", "spring-sale-web") is None and get_json(lab, "configmap", "spring-sale-web") is None)
    assert gone, "Xoá Storefront thì garbage collector xoá Deployment và ConfigMap con (ownerReferences)"


def test_operator_rbac_is_namespaced_and_narrow(operator):
    lab, _ = operator
    sa = {"serviceaccount": OPERATOR_SA}
    assert lab.can_i("list", f"storefronts.{lab.api_group}", **sa)
    assert lab.can_i("patch", f"storefronts.{lab.api_group}", subresource="status", **sa)
    assert lab.can_i("patch", "deployments.apps", **sa)
    assert not lab.can_i("list", f"storefronts.{lab.api_group}", all_namespaces=True, **sa), "Operator chỉ xem namespace của nó"
    assert not lab.can_i("get", "secrets", **sa)
    assert not lab.can_i("create", "pods", **sa), "Operator tạo Deployment, không tạo pod trực tiếp"
    assert not lab.can_i("delete", f"storefronts.{lab.api_group}", **sa), "Operator không xoá tài nguyên của người dùng"

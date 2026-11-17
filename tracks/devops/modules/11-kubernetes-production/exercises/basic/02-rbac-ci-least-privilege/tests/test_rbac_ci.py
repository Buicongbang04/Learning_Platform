import json
import subprocess
import time

import pytest

from testkit import Exercise, KubeLab

ex = Exercise(__file__)
CI = "ci-deployer"
CI_ALLOWED = [
    ("get", "deployments.apps"), ("list", "deployments.apps"), ("watch", "deployments.apps"), ("create", "deployments.apps"),
    ("patch", "deployments.apps"), ("update", "deployments.apps"), ("list", "replicasets.apps"), ("watch", "replicasets.apps"),
    ("create", "services"), ("patch", "services"), ("create", "configmaps"), ("patch", "configmaps"), ("list", "pods"),
    ("watch", "pods"), ("list", "events"),
]
CI_DENIED = [
    ("get", "secrets"), ("list", "secrets"), ("watch", "secrets"), ("delete", "deployments.apps"),
    ("deletecollection", "deployments.apps"), ("delete", "pods"), ("create", "pods"), ("delete", "services"),
    ("delete", "configmaps"), ("create", "rolebindings.rbac.authorization.k8s.io"), ("patch", "roles.rbac.authorization.k8s.io"),
    ("create", "serviceaccounts"), ("patch", "replicasets.apps"), ("create", "jobs.batch"), ("create", "cronjobs.batch"),
]


@pytest.fixture(scope="module")
def lab():
    ex.require_cluster()
    with KubeLab() as lab:
        try:
            applied = lab.apply_learner(ex.path("k8s"), check=False)
        except pytest.fail.Exception as error:
            applied = subprocess.CompletedProcess([], 1, "", str(error))
        deadline = time.monotonic() + 30
        while applied.returncode == 0 and time.monotonic() < deadline and not lab.can_i("get", "deployments.apps", serviceaccount=CI):
            time.sleep(1)
        yield lab, applied


def documents():
    import yaml

    return [d for f in sorted(ex.path("k8s").glob("*.yaml")) for d in yaml.safe_load_all(f.read_text(encoding="utf-8")) if d]


def test_manifests_apply(lab):
    _, applied = lab
    assert applied.returncode == 0, applied.stderr[-1500:]


def test_service_account_does_not_mount_token(lab):
    lab, _ = lab
    account = json.loads(lab.kubectl("get", "serviceaccount", CI, "-o", "json").stdout)
    assert account.get("automountServiceAccountToken") is False, "Pod không cần token của CI thì không mount (automountServiceAccountToken: false)"


@pytest.mark.parametrize("verb,resource", CI_ALLOWED)
def test_ci_can_deploy(lab, verb, resource):
    lab, _ = lab
    assert lab.can_i(verb, resource, serviceaccount=CI), f"{CI} cần quyền {verb} {resource} để deploy và theo dõi rollout"


def test_ci_can_read_logs(lab):
    lab, _ = lab
    assert lab.can_i("get", "pods", subresource="log", serviceaccount=CI), f"{CI} cần đọc log pod khi rollout lỗi"


@pytest.mark.parametrize("verb,resource", CI_DENIED)
def test_ci_least_privilege(lab, verb, resource):
    lab, _ = lab
    assert not lab.can_i(verb, resource, serviceaccount=CI), f"{CI} không được {verb} {resource}"


def test_ci_cannot_exec_or_leave_namespace(lab):
    lab, _ = lab
    assert not lab.can_i("create", "pods", subresource="exec", serviceaccount=CI), "CI không được exec vào pod"
    assert not lab.can_i("list", "deployments.apps", serviceaccount=CI, all_namespaces=True), "CI chỉ có quyền trong namespace của mình"


def test_role_has_no_wildcards():
    for doc in documents():
        if doc.get("kind") in ("Role", "ClusterRole"):
            for rule in doc.get("rules") or []:
                for field in ("apiGroups", "resources", "verbs"):
                    assert "*" not in (rule.get(field) or []), f"{doc['kind']} {doc['metadata']['name']}: không dùng '*' trong {field}"


def test_oncall_group_reads_but_cannot_change(lab):
    lab, _ = lab
    who = {"user": "an@olist.example", "groups": ("olist-oncall",)}
    assert lab.can_i("list", "pods", **who) and lab.can_i("get", "pods", subresource="log", **who)
    assert lab.can_i("list", "deployments.apps", **who)
    assert not lab.can_i("get", "secrets", **who), "Nhóm on-call không đọc Secret"
    assert not lab.can_i("patch", "deployments.apps", **who), "Nhóm on-call chỉ xem"
    assert not lab.can_i("create", "pods", subresource="exec", **who), "Nhóm on-call không exec"
    assert not lab.can_i("list", "pods", user="an@olist.example", groups=("other",)), "Quyền đi theo nhóm olist-oncall"


def test_lead_can_exec_only(lab):
    lab, _ = lab
    lead = {"user": "lead@olist.example"}
    assert lab.can_i("create", "pods", subresource="exec", **lead) and lab.can_i("get", "pods", **lead)
    assert not lab.can_i("get", "secrets", **lead)
    assert not lab.can_i("delete", "pods", **lead)
    assert not lab.can_i("patch", "deployments.apps", **lead)
    assert not lab.can_i("create", "pods", subresource="exec", user="other@olist.example"), "Chỉ lead@olist.example được exec"

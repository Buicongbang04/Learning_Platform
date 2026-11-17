import json
from pathlib import Path

import pytest

from testkit import KUBE_IMAGES, Exercise, KubeLab

ex = Exercise(__file__)
DEPS = Path(__file__).parent / "fixtures" / "deps.yaml"
BROKEN_DB = "DATABASE_URL=postgresql+psycopg://olist:olist-k8s-lab@postgres-khong-ton-tai:5432/olist"
VERSION = ("import json, urllib.request; "
           "print(json.load(urllib.request.urlopen('http://api:8000/healthz', timeout=5))['version'])")


def get_json(lab, *args):
    result = lab.kubectl("get", *args, "-o", "json", check=False)
    return json.loads(result.stdout) if result.returncode == 0 and result.stdout.strip() else None


def script(lab, name: str, *args: str, timeout: float = 240):
    return lab.run(["bash", str(ex.path(name)), *args], readonly=[ex.target], timeout=timeout)


def served_versions(lab) -> set[str]:
    seen = set()
    for _ in range(6):
        out = lab.kubectl("exec", "deployment/api", "--", "python", "-c", VERSION, check=False)
        seen.add(out.stdout.strip() if out.returncode == 0 else f"lỗi: {out.stderr.strip()[-200:]}")
    return seen


def active_replicasets(lab) -> dict[str, dict]:
    found = get_json(lab, "replicasets", "-l", "app.kubernetes.io/name=api") or {"items": []}
    return {rs["metadata"]["name"]: rs for rs in found["items"]}


def current_rs(lab) -> str | None:
    live = [name for name, rs in active_replicasets(lab).items() if rs["spec"].get("replicas", 0) > 0]
    return live[0] if len(live) == 1 else None


@pytest.fixture(scope="module")
def lab():
    ex.require_cluster()
    ex.require_kind_images(KUBE_IMAGES["olist"], KUBE_IMAGES["postgres"], KUBE_IMAGES["redis"])
    with KubeLab() as lab:
        lab.apply_learner(DEPS)
        lab.kubectl("rollout", "status", "deployment/postgres", "--timeout=180s")
        lab.kubectl("rollout", "status", "deployment/redis", "--timeout=180s")
        yield lab


@pytest.fixture(scope="module")
def history(lab):
    steps = {"apply": lab.apply_learner(ex.path("api.yaml"), check=False)}
    steps["first"] = lab.kubectl("rollout", "status", "deployment/api", "--timeout=180s", check=False)
    steps["rs_1.0"] = current_rs(lab) if steps["first"].returncode == 0 else None
    steps["release_ok"] = script(lab, "release.sh", "1.1")
    steps["versions_1.1"] = served_versions(lab)
    steps["rs_1.1"] = current_rs(lab) if steps["release_ok"].returncode == 0 else None
    steps["release_bad"] = script(lab, "release.sh", "1.2", BROKEN_DB)
    steps["after_bad"] = get_json(lab, "deployment", "api")
    steps["versions_bad"] = served_versions(lab)
    steps["rollback"] = script(lab, "rollback.sh")
    steps["versions_rollback"] = served_versions(lab)
    steps["rs_rollback"] = current_rs(lab) if steps["rollback"].returncode == 0 else None
    steps["history"] = lab.kubectl("rollout", "history", "deployment/api", check=False).stdout
    steps["rollback_to_1"] = script(lab, "rollback.sh", "1")
    steps["rs_revision_1"] = current_rs(lab) if steps["rollback_to_1"].returncode == 0 else None
    return steps


def test_strategy_keeps_capacity(lab, history):
    assert history["apply"].returncode == 0, history["apply"].stderr
    deployment = get_json(lab, "deployment", "api")
    spec = deployment["spec"]
    assert spec["replicas"] == 4
    rolling = spec["strategy"].get("rollingUpdate") or {}
    assert spec["strategy"]["type"] == "RollingUpdate" and str(rolling.get("maxUnavailable")) == "0", (
        "maxUnavailable phải là 0 để bản lỗi không lấy mất pod đang phục vụ")
    assert 3 <= spec.get("revisionHistoryLimit", 10) <= 10, "revisionHistoryLimit từ 3 tới 10"
    assert spec.get("progressDeadlineSeconds", 600) <= 90, "progressDeadlineSeconds tối đa 90 để bản lỗi bị phát hiện sớm"
    probe = spec["template"]["spec"]["containers"][0].get("readinessProbe") or {}
    assert (probe.get("httpGet") or {}).get("path") == "/readyz", "Không có readinessProbe thì rollout không biết bản mới lỗi"


def test_release_rolls_out_new_version(history):
    assert history["first"].returncode == 0, history["first"].stderr
    result = history["release_ok"]
    assert result.returncode == 0, f"release.sh 1.1 lỗi:\n{result.stdout[-600:]}{result.stderr[-600:]}"
    assert history["versions_1.1"] == {"1.1"}, f"Sau release 1.1 Service trả {history['versions_1.1']}"
    assert history["rs_1.1"] != history["rs_1.0"], "Đổi env phải tạo ReplicaSet mới"


def test_bad_release_fails_without_dropping_capacity(history):
    result = history["release_bad"]
    assert result.returncode != 0, "release.sh phải trả mã khác 0 khi rollout không xong"
    status = history["after_bad"]["status"]
    assert status.get("availableReplicas") == 4, f"Bản lỗi làm giảm pod đang phục vụ: {status}"
    assert history["versions_bad"] == {"1.1"}, f"Trong lúc bản 1.2 kẹt, Service phải vẫn trả 1.1: {history['versions_bad']}"
    template = history["after_bad"]["spec"]["template"]["spec"]["containers"][0]
    assert any(e.get("value") == "1.2" for e in template.get("env", [])), "release.sh không được tự rollback; để rollback.sh làm"


def test_rollback_restores_previous_replicaset(history):
    result = history["rollback"]
    assert result.returncode == 0, f"rollback.sh lỗi:\n{result.stdout[-600:]}{result.stderr[-600:]}"
    assert history["rs_1.1"] and history["rs_rollback"] == history["rs_1.1"], "rollout undo phải dùng lại ReplicaSet của bản 1.1, không tạo cái mới"
    assert history["versions_rollback"] == {"1.1"}


def test_history_has_change_cause(history):
    text = history["history"]
    for version in ("1.1", "1.2"):
        assert f"release {version}" in text, f"rollout history thiếu change-cause 'release {version}':\n{text}"


def test_rollback_to_explicit_revision(history):
    result = history["rollback_to_1"]
    assert result.returncode == 0, f"rollback.sh 1 lỗi:\n{result.stdout[-600:]}{result.stderr[-600:]}"
    assert history["rs_1.0"] and history["rs_revision_1"] == history["rs_1.0"], "rollback.sh 1 phải quay về ReplicaSet của revision 1 (bản 1.0)"

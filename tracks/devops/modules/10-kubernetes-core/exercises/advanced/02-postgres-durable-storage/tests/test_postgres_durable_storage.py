import json
import time
from pathlib import Path

import pytest

from testkit import KUBE_IMAGES, Exercise, KubeLab

ex = Exercise(__file__)
SECRET = Path(__file__).parent / "fixtures" / "secret.yaml"
NODE = "devops-lab-worker"
MARKER = "don-hang-2026-11-02"


def get_json(lab, *args):
    result = lab.kubectl("get", *args, "-o", "json", check=False)
    return json.loads(result.stdout) if result.returncode == 0 and result.stdout.strip() else None


def psql(lab, sql: str):
    return lab.kubectl("exec", "postgres-0", "-c", "postgres", "--", "psql", "-U", "olist", "-d", "olist", "-v", "ON_ERROR_STOP=1",
                       "-tAc", sql, check=False)


def wait_job(lab, name: str, timeout: float = 240) -> dict:
    deadline = time.monotonic() + timeout
    job = None
    started = time.monotonic()
    while time.monotonic() < deadline:
        job = get_json(lab, "job", name)
        if job is None and time.monotonic() - started > 15:
            break
        conditions = {c["type"]: c["status"] for c in (job or {}).get("status", {}).get("conditions", [])}
        if conditions.get("Complete") == "True" or conditions.get("Failed") == "True":
            break
        time.sleep(3)
    return job or {}


def complete(job: dict) -> bool:
    return any(c["type"] == "Complete" and c["status"] == "True" for c in job.get("status", {}).get("conditions", []))


@pytest.fixture(scope="module")
def run():
    ex.require_cluster()
    ex.require_kind_images(KUBE_IMAGES["postgres"])
    with KubeLab() as lab:
        volume = lab.admin_local_pv({"name": "pgdata", "capacity": "1Gi", "node": NODE, "storageClassName": "olist-local",
                                     "claim": "data-postgres-0"})
        lab.apply_learner(SECRET)
        state = {"volume": volume, "applied": lab.apply_learner(ex.path("k8s"), check=False)}
        state["rollout"] = lab.kubectl("rollout", "status", "statefulset/postgres", "--timeout=180s", check=False)
        state["pod_node"] = (get_json(lab, "pod", "postgres-0") or {}).get("spec", {}).get("nodeName")
        state["write"] = psql(lab, f"create table marker(id text primary key); insert into marker values ('{MARKER}')")
        uid = (get_json(lab, "pod", "postgres-0") or {}).get("metadata", {}).get("uid")
        lab.kubectl("delete", "pod", "postgres-0", "--wait=true", "--timeout=120s", check=False)
        lab.kubectl("wait", "--for=condition=Ready", "pod/postgres-0", "--timeout=180s", check=False)
        state["recreated"] = (get_json(lab, "pod", "postgres-0") or {}).get("metadata", {}).get("uid") != uid
        state["after_delete"] = psql(lab, "select id from marker")
        state["backup_create"] = lab.kubectl("create", "job", "pg-backup-now", "--from=cronjob/pg-backup", check=False)
        state["backup"] = wait_job(lab, "pg-backup-now")
        state["drop"] = psql(lab, "drop table marker")
        state["restore_apply"] = lab.apply_learner(ex.path("restore"), check=False)
        state["restore"] = wait_job(lab, "pg-restore")
        state["after_restore"] = psql(lab, "select id from marker")
        state["cronjob"] = get_json(lab, "cronjob", "pg-backup")
        state["pvc"] = get_json(lab, "pvc", "data-postgres-0")
        yield lab, state


def test_statefulset_binds_admin_volume(run):
    _, state = run
    assert state["applied"].returncode == 0, state["applied"].stderr
    assert state["rollout"].returncode == 0, state["rollout"].stdout[-300:] + state["rollout"].stderr[-300:]
    pvc = state["pvc"]
    assert pvc and pvc["status"].get("phase") == "Bound", "PVC data-postgres-0 phải Bound"
    assert pvc["spec"].get("volumeName") == state["volume"], (
        f"PVC data-postgres-0 phải bind vào PV {state['volume']} (StorageClass olist-local), không xin volume động")
    assert state["pod_node"] == NODE, f"Pod postgres-0 phải chạy trên {NODE}, nơi có ổ local"


def test_data_survives_pod_recreation(run):
    _, state = run
    assert state["write"].returncode == 0, state["write"].stderr
    assert state["recreated"], "Pod postgres-0 phải được tạo lại sau khi xoá"
    assert state["after_delete"].stdout.strip() == MARKER, "Dữ liệu phải còn sau khi pod bị tạo lại"


def test_backup_cronjob_is_safe(run):
    _, state = run
    cronjob = state["cronjob"]
    assert cronjob, "Cần CronJob pg-backup"
    spec = cronjob["spec"]
    assert spec.get("concurrencyPolicy") == "Forbid", "Hai lần pg_dump chồng nhau ghi cùng thư mục: Forbid"
    assert spec.get("startingDeadlineSeconds"), "Đặt startingDeadlineSeconds để lần lỡ lịch không chạy bù vô hạn"
    job_spec = spec["jobTemplate"]["spec"]
    assert job_spec.get("activeDeadlineSeconds"), "Job backup cần activeDeadlineSeconds"
    assert 0 < job_spec.get("backoffLimit", 6) <= 3
    text = json.dumps(job_spec)
    assert "olist-k8s-lab" not in text, "Mật khẩu lấy từ Secret olist-db"
    volumes = job_spec["template"]["spec"].get("volumes") or []
    assert any((v.get("persistentVolumeClaim") or {}).get("claimName") for v in volumes), "Bản dump ghi vào một PVC riêng"


def test_backup_and_restore_recover_dropped_table(run):
    lab, state = run
    assert state["backup_create"].returncode == 0, state["backup_create"].stderr
    assert complete(state["backup"]), f"Job backup chưa Complete: {state['backup'].get('status')}"
    assert state["drop"].returncode == 0
    assert state["restore_apply"].returncode == 0, state["restore_apply"].stderr
    assert complete(state["restore"]), (f"Job pg-restore chưa Complete: {state['restore'].get('status')}\n"
                                        + lab.kubectl("logs", "job/pg-restore", check=False).stdout[-600:])
    assert state["after_restore"].stdout.strip() == MARKER, "Restore phải đưa bảng đã xoá trở lại"

import json
import time
from datetime import datetime
from pathlib import Path

import pytest

from testkit import KUBE_IMAGES, Exercise, KubeLab

ex = Exercise(__file__)
FIXTURES = Path(__file__).parent / "fixtures"
PROBE = ("import json, urllib.request; r = urllib.request.urlopen('http://api/readyz', timeout=5); "
         "print(json.dumps({'status': r.status, 'served_by': r.headers.get('X-Served-By'), 'body': json.load(r)}))")


def get_json(lab, *args):
    result = lab.kubectl("get", *args, "-o", "json", check=False)
    return json.loads(result.stdout) if result.returncode == 0 and result.stdout.strip() else None


def when(value: str | None) -> datetime | None:
    return datetime.fromisoformat(value.replace("Z", "+00:00")) if value else None


def native_sidecars(pod_spec: dict) -> list[dict]:
    return [c for c in pod_spec.get("initContainers") or [] if c.get("restartPolicy") == "Always"]


def job_done(lab, name: str, timeout: float) -> dict | None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        job = get_json(lab, "job", name)
        conditions = {c["type"]: c["status"] for c in (job or {}).get("status", {}).get("conditions", [])}
        if conditions.get("Complete") == "True" or conditions.get("Failed") == "True":
            return job
        time.sleep(2)
    return get_json(lab, "job", name)


@pytest.fixture(scope="module")
def lab():
    ex.require_cluster()
    ex.require_kind_images(KUBE_IMAGES["olist"], KUBE_IMAGES["postgres"], KUBE_IMAGES["redis"], KUBE_IMAGES["nginx"])
    with KubeLab() as lab:
        lab.apply_learner(FIXTURES / "deps.yaml")
        lab.kubectl("rollout", "status", "deployment/postgres", "--timeout=180s")
        lab.kubectl("rollout", "status", "deployment/redis", "--timeout=180s")
        yield lab


@pytest.fixture(scope="module")
def deployed(lab):
    applied = lab.apply_learner(ex.path("k8s"), check=False)
    rollout = lab.kubectl("rollout", "status", "deployment/api", "--timeout=180s", check=False)
    job = get_json(lab, "job", "db-check")
    has_sidecar = bool(job and native_sidecars(job["spec"]["template"]["spec"]))
    return {"applied": applied, "rollout": rollout, "job": job_done(lab, "db-check", 150) if has_sidecar else job}


def api_pod(lab) -> dict:
    pods = get_json(lab, "pods", "-l", "app.kubernetes.io/name=api") or {"items": []}
    running = [p for p in pods["items"] if p["status"].get("phase") == "Running"]
    assert running, "Không có pod api nào Running"
    return running[0]


def test_api_rolls_out(deployed):
    assert deployed["applied"].returncode == 0, deployed["applied"].stderr
    assert deployed["rollout"].returncode == 0, deployed["rollout"].stdout[-400:] + deployed["rollout"].stderr[-400:]


def test_init_container_waits_for_postgres(lab, deployed):
    pod = api_pod(lab)
    plain = [c for c in pod["spec"].get("initContainers") or [] if c.get("restartPolicy") != "Always"]
    assert plain and plain[0]["name"] == "wait-db", "Init container đầu tiên của api tên wait-db"
    assert "postgres" in json.dumps(plain[0]), "wait-db phải chờ tới postgres"
    status = {s["name"]: s for s in pod["status"].get("initContainerStatuses") or []}
    finished = status.get("wait-db", {}).get("state", {}).get("terminated") or {}
    assert finished.get("exitCode") == 0, f"wait-db chưa kết thúc thành công: {status.get('wait-db')}"


def test_proxy_is_native_sidecar_started_before_api(lab, deployed):
    pod = api_pod(lab)
    sidecars = native_sidecars(pod["spec"])
    assert [c["name"] for c in sidecars] == ["proxy"], "proxy phải là native sidecar: initContainers kèm restartPolicy: Always"
    assert sidecars[0]["image"] == KUBE_IMAGES["nginx"]
    assert sidecars[0].get("startupProbe"), "Sidecar cần startupProbe để api chỉ khởi động khi proxy đã nghe"
    init = {s["name"]: s for s in pod["status"].get("initContainerStatuses") or []}
    main = {s["name"]: s for s in pod["status"].get("containerStatuses") or []}
    proxy_started = when((init.get("proxy", {}).get("state", {}).get("running") or {}).get("startedAt"))
    wait_done = when((init.get("wait-db", {}).get("state", {}).get("terminated") or {}).get("finishedAt"))
    api_started = when((main.get("api", {}).get("state", {}).get("running") or {}).get("startedAt"))
    assert proxy_started and wait_done and api_started, (init, main)
    assert wait_done <= proxy_started <= api_started, "Thứ tự phải là wait-db xong, rồi proxy, rồi api"
    assert init["proxy"].get("ready") is True


def test_service_goes_through_proxy(lab, deployed):
    service = get_json(lab, "service", "api")
    assert service and service["spec"]["ports"][0]["port"] == 80, "Service api nghe cổng 80"
    result = lab.kubectl("exec", api_pod(lab)["metadata"]["name"], "-c", "api", "--", "python", "-c", PROBE, check=False)
    assert result.returncode == 0, result.stderr[-500:]
    answer = json.loads(result.stdout)
    assert answer["status"] == 200 and answer["body"] == {"db": "ok", "redis": "ok"}
    assert answer["served_by"] == "olist-proxy", "Request qua Service phải đi qua sidecar proxy (header X-Served-By)"


def test_job_with_native_sidecar_completes(lab, deployed):
    job = deployed["job"]
    assert job, "Không có Job db-check"
    spec = job["spec"]["template"]["spec"]
    assert [c["name"] for c in native_sidecars(spec)] == ["pg-proxy"], "pg-proxy phải là native sidecar của Job"
    main = json.dumps(spec["containers"])
    assert "127.0.0.1" in main or "localhost" in main, "Container check kết nối Postgres qua sidecar ở 127.0.0.1"
    assert "olist-k8s-lab" not in main, "Mật khẩu lấy từ Secret olist-db"
    conditions = {c["type"]: c["status"] for c in job.get("status", {}).get("conditions", [])}
    assert conditions.get("Complete") == "True", f"Job db-check chưa Complete: {job.get('status')}"
    logs = lab.kubectl("logs", "job/db-check", "-c", "check", check=False).stdout
    assert "postgres 16" in logs, logs


def test_classic_sidecar_blocks_job_completion(lab):
    lab.apply_learner(FIXTURES / "classic-sidecar-job.yaml")
    deadline = time.monotonic() + 150
    finished = None
    while time.monotonic() < deadline and finished is None:
        pods = get_json(lab, "pods", "-l", "app.kubernetes.io/name=db-check-classic") or {"items": []}
        for pod in pods["items"]:
            status = {s["name"]: s for s in pod["status"].get("containerStatuses") or []}
            finished = (status.get("check", {}).get("state", {}).get("terminated") or {}) or None
        time.sleep(2)
    assert finished and finished.get("exitCode") == 0, "Container check của bản đối chứng phải chạy xong"
    time.sleep(15)
    job = get_json(lab, "job", "db-check-classic")
    conditions = {c["type"]: c["status"] for c in job.get("status", {}).get("conditions", [])}
    assert conditions.get("Complete") != "True", "Sidecar thường (containers) phải giữ Job không Complete"
    assert job["status"].get("active") == 1

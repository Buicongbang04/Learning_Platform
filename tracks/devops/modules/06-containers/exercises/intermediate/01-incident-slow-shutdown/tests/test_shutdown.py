import json
import shutil
from pathlib import Path

import pytest

from testkit import DockerLab, Exercise

ex = Exercise(__file__)
BASE = "python:3.12.16-slim-trixie"
FIXTURES = Path(__file__).parent / "fixtures"
FILES = ("Dockerfile", "entrypoint.sh", "worker.py")
GRACE = 10
CLEAN_STOP = 5
REGION = "us-east-1"
READY = "order-sync sẵn sàng"
SIGNALLED = "nhận tín hiệu, hoàn tất batch đang dở"
FINISHED = "đã ack batch cuối, dừng sạch"


def context(source: Path, dest: Path) -> Path:
    dest.mkdir(parents=True)
    for name in FILES:
        if (source / name).is_file():
            shutil.copy2(source / name, dest / name)
    return dest


def run_and_stop(lab: DockerLab, tag: str, alias: str) -> dict:
    lab.start(alias, tag, env={"REGION": REGION})
    lab.wait_log(alias, READY, timeout=60)
    seconds = lab.stop(alias, timeout=GRACE)
    return {"seconds": seconds, "state": lab.state(alias), "logs": lab.logs(alias)}


def worker_events(logs: str) -> list[dict]:
    events = []
    for line in logs.splitlines():
        try:
            event = json.loads(line)
        except ValueError:
            continue
        if isinstance(event, dict) and "msg" in event:
            events.append(event)
    return events


def worker_problems(logs: str) -> list[str]:
    events = worker_events(logs)
    messages = [e["msg"] for e in events]
    signalled = [e for e in events if e["msg"] == SIGNALLED]
    finished = [e for e in events if e["msg"] == FINISHED]
    if not signalled or signalled[0].get("signal") != "SIGTERM":
        return [f"Worker không tự log '{SIGNALLED}' với signal SIGTERM: chính worker không nhận được SIGTERM, batch đang dở "
                "không được ack"]
    if not finished or not isinstance(finished[0].get("batches"), int) or messages.index(FINISHED) < messages.index(SIGNALLED):
        return [f"Worker không log '{FINISHED}' sau khi nhận SIGTERM"]
    return []


def shutdown_problems(result: dict) -> list[str]:
    found = []
    tail = "\n".join(result["logs"].splitlines()[-8:])
    if result["seconds"] >= CLEAN_STOP:
        found.append(f"docker stop mất {result['seconds']:.1f} giây (grace period {GRACE} giây); phải dừng trong "
                     f"{CLEAN_STOP} giây")
    if result["state"]["ExitCode"] != 0:
        found.append(f"Container thoát với mã {result['state']['ExitCode']}, phải là 0 (dừng sạch)")
    found += worker_problems(result["logs"])
    if f"olist-orders-{REGION}" not in result["logs"]:
        found.append(f"Với REGION={REGION}, worker phải đọc queue olist-orders-{REGION} như trước khi sửa")
    return found + ([f"Log cuối:\n{tail}"] if found else [])


@pytest.fixture(scope="module")
def lab():
    ex.require_image(BASE)
    with DockerLab() as lab:
        yield lab


def test_worker_stops_cleanly(lab, tmp_path):
    source = ex.path("Dockerfile").parent
    tag = lab.build(context(source, tmp_path / "ctx"), "order-sync")
    found = shutdown_problems(run_and_stop(lab, tag, "order-sync"))
    assert not found, "\n".join(found)


def test_incident_build_reproduces_symptoms(lab, tmp_path):
    tag = lab.build(context(FIXTURES / "incident", tmp_path / "ctx"), "incident")
    result = run_and_stop(lab, tag, "incident")
    assert result["seconds"] >= GRACE - 2, result["seconds"]
    assert result["state"]["ExitCode"] == 137, result["state"]
    found = shutdown_problems(result)
    joined = "\n".join(found)
    assert "docker stop mất" in joined and "mã 137" in joined and "không nhận được SIGTERM" in joined, joined
    assert not any(line.startswith("Với REGION") for line in found), joined


def test_trap_in_shell_is_not_a_fix(lab, tmp_path):
    tag = lab.build(context(FIXTURES / "trap-only", tmp_path / "ctx"), "trap-only")
    result = run_and_stop(lab, tag, "trap-only")
    assert result["seconds"] < CLEAN_STOP and result["state"]["ExitCode"] == 0, result
    assert "dừng sạch" in result["logs"], result["logs"]
    found = shutdown_problems(result)
    assert any("không nhận được SIGTERM" in line for line in found), "\n".join(found)

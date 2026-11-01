import pytest

from testkit import AnsibleLab, Exercise

ex = Exercise(__file__)
HOSTS = ["worker-1", "worker-2", "worker-3"]
ROOT = "/opt/olist-shop"
OLD = f"{ROOT}/releases/1.4.2"
NEW = f"{ROOT}/releases/1.5.0"
FLAG = "/var/lib/olist-shop/maintenance"
BROKEN = "/etc/olist-shop/broken"
HEALTHCHECK = """#!/bin/sh
if [ -e /etc/olist-shop/broken ]; then echo "health: 503"; exit 1; fi
version=$(cat /opt/olist-shop/current/VERSION 2>/dev/null) || { echo "health: không đọc được VERSION"; exit 1; }
echo "health: ok $version"
"""
SEED = (f"cat > /usr/local/bin/olist-healthcheck <<'HC'\n{HEALTHCHECK}HC\n"
        f"chmod 0755 /usr/local/bin/olist-healthcheck && mkdir -p {OLD} /etc/olist-shop /var/lib/olist-shop && "
        f"echo 1.4.2 > {OLD}/VERSION && ln -sfn {OLD} {ROOT}/current")


def seed(lab: AnsibleLab) -> None:
    for host in HOSTS:
        result = lab.exec(host, "sh", "-c", SEED)
        assert result.returncode == 0, result.stderr
    assert lab.exec("worker-2", "touch", BROKEN).returncode == 0


def snapshot(lab: AnsibleLab) -> dict:
    return {host: {"current": lab.exec(host, "readlink", f"{ROOT}/current").stdout.strip(),
                   "flag": lab.stat(host, FLAG) is not None,
                   "new_release": lab.stat(host, NEW) is not None,
                   "version": (lab.read(host, f"{ROOT}/current/VERSION") or "").strip()} for host in HOSTS}


@pytest.fixture(scope="module")
def lab():
    with AnsibleLab(HOSTS) as lab:
        seed(lab)
        project = lab.stage(ex.target)
        runs = {"missing": lab.playbook("rollout.yml", inventory=["inventory"], cwd=project)}
        runs["after_missing"] = snapshot(lab)
        runs["broken"] = lab.playbook("rollout.yml", "-e", "olist_release=1.5.0", inventory=["inventory"], cwd=project)
        runs["after_broken"] = snapshot(lab)
        assert lab.exec("worker-2", "rm", "-f", BROKEN).returncode == 0
        runs["fixed"] = lab.playbook("rollout.yml", "-e", "olist_release=1.5.0", inventory=["inventory"], cwd=project)
        runs["after_fixed"] = snapshot(lab)
        runs["again"] = lab.playbook("rollout.yml", "-e", "olist_release=1.5.0", inventory=["inventory"], cwd=project)
        yield runs


def test_missing_release_touches_nothing(lab):
    assert lab["missing"].returncode != 0, "Thiếu -e olist_release thì playbook phải dừng"
    for host, state in lab["after_missing"].items():
        assert state == {"current": OLD, "flag": False, "new_release": False, "version": "1.4.2"}, f"{host}: {state}"


def test_first_host_upgraded(lab):
    state = lab["after_broken"]["worker-1"]
    assert state == {"current": NEW, "flag": False, "new_release": True, "version": "1.5.0"}, (
        f"worker-1 khoẻ: phải chạy 1.5.0 và đã về lại load balancer (không còn cờ maintenance): {state}")


def test_unhealthy_host_rolled_back_and_drained(lab):
    broken = lab["broken"]
    assert broken.returncode != 0, "Rollout gặp máy không khoẻ thì playbook phải kết thúc lỗi"
    state = lab["after_broken"]["worker-2"]
    assert state["current"] == OLD and state["version"] == "1.4.2", f"worker-2 phải rollback về 1.4.2: {state}"
    assert state["flag"], "worker-2 lỗi phải giữ cờ maintenance để load balancer không gửi traffic"
    fatal = [line for line in broken.output.splitlines() if line.startswith("fatal: [worker-2]")]
    assert fatal and "rollback" in fatal[-1].lower(), f"Thông báo dừng của worker-2 phải nói đã rollback: {fatal}"


def test_rollout_stops_before_next_host(lab):
    broken = lab["broken"]
    assert not broken.tasks(host="worker-3"), "Sau máy lỗi, rollout phải dừng: worker-3 không được chạy task nào"
    assert lab["after_broken"]["worker-3"] == {"current": OLD, "flag": False, "new_release": False, "version": "1.4.2"}


def test_one_host_at_a_time(lab):
    fixed = lab["fixed"]
    assert fixed.returncode == 0, fixed.tail()
    order = [event["host"] for event in fixed.tasks()]
    first_seen = {host: order.index(host) for host in HOSTS if host in order}
    last_seen = {host: len(order) - 1 - order[::-1].index(host) for host in HOSTS if host in order}
    assert sorted(first_seen) == HOSTS, f"Lần chạy sau khi sửa phải đi qua cả ba máy: {sorted(first_seen)}"
    assert last_seen["worker-1"] < first_seen["worker-2"] and last_seen["worker-2"] < first_seen["worker-3"], (
        "Mỗi đợt chỉ một máy theo thứ tự inventory (serial: 1)")


def test_all_upgraded_after_fix(lab):
    for host, state in lab["after_fixed"].items():
        assert state == {"current": NEW, "flag": False, "new_release": True, "version": "1.5.0"}, f"{host}: {state}"
    assert lab["fixed"].changed["worker-1"] == 0, "worker-1 đã ở 1.5.0: không được rút khỏi load balancer hay đổi gì"


def test_rerun_at_target_version_changes_nothing(lab):
    again = lab["again"]
    assert again.returncode == 0, again.tail()
    assert again.changed == {h: 0 for h in HOSTS}, again.changed

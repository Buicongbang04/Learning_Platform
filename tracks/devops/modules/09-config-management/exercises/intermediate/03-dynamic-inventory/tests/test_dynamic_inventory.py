import json
import re
import shutil
from pathlib import Path

import pytest

from testkit import AnsibleLab, Exercise, run_sandboxed

ex = Exercise(__file__)
FIXTURES = Path(__file__).parent / "fixtures"
PROD = sorted(["web-1", "web-2", "worker-1", "worker-2", "worker-3", "db-1"])


@pytest.fixture(scope="module")
def lab():
    with AnsibleLab() as lab:
        project = lab.root / "project"
        shutil.copytree(ex.target, project, ignore=shutil.ignore_patterns("__pycache__"))
        for name in ("cmdb.json", "cmdb-messy.json"):
            shutil.copy(FIXTURES / name, lab.root / name)
        yield lab, project


def inventory(lab, cmdb: str, *sources: str) -> dict:
    ansible, project = lab
    args = [arg for source in sources or ("inventory",) for arg in ("-i", source)]
    result = ansible.run("ansible-inventory", *args, "--list", cwd=project, env={"OLIST_CMDB_FILE": str(ansible.root / cmdb)})
    assert result.returncode == 0, f"ansible-inventory lỗi:\n{result.stderr}"
    assert "Unable to parse" not in result.stderr and "Failed to parse" not in result.stderr, result.stderr
    return json.loads(result.stdout)


def hosts(data: dict, group: str) -> list[str]:
    return sorted(data.get(group, {}).get("hosts", []))


def hostvars(data: dict, host: str) -> dict:
    return data.get("_meta", {}).get("hostvars", {}).get(host, {})


def script(lab, *args: str, env: dict | None = None):
    ansible, project = lab
    path = project / "inventory" / "cmdb.py"
    return run_sandboxed([str(path), *args], writable=[ansible.root], cwd=project, env=env or {}, timeout=30)


def test_script_is_executable():
    path = ex.path("inventory/cmdb.py")
    assert path.stat().st_mode & 0o111, "inventory/cmdb.py phải có quyền thực thi (chmod +x) để Ansible chạy nó như script"
    assert path.read_text(encoding="utf-8").startswith("#!/usr/bin/env python3"), "Dòng đầu phải là #!/usr/bin/env python3"


def test_groups_by_role_env_az(lab):
    data = inventory(lab, "cmdb.json", "inventory/cmdb.py")
    assert hosts(data, "role_web") == ["web-1", "web-2"]
    assert hosts(data, "role_worker") == ["worker-1", "worker-2", "worker-3", "worker-stg-1"]
    assert hosts(data, "role_postgres") == ["db-1"]
    assert hosts(data, "env_prod") == PROD
    assert hosts(data, "env_staging") == ["worker-stg-1"]
    assert hosts(data, "az_hcm_1a") == ["db-1", "web-1", "worker-1", "worker-3", "worker-stg-1"]
    assert hosts(data, "az_hcm_1b") == ["web-2", "worker-2"]


def test_decommissioned_excluded(lab):
    data = inventory(lab, "cmdb.json", "inventory/cmdb.py")
    assert "worker-4" not in data.get("_meta", {}).get("hostvars", {}), "Host decommissioned không được vào inventory"
    assert all("worker-4" not in group.get("hosts", []) for group in data.values() if isinstance(group, dict))


def test_hostvars(lab):
    data = inventory(lab, "cmdb.json", "inventory/cmdb.py")
    expected = {"ansible_host": "10.20.2.21", "olist_role": "worker", "olist_env": "prod", "olist_az": "hcm-1a", "olist_cpu": 8,
                "olist_canary": True}
    got = {key: hostvars(data, "worker-1").get(key) for key in expected}
    assert got == expected


def test_host_mode_and_missing_cmdb(lab):
    ansible, _ = lab
    single = script(lab, "--host", "worker-1", env={"OLIST_CMDB_FILE": str(ansible.root / "cmdb.json")})
    assert single.returncode == 0 and json.loads(single.stdout or "null") == {}, (
        f"`cmdb.py --host <tên>` trả {{}} vì biến đã nằm trong _meta: {single.stdout!r} {single.stderr!r}")
    missing = script(lab, "--list")
    assert missing.returncode != 0, "Thiếu OLIST_CMDB_FILE thì script phải thoát mã khác 0, không trả inventory rỗng"
    assert "OLIST_CMDB_FILE" in missing.stderr, f"Thông báo lỗi phải nhắc OLIST_CMDB_FILE: {missing.stderr!r}"


def test_messy_cmdb_normalized(lab):
    data = inventory(lab, "cmdb-messy.json", "inventory/cmdb.py")
    assert hosts(data, "role_payment_api") == ["pay-1", "pay-2"]
    assert hosts(data, "env_prod") == ["pay-1", "pay-2"]
    assert hosts(data, "az_hcm_1a") == ["pay-1"]
    assert hostvars(data, "pay-2").get("olist_canary") is True
    assert hostvars(data, "pay-1").get("olist_az") == "hcm-1a" and hostvars(data, "pay-1").get("olist_role") == "payment-api"
    assert hostvars(data, "pay-1").get("olist_canary") is False, "Thiếu canary thì mặc định false"
    assert hostvars(data, "pay-2").get("olist_az") is None, "Thiếu az thì olist_az là null và host không vào nhóm az_*"
    bad = sorted(g for g in data if g != "_meta" and not re.fullmatch(r"[a-z0-9_]+", g))
    assert not bad, f"Tên nhóm chỉ gồm chữ thường, số, gạch dưới: {bad}"


def test_constructed_groups(lab):
    data = inventory(lab, "cmdb.json")
    assert hosts(data, "canary") == ["worker-1"]
    assert hosts(data, "big") == ["db-1", "worker-1", "worker-2"]
    assert hostvars(data, "worker-3").get("olist_worker_concurrency") == 8
    assert hostvars(data, "worker-stg-1").get("olist_worker_concurrency") == 4


def list_hosts(lab, cmdb: str) -> list[tuple[str, list[str]]]:
    ansible, project = lab
    result = ansible.run("ansible-playbook", "-i", "inventory", "rollout.yml", "--list-hosts", cwd=project,
                         env={"OLIST_CMDB_FILE": str(ansible.root / cmdb)})
    assert result.returncode == 0, f"--list-hosts lỗi:\n{result.stdout}\n{result.stderr}"
    plays = []
    for block in re.split(r"\n\s*play #\d+ ", result.stdout)[1:]:
        name = block.splitlines()[0]
        found = re.search(r"hosts \(\d+\):\n((?:\s{6}\S+\n?)*)", block)
        plays.append((name, sorted(found.group(1).split()) if found else []))
    return plays


def test_rollout_patterns(lab):
    plays = list_hosts(lab, "cmdb.json")
    assert [p[1] for p in plays] == [["worker-1"], ["worker-2", "worker-3"]], (
        f"rollout.yml: play 1 chỉ canary worker prod, play 2 các worker prod còn lại. Đang là {plays}")

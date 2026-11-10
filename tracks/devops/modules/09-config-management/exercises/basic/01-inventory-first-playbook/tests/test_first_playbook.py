import json

import pytest

from testkit import AnsibleLab, Exercise

ex = Exercise(__file__)
HOSTS = ["web-1", "worker-1", "worker-2"]
HOST_INI = "/etc/olist-shop/host.ini"
EXPECTED = {
    "web-1": "[host]\nname = web-1\nenv = staging\nrole = web\n",
    "worker-1": "[host]\nname = worker-1\nenv = staging\nrole = worker\nconcurrency = 2\n",
    "worker-2": "[host]\nname = worker-2\nenv = staging\nrole = worker\nconcurrency = 4\n",
}
MODULE_ONLY = {"ansible.builtin.shell", "ansible.builtin.command", "ansible.builtin.raw", "ansible.builtin.script"}


@pytest.fixture(scope="module")
def lab():
    with AnsibleLab(HOSTS) as lab:
        project = lab.stage(ex.target)
        inventory = lab.run("ansible-inventory", "-i", "inventory", "--list", cwd=project)
        first = lab.playbook("site.yml", inventory=["inventory"], cwd=project)
        second = lab.playbook("site.yml", inventory=["inventory"], cwd=project)
        check = lab.playbook("site.yml", "--check", "--diff", inventory=["inventory"], cwd=project)
        yield lab, inventory, first, second, check


@pytest.fixture(scope="module")
def inventory(lab):
    result = lab[1]
    assert result.returncode == 0, f"ansible-inventory lỗi:\n{result.stderr}"
    return json.loads(result.stdout)


def hostvars(inventory: dict, host: str) -> dict:
    return inventory.get("_meta", {}).get("hostvars", {}).get(host, {})


def test_groups(inventory):
    assert sorted(inventory.get("web", {}).get("hosts", [])) == ["web-1"]
    assert sorted(inventory.get("workers", {}).get("hosts", [])) == ["worker-1", "worker-2"]
    assert sorted(inventory.get("olist", {}).get("children", [])) == ["web", "workers"], (
        "Nhóm olist phải có đúng hai nhóm con web và workers, không liệt kê host trực tiếp")
    assert not inventory.get("olist", {}).get("hosts"), "Nhóm olist chỉ gom nhóm con, không chứa host trực tiếp"


def test_variables(inventory):
    for host in HOSTS:
        assert hostvars(inventory, host).get("olist_env") == "staging", f"{host}: olist_env lấy từ group_vars/all.yml"
    assert hostvars(inventory, "web-1").get("olist_role") == "web"
    assert "olist_worker_concurrency" not in hostvars(inventory, "web-1"), "Biến của worker không được rò sang web"
    assert hostvars(inventory, "worker-1").get("olist_role") == "worker"
    assert hostvars(inventory, "worker-1").get("olist_worker_concurrency") == 2
    assert hostvars(inventory, "worker-2").get("olist_worker_concurrency") == 4, "worker-2 ghi đè bằng host_vars"


def test_inventory_has_no_connection_details():
    text = ex.read("inventory/hosts.yml")
    assert "ansible_" not in text, "Inventory chỉ khai báo host và nhóm; lab tự cấp cách kết nối"


def test_first_run(lab):
    first = lab[2]
    assert first.returncode == 0, first.tail()
    assert sorted(first.recap) == HOSTS, f"Play phải chạy trên cả {HOSTS}, recap có {sorted(first.recap)}"
    assert all(first.recap[h]["changed"] > 0 for h in HOSTS), first.recap


@pytest.mark.parametrize("host", HOSTS)
def test_host_ini(lab, host):
    ansible = lab[0]
    assert ansible.read(host, HOST_INI) == EXPECTED[host]
    assert ansible.stat(host, HOST_INI) == ("644", "root", "root")
    assert ansible.stat(host, "/etc/olist-shop") == ("755", "root", "root")


@pytest.mark.parametrize("host", HOSTS)
def test_system_user(lab, host):
    ansible = lab[0]
    passwd = ansible.exec(host, "getent", "passwd", "olist").stdout.strip().split(":")
    assert len(passwd) == 7, f"{host}: chưa có user olist"
    group = ansible.exec(host, "getent", "group", "olist").stdout.strip().split(":")
    assert len(group) == 4 and passwd[3] == group[2], f"{host}: group chính của olist phải là group olist"
    assert int(passwd[2]) < 1000 and passwd[6] == "/usr/sbin/nologin", f"{host}: user hệ thống, shell nologin: {passwd}"
    assert ansible.stat(host, passwd[5]) is None, f"{host}: không tạo thư mục home cho user dịch vụ"


def test_only_modules(lab):
    first = lab[2]
    used = sorted({t["action"] for t in first.tasks()} & MODULE_ONLY)
    assert first.tasks() and not used, f"Bài này chỉ dùng module có trạng thái, không dùng {used}"


def test_second_run_idempotent(lab):
    first, second = lab[2], lab[3]
    assert first.returncode == 0 and second.returncode == 0, second.tail()
    assert second.changed == {h: 0 for h in HOSTS}, (
        f"Lần hai phải changed=0, nhận {second.changed}; task còn đổi: {sorted({t['task'] for t in second.tasks(changed=True)})}")


def test_check_diff_clean(lab):
    first, check = lab[2], lab[4]
    assert first.returncode == 0 and check.returncode == 0, check.tail()
    assert check.changed == {h: 0 for h in HOSTS}, check.tail()

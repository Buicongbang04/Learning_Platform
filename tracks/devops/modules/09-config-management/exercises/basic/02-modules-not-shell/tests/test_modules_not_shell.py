import pytest

from testkit import AnsibleLab, Exercise

ex = Exercise(__file__)
HOSTS = ["worker-1", "worker-2", "worker-3"]
ENV = "/etc/olist-shop/worker.env"
LOG = "/var/log/olist-shop/worker.log"
SEED_ENV = "DATABASE_HOST=db.internal\nTZ=UTC\n"
EXPECTED_ENV = "DATABASE_HOST=db.internal\nTZ=Asia/Ho_Chi_Minh\nLOG_LEVEL=INFO\n"
LOGS = {
    "worker-1": "INFO job done\nWARNING slow job\nINFO job done\n",
    "worker-2": "".join(f"ERROR job {i} lỗi\n" for i in range(7)),
}
CHECK_ACTIONS = {"ansible.builtin.command"}
FORBIDDEN = {"ansible.builtin.shell", "ansible.builtin.raw", "ansible.builtin.script"}
STOP_ACTIONS = {"ansible.builtin.assert", "ansible.builtin.fail"}


def seed(lab: AnsibleLab) -> None:
    for host in HOSTS:
        script = f"mkdir -p /etc/olist-shop /var/log/olist-shop && printf '%s' '{SEED_ENV}' > {ENV}"
        if host in LOGS:
            script += f" && printf '%s' '{LOGS[host]}' > {LOG}"
        result = lab.exec(host, "sh", "-c", script)
        assert result.returncode == 0, result.stderr


@pytest.fixture(scope="module")
def lab():
    with AnsibleLab(HOSTS) as lab:
        seed(lab)
        project = lab.stage(ex.target)
        first = lab.playbook("harden.yml", inventory=["inventory"], cwd=project)
        second = lab.playbook("harden.yml", inventory=["inventory"], cwd=project)
        yield lab, first, second


def failed_actions(run, host: str) -> list[str]:
    return [t["action"] for t in run.tasks(host=host) if t["status"] == "failed"]


def test_no_shell_left(lab):
    _, first, _ = lab
    used = sorted({t["action"] for t in first.tasks()} & FORBIDDEN)
    assert first.tasks() and not used, f"Còn task {used}: viết lại bằng module (file, lineinfile...)"
    commands = first.tasks(host="worker-1")
    commands = [t for t in commands if t["action"] in CHECK_ACTIONS]
    assert len(commands) == 2, f"Chỉ còn đúng hai task ansible.builtin.command (kiểm Python, đếm ERROR), có {len(commands)}"


def test_healthy_host_passes(lab):
    _, first, _ = lab
    assert first.recap.get("worker-1", {}).get("failures") == 0, (
        f"worker-1 có log không lỗi (grep không tìm thấy dòng nào, mã thoát 1) mà play vẫn fail:\n{first.tail()}")


def test_files_on_healthy_host(lab):
    ansible, _, _ = lab
    assert ansible.read("worker-1", ENV) == EXPECTED_ENV, "Env file sau khi sửa phải đúng ba dòng, giữ dòng cũ, không lặp"
    assert ansible.stat("worker-1", "/opt/olist-shop/releases") == ("750", "root", "root")
    assert ansible.stat("worker-1", "/opt/olist-shop/releases/1.4.2") is not None
    link = ansible.exec("worker-1", "readlink", "/opt/olist-shop/current").stdout.strip()
    assert link == "/opt/olist-shop/releases/1.4.2", f"current phải là symlink tới releases/1.4.2, đang là {link!r}"


def test_too_many_errors_stops_host(lab):
    _, first, _ = lab
    failed = failed_actions(first, "worker-2")
    assert failed and set(failed) <= STOP_ACTIONS, (
        f"worker-2 có 7 dòng ERROR: phải dừng ở ansible.builtin.assert hay fail, không phải ở lệnh đếm. Task fail: {failed}")
    fatal = [line for line in first.output.splitlines() if line.startswith("fatal: [worker-2]")]
    assert fatal and "ERROR" in fatal[-1], f"Thông báo dừng của worker-2 phải nhắc tới ERROR và số dòng lỗi: {fatal}"


def test_missing_log_is_an_error(lab):
    _, first, _ = lab
    failed = failed_actions(first, "worker-3")
    assert failed == ["ansible.builtin.command"], (
        f"worker-3 không có tệp log: grep thoát mã 2 và chính task đếm phải fail (failed_when). Task fail: {failed}")


def test_checks_never_report_changed(lab):
    _, first, _ = lab
    noisy = sorted({t["task"] for t in first.tasks(changed=True) if t["action"] in CHECK_ACTIONS})
    assert not noisy, f"Task chỉ đọc phải changed_when: false: {noisy}"


def test_second_run_idempotent(lab):
    ansible, first, second = lab
    assert first.recap.get("worker-1", {}).get("failures") == 0
    assert second.recap.get("worker-1", {}).get("changed") == 0, (
        f"Lần hai trên worker-1 phải changed=0; task còn đổi: {sorted({t['task'] for t in second.tasks(host='worker-1', changed=True)})}")
    assert ansible.read("worker-1", ENV) == EXPECTED_ENV, "Chạy lại không được thêm dòng trùng"

import re
import shutil

import pytest

from testkit import ROOT, AnsibleLab, Exercise

ex = Exercise(__file__)
HOSTS = ["worker-1", "worker-2"]
APP = ROOT / "tracks" / "devops" / "sample-app" / "olist_shop"
ROLE_FILES = ["defaults/main.yml", "tasks/main.yml", "handlers/main.yml", "meta/main.yml", "templates/worker.env.j2",
              "templates/olist-worker.service.j2"]
HANDLER = "Restart olist-worker"
UNIT = "/etc/systemd/system/olist-worker.service"
ENV = "/etc/olist-shop/worker.env"
PARSE_WARNING = re.compile(r"Unknown key|Unknown section|Failed to parse|Invalid|ignoring|Missing '='|not executable", re.I)
EXPECTED_ENV = {
    "DATABASE_URL": "postgresql://olist@db.internal:5432/olist",
    "REDIS_URL": "redis://redis.internal:6379/0",
    "LOG_LEVEL": "INFO",
    "PYTHONPATH": "/opt/olist-shop/app",
}
UNIT_LINES = {
    "Service": ["User=olist", "Group=olist", f"EnvironmentFile={ENV}", "WorkingDirectory=/opt/olist-shop/app",
                "ExecStart=/opt/olist-shop/.venv/bin/python -m olist_shop.worker", "Restart=on-failure", "MemoryMax=512M",
                "NoNewPrivileges=yes", "ProtectSystem=strict"],
    "Install": ["WantedBy=multi-user.target"],
}


def env_lines(text: str | None) -> dict[str, str]:
    pairs = [line.split("=", 1) for line in (text or "").splitlines() if "=" in line and not line.startswith("#")]
    return {key.strip(): value.strip() for key, value in pairs}


def unit_sections(text: str | None) -> dict[str, list[str]]:
    sections: dict[str, list[str]] = {}
    current = None
    for raw in (text or "").splitlines():
        line = raw.strip()
        if line.startswith("[") and line.endswith("]"):
            current = sections.setdefault(line[1:-1], [])
        elif line and not line.startswith(("#", ";")) and current is not None:
            current.append(re.sub(r"\s*=\s*", "=", line, count=1))
    return sections


@pytest.fixture(scope="module")
def lab():
    with AnsibleLab(HOSTS) as lab:
        project = lab.stage(ex.target)
        shutil.copytree(APP, project / "artifacts" / "olist_shop", ignore=shutil.ignore_patterns("__pycache__"))
        runs = {"first": lab.playbook("site.yml", inventory=["inventory"], cwd=project)}
        runs["second"] = lab.playbook("site.yml", inventory=["inventory"], cwd=project)
        yield lab, project, runs


def converged(lab):
    lab_, project, runs = lab
    first = runs["first"]
    assert first.returncode == 0, f"Lần chạy đầu lỗi:\n{first.tail()}"
    assert all(first.recap.get(h, {}).get("failures", 1) == 0 for h in HOSTS), first.recap
    missing = [h for h in HOSTS if lab_.stat(h, ENV) is None]
    assert not missing, f"Role chưa ghi {ENV} trên {missing}: role chưa cài gì"
    return lab_, project, runs


def test_role_layout():
    role = ex.path("roles/olist_worker")
    missing = [rel for rel in ROLE_FILES if not (role / rel).is_file()]
    assert not missing, f"Role olist_worker thiếu tệp: {missing}"
    assert "olist_worker" in ex.read("site.yml"), "site.yml phải dùng role olist_worker"


def test_first_run_converges_and_notifies_handler(lab):
    _, _, runs = converged(lab)
    first = runs["first"]
    assert all(first.recap[h]["changed"] > 0 for h in HOSTS), first.recap
    notified = {t["host"] for t in first.tasks(HANDLER, handler=True)}
    assert notified == set(HOSTS), f"Handler '{HANDLER}' phải chạy (được notify) trên mọi host ở lần đầu, chỉ thấy {notified}"


def test_user_and_directories(lab):
    lab_, _, _ = converged(lab)
    for host in HOSTS:
        passwd = lab_.exec(host, "getent", "passwd", "olist").stdout.strip().split(":")
        assert len(passwd) == 7, f"{host}: chưa có user olist"
        assert int(passwd[2]) < 1000 and passwd[6] == "/usr/sbin/nologin", f"{host}: olist phải là user hệ thống, shell nologin: {passwd}"
        assert lab_.stat(host, "/opt/olist-shop") == ("755", "root", "root")
        assert lab_.stat(host, "/etc/olist-shop") == ("750", "root", "olist")
        assert lab_.stat(host, "/opt/olist-shop/app/olist_shop/worker.py") == ("644", "root", "root")


def test_env_file(lab):
    lab_, _, _ = converged(lab)
    for host in HOSTS:
        assert lab_.stat(host, ENV) == ("640", "root", "olist"), f"{host}: {ENV} phải 0640 root:olist"
        assert env_lines(lab_.read(host, ENV)) == EXPECTED_ENV


def test_unit_file_verified_by_systemd(lab):
    lab_, _, _ = converged(lab)
    for host in HOSTS:
        assert lab_.stat(host, UNIT) == ("644", "root", "root")
        sections = unit_sections(lab_.read(host, UNIT))
        for section, lines in UNIT_LINES.items():
            missing = [line for line in lines if line not in sections.get(section, [])]
            assert not missing, f"{host}: [{section}] của {UNIT} thiếu {missing}"
        result = lab_.exec(host, "systemd-analyze", "verify", "--man=no", UNIT)
        output = result.stdout + result.stderr
        warnings = [line for line in output.splitlines() if PARSE_WARNING.search(line)]
        assert result.returncode == 0 and not warnings, f"{host}: systemd-analyze verify báo lỗi:\n{output}"


def test_worker_imports_with_env(lab):
    lab_, _, _ = converged(lab)
    script = ("set -a; . /etc/olist-shop/worker.env; set +a; cd /opt/olist-shop/app; "
              "/opt/olist-shop/.venv/bin/python -c 'import olist_shop.worker; from olist_shop.settings import Settings; "
              "print(Settings().log_level)'")
    for host in HOSTS:
        result = lab_.exec(host, "su", "-s", "/bin/sh", "olist", "-c", script, timeout=60)
        assert result.returncode == 0 and result.stdout.strip() == "INFO", (
            f"{host}: user olist chưa chạy được worker bằng venv và env file:\n{result.stdout}{result.stderr}")


def test_second_run_changes_nothing(lab):
    _, _, runs = converged(lab)
    second = runs["second"]
    assert second.returncode == 0, second.tail()
    assert second.changed == {h: 0 for h in HOSTS}, (
        f"Lần chạy thứ hai phải changed=0, nhận {second.changed}. Task còn đổi: "
        f"{sorted({t['task'] for t in second.tasks(changed=True)})}")
    assert not second.tasks(HANDLER, handler=True), "Không có gì đổi thì handler không được chạy"


def test_check_diff_reports_no_drift(lab):
    lab_, project, _ = converged(lab)
    run = lab_.playbook("site.yml", "--check", "--diff", inventory=["inventory"], cwd=project)
    assert run.returncode == 0 and run.changed == {h: 0 for h in HOSTS}, (
        f"`--check --diff` sau khi converge phải changed=0:\n{run.tail()}")


def test_log_level_change_restarts_worker(lab):
    lab_, project, _ = converged(lab)
    run = lab_.playbook("site.yml", "-e", "olist_worker_log_level=DEBUG", inventory=["inventory"], cwd=project)
    assert run.returncode == 0, run.tail()
    for host in HOSTS:
        assert env_lines(lab_.read(host, ENV))["LOG_LEVEL"] == "DEBUG"
    assert run.changed == {h: 1 for h in HOSTS}, f"Đổi log level chỉ được đổi đúng một task (env file): {run.changed}"
    assert {t["host"] for t in run.tasks(HANDLER, handler=True)} == set(HOSTS), "Đổi env file phải notify handler"


def test_tags_config_runs_only_config_tasks(lab):
    lab_, project, _ = converged(lab)
    run = lab_.playbook("site.yml", "--tags", "config", "-e", "olist_worker_log_level=WARNING", inventory=["inventory"],
                        cwd=project)
    assert run.returncode == 0, run.tail()
    ran = [t for t in run.tasks(handler=False) if t["task"] != "Gathering Facts"]
    assert ran, "--tags config phải chạy được ít nhất task env file và unit"
    untagged = sorted({t["task"] for t in ran if "config" not in t["tags"]})
    assert not untagged, f"--tags config chạy cả task không gắn tag config: {untagged}"
    names = {t["action"] for t in ran}
    assert {"ansible.builtin.template"} <= names and not names & {"ansible.builtin.pip", "ansible.builtin.copy"}, names
    for host in HOSTS:
        assert env_lines(lab_.read(host, ENV))["LOG_LEVEL"] == "WARNING"


def test_drift_is_corrected_on_one_host(lab):
    lab_, project, _ = converged(lab)
    lab_.playbook("site.yml", inventory=["inventory"], cwd=project)
    tamper = lab_.exec("worker-1", "sh", "-c", f"printf 'Environment=DEBUG_HACK=1\\n' >> {UNIT}")
    assert tamper.returncode == 0
    run = lab_.playbook("site.yml", inventory=["inventory"], cwd=project)
    assert run.returncode == 0, run.tail()
    assert run.changed["worker-1"] >= 1 and run.changed["worker-2"] == 0, run.changed
    assert {t["host"] for t in run.tasks(HANDLER, handler=True)} == {"worker-1"}
    assert "DEBUG_HACK" not in lab_.read("worker-1", UNIT)

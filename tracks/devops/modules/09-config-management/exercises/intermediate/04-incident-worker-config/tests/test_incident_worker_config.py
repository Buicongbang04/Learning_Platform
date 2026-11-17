import re
from pathlib import Path

import pytest

from testkit import AnsibleLab, Exercise

ex = Exercise(__file__)
INCIDENT = Path(__file__).parent / "fixtures" / "incident"
HOSTS = ["worker-1", "worker-2", "worker-3"]
WORKERS = ["worker-1", "worker-2"]
ENV = "/etc/olist-shop/worker.env"
HANDLER = "Restart olist-worker"
NEW_REDIS = "redis://redis-b.internal:6379/0"


def env(lab, host: str) -> dict[str, str]:
    text = lab.read(host, ENV) or ""
    return dict(line.split("=", 1) for line in text.splitlines() if "=" in line and not line.startswith("#"))


def converge(source: Path):
    with AnsibleLab(HOSTS) as lab:
        project = lab.stage(source)
        runs = {"first": lab.playbook("site.yml", inventory=["inventory"], cwd=project)}
        runs["env_first"] = {host: env(lab, host) for host in HOSTS}
        runs["data_dir"] = {host: lab.stat(host, "/var/lib/olist-shop") for host in HOSTS}
        runs["second"] = lab.playbook("site.yml", inventory=["inventory"], cwd=project)
        group_vars = project / "inventory" / "group_vars" / "workers.yml"
        text = group_vars.read_text(encoding="utf-8")
        group_vars.write_text(re.sub(r"(?m)^olist_worker_redis_url:.*$", f"olist_worker_redis_url: {NEW_REDIS}", text), encoding="utf-8")
        runs["migrate"] = lab.playbook("site.yml", inventory=["inventory"], cwd=project)
        runs["env_migrate"] = {host: env(lab, host) for host in HOSTS}
        runs["check"] = lab.playbook("site.yml", "--check", "--diff", inventory=["inventory"], cwd=project)
        yield runs


@pytest.fixture(scope="module")
def fixed():
    yield from converge(ex.target)


@pytest.fixture(scope="module")
def incident():
    yield from converge(INCIDENT)


def ok(run) -> None:
    assert run.returncode == 0 and all(run.recap.get(h, {}).get("failures", 1) == 0 for h in HOSTS), run.tail()


def test_group_vars_log_level_applies(fixed):
    ok(fixed["first"])
    for host in WORKERS:
        assert fixed["env_first"][host].get("LOG_LEVEL") == "DEBUG", (
            f"{host}: group_vars/workers.yml đặt DEBUG mà env file là {fixed['env_first'][host].get('LOG_LEVEL')}")
    assert fixed["env_first"]["worker-3"] == {"REDIS_URL": "redis://redis.internal:6379/0", "LOG_LEVEL": "INFO"}, (
        "worker-3 (nhóm batch, inventory không đặt gì) phải nhận giá trị mặc định của role")


def test_data_dir_owned_by_olist(fixed):
    ok(fixed["first"])
    for host in HOSTS:
        assert fixed["data_dir"][host] == ("750", "olist", "olist"), f"{host}: /var/lib/olist-shop phải 0750 olist:olist"


def test_rerun_reports_no_change(fixed):
    ok(fixed["second"])
    assert fixed["second"].changed == {h: 0 for h in HOSTS}, (
        f"Chạy lại không đổi gì phải changed=0; task còn đổi: {sorted({t['task'] for t in fixed['second'].tasks(changed=True)})}")


def test_redis_migration_restarts_workers(fixed):
    migrate = fixed["migrate"]
    ok(migrate)
    for host in WORKERS:
        assert fixed["env_migrate"][host].get("REDIS_URL") == NEW_REDIS
    assert {h: migrate.changed[h] for h in WORKERS} == {h: 1 for h in WORKERS}, (
        f"Đổi Redis chỉ đổi đúng env file trên worker-1, worker-2: {migrate.changed}")
    assert migrate.changed["worker-3"] == 0
    assert {t["host"] for t in migrate.tasks(HANDLER, handler=True)} == set(WORKERS), (
        "Env file đổi thì worker phải được restart (handler chạy) trên đúng hai worker")


def test_check_mode_clean_after_converge(fixed):
    ok(fixed["check"])
    assert fixed["check"].changed == {h: 0 for h in HOSTS}, fixed["check"].tail()


def test_incident_reproduces_symptoms(incident):
    ok(incident["first"])
    assert incident["env_first"]["worker-1"].get("LOG_LEVEL") == "INFO", "Bản lúc sự cố: DEBUG trong group_vars bị bỏ qua"
    assert all(incident["second"].changed[h] >= 1 for h in HOSTS), "Bản lúc sự cố: chạy lại vẫn báo changed"
    assert incident["env_migrate"]["worker-1"].get("REDIS_URL") == NEW_REDIS
    assert not incident["migrate"].tasks(HANDLER, handler=True), "Bản lúc sự cố: đổi Redis mà handler không chạy"

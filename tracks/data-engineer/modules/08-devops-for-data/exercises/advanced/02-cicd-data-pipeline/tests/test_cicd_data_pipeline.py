import re

import yaml

from testkit import Exercise

ex = Exercise(__file__)


def load():
    doc = yaml.safe_load(ex.read("pipeline.yml"))
    assert isinstance(doc, dict)
    return doc


def jobs():
    return load().get("jobs") or {}


def text_of(job):
    return yaml.safe_dump(job, allow_unicode=True)


def run_text(job):
    return "\n".join(str(s.get("run", "")) + " " + str(s.get("uses", "")) + " " + yaml.safe_dump(s.get("with", {}))
                     for s in job.get("steps") or [])


def needs(job):
    n = job.get("needs") or []
    return [n] if isinstance(n, str) else list(n)


def ancestors(name, all_jobs, seen=None):
    seen = set() if seen is None else seen
    for parent in needs(all_jobs[name]):
        if parent not in seen and parent in all_jobs:
            seen.add(parent)
            ancestors(parent, all_jobs, seen)
    return seen


def env_name(job):
    env = job.get("environment")
    return env.get("name") if isinstance(env, dict) else env


def find(pred):
    found = [name for name, job in jobs().items() if pred(job)]
    return found


def unit_jobs():
    return find(lambda j: "services" not in j and "ruff" in run_text(j) and "pytest" in run_text(j))


def integration_jobs():
    return find(lambda j: "postgres" in (j.get("services") or {}) and "pytest" in run_text(j))


def build_jobs():
    return find(lambda j: re.search(r"docker/build-push-action|docker (build|push)", run_text(j)) is not None
                and not env_name(j))


def env_jobs(name):
    return find(lambda j: env_name(j) == name)


def test_triggers_and_concurrency():
    doc = load()
    on = doc.get("on", doc.get(True))
    assert isinstance(on, dict) and "pull_request" in on and "push" in on
    assert "main" in ((on["push"] or {}).get("branches") or [])
    assert doc.get("concurrency"), "Cần concurrency"


def test_permissions():
    assert load().get("permissions") == {"contents": "read"}
    for name in build_jobs():
        assert (jobs()[name].get("permissions") or {}).get("packages") == "write"


def test_unit_job():
    assert unit_jobs(), "Cần job chạy ruff + pytest không có services"


def test_integration_job():
    integ = integration_jobs()
    assert integ, "Cần job có services.postgres chạy pytest"
    name = integ[0]
    pg = jobs()[name]["services"]["postgres"]
    image = str(pg.get("image", ""))
    assert re.search(r"postgres:\d", image), "Image postgres cần pin version"
    assert "--health-cmd" in str(pg.get("options", "")), "Service postgres cần health check"
    assert jobs()[name].get("env") or any(s.get("env") for s in jobs()[name].get("steps", [])), "Truyền DSN qua env"
    assert set(unit_jobs()) & ancestors(name, jobs()), "Integration phải phụ thuộc job unit"


def test_build_job_main_only_and_sha_tag():
    builds = build_jobs()
    assert builds, "Cần job build/push image"
    name = builds[0]
    job = jobs()[name]
    assert "refs/heads/main" in str(job.get("if", "")), "Build chỉ chạy trên main"
    assert "github.sha" in text_of(job), "Tag image phải chứa github.sha"
    assert set(integration_jobs()) & ancestors(name, jobs()), "Build phải phụ thuộc integration"


def test_deploy_order():
    staging, production = env_jobs("staging"), env_jobs("production")
    assert staging and production, "Cần job environment staging và production"
    all_jobs = jobs()
    assert set(build_jobs()) & ancestors(staging[0], all_jobs), "Staging phải phụ thuộc build"
    assert staging[0] in ancestors(production[0], all_jobs), "Production phải phụ thuộc staging"
    for name in staging + production:
        assert "sha" in text_of(all_jobs[name]), "Deploy phải dùng image tag theo SHA"


def test_timeouts():
    for name, job in jobs().items():
        assert isinstance(job.get("timeout-minutes"), int), f"Job {name} thiếu timeout-minutes"


def test_no_hardcoded_tokens():
    raw = ex.read("pipeline.yml")
    assert not re.search(r"ghp_[A-Za-z0-9]{20,}|AKIA[0-9A-Z]{16}", raw)

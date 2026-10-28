import json
import re

import yaml

from testkit import Exercise

ex = Exercise(__file__)


def parse_dockerfile(text):
    out, buf = [], ""
    for raw in text.splitlines():
        line = raw.strip()
        if line.startswith("#") or (not buf and not line):
            continue
        if line.endswith("\\"):
            buf += line[:-1] + " "
            continue
        buf += line
        word, _, rest = buf.strip().partition(" ")
        out.append((word.upper(), rest.strip()))
        buf = ""
    return out


def stages():
    result = []
    for cmd, args in parse_dockerfile(ex.read("Dockerfile")):
        if cmd == "FROM":
            result.append({"from": args, "instrs": []})
        elif result:
            result[-1]["instrs"].append((cmd, args))
    return result


def compose():
    return yaml.safe_load(ex.read("docker-compose.yml"))


# ---------- Dockerfile ----------

def test_multi_stage():
    st = stages()
    assert len(st) >= 2, "Cần ít nhất 2 stage"
    assert re.search(r"\bAS\s+builder\b", st[0]["from"], re.I), "Stage đầu phải là AS builder"
    final = st[-1]["instrs"]
    assert any(c == "COPY" and "--from=builder" in a for c, a in final), "Stage cuối cần COPY --from=builder"


def test_all_from_pinned():
    for s in stages():
        image = s["from"].split()[0]
        base = image.split("@")[0]
        assert ":" in base or "@sha256" in image, f"{image} chưa có tag"
        tag = base.split(":", 1)[1] if ":" in base else "digest"
        assert tag != "latest" and (tag == "digest" or re.search(r"\d", tag)), f"{image} chưa pin version"


def test_final_stage_lean_and_safe():
    final = stages()[-1]["instrs"]
    for c, a in final:
        if c == "RUN":
            assert not re.search(r"build-essential|\bgcc\b", a), "Stage runtime không được cài compiler"
    users = [a for c, a in final if c == "USER"]
    assert users and users[-1].split(":")[0] not in {"root", "0"}, "Stage cuối cần USER không phải root"
    assert any(c == "HEALTHCHECK" for c, _ in final), "Stage cuối cần HEALTHCHECK"
    entry = [(c, a) for c, a in final if c in {"CMD", "ENTRYPOINT"}]
    assert entry, "Thiếu CMD/ENTRYPOINT"
    tokens = []
    for c, a in entry:
        try:
            tokens += json.loads(a)
        except json.JSONDecodeError:
            raise AssertionError(f"{c} phải ở exec form: {a}")
    assert "loader" in tokens


def test_pip_no_cache():
    for s in stages():
        for c, a in s["instrs"]:
            if c == "RUN":
                for part in a.split("&&"):
                    if re.search(r"pip (install|wheel)", part):
                        assert "--no-cache-dir" in part, part


# ---------- Compose ----------

def test_postgres_image_pinned():
    image = compose()["services"]["postgres"]["image"]
    assert ":" in image and not image.endswith(":latest") and re.search(r":\d", image)


def env_of(service):
    env = service.get("environment") or {}
    if isinstance(env, list):
        env = dict(item.split("=", 1) for item in env)
    return env


def test_no_hardcoded_password():
    services = compose()["services"]
    pw = str(env_of(services["postgres"]).get("POSTGRES_PASSWORD", ""))
    assert re.fullmatch(r"\$\{POSTGRES_PASSWORD[^}]*\}", pw), "POSTGRES_PASSWORD phải là ${POSTGRES_PASSWORD}"
    url = str(env_of(services["loader"]).get("DATABASE_URL", ""))
    match = re.match(r"\w+(\+\w+)?://[^:]+:([^@]+)@", url)
    assert match and match[2].startswith("${"), "DATABASE_URL không được chứa mật khẩu viết thẳng"


def test_postgres_healthcheck_and_volume():
    doc = compose()
    pg = doc["services"]["postgres"]
    test = pg.get("healthcheck", {}).get("test")
    assert test and "pg_isready" in (" ".join(test) if isinstance(test, list) else test)
    named = set((doc.get("volumes") or {}).keys())
    mounts = [v.split(":")[0] if isinstance(v, str) else v.get("source") for v in pg.get("volumes", [])]
    assert any(m in named for m in mounts), "Postgres phải mount một named volume khai báo ở volumes:"


def test_loader_depends_on_healthy():
    loader = compose()["services"]["loader"]
    assert "build" in loader
    deps = loader.get("depends_on")
    assert isinstance(deps, dict), "depends_on phải ở dạng mapping có condition"
    assert deps["postgres"]["condition"] == "service_healthy"
    assert "@postgres:5432" in str(env_of(loader).get("DATABASE_URL", ""))

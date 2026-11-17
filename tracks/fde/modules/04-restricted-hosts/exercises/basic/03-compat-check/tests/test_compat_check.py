import datetime
import json
import random
import shutil
import subprocess
import sys
import uuid
from pathlib import Path

import pytest
import yaml

import fdekit
from testkit import Exercise, run_sandboxed

ex = Exercise(__file__)
FIXTURES = ex.fixtures
APP_REQUIREMENTS = ex.dir / "app-requirements.yaml"
CODES = {"glibc_too_old", "python_missing", "python_too_old", "python_too_new", "os_unsupported", "os_eol"}
FACTS = {
    "bank": {"glibc": "2.28", "python": None, "os": ("rocky", "8.10"), "support_end": "2029-05-31"},
    "factory": {"glibc": "2.36", "python": "3.11.2", "os": ("debian", "12"), "support_end": None},
    "hospital": {"glibc": "2.31", "python": "3.8.10", "os": ("ubuntu", "20.04"), "support_end": None},
    "lab-open": {"glibc": "2.35", "python": "3.10.12", "os": ("ubuntu", "22.04"), "support_end": None},
}
GIVEN_APP = {
    "bank": {"glibc_too_old": "2.28", "python_missing": None},
    "factory": {},
    "hospital": {"python_too_old": "3.8.10", "os_unsupported": "ubuntu 20.04", "os_eol": "2025-05-31"},
    "lab-open": {},
}


def version(text: str) -> tuple[int, ...]:
    return tuple(int(part) for part in text.split("."))


def matches(version_id: str, entry: str) -> bool:
    return version_id == entry or version_id.startswith(entry + ".")


def expected(profile: str, req: dict) -> dict[str, str | None]:
    facts = FACTS[profile]
    issues: dict[str, str | None] = {}
    if version(facts["glibc"]) < version(req["glibc_min"]):
        issues["glibc_too_old"] = facts["glibc"]
    python = facts["python"]
    if python is None:
        issues["python_missing"] = None
    else:
        minor = version(python)[:2]
        if minor < version(req["python_min"]):
            issues["python_too_old"] = python
        if req.get("python_max") and minor > version(req["python_max"]):
            issues["python_too_new"] = python
    os_id, version_id = facts["os"]
    if not any(matches(version_id, entry) for entry in req["os_supported"].get(os_id, [])):
        issues["os_unsupported"] = f"{os_id} {version_id}"
    table = (req.get("os_eol") or {}).get(os_id, {})
    end = next((day for entry, day in table.items() if matches(version_id, entry)), facts["support_end"])
    if end and end <= req["as_of"]:
        issues["os_eol"] = end
    return issues


def random_requirements(rng: random.Random) -> dict:
    req = {
        "app": f"app-{rng.getrandbits(24):06x}",
        "glibc_min": rng.choice(["2.17", "2.27", "2.28", "2.31", "2.34", "2.35", "2.36", "2.39"]),
        "python_min": rng.choice(["3.6", "3.8", "3.9", "3.10", "3.11", "3.12"]),
        "os_supported": {},
        "as_of": (datetime.date(2024, 1, 1) + datetime.timedelta(days=rng.randrange(2500))).isoformat(),
    }
    if rng.random() < 0.6:
        req["python_max"] = rng.choice(["3.8", "3.10", "3.11", "3.12", "3.13"])
    pool = {"ubuntu": ["18.04", "20.04", "22.04", "24.04"], "debian": ["11", "12", "13"], "rocky": ["8", "8.10", "9"]}
    for os_id, versions in pool.items():
        if rng.random() < 0.8:
            req["os_supported"][os_id] = rng.sample(versions, rng.randint(1, len(versions)))
    if rng.random() < 0.7:
        req["os_eol"] = {"ubuntu": {"20.04": rng.choice(["2025-05-31", "2030-04-30"])},
                         "rocky": {"8": rng.choice(["2024-05-31", "2029-05-31"])}}
    return req


@pytest.fixture(scope="module")
def mod():
    return ex.module("compat_check.py")


@pytest.fixture()
def hosts(tmp_path) -> dict[str, Path]:
    copies = {}
    for profile in FACTS:
        target = tmp_path / f"host-{uuid.uuid4().hex[:8]}"
        shutil.copytree(FIXTURES / profile, target)
        copies[profile] = target
    return copies


def run(mod, host: Path, req: dict) -> dict[str, str | None]:
    issues = mod.check_host(host, json.loads(json.dumps(req)))
    assert isinstance(issues, list), f"check_host() phải trả list, nhận {type(issues).__name__}"
    found = {}
    for item in issues:
        assert isinstance(item, dict) and {"code", "found"} <= set(item), f"Mỗi vấn đề cần khoá code và found: {item!r}"
        assert item["code"] in CODES, f"code {item['code']!r} không thuộc {sorted(CODES)}"
        assert item["code"] not in found, f"code {item['code']!r} xuất hiện hai lần"
        found[item["code"]] = item["found"]
    return found


def test_fixtures_are_the_real_profiles():
    for profile, facts in FACTS.items():
        assert fdekit.PROFILES[profile].facts["glibc"] == facts["glibc"]
        assert (FIXTURES / profile / "ldd.txt").is_file() and (FIXTURES / profile / "os-release").is_file()


def test_given_app_on_four_profiles(mod, hosts):
    req = yaml.safe_load(APP_REQUIREMENTS.read_text(encoding="utf-8"))
    for profile, want in GIVEN_APP.items():
        assert expected(profile, req) == want
        assert run(mod, hosts[profile], req) == want, f"{profile}: danh sách vấn đề sai với app-requirements.yaml"


def test_random_requirements(mod, hosts):
    rng = random.Random(random.SystemRandom().randrange(1 << 30))
    for _ in range(40):
        req = random_requirements(rng)
        for profile, host in hosts.items():
            want = expected(profile, req)
            assert run(mod, host, req) == want, f"{profile} với yêu cầu {req}: cần {want}"


def test_cli_prints_json_and_exit_code(hosts, tmp_path):
    req = yaml.safe_load(APP_REQUIREMENTS.read_text(encoding="utf-8"))
    order = ["factory", "bank", "lab-open", "hospital"]
    argv = [sys.executable, ex.path("compat_check.py"), APP_REQUIREMENTS, *[hosts[p] for p in order]]
    try:
        done = run_sandboxed(argv, writable=[tmp_path], cwd=tmp_path, env={}, timeout=60)
    except subprocess.TimeoutExpired:
        pytest.fail("compat_check.py chạy quá 60 s")
    assert done.returncode == 1, f"Có máy có vấn đề thì mã thoát phải là 1, nhận {done.returncode}\n{done.stderr[-1500:]}"
    report = json.loads(done.stdout)
    assert list(report) == [hosts[p].name for p in order], "Khoá của JSON là tên thư mục máy, đúng thứ tự tham số"
    for profile in order:
        codes = {item["code"]: item["found"] for item in report[hosts[profile].name]}
        assert codes == GIVEN_APP[profile], f"{profile}: JSON của CLI sai"
    clean = [sys.executable, ex.path("compat_check.py"), APP_REQUIREMENTS, hosts["factory"], hosts["lab-open"]]
    ok = run_sandboxed(clean, writable=[tmp_path], cwd=tmp_path, env={}, timeout=60)
    assert ok.returncode == 0, f"Không máy nào có vấn đề thì mã thoát 0, nhận {ok.returncode}\n{ok.stderr[-1500:]}"

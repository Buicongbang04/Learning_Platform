import re
import shutil
from pathlib import Path

import pytest

from testkit import Exercise, run_sandboxed

ex = Exercise(__file__)
ORIGINAL = Path(__file__).parent / "fixtures" / "ssh_config.original"
OPS_KEY = "olist_ops_ed25519"
GITHUB_KEY = "github_ed25519"
INTERNAL = ["app-1", "app-17", "db-primary", "db-replica-2"]
ALL_HOSTS = ["bastion", *INTERNAL, "github.com", "partner.example.org"]


@pytest.fixture(autouse=True)
def ssh_client():
    ex.require_tool("ssh", min_version="8.0")


def resolve(config: Path, host: str, tmp_path: Path) -> dict[str, list[str]]:
    work = tmp_path / "work"
    work.mkdir(exist_ok=True)
    target = work / "ssh_config"
    shutil.copyfile(config, target)
    result = run_sandboxed(["ssh", "-G", "-F", str(target), host], writable=[work], cwd=work, env={}, timeout=15)
    assert result.returncode == 0, f"ssh -G {host} lỗi (cú pháp cấu hình?):\n{result.stderr}"
    options: dict[str, list[str]] = {}
    for line in result.stdout.splitlines():
        key, _, value = line.partition(" ")
        options.setdefault(key.lower(), []).append(value.strip())
    return options


def one(options: dict[str, list[str]], key: str) -> str | None:
    values = options.get(key)
    return values[0] if values else None


def key_names(options: dict[str, list[str]]) -> list[str]:
    return [Path(p).name for p in options.get("identityfile", [])]


def common_problems(host: str, o: dict[str, list[str]]) -> list[str]:
    found = []
    if one(o, "forwardagent") != "no":
        found.append(f"{host}: forwardagent phải là no")
    if one(o, "forwardx11") != "no":
        found.append(f"{host}: forwardx11 phải là no")
    if one(o, "passwordauthentication") != "no":
        found.append(f"{host}: passwordauthentication phải là no")
    if one(o, "stricthostkeychecking") not in ("yes", "true", "accept-new"):
        found.append(f"{host}: stricthostkeychecking phải là yes hoặc accept-new")
    if any(p == "/dev/null" for v in o.get("userknownhostsfile", []) for p in v.split()):
        found.append(f"{host}: userknownhostsfile không được là /dev/null")
    interval = one(o, "serveraliveinterval") or "0"
    if not (interval.isdigit() and 15 <= int(interval) <= 60):
        found.append(f"{host}: serveraliveinterval phải trong 15..60, đang là {interval}")
    count = one(o, "serveralivecountmax") or "0"
    if not (count.isdigit() and 2 <= int(count) <= 5):
        found.append(f"{host}: serveralivecountmax phải trong 2..5, đang là {count}")
    if one(o, "controlmaster") != "auto":
        found.append(f"{host}: controlmaster phải là auto")
    if not re.search(r"/\.ssh/[^/]*[0-9a-f]{40}$", one(o, "controlpath") or ""):
        found.append(f"{host}: controlpath phải nằm trong ~/.ssh và dùng %C")
    persist = one(o, "controlpersist") or ""
    if not (persist.isdigit() and 60 <= int(persist) <= 1800):
        found.append(f"{host}: controlpersist phải từ 1 tới 30 phút, đang là {persist or 'không đặt'}")
    if one(o, "proxycommand") not in (None, "none"):
        found.append(f"{host}: dùng ProxyJump, không dùng ProxyCommand")
    return found


def host_problems(host: str, o: dict[str, list[str]]) -> list[str]:
    found = common_problems(host, o)
    jump = one(o, "proxyjump")
    if host == "bastion":
        expected = {"user": "ops", "hostname": "bastion.olist-shop.com.br", "port": "2222"}
        keys, want_jump = [OPS_KEY], None
    elif host in INTERNAL:
        expected = {"user": "dba" if host.startswith("db-") else "deploy", "hostname": f"{host}.internal.olist-shop.com.br", "port": "22"}
        keys, want_jump = [OPS_KEY], "bastion"
    elif host == "github.com":
        expected = {"user": "git", "hostname": "github.com", "port": "22"}
        keys, want_jump = [GITHUB_KEY], None
    else:
        expected, keys, want_jump = {}, None, None
        if OPS_KEY in key_names(o) or GITHUB_KEY in key_names(o):
            found.append(f"{host}: host lạ không được nhận khoá {OPS_KEY} hay {GITHUB_KEY}")
    for key, value in expected.items():
        if one(o, key) != value:
            found.append(f"{host}: {key} phải là {value}, đang là {one(o, key)}")
    if keys is not None:
        if key_names(o) != keys:
            found.append(f"{host}: identityfile phải chỉ có {keys}, đang là {key_names(o)}")
        if one(o, "identitiesonly") != "yes":
            found.append(f"{host}: identitiesonly phải là yes")
    if (jump if jump != "none" else None) != want_jump:
        found.append(f"{host}: proxyjump phải là {want_jump or 'không đặt'}, đang là {jump}")
    return found


@pytest.mark.parametrize("host", ALL_HOSTS)
def test_resolved_config(host, tmp_path):
    found = host_problems(host, resolve(ex.path("ssh_config"), host, tmp_path))
    assert not found, "\n".join(found)


def test_no_match_exec(tmp_path):
    text = ex.read("ssh_config")
    assert not re.search(r"^\s*Match\b.*\bexec\b", text, re.M | re.I), "Không dùng Match exec trong bài này"


def test_checks_catch_original_config(tmp_path):
    found = [p for host in ("bastion", "app-1", "partner.example.org") for p in host_problems(host, resolve(ORIGINAL, host, tmp_path))]
    for expected in (
        "app-1: forwardagent phải là no",
        "app-1: stricthostkeychecking phải là yes hoặc accept-new",
        "app-1: userknownhostsfile không được là /dev/null",
        "app-1: dùng ProxyJump, không dùng ProxyCommand",
        "app-1: user phải là deploy, đang là root",
        "bastion: user phải là ops, đang là root",
    ):
        assert expected in found, f"Phép kiểm phải bắt lỗi '{expected}' của cấu hình cũ. Bắt được: {found}"

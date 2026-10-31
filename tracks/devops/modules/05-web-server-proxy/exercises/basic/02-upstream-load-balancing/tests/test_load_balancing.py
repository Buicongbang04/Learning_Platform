import re
import shutil
from collections import Counter
from pathlib import Path

import httpx
import pytest

from testkit import DockerLab, Exercise

ex = Exercise(__file__)
NGINX = "nginx:1.30.6-alpine"
PYTHON = "python:3.12.16-alpine3.24"
FIXTURES = Path(__file__).parent / "fixtures"
HOST = "shop.olist.test"
BACKENDS = ("olist-api-1", "olist-api-2")
MAX_FAILS = 3


def start_backend(lab: DockerLab, alias: str) -> None:
    lab.start(alias, PYTHON, "sh", "-c", "python /srv/backend.py; exec sleep 86400",
              mounts=[(FIXTURES / "backend.py", "/srv/backend.py")], env={"INSTANCE": alias})
    lab.wait_log(alias, "ready")


def start_nginx(lab: DockerLab, alias: str, conf: Path, workdir: Path) -> str:
    workdir.mkdir(parents=True, exist_ok=True)
    copy = workdir / "nginx.conf"
    shutil.copyfile(conf, copy)
    mounts = [(copy, "/etc/nginx/nginx.conf")]
    check = lab.run_once(f"{alias}-t", NGINX, "-t", mounts=mounts, entrypoint="nginx")
    assert check.returncode == 0, f"nginx -t báo lỗi:\n{check.stderr}"
    lab.start(alias, NGINX, "-g", "daemon off;", ports=[80], mounts=mounts, entrypoint="nginx")
    url = f"http://127.0.0.1:{lab.port(alias, 80)}"
    lab.wait_http(alias, url + "/healthz", headers={"Host": HOST})
    return url


def new_lab() -> DockerLab:
    ex.require_image(NGINX)
    ex.require_image(PYTHON)
    lab = DockerLab()
    lab.open()
    for alias in BACKENDS:
        start_backend(lab, alias)
    return lab


@pytest.fixture(scope="module")
def lab():
    lab = None
    try:
        lab = new_lab()
        yield lab
    finally:
        if lab:
            lab.close()


@pytest.fixture
def fresh_lab():
    lab = None
    try:
        lab = new_lab()
        yield lab
    finally:
        if lab:
            lab.close()


@pytest.fixture(scope="module")
def proxy(lab, tmp_path_factory):
    return start_nginx(lab, "nginx", ex.path("nginx.conf"), tmp_path_factory.mktemp("conf"))


def get(url: str, path: str) -> httpx.Response:
    return httpx.get(url + path, headers={"Host": HOST}, timeout=10)


def distribution_problems(url: str) -> list[str]:
    responses = [get(url, "/healthz") for _ in range(40)]
    bad = [r.status_code for r in responses if r.status_code != 200]
    if bad:
        return [f"40 request GET /healthz phải đều 200, có mã {sorted(set(bad))}"]
    counts = Counter(r.json()["instance"] for r in responses)
    if not 8 <= counts["olist-api-1"] <= 12 or not 28 <= counts["olist-api-2"] <= 32:
        return [f"40 request phải chia theo tỉ lệ 1:3 (olist-api-1 khoảng 10, olist-api-2 khoảng 30); đang là {dict(counts)}"]
    return []


def upstream_servers(effective_config: str) -> list[str]:
    match = re.search(r"upstream\s+olist_api\s*\{(.*?)\}", effective_config, re.S)
    if not match:
        return []
    return [line.strip() for line in match.group(1).splitlines() if line.strip().startswith("server ")]


def config_problems(effective_config: str) -> list[str]:
    servers = upstream_servers(effective_config)
    found = []
    for backend in BACKENDS:
        line = next((s for s in servers if f"{backend}:8000" in s), None)
        if line is None:
            found.append(f"upstream olist_api thiếu server {backend}:8000")
        elif f"max_fails={MAX_FAILS}" not in line or "fail_timeout=30s" not in line:
            found.append(f"Server {backend} cần max_fails={MAX_FAILS} fail_timeout=30s, đang là: {line}")
        elif backend == "olist-api-2" and "weight=3" not in line:
            found.append(f"Server olist-api-2 cần weight=3, đang là: {line}")
    return found


def attempts_to(log_lines: list[str], ip: str) -> int:
    fields = [re.search(r" up=(.*?) ust=", line) for line in log_lines]
    return sum(1 for f in fields if f and f"{ip}:8000" in [a.strip() for a in re.split(r"[,:] ", f.group(1))])


def passive_health_problems(lab: DockerLab, alias: str, url: str) -> list[str]:
    dead_ip = lab.ip("olist-api-2")
    for _ in range(4):
        get(url, "/healthz")
    killed = lab.exec("olist-api-2", "pkill", "-f", "backend.py")
    assert killed.returncode == 0, f"Không dừng được tiến trình backend olist-api-2: {killed.stderr}"
    before = len(lab.logs(alias).splitlines())
    responses = [get(url, f"/orders/o{i}") for i in range(20)]
    lines = [line for line in lab.logs(alias).splitlines()[before:] if "/orders/o" in line and " up=" in line]
    found = []
    bad = [r.status_code for r in responses if r.status_code != 200]
    if bad:
        found.append(f"Một backend chết thì client không được thấy lỗi: 20 request phải đều 200, có {len(bad)} mã {sorted(set(bad))}")
    if len(lines) != 20:
        return found + [f"Access log phải có đúng 20 dòng cho 20 request (format có up=$upstream_addr), thấy {len(lines)}"]
    tried = attempts_to(lines, dead_ip)
    if tried == 0:
        found.append("Nginx không thử olist-api-2 lần nào: backend thứ hai có trong upstream không?")
    if tried > MAX_FAILS:
        found.append(f"Nginx thử backend đã chết {tried} lần trong 20 request; với max_fails={MAX_FAILS} phải đánh dấu "
                     f"backend tạm hỏng sau tối đa {MAX_FAILS} lần thử lỗi")
    if attempts_to(lines[10:], dead_ip):
        found.append("Trong 10 request cuối Nginx vẫn thử backend đã chết: fail_timeout phải giữ backend ngoài vòng quay")
    return found


def test_requests_spread_over_both_backends(proxy):
    found = distribution_problems(proxy)
    assert not found, "\n".join(found)


def test_upstream_server_parameters(lab, proxy):
    dump = lab.exec("nginx", "nginx", "-T")
    assert dump.returncode == 0, dump.stderr
    found = config_problems(dump.stdout)
    assert not found, "\n".join(found)


def test_passive_health_check_when_backend_dies(fresh_lab, tmp_path):
    url = start_nginx(fresh_lab, "nginx", ex.path("nginx.conf"), tmp_path)
    found = passive_health_problems(fresh_lab, "nginx", url)
    assert not found, "\n".join(found)


def test_checks_catch_starter_config(fresh_lab, tmp_path):
    url = start_nginx(fresh_lab, "starter", FIXTURES / "nginx.starter.conf", tmp_path)
    assert distribution_problems(url)
    dump = fresh_lab.exec("starter", "nginx", "-T")
    assert config_problems(dump.stdout)
    assert any("olist-api-2" in p for p in passive_health_problems(fresh_lab, "starter", url))

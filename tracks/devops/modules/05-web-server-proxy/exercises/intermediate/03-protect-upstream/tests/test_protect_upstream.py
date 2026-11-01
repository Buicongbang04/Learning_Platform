import shutil
import time
from pathlib import Path

import httpx
import pytest

from testkit import DockerLab, Exercise

ex = Exercise(__file__)
NGINX = "nginx:1.30.6-alpine"
PYTHON = "python:3.12.16-alpine3.24"
FIXTURES = Path(__file__).parent / "fixtures"
HOST = "shop.olist.test"
STATS = "/stats/revenue-by-state"


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


@pytest.fixture(scope="module")
def lab():
    ex.require_image(NGINX)
    ex.require_image(PYTHON)
    with DockerLab() as lab:
        start_backend(lab, "olist-api-1")
        yield lab


@pytest.fixture(scope="module")
def proxy(lab, tmp_path_factory):
    return start_nginx(lab, "nginx", ex.path("nginx.conf"), tmp_path_factory.mktemp("conf"))


def call(url: str, method: str, path: str, timeout: float = 15, **headers: str) -> httpx.Response:
    return httpx.request(method, url + path, headers={"Host": HOST, **headers}, timeout=timeout)


def rate_limit_problems(url: str) -> list[str]:
    with httpx.Client(headers={"Host": HOST}, timeout=10) as client:
        statuses = [client.post(url + "/jobs/recompute").status_code for _ in range(15)]
        reads = [client.get(url + "/orders/o42").status_code for _ in range(20)]
    found = []
    if statuses[:6] != [202] * 6:
        found.append(f"6 POST /jobs/recompute đầu tiên (1 + burst 5) phải 202, đang là {statuses[:6]}")
    if statuses.count(429) < 5 or set(statuses) - {202, 429}:
        found.append(f"Vượt giới hạn phải trả 429 (không phải 503), cần ít nhất 5 mã 429 trong 15 request; đang là {statuses}")
    if set(reads) != {200}:
        found.append(f"GET /orders/... không bị giới hạn: 20 request liên tiếp phải đều 200, đang là {sorted(set(reads))}")
    return found


def cache_problems(url: str) -> list[str]:
    steps = [
        ("lần đầu", {}, "MISS"),
        ("lần hai", {}, "HIT"),
        ("có X-Cache-Bypass: 1", {"X-Cache-Bypass": "1"}, "BYPASS"),
        ("sau bypass", {}, "HIT"),
    ]
    seen = []
    for label, headers, expected in steps:
        response = call(url, "GET", STATS, **headers)
        status = response.headers.get("x-cache-status")
        if response.status_code != 200 or status != expected:
            return [f"GET {STATS} {label}: mong 200 và X-Cache-Status {expected}, nhận {response.status_code} {status!r}"]
        seen.append(response.json()["served"])
    found = []
    if seen[1] != seen[0]:
        found.append(f"HIT phải trả đúng bản đã cache (backend phục vụ lần {seen[0]}), nhận bản lần {seen[1]}")
    if seen[2] != seen[0] + 1:
        found.append("BYPASS phải đi tới backend lấy bản mới")
    if seen[3] != seen[2]:
        found.append("Response lấy được khi bypass phải được lưu lại: request thường ngay sau đó phải HIT bản mới")
    first, second = call(url, "GET", "/orders/o7"), call(url, "GET", "/orders/o7")
    if second.json()["served"] == first.json()["served"] or second.headers.get("x-cache-status") == "HIT":
        found.append("GET /orders/{id} là dữ liệu từng đơn, không được cache")
    return found


def timeout_problems(url: str) -> list[str]:
    found = []
    start = time.monotonic()
    try:
        response = call(url, "GET", "/slow?seconds=6", timeout=20)
        status = response.status_code
    except httpx.TimeoutException:
        status = "client timeout"
    elapsed = time.monotonic() - start
    if status != 504 or not 2.5 <= elapsed <= 5.5:
        found.append(f"Backend trả lời sau 6 giây: Nginx phải trả 504 sau khoảng 3 giây (proxy_read_timeout 3s), "
                     f"nhận {status} sau {elapsed:.1f} giây")
    response = call(url, "GET", "/slow?seconds=1")
    if response.status_code != 200:
        found.append(f"Backend trả lời sau 1 giây vẫn trong timeout: phải 200, nhận {response.status_code}")
    return found


def test_rate_limit_on_jobs(proxy):
    found = rate_limit_problems(proxy)
    assert not found, "\n".join(found)


def test_stats_cached_with_bypass(proxy):
    found = cache_problems(proxy)
    assert not found, "\n".join(found)


def test_slow_upstream_times_out_with_504(proxy):
    found = timeout_problems(proxy)
    assert not found, "\n".join(found)


def test_checks_catch_starter_config(lab, tmp_path):
    url = start_nginx(lab, "starter", FIXTURES / "nginx.starter.conf", tmp_path)
    assert rate_limit_problems(url)
    assert cache_problems(url)
    assert timeout_problems(url)

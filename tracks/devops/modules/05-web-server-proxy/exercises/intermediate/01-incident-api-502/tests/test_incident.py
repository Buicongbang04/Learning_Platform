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
    lab.wait_http(alias, url + "/", headers={"Host": HOST})
    return url


@pytest.fixture(scope="module")
def lab():
    ex.require_image(NGINX)
    ex.require_image(PYTHON)
    lab = DockerLab()
    try:
        lab.open()
        for alias in BACKENDS:
            start_backend(lab, alias)
        yield lab
    finally:
        lab.close()


@pytest.fixture(scope="module")
def proxy(lab, tmp_path_factory):
    return start_nginx(lab, "nginx", ex.path("nginx.conf"), tmp_path_factory.mktemp("conf"))


def call(url: str, method: str, path: str) -> httpx.Response:
    return httpx.request(method, url + path, headers={"Host": HOST}, timeout=10)


def evidence(lab: DockerLab, alias: str) -> str:
    lines = lab.logs(alias).splitlines()
    return "\nLog Nginx gần nhất (bằng chứng để chẩn đoán):\n" + "\n".join(lines[-8:])


API_CASES = [
    ("GET", "/api/healthz", 200, "/healthz"),
    ("GET", "/api/orders/e481f51cbdc5?expand=items", 200, "/orders/e481f51cbdc5?expand=items"),
    ("GET", "/api/stats/revenue-by-state", 200, "/stats/revenue-by-state"),
    ("POST", "/api/jobs/recompute", 202, "/jobs/recompute"),
]


def api_problems(url: str) -> list[str]:
    found = []
    for method, path, status, backend_path in API_CASES:
        response = call(url, method, path)
        if response.status_code != status:
            found.append(f"{method} {path}: mong {status}, nhận {response.status_code}")
            continue
        body = response.json()
        if body.get("path") != backend_path:
            found.append(f"{method} {path}: backend phải nhận {backend_path}, nhận {body.get('path')}")
    return found


def balance_problems(url: str) -> list[str]:
    responses = [call(url, "GET", "/api/healthz") for _ in range(10)]
    if any(r.status_code != 200 for r in responses):
        return ["10 request GET /api/healthz phải đều 200"]
    counts = Counter(r.json().get("instance") for r in responses)
    if set(counts) != set(BACKENDS):
        return [f"Request /api/ phải tới cả hai backend như trước sự cố, đang là {dict(counts)}"]
    return []


def frontend_problems(url: str) -> list[str]:
    found = []
    for path in ("/", "/checkout/cart"):
        response = call(url, "GET", path)
        if response.status_code != 200 or "text/html" not in response.headers.get("content-type", ""):
            found.append(f"GET {path}: frontend tĩnh phải vẫn 200 text/html, nhận {response.status_code} {response.headers.get('content-type')}")
    return found


def health_problems(url: str) -> list[str]:
    response = call(url, "GET", "/healthz")
    try:
        body = response.json()
    except ValueError:
        body = {}
    if response.status_code != 200 or body.get("status") != "ok" or body.get("instance") not in BACKENDS:
        return [f"GET /healthz (health check của load balancer) phải do API trả lời (JSON status ok từ backend), "
                f"nhận {response.status_code} {response.text[:80]!r}"]
    return []


def test_api_routes_answer_again(lab, proxy):
    found = api_problems(proxy)
    assert not found, "\n".join(found) + evidence(lab, "nginx")


def test_api_still_load_balanced(lab, proxy):
    found = balance_problems(proxy)
    assert not found, "\n".join(found) + evidence(lab, "nginx")


def test_frontend_unaffected(proxy):
    found = frontend_problems(proxy)
    assert not found, "\n".join(found)


def test_health_check_reflects_api(lab, proxy):
    found = health_problems(proxy)
    assert not found, "\n".join(found) + evidence(lab, "nginx")


def test_incident_config_reproduces_symptoms(lab, tmp_path):
    url = start_nginx(lab, "incident", FIXTURES / "nginx.incident.conf", tmp_path)
    assert call(url, "GET", "/api/healthz").status_code == 502
    assert not frontend_problems(url)
    assert call(url, "GET", "/healthz").status_code == 200
    assert api_problems(url)
    assert health_problems(url)

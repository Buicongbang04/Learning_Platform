import ipaddress
import re
import shutil
import uuid
from pathlib import Path

import httpx
import pytest

from testkit import DockerLab, Exercise

ex = Exercise(__file__)
NGINX = "nginx:1.30.6-alpine"
PYTHON = "python:3.12.16-alpine3.24"
FIXTURES = Path(__file__).parent / "fixtures"
HOST = "shop.olist.test"
GENERATED_ID = re.compile(r"^[0-9a-f]{32}$")


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
def lab(tmp_path_factory):
    ex.require_image(NGINX)
    ex.require_image(PYTHON)
    lab = DockerLab()
    try:
        lab.open()
        start_backend(lab, "olist-api-1")
        yield lab
    finally:
        lab.close()


@pytest.fixture(scope="module")
def proxy(lab, tmp_path_factory):
    return start_nginx(lab, "nginx", ex.path("nginx.conf"), tmp_path_factory.mktemp("conf"))


def get(url: str, path: str, host: str = HOST, **headers: str) -> httpx.Response:
    return httpx.get(url + path, headers={"Host": host, **headers}, timeout=10)


def backend_view(response: httpx.Response) -> dict:
    assert response.status_code == 200, f"Mong 200 từ backend, nhận {response.status_code}: {response.text[:300]}"
    return response.json()


def forwarding_problems(url: str) -> list[str]:
    found = []
    body = backend_view(get(url, "/orders/abc123?expand=items"))
    if body["path"] != "/orders/abc123?expand=items":
        found.append(f"Backend phải nhận nguyên path và query /orders/abc123?expand=items, nhận {body['path']}")
    if body["host"] != HOST:
        found.append(f"Header Host tới backend phải là {HOST}, đang là {body['host']!r}")
    if body["x_forwarded_proto"] != "http":
        found.append(f"X-Forwarded-Proto phải là http, đang là {body['x_forwarded_proto']!r}")
    return found


def client_ip_problems(url: str) -> list[str]:
    body = backend_view(get(url, "/healthz", **{"X-Forwarded-For": "6.6.6.6", "X-Real-IP": "6.6.6.6"}))
    xff, real_ip = body["x_forwarded_for"], body["x_real_ip"]
    if not xff or "6.6.6.6" in xff:
        return [f"X-Forwarded-For tới backend là {xff!r}: Nginx là tầng ngoài cùng nên phải ghi đè bằng IP client thật, bỏ giá trị client tự gửi"]
    if not real_ip or "6.6.6.6" in real_ip:
        return [f"X-Real-IP tới backend là {real_ip!r}: phải là IP client thật Nginx thấy"]
    found = []
    try:
        ipaddress.ip_address(xff)
    except ValueError:
        found.append(f"X-Forwarded-For phải đúng một địa chỉ IP, đang là {xff!r}")
    if xff != real_ip:
        found.append(f"X-Forwarded-For ({xff}) và X-Real-IP ({real_ip}) phải là cùng IP client")
    return found


def request_id_problems(url: str, logs) -> list[str]:
    found = []
    kept = f"checkout-{uuid.uuid4().hex[:8]}.retry_1"
    response = get(url, "/healthz", **{"X-Request-ID": kept})
    body = backend_view(response)
    if body["x_request_id"] != kept:
        found.append(f"X-Request-ID hợp lệ của client phải tới backend nguyên vẹn, backend nhận {body['x_request_id']!r}")
    if response.headers.get_list("x-request-id") != [kept]:
        found.append(f"Response phải có đúng một X-Request-ID = {kept}, đang là {response.headers.get_list('x-request-id')}")
    for label, headers in (("không gửi", {}), ("có khoảng trắng", {"X-Request-ID": "abc def"}), ("dài 65 ký tự", {"X-Request-ID": "a" * 65})):
        response = get(url, "/healthz", **headers)
        received = backend_view(response)["x_request_id"]
        if not received or not GENERATED_ID.match(received):
            found.append(f"Client {label} X-Request-ID: Nginx phải sinh id 32 ký tự hex ($request_id), backend nhận {received!r}")
        elif response.headers.get_list("x-request-id") != [received]:
            found.append(f"Client {label} X-Request-ID: response phải trả đúng id backend nhận ({received})")
        elif received not in logs():
            found.append(f"Access log của Nginx phải ghi id mà backend nhận ({received}), để lần theo request qua hai tầng")
    if kept not in logs():
        found.append(f"Access log của Nginx phải ghi id client gửi khi hợp lệ ({kept})")
    return found


def unknown_host_problems(url: str) -> list[str]:
    try:
        response = get(url, "/healthz", host="evil.example")
    except httpx.RemoteProtocolError:
        return []
    if response.status_code == 421:
        return []
    return [f"Host lạ (evil.example) không được tới backend: trả 421 hoặc đóng kết nối (444), đang là {response.status_code}"]


def server_header_problems(url: str) -> list[str]:
    server = get(url, "/healthz").headers.get("server")
    return [] if server == "nginx" else [f"Header Server phải là 'nginx' không kèm phiên bản, đang là {server!r}"]


def test_host_path_and_proto_forwarded(proxy):
    found = forwarding_problems(proxy)
    assert not found, "\n".join(found)


def test_client_ip_cannot_be_spoofed(proxy):
    found = client_ip_problems(proxy)
    assert not found, "\n".join(found)


def test_request_id_propagated_and_logged(lab, proxy):
    found = request_id_problems(proxy, lambda: lab.logs("nginx"))
    assert not found, "\n".join(found)


def test_unknown_host_rejected(proxy):
    found = unknown_host_problems(proxy)
    assert not found, "\n".join(found)


def test_server_version_hidden(proxy):
    found = server_header_problems(proxy)
    assert not found, "\n".join(found)


def test_checks_catch_starter_config(lab, tmp_path):
    url = start_nginx(lab, "starter", FIXTURES / "nginx.starter.conf", tmp_path)
    assert any("X-Forwarded-For" in p for p in client_ip_problems(url))
    assert any("X-Request-ID" in p for p in request_id_problems(url, lambda: lab.logs("starter")))
    assert unknown_host_problems(url)
    assert server_header_problems(url)
    assert any("Host" in p for p in forwarding_problems(url))

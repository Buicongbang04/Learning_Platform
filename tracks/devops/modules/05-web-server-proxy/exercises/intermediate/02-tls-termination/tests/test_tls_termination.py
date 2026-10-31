import datetime as dt
import re
import shutil
import socket
import ssl
from pathlib import Path

import httpx
import pytest
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.x509.oid import ExtendedKeyUsageOID, NameOID

from testkit import DockerLab, Exercise

ex = Exercise(__file__)
NGINX = "nginx:1.30.6-alpine"
PYTHON = "python:3.12.16-alpine3.24"
FIXTURES = Path(__file__).parent / "fixtures"
HOST = "shop.olist.test"
TOKEN = "Xk2-olist-acme-token"
ONE_YEAR = 31536000


def start_backend(lab: DockerLab, alias: str) -> None:
    lab.start(alias, PYTHON, "sh", "-c", "python /srv/backend.py; exec sleep 86400",
              mounts=[(FIXTURES / "backend.py", "/srv/backend.py")], env={"INSTANCE": alias})
    lab.wait_log(alias, "ready")


def make_pki(base: Path) -> Path:
    now = dt.datetime.now(dt.timezone.utc)
    ca_key, leaf_key = ec.generate_private_key(ec.SECP256R1()), ec.generate_private_key(ec.SECP256R1())
    ca_name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "Olist Lab Test CA")])
    ca = (
        x509.CertificateBuilder().subject_name(ca_name).issuer_name(ca_name).public_key(ca_key.public_key())
        .serial_number(x509.random_serial_number()).not_valid_before(now - dt.timedelta(days=1))
        .not_valid_after(now + dt.timedelta(days=30))
        .add_extension(x509.BasicConstraints(ca=True, path_length=0), critical=True)
        .sign(ca_key, hashes.SHA256())
    )
    leaf = (
        x509.CertificateBuilder().subject_name(x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, HOST)]))
        .issuer_name(ca_name).public_key(leaf_key.public_key()).serial_number(x509.random_serial_number())
        .not_valid_before(now - dt.timedelta(days=1)).not_valid_after(now + dt.timedelta(days=30))
        .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
        .add_extension(x509.ExtendedKeyUsage([ExtendedKeyUsageOID.SERVER_AUTH]), critical=False)
        .add_extension(x509.SubjectAlternativeName([x509.DNSName(HOST)]), critical=False)
        .sign(ca_key, hashes.SHA256())
    )
    tls = base / "tls"
    tls.mkdir(parents=True)
    (tls / "fullchain.pem").write_bytes(leaf.public_bytes(serialization.Encoding.PEM))
    (tls / "privkey.pem").write_bytes(leaf_key.private_bytes(
        serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()))
    (tls / "privkey.pem").chmod(0o644)
    (base / "ca.pem").write_bytes(ca.public_bytes(serialization.Encoding.PEM))
    acme = base / "acme" / ".well-known" / "acme-challenge"
    acme.mkdir(parents=True)
    (acme / TOKEN).write_text(f"{TOKEN}.thumbprint\n")
    return base


class Edge:
    def __init__(self, http_url: str, https_port: int, ca: Path):
        self.http_url = http_url
        self.https_port = https_port
        self.ca = ca

    def context(self) -> ssl.SSLContext:
        return ssl.create_default_context(cafile=str(self.ca))

    def https(self, method: str, path: str) -> httpx.Response:
        with httpx.Client(verify=self.context(), timeout=10) as client:
            return client.request(method, f"https://127.0.0.1:{self.https_port}{path}", headers={"Host": HOST},
                                  extensions={"sni_hostname": HOST})

    def http(self, method: str, path: str) -> httpx.Response:
        return httpx.request(method, self.http_url + path, headers={"Host": HOST}, timeout=10)

    def handshake(self, server_name: str | None, alpn: list[str] | None = None) -> str:
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
        if alpn:
            context.set_alpn_protocols(alpn)
        try:
            with socket.create_connection(("127.0.0.1", self.https_port), timeout=10) as raw:
                with context.wrap_socket(raw, server_hostname=server_name) as tls:
                    return f"ok {tls.selected_alpn_protocol()}"
        except (ssl.SSLError, OSError) as exc:
            return f"rejected {exc.__class__.__name__}"


def start_edge(lab: DockerLab, alias: str, conf: Path, workdir: Path) -> Edge:
    pki = make_pki(workdir)
    copy = workdir / "nginx.conf"
    shutil.copyfile(conf, copy)
    mounts = [(copy, "/etc/nginx/nginx.conf"), (pki / "tls", "/etc/nginx/tls"), (pki / "acme", "/var/www/acme")]
    check = lab.run_once(f"{alias}-t", NGINX, "-t", mounts=mounts, entrypoint="nginx")
    assert check.returncode == 0, f"nginx -t báo lỗi:\n{check.stderr}"
    lab.start(alias, NGINX, "-g", "daemon off;", ports=[80, 443], mounts=mounts, entrypoint="nginx")
    http_url = f"http://127.0.0.1:{lab.port(alias, 80)}"
    lab.wait_http(alias, http_url + "/", headers={"Host": HOST})
    return Edge(http_url, lab.port(alias, 443), pki / "ca.pem")


@pytest.fixture(scope="module")
def lab():
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
def edge(lab, tmp_path_factory):
    return start_edge(lab, "nginx", ex.path("nginx.conf"), tmp_path_factory.mktemp("edge"))


def redirect_problems(edge: Edge) -> list[str]:
    found = []
    for method, path in (("GET", "/orders/abc?utm_source=email&x=1"), ("POST", "/jobs/recompute")):
        response = edge.http(method, path)
        expected = f"https://{HOST}{path}"
        if response.status_code not in (301, 308) or response.headers.get("location") != expected:
            found.append(f"HTTP {method} {path}: phải 301 hoặc 308 tới {expected}, nhận {response.status_code} "
                         f"Location={response.headers.get('location')!r}")
    return found


def acme_problems(edge: Edge) -> list[str]:
    response = edge.http("GET", f"/.well-known/acme-challenge/{TOKEN}")
    if response.status_code != 200 or response.text.strip() != f"{TOKEN}.thumbprint":
        return [f"HTTP /.well-known/acme-challenge/{TOKEN} phải trả 200 nội dung tệp trong /var/www/acme, không chuyển hướng; "
                f"nhận {response.status_code} Location={response.headers.get('location')!r}"]
    return []


def proxy_problems(edge: Edge) -> list[str]:
    try:
        response = edge.https("GET", "/orders/abc?x=1")
    except (httpx.HTTPError, ssl.SSLError) as exc:
        return [f"HTTPS tới {HOST} với SNI {HOST} lỗi: {exc!r}"]
    if response.status_code != 200:
        return [f"HTTPS GET /orders/abc?x=1 phải 200 từ backend, nhận {response.status_code}"]
    body = response.json()
    found = []
    if body["x_forwarded_proto"] != "https":
        found.append(f"Qua HTTPS, X-Forwarded-Proto tới backend phải là https, đang là {body['x_forwarded_proto']!r}")
    if body["host"] != HOST:
        found.append(f"Host tới backend phải là {HOST}, đang là {body['host']!r}")
    if body["path"] != "/orders/abc?x=1":
        found.append(f"Backend phải nhận /orders/abc?x=1, nhận {body['path']}")
    return found


def hsts_problems(edge: Edge) -> list[str]:
    found = []
    for path, status in (("/healthz", 200), ("/khong-co", 404)):
        try:
            response = edge.https("GET", path)
        except (httpx.HTTPError, ssl.SSLError) as exc:
            return [f"HTTPS GET {path} lỗi: {exc!r}"]
        header = response.headers.get("strict-transport-security", "")
        match = re.search(r"max-age=(\d+)", header)
        if response.status_code != status or not match or int(match.group(1)) < ONE_YEAR:
            found.append(f"HTTPS GET {path} ({response.status_code}): cần Strict-Transport-Security max-age >= {ONE_YEAR}, "
                         f"đang là {header!r}")
    return found


def http2_problems(edge: Edge) -> list[str]:
    result = edge.handshake(HOST, ["h2", "http/1.1"])
    return [] if result == "ok h2" else [f"Cổng 443 phải chọn HTTP/2 qua ALPN khi client mời h2, kết quả: {result}"]


def default_server_problems(edge: Edge) -> list[str]:
    found = []
    if not edge.handshake(HOST).startswith("ok"):
        found.append(f"Bắt tay TLS với SNI {HOST} phải thành công")
    for name in ("evil.example", None):
        result = edge.handshake(name)
        if result.startswith("ok"):
            found.append(f"Bắt tay TLS với SNI {name or '(không có SNI)'} phải bị từ chối, không được trả cert của {HOST}")
    return found


def test_http_redirects_to_https(edge):
    found = redirect_problems(edge)
    assert not found, "\n".join(found)


def test_acme_challenge_served_over_http(edge):
    found = acme_problems(edge)
    assert not found, "\n".join(found)


def test_https_proxies_with_forwarded_proto(edge):
    found = proxy_problems(edge)
    assert not found, "\n".join(found)


def test_hsts_on_every_https_response(edge):
    found = hsts_problems(edge)
    assert not found, "\n".join(found)


def test_http2_negotiated(edge):
    found = http2_problems(edge)
    assert not found, "\n".join(found)


def test_unknown_sni_rejected(edge):
    found = default_server_problems(edge)
    assert not found, "\n".join(found)


def test_checks_catch_starter_config(lab, tmp_path):
    edge = start_edge(lab, "starter", FIXTURES / "nginx.starter.conf", tmp_path)
    assert redirect_problems(edge)
    assert acme_problems(edge)
    assert proxy_problems(edge)
    assert hsts_problems(edge)
    assert http2_problems(edge)
    assert default_server_problems(edge)


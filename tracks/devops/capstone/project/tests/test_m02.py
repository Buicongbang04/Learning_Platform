"""M02: nginx/olist-shop.conf và nginx/gen-cert.sh. Hợp đồng đầy đủ ở capstone/milestones/m02-nginx-front.md."""

import datetime as dt
import ipaddress
import re
import shutil
import socket
import ssl
import stat
import subprocess
import time
import uuid
from dataclasses import dataclass
from pathlib import Path

import httpx
import pytest
from cryptography import x509
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.x509.oid import NameOID

from testkit import ROOT, DockerLab, Exercise, run_sandboxed

NGINX = "nginx:1.30.6-alpine"
PYTHON = "python:3.12.16-alpine3.24"
FIXTURES = Path(__file__).parent / "fixtures"
HOST = "olist-shop.local"
SAN_DNS = {"olist-shop.local", "localhost"}
SAN_IP = {ipaddress.ip_address("127.0.0.1")}
BASH = shutil.which("bash")
HEX32 = re.compile(r"^[0-9a-f]{32}$")
BURST_PROBE = 60


def require_file(path: Path) -> Path:
    if not path.is_file():
        shown = path.relative_to(ROOT) if path.is_relative_to(ROOT) else path
        pytest.fail(f"Chưa có tệp {shown}. Xem tracks/devops/capstone/milestones/m02-nginx-front.md")
    return path


def now() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


def make_cert(folder: Path, *, san: bool = True, days: int = 90, expired: bool = False) -> Path:
    """Cert tự ký do test tạo: dùng cho Nginx trong test và cho các ca hỏng (không SAN, hết hạn)."""
    folder.mkdir(parents=True, exist_ok=True)
    key = ec.generate_private_key(ec.SECP256R1())
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, HOST)])
    start = now() - dt.timedelta(days=days + 2 if expired else 1)
    builder = (
        x509.CertificateBuilder().subject_name(name).issuer_name(name).public_key(key.public_key())
        .serial_number(x509.random_serial_number()).not_valid_before(start)
        .not_valid_after(start + dt.timedelta(days=days))
    )
    if san:
        builder = builder.add_extension(x509.SubjectAlternativeName(
            [x509.DNSName(d) for d in sorted(SAN_DNS)] + [x509.IPAddress(i) for i in SAN_IP]), critical=False)
    cert = builder.sign(key, hashes.SHA256())
    (folder / "olist-shop.crt").write_bytes(cert.public_bytes(serialization.Encoding.PEM))
    (folder / "olist-shop.key").write_bytes(key.private_bytes(
        serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()))
    (folder / "olist-shop.key").chmod(0o600)
    return folder


def run_gen_cert(script: Path, tmp: Path, *args) -> subprocess.CompletedProcess:
    return run_sandboxed([BASH, script, *map(str, args)], writable=[tmp], cwd=tmp, env={}, timeout=60)


def public_der(public_key) -> bytes:
    return public_key.public_bytes(serialization.Encoding.DER, serialization.PublicFormat.SubjectPublicKeyInfo)


def cert_problems(folder: Path, output: str = "") -> list[str]:
    crt, key = folder / "olist-shop.crt", folder / "olist-shop.key"
    missing = [p.name for p in (crt, key) if not p.is_file()]
    if missing:
        return [f"Thiếu {missing} trong thư mục đích"]
    found = []
    if stat.S_IMODE(key.stat().st_mode) & 0o077:
        found.append(f"olist-shop.key phải chỉ chủ sở hữu đọc được (600), đang là {oct(stat.S_IMODE(key.stat().st_mode))}")
    if "PRIVATE KEY" in output:
        found.append("Không in private key ra stdout/stderr")
    try:
        cert = x509.load_pem_x509_certificate(crt.read_bytes())
        private = serialization.load_pem_private_key(key.read_bytes(), password=None)
    except ValueError as exc:
        return found + [f"Không đọc được cert/key PEM (key không được đặt mật khẩu): {exc}"]
    if public_der(private.public_key()) != public_der(cert.public_key()):
        found.append("olist-shop.key không khớp olist-shop.crt")
    try:
        if cert.issuer != cert.subject:
            raise ValueError("issuer khác subject")
        cert.verify_directly_issued_by(cert)
    except (ValueError, TypeError, InvalidSignature) as exc:
        found.append(f"Cert phải tự ký (issuer = subject, chữ ký kiểm được bằng chính public key): {exc}")
    try:
        san = cert.extensions.get_extension_for_class(x509.SubjectAlternativeName).value
        dns, ips = set(san.get_values_for_type(x509.DNSName)), set(san.get_values_for_type(x509.IPAddress))
    except x509.ExtensionNotFound:
        dns, ips = set(), set()
    if not SAN_DNS <= dns or not SAN_IP <= ips:
        found.append(f"subjectAltName phải có DNS:olist-shop.local, DNS:localhost, IP:127.0.0.1; đang có DNS={sorted(dns)} "
                     f"IP={sorted(map(str, ips))}")
    start, end = cert.not_valid_before_utc, cert.not_valid_after_utc
    if start > now() + dt.timedelta(minutes=5) or end < now() + dt.timedelta(days=30):
        found.append(f"Cert phải đang hiệu lực và còn ít nhất 30 ngày, đang là {start:%F} → {end:%F}")
    if end - start > dt.timedelta(days=398):
        found.append(f"Thời hạn cert tối đa 398 ngày, đang là {(end - start).days} ngày")
    return found


@dataclass
class Edge:
    lab: DockerLab | None = None
    http_port: int = 0
    https_port: int = 0
    cert: Path | None = None
    error: str = ""

    def require(self) -> None:
        if self.error:
            pytest.fail(self.error)

    def https(self, method: str, path: str, headers: dict | None = None, client: httpx.Client | None = None):
        own = client is None
        client = client or httpx.Client(verify=False, timeout=10)
        try:
            return client.request(method, f"https://127.0.0.1:{self.https_port}{path}",
                                  headers={"Host": HOST, **(headers or {})}, extensions={"sni_hostname": HOST})
        finally:
            if own:
                client.close()

    def http(self, method: str, path: str) -> httpx.Response:
        return httpx.request(method, f"http://127.0.0.1:{self.http_port}{path}", headers={"Host": HOST}, timeout=10)

    def served_cert(self) -> bytes:
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
        with socket.create_connection(("127.0.0.1", self.https_port), timeout=10) as raw:
            with context.wrap_socket(raw, server_hostname=HOST) as tls:
                return tls.getpeercert(binary_form=True)

    def wait_logs(self, alias: str, text: str, timeout: float = 10) -> bool:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if text in self.lab.logs(alias):
                return True
            time.sleep(0.2)
        return False


def start_edge(lab: DockerLab, conf: Path, work: Path) -> Edge:
    """Dựng backend `api:8000` và Nginx `edge` (cổng 80, 443) với cấu hình `conf` và cert test tự tạo."""
    work.mkdir(parents=True, exist_ok=True)
    copy = work / "olist-shop.conf"
    shutil.copyfile(conf, copy)
    tls = make_cert(work / "tls")
    (tls / "olist-shop.key").chmod(0o644)
    lab.start("api", PYTHON, "sh", "-c", "python /srv/backend.py; exec sleep 86400",
              mounts=[(FIXTURES / "backend.py", "/srv/backend.py")])
    lab.wait_log("api", "ready")
    mounts = [(copy, "/etc/nginx/conf.d/default.conf"), (tls, "/etc/nginx/tls")]
    check = lab.run_once("edge-t", NGINX, "-t", mounts=mounts, entrypoint="nginx")
    if check.returncode != 0:
        pytest.fail(f"nginx -t báo lỗi với {conf.name}:\n{check.stderr.strip()}")
    lab.start("edge", NGINX, "-g", "daemon off;", ports=[80, 443], mounts=mounts, entrypoint="nginx")
    edge = Edge(lab=lab, http_port=lab.port("edge", 80), https_port=lab.port("edge", 443), cert=tls / "olist-shop.crt")
    lab.wait_http("edge", f"http://127.0.0.1:{edge.http_port}/healthz", headers={"Host": HOST})
    return edge


def redirect_problems(edge: Edge) -> list[str]:
    found = []
    for method, path in (("GET", "/orders/abc?utm_source=email&x=1"), ("GET", "/"), ("POST", "/jobs/recompute")):
        response = edge.http(method, path)
        expected = f"https://{HOST}{path}"
        if response.status_code not in (301, 308) or response.headers.get("location") != expected:
            found.append(f"HTTP {method} {path}: phải 301 hoặc 308 tới {expected}, nhận {response.status_code} "
                         f"Location={response.headers.get('location')!r}")
    return found


def https_problems(edge: Edge) -> list[str]:
    try:
        response = edge.https("GET", "/orders/abc?x=1")
        served = edge.served_cert()
    except (httpx.HTTPError, ssl.SSLError, OSError) as exc:
        return [f"HTTPS tới {HOST} lỗi: {exc!r}"]
    expected = x509.load_pem_x509_certificate(edge.cert.read_bytes()).public_bytes(serialization.Encoding.DER)
    found = [] if served == expected else ["Cổng 443 phải dùng cert ở /etc/nginx/tls/olist-shop.crt"]
    if response.status_code != 200:
        return found + [f"HTTPS GET /orders/abc?x=1 phải 200 từ backend, nhận {response.status_code}"]
    body = response.json()
    checks = [
        ("path", "/orders/abc?x=1", body.get("path")),
        ("Host", HOST, body.get("host")),
        ("X-Forwarded-Proto", "https", body.get("x_forwarded_proto")),
    ]
    found += [f"Backend phải nhận {name} = {want!r}, nhận {got!r}" for name, want, got in checks if got != want]
    for name, key in (("X-Real-IP", "x_real_ip"), ("X-Forwarded-For", "x_forwarded_for")):
        if not body.get(key):
            found.append(f"Backend phải nhận header {name} (IP client)")
    return found


def request_id_problems(edge: Edge) -> list[str]:
    found = []
    sent = f"m02-{uuid.uuid4().hex[:12]}"
    for label, headers in (("có X-Request-ID", {"X-Request-ID": sent}), ("không có X-Request-ID", {})):
        try:
            response = edge.https("GET", "/healthz", headers=headers)
        except (httpx.HTTPError, ssl.SSLError, OSError) as exc:
            return found + [f"HTTPS GET /healthz lỗi: {exc!r}"]
        if response.status_code != 200:
            found.append(f"Request {label}: HTTPS GET /healthz phải 200, nhận {response.status_code}")
            continue
        got = response.json().get("x_request_id")
        if headers and got != sent:
            found.append(f"Client gửi X-Request-ID {sent}: backend phải nhận nguyên giá trị đó, nhận {got!r}")
        if not headers and not (got and HEX32.match(got)):
            found.append(f"Client không gửi X-Request-ID: Nginx phải tự sinh ($request_id, 32 hex) và gửi xuống backend, "
                         f"backend nhận {got!r}")
        echoed = response.headers.get_list("x-request-id")
        if got and echoed != [got]:
            found.append(f"Request {label}: response phải có đúng một header X-Request-ID = {got}, nhận {echoed}")
        if got and not edge.wait_logs("api", f'"request_id": "{got}"'):
            found.append(f"Request {label}: log của API không có request_id {got}")
        if got and not edge.wait_logs("edge", got):
            found.append(f"Request {label}: access log của Nginx phải ghi request id {got} để lần theo request")
    return found


def rate_limit_problems(edge: Edge) -> list[str]:
    statuses = []
    try:
        with httpx.Client(verify=False, timeout=10) as client:
            for _ in range(BURST_PROBE):
                statuses.append(edge.https("POST", "/jobs/recompute", client=client).status_code)
    except (httpx.HTTPError, ssl.SSLError, OSError) as exc:
        return [f"HTTPS POST /jobs/recompute lỗi: {exc!r}"]
    found = []
    if statuses[:3] != [202] * 3:
        found.append(f"3 POST /jobs/recompute đầu tiên phải 202 (burst ≥ 2, nodelay), nhận {statuses[:3]}")
    if 429 not in statuses or set(statuses) - {202, 429}:
        found.append(f"{BURST_PROBE} POST /jobs/recompute liên tiếp phải có 429 (không phải 503) và chỉ gồm 202/429, "
                     f"nhận {sorted(set(statuses))} ({statuses.count(429)} lần 429)")
    return found


def unlimited_problems(edge: Edge) -> list[str]:
    try:
        with httpx.Client(verify=False, timeout=10) as client:
            statuses = [edge.https("GET", "/healthz", client=client).status_code for _ in range(BURST_PROBE)]
    except (httpx.HTTPError, ssl.SSLError, OSError) as exc:
        return [f"HTTPS GET /healthz lỗi: {exc!r}"]
    if set(statuses) != {200}:
        return [f"Rate limit chỉ áp cho /jobs/: {BURST_PROBE} GET /healthz liên tiếp phải đều 200, nhận {sorted(set(statuses))}"]
    return []


@pytest.fixture(scope="module")
def edge(project_root, tmp_path_factory):
    conf = project_root / "nginx" / "olist-shop.conf"
    if not conf.is_file():
        shown = conf.relative_to(ROOT) if conf.is_relative_to(ROOT) else conf
        yield Edge(error=f"Chưa có tệp {shown}. Xem tracks/devops/capstone/milestones/m02-nginx-front.md")
        return
    Exercise.require_image(NGINX)
    Exercise.require_image(PYTHON)
    with DockerLab() as lab:
        try:
            edge = start_edge(lab, conf, tmp_path_factory.mktemp("m02-edge"))
        except pytest.fail.Exception as exc:
            edge = Edge(error=str(exc))
        yield edge


@pytest.fixture
def gen_cert_tools():
    if BASH is None:
        pytest.skip("Cần bash")
    Exercise.require_tool("openssl", min_version="1.1.1")


@pytest.mark.usefixtures("gen_cert_tools")
class TestM02Cert:
    def test_m02_cert_generated(self, project_root, tmp_path):
        script = require_file(project_root / "nginx" / "gen-cert.sh")
        result = run_gen_cert(script, tmp_path, tmp_path / "tls")
        assert result.returncode == 0, result.stdout + result.stderr
        found = cert_problems(tmp_path / "tls", result.stdout + result.stderr)
        assert not found, "\n".join(found)

    def test_m02_cert_idempotent(self, project_root, tmp_path):
        script = require_file(project_root / "nginx" / "gen-cert.sh")
        out = tmp_path / "tls"
        assert run_gen_cert(script, tmp_path, out).returncode == 0
        before = {p.name: p.read_bytes() for p in out.iterdir() if not p.name.startswith(".")}
        again = run_gen_cert(script, tmp_path, out)
        assert again.returncode == 0, again.stderr
        assert {p.name: p.read_bytes() for p in out.iterdir() if not p.name.startswith(".")} == before, (
            "Cert còn hạn và khớp key thì giữ nguyên cả hai tệp")

    @pytest.mark.parametrize("damage", ["expired", "mismatched-key", "missing-key"])
    def test_m02_cert_regenerated_when_unusable(self, project_root, tmp_path, damage):
        script = require_file(project_root / "nginx" / "gen-cert.sh")
        out = tmp_path / "tls"
        if damage == "expired":
            make_cert(out, expired=True)
        else:
            make_cert(out)
            if damage == "mismatched-key":
                other = make_cert(tmp_path / "other")
                (out / "olist-shop.key").write_bytes((other / "olist-shop.key").read_bytes())
            else:
                (out / "olist-shop.key").unlink()
        old = (out / "olist-shop.crt").read_bytes()
        result = run_gen_cert(script, tmp_path, out)
        assert result.returncode == 0, result.stdout + result.stderr
        assert (out / "olist-shop.crt").read_bytes() != old, f"Cert {damage}: phải tạo lại"
        found = cert_problems(out, result.stdout + result.stderr)
        assert not found, "\n".join(found)

    @pytest.mark.parametrize("args", [(), ("a", "b")])
    def test_m02_gen_cert_usage_errors(self, project_root, tmp_path, args):
        script = require_file(project_root / "nginx" / "gen-cert.sh")
        result = run_gen_cert(script, tmp_path, *args)
        assert result.returncode == 2, result.stdout + result.stderr
        assert result.stderr.startswith("Usage:")

    def test_m02_checks_catch_defective_certs(self, tmp_path):
        assert any("subjectAltName" in p for p in cert_problems(make_cert(tmp_path / "nosan", san=False)))
        assert any("30 ngày" in p for p in cert_problems(make_cert(tmp_path / "old", expired=True)))
        assert any("398" in p for p in cert_problems(make_cert(tmp_path / "long", days=3650)))
        script = FIXTURES / "defective" / "nginx" / "gen-cert.sh"
        result = run_gen_cert(script, tmp_path, tmp_path / "bad")
        assert result.returncode == 0, result.stderr
        found = cert_problems(tmp_path / "bad", result.stdout + result.stderr)
        assert any("600" in p for p in found), found
        assert any("subjectAltName" in p for p in found), found
        assert any("398" in p for p in found), found


def test_m02_shellcheck_gen_cert(project_root):
    script = require_file(project_root / "nginx" / "gen-cert.sh")
    Exercise.require_tool("shellcheck", min_version="0.9.0")
    result = subprocess.run(["shellcheck", "-S", "style", str(script)], capture_output=True, text=True)
    assert result.returncode == 0, result.stdout


def test_m02_nginx_starts(edge):
    edge.require()


def test_m02_http_redirects_to_https(edge):
    edge.require()
    found = redirect_problems(edge)
    assert not found, "\n".join(found)


def test_m02_https_proxies_to_api(edge):
    edge.require()
    found = https_problems(edge)
    assert not found, "\n".join(found)


def test_m02_request_id_end_to_end(edge):
    edge.require()
    found = request_id_problems(edge)
    assert not found, "\n".join(found)


def test_m02_rate_limit_on_jobs(edge):
    edge.require()
    found = rate_limit_problems(edge)
    assert not found, "\n".join(found)


def test_m02_other_paths_not_limited(edge):
    edge.require()
    found = unlimited_problems(edge)
    assert not found, "\n".join(found)


def test_m02_checks_catch_defective_config(tmp_path):
    """fixtures/defective/nginx/olist-shop.conf: proxy cả cổng 80, thiếu X-Forwarded-Proto, ghi đè X-Request-ID của
    client, không ghi request id vào access log, limit_req cho mọi path và trả 503."""
    Exercise.require_image(NGINX)
    Exercise.require_image(PYTHON)
    with DockerLab() as lab:
        edge = start_edge(lab, FIXTURES / "defective" / "nginx" / "olist-shop.conf", tmp_path)
        assert redirect_problems(edge)
        assert any("X-Forwarded-Proto" in p for p in https_problems(edge))
        time.sleep(1)
        assert any("nhận nguyên giá trị" in p for p in request_id_problems(edge))
        time.sleep(1)
        assert any("503" in p for p in rate_limit_problems(edge))
        time.sleep(1)
        assert unlimited_problems(edge)

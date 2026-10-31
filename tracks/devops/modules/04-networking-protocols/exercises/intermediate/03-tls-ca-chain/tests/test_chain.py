import datetime as dt
import hashlib
import ipaddress
import os
import shutil
import socket
import ssl
import subprocess
import threading
from pathlib import Path

import pytest
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec, rsa
from cryptography.x509.oid import ExtendedKeyUsageOID, NameOID

from testkit import Exercise, run_sandboxed, tool_version

ex = Exercise(__file__)
NAMES = {"shop.olist.test", "api.olist.test"}
IPS = {ipaddress.ip_address("127.0.0.1")}
FILES = ["root-ca.key", "root-ca.crt", "intermediate-ca.key", "intermediate-ca.crt", "server.key", "server.crt", "fullchain.pem"]
DAY = dt.timedelta(days=1)


@pytest.fixture(autouse=True)
def openssl():
    ex.require_tool("openssl", min_version="1.1.1")
    ex.require_tool("bash")


def isolated_env(home: Path) -> dict[str, str]:
    return {
        "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
        "HOME": str(home),
        "OPENSSL_CONF": "/dev/null",
        "SSL_CERT_FILE": str(home / "no-system-ca.pem"),
        "SSL_CERT_DIR": str(home / "no-system-ca"),
        "LANG": "C.UTF-8",
        "LC_ALL": "C.UTF-8",
    }


def make_chain(tmp_path: Path, out: Path):
    script = tmp_path / "make_chain.sh"
    shutil.copyfile(ex.path("make_chain.sh"), script)
    env = isolated_env(tmp_path)
    return run_sandboxed(["bash", script, out], writable=[tmp_path], cwd=tmp_path, env=env, timeout=120)


@pytest.fixture(scope="module")
def built(tmp_path_factory):
    tmp = tmp_path_factory.mktemp("chain")
    return make_chain(tmp, tmp / "pki"), tmp / "pki"


def ok(built) -> Path:
    result, pki = built
    assert result.returncode == 0, f"make_chain.sh exit {result.returncode}\nstderr:\n{result.stderr}"
    return pki


def openssl_verify(ca: Path, untrusted: Path | None, leaf: Path, *extra: str) -> subprocess.CompletedProcess:
    args = ["openssl", "verify", "-no-CApath", "-CAfile", str(ca)]
    if (tool_version("openssl") or (0,)) >= (3,):
        args.append("-no-CAstore")
    if untrusted:
        args += ["-untrusted", str(untrusted)]
    home = leaf.parent
    return subprocess.run([*args, *extra, str(leaf)], capture_output=True, text=True, env=isolated_env(home), timeout=30)


def load(path: Path) -> x509.Certificate:
    return x509.load_pem_x509_certificate(path.read_bytes())


def ext(cert: x509.Certificate, kind):
    try:
        return cert.extensions.get_extension_for_class(kind)
    except x509.ExtensionNotFound:
        return None


def ca_problems(name: str, cert: x509.Certificate, now: dt.datetime, min_days: int) -> list[str]:
    found = []
    bc = ext(cert, x509.BasicConstraints)
    if bc is None or not bc.critical or not bc.value.ca:
        found.append(f"{name}: basicConstraints phải critical, CA:TRUE")
    ku = ext(cert, x509.KeyUsage)
    if ku is None or not ku.critical or not ku.value.key_cert_sign or not ku.value.crl_sign:
        found.append(f"{name}: keyUsage phải critical, có keyCertSign và cRLSign")
    if cert.not_valid_before_utc > now + dt.timedelta(minutes=5) or cert.not_valid_after_utc < now + min_days * DAY:
        found.append(f"{name}: phải đang hiệu lực và còn ít nhất {min_days} ngày")
    return found


def key_problems(name: str, key) -> list[str]:
    if isinstance(key, rsa.RSAPublicKey) and key.key_size >= 2048:
        return []
    if isinstance(key, ec.EllipticCurvePublicKey) and key.curve.name in ("secp256r1", "secp384r1"):
        return []
    return [f"{name}: khoá phải là RSA >= 2048 hoặc EC P-256/P-384"]


def chain_problems(pki: Path, now: dt.datetime | None = None) -> list[str]:
    now = now or dt.datetime.now(dt.timezone.utc)
    missing = [f for f in FILES if not (pki / f).is_file()]
    if missing:
        return [f"thiếu tệp: {missing}"]
    found = []
    root, inter, leaf = load(pki / "root-ca.crt"), load(pki / "intermediate-ca.crt"), load(pki / "server.crt")
    found += ca_problems("root-ca.crt", root, now, 1825)
    if root.issuer != root.subject:
        found.append("root-ca.crt: phải tự ký (issuer = subject)")
    found += ca_problems("intermediate-ca.crt", inter, now, 365)
    bc = ext(inter, x509.BasicConstraints)
    if bc is not None and bc.value.path_length != 0:
        found.append("intermediate-ca.crt: basicConstraints phải có pathlen:0")
    if inter.issuer != root.subject:
        found.append("intermediate-ca.crt: phải do root-ca ký")
    if leaf.issuer != inter.subject:
        found.append("server.crt: phải do intermediate-ca ký, không phải root")
    if inter.not_valid_after_utc > root.not_valid_after_utc or leaf.not_valid_after_utc > inter.not_valid_after_utc:
        found.append("hạn của cert con không được vượt hạn của CA ký nó")

    bc = ext(leaf, x509.BasicConstraints)
    if bc is None or bc.value.ca:
        found.append("server.crt: basicConstraints phải có và là CA:FALSE")
    ku = ext(leaf, x509.KeyUsage)
    if ku is None or not ku.critical or not ku.value.digital_signature or ku.value.key_cert_sign or ku.value.crl_sign:
        found.append("server.crt: keyUsage phải critical, có digitalSignature, không có keyCertSign/cRLSign")
    elif ku.value.key_encipherment and not isinstance(leaf.public_key(), rsa.RSAPublicKey):
        found.append("server.crt: keyEncipherment chỉ hợp với khoá RSA")
    eku = ext(leaf, x509.ExtendedKeyUsage)
    if eku is None or ExtendedKeyUsageOID.SERVER_AUTH not in eku.value:
        found.append("server.crt: extendedKeyUsage phải có serverAuth")
    san = ext(leaf, x509.SubjectAlternativeName)
    dns_names = set(san.value.get_values_for_type(x509.DNSName)) if san else set()
    ips = set(san.value.get_values_for_type(x509.IPAddress)) if san else set()
    if dns_names != NAMES or ips != IPS:
        found.append(f"server.crt: SAN phải đúng DNS {sorted(NAMES)} và IP 127.0.0.1, đang là {sorted(dns_names)} {sorted(map(str, ips))}")
    if leaf.not_valid_before_utc > now + dt.timedelta(minutes=5) or leaf.not_valid_after_utc < now:
        found.append("server.crt: đã hết hạn hoặc chưa tới ngày hiệu lực")
    lifetime = leaf.not_valid_after_utc - max(leaf.not_valid_before_utc, now)
    if not 30 * DAY <= lifetime <= 397 * DAY:
        found.append("server.crt: thời hạn còn lại phải từ 30 tới 397 ngày")
    for name, cert in (("root-ca", root), ("intermediate-ca", inter), ("server", leaf)):
        found += key_problems(f"{name}.crt", cert.public_key())
        key = serialization.load_pem_private_key((pki / f"{name}.key").read_bytes(), password=None)
        if key.public_key().public_numbers() != cert.public_key().public_numbers():
            found.append(f"{name}.key không khớp {name}.crt")
        if (pki / f"{name}.key").stat().st_mode & 0o077:
            found.append(f"{name}.key: quyền phải là 600 (chỉ chủ sở hữu đọc được)")
    pem = (pki / "fullchain.pem").read_bytes()
    certs = x509.load_pem_x509_certificates(pem)
    if [c.fingerprint(hashes.SHA256()) for c in certs] != [leaf.fingerprint(hashes.SHA256()), inter.fingerprint(hashes.SHA256())]:
        found.append("fullchain.pem: phải đúng 2 cert theo thứ tự server.crt rồi intermediate-ca.crt, không kèm root")
    return found


class TLSServer:
    def __init__(self, certfile: Path, keyfile: Path):
        self.context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        self.context.load_cert_chain(certfile, keyfile)
        self.sock = socket.create_server(("127.0.0.1", 0))
        self.port = self.sock.getsockname()[1]
        self.thread = threading.Thread(target=self.serve, daemon=True)
        self.thread.start()

    def serve(self):
        self.sock.settimeout(10)
        while True:
            try:
                conn, _ = self.sock.accept()
            except OSError:
                return
            try:
                with self.context.wrap_socket(conn, server_side=True) as tls:
                    tls.sendall(b"ok")
            except (ssl.SSLError, OSError):
                conn.close()

    def close(self):
        self.sock.close()


def handshake(server: TLSServer, cafile: Path, hostname: str) -> str:
    context = ssl.create_default_context(cafile=str(cafile))
    context.minimum_version = ssl.TLSVersion.TLSv1_2
    try:
        with socket.create_connection(("127.0.0.1", server.port), timeout=10) as raw:
            with context.wrap_socket(raw, server_hostname=hostname) as tls:
                return tls.recv(2).decode()
    except ssl.SSLCertVerificationError as exc:
        return f"verify-failed: {exc.verify_message}"


@pytest.fixture
def served():
    servers = []

    def start(certfile: Path, keyfile: Path) -> TLSServer:
        servers.append(TLSServer(certfile, keyfile))
        return servers[-1]

    yield start
    for server in servers:
        server.close()


def test_chain_properties(built):
    chain = ok(built)
    found = chain_problems(chain)
    assert not found, "\n".join(found)


def test_openssl_verify(built):
    chain = ok(built)
    by_name = openssl_verify(chain / "root-ca.crt", chain / "intermediate-ca.crt", chain / "server.crt", "-verify_hostname", "shop.olist.test")
    assert by_name.returncode == 0, by_name.stdout + by_name.stderr
    by_ip = openssl_verify(chain / "root-ca.crt", chain / "intermediate-ca.crt", chain / "server.crt", "-verify_ip", "127.0.0.1")
    assert by_ip.returncode == 0, by_ip.stdout + by_ip.stderr
    no_intermediate = openssl_verify(chain / "root-ca.crt", None, chain / "server.crt")
    assert no_intermediate.returncode != 0, "Thiếu intermediate thì phải không xác minh được"
    wrong_name = openssl_verify(chain / "root-ca.crt", chain / "intermediate-ca.crt", chain / "server.crt", "-verify_hostname", "admin.olist.test")
    assert wrong_name.returncode != 0 and "hostname mismatch" in wrong_name.stdout + wrong_name.stderr


def test_tls_handshake_with_sni(built, served):
    chain = ok(built)
    server = served(chain / "fullchain.pem", chain / "server.key")
    for name in ("shop.olist.test", "api.olist.test", "127.0.0.1"):
        assert handshake(server, chain / "root-ca.crt", name) == "ok", name
    assert handshake(server, chain / "root-ca.crt", "admin.olist.test").startswith("verify-failed")


def test_leaf_only_server_fails(built, served):
    chain = ok(built)
    server = served(chain / "server.crt", chain / "server.key")
    assert handshake(server, chain / "root-ca.crt", "shop.olist.test").startswith("verify-failed"), (
        "Server chỉ gửi leaf (thiếu intermediate) thì client chỉ tin root phải thất bại"
    )


def test_refuses_to_overwrite_ca(built, tmp_path):
    chain = ok(built)
    copy = tmp_path / "pki"
    shutil.copytree(chain, copy)
    before = {f: hashlib.sha256((copy / f).read_bytes()).hexdigest() for f in FILES}
    result = make_chain(tmp_path, copy)
    assert result.returncode == 2, f"Chạy lại trên thư mục đã có root-ca.key phải exit 2, đang là {result.returncode}"
    assert before == {f: hashlib.sha256((copy / f).read_bytes()).hexdigest() for f in FILES}, "Không được ghi đè tệp nào"


def write_key(path: Path, key) -> None:
    path.write_bytes(key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()))
    path.chmod(0o600)


def issue(subject: str, key, issuer_cert, issuer_key, start, end, *, ca: bool, san=None, pathlen=None):
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, subject)])
    builder = (
        x509.CertificateBuilder()
        .subject_name(name)
        .issuer_name(issuer_cert.subject if issuer_cert else name)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(start)
        .not_valid_after(end)
        .add_extension(x509.BasicConstraints(ca=ca, path_length=pathlen), critical=True)
    )
    if ca:
        usage = dict(digital_signature=False, key_cert_sign=True, crl_sign=True)
    else:
        usage = dict(digital_signature=True, key_cert_sign=False, crl_sign=False)
        builder = builder.add_extension(x509.ExtendedKeyUsage([ExtendedKeyUsageOID.SERVER_AUTH]), critical=False)
    builder = builder.add_extension(
        x509.KeyUsage(content_commitment=False, key_encipherment=False, data_encipherment=False, key_agreement=False,
                      encipher_only=False, decipher_only=False, **usage),
        critical=True,
    )
    if san is not None:
        builder = builder.add_extension(x509.SubjectAlternativeName(san), critical=False)
    return builder.sign(issuer_key or key, hashes.SHA256())


def defective_pki(base: Path, defect: str) -> Path:
    now = dt.datetime.now(dt.timezone.utc)
    pki = base / defect
    pki.mkdir()
    keys = {n: ec.generate_private_key(ec.SECP256R1()) for n in ("root-ca", "intermediate-ca", "server")}
    root = issue("Lab Root", keys["root-ca"], None, None, now - DAY, now + 3650 * DAY, ca=True)
    inter = issue("Lab Intermediate", keys["intermediate-ca"], root, keys["root-ca"], now - DAY, now + 1825 * DAY, ca=True, pathlen=0)
    san = [x509.DNSName("shop.olist.test"), x509.DNSName("api.olist.test"), x509.IPAddress(ipaddress.ip_address("127.0.0.1"))]
    start, end = now - DAY, now + 90 * DAY
    if defect == "expired":
        start, end = now - 120 * DAY, now - DAY
    if defect == "wrong-san":
        san = [x509.DNSName("www.olist.test")]
    leaf = issue("shop.olist.test", keys["server"], inter, keys["intermediate-ca"], start, end, ca=defect == "leaf-is-ca", san=san)
    for name, cert in (("root-ca", root), ("intermediate-ca", inter), ("server", leaf)):
        (pki / f"{name}.crt").write_bytes(cert.public_bytes(serialization.Encoding.PEM))
        write_key(pki / f"{name}.key", keys[name])
    chain_certs = [leaf] if defect == "no-intermediate-in-fullchain" else [leaf, inter]
    (pki / "fullchain.pem").write_bytes(b"".join(c.public_bytes(serialization.Encoding.PEM) for c in chain_certs))
    return pki


@pytest.mark.parametrize(
    "defect,message",
    [
        ("expired", "server.crt: đã hết hạn"),
        ("wrong-san", "server.crt: SAN phải đúng"),
        ("leaf-is-ca", "server.crt: basicConstraints phải có và là CA:FALSE"),
        ("no-intermediate-in-fullchain", "fullchain.pem"),
    ],
)
def test_checks_catch_defective_chains(tmp_path, defect, message):
    good = chain_problems(defective_pki(tmp_path, "none"))
    assert good == [], f"Bộ cert mẫu không lỗi phải qua mọi phép kiểm: {good}"
    found = chain_problems(defective_pki(tmp_path, defect))
    assert any(p.startswith(message) for p in found), f"{defect}: phép kiểm phải bắt '{message}', bắt được {found}"


def test_expired_and_wrong_san_fail_in_openssl_and_tls(tmp_path, served):
    expired = defective_pki(tmp_path, "expired")
    result = openssl_verify(expired / "root-ca.crt", expired / "intermediate-ca.crt", expired / "server.crt")
    assert result.returncode != 0 and "expired" in (result.stdout + result.stderr).lower()
    server = served(expired / "fullchain.pem", expired / "server.key")
    assert "expired" in handshake(server, expired / "root-ca.crt", "shop.olist.test")
    wrong = defective_pki(tmp_path, "wrong-san")
    server = served(wrong / "fullchain.pem", wrong / "server.key")
    assert "mismatch" in handshake(server, wrong / "root-ca.crt", "shop.olist.test").lower()


def test_shellcheck_clean():
    ex.require_tool("shellcheck", min_version="0.9.0")
    script = ex.path("make_chain.sh")
    if "TODO" in script.read_text(encoding="utf-8"):
        pytest.fail("make_chain.sh còn TODO")
    result = subprocess.run(["shellcheck", "--norc", "-S", "style", "-s", "bash", str(script)], capture_output=True, text=True)
    assert result.returncode == 0, result.stdout

"""Ghi lại support bundle thật mà bệnh viện gửi cho bài 08/intermediate/02, vào `../customer-bundle/`.

Chạy từ gốc repo (cần snapshot dẫn xuất `08-field-troubleshooting-hospital`):

    PYTHONPATH=. uv run python tracks/fde/modules/08-field-troubleshooting/exercises/intermediate/02-repro-lab/tests/capture_bundle.py

Máy `hospital` đang chạy quillo 1.0.0; đồng nghiệp bật SSO với IdP nội bộ của bệnh viện. IdP được đóng vai bởi một
server HTTPS nhỏ phía host (chứng chỉ do CA nội bộ của lab cấp, đúng tên `sso.benhvien.local`), nối vào VM ở
`10.0.2.104:443` bằng `guestfwd` của QEMU; compose thêm `extra_hosts` vì bệnh viện không có DNS nội bộ cho máy này.
Nhân viên thử đăng nhập vài lần, rồi IT chạy `quillo-support.sh` như hướng dẫn của bạn.
"""

import datetime
import io
import json
import secrets
import shutil
import ssl
import subprocess
import tarfile
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import requests
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.x509.oid import NameOID

import fdekit

HERE = Path(__file__).resolve().parent
OUT = HERE.parent / "customer-bundle"
COLLECTOR = HERE.parents[1] / "01-field-incident" / "tools" / "quillo-support.sh"
QUILLO = "/home/fde/quillo-1.0.0"
IDP = "sso.benhvien.local"
ISSUER = f"https://{IDP}/realms/benhvien"


def certificates(work: Path) -> tuple[Path, Path]:
    now = datetime.datetime.now(datetime.timezone.utc)
    ca_key = ec.generate_private_key(ec.SECP256R1())
    ca_name = x509.Name([x509.NameAttribute(NameOID.ORGANIZATION_NAME, "Benh vien Lab"),
                         x509.NameAttribute(NameOID.COMMON_NAME, "Benh vien Internal Root CA")])
    ca = (x509.CertificateBuilder().subject_name(ca_name).issuer_name(ca_name).public_key(ca_key.public_key())
          .serial_number(x509.random_serial_number()).not_valid_before(now - datetime.timedelta(days=1))
          .not_valid_after(now + datetime.timedelta(days=365))
          .add_extension(x509.BasicConstraints(ca=True, path_length=None), critical=True)
          .sign(ca_key, hashes.SHA256()))
    key = ec.generate_private_key(ec.SECP256R1())
    leaf = (x509.CertificateBuilder().subject_name(x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, IDP)]))
            .issuer_name(ca_name).public_key(key.public_key()).serial_number(x509.random_serial_number())
            .not_valid_before(now - datetime.timedelta(days=1)).not_valid_after(now + datetime.timedelta(days=90))
            .add_extension(x509.SubjectAlternativeName([x509.DNSName(IDP)]), critical=False)
            .sign(ca_key, hashes.SHA256()))
    cert, private = work / "idp.pem", work / "idp.key"
    cert.write_bytes(leaf.public_bytes(serialization.Encoding.PEM))
    private.write_bytes(key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
                                          serialization.NoEncryption()))
    return cert, private


def idp_server(cert: Path, key: Path) -> ThreadingHTTPServer:
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args) -> None:
            pass

        def do_GET(self) -> None:
            body = json.dumps({"issuer": ISSUER, "jwks_uri": f"{ISSUER}/protocol/openid-connect/certs",
                               "authorization_endpoint": f"{ISSUER}/protocol/openid-connect/auth",
                               "token_endpoint": f"{ISSUER}/protocol/openid-connect/token"}).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain(cert, key)
    server.socket = context.wrap_socket(server.socket, server_side=True)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server


def sh(m: fdekit.VM, cmd: str, timeout: float = 180) -> str:
    done = m.ssh(cmd, timeout=timeout)
    if done.returncode != 0:
        raise SystemExit(f"lệnh lỗi: {cmd}\n{done.stdout}{done.stderr}")
    return done.stdout


def main() -> None:
    work = HERE / ".capture"
    work.mkdir(exist_ok=True)
    cert, key = certificates(work)
    server = idp_server(cert, key)
    port = server.server_address[1]
    try:
        with fdekit.vm("hospital", base=fdekit.derived("08-field-troubleshooting-hospital"), memory_mb=3072,
                       forwards=(18080,), guestfwds={"10.0.2.104:443": port}) as m:
            api = f"http://127.0.0.1:{m.port(18080)}"
            deadline = time.monotonic() + 180
            while requests.get(f"{api}/healthz", timeout=5).status_code != 200:
                if time.monotonic() > deadline:
                    raise SystemExit("quillo không healthy")
                time.sleep(2)
            override = (f"services:\n  api:\n    extra_hosts:\n      - \"{IDP}:10.0.2.104\"\n")
            (work / "compose.hosts.yaml").write_text(override)
            m.put(work / "compose.hosts.yaml", f"{QUILLO}/compose.hosts.yaml")
            (work / "client-secret").write_text(secrets.token_urlsafe(24))
            m.put(work / "client-secret", "/home/fde/client-secret")
            sh(m, f"set -e; cd {QUILLO}; sed -i -e '/^QUILLO_OIDC_ISSUER=/d' -e '/^QUILLO_OIDC_CLIENT_ID=/d' "
                  f"-e '/^QUILLO_ACL=/d' .env; printf '%s\\n' 'QUILLO_OIDC_ISSUER={ISSUER}' "
                  "'QUILLO_OIDC_CLIENT_ID=quillo' 'QUILLO_ACL=bacsi:noi-khoa/,dieuduong:dieu-duong/' >> .env; "
                  "sudo -n install -d -o 10001 -g 10001 -m 0700 oidc; "
                  "sudo -n install -o 10001 -g 10001 -m 0400 /home/fde/client-secret oidc/client-secret; "
                  "rm /home/fde/client-secret; "
                  "docker compose -f compose.yaml -f compose.sso.yaml -f compose.hosts.yaml up -d 2>&1")
            deadline = time.monotonic() + 180
            while True:
                try:
                    if requests.get(f"{api}/healthz", timeout=5).status_code == 200:
                        break
                except requests.RequestException:
                    pass
                if time.monotonic() > deadline:
                    raise SystemExit("quillo không healthy sau khi bật SSO")
                time.sleep(2)
            for _ in range(3):
                requests.get(f"{api}/oidc/login", allow_redirects=False, timeout=30)
                time.sleep(4)
            requests.get(f"{api}/login", timeout=30)
            command = [*m.ssh_command(), f"cd {QUILLO} && sh -s"]
            done = subprocess.run(command, input=COLLECTOR.read_bytes(), capture_output=True, timeout=180, check=True)
    finally:
        server.shutdown()
        shutil.rmtree(work, ignore_errors=True)
    shutil.rmtree(OUT, ignore_errors=True)
    with tarfile.open(fileobj=io.BytesIO(done.stdout), mode="r:gz") as tar:
        for member in tar.getmembers():
            if member.isfile():
                target = OUT / Path(*Path(member.name).parts[1:])
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(tar.extractfile(member).read())
    print(f"đã ghi {OUT}")


if __name__ == "__main__":
    main()

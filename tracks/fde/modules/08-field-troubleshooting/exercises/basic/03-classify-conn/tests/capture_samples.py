"""Ghi lại output thật của `curl -v`, `openssl s_client`, `getent` trên VM `hospital` và `bank` vào `samples/`.

Chạy từ gốc repo (cần golden `hospital`, `bank`, image mitmproxy và mạng ra internet phía host cho proxy):

    PYTHONPATH=. uv run python tracks/fde/modules/08-field-troubleshooting/exercises/basic/03-classify-conn/tests/capture_samples.py

Mỗi mẫu là `samples/<tên>.txt`: dòng đầu `$ <lệnh>` như khách dán vào ticket, sau đó là stdout+stderr nguyên văn.
Nhãn đúng của từng mẫu nằm trong `labels.json` (viết tay sau khi đọc output, không sinh từ script này).
"""

import secrets
import shlex
import sys
import time
from pathlib import Path

import fdekit
from testkit import DockerLab

HERE = Path(__file__).resolve().parent
SAMPLES = HERE / "samples"
PROXY = "10.0.2.100:3128"

LOCAL_TLS = r"""
set -e
d=$HOME/tlslab
rm -rf "$d"; mkdir -p "$d"; cd "$d"
openssl req -x509 -newkey rsa:2048 -nodes -days 30 -subj "/CN=BV Internal Root CA" -keyout ca.key -out ca.pem 2>/dev/null
openssl req -newkey rsa:2048 -nodes -subj "/CN=quillo.benhvien.local" -keyout leaf.key -out leaf.csr 2>/dev/null
printf 'subjectAltName=DNS:quillo.benhvien.local\n' > ext.cnf
openssl x509 -req -in leaf.csr -CA ca.pem -CAkey ca.key -CAcreateserial -days 30 -extfile ext.cnf -out leaf.pem 2>/dev/null
grep -q quillo.benhvien.local /etc/hosts || echo '127.0.0.1 quillo.benhvien.local' | sudo -n tee -a /etc/hosts >/dev/null
nohup openssl s_server -quiet -accept 8443 -cert leaf.pem -key leaf.key -www >/dev/null 2>&1 &
sleep 1
"""


def capture(machine, name: str, command: str, *, prefix: str = "") -> None:
    done = machine.ssh(f"{prefix}{command} 2>&1", timeout=90)
    text = f"$ {command}\n{done.stdout}"
    (SAMPLES / f"{name}.txt").write_text(text)
    print(f"{name}: exit {done.returncode}, {len(done.stdout)} byte", flush=True)


def hospital_site() -> None:
    with fdekit.customer_site("hospital") as site:
        m = site.vm
        m.put(site.proxy_ca, "/home/fde/proxy-ca.pem")
        env = ". /etc/environment; export http_proxy https_proxy no_proxy; "
        capture(m, "hospital-curl-pypi", "curl -v https://pypi.org/robots.txt -o /dev/null", prefix=env)
        capture(m, "hospital-curl-pypi-cacert", "curl -v --cacert ~/proxy-ca.pem https://pypi.org/robots.txt -o /dev/null",
                prefix=env)
        capture(m, "hospital-openssl-pypi",
                f"openssl s_client -connect pypi.org:443 -proxy {PROXY} -servername pypi.org -brief </dev/null")
        capture(m, "hospital-openssl-pypi-cafile",
                f"openssl s_client -connect pypi.org:443 -proxy {PROXY} -servername pypi.org -CAfile ~/proxy-ca.pem "
                "-verify_return_error -brief </dev/null")
        capture(m, "hospital-curl-noproxy-dns", "curl -v --noproxy '*' https://pypi.org/robots.txt -o /dev/null")
        capture(m, "hospital-getent-pypi", "getent hosts pypi.org")
        capture(m, "hospital-curl-proxy-timeout", "curl -v -m 8 https://10.255.255.1/ -o /dev/null", prefix=env)
        capture(m, "hospital-curl-proxy-timeout-http", "curl -v -m 8 http://10.255.255.1:8080/status", prefix=env)
        capture(m, "hospital-curl-refused", "curl -v http://127.0.0.1:18080/healthz", prefix=env)
        capture(m, "hospital-openssl-refused", "openssl s_client -connect 127.0.0.1:8444 -brief </dev/null")
        done = m.ssh(LOCAL_TLS, timeout=60)
        if done.returncode != 0:
            sys.exit(f"dựng TLS cục bộ lỗi: {done.stdout}{done.stderr}")
        capture(m, "hospital-curl-hostname", "curl -v --cacert ~/tlslab/ca.pem https://127.0.0.1:8443/ -o /dev/null",
                prefix=env)
        capture(m, "hospital-openssl-hostname",
                "openssl s_client -connect 127.0.0.1:8443 -CAfile ~/tlslab/ca.pem -verify_hostname 127.0.0.1 "
                "-brief </dev/null")
        internal = env + "no_proxy=$no_proxy,.benhvien.local; "
        capture(m, "hospital-curl-internal-ca", "curl -v https://quillo.benhvien.local:8443/ -o /dev/null",
                prefix=internal)
        capture(m, "hospital-openssl-internal-ca",
                "openssl s_client -connect quillo.benhvien.local:8443 -servername quillo.benhvien.local -brief "
                "</dev/null")
        capture(m, "hospital-curl-subnet-host", "curl -v --noproxy '*' --connect-timeout 10 http://10.0.2.77:8080/")


def hospital_auth_proxy() -> None:
    password = secrets.token_hex(8)
    with DockerLab() as lab:
        lab.start("authproxy", fdekit.MITMPROXY_IMAGE, "mitmdump", "--listen-host", "0.0.0.0", "--listen-port", "8080",
                  "--proxyauth", f"svc-proxy:{password}", ports=(8080,), env={"PYTHONUNBUFFERED": "1"}, memory="512m")
        port = lab.port("authproxy", 8080)
        time.sleep(4)
        with fdekit.vm("hospital", guestfwds={PROXY: port}) as m:
            env = ". /etc/environment; export http_proxy https_proxy no_proxy; "
            capture(m, "hospital-curl-proxy-407", "curl -v https://pypi.org/robots.txt -o /dev/null", prefix=env)
            capture(m, "hospital-curl-proxy-407-http", "curl -v http://archive.ubuntu.com/ubuntu/ -o /dev/null",
                    prefix=env)
            capture(m, "hospital-openssl-proxy-407",
                    f"openssl s_client -connect pypi.org:443 -proxy {PROXY} -servername pypi.org -brief </dev/null")
            capture(m, "hospital-curl-proxy-badpass",
                    "curl -v --proxy-user svc-proxy:" + shlex.quote("wrong-" + secrets.token_hex(3))
                    + " https://pypi.org/robots.txt -o /dev/null", prefix=env)


def bank() -> None:
    with fdekit.vm("bank") as m:
        capture(m, "bank-curl-dns", "curl -v https://pypi.org/robots.txt -o /dev/null")
        capture(m, "bank-getent-dns", "getent ahosts registry.npmjs.org")
        capture(m, "bank-openssl-dns", "openssl s_client -connect pypi.org:443 -brief </dev/null")
        capture(m, "bank-curl-noroute", "curl -v --connect-timeout 8 http://93.184.215.14/")
        capture(m, "bank-curl-noroute-https", "curl -v -m 8 https://151.101.0.223/ -o /dev/null")
        capture(m, "bank-curl-refused", "curl -v http://localhost:8080/healthz")
        capture(m, "bank-curl-subnet-host", "curl -v --connect-timeout 10 http://10.0.2.88:5432/")
        capture(m, "bank-getent-hosts-ok", "getent hosts localhost")


def main() -> None:
    SAMPLES.mkdir(exist_ok=True)
    which = set(sys.argv[1:]) or {"site", "auth", "bank"}
    if "site" in which:
        hospital_site()
    if "auth" in which:
        hospital_auth_proxy()
    if "bank" in which:
        bank()


if __name__ == "__main__":
    main()

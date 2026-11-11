"""Cảnh hiện trường của bài 08/intermediate/01: máy `hospital` chạy quillo, support bundle và kênh "nhờ khách gõ lệnh".

Dùng chung cho test (`test_field_incident.py`) và cho lúc bạn tự điều tra (chạy thẳng tệp test).
"""

import io
import json
import random
import re
import shlex
import subprocess
import tarfile
import time
from pathlib import Path

import pytest
import requests

import fdekit

HERE = Path(__file__).resolve().parent
EXERCISE = HERE.parent
COLLECTOR = EXERCISE / "tools" / "quillo-support.sh"
SNAPSHOT = "08-field-troubleshooting-hospital"
QUILLO = "/home/fde/quillo-1.0.0"
MEMORY_MB = 3072
COMMAND_TIMEOUT = 30
OUTPUT_LIMIT = 200_000
CAUSES = ("disk-full", "memory-pressure", "dns", "firewall-blocked", "proxy-misrouting", "tls-trust", "credentials",
          "permission", "resource-limit", "config-error", "product-bug")
SHELL_META = re.compile(r"[|;&$<>`\\\n\r]|\$\(")
SECRET_PATH = re.compile(r"(^|/|=)(\.env|\.ssh|oidc|shadow|gshadow|sudoers[^/]*|environ|private|[^/]*\.key|"
                         r"[^/]*secret[^/]*|[^/]*\.pem|\.bash_history)($|/)")
CURL_VALUE_OPTS = {"-m", "--max-time", "--connect-timeout", "-w", "--write-out", "--noproxy", "-H", "--header", "-A",
                   "--user-agent", "--retry", "--resolve", "--cacert", "--capath", "-x", "--proxy", "--interface"}
READ_ONLY = {"df", "du", "free", "uptime", "uname", "ps", "ss", "getent", "ls", "stat", "cat", "head", "tail", "grep",
             "wc", "find", "id", "date", "hostname", "lsblk", "findmnt", "dmesg", "ip", "journalctl", "systemctl",
             "docker", "curl", "openssl", "nproc", "mount"}
DOCKER_SUB = {"ps", "logs", "inspect", "images", "info", "version", "stats", "top", "port", "events"}
COMPOSE_SUB = {"ps", "logs", "config", "images", "top", "ls", "version", "port"}
NOUN_SUB = {"network": {"ls", "inspect"}, "volume": {"ls", "inspect"}, "system": {"df", "info"},
            "container": {"ls", "inspect", "logs", "top", "port"}, "image": {"ls", "inspect"}}
SYSTEMCTL_SUB = {"status", "show", "is-active", "is-failed", "list-units", "list-timers", "cat", "is-enabled"}
IP_SUB = {"addr", "address", "a", "route", "r", "link", "l", "neigh", "rule"}


def has_short(args: list[str], letters: str) -> bool:
    """Có cờ ngắn (kể cả gộp, vd. `-tf`) chứa một trong các chữ cái `letters`."""
    return any(a.startswith("-") and not a.startswith("--") and set(a[1:].split("=")[0]) & set(letters) for a in args)


def check_command(command: str) -> tuple[list[str] | None, str]:
    """(argv, "") nếu khách đồng ý gõ lệnh này, (None, lý do) nếu khách từ chối. Quy tắc nằm trong README của bài."""
    if not command.strip():
        return None, "lệnh rỗng"
    if SHELL_META.search(command):
        return None, "khách chỉ gõ một lệnh đơn: không pipe, không ;, &&, >, <, $(), backtick"
    try:
        argv = shlex.split(command)
    except ValueError as error:
        return None, f"không tách được lệnh: {error}"
    words = argv[1:] if argv[:1] == ["sudo"] else argv
    if not words or words[0] not in READ_ONLY:
        return None, f"khách chỉ chạy lệnh chỉ đọc trong danh sách: {', '.join(sorted(READ_ONLY))}"
    name, args = words[0], words[1:]
    for arg in args:
        if SECRET_PATH.search(arg):
            return None, f"khách không mở tệp chứa secret hay khoá: {arg}"
    if name == "docker":
        if args[:1] == ["compose"]:
            sub = [a for a in args[1:] if not a.startswith("-")][:1]
            if not sub or sub[0] not in COMPOSE_SUB:
                return None, f"docker compose chỉ được: {', '.join(sorted(COMPOSE_SUB))}"
        elif args[:1] and args[0] in NOUN_SUB:
            if len(args) < 2 or args[1] not in NOUN_SUB[args[0]]:
                return None, f"docker {args[0]} chỉ được: {', '.join(sorted(NOUN_SUB[args[0]]))}"
        elif not args or args[0] not in DOCKER_SUB:
            return None, f"docker chỉ được: {', '.join(sorted(DOCKER_SUB))}, compose …, network/volume/system/…"
        if args[:1] == ["stats"] and "--no-stream" not in args:
            return None, "docker stats phải có --no-stream"
        if args[:1] == ["events"] and not any(a.startswith("--until") for a in args):
            return None, "docker events phải có --until"
        if args[:1] in (["logs"], ["compose"], ["container"]) and ("--follow" in args or has_short(args, "f")):
            return None, "không theo dõi log liên tục (-f)"
        if args[:1] == ["compose"] and (has_short(args, "o") or any(a.startswith("--output") for a in args)):
            return None, "docker compose không ghi tệp (-o/--output)"
    elif name == "systemctl":
        sub = [a for a in args if not a.startswith("-")][:1]
        if not sub or sub[0] not in SYSTEMCTL_SUB:
            return None, f"systemctl chỉ được: {', '.join(sorted(SYSTEMCTL_SUB))}"
    elif name == "journalctl":
        if has_short(args, "f") or any(a.startswith(("--vacuum", "--rotate", "--flush", "--sync", "--relinquish",
                                                          "--follow", "--setup-keys", "--update-catalog", "--new-id128"))
                                         for a in args):
            return None, "journalctl chỉ đọc, không -f, --vacuum…, --rotate…, --setup-keys…"
    elif name == "ip":
        sub = [a for a in args if not a.startswith("-")]
        if sub and (sub[0] not in IP_SUB or any(a in ("add", "del", "delete", "change", "replace", "set", "flush")
                                                for a in sub[1:])):
            return None, f"ip chỉ xem: {', '.join(sorted(IP_SUB))}"
    elif name == "find":
        if any(a in ("-exec", "-execdir", "-ok", "-okdir", "-delete", "-fprint", "-fprintf", "-fls", "-fprint0")
               for a in args):
            return None, "find không được -exec/-delete/-fprint…"
    elif name == "curl":
        targets, skip = [], False
        for a in args:
            if skip:
                skip = False
            elif a in CURL_VALUE_OPTS:
                skip = True
            elif not a.startswith("-"):
                targets.append(a)
        if not targets or any(not re.match(r"^https?://(127\.0\.0\.1|localhost)(:\d+)?(/|$)", u) for u in targets):
            return None, "curl chỉ tới http(s)://127.0.0.1 hoặc http(s)://localhost của chính máy đó"
        long_bad = ("--output", "--remote-name", "--upload", "--data", "--json", "--form", "--config", "--request",
                    "--cookie-jar", "--dump-header", "--trace", "--stderr", "--libcurl", "--etag-save", "--create-dirs")
        if any(a.startswith(long_bad) or (a.startswith("-") and not a.startswith("--") and set(a[1:]) & set("oOTdFKXcDJ"))
               for a in args):
            return None, "curl chỉ GET/HEAD, không ghi tệp, không gửi dữ liệu"
    elif name == "openssl":
        if args[:1] not in (["s_client"], ["x509"], ["version"]):
            return None, "openssl chỉ s_client, x509, version"
        if any(a in ("-out", "-sess_out", "-keylogfile", "-msgfile", "-signkey", "-req", "-CAcreateserial", "-writerand")
               for a in args[1:]):
            return None, "openssl chỉ đọc, không ghi tệp"
    elif name == "ss" and any(a in ("-K", "--kill") or (a.startswith("-") and not a.startswith("--") and "K" in a)
                              for a in args):
        return None, "ss chỉ xem, không -K"
    elif name == "dmesg" and any(a.startswith(("-c", "-C", "--clear", "--read-clear", "-w", "--follow", "-n",
                                                "--console", "-D", "-E")) for a in args):
        return None, "dmesg chỉ đọc"
    elif name == "mount" and args:
        return None, "mount chỉ để xem (không đối số)"
    elif name == "tail" and (has_short(args, "fF") or any(a.startswith("--follow") for a in args)):
        return None, "tail không -f"
    elif name == "grep" and (has_short(args, "rR") or any(a.startswith(("--recursive", "--dereference-recursive"))
                                                          for a in args)):
        return None, "grep không đệ quy (-r): chỉ đọc tệp cụ thể"
    elif name == "date" and (has_short(args, "s") or any(a.startswith("--set") for a in args)):
        return None, "date chỉ xem"
    elif name == "hostname" and any(a not in ("-f", "-i", "-I", "-s", "-d", "-A", "--fqdn", "--short") for a in args):
        return None, "hostname chỉ xem (-f, -i, -I, -s, -d, -A)"
    return argv, ""


def pick_scenario(seed: int, names: list[str]) -> str:
    return sorted(names)[random.Random(seed).randrange(len(names))]


class Scene:
    """Máy `hospital` của khách (snapshot dẫn xuất có quillo 1.0.0) cùng các thao tác test cần để dựng sự cố."""

    def __init__(self, site: fdekit.Site, seed: int) -> None:
        self.site = site
        self.vm = site.vm
        self.seed = seed
        self.rng = random.Random(seed)
        self.api = f"http://127.0.0.1:{site.vm.port(18080)}"
        self.admin = ""
        self.hidden: list[str] = []

    def sh(self, cmd: str, timeout: float = 60) -> subprocess.CompletedProcess:
        for attempt in range(3):
            try:
                done = self.vm.ssh(cmd, timeout=timeout)
            except subprocess.TimeoutExpired:
                pytest.fail(f"Lệnh dựng cảnh trong VM chạy quá {timeout:.0f} s: {cmd[:150]}")
            if done.returncode != 255 or attempt == 2:
                return done
            time.sleep(2)
        return done

    def must(self, cmd: str, what: str, timeout: float = 120) -> str:
        done = self.sh(cmd, timeout=timeout)
        if done.returncode != 0:
            pytest.fail(f"Không dựng được cảnh (bước {what}); chạy lại, lặp lại thì báo lỗi bộ chấm")
        return done.stdout

    def health(self) -> tuple[int | None, dict]:
        try:
            response = requests.get(f"{self.api}/healthz", timeout=5)
            return response.status_code, response.json()
        except (requests.RequestException, ValueError):
            return None, {}

    def wait_health(self, timeout: float = 150) -> None:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if self.health()[0] == 200:
                self.admin = self.must(f"sed -n 's/^QUILLO_ADMIN_TOKEN=//p' {QUILLO}/.env", "token quản trị").strip()
                password = self.must(f"sed -n 's/^QUILLO_DB_PASSWORD=//p' {QUILLO}/.env", "mật khẩu db").strip()
                self.hidden = [value for value in (self.admin, password) if value]
                return
            time.sleep(2)
        logs = self.sh(f"cd {QUILLO} && docker compose ps -a", timeout=60).stdout
        pytest.fail(f"quillo của snapshot không lên /healthz 200 sau {timeout:.0f} s\n{logs[-2000:]}")

    def wait_api(self, timeout: float = 120) -> None:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if self.health()[0] is not None:
                return
            time.sleep(2)
        pytest.fail(f"api của quillo không trả lời sau {timeout:.0f} s khi dựng cảnh")

    def ask(self, question: str) -> int | None:
        try:
            return requests.post(f"{self.api}/api/ask", headers={"Authorization": f"Bearer {self.admin}"},
                                 json={"question": question, "top_k": 3}, timeout=120).status_code
        except requests.RequestException:
            return None

    def drop(self, names: list[str], words: int) -> None:
        """Thả tài liệu vào inbox như nhân viên khoa xét nghiệm."""
        buffer = io.BytesIO()
        with tarfile.open(fileobj=buffer, mode="w") as tar:
            for name in names:
                body = " ".join(f"Bệnh nhân {self.rng.randint(1000, 9999)} kết quả xét nghiệm "
                                f"{self.rng.choice(['máu', 'nước tiểu', 'sinh hoá', 'vi sinh'])} "
                                f"chỉ số {self.rng.randint(1, 300)}." for _ in range(words)).encode()
                info = tarfile.TarInfo(name)
                info.size, info.mtime, info.mode, info.uid, info.gid = len(body), time.time(), 0o644, 10001, 10001
                tar.addfile(info, io.BytesIO(body))
        command = [*self.vm.ssh_command(), f"sudo -n tar -x --same-owner -C {QUILLO}/inbox -f -"]
        done = subprocess.run(command, input=buffer.getvalue(), capture_output=True, timeout=60)
        if done.returncode != 0:
            pytest.fail(f"Không thả được tài liệu vào inbox khi dựng cảnh: {done.stderr.decode(errors='replace')}")

    def wait_log(self, service: str, needle: str, timeout: float, what: str) -> None:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            logs = self.sh(f"cd {QUILLO} && docker compose logs --no-color --since 15m {service}", timeout=60).stdout
            if needle in logs:
                return
            time.sleep(3)
        pytest.fail(f"Dựng cảnh không thành sau {timeout:.0f} s (bước {what}); chạy lại, lặp lại thì báo lỗi bộ chấm")

    def bundle(self, dest: Path) -> dict[str, str]:
        """Khách chạy quillo-support.sh trong thư mục cài (user fde, không sudo) và gửi lại bundle."""
        script = COLLECTOR.read_bytes()
        command = [*self.vm.ssh_command(), f"cd {QUILLO} && sh -s"]
        for attempt in range(3):
            done = subprocess.run(command, input=script, capture_output=True, timeout=180)
            if done.returncode == 0 and done.stdout:
                break
            if attempt == 2:
                pytest.fail(f"quillo-support.sh lỗi khi dựng cảnh: {done.stderr.decode(errors='replace')[-1500:]}")
            time.sleep(2)
        dest.write_bytes(done.stdout)
        files: dict[str, str] = {}
        with tarfile.open(fileobj=io.BytesIO(done.stdout), mode="r:gz") as tar:
            for member in tar.getmembers():
                if member.isfile():
                    files["/".join(Path(member.name).parts[1:])] = tar.extractfile(member).read().decode(
                        "utf-8", errors="replace")
        return files

    def customer_runs(self, command: str) -> tuple[bool, str]:
        """Khách gõ một lệnh (đã qua check_command) trong thư mục cài quillo; trước khi dán, khách che hai secret của bản
        cài (token quản trị và mật khẩu database trong .env)."""
        argv, reason = check_command(command)
        if argv is None:
            return False, reason
        argv = ["/home/fde/" + a[2:] if a.startswith("~/") else a for a in argv]
        if argv[0] == "sudo":
            argv = ["sudo", "-n", *argv[1:]]
        line = f"cd {QUILLO} && timeout {COMMAND_TIMEOUT} {shlex.join(argv)} 2>&1"
        done = self.sh(line, timeout=COMMAND_TIMEOUT + 30)
        output = done.stdout
        for value in self.hidden:
            output = output.replace(value, "***")
        output = output[:OUTPUT_LIMIT]
        if done.returncode == 124:
            output += f"\n(khách: lệnh chạy quá {COMMAND_TIMEOUT} s, đã dừng)"
        return True, output


def extract(bundle: dict[str, str], dest: Path) -> None:
    for name, text in bundle.items():
        path = dest / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)


def log_line(path: Path, record: dict) -> None:
    with path.open("a") as handle:
        handle.write(json.dumps(record, ensure_ascii=False) + "\n")

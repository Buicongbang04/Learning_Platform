"""Ghi lại log thật của quillo 1.0.0 trong một buổi có sự cố, vào `logs/<tên>.log`.

Chạy từ gốc repo (cần snapshot dẫn xuất `07-customer-integration-quillo`):

    PYTHONPATH=. uv run python tracks/fde/modules/08-field-troubleshooting/exercises/basic/02-triage-logs/tests/capture_logs.py

Hai buổi trên `lab-open`, mỗi buổi một VM mới từ snapshot. Người vận hành (script này) dùng quillo như khách: thả tài
liệu vào inbox, hỏi qua `/api/ask`, và làm hỏng hạ tầng bằng `docker compose stop/start` từng dịch vụ một lúc. Tệp log
là output nguyên văn của `docker compose logs --no-color` lấy ở cuối buổi.
"""

import io
import random
import sys
import tarfile
import time
from pathlib import Path

import requests

import fdekit

HERE = Path(__file__).resolve().parent
QUILLO = "/home/fde/quillo-1.0.0"
WORDS = ("hợp đồng", "bảo mật", "thanh toán", "bồi thường", "chấm dứt", "bất khả kháng", "phạt vi phạm", "gia hạn")


class Session:
    def __init__(self, site: fdekit.Site, seed: int) -> None:
        self.vm = site.vm
        self.api = f"http://127.0.0.1:{site.vm.port(18080)}"
        self.rng = random.Random(seed)
        self.token = self.sh(f"sed -n 's/^QUILLO_ADMIN_TOKEN=//p' {QUILLO}/.env").strip()
        self.n = 0

    def sh(self, cmd: str, timeout: float = 120) -> str:
        done = self.vm.ssh(cmd, timeout=timeout)
        if done.returncode != 0:
            sys.exit(f"lệnh lỗi: {cmd}\n{done.stdout}{done.stderr}")
        return done.stdout

    def wait_health(self, timeout: float = 240) -> None:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            try:
                if requests.get(f"{self.api}/healthz", timeout=5).status_code == 200:
                    return
            except requests.RequestException:
                pass
            time.sleep(2)
        sys.exit("quillo không healthy")

    def drop(self, count: int, *, broken: bool = False) -> None:
        buffer = io.BytesIO()
        with tarfile.open(fileobj=buffer, mode="w") as tar:
            for _ in range(count):
                self.n += 1
                if broken:
                    name, data = f"scan-{self.n:03d}.pdf", b"%PDF-1.4\n" + self.rng.randbytes(3000)
                else:
                    name = f"hop-dong-{self.n:03d}.txt"
                    data = " ".join(f"Điều {i}: {self.rng.choice(WORDS)} trong {self.rng.randint(5, 90)} ngày."
                                    for i in range(1, 40)).encode()
                info = tarfile.TarInfo(name)
                info.size, info.mtime, info.mode = len(data), time.time() - 3600, 0o644
                tar.addfile(info, io.BytesIO(data))
        local = HERE / ".drop.tar"
        local.write_bytes(buffer.getvalue())
        self.vm.put(local, "/home/fde/drop.tar")
        local.unlink()
        self.sh(f"cd {QUILLO} && sudo -n tar -x --no-same-owner -C inbox -f /home/fde/drop.tar && "
                "sudo -n chown -R 10001:10001 inbox && rm /home/fde/drop.tar")

    def ask(self, count: int = 1) -> None:
        for _ in range(count):
            try:
                requests.post(f"{self.api}/api/ask", headers={"Authorization": f"Bearer {self.token}"},
                              json={"question": f"Điều khoản {self.rng.choice(WORDS)} là gì?", "top_k": 3}, timeout=120)
            except requests.RequestException:
                pass

    def compose(self, action: str) -> None:
        self.sh(f"cd {QUILLO} && docker compose {action}", timeout=180)

    def logs(self, name: str) -> None:
        text = self.sh(f"cd {QUILLO} && docker compose logs --no-color", timeout=120)
        (HERE / "logs" / f"{name}.log").write_text(text)
        print(f"{name}: {len(text.splitlines())} dòng", flush=True)


def run(name: str, seed: int, plan) -> None:
    with fdekit.customer_site("lab-open", base=fdekit.derived("07-customer-integration-quillo"), memory_mb=3072,
                              forwards=(18080,)) as site:
        session = Session(site, seed)
        session.wait_health()
        plan(session)
        session.logs(name)


def morning(s: Session) -> None:
    s.drop(3)
    time.sleep(35)
    s.ask(2)
    s.compose("stop embed")
    s.ask(2)
    s.drop(2)
    time.sleep(45)
    s.ask(1)
    s.compose("start embed")
    time.sleep(50)
    s.drop(1, broken=True)
    time.sleep(25)
    s.ask(2)


def evening(s: Session) -> None:
    s.drop(2)
    time.sleep(30)
    s.compose("stop db")
    s.ask(2)
    s.drop(2)
    time.sleep(40)
    s.compose("start db")
    time.sleep(40)
    s.ask(1)
    s.compose("stop llm")
    s.ask(2)
    time.sleep(70)
    s.compose("start llm")
    time.sleep(30)
    s.ask(1)


def main() -> None:
    (HERE / "logs").mkdir(exist_ok=True)
    which = set(sys.argv[1:]) or {"morning", "evening"}
    if "morning" in which:
        run("lab-morning", 8101, morning)
    if "evening" in which:
        run("lab-evening", 8102, evening)


if __name__ == "__main__":
    main()

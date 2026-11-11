"""Nâng cấp quillo 1.0.0 → 1.1.0 tại chỗ ở bệnh viện rồi rollback. Chạy thẳng tệp này từ gốc repo
(`PYTHONPATH=. uv run python <tệp>`) để dựng đúng máy của test và tự thử: in lệnh SSH, cổng quillo, chờ Enter."""

import hashlib
import secrets
import shlex
import subprocess
import sys
import threading
import time
from pathlib import Path

import pytest
import requests

import fdekit
from testkit import ROOT, Exercise, run_sandboxed

ex = Exercise(__file__)
SNAPSHOT = "09-production-trust-hospital"
MEMORY_MB = 3072
INSTALL = "/home/fde/quillo-1.0.0"
ARCHIVE = "/home/fde/quillo-1.0.0.tar"
DIST = ROOT / "tracks" / "fde" / "product" / "dist"
BUNDLE = DIST / "quillo-1.1.0.tar"
OLD_BUNDLE = DIST / "quillo-1.0.0.tar"
BUILD = "nice -n 15 uv run python tracks/fde/product/release.py build --version {v} --out tracks/fde/product/dist"
MIN_FREE_PCT = 15
UPGRADE_TIMEOUT = 150
ROLLBACK_TIMEOUT = 120
HEALTH_TIMEOUT = 120
OLD_CONTRACT = "vat-tu/Distributor Agreement Fuse Medical.txt"
OLD_QUESTION = "Which state's law governs the distributor agreement with Fuse Medical?"
DUMP_MAGIC = b"PGDMP"
DATA_MARKERS = (b"COPY public.documents", b"INSERT INTO public.documents", b"COPY public.chunks")


def sh(m: fdekit.VM, cmd: str, timeout: float = 60) -> subprocess.CompletedProcess:
    for attempt in range(3):
        try:
            done = m.ssh(cmd, timeout=timeout)
        except subprocess.TimeoutExpired:
            pytest.fail(f"Lệnh trong VM chạy quá {timeout:.0f} s: {cmd[:150]}")
        if done.returncode != 255 or attempt == 2:
            return done
        time.sleep(2)
    return done


def file_sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


class Watch:
    """Đo đĩa trống của `/` mỗi 2 s qua một phiên SSH riêng, như hệ thống giám sát của bệnh viện."""

    def __init__(self, m: fdekit.VM) -> None:
        self.samples: list[tuple[int, int]] = []
        script = "while :; do df -B1 --output=size,avail / | tail -n 1; sleep 2; done"
        self.proc = subprocess.Popen([*m.ssh_command(), script], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                                     stdin=subprocess.DEVNULL, text=True)
        self.thread = threading.Thread(target=self._read, daemon=True)
        self.thread.start()

    def _read(self) -> None:
        for line in self.proc.stdout:
            parts = line.split()
            if len(parts) == 2 and all(p.isdigit() for p in parts):
                self.samples.append((int(parts[0]), int(parts[1])))

    def stop(self) -> None:
        self.proc.terminate()
        try:
            self.proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            self.proc.kill()

    def check(self, step: str) -> None:
        assert len(self.samples) >= 3, f"{step}: giám sát đĩa không đo được (SSH tới máy lỗi?)"
        size = self.samples[0][0]
        floor = size * MIN_FREE_PCT // 100
        low = min(avail for _, avail in self.samples)
        assert low >= floor, (f"{step}: đĩa / có lúc chỉ còn {low:,} byte trống, dưới mức {MIN_FREE_PCT}% "
                              f"({floor:,} byte) mà bệnh viện yêu cầu giữ trong cửa sổ bảo trì")


class Hospital:
    def __init__(self, site: fdekit.Site, work: Path) -> None:
        self.vm = site.vm
        self.work = work
        self.api = f"http://127.0.0.1:{site.vm.port(18080)}"
        self.token = sh(self.vm, f"sed -n 's/^QUILLO_ADMIN_TOKEN=//p' {INSTALL}/.env").stdout.strip()
        assert len(self.token) >= 16, "Không đọc được QUILLO_ADMIN_TOKEN trong .env của snapshot"

    def health(self, version: str, label: str, timeout: float = HEALTH_TIMEOUT) -> None:
        deadline = time.monotonic() + timeout
        last = ""
        while time.monotonic() < deadline:
            try:
                response = requests.get(f"{self.api}/healthz", timeout=5)
                body = response.json() if response.headers.get("content-type", "").startswith("application/json") \
                    else {}
                if response.status_code == 200 and body.get("version") == version:
                    return
                last = f"HTTP {response.status_code} {response.text[:200]}"
            except requests.RequestException as error:
                last = type(error).__name__
            time.sleep(2)
        logs = sh(self.vm, f"cd {INSTALL} && docker compose ps -a; docker compose logs --tail 20 api", timeout=60)
        pytest.fail(f"{label}: quillo không trả /healthz 200 với version {version} sau {timeout:.0f} s ({last})\n"
                    f"{logs.stdout[-3000:]}{logs.stderr[-500:]}")

    def sql(self, query: str) -> str:
        done = sh(self.vm, f"cd {INSTALL} && docker compose exec -T db psql -X -q -At -U quillo -d quillo "
                           f"-c {shlex.quote(query)}", timeout=60)
        assert done.returncode == 0, f"psql trong container db lỗi: {done.stderr[-500:]}"
        return done.stdout.strip()

    def counts(self) -> tuple[int, int]:
        return int(self.sql("SELECT count(*) FROM documents")), int(self.sql("SELECT count(*) FROM chunks"))

    def schema(self) -> int:
        return int(self.sql("SELECT coalesce(max(version), 0) FROM schema_migrations"))

    def doc_id(self, filename: str) -> str:
        response = requests.get(f"{self.api}/api/documents", headers={"Authorization": f"Bearer {self.token}"},
                                timeout=30)
        assert response.status_code == 200, f"GET /api/documents trả {response.status_code}: {response.text[:300]}"
        found = [d["doc_id"] for d in response.json() if d["filename"] == filename]
        assert found, f"Không thấy tài liệu {filename} trong /api/documents"
        return found[0]

    def cited(self, question: str, label: str) -> set[str]:
        response = requests.post(f"{self.api}/api/ask", headers={"Authorization": f"Bearer {self.token}"},
                                 json={"question": question, "top_k": 4}, timeout=120)
        assert response.status_code == 200, f"{label}: /api/ask trả {response.status_code}: {response.text[:300]}"
        return {c["doc_id"] for c in response.json().get("citations", [])}

    def upload(self, name: str, text: str, tags: list[str]) -> str:
        response = requests.post(f"{self.api}/api/documents", headers={"Authorization": f"Bearer {self.token}"},
                                 data={"folder": "vat-tu", "tags": ",".join(tags)},
                                 files={"file": (name, text.encode("utf-8"), "text/plain")}, timeout=180)
        assert response.status_code == 201, f"Nạp tài liệu trên 1.1.0 trả {response.status_code}: {response.text[:300]}"
        return response.json()["doc_id"]

    def secrets(self) -> str:
        return sh(self.vm, f"grep -E '^(QUILLO_ADMIN_TOKEN|QUILLO_DB_PASSWORD)=' {INSTALL}/.env | sort").stdout

    def run(self, script: str, work: Path, timeout: float, step: str) -> None:
        env = {"SSH": shlex.join(self.vm.ssh_command()), "BUNDLE": str(BUNDLE), "WORK": str(work)}
        try:
            done = run_sandboxed(["sh", script], writable=[work], cwd=work, env=env, timeout=timeout, input="")
        except subprocess.TimeoutExpired:
            pytest.fail(f"{step} chạy quá {timeout} s")
        assert done.returncode == 0, (f"{step} thoát {done.returncode}\n--- stdout ---\n{done.stdout[-2500:]}\n"
                                      f"--- stderr ---\n{done.stderr[-2500:]}")

    def dumps(self) -> list[str]:
        listed = sh(self.vm, "ls -1t /home/fde/backups/*.dump 2>/dev/null").stdout.split()
        return [path for path in listed if path.endswith(".dump")]

    def dump_state(self, path: str) -> tuple[int, int, int]:
        quoted = shlex.quote(path)
        check = sh(self.vm, f"cd {shlex.quote(str(Path(path).parent))} && sha256sum -c {shlex.quote(Path(path).name)}.sha256",
                   timeout=60)
        assert check.returncode == 0, f"{path}: sha256 không khớp tệp .sha256 đi kèm ({check.stdout}{check.stderr})"
        db = "restore_check"
        self.sql(f"DROP DATABASE IF EXISTS {db}")
        self.sql(f"CREATE DATABASE {db}")
        try:
            done = sh(self.vm, f"cd {INSTALL} && docker compose exec -T db pg_restore -U quillo -d {db} --no-owner "
                               f"< {quoted}", timeout=120)
            assert done.returncode == 0, f"{path}: pg_restore vào database trống lỗi: {done.stderr[-800:]}"
            query = ("SELECT (SELECT count(*) FROM documents) || ' ' || (SELECT count(*) FROM chunks) || ' ' || "
                     "(SELECT coalesce(max(version), 0) FROM schema_migrations)")
            out = sh(self.vm, f"cd {INSTALL} && docker compose exec -T db psql -X -q -At -U quillo -d {db} "
                              f"-c {shlex.quote(query)}", timeout=60)
            assert out.returncode == 0, f"{path}: đọc bản restore lỗi: {out.stderr[-500:]}"
            documents, chunks, schema = (int(x) for x in out.stdout.split())
        finally:
            self.sql(f"DROP DATABASE IF EXISTS {db}")
        return documents, chunks, schema


def leaked(work: Path) -> list[str]:
    found = []
    for path in work.rglob("*"):
        if not path.is_file() or path.is_symlink():
            continue
        with path.open("rb") as handle:
            head = handle.read(5)
        if head == DUMP_MAGIC:
            found.append(str(path))
            continue
        if path.stat().st_size < 64 << 20:
            data = path.read_bytes()
            if any(marker in data for marker in DATA_MARKERS):
                found.append(str(path))
    return found


def require_bundles() -> None:
    for version, path in (("1.1.0", BUNDLE), ("1.0.0", OLD_BUNDLE)):
        if not path.is_file():
            pytest.skip(f"Thiếu bundle {path.relative_to(ROOT)}. Dựng: {BUILD.format(v=version)}")


def appendix() -> tuple[str, str, str]:
    code = f"PL-{secrets.token_hex(3).upper()}"
    price = f"{secrets.randbelow(900) + 100}.{secrets.randbelow(90) + 10}"
    text = (f"PRICE APPENDIX {code}\n\nThis appendix to the nitrile gloves supply contract of the hospital sets the unit "
            f"price of one box of nitrile examination gloves at {price} thousand VND, valid from 1 January 2027. "
            f"Appendix code {code} replaces all earlier price lists for nitrile gloves.\n")
    return code, price, text


def test_upgrade_rollback_keeps_documents(tmp_path):
    require_bundles()
    upgrade, rollback = ex.path("upgrade.sh"), ex.path("rollback.sh")
    archive_sha = file_sha(OLD_BUNDLE)
    base = fdekit.derived(SNAPSHOT)
    with fdekit.customer_site("hospital", base=base, memory_mb=MEMORY_MB, forwards=(18080,)) as site:
        h = Hospital(site, tmp_path)
        h.health("1.0.0", "Sau khi boot snapshot", timeout=180)
        documents, chunks = h.counts()
        old_doc = h.doc_id(OLD_CONTRACT)
        assert old_doc in h.cited(OLD_QUESTION, "Trước nâng cấp"), "Snapshot hỏng: câu hỏi mẫu không trích hợp đồng cũ"
        secrets_before = h.secrets()
        work = tmp_path / "work"
        work.mkdir()

        watch = Watch(h.vm)
        try:
            h.run(str(upgrade), work, UPGRADE_TIMEOUT, "upgrade.sh")
            h.health("1.1.0", "Sau upgrade.sh")
        finally:
            watch.stop()
        watch.check("upgrade.sh")
        assert h.schema() == 2, "Sau nâng cấp, schema_migrations phải có migration 2 (0002_v1_1_tags.sql)"
        assert h.counts() == (documents, chunks), \
            f"Nâng cấp làm đổi số tài liệu/chunk: trước {(documents, chunks)}, sau {h.counts()}"
        assert old_doc in h.cited(OLD_QUESTION, "Sau nâng cấp"), "Sau nâng cấp /api/ask không còn trích hợp đồng cũ"
        dumps = h.dumps()
        assert dumps, "Không thấy bản backup *.dump nào trong /home/fde/backups/ trên máy"
        assert any(h.dump_state(path) == (documents, chunks, 1) for path in dumps[:3]), \
            (f"Không bản backup nào trong /home/fde/backups/ là bản trước nâng cấp: cần restore được ra {documents} tài "
             f"liệu, {chunks} chunk, schema 1")

        code, price, text = appendix()
        tags = ["bang-gia", code.lower()]
        new_doc = h.upload(f"Price appendix {code}.txt", text, tags)
        new_documents, new_chunks = h.counts()
        assert new_documents == documents + 1, "Tài liệu nạp trên 1.1.0 không vào database"
        question = f"What is the unit price of nitrile gloves in price appendix {code}?"
        assert new_doc in h.cited(question, "Trên 1.1.0"), "Tài liệu mới không được trích trên 1.1.0"

        watch = Watch(h.vm)
        try:
            h.run(str(rollback), work, ROLLBACK_TIMEOUT, "rollback.sh")
            h.health("1.0.0", "Sau rollback.sh")
        finally:
            watch.stop()
        watch.check("rollback.sh")
        assert h.counts() == (new_documents, new_chunks), (
            f"Rollback làm đổi dữ liệu: trước rollback {new_documents} tài liệu/{new_chunks} chunk, sau "
            f"{h.counts()} (tài liệu nạp trên 1.1.0 phải còn)")
        stored = h.sql(f"SELECT array_to_string(tags, ',') FROM documents WHERE id = '{new_doc}'")
        assert sorted(stored.split(",")) == sorted(tags), f"tags của tài liệu nạp trên 1.1.0 mất sau rollback: {stored!r}"
        assert old_doc in h.cited(OLD_QUESTION, "Sau rollback"), "Sau rollback /api/ask không còn trích hợp đồng cũ"
        assert new_doc in h.cited(question, "Sau rollback"), "Sau rollback /api/ask không còn trích tài liệu nạp trên 1.1.0"

        assert h.secrets() == secrets_before, "QUILLO_ADMIN_TOKEN/QUILLO_DB_PASSWORD trong .env bị đổi"
        sha = sh(h.vm, f"sha256sum {ARCHIVE}", timeout=120).stdout.split()
        assert sha[:1] == [archive_sha], f"{ARCHIVE} (bundle lưu trữ của bệnh viện) bị xoá hoặc sửa"
        assert not leaked(work), f"Dữ liệu bệnh viện bị chép ra laptop: {leaked(work)}"


def main() -> None:
    require_bundles()
    with fdekit.customer_site("hospital", base=fdekit.derived(SNAPSHOT), memory_mb=MEMORY_MB,
                              forwards=(18080,)) as site:
        print(f"""
SSH vào máy bệnh viện:  {shlex.join(site.vm.ssh_command())}
quillo (từ laptop):     http://127.0.0.1:{site.vm.port(18080)}   (cài ở {INSTALL}, token quản trị trong .env)
Chạy thử script của bạn:
  SSH={shlex.quote(shlex.join(site.vm.ssh_command()))} BUNDLE={BUNDLE} WORK=$(mktemp -d) sh <script>
Nhấn Enter để dọn máy.""")
        input()


if __name__ == "__main__":
    sys.exit(main())

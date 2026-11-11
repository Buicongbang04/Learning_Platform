"""Chuẩn bị nâng cấp ở bệnh viện: backup đã kiểm và kế hoạch chỗ chứa. Chạy thẳng tệp này từ gốc repo
(`PYTHONPATH=. uv run python <tệp>`) để dựng đúng máy của test và tự thử: in lệnh SSH, cổng quillo, chờ Enter."""

import hashlib
import json
import secrets
import shlex
import subprocess
import sys
import tarfile
import threading
import time
from pathlib import Path

import pytest

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
NEW_ROOT = "quillo-1.1.0"
MIN_FREE_PCT = 15
SCRIPT_TIMEOUT = 180
FREE_TOLERANCE = 64 << 20
DB_TOLERANCE = 0.10
EXPORT_MIB = (20, 120)
KEYS = ("disk_free_bytes", "db_bytes", "dump", "dump_bytes", "stage", "stage_bytes", "free_after_bytes")
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


def bundle_members() -> tuple[dict[str, int], dict[str, str], dict[str, list[str]]]:
    """(kích thước, sha256 theo manifest, image ID trong từng images/*.tar) của bundle 1.1.0."""
    sizes, images = {}, {}
    with tarfile.open(BUNDLE) as tar:
        for info in tar.getmembers():
            if info.isfile() and info.name.startswith(NEW_ROOT + "/"):
                sizes[info.name[len(NEW_ROOT) + 1:]] = info.size
        manifest = json.load(tar.extractfile(f"{NEW_ROOT}/manifest.json"))["files"]
        for path in sizes:
            if path.startswith("images/") and path.endswith(".tar"):
                with tarfile.open(fileobj=tar.extractfile(f"{NEW_ROOT}/{path}")) as image:
                    entries = json.load(image.extractfile("manifest.json"))
                images[path] = ["sha256:" + e["Config"].rsplit("/", 1)[1] for e in entries]
    return sizes, manifest, images


class Watch:
    """Mỗi 2 s qua một phiên SSH riêng: đĩa trống của `/` và mã HTTP của `/healthz`, như giám sát của bệnh viện."""

    def __init__(self, m: fdekit.VM) -> None:
        self.samples: list[tuple[int, int, str]] = []
        script = ("while :; do s=$(df -B1 --output=size,avail / | tail -n 1); "
                  "c=$(curl -s --noproxy '*' -o /dev/null -m 4 -w '%{http_code}' http://127.0.0.1:18080/healthz); "
                  "echo \"$s $c\"; sleep 2; done")
        self.proc = subprocess.Popen([*m.ssh_command(), script], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                                     stdin=subprocess.DEVNULL, text=True)
        self.thread = threading.Thread(target=self._read, daemon=True)
        self.thread.start()

    def _read(self) -> None:
        for line in self.proc.stdout:
            parts = line.split()
            if len(parts) == 3 and parts[0].isdigit() and parts[1].isdigit():
                self.samples.append((int(parts[0]), int(parts[1]), parts[2]))

    def stop(self) -> None:
        self.proc.terminate()
        try:
            self.proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            self.proc.kill()


class Hospital:
    def __init__(self, site: fdekit.Site) -> None:
        self.vm = site.vm

    def wait_health(self, timeout: float = 180) -> None:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            done = sh(self.vm, "curl -fsS --noproxy '*' -m 5 -o /dev/null http://127.0.0.1:18080/healthz", timeout=30)
            if done.returncode == 0:
                return
            time.sleep(2)
        pytest.fail(f"quillo không trả /healthz 200 sau {timeout} s từ lúc boot snapshot")

    def sql(self, query: str, db: str = "quillo") -> str:
        done = sh(self.vm, f"cd {INSTALL} && docker compose exec -T db psql -X -q -At -U quillo -d {db} "
                           f"-c {shlex.quote(query)}", timeout=60)
        assert done.returncode == 0, f"psql trong container db lỗi: {done.stderr[-500:]}"
        return done.stdout.strip()

    def free(self) -> tuple[int, int]:
        size, avail = sh(self.vm, "df -B1 --output=size,avail / | tail -n 1").stdout.split()
        return int(size), int(avail)

    def install_listing(self) -> str:
        return sh(self.vm, f"cd {INSTALL} && find . -path ./inbox -prune -o -type f -printf '%P %s\\n' | sort; "
                           "sha256sum .env compose.yaml").stdout

    def images(self) -> set[str]:
        return set(sh(self.vm, "docker images -q --no-trunc").stdout.split())

    def restore_counts(self, dump: str) -> tuple[int, int, int]:
        db = "restore_check"
        self.sql(f"DROP DATABASE IF EXISTS {db}")
        self.sql(f"CREATE DATABASE {db}")
        try:
            done = sh(self.vm, f"cd {INSTALL} && docker compose exec -T db pg_restore -U quillo -d {db} --no-owner "
                               f"< {shlex.quote(dump)}", timeout=120)
            assert done.returncode == 0, f"pg_restore bản dump vào database trống lỗi: {done.stderr[-800:]}"
            counts = self.sql("SELECT (SELECT count(*) FROM documents) || ' ' || (SELECT count(*) FROM chunks) || ' ' "
                              "|| (SELECT coalesce(max(version), 0) FROM schema_migrations)", db=db)
        finally:
            self.sql(f"DROP DATABASE IF EXISTS {db}")
        documents, chunks, schema = (int(x) for x in counts.split())
        return documents, chunks, schema


def require_bundles() -> None:
    for version, path in (("1.1.0", BUNDLE), ("1.0.0", OLD_BUNDLE)):
        if not path.is_file():
            pytest.skip(f"Thiếu bundle {path.relative_to(ROOT)}. Dựng: {BUILD.format(v=version)}")


def load_plan(work: Path) -> dict:
    path = work / "storage-plan.json"
    if not path.is_file():
        pytest.fail("Script không ghi $WORK/storage-plan.json")
    try:
        plan = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        pytest.fail(f"storage-plan.json không phải JSON: {error}")
    assert isinstance(plan, dict), "storage-plan.json phải là object"
    for key in KEYS:
        assert key in plan, f"storage-plan.json thiếu {key!r}"
    for key in ("disk_free_bytes", "db_bytes", "dump_bytes", "stage_bytes", "free_after_bytes"):
        assert isinstance(plan[key], int) and not isinstance(plan[key], bool), f"{key} phải là số nguyên (byte)"
    assert isinstance(plan["dump"], str) and plan["dump"].startswith("/"), "dump phải là đường dẫn tuyệt đối trên máy"
    assert isinstance(plan["stage"], list) and all(isinstance(p, str) for p in plan["stage"]), \
        "stage phải là mảng đường dẫn trong bundle"
    return plan


def leaked(work: Path) -> list[str]:
    found = []
    for path in work.rglob("*"):
        if not path.is_file() or path.is_symlink():
            continue
        with path.open("rb") as handle:
            if handle.read(5) == b"PGDMP":
                found.append(str(path))
                continue
        if path.stat().st_size < 64 << 20 and any(m in path.read_bytes() for m in DATA_MARKERS):
            found.append(str(path))
    return found


def test_backup_and_storage_plan(tmp_path):
    require_bundles()
    script = ex.path("pre_upgrade.sh")
    archive_sha = file_sha(OLD_BUNDLE)
    sizes, manifest, image_ids = bundle_members()
    with fdekit.customer_site("hospital", base=fdekit.derived(SNAPSHOT), memory_mb=MEMORY_MB,
                              forwards=(18080,)) as site:
        h = Hospital(site)
        h.wait_health()
        mib = EXPORT_MIB[0] + secrets.randbelow(EXPORT_MIB[1] - EXPORT_MIB[0] + 1)
        made = sh(h.vm, f"sudo -n mkdir -p /var/lib/his-export && sudo -n fallocate -l {mib}M "
                        f"/var/lib/his-export/his-{secrets.token_hex(3)}.bak")
        assert made.returncode == 0, f"Test không tạo được dữ liệu xuất của bệnh viện: {made.stderr}"
        installed = json.loads(sh(h.vm, f"cat {INSTALL}/manifest.json").stdout)["files"]
        listing = h.install_listing()
        images = h.images()
        size, free_before = h.free()
        floor = size * MIN_FREE_PCT // 100

        work = tmp_path / "work"
        work.mkdir()
        env = {"SSH": shlex.join(h.vm.ssh_command()), "BUNDLE": str(BUNDLE), "WORK": str(work)}
        watch = Watch(h.vm)
        try:
            done = run_sandboxed(["sh", str(script)], writable=[work], cwd=work, env=env, timeout=SCRIPT_TIMEOUT,
                                 input="")
        except subprocess.TimeoutExpired:
            pytest.fail(f"pre_upgrade.sh chạy quá {SCRIPT_TIMEOUT} s")
        finally:
            time.sleep(2)
            watch.stop()
        assert done.returncode == 0, (f"pre_upgrade.sh thoát {done.returncode}\n--- stdout ---\n{done.stdout[-2500:]}\n"
                                      f"--- stderr ---\n{done.stderr[-2500:]}")
        assert len(watch.samples) >= 3, "Giám sát của bệnh viện không đo được (SSH tới máy lỗi?)"
        down = [code for _, _, code in watch.samples if code != "200"]
        assert not down, f"quillo không trả /healthz 200 ở {len(down)}/{len(watch.samples)} lần đo trong lúc script chạy"
        low = min(avail for _, avail, _ in watch.samples)
        assert low >= floor, (f"đĩa / có lúc chỉ còn {low:,} byte trống, dưới mức {MIN_FREE_PCT}% ({floor:,} byte) "
                              "bệnh viện yêu cầu")

        plan = load_plan(work)
        dump = plan["dump"]
        stat = sh(h.vm, f"stat -c '%a %s %F' {shlex.quote(dump)}").stdout.strip().split(maxsplit=2)
        assert len(stat) == 3 and stat[2] == "regular file", f"Không có tệp dump {dump} trên máy"
        assert stat[0] == "600", f"{dump} phải có quyền 0600 (chứa toàn bộ tài liệu của bệnh viện), đang là {stat[0]}"
        assert int(stat[1]) == plan["dump_bytes"], f"dump_bytes {plan['dump_bytes']} khác kích thước thật {stat[1]}"
        folder, name = shlex.quote(str(Path(dump).parent)), shlex.quote(Path(dump).name)
        check = sh(h.vm, f"cd {folder} && sha256sum -c {name}.sha256", timeout=60)
        assert check.returncode == 0, f"{dump}.sha256 không có hoặc không khớp: {check.stdout}{check.stderr}"
        live = (int(h.sql("SELECT count(*) FROM documents")), int(h.sql("SELECT count(*) FROM chunks")), 1)
        assert h.restore_counts(dump) == live, \
            f"Restore bản dump vào database trống không ra đúng dữ liệu đang chạy (tài liệu, chunk, schema) {live}"
        db_bytes = int(h.sql("SELECT pg_database_size('quillo')"))

        assert abs(plan["disk_free_bytes"] - free_before) <= FREE_TOLERANCE, \
            f"disk_free_bytes {plan['disk_free_bytes']:,} lệch quá 64 MiB so với đĩa trống đo trước khi chạy {free_before:,}"
        assert abs(plan["db_bytes"] - db_bytes) <= DB_TOLERANCE * db_bytes, \
            f"db_bytes {plan['db_bytes']:,} lệch quá 10% so với pg_database_size {db_bytes:,}"
        unknown = [p for p in plan["stage"] if p not in sizes]
        assert not unknown, f"stage có đường dẫn không nằm trong bundle 1.1.0: {unknown}"
        assert len(set(plan["stage"])) == len(plan["stage"]), "stage có đường dẫn lặp"
        assert plan["stage_bytes"] == sum(sizes[p] for p in plan["stage"]), \
            f"stage_bytes {plan['stage_bytes']:,} khác tổng kích thước các tệp trong stage"
        assert plan["free_after_bytes"] == plan["disk_free_bytes"] - plan["dump_bytes"] - plan["stage_bytes"], \
            "free_after_bytes phải bằng disk_free_bytes − dump_bytes − stage_bytes"
        needed = [p for p in manifest if not p.startswith("chart/") and installed.get(p) != manifest[p]
                  and not set(image_ids.get(p, ["-"])) <= images]
        missing = sorted(set(needed) - set(plan["stage"]))
        assert not missing, f"stage thiếu tệp mà máy chưa có bản giống hệt: {missing}"
        real_after = free_before - int(stat[1]) - plan["stage_bytes"]
        assert real_after >= floor, (f"Kế hoạch không vừa máy: đĩa trống {free_before:,} − dump {int(stat[1]):,} − stage "
                                     f"{plan['stage_bytes']:,} = {real_after:,} byte, dưới mức {MIN_FREE_PCT}% "
                                     f"({floor:,} byte)")

        assert h.install_listing() == listing, f"Bản cài đang chạy ở {INSTALL} bị thêm, xoá hoặc sửa tệp"
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
  SSH={shlex.quote(shlex.join(site.vm.ssh_command()))} BUNDLE={BUNDLE} WORK=$(mktemp -d) sh pre_upgrade.sh
Nhấn Enter để dọn máy.""")
        input()


if __name__ == "__main__":
    sys.exit(main())

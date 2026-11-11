import json
import os
import secrets
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

import fdekit
from testkit import Exercise, run_sandboxed

ex = Exercise(__file__)
RUN_TIMEOUT = 60
A = "Pháp chế/Hợp đồng 2024/NDA-01.txt"
B = "Pháp chế/Hợp đồng 2024/NDA-02.pdf"
C = "Tài chính/Hoá đơn T10.txt"
D = "README.txt"
E = "Pháp chế/Biên bản họp.txt"
F = "Tài chính/2024/Q4/Bảng kê.txt"
G = "Pháp chế/khóa.txt"
IGNORED = ["Pháp chế/Hợp đồng 2024/~$NDA-02.docx", "Tài chính/Thumbs.db", "desktop.ini", "Pháp chế/.DS_Store"]
USER_FILE = "Tài chính/tay.txt"


def body(name: str) -> bytes:
    return f"{name}\n{secrets.token_hex(16)}\n".encode() * (1 + secrets.randbelow(40))


def write(root: Path, rel: str, data: bytes, mtime: float | None = None) -> None:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    if mtime is not None:
        os.utime(path, (mtime, mtime))


def tree(root: Path) -> dict[str, tuple[bytes, int, int]]:
    return {p.relative_to(root).as_posix(): (p.read_bytes(), p.stat().st_mtime_ns, p.stat().st_ino)
            for p in sorted(root.rglob("*")) if p.is_file()}


class Connector:
    def __init__(self, site: fdekit.Site, work: Path) -> None:
        self.work = work
        self.inbox = work / "inbox"
        self.inbox.mkdir(parents=True)
        secret = work / "secrets" / "smb-password"
        secret.parent.mkdir()
        secret.write_text(site.fileshare_creds[1] + "\n")
        secret.chmod(0o600)
        host, port = site.fileshare_host
        self.args = ["--server", host, "--port", str(port), "--share", fdekit.FILESHARE_SHARE,
                     "--user", site.fileshare_creds[0], "--password-file", str(secret),
                     "--inbox", str(self.inbox), "--state", str(work / "state" / "sync-state.json")]
        (work / "state").mkdir()

    def run(self, label: str) -> tuple[int, dict]:
        cmd = [sys.executable, str(ex.path("sync_share.py")), *self.args]
        try:
            done = run_sandboxed(cmd, writable=[self.work], cwd=self.work, env={}, timeout=RUN_TIMEOUT)
        except subprocess.TimeoutExpired:
            pytest.fail(f"{label}: sync_share.py chạy quá {RUN_TIMEOUT} s")
        lines = done.stdout.strip().splitlines()
        try:
            report = json.loads(lines[-1])
        except (IndexError, json.JSONDecodeError):
            pytest.fail(f"{label}: dòng cuối stdout phải là báo cáo JSON (thoát {done.returncode})\n"
                        f"stdout:\n{done.stdout[-1500:]}\nstderr:\n{done.stderr[-2500:]}")
        if not isinstance(report, dict) or any(not isinstance(report.get(k), list) for k in
                                               ("added", "updated", "deleted", "errors")):
            pytest.fail(f"{label}: báo cáo phải có đủ 4 mảng added, updated, deleted, errors: {report}")
        return done.returncode, {k: sorted(report[k]) for k in ("added", "updated", "deleted", "errors")}


def expect(label: str, got: tuple[int, dict], code: int, **lists: list[str]) -> None:
    want = {k: sorted(lists.get(k, [])) for k in ("added", "updated", "deleted", "errors")}
    assert got[1] == want, f"{label}: báo cáo sai\ncần {want}\nnhận {got[1]}"
    assert got[0] == code, f"{label}: phải thoát {code}, thoát {got[0]}"


def worker_takes(inbox: Path, rel: str) -> None:
    target = inbox / "done" / rel
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(inbox / rel, target)


def test_incremental_sync(tmp_path):
    with fdekit.customer_site("lab-open", memory_mb=1024, extra_services=("fileshare",)) as site:
        share = site.fileshare_dir
        old = 1_700_000_000.0
        files = {rel: body(rel) for rel in (A, B, C, D, E)}
        for rel, data in files.items():
            write(share, rel, data, old)
        for rel in IGNORED:
            write(share, rel, b"lock", old)
        conn = Connector(site, tmp_path / "work")
        inbox = conn.inbox

        expect("Lần 1 (inbox rỗng)", conn.run("Lần 1"), 0, added=[A, B, C, D, E])
        got = {k: v[0] for k, v in tree(inbox).items()}
        assert got == files, f"Lần 1: inbox phải chứa đúng các tệp của share, giữ thư mục: {sorted(got)}"

        worker_takes(inbox, A)
        worker_takes(inbox, D)
        write(inbox, USER_FILE, b"nguoi dung tu tha vao")
        (share / C).chmod(0)
        before = tree(inbox)
        expect("Lần 2 (không có gì đổi; worker đã chuyển 2 tệp sang done/)", conn.run("Lần 2"), 0)
        assert tree(inbox) == before, "Lần 2: không có gì đổi ở share thì inbox phải giữ nguyên từng tệp"

        (share / C).chmod(0o644)
        os.utime(share / B, (old + 3600, old + 3600))
        files[C] = body(C) + b"sua doi\n"
        write(share, C, files[C], old + 7200)
        (share / A).unlink()
        (share / E).unlink()
        files[F] = body(F)
        write(share, F, files[F], old + 60)
        write(share, G, body(G), old + 60)
        (share / G).chmod(0)
        before = tree(inbox)
        expect("Lần 3 (sửa, xoá, thêm, một tệp không đọc được)", conn.run("Lần 3"), 1,
               added=[F], updated=[C], deleted=[A, E], errors=[G])
        after = tree(inbox)
        assert E not in after, "Lần 3: tệp bị xoá ở nguồn mà còn chờ trong inbox phải bị gỡ khỏi inbox"
        assert after.get(f"done/{A}") == before[f"done/{A}"], "Lần 3: connector không được đụng vào done/"
        assert after.get(USER_FILE) == before[USER_FILE], "Lần 3: tệp người khác thả vào inbox phải giữ nguyên"
        assert after.get(B) == before[B], "Lần 3: chỉ đổi mtime, nội dung giữ nguyên thì không giao lại"
        assert after.get(C, (b"",))[0] == files[C], "Lần 3: inbox phải có nội dung mới của tệp đã sửa"
        assert after.get(F, (b"",))[0] == files[F], "Lần 3: tệp mới trong thư mục con mới phải có trong inbox"
        assert G not in after, "Lần 3: tệp không đọc được thì không có gì trong inbox"

        (share / G).chmod(0o644)
        expect("Lần 4 (tệp lỗi đã đọc được)", conn.run("Lần 4"), 0, added=[G])
        assert tree(inbox)[G][0] == (share / G).read_bytes()
        before = tree(inbox)
        expect("Lần 5 (không có gì đổi)", conn.run("Lần 5"), 0)
        assert tree(inbox) == before, "Lần 5: không có gì đổi ở share thì inbox phải giữ nguyên từng tệp"

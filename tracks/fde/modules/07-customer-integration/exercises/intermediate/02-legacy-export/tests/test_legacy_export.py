"""Chạy thẳng `PYTHONPATH=. uv run python <tệp này> samples` để sinh lại thư mục samples/ (seed cố định)."""

import csv
import hashlib
import io
import random
import subprocess
import sys
import tarfile
import time
import unicodedata
from datetime import date, timedelta
from pathlib import Path

import pytest
import requests

import fdekit
from testkit import Exercise, run_sandboxed

ex = Exercise(__file__)
SAMPLES = ex.dir / "samples"
SNAPSHOT = "07-customer-integration-quillo"
QUILLO = "/home/fde/quillo-1.0.0"
RUN_TIMEOUT = 60
TONES = {"\u0300", "\u0301", "\u0303", "\u0309", "\u0323"}

VN_CUSTOMERS = ["Công ty TNHH Thương mại Hoà Bình", "Công ty Cổ phần Đầu tư Xây dựng Hưng Thịnh",
                "Ngân hàng TMCP Phương Đông", "Công ty TNHH Một thành viên Dịch vụ Kỹ thuật Ánh Dương",
                "Hộ kinh doanh Nguyễn Thị Hằng", "Tổng công ty Điện lực Miền Nam", "Công ty TNHH Phần mềm Sơn Hà",
                "Trường Đại học Quốc tế Hồng Bàng", "Công ty Cổ phần Thủy sản Cửu Long"]
VN_TYPES = ["Dịch vụ pháp lý thường xuyên", "Tư vấn sáp nhập, mua lại", "Soạn thảo hợp đồng thương mại",
            "Đại diện tranh tụng", "Thẩm định pháp lý dự án"]
VN_NOTES = ["", "Gia hạn tự động 12 tháng; báo trước 30 ngày", 'Khách yêu cầu "bảo mật tuyệt đối" với hồ sơ',
            "Thanh toán 2 đợt:\r\n- Đợt 1: 50% khi ký\r\n- Đợt 2: 50% khi nghiệm thu",
            "Đã điều chỉnh phụ lục số 02 ngày 15/08/2024", "Liên hệ: chị Hằng – phòng pháp chế, sđt nội bộ 214"]
FR_CUSTOMERS = ["Société Générale Vietnam", "Müller & Söhne GmbH", "Œuvres Françaises SARL",
                "Café Crème Import–Export", "Banco Español de Crédito", "Brasserie Saint-Étienne"]
FR_ONLY_1252 = ["Transportes São Gonçalo Ltda", "Škoda Auto a.s.", "Ristorante Fiorentìno", "Hôtel Ýmir & Þór",
                "Žabka Polska", "Bodegas Peñalòn"]
FR_NOTES = ["", "Honoraires forfaitaires : 5 000 € HT", "Dossier « urgent » – voir note du 12/03",
            "Le client a demandé une révision\r\ndu contrat de distribution", "Contact : M. Lefèvre (Œnologie)",
            "“Due diligence” terminée, rapport envoyé", "Réunion à Lisboa avec João Gonçalves",
            "Voir dossier Šimek (Brno)"]


def to_cp1258(text: str) -> bytes:
    out = bytearray()
    for ch in unicodedata.normalize("NFC", text):
        try:
            out += ch.encode("cp1258")
            continue
        except UnicodeEncodeError:
            pass
        parts = unicodedata.normalize("NFD", ch)
        base = unicodedata.normalize("NFC", "".join(c for c in parts if c not in TONES))
        out += base.encode("cp1258") + "".join(c for c in parts[1:] if c in TONES).encode("cp1258")
    return bytes(out)


def csv_text(rows: list[list[str]]) -> str:
    buffer = io.StringIO()
    csv.writer(buffer, delimiter=";", lineterminator="\r\n").writerows(rows)
    return buffer.getvalue()


def some_date(rng: random.Random) -> date:
    return date(2021, 1, 1) + timedelta(days=rng.randrange(5 * 365))


def legacy_date(day: date, rng: random.Random) -> str:
    if rng.random() < 0.3:
        return f"{day.day}/{day.month}/{day.year}"
    return day.strftime("%d/%m/%Y")


def note_text(note: str) -> str:
    return note.replace("\r\n", "\n")


def make_exports(folder: Path, rng: random.Random, contracts: int = 8, partners: int = 4) -> dict[str, str]:
    """Ghi HOPDONG.CSV, DOITAC.CSV như hệ thống cũ xuất; trả {đường dẫn tài liệu: nội dung UTF-8 cần có}."""
    folder.mkdir(parents=True, exist_ok=True)
    expected: dict[str, str] = {}
    rows = [["Số HĐ", "Khách hàng", "Loại hợp đồng", "Ngày ký", "Giá trị (VNĐ)", "Ghi chú"]]
    total = 0
    numbers = rng.sample(range(1, 999), contracts)
    vn_notes = rng.sample(VN_NOTES, len(VN_NOTES))
    for i, number in enumerate(numbers):
        day = some_date(rng)
        ref = f"HD-{day.year}-{number:04d}"
        amount = rng.randrange(20, 5000) * 1_000_000 + rng.choice([0, 500_000])
        total += amount
        customer, kind = rng.choice(VN_CUSTOMERS), rng.choice(VN_TYPES)
        note = vn_notes[i] if i < len(vn_notes) else rng.choice(VN_NOTES)
        rows.append([ref, customer, kind, legacy_date(day, rng), f"{amount:,}".replace(",", "."), note])
        body = (f"Nguồn: hệ thống hợp đồng\nSố hợp đồng: {ref}\nKhách hàng: {customer}\nLoại hợp đồng: {kind}\n"
                f"Ngày ký: {day.isoformat()}\nGiá trị: {amount} VND\nGhi chú:\n")
        expected[f"hop-dong/{ref}.txt"] = body + (note_text(note) + "\n" if note else "")
    rows.append(["", f"Tổng cộng: {contracts} hợp đồng", "", "", f"{total:,}".replace(",", "."), ""])
    (folder / "HOPDONG.CSV").write_bytes(to_cp1258(csv_text(rows)))
    rows = [["Réf", "Client", "Ouverture", "Honoraires (EUR)", "Remarques"]]
    customers = rng.sample(FR_CUSTOMERS, partners - 1) + [rng.choice(FR_ONLY_1252)]
    rng.shuffle(customers)
    fr_notes = rng.sample(FR_NOTES, partners)
    for i, number in enumerate(rng.sample(range(1, 9999), partners)):
        day = some_date(rng)
        ref = f"P-{number:04d}"
        cents = rng.randrange(50_000, 9_000_000)
        fee = f"{cents // 100}.{cents % 100:02d}"
        customer, note = customers[i], fr_notes[i]
        rows.append([ref, customer, day.strftime("%d/%m/%Y"), fee.replace(".", ","), note])
        body = (f"Nguồn: văn phòng đối tác\nMã hồ sơ: {ref}\nKhách hàng: {customer}\nNgày mở: {day.isoformat()}\n"
                f"Phí: {fee} EUR\nGhi chú:\n")
        expected[f"doi-tac/{ref}.txt"] = body + (note_text(note) + "\n" if note else "")
    (folder / "DOITAC.CSV").write_bytes(csv_text(rows).encode("cp1252"))
    return expected


def convert(src: Path, out: Path, label: str) -> None:
    cmd = [sys.executable, str(ex.path("legacy_export.py")), "--in", str(src), "--out", str(out)]
    try:
        done = run_sandboxed(cmd, writable=[out.parent], cwd=out, env={}, timeout=RUN_TIMEOUT)
    except subprocess.TimeoutExpired:
        pytest.fail(f"{label}: legacy_export.py chạy quá {RUN_TIMEOUT} s")
    assert done.returncode == 0, f"{label}: legacy_export.py thoát {done.returncode}\n{done.stderr[-2500:]}"


def produced(out: Path) -> dict[str, bytes]:
    return {p.relative_to(out).as_posix(): p.read_bytes() for p in sorted(out.rglob("*")) if p.is_file()}


def compare(label: str, got: dict[str, bytes], expected: dict[str, str]) -> None:
    assert sorted(got) == sorted(expected), (
        f"{label}: tệp sinh ra khác cần có\nthiếu {sorted(set(expected) - set(got))}\n"
        f"thừa {sorted(set(got) - set(expected))}")
    for path, text in expected.items():
        want = text.encode("utf-8")
        if got[path] == want:
            continue
        try:
            have = got[path].decode("utf-8")
        except UnicodeDecodeError:
            pytest.fail(f"{label}: {path} không phải UTF-8 hợp lệ")
        diff = next((i for i, (a, b) in enumerate(zip(have, text)) if a != b), min(len(have), len(text)))
        points = " ".join(f"U+{ord(c):04X}" for c in text[diff:diff + 3])
        found = " ".join(f"U+{ord(c):04X}" for c in have[diff:diff + 3])
        pytest.fail(f"{label}: {path} khác từ ký tự thứ {diff}\ncần: {text[max(0, diff - 20):diff + 30]!r}\n"
                    f"có:  {have[max(0, diff - 20):diff + 30]!r}\ncode point từ chỗ khác: cần {points}, có {found}")


def test_samples(tmp_path):
    expected = {p.relative_to(SAMPLES / "expected").as_posix(): p.read_text(encoding="utf-8")
                for p in (SAMPLES / "expected").rglob("*.txt")}
    out = tmp_path / "out"
    out.mkdir()
    src = tmp_path / "in"
    src.mkdir()
    for name in ("HOPDONG.CSV", "DOITAC.CSV"):
        (src / name).write_bytes((SAMPLES / name).read_bytes())
    convert(src, out, "samples")
    compare("samples", produced(out), expected)


def test_fresh_exports_and_rerun(tmp_path):
    for round_ in range(2):
        src, out = tmp_path / f"in{round_}", tmp_path / f"out{round_}"
        out.mkdir()
        expected = make_exports(src, random.Random())
        convert(src, out, f"Bộ xuất ngẫu nhiên {round_ + 1}")
        compare(f"Bộ xuất ngẫu nhiên {round_ + 1}", produced(out), expected)
        convert(src, out, f"Chạy lại bộ {round_ + 1}")
        compare(f"Chạy lại bộ {round_ + 1}", produced(out), expected)


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


def wait_health(api: str, m: fdekit.VM) -> None:
    deadline = time.monotonic() + 150
    while time.monotonic() < deadline:
        try:
            if requests.get(f"{api}/healthz", timeout=5).status_code == 200:
                return
        except requests.RequestException:
            pass
        time.sleep(2)
    logs = sh(m, f"cd {QUILLO} && docker compose ps -a", timeout=60).stdout
    pytest.fail(f"quillo không trả /healthz 200 sau khi boot snapshot\n{logs[-2000:]}")


def test_quillo_ingests_documents(tmp_path):
    base = fdekit.derived(SNAPSHOT)
    src, out = tmp_path / "in", tmp_path / "out"
    out.mkdir()
    expected = make_exports(src, random.Random())
    convert(src, out, "Bộ xuất cho quillo")
    compare("Bộ xuất cho quillo", produced(out), expected)
    buffer = io.BytesIO()
    old = time.time() - 3600
    with tarfile.open(fileobj=buffer, mode="w") as tar:
        for path, data in produced(out).items():
            info = tarfile.TarInfo(path)
            info.size, info.mtime, info.mode = len(data), old, 0o644
            tar.addfile(info, io.BytesIO(data))
    (tmp_path / "docs.tar").write_bytes(buffer.getvalue())
    with fdekit.customer_site("lab-open", base=base, memory_mb=3072, forwards=(18080,)) as site:
        m = site.vm
        api = f"http://127.0.0.1:{m.port(18080)}"
        wait_health(api, m)
        token = sh(m, f"sed -n 's/^QUILLO_ADMIN_TOKEN=//p' {QUILLO}/.env").stdout.strip()
        m.put(tmp_path / "docs.tar", "/home/fde/docs.tar")
        done = sh(m, f"cd {QUILLO} && sudo -n mkdir .stage && sudo -n tar -x -C .stage -f /home/fde/docs.tar "
                     "&& sudo -n chown -R 10001:10001 .stage && sudo -n sh -c 'mv .stage/* inbox/' && sudo -n rmdir .stage")
        assert done.returncode == 0, f"Test không đặt được tài liệu vào inbox: {done.stderr}"
        want = {path: hashlib.sha256(text.encode()).hexdigest()[:16] for path, text in expected.items()}
        stored: dict[str, str] = {}
        deadline = time.monotonic() + 120
        while time.monotonic() < deadline:
            response = requests.get(f"{api}/api/documents", headers={"Authorization": f"Bearer {token}"}, timeout=30)
            stored = {d["filename"]: d["doc_id"] for d in response.json()} if response.status_code == 200 else {}
            if len(stored) >= len(want):
                break
            time.sleep(2)
        failed = sh(m, f"sudo -n find {QUILLO}/inbox/failed -type f").stdout.split()
        assert not failed, f"Worker chuyển tài liệu vào failed/: {failed}"
        assert stored == want, f"quillo lưu {len(stored)}/{len(want)} tài liệu, khác đường dẫn hoặc nội dung cần có"


if __name__ == "__main__" and sys.argv[1:] == ["samples"]:
    target = Path(__file__).resolve().parents[1] / "samples"
    docs = make_exports(target, random.Random(20261111))
    for rel, text in docs.items():
        path = target / "expected" / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")

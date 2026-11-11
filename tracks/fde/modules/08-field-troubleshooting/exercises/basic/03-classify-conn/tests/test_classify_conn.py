import json
import random
import re
import subprocess
import sys
from pathlib import Path

import pytest

from testkit import Exercise, run_sandboxed

ex = Exercise(__file__)
HERE = Path(__file__).resolve().parent
SAMPLES = HERE / "samples"
LABELS = json.loads((HERE / "labels.json").read_text())
CLASSES = {"dns", "route", "refused", "timeout", "tls-ca", "tls-hostname", "proxy-auth", "ok"}
NAMES = ["pypi.org", "registry.npmjs.org", "archive.ubuntu.com", "quillo.benhvien.local"]
ADDRESSES = ["10.0.2.100", "10.255.255.1", "93.184.215.14", "151.101.0.223", "10.0.2.77", "10.0.2.88"]
PORTS = ["3128", "18080", "8443", "8444", "8080", "5432"]


def classify(path: Path, tmp_path: Path) -> str:
    try:
        done = run_sandboxed([sys.executable, str(ex.path("classify_conn.py")), str(path)], writable=[tmp_path],
                             cwd=tmp_path, env={}, timeout=20)
    except subprocess.TimeoutExpired:
        pytest.fail(f"classify_conn.py chạy quá 20 s với {path.name}")
    assert done.returncode == 0, f"{path.name}: classify_conn.py thoát {done.returncode}\n{done.stderr[-1500:]}"
    lines = done.stdout.strip().splitlines()
    assert len(lines) == 1, f"{path.name}: stdout phải đúng một dòng (tên loại), có {done.stdout[-300:]!r}"
    return lines[0].strip()


def rewrite(text: str, rng: random.Random) -> str:
    """Đổi tên máy, địa chỉ, cổng, user proxy sang giá trị ngẫu nhiên nhất quán (như output của một khách khác)."""
    mapping: dict[str, str] = {}
    for name in NAMES:
        mapping[name] = f"{rng.choice(['files', 'sso', 'api', 'repo', 'mirror'])}{rng.randint(2, 98)}." \
                        f"{rng.choice(['corp', 'noibo', 'site'])}{rng.randint(1, 9)}.{rng.choice(['vn', 'com', 'net'])}"
    for address in ADDRESSES:
        mapping[address] = f"10.{rng.randint(1, 254)}.{rng.randint(0, 254)}.{rng.randint(2, 250)}"
    used = set()
    for port in PORTS:
        new = str(rng.randint(1100, 60000))
        while new in used:
            new = str(rng.randint(1100, 60000))
        used.add(new)
        mapping[port] = new
    mapping["svc-proxy"] = f"svc{rng.randint(10, 99)}"
    pattern = re.compile(r"(?<![\w.])(" + "|".join(re.escape(k) for k in sorted(mapping, key=len, reverse=True))
                         + r")(?![\w])")
    return pattern.sub(lambda m: mapping[m.group(1)], text)


def test_labels_cover_samples():
    assert {p.stem for p in SAMPLES.glob("*.txt")} == set(LABELS)
    assert all(set(v) <= CLASSES for v in LABELS.values())


@pytest.mark.parametrize("name", sorted(LABELS))
def test_recorded_output(name, tmp_path):
    got = classify(SAMPLES / f"{name}.txt", tmp_path)
    assert got in LABELS[name], f"{name}: phân loại {got!r}, đúng là {' hoặc '.join(LABELS[name])}"


def test_other_customer_same_errors(tmp_path):
    rng = random.Random()
    wrong = []
    for name in sorted(LABELS):
        text = rewrite((SAMPLES / f"{name}.txt").read_text(), rng)
        path = tmp_path / f"case-{rng.randint(10000, 99999)}-{len(wrong)}.txt"
        path.write_text(text)
        got = classify(path, tmp_path)
        if got not in LABELS[name]:
            wrong.append(f"{name} (sau khi đổi tên máy/địa chỉ/cổng): {got!r}, đúng là {LABELS[name]}")
        path.unlink()
    assert not wrong, "Phân loại sai khi cùng lỗi xảy ra ở máy khác:\n" + "\n".join(wrong)

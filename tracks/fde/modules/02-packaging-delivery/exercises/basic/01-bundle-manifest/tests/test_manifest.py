import copy
import hashlib
import json
import os
import tracemalloc
from pathlib import Path

import pytest

from testkit import Exercise

ex = Exercise(__file__)


def lib():
    return ex.module("manifest.py")


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


@pytest.fixture
def bundle(tmp_path) -> tuple[Path, dict[str, bytes]]:
    root = tmp_path / "beacon-1.4.0"
    files = {
        "app/beacon.py": os.urandom(3000),
        "app/VERSION": b"1.4.0\n",
        "config/beacon.env": b"BEACON_PORT=8088\n",
        "models/weights.bin": os.urandom(300_000),
        "models/tokenizer/vocab.txt": os.urandom(5000),
        "README": b"",
    }
    for name, data in files.items():
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
    (root / "logs").mkdir()
    return root, files


def test_make_manifest_lists_every_file(bundle):
    root, files = bundle
    manifest = lib().make_manifest(root)
    assert set(manifest) == {"files"}, "Manifest chỉ có khoá 'files' (xem README)"
    want = {name: {"sha256": sha(data), "size": len(data)} for name, data in files.items()}
    assert manifest["files"] == want
    assert list(manifest["files"]) == sorted(want), "Khoá trong 'files' phải sắp xếp tăng dần"
    json.dumps(manifest)


def test_manifest_json_is_not_listed(bundle):
    root, files = bundle
    (root / "manifest.json").write_text("{}")
    assert "manifest.json" not in lib().make_manifest(root)["files"]


def test_symlink_rejected(bundle):
    root, _ = bundle
    (root / "app" / "link").symlink_to("/etc/passwd")
    with pytest.raises(ValueError):
        lib().make_manifest(root)


def test_hashing_streams_large_files(tmp_path):
    root = tmp_path / "big"
    root.mkdir()
    with open(root / "weights.bin", "wb") as handle:
        for _ in range(40):
            handle.write(os.urandom(1 << 20))
    module = lib()
    tracemalloc.start()
    try:
        manifest = module.make_manifest(root)
        _, peak = tracemalloc.get_traced_memory()
    finally:
        tracemalloc.stop()
    assert manifest["files"]["weights.bin"]["size"] == 40 << 20
    assert peak < 8 << 20, f"make_manifest dùng tới {peak >> 20} MiB RAM cho tệp 40 MiB: phải đọc theo khối"


def test_verify_clean_bundle(bundle):
    root, _ = bundle
    module = lib()
    assert module.verify_manifest(root, module.make_manifest(root)) == []


def test_verify_reports_missing_extra_and_wrong_sha(bundle):
    root, _ = bundle
    module = lib()
    manifest = module.make_manifest(root)
    (root / "models" / "tokenizer" / "vocab.txt").unlink()
    (root / "app" / "debug.py").write_text("print('x')\n")
    weights = root / "models" / "weights.bin"
    data = bytearray(weights.read_bytes())
    data[1234] ^= 0xFF
    weights.write_bytes(bytes(data))
    (root / "app" / "VERSION").write_text("1.4.1\n")
    got = module.verify_manifest(root, manifest)
    assert sorted(got) == sorted([
        "thiếu: models/tokenizer/vocab.txt",
        "thừa: app/debug.py",
        "sai sha256: models/weights.bin",
        "sai sha256: app/VERSION",
    ])


def test_verify_truncated_file(bundle):
    root, _ = bundle
    module = lib()
    manifest = module.make_manifest(root)
    weights = root / "models" / "weights.bin"
    weights.write_bytes(weights.read_bytes()[:1000])
    assert module.verify_manifest(root, manifest) == ["sai sha256: models/weights.bin"]


def test_verify_ignores_manifest_json_itself(bundle):
    root, _ = bundle
    module = lib()
    manifest = module.make_manifest(root)
    (root / "manifest.json").write_text(json.dumps(manifest))
    assert module.verify_manifest(root, manifest) == []


def test_verify_rejects_unsafe_paths_without_reading_them(bundle, tmp_path):
    root, _ = bundle
    module = lib()
    manifest = copy.deepcopy(module.make_manifest(root))
    outside = tmp_path / "secret.txt"
    outside.write_bytes(b"ngoai bundle\n")
    entry = {"sha256": sha(b"ngoai bundle\n"), "size": 13}
    manifest["files"]["../secret.txt"] = entry
    manifest["files"][str(outside)] = entry
    got = module.verify_manifest(root, manifest)
    assert sorted(got) == sorted(["đường dẫn không an toàn: ../secret.txt", f"đường dẫn không an toàn: {outside}"])


def test_verify_symlink_in_bundle_is_a_problem(bundle):
    root, files = bundle
    module = lib()
    manifest = module.make_manifest(root)
    target = root / "config" / "beacon.env"
    target.unlink()
    target.symlink_to("/etc/hostname")
    got = module.verify_manifest(root, manifest)
    assert got == ["sai sha256: config/beacon.env"], (
        "Tệp trong manifest mà ở bundle là symlink phải bị báo 'sai sha256', không đi theo link")

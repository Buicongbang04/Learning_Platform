import hashlib
import io
import json
import shutil
import subprocess
import sys
import tarfile
import uuid

import pytest

import release
import testkit
from quillo.config import PRODUCT_DIR

BUDGET = int(1.5 * 1024**3)


def run_verify(path) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(PRODUCT_DIR / "release.py"), "verify", str(path)],
                          capture_output=True, text=True, timeout=300)


@pytest.fixture(scope="module")
def bundle():
    if not testkit.docker_ready():
        pytest.skip("release.py build cần Docker đang chạy")
    out = PRODUCT_DIR / "dist" / f"pytest-{uuid.uuid4().hex[:8]}"
    try:
        yield release.build("1.0.0", out)
    finally:
        shutil.rmtree(out, ignore_errors=True)


def test_release_bundle_layout(bundle):
    assert bundle.name == "quillo-1.0.0.tar"
    with tarfile.open(bundle) as tar:
        members = {m.name: m for m in tar.getmembers() if m.isfile()}
        manifest = json.load(tar.extractfile("quillo-1.0.0/manifest.json"))
        assert manifest["version"] == "1.0.0"
        files = {f"quillo-1.0.0/{path}" for path in manifest["files"]}
        assert files == set(members) - {"quillo-1.0.0/manifest.json"}
        for path, digest in manifest["files"].items():
            assert hashlib.file_digest(tar.extractfile(f"quillo-1.0.0/{path}"), "sha256").hexdigest() == digest
    names = set(manifest["files"])
    assert {"compose.yaml", ".env.example", "REQUIREMENTS.yaml", "LICENSE", "migrations/0001_init.sql"} <= names
    assert "migrations/0002_v1_1_tags.sql" not in names
    assert {"models/qwen2.5-0.5b-instruct-q4_k_m.gguf", "models/nomic-embed-text-v1.5.Q8_0.gguf"} <= names
    assert sorted(n for n in names if n.startswith("images/")) == [
        "images/llama-cpp-server.tar", "images/pgvector.tar", "images/quillo-api.tar"]
    assert "quillo-api:1.0.0" in manifest["images"]
    assert set(release.IMAGES.values()) <= set(manifest["images"])
    assert run_verify(bundle).returncode == 0


def test_bundle_api_image_runs_as_non_root(bundle):
    with tarfile.open(bundle) as tar:
        image = tarfile.open(fileobj=io.BytesIO(tar.extractfile("quillo-1.0.0/images/quillo-api.tar").read()))
        manifest = json.load(image.extractfile("manifest.json"))[0]
        config = json.load(image.extractfile(manifest["Config"]))
        assert manifest["RepoTags"] == ["quillo-api:1.0.0"]
        assert config["config"]["User"] == "10001"
        assert "QUILLO_VERSION=1.0.0" in config["config"]["Env"]
        env = tar.extractfile("quillo-1.0.0/.env.example").read().decode()
        assert "QUILLO_VERSION=1.0.0" in env and "QUILLO_ADMIN_TOKEN=\n" in env


def test_bundle_manifest_detects_tamper(bundle):
    with tarfile.open(bundle) as tar:
        offset = tar.getmember("quillo-1.0.0/compose.yaml").offset_data
    with open(bundle, "r+b") as handle:
        handle.seek(offset)
        original = handle.read(1)
        handle.seek(offset)
        handle.write(bytes([original[0] ^ 0x01]))
    try:
        result = run_verify(bundle)
        assert result.returncode == 1
        assert "compose.yaml" in result.stdout + result.stderr
    finally:
        with open(bundle, "r+b") as handle:
            handle.seek(offset)
            handle.write(original)
    assert run_verify(bundle).returncode == 0


def test_bundle_size_budget(bundle):
    size = bundle.stat().st_size
    print(f"quillo-1.0.0.tar (llm-small): {size / 1024**3:.2f} GiB")
    assert size <= BUDGET


def small_bundle(path, files: dict[str, bytes], manifest_files: dict[str, str]) -> None:
    manifest = json.dumps({"version": "1.0.0", "files": manifest_files, "images": []}).encode()
    with tarfile.open(path, "w") as tar:
        for name, data in {"manifest.json": manifest, **files}.items():
            info = tarfile.TarInfo(f"quillo-1.0.0/{name}")
            info.size = len(data)
            tar.addfile(info, io.BytesIO(data))


def test_verify_detects_missing_and_extra_files(tmp_path):
    good = {"compose.yaml": b"services: {}\n"}
    sha = {"compose.yaml": hashlib.sha256(good["compose.yaml"]).hexdigest()}
    small_bundle(tmp_path / "ok.tar", good, sha)
    assert run_verify(tmp_path / "ok.tar").returncode == 0
    small_bundle(tmp_path / "missing.tar", {}, sha)
    missing = run_verify(tmp_path / "missing.tar")
    assert missing.returncode == 1 and "compose.yaml" in missing.stdout
    small_bundle(tmp_path / "extra.tar", {**good, "evil.sh": b"rm -rf /"}, sha)
    extra = run_verify(tmp_path / "extra.tar")
    assert extra.returncode == 1 and "evil.sh" in extra.stdout
    (tmp_path / "cut.tar").write_bytes((tmp_path / "ok.tar").read_bytes()[:700])
    assert run_verify(tmp_path / "cut.tar").returncode == 1
    assert run_verify(tmp_path / "nope.tar").returncode == 1


def test_verify_rejects_unsafe_paths(tmp_path):
    data = b"x"
    manifest = json.dumps({"version": "1.0.0", "files": {"../escape": hashlib.sha256(data).hexdigest()},
                           "images": []}).encode()
    with tarfile.open(tmp_path / "evil.tar", "w") as tar:
        for name, payload in (("quillo-1.0.0/manifest.json", manifest), ("quillo-1.0.0/../escape", data)):
            info = tarfile.TarInfo(name)
            info.size = len(payload)
            tar.addfile(info, io.BytesIO(payload))
    assert run_verify(tmp_path / "evil.tar").returncode == 1

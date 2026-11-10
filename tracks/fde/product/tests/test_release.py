import hashlib
import io
import json
import shutil
import subprocess
import sys
import tarfile

import pytest
import yaml

import release
from quillo.config import PRODUCT_DIR

BUDGET = int(1.5 * 1024**3)


def run_verify(path) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(PRODUCT_DIR / "release.py"), "verify", str(path)],
                          capture_output=True, text=True, timeout=300)


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


def test_env_example_follows_llm_choice():
    import fdekit

    small = release.env_example("1.0.0")
    assert "QUILLO_VERSION=1.0.0\n" in small and "QUILLO_LLM_MODEL=llm-small\n" in small
    assert f"QUILLO_LLM_FILE={fdekit.MODELS['llm-small'].filename}\n" in small
    medium = release.env_example("1.1.0", "llm-medium")
    assert f"QUILLO_LLM_FILE={fdekit.MODELS['llm-medium'].filename}\n" in medium
    assert "QUILLO_LLM_MODEL=llm-medium\n" in medium and "QUILLO_VERSION=1.1.0\n" in medium


def test_verify_rejects_outside_top_folder_and_wrong_version(tmp_path):
    data = b"services: {}\n"
    sha = {"compose.yaml": hashlib.sha256(data).hexdigest()}
    small_bundle(tmp_path / "ok.tar", {"compose.yaml": data}, sha)
    with tarfile.open(tmp_path / "ok.tar", "a") as tar:
        info = tarfile.TarInfo("other/install.sh")
        info.size = 2
        tar.addfile(info, io.BytesIO(b"hi"))
    outside = run_verify(tmp_path / "ok.tar")
    assert outside.returncode == 1 and "ngoài thư mục gốc" in outside.stdout
    manifest = json.dumps({"version": "1.1.0", "files": sha, "images": []}).encode()
    with tarfile.open(tmp_path / "renamed.tar", "w") as tar:
        for name, payload in (("quillo-1.0.0/manifest.json", manifest), ("quillo-1.0.0/compose.yaml", data)):
            info = tarfile.TarInfo(name)
            info.size = len(payload)
            tar.addfile(info, io.BytesIO(payload))
    renamed = run_verify(tmp_path / "renamed.tar")
    assert renamed.returncode == 1 and "1.1.0" in renamed.stdout


def test_build_removes_partial_bundle_on_failure(tmp_path, monkeypatch):
    import fdekit

    blob = tmp_path / "blob.bin"
    blob.write_bytes(b"x" * 1024)
    monkeypatch.setattr(release, "build_api_image", lambda version, work: f"quillo-api:{version}")
    monkeypatch.setattr(release, "save_images", lambda tag, work: {"images/quillo-api.tar": blob})
    monkeypatch.setattr(release, "derived_images", lambda version, sources, work: {})
    monkeypatch.setattr(fdekit, "fetch_model", lambda name: blob.with_name(f"{name}.gguf"))
    for name in ("llm-small", "embed-small"):
        blob.with_name(f"{name}.gguf").write_bytes(b"gguf")
    original = tarfile.TarFile.addfile
    calls = []

    def failing(self, info, fileobj=None, **kwargs):
        calls.append(info.name)
        if len(calls) == 3:
            raise OSError("No space left on device")
        return original(self, info, fileobj, **kwargs)

    monkeypatch.setattr(tarfile.TarFile, "addfile", failing)
    out = tmp_path / "out"
    with pytest.raises(OSError, match="No space"):
        release.build("1.0.0", out)
    assert list(out.iterdir()) == []


def test_verify_handles_dot_members(tmp_path):
    data = b"services: {}\n"
    manifest = json.dumps({"version": "1.0.0", "files": {"compose.yaml": hashlib.sha256(data).hexdigest()},
                           "images": []}).encode()

    def write(path, extra=()):
        with tarfile.open(path, "w") as tar:
            root = tarfile.TarInfo(".")
            root.type = tarfile.DIRTYPE
            tar.addfile(root)
            for name, payload in (("./quillo-1.0.0/manifest.json", manifest), ("./quillo-1.0.0/compose.yaml", data),
                                  *extra):
                info = tarfile.TarInfo(name)
                info.size = len(payload)
                tar.addfile(info, io.BytesIO(payload))

    write(tmp_path / "dotted.tar")
    ok = run_verify(tmp_path / "dotted.tar")
    assert ok.returncode == 0, ok.stdout + ok.stderr
    write(tmp_path / "outside.tar", [("./evil.sh", b"x")])
    outside = run_verify(tmp_path / "outside.tar")
    assert outside.returncode == 1 and "evil.sh" in outside.stdout and "Traceback" not in outside.stderr


def test_bundle_contains_chart_and_ops(bundle):
    with tarfile.open(bundle) as tar:
        manifest = json.load(tar.extractfile("quillo-1.0.0/manifest.json"))
        names = set(manifest["files"])
        assert {"chart/quillo-1.0.0.tgz", "ops/backup.sh", "ops/restore.sh", "ops/models_image.py",
                "compose.sso.yaml", "compose.extensions.yaml"} <= names
        assert "images/quillo-models.tar" not in names
        for script in ("ops/backup.sh", "ops/restore.sh"):
            assert tar.getmember(f"quillo-1.0.0/{script}").mode == 0o755
        chart = tarfile.open(fileobj=io.BytesIO(tar.extractfile("quillo-1.0.0/chart/quillo-1.0.0.tgz").read()))
        meta = yaml.safe_load(chart.extractfile("quillo/Chart.yaml"))
        values = yaml.safe_load(chart.extractfile("quillo/values.yaml"))
    assert meta["version"] == meta["appVersion"] == "1.0.0"
    assert values["models"]["llmFile"] == "qwen2.5-0.5b-instruct-q4_k_m.gguf" and values["models"]["llmAlias"] == "llm-small"
    assert {"quillo/values.yaml", "quillo/templates/api.yaml"} <= set(chart.getnames())
    assert not [n for n in chart.getnames() if not n.startswith("quillo/")]
    assert manifest["derived"]["images/quillo-models.tar"]["image"] == "quillo-models:1.0.0"


def blob(tar: tarfile.TarFile, digest: str) -> bytes:
    return tar.extractfile(f"blobs/sha256/{digest.removeprefix('sha256:')}").read()


def test_bundle_contains_chart_and_models_image(bundle):
    """Image quillo-models dựng từ chính bundle bằng ops/models_image.py: tái lập đúng sha ghi trong manifest, là OCI
    layout hợp lệ (digest/diff_id khớp), có models/*.gguf và giữ các layer của llama.cpp (có `cp`)."""
    import fdekit

    work = bundle.parent / "models-image"
    try:
        with tarfile.open(bundle) as tar:
            members = [m for m in tar.getmembers() if m.isfile() and (
                m.name.endswith(("manifest.json", "llama-cpp-server.tar", ".gguf")) or "/ops/" in m.name)]
            tar.extractall(work, members=members, filter="data")
        root = work / "quillo-1.0.0"
        out = work / "quillo-models.tar"
        made = subprocess.run([sys.executable, str(root / "ops" / "models_image.py"), str(root), str(out)],
                              capture_output=True, text=True, timeout=300)
        assert made.returncode == 0 and "khớp manifest.json" in made.stdout, made.stdout + made.stderr
        with tarfile.open(out) as image, tarfile.open(root / "images" / "llama-cpp-server.tar") as base:
            index = json.load(image.extractfile("index.json"))
            assert index["manifests"][0]["annotations"]["io.containerd.image.name"] == "docker.io/library/quillo-models:1.0.0"
            manifest = json.loads(blob(image, index["manifests"][0]["digest"]))
            config_bytes = blob(image, manifest["config"]["digest"])
            assert hashlib.sha256(config_bytes).hexdigest() == manifest["config"]["digest"][7:]
            config = json.loads(config_bytes)
            assert config["config"]["User"] == "65534"
            docker_manifest = json.load(image.extractfile("manifest.json"))[0]
            assert docker_manifest["RepoTags"] == ["quillo-models:1.0.0"]
            base_index = json.load(base.extractfile("index.json"))
            base_layers = json.loads(blob(base, base_index["manifests"][0]["digest"]))["layers"]
            assert manifest["layers"][:-1] == base_layers
            last = manifest["layers"][-1]
            data = blob(image, last["digest"])
            assert hashlib.sha256(data).hexdigest() == last["digest"][7:] == config["rootfs"]["diff_ids"][-1][7:]
            assert len(config["rootfs"]["diff_ids"]) == len(manifest["layers"])
            with tarfile.open(fileobj=io.BytesIO(data)) as layer:
                sizes = {m.name: m.size for m in layer.getmembers() if m.isfile()}
        for name in ("llm-small", "embed-small"):
            model = fdekit.fetch_model(name)
            assert sizes[f"models/{model.name}"] == model.stat().st_size
        again = subprocess.run([sys.executable, str(root / "ops" / "models_image.py"), str(root), str(out)],
                               capture_output=True, text=True, timeout=300)
        assert again.returncode == 0
        (root / "models" / "nomic-embed-text-v1.5.Q8_0.gguf").write_bytes(b"tampered")
        tampered = subprocess.run([sys.executable, str(root / "ops" / "models_image.py"), str(root), str(out)],
                                  capture_output=True, text=True, timeout=300)
        assert tampered.returncode == 1 and "khác manifest.json" in tampered.stderr and not out.exists()
    finally:
        shutil.rmtree(work, ignore_errors=True)

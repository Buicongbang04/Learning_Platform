"""Đóng gói bản phát hành offline của quillo và kiểm tra bundle.

    python release.py build --version 1.0.0 --out dist/
    python release.py verify dist/quillo-1.0.0.tar

Bundle `quillo-<version>.tar` (không nén: layer image và GGUF vốn đã nén) chứa thư mục `quillo-<version>/` với
`manifest.json` ({"version", "files": {đường dẫn: sha256}, "images": [ref]}), `images/*.tar` (`docker save`),
`models/*.gguf`, `compose.yaml`, `.env.example`, `REQUIREMENTS.yaml`, `LICENSE`, `migrations/`.
Lệnh build cần Docker và mạng (pull image, tải model lần đầu); bundle tạo ra thì cài được không cần mạng.
"""

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path, PurePosixPath

PRODUCT = Path(__file__).resolve().parent
ROOT = PRODUCT.parents[2]
sys.path[:0] = [str(PRODUCT / "src"), str(ROOT)]

from quillo import db

IMAGES = {
    "db": "pgvector/pgvector:0.8.6-pg16@sha256:ccc6e83d6e35e931dc7c5def2022729d5a6c370318d099181995567ff1fb4d6b",
    "llm": "ghcr.io/ggml-org/llama.cpp:server-b11718@sha256:4b7be0376002b4450a357a109bab804093ff9251193cc75ed4ce0cb39953ff5c",
}
IMAGE_FILES = {"db": "images/pgvector.tar", "llm": "images/llama-cpp-server.tar", "api": "images/quillo-api.tar"}
EMBED_MODEL = "embed-small"
STATIC_FILES = ("compose.yaml", "REQUIREMENTS.yaml", "LICENSE")
BUILD_CONTEXT = ("Dockerfile", "requirements.lock", "LICENSE", "src")
PLATFORM = "linux/amd64"


def tag_only(ref: str) -> str:
    return ref.split("@", 1)[0]


def migrations_for(version: str) -> list[Path]:
    return [path for _, path in db.migration_files(PRODUCT / "migrations", db.schema_for(version))]


def sha256(path: Path) -> str:
    with open(path, "rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def docker(*args: str) -> None:
    print("+ docker", " ".join(args), flush=True)
    subprocess.run(["nice", "-n", "15", "docker", *args], check=True)


def _has_image(ref: str) -> bool:
    return subprocess.run(["docker", "image", "inspect", ref], capture_output=True).returncode == 0


def build_api_image(version: str, work: Path) -> str:
    context = work / "context"
    context.mkdir()
    for name in BUILD_CONTEXT:
        source = PRODUCT / name
        if source.is_dir():
            shutil.copytree(source, context / name, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        else:
            shutil.copy2(source, context / name)
    (context / "migrations").mkdir()
    for path in migrations_for(version):
        shutil.copy2(path, context / "migrations" / path.name)
    tag = f"quillo-api:{version}"
    docker("build", "--pull=false", "--platform", PLATFORM, "--build-arg", f"QUILLO_VERSION={version}", "-t", tag,
           str(context))
    return tag


def save_images(api_tag: str, work: Path) -> dict[str, Path]:
    saved = {}
    for key, ref in IMAGES.items():
        if not _has_image(ref):
            docker("pull", "--platform", PLATFORM, ref)
        docker("tag", ref, tag_only(ref))
    for key, ref in {**{k: tag_only(v) for k, v in IMAGES.items()}, "api": api_tag}.items():
        target = work / IMAGE_FILES[key]
        target.parent.mkdir(parents=True, exist_ok=True)
        docker("save", "--platform", PLATFORM, "-o", str(target), ref)
        saved[IMAGE_FILES[key]] = target
    return saved


def env_example(version: str, llm: str = "llm-small") -> str:
    """`.env.example` của bundle: bản và model chat khớp đúng thứ có trong bundle."""
    import fdekit

    values = {"QUILLO_VERSION": version, "QUILLO_LLM_FILE": fdekit.MODELS[llm].filename, "QUILLO_LLM_MODEL": llm}
    text = (PRODUCT / ".env.example").read_text()
    for key, value in values.items():
        text, count = re.subn(rf"(?m)^{key}=.*$", f"{key}={value}", text)
        if count != 1:
            raise ValueError(f".env.example phải có đúng một dòng {key}=")
    return text


def build(version: str, out: Path, llm: str = "llm-small") -> Path:
    import fdekit

    db.schema_for(version)
    out = Path(out).resolve()
    out.mkdir(parents=True, exist_ok=True)
    bundle = out / f"quillo-{version}.tar"
    with tempfile.TemporaryDirectory(dir=out, prefix=".build-") as tmp:
        work = Path(tmp)
        api_tag = build_api_image(version, work)
        sources: dict[str, Path] = save_images(api_tag, work)
        (work / ".env.example").write_text(env_example(version, llm))
        sources[".env.example"] = work / ".env.example"
        for name in STATIC_FILES:
            sources[name] = PRODUCT / name
        for path in migrations_for(version):
            sources[f"migrations/{path.name}"] = path
        for name in (llm, EMBED_MODEL):
            model = fdekit.fetch_model(name)
            sources[f"models/{model.name}"] = model
        manifest = {"version": version, "files": {name: sha256(path) for name, path in sorted(sources.items())},
                    "images": [*IMAGES.values(), api_tag]}
        (work / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
        part = bundle.with_name(bundle.name + ".part")
        prefix = f"quillo-{version}"
        try:
            with tarfile.open(part, "w", format=tarfile.PAX_FORMAT) as tar:
                tar.add(work / "manifest.json", f"{prefix}/manifest.json")
                for name, path in sorted(sources.items()):
                    info = tar.gettarinfo(path, f"{prefix}/{name}")
                    info.uid = info.gid = 0
                    info.uname = info.gname = ""
                    info.mode = 0o644
                    with open(path, "rb") as handle:
                        tar.addfile(info, handle)
            os.replace(part, bundle)
        except BaseException:
            part.unlink(missing_ok=True)
            raise
    print(f"{bundle} ({bundle.stat().st_size / 1024**3:.2f} GiB)")
    return bundle


def _safe(name: str) -> bool:
    path = PurePosixPath(name)
    return not path.is_absolute() and ".." not in path.parts


def verify(bundle: Path) -> list[str]:
    """Trả danh sách lỗi (rỗng = bundle nguyên vẹn): sha256 sai, thiếu tệp, tệp lạ ngoài manifest, đường dẫn nguy hiểm."""
    problems: list[str] = []
    try:
        with tarfile.open(bundle) as tar:
            members = tar.getmembers()
            unsafe = [m.name for m in members if not _safe(m.name) or not (m.isfile() or m.isdir())]
            if unsafe:
                return [f"đường dẫn/loại tệp không an toàn: {name}" for name in unsafe]
            files = {m.name: m for m in members if m.isfile()}
            manifests = [name for name in files if PurePosixPath(name).name == "manifest.json"
                         and len(PurePosixPath(name).parts) == 2]
            if len(manifests) != 1:
                return ["không tìm thấy <bundle>/manifest.json"]
            prefix = PurePosixPath(manifests[0]).parent
            outside = sorted(m.name for m in members if PurePosixPath(m.name).parts[0] != prefix.name)
            if outside:
                return [f"tệp nằm ngoài thư mục gốc {prefix}/ của bundle: {name}" for name in outside]
            manifest = json.load(tar.extractfile(manifests[0]))
            if prefix.name != f"quillo-{manifest['version']}":
                return [f"manifest.json ghi version {manifest['version']!r} nhưng thư mục gốc là {prefix}/"]
            expected = manifest["files"]
            for name, digest in sorted(expected.items()):
                member = files.get(str(prefix / name))
                if not _safe(name):
                    problems.append(f"đường dẫn không an toàn trong manifest: {name}")
                elif member is None:
                    problems.append(f"thiếu tệp: {name}")
                elif hashlib.file_digest(tar.extractfile(member), "sha256").hexdigest() != digest:
                    problems.append(f"sha256 không khớp: {name}")
            listed = {str(prefix / name) for name in expected} | {manifests[0]}
            problems += [f"tệp không có trong manifest: {PurePosixPath(name).relative_to(prefix)}"
                         for name in sorted(set(files) - listed)]
    except (OSError, tarfile.TarError, EOFError, json.JSONDecodeError, KeyError, ValueError) as error:
        return [f"không đọc được bundle {bundle}: {error}"]
    return problems


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    commands = parser.add_subparsers(dest="command", required=True)
    build_cmd = commands.add_parser("build", help="dựng bundle offline")
    build_cmd.add_argument("--version", required=True, choices=sorted(db.SCHEMA_FOR_RELEASE))
    build_cmd.add_argument("--out", type=Path, default=PRODUCT / "dist")
    build_cmd.add_argument("--llm", default="llm-small", choices=["llm-small", "llm-medium"])
    verify_cmd = commands.add_parser("verify", help="kiểm sha256 mọi tệp trong bundle theo manifest.json")
    verify_cmd.add_argument("bundle", type=Path)
    args = parser.parse_args(argv)
    if args.command == "build":
        build(args.version, args.out, args.llm)
        return 0
    problems = verify(args.bundle)
    for problem in problems:
        print(problem)
    print("OK" if not problems else f"LỖI: {len(problems)} vấn đề")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())

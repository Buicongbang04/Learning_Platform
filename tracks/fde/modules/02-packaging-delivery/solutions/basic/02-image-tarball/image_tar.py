import hashlib
import json
import sys
import tarfile
from pathlib import Path, PurePosixPath

CHUNK = 1 << 20


class Unreadable(Exception):
    pass


def _digest_name(name: str) -> str | None:
    path = PurePosixPath(name)
    if len(path.parts) == 3 and path.parts[:2] == ("blobs", "sha256"):
        return path.parts[2]
    return None


def _load(tar: tarfile.TarFile) -> tuple[dict[str, tarfile.TarInfo], list[dict]]:
    members = {m.name.removeprefix("./"): m for m in tar.getmembers() if m.isfile()}
    if "manifest.json" not in members:
        raise Unreadable("không có manifest.json")
    manifest = json.load(tar.extractfile(members["manifest.json"]))
    if not isinstance(manifest, list):
        raise Unreadable("manifest.json không phải danh sách")
    return members, manifest


def _read_json(tar: tarfile.TarFile, member: tarfile.TarInfo) -> dict:
    return json.load(tar.extractfile(member))


def _sha256(tar: tarfile.TarFile, member: tarfile.TarInfo) -> str:
    sha = hashlib.sha256()
    handle = tar.extractfile(member)
    while chunk := handle.read(CHUNK):
        sha.update(chunk)
    return sha.hexdigest()


def _platform(config: dict) -> str:
    return f"{config.get('os')}/{config.get('architecture')}"


def _blob_ref(name: str) -> str:
    digest = _digest_name(name)
    return f"sha256:{digest}" if digest else name


def inspect_image(path: Path) -> dict:
    """{"tags", "platform", "config", "layers", "size"} của tarball `docker save` (xem README)."""
    with tarfile.open(path) as tar:
        members, manifest = _load(tar)
        entry = manifest[0]
        config = _read_json(tar, members[entry["Config"]])
        return {
            "tags": list(entry.get("RepoTags") or []),
            "platform": _platform(config),
            "config": _blob_ref(entry["Config"]),
            "layers": [_blob_ref(layer) for layer in entry["Layers"]],
            "size": sum(members[layer].size for layer in entry["Layers"]),
        }


def check_image(path: Path, platform: str) -> list[str]:
    """Danh sách vấn đề trước khi mang tarball tới khách có nền tảng `platform` (vd. linux/amd64); rỗng là đạt."""
    try:
        with tarfile.open(path) as tar:
            members, manifest = _load(tar)
            if len(manifest) != 1:
                return [f"cần đúng 1 image, có {len(manifest)}"]
            entry = manifest[0]
            problems = []
            for name in [entry["Config"], *entry["Layers"]]:
                member = members.get(name)
                if member is None:
                    problems.append(f"thiếu blob: {name}")
                    continue
                digest = _digest_name(name)
                if digest and _sha256(tar, member) != digest:
                    problems.append(f"sai digest: {name}")
            if entry["Config"] in members and not any(p.endswith(entry["Config"]) for p in problems):
                found = _platform(_read_json(tar, members[entry["Config"]]))
                if found != platform:
                    problems.append(f"sai nền tảng: {found}, cần {platform}")
            if not entry.get("RepoTags"):
                problems.append("không có tag")
            return problems
    except (Unreadable, tarfile.TarError, EOFError, OSError, KeyError, TypeError, ValueError) as error:
        return [f"không đọc được: {error}"]


if __name__ == "__main__":
    tar, want = Path(sys.argv[1]), sys.argv[2] if len(sys.argv) > 2 else "linux/amd64"
    print(json.dumps({"image": inspect_image(tar), "problems": check_image(tar, want)}, indent=2, ensure_ascii=False))

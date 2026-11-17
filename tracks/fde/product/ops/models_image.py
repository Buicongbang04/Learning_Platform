"""Dựng image `quillo-models:<version>` (OCI archive) từ chính bundle, không cần Docker hay mạng.

    python3 ops/models_image.py <thư mục bundle đã giải nén> <tệp ra .tar>

Image = các layer của `images/llama-cpp-server.tar` (đã có trong bundle, có `cp` và shell) + một layer chứa
`models/*.gguf` của bundle. Helm chart dùng nó cho initContainer chép GGUF vào pod llm/embed (không cần hostPath).
Bundle không mang sẵn image này vì GGUF đã có ở `models/`: mang hai lần làm bundle nặng thêm ~0,6 GB.

Kết quả tái lập từng byte (mtime 0, uid 0, thứ tự cố định): `manifest.json` của bundle ghi sha256 của tệp ra
(`derived["images/quillo-models.tar"]`) và script so với nó. Tệp ra nạp được bằng `docker load`, `podman load`,
`ctr images import`, hoặc đẩy lên registry bằng công cụ đọc OCI layout (skopeo, crane, regctl).
"""

from __future__ import annotations

import hashlib
import io
import json
import os
import sys
import tarfile
import tempfile
from pathlib import Path

BASE = "images/llama-cpp-server.tar"
OUTPUT = "images/quillo-models.tar"
OCI_MANIFEST = "application/vnd.oci.image.manifest.v1+json"
OCI_CONFIG = "application/vnd.oci.image.config.v1+json"
OCI_LAYER = "application/vnd.oci.image.layer.v1.tar"
USER = "65534"
CHUNK = 1 << 20


def _digest(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


def _file_digest(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(CHUNK), b""):
            digest.update(block)
    return "sha256:" + digest.hexdigest()


def _json(value) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode()


def _info(name: str, size: int = 0, directory: bool = False) -> tarfile.TarInfo:
    info = tarfile.TarInfo(name)
    info.size, info.mtime, info.uid, info.gid, info.uname, info.gname = size, 0, 0, 0, "", ""
    info.type = tarfile.DIRTYPE if directory else tarfile.REGTYPE
    info.mode = 0o755 if directory else 0o644
    return info


def _models_layer(models: list[Path], target: Path) -> str:
    """Layer tar không nén: `models/` + các GGUF; trả digest (cũng là diff_id vì không nén)."""
    with tarfile.open(target, "w", format=tarfile.USTAR_FORMAT) as tar:
        tar.addfile(_info("models/", directory=True))
        for model in models:
            with open(model, "rb") as handle:
                tar.addfile(_info(f"models/{model.name}", model.stat().st_size), handle)
    return _file_digest(target)


def build(bundle: Path, out: Path) -> str:
    """Ghi OCI archive của `quillo-models:<version>` vào `out`, trả sha256 của tệp ra."""
    version = json.loads((bundle / "manifest.json").read_text())["version"]
    models = sorted((bundle / "models").glob("*.gguf"))
    out.parent.mkdir(parents=True, exist_ok=True)
    if not models:
        raise SystemExit(f"models_image: không có models/*.gguf trong {bundle}")
    with tarfile.open(bundle / BASE) as base, tempfile.TemporaryDirectory(dir=out.parent) as tmp:
        index = json.load(base.extractfile("index.json"))
        [entry] = index["manifests"]
        manifest = json.load(base.extractfile(f"blobs/sha256/{entry['digest'].split(':')[1]}"))
        config = json.load(base.extractfile(f"blobs/sha256/{manifest['config']['digest'].split(':')[1]}"))
        layer_path = Path(tmp) / "models-layer.tar"
        layer = _models_layer(models, layer_path)
        config["rootfs"]["diff_ids"].append(layer)
        config["config"] = {**config.get("config", {}), "User": USER, "Entrypoint": None, "Cmd": ["ls", "/models"],
                            "Labels": {"org.opencontainers.image.title": "quillo-models",
                                       "org.opencontainers.image.version": version}}
        config["history"] = [*config.get("history", []),
                             {"created": "1970-01-01T00:00:00Z", "created_by": "quillo ops/models_image.py"}]
        config.pop("created", None)
        config_blob = _json(config)
        layers = [*manifest["layers"], {"mediaType": OCI_LAYER, "digest": layer, "size": layer_path.stat().st_size}]
        image_manifest = _json({"schemaVersion": 2, "mediaType": OCI_MANIFEST, "layers": layers,
                                "config": {"mediaType": OCI_CONFIG, "digest": _digest(config_blob),
                                           "size": len(config_blob)}})
        ref = f"quillo-models:{version}"
        blobs = {_digest(config_blob): config_blob, _digest(image_manifest): image_manifest}
        new_index = _json({"schemaVersion": 2, "mediaType": "application/vnd.oci.image.index.v1+json", "manifests": [
            {"mediaType": OCI_MANIFEST, "digest": _digest(image_manifest), "size": len(image_manifest),
             "platform": {"architecture": "amd64", "os": "linux"},
             "annotations": {"io.containerd.image.name": f"docker.io/library/{ref}",
                             "org.opencontainers.image.ref.name": version}}]})
        docker_manifest = _json([{"Config": f"blobs/sha256/{_digest(config_blob)[7:]}", "RepoTags": [ref],
                                  "Layers": [f"blobs/sha256/{item['digest'][7:]}" for item in layers]}])
        part = out.with_name(out.name + ".part")
        with tarfile.open(part, "w", format=tarfile.USTAR_FORMAT) as tar:
            tar.addfile(_info("blobs/", directory=True))
            tar.addfile(_info("blobs/sha256/", directory=True))
            for item in manifest["layers"]:
                member = base.getmember(f"blobs/sha256/{item['digest'][7:]}")
                tar.addfile(_info(member.name, member.size), base.extractfile(member))
            with open(layer_path, "rb") as handle:
                tar.addfile(_info(f"blobs/sha256/{layer[7:]}", layer_path.stat().st_size), handle)
            for digest, data in sorted(blobs.items()):
                tar.addfile(_info(f"blobs/sha256/{digest[7:]}", len(data)), io.BytesIO(data))
            for name, data in (("oci-layout", b'{"imageLayoutVersion":"1.0.0"}'), ("index.json", new_index),
                               ("manifest.json", docker_manifest)):
                tar.addfile(_info(name, len(data)), io.BytesIO(data))
        os.replace(part, out)
    return _file_digest(out)[7:]


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print(__doc__.strip(), file=sys.stderr)
        return 2
    bundle, out = Path(argv[0]), Path(argv[1]).resolve()
    sha = build(bundle, out)
    expected = json.loads((bundle / "manifest.json").read_text()).get("derived", {}).get(OUTPUT, {}).get("sha256")
    if expected and expected != sha:
        out.unlink()
        print(f"models_image: sha256 {sha} khác manifest.json ({expected}): bundle hỏng hoặc khác bản", file=sys.stderr)
        return 1
    print(f"{out} sha256={sha}{' (khớp manifest.json)' if expected else ''}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

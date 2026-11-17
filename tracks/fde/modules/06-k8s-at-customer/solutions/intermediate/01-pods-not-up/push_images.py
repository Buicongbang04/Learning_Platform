"""Đẩy image từ OCI archive (docker save, models_image.py) lên registry HTTP, chỉ dùng thư viện chuẩn Python 3.8+.

    python3 push_images.py <registry host:port> <archive.tar>...

Tên đích bỏ host gốc (docker.io/library/, ghcr.io/...) như chart quillo: <registry>/<đường dẫn>:<tag>.
"""

from __future__ import annotations

import http.client
import json
import sys
import tarfile

MANIFEST_TYPES = ("application/vnd.oci.image.manifest.v1+json", "application/vnd.docker.distribution.manifest.v2+json")


def target_name(ref: str) -> tuple[str, str]:
    name, _, tag = ref.rpartition(":")
    parts = name.split("/")
    if len(parts) > 1 and ("." in parts[0] or ":" in parts[0] or parts[0] == "localhost"):
        parts = parts[1:]
    if parts[0] == "library" and len(parts) > 1:
        parts = parts[1:]
    return "/".join(parts), tag


class Registry:
    def __init__(self, address: str) -> None:
        self.address = address

    def request(self, method: str, path: str, body=None, headers: dict | None = None) -> http.client.HTTPResponse:
        conn = http.client.HTTPConnection(self.address, timeout=300)
        conn.request(method, path, body=body, headers=headers or {})
        response = conn.getresponse()
        response.data = response.read()
        conn.close()
        return response

    def has_blob(self, repo: str, digest: str) -> bool:
        return self.request("HEAD", f"/v2/{repo}/blobs/{digest}").status == 200

    def put_blob(self, repo: str, digest: str, size: int, stream) -> None:
        if self.has_blob(repo, digest):
            return
        started = self.request("POST", f"/v2/{repo}/blobs/uploads/", headers={"Content-Length": "0"})
        if started.status != 202:
            raise SystemExit(f"push: bắt đầu upload {digest} lỗi HTTP {started.status}: {started.data[:300]!r}")
        location = started.getheader("Location")
        if location.startswith("http"):
            location = "/" + location.split("/", 3)[3]
        joiner = "&" if "?" in location else "?"
        done = self.request("PUT", f"{location}{joiner}digest={digest}", body=stream,
                            headers={"Content-Length": str(size), "Content-Type": "application/octet-stream"})
        if done.status != 201:
            raise SystemExit(f"push: upload {digest} lỗi HTTP {done.status}: {done.data[:300]!r}")

    def put_manifest(self, repo: str, tag: str, media_type: str, data: bytes) -> None:
        done = self.request("PUT", f"/v2/{repo}/manifests/{tag}", body=data,
                            headers={"Content-Type": media_type, "Content-Length": str(len(data))})
        if done.status != 201:
            raise SystemExit(f"push: manifest {repo}:{tag} lỗi HTTP {done.status}: {done.data[:300]!r}")


def blob(archive: tarfile.TarFile, digest: str) -> tarfile.TarInfo:
    return archive.getmember(f"blobs/sha256/{digest.split(':', 1)[1]}")


def push_archive(registry: Registry, path: str) -> list[str]:
    pushed = []
    with tarfile.open(path) as archive:
        index = json.load(archive.extractfile("index.json"))
        for entry in index["manifests"]:
            ref = entry.get("annotations", {}).get("io.containerd.image.name")
            if not ref or entry.get("mediaType") not in MANIFEST_TYPES:
                continue
            repo, tag = target_name(ref)
            manifest_bytes = archive.extractfile(blob(archive, entry["digest"])).read()
            manifest = json.loads(manifest_bytes)
            for item in [manifest["config"], *manifest["layers"]]:
                member = blob(archive, item["digest"])
                registry.put_blob(repo, item["digest"], member.size, archive.extractfile(member))
            registry.put_manifest(repo, tag, entry["mediaType"], manifest_bytes)
            pushed.append(f"{registry.address}/{repo}:{tag}")
    if not pushed:
        raise SystemExit(f"push: {path} không có image nào có tên (io.containerd.image.name)")
    return pushed


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print(__doc__.strip(), file=sys.stderr)
        return 2
    registry = Registry(argv[0])
    for path in argv[1:]:
        for ref in push_archive(registry, path):
            print(ref, flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

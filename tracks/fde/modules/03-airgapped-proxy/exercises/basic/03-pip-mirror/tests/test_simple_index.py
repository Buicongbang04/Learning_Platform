import base64
import functools
import hashlib
import html.parser
import http.server
import io
import os
import secrets
import shutil
import subprocess
import sys
import tarfile
import threading
import urllib.parse
import zipfile
from contextlib import contextmanager
from pathlib import Path

import pytest

from testkit import Exercise

ex = Exercise(__file__)
PIP = "pip==25.2"


def b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(hashlib.sha256(data).digest()).rstrip(b"=").decode()


def make_wheel(folder: Path, dist: str, module: str, version: str, requires: str | None = None,
               token: str = "") -> Path:
    stem = f"{dist}-{version}"
    files = {
        f"{module}/__init__.py": f'VERSION = "{version}"\nTOKEN = "{token}"\n'.encode(),
        f"{stem}.dist-info/METADATA": (f"Metadata-Version: 2.1\nName: {dist.replace('_', '-')}\nVersion: {version}\n"
                                       + (f"Requires-Python: {requires}\n" if requires else "")).encode(),
        f"{stem}.dist-info/WHEEL": b"Wheel-Version: 1.0\nGenerator: fde-test\nRoot-Is-Purelib: true\nTag: py3-none-any\n",
    }
    record = "".join(f"{name},sha256={b64(data)},{len(data)}\n" for name, data in files.items())
    record += f"{stem}.dist-info/RECORD,,\n"
    path = folder / f"{stem}-py3-none-any.whl"
    with zipfile.ZipFile(path, "w") as archive:
        for name, data in files.items():
            archive.writestr(name, data)
        archive.writestr(f"{stem}.dist-info/RECORD", record)
    return path


def make_sdist(folder: Path, name: str, version: str) -> Path:
    path = folder / f"{name}-{version}.tar.gz"
    data = f"Metadata-Version: 2.1\nName: {name}\nVersion: {version}\n".encode()
    with tarfile.open(path, "w:gz") as tar:
        info = tarfile.TarInfo(f"{name}-{version}/PKG-INFO")
        info.size = len(data)
        tar.addfile(info, io.BytesIO(data))
    return path


class Links(html.parser.HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.links: list[dict] = []
        self._current: dict | None = None

    def handle_starttag(self, tag, attrs):
        if tag == "a":
            self._current = {**dict(attrs), "text": ""}

    def handle_data(self, data):
        if self._current is not None:
            self._current["text"] += data

    def handle_endtag(self, tag):
        if tag == "a" and self._current is not None:
            self.links.append(self._current)
            self._current = None


def links(page: Path) -> list[dict]:
    parser = Links()
    parser.feed(page.read_text(encoding="utf-8"))
    return parser.links


@pytest.fixture
def dists(tmp_path):
    folder = tmp_path / "dists"
    folder.mkdir()
    token = secrets.token_hex(4)
    made = {
        "acme-report-tools": [
            make_wheel(folder, "Acme.Report_Tools", "acme_report", "1.4.0", ">=3.8"),
            make_wheel(folder, "Acme.Report_Tools", "acme_report", "1.5.0", ">=3.8", token),
            make_wheel(folder, "Acme.Report_Tools", "acme_report", "2.0.0", ">=3.99,<4"),
            make_sdist(folder, "acme_report_tools", "1.5.0"),
        ],
        "law-ocr": [make_wheel(folder, "law_ocr", "law_ocr", "0.3.1")],
    }
    (folder / "README.txt").write_text("không phải gói")
    (folder / "law_ocr-0.4.0-py3-none-any.whl.part").write_bytes(b"dang tai do")
    return folder, made, token


def build(tmp_path, folder):
    out = tmp_path / "mirror"
    result = ex.module("simple_index.py").build_index(folder, out)
    return out, result


def test_normalize():
    normalize = ex.module("simple_index.py").normalize
    assert normalize("Acme.Report_Tools") == "acme-report-tools"
    assert normalize("Friendly-Bard") == normalize("FRIENDLY__BARD") == normalize("friendly.-_bard") == "friendly-bard"


def test_layout_and_return_value(tmp_path, dists):
    folder, made, _ = dists
    out, result = build(tmp_path, folder)
    assert result == {k: sorted(p.name for p in v) for k, v in made.items()}
    root = links(out / "simple" / "index.html")
    assert sorted(a["text"].strip() for a in root) == sorted(made), "Trang gốc phải liệt kê mỗi project một lần"
    for project in made:
        assert (out / "simple" / project / "index.html").is_file(), f"Thiếu simple/{project}/index.html"


def test_links_hashes_and_requires_python(tmp_path, dists):
    folder, made, _ = dists
    out, _ = build(tmp_path, folder)
    for project, files in made.items():
        page = out / "simple" / project / "index.html"
        found = {a["text"].strip(): a for a in links(page)}
        assert sorted(found) == sorted(p.name for p in files), f"{project}: liên kết sai"
        for source in files:
            anchor = found[source.name]
            href, _, fragment = anchor["href"].partition("#")
            assert fragment == f"sha256={hashlib.sha256(source.read_bytes()).hexdigest()}", (
                f"{source.name}: thiếu hoặc sai #sha256=")
            target = (page.parent / urllib.parse.unquote(href)).resolve()
            assert target.is_file() and target.read_bytes() == source.read_bytes(), (
                f"{source.name}: href {href} không trỏ tới bản sao đúng trong thư mục mirror")
            assert out.resolve() in target.parents, f"{source.name}: href trỏ ra ngoài thư mục mirror"
    page = (out / "simple" / "acme-report-tools" / "index.html").read_text(encoding="utf-8")
    assert 'data-requires-python="&gt;=3.99,&lt;4"' in page, "Thiếu data-requires-python (đã escape HTML) cho bản 2.0.0"
    acme = {a["text"].strip(): a for a in links(out / "simple" / "acme-report-tools" / "index.html")}
    assert "data-requires-python" not in acme["acme_report_tools-1.5.0.tar.gz"]


def test_rebuild_is_stable(tmp_path, dists):
    folder, _, _ = dists
    out, _ = build(tmp_path, folder)
    first = {p.relative_to(out): p.read_bytes() for p in out.rglob("*") if p.is_file()}
    out, _ = build(tmp_path, folder)
    second = {p.relative_to(out): p.read_bytes() for p in out.rglob("*") if p.is_file()}
    assert first == second, "Chạy lại trên cùng đầu vào phải cho đúng cùng mirror"


@contextmanager
def serve(out: Path):
    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(out))
    handler.log_message = lambda *args: None
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_address[1]}/simple/"
    finally:
        server.shutdown()
        server.server_close()


def clean_env() -> dict[str, str]:
    return {k: v for k, v in os.environ.items() if not k.startswith(("UV_", "PIP_"))}


def uv_install(tmp_path, index: str, spec: str) -> tuple[subprocess.CompletedProcess, Path]:
    target = tmp_path / f"site-{secrets.token_hex(3)}"
    result = subprocess.run(
        ["uv", "pip", "install", "--python", sys.executable, "--target", str(target), "--no-cache", "--no-config",
         "--index-url", index, spec],
        capture_output=True, text=True, timeout=120, env=clean_env())
    return result, target


def test_uv_installs_from_mirror(tmp_path, dists):
    if not shutil.which("uv"):
        pytest.skip("Chưa có uv trên PATH (xem README gốc của repo)")
    folder, _, token = dists
    out, _ = build(tmp_path, folder)
    with serve(out) as index:
        result, target = uv_install(tmp_path, index, "ACME_report.tools")
    assert result.returncode == 0, f"uv không cài được từ mirror:\n{result.stderr[-1500:]}"
    init = (target / "acme_report" / "__init__.py").read_text()
    assert 'VERSION = "1.5.0"' in init and token in init, (
        "uv phải chọn 1.5.0 (2.0.0 đòi Python >=3.99 không hợp với máy này)")


def require_pip(tmp_path) -> list[str]:
    command = ["uvx", "--from", PIP, "pip"]
    probe = subprocess.run([*command, "--version"], capture_output=True, text=True, timeout=120, env=clean_env())
    if probe.returncode != 0:
        pytest.skip(f"Cần {PIP} (uvx tải một lần, máy đang không có mạng?): {probe.stderr.strip()[-300:]}")
    return command


def test_pip_rejects_tampered_file(tmp_path, dists):
    pip = require_pip(tmp_path)
    folder, _, _ = dists
    out, _ = build(tmp_path, folder)
    page = out / "simple" / "law-ocr" / "index.html"
    href = next(a["href"] for a in links(page) if a["text"].strip() == "law_ocr-0.3.1-py3-none-any.whl")
    victim = (page.parent / urllib.parse.unquote(href.partition("#")[0])).resolve()
    other = tmp_path / "other"
    other.mkdir()
    shutil.copyfile(make_wheel(other, "law_ocr", "law_ocr", "0.3.1", token="da-bi-sua"), victim)
    with serve(out) as index:
        result = subprocess.run(
            [*pip, "install", "--no-cache-dir", "--disable-pip-version-check", "--isolated", "--target",
             str(tmp_path / "pip-site"), "--index-url", index, "law-ocr==0.3.1"],
            capture_output=True, text=True, timeout=120, env=clean_env())
    assert result.returncode != 0 and "HASHES" in result.stderr, (
        "Tệp trong mirror bị thay mà pip vẫn cài: trang index phải mang #sha256= đúng của tệp gốc\n"
        f"{result.stderr[-800:]}")

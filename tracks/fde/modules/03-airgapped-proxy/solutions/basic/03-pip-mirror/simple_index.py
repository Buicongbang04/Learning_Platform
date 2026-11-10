import hashlib
import html
import re
import shutil
import zipfile
from email.parser import HeaderParser
from pathlib import Path

WHEEL = re.compile(r"^(?P<name>[A-Za-z0-9](?:[A-Za-z0-9._]*[A-Za-z0-9])?)-(?P<version>[^-]+)(?:-\d[^-]*)?-[^-]+-[^-]+-[^-]+\.whl$")
SDIST = re.compile(r"^(?P<name>[A-Za-z0-9](?:[A-Za-z0-9._-]*[A-Za-z0-9])?)-(?P<version>\d[^-]*)\.tar\.gz$")


def normalize(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _requires_python(path: Path) -> str | None:
    with zipfile.ZipFile(path) as archive:
        metadata = [n for n in archive.namelist() if n.count("/") == 1 and n.endswith(".dist-info/METADATA")]
        if len(metadata) != 1:
            raise ValueError(f"{path.name}: cần đúng một .dist-info/METADATA")
        headers = HeaderParser().parsestr(archive.read(metadata[0]).decode("utf-8"))
    return headers.get("Requires-Python")


def _page(title: str, links: list[str]) -> str:
    body = "\n".join(f"    {link}<br/>" for link in links)
    return (f"<!DOCTYPE html>\n<html>\n  <head><meta name=\"pypi:repository-version\" content=\"1.0\">"
            f"<title>{html.escape(title)}</title></head>\n  <body>\n{body}\n  </body>\n</html>\n")


def build_index(dist_dir: Path, out_dir: Path) -> dict[str, list[str]]:
    dist_dir, out_dir = Path(dist_dir), Path(out_dir)
    projects: dict[str, list[tuple[str, str, str | None]]] = {}
    files_dir = out_dir / "files"
    files_dir.mkdir(parents=True, exist_ok=True)
    for path in sorted(p for p in dist_dir.iterdir() if p.is_file()):
        match = WHEEL.match(path.name) or SDIST.match(path.name)
        if not match:
            continue
        requires = _requires_python(path) if path.name.endswith(".whl") else None
        target = files_dir / path.name
        if not target.exists() or _sha256(target) != _sha256(path):
            shutil.copy2(path, target)
        projects.setdefault(normalize(match["name"]), []).append((path.name, _sha256(target), requires))

    simple = out_dir / "simple"
    simple.mkdir(parents=True, exist_ok=True)
    for project, entries in sorted(projects.items()):
        links = []
        for filename, digest, requires in sorted(entries):
            attr = f' data-requires-python="{html.escape(requires, quote=True)}"' if requires else ""
            href = f"../../files/{html.escape(filename)}#sha256={digest}"
            links.append(f'<a href="{href}"{attr}>{html.escape(filename)}</a>')
        (simple / project).mkdir(exist_ok=True)
        (simple / project / "index.html").write_text(_page(f"Links for {project}", links), encoding="utf-8")
    root = [f'<a href="{project}/">{project}</a>' for project in sorted(projects)]
    (simple / "index.html").write_text(_page("Simple index", root), encoding="utf-8")
    return {project: sorted(e[0] for e in entries) for project, entries in sorted(projects.items())}

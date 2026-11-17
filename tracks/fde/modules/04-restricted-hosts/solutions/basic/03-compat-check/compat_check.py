import json
import re
import sys
from pathlib import Path

import yaml

PYTHON = re.compile(r"^Python (\d+)\.(\d+)(?:\.(\d+))?", re.M)


def version(text: str) -> tuple[int, ...]:
    return tuple(int(part) for part in re.findall(r"\d+", text))


def matches(version_id: str, entry: str) -> bool:
    entry = str(entry)
    return version_id == entry or version_id.startswith(entry + ".")


def read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except FileNotFoundError:
        return ""


def os_release(text: str) -> dict[str, str]:
    fields = {}
    for line in text.splitlines():
        key, sep, value = line.strip().partition("=")
        if sep and key and not key.startswith("#"):
            fields[key] = value.strip().strip("\"'")
    return fields


def glibc(text: str) -> str | None:
    for line in text.splitlines():
        if line.startswith("ldd "):
            token = line.split()[-1]
            return token if re.fullmatch(r"\d+(\.\d+)+", token) else None
    return None


def python3(text: str) -> str | None:
    match = PYTHON.search(text)
    return match.group(0).split()[1] if match else None


def check_host(host_dir: Path, requirements: dict) -> list[dict]:
    """Đọc ldd.txt, python3.txt, os-release trong host_dir; trả danh sách vấn đề {"code", "found"} so với requirements."""
    host_dir = Path(host_dir)
    issues = []
    found_glibc = glibc(read(host_dir / "ldd.txt"))
    need_glibc = str(requirements["glibc_min"])
    if found_glibc is None or version(found_glibc) < version(need_glibc):
        issues.append({"code": "glibc_too_old", "found": found_glibc, "required": f">= {need_glibc}"})

    found_python = python3(read(host_dir / "python3.txt"))
    need_min = str(requirements["python_min"])
    need_max = requirements.get("python_max")
    if found_python is None:
        issues.append({"code": "python_missing", "found": None, "required": f">= {need_min}"})
    else:
        minor = version(found_python)[:2]
        if minor < version(need_min):
            issues.append({"code": "python_too_old", "found": found_python, "required": f">= {need_min}"})
        if need_max and minor > version(str(need_max)):
            issues.append({"code": "python_too_new", "found": found_python, "required": f"<= {need_max}"})

    release = os_release(read(host_dir / "os-release"))
    os_id, version_id = release.get("ID", ""), release.get("VERSION_ID", "")
    supported = (requirements.get("os_supported") or {}).get(os_id) or []
    if not any(matches(version_id, entry) for entry in supported):
        listed = ", ".join(f"{k} {'/'.join(map(str, v))}" for k, v in (requirements.get("os_supported") or {}).items())
        issues.append({"code": "os_unsupported", "found": f"{os_id} {version_id}", "required": listed})

    table = ((requirements.get("os_eol") or {}).get(os_id)) or {}
    end = next((str(day) for entry, day in table.items() if matches(version_id, str(entry))), None)
    end = end or release.get("SUPPORT_END") or None
    as_of = str(requirements["as_of"])
    if end and end <= as_of:
        issues.append({"code": "os_eol", "found": end, "required": f"còn hỗ trợ sau {as_of}"})
    return issues


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print("Cách dùng: python compat_check.py <requirements.yaml> <thư mục máy>...", file=sys.stderr)
        return 2
    requirements = yaml.safe_load(Path(argv[0]).read_text(encoding="utf-8"))
    report = {Path(host).name: check_host(Path(host), requirements) for host in argv[1:]}
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 1 if any(report.values()) else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

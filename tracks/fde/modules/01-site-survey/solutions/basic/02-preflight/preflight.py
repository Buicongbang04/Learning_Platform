import json
import re
import sys
from pathlib import Path

import yaml

MEM_GRACE = 0.9


def version_key(text: str) -> tuple[int, ...]:
    return tuple(int(part) for part in re.findall(r"\d+", str(text)))


def runtime_names(specs: list[str]) -> list[str]:
    return [re.split(r"[<>=!~]", spec, maxsplit=1)[0].strip() for spec in specs]


def finding(check: str, severity: str, detail: str) -> dict:
    return {"check": check, "severity": severity, "detail": detail}


def check_os(survey: dict, req: dict) -> list[dict]:
    supported = {item["id"]: str(item["min"]) for item in req["os"]}
    os_id, version = survey["os_id"], str(survey["os_version"])
    if os_id not in supported:
        names = ", ".join(f"{k} >= {v}" for k, v in supported.items())
        return [finding("os", "blocker", f"{os_id} {version} không nằm trong danh sách hỗ trợ ({names})")]
    if version_key(version) < version_key(supported[os_id]):
        return [finding("os", "blocker", f"{os_id} {version} cũ hơn bản tối thiểu {supported[os_id]}")]
    return []


def check_capacity(survey: dict, req: dict) -> list[dict]:
    out = []
    if survey["cpus"] < req["min_cpus"]:
        out.append(finding("cpus", "blocker", f"{survey['cpus']} CPU, cần tối thiểu {req['min_cpus']}"))
    mem, need = survey["mem_mb"], req["min_mem_mb"]
    if mem < MEM_GRACE * need:
        out.append(finding("mem", "blocker", f"MemTotal {mem} MB, cần tối thiểu {need} MB"))
    elif mem < need:
        out.append(finding("mem", "warning",
                           f"MemTotal {mem} MB, dưới {need} MB nhưng trong 10%: máy {need // 1024} GB danh nghĩa "
                           f"thường báo MemTotal thấp hơn; xác nhận RAM cấp cho VM với IT"))
    disk, need_disk = survey["disk_free_gb_max"], req["min_disk_free_gb"]
    if disk < need_disk:
        out.append(finding("disk", "blocker", f"Còn trống {disk} GiB ở /, cần tối thiểu {need_disk} GiB"))
    return out


def check_runtime(survey: dict, req: dict) -> list[dict]:
    allowed = runtime_names(req["runtime"])
    runtime = survey["runtime"]
    if runtime is None:
        return [finding("runtime", "blocker", f"Không có container runtime; sản phẩm cần một trong {req['runtime']}")]
    if runtime not in allowed:
        return [finding("runtime", "blocker", f"Runtime {runtime} không được hỗ trợ; cần một trong {req['runtime']}")]
    return []


def check_access(survey: dict) -> list[dict]:
    out = []
    if not survey["sudo"] and survey["runtime"] == "docker":
        out.append(finding("sudo", "warning",
                           "Không có sudo mà runtime là Docker: cần IT thêm user vào nhóm docker hoặc chạy hộ phần cài"))
    if survey["selinux"] == "enforcing":
        out.append(finding("selinux", "warning",
                           "SELinux enforcing: volume cần nhãn :Z/:z, không tắt SELinux; thử cài trên lab enforcing trước"))
    if survey["egress"] == "none":
        out.append(finding("egress", "warning", "Không ra internet: chỉ cài bằng bundle offline, mang theo mọi image và model"))
    elif survey["egress"] == "proxy":
        out.append(finding("egress", "warning",
                           f"Ra internet qua proxy {survey['proxy_url']}: cần cấu hình proxy cho runtime và CA nội bộ"))
    return out


def preflight(survey: dict, requirements: dict) -> list[dict]:
    return [
        *check_os(survey, requirements),
        *check_capacity(survey, requirements),
        *check_runtime(survey, requirements),
        *check_access(survey),
    ]


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("Cách dùng: python preflight.py <survey.json> <REQUIREMENTS.yaml>", file=sys.stderr)
        return 2
    survey = json.loads(Path(argv[0]).read_text(encoding="utf-8"))
    requirements = yaml.safe_load(Path(argv[1]).read_text(encoding="utf-8"))
    findings = preflight(survey, requirements)
    print(json.dumps(findings, ensure_ascii=False, indent=2))
    return 1 if any(f["severity"] == "blocker" for f in findings) else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

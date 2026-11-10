import json
import sys
from pathlib import Path

CUDA_MIN_DRIVER = {
    "11.0": "450.51.05", "11.1": "455.23", "11.2": "460.27.03", "11.3": "465.19.01", "11.4": "470.42.01",
    "11.5": "495.29.05", "11.6": "510.39.01", "11.7": "515.43.04", "11.8": "520.61.05",
    "12.0": "525.60.13", "12.1": "530.30.02", "12.2": "535.54.03", "12.3": "545.23.06", "12.4": "550.54.14",
    "12.5": "555.42.02", "12.6": "560.28.03", "12.8": "570.26", "12.9": "575.51.03",
    "13.0": "580.65.06", "13.1": "590", "13.2": "595", "13.3": "610", "13.4": "615", "13.5": "620",
}
MAJOR_MIN_DRIVER = {"11": "450.80.02", "12": "525.60.13", "13": "580.65.06"}
MAJOR_MIN_CC = {"11": "3.5", "12": "5.0", "13": "7.5"}
DRIVER_DROPS = (("495", "5.0"), ("590", "7.5"))
TOOLKIT_CDI = "1.12.0"
TOOLKIT_SAFE = "1.19.1"
DOCKER_CDI = "25.0.0"
DOCKER_CDI_DEFAULT = "28.3.0"
ERRORS = {"no_driver", "driver_too_old", "cuda_drops_gpu", "driver_drops_gpu", "no_toolkit", "cdi_unsupported"}


def version(text: str) -> tuple[int, ...]:
    return tuple(int(part) for part in str(text).strip().split("."))


def check(host: dict) -> dict:
    parts = version(host["cuda"])
    minor = f"{parts[0]}.{parts[1]}"
    if minor not in CUDA_MIN_DRIVER:
        raise ValueError(f"CUDA {host['cuda']} không có trong bảng")
    access = host.get("access", "gpus")
    if access not in ("gpus", "cdi"):
        raise ValueError(f"access phải là gpus hoặc cdi, nhận {access!r}")
    major = str(parts[0])
    cc = version(host["compute_capability"])
    driver = host.get("driver")
    toolkit = host.get("toolkit")
    issues = []

    def add(code: str, detail: str) -> None:
        issues.append({"code": code, "severity": "error" if code in ERRORS else "warning", "detail": detail})

    if driver is None:
        add("no_driver", "máy không có driver NVIDIA chạy được")
    else:
        exact = version(driver) >= version(CUDA_MIN_DRIVER[minor])
        if not exact and version(driver) < version(MAJOR_MIN_DRIVER[major]):
            add("driver_too_old", f"CUDA {minor} cần driver ≥ {CUDA_MIN_DRIVER[minor]} (tối thiểu ≥ "
                                  f"{MAJOR_MIN_DRIVER[major]} nhờ minor version compatibility), máy có {driver}")
        elif not exact:
            add("minor_version_compat", f"CUDA {minor} chuẩn cần ≥ {CUDA_MIN_DRIVER[minor]}; {driver} chạy được "
                                        "nhờ minor version compatibility, không JIT được PTX")
        for branch, lowest in DRIVER_DROPS:
            if version(driver) >= version(branch) and cc < version(lowest):
                add("driver_drops_gpu", f"driver ≥ {branch} không hỗ trợ GPU compute capability < {lowest}")
                break
    if cc < version(MAJOR_MIN_CC[major]):
        add("cuda_drops_gpu", f"CUDA {major}.x cần compute capability ≥ {MAJOR_MIN_CC[major]}")
    if toolkit is None:
        add("no_toolkit", "chưa có NVIDIA Container Toolkit")
    else:
        if access == "cdi":
            docker = host.get("docker")
            if version(toolkit) < version(TOOLKIT_CDI) or docker is None or version(docker) < version(DOCKER_CDI):
                add("cdi_unsupported", f"CDI cần toolkit ≥ {TOOLKIT_CDI} và Docker ≥ {DOCKER_CDI}")
            elif version(docker) < version(DOCKER_CDI_DEFAULT):
                add("cdi_needs_daemon_config", f"Docker < {DOCKER_CDI_DEFAULT} cần bật features.cdi trong daemon.json")
        if version(toolkit) < version(TOOLKIT_SAFE):
            add("toolkit_cve", f"toolkit < {TOOLKIT_SAFE} còn lỗ hổng đã công bố")
    return {"compatible": not any(i["severity"] == "error" for i in issues), "issues": issues}


def main(argv: list[str]) -> int:
    if len(argv) != 1:
        print("Cách dùng: python cuda_compat.py <host.json>", file=sys.stderr)
        return 2
    result = check(json.loads(Path(argv[0]).read_text(encoding="utf-8")))
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["compatible"] else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

import json
import sys
from pathlib import Path

import yaml


def preflight(survey: dict, requirements: dict) -> list[dict]:
    """Trả danh sách phát hiện {"check", "severity", "detail"} cho một báo cáo survey so với REQUIREMENTS.yaml."""
    raise NotImplementedError("TODO: os, cpus, mem, disk, runtime, sudo, selinux, egress, gpu")


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("Cách dùng: python preflight.py <survey.json> <REQUIREMENTS.yaml>", file=sys.stderr)
        return 2
    survey = json.loads(Path(argv[0]).read_text(encoding="utf-8"))
    requirements = yaml.safe_load(Path(argv[1]).read_text(encoding="utf-8"))
    raise NotImplementedError("TODO: in JSON danh sách phát hiện ra stdout, trả mã thoát theo quy tắc trong README")


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

import sys
from pathlib import Path

import yaml

WINDOWS = ("5m", "30m", "1h", "2h", "6h", "1d", "3d")
ALERTS = (
    ("page", 14.4, "1h", "5m"),
    ("page", 6.0, "6h", "30m"),
    ("ticket", 3.0, "1d", "2h"),
    ("ticket", 1.0, "3d", "6h"),
)
RUNBOOK = "https://runbooks.olist.test/slo/{name}"
PLACEHOLDER = "{{window}}"


def load_spec(path: Path) -> dict:
    # TODO: đọc YAML và kiểm từng SLO như đề bài; sai thì ValueError
    raise NotImplementedError


def budget(slo: dict) -> float:
    # TODO: phần được phép xấu, ví dụ objective 99.5 cho 0.005
    raise NotImplementedError


def recording_rules(slo: dict) -> list[dict]:
    # TODO: mỗi cửa sổ trong WINDOWS một recording rule slo:sli_error:ratio_rate<cửa sổ>, nhãn slo
    raise NotImplementedError


def alert_rules(slo: dict) -> list[dict]:
    # TODO: mỗi dòng của ALERTS một alert ErrorBudgetBurn, điều kiện cửa sổ dài AND cửa sổ ngắn
    raise NotImplementedError


def generate(spec: dict) -> dict:
    # TODO: tệp rule Prometheus, mỗi SLO một group slo-<tên>
    raise NotImplementedError


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("Cách dùng: python slogen.py slo.yaml > rules.yml", file=sys.stderr)
        return 2
    sys.stdout.write(yaml.safe_dump(generate(load_spec(Path(argv[1]))), sort_keys=False, allow_unicode=True))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))

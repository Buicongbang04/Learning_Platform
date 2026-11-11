import re
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
NAME = re.compile(r"[a-z0-9]([-a-z0-9]{0,40}[a-z0-9])?")
PLACEHOLDER = "{{window}}"


def load_spec(path: Path) -> dict:
    spec = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    if not isinstance(spec, dict) or not isinstance(spec.get("slos"), list) or not spec["slos"]:
        raise ValueError("Tệp SLO cần khoá slos là danh sách không rỗng")
    if not isinstance(spec.get("service"), str) or not NAME.fullmatch(spec["service"]):
        raise ValueError("service phải là tên chữ thường, số, '-'")
    seen = set()
    for slo in spec["slos"]:
        name = slo.get("name")
        if not isinstance(name, str) or not NAME.fullmatch(name) or name in seen:
            raise ValueError(f"Tên SLO {name!r} sai dạng hoặc trùng")
        seen.add(name)
        objective = slo.get("objective")
        if isinstance(objective, bool) or not isinstance(objective, (int, float)) or not 0 < objective < 100:
            raise ValueError(f"{name}: objective là phần trăm trong (0, 100)")
        if slo.get("window") != "30d":
            raise ValueError(f"{name}: window chỉ nhận 30d")
        for key in ("errors", "total"):
            query = slo.get(key)
            if not isinstance(query, str) or PLACEHOLDER not in query:
                raise ValueError(f"{name}: {key} phải là PromQL có {PLACEHOLDER}")
    return spec


def budget(slo: dict) -> float:
    return round(1 - slo["objective"] / 100, 10)


def record_name(window: str) -> str:
    return f"slo:sli_error:ratio_rate{window}"


def recording_rules(slo: dict) -> list[dict]:
    return [{"record": record_name(w),
             "expr": f"({slo['errors'].replace(PLACEHOLDER, w)}) / ({slo['total'].replace(PLACEHOLDER, w)})",
             "labels": {"slo": slo["name"]}} for w in WINDOWS]


def alert_rules(slo: dict) -> list[dict]:
    rules = []
    for severity, factor, long, short in ALERTS:
        threshold = f"({factor:g} * {budget(slo):g})"
        selector = f'{{slo="{slo["name"]}"}}'
        rules.append({
            "alert": "ErrorBudgetBurn",
            "expr": f"{record_name(long)}{selector} > {threshold} and {record_name(short)}{selector} > {threshold}",
            "labels": {"severity": severity, "long_window": long},
            "annotations": {
                "summary": f"SLO {slo['name']} tiêu error budget nhanh gấp {factor:g} lần ({long} và {short})",
                "runbook_url": RUNBOOK.format(name=slo["name"]),
            },
        })
    return rules


def generate(spec: dict) -> dict:
    return {"groups": [{"name": f"slo-{slo['name']}", "rules": recording_rules(slo) + alert_rules(slo)} for slo in spec["slos"]]}


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("Cách dùng: python slogen.py slo.yaml > rules.yml", file=sys.stderr)
        return 2
    sys.stdout.write(yaml.safe_dump(generate(load_spec(Path(argv[1]))), sort_keys=False, allow_unicode=True))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))

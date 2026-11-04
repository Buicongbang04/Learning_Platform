"""`python -m eta.platform sign|gate|cost`: lệnh của nền tảng cho đội onboard model."""

import argparse
import json
import sys
from pathlib import Path

import yaml


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m eta.platform")
    sub = parser.add_subparsers(dest="command", required=True)
    sign = sub.add_parser("sign", help="ký cả thư mục model bằng khoá riêng EC")
    sign.add_argument("model_dir", type=Path)
    sign.add_argument("--key", type=Path, required=True)
    sign.add_argument("--out", type=Path, required=True)
    gate = sub.add_parser("gate", help="cổng deploy: allowlist, modelscan (Docker), chữ ký, tag")
    gate.add_argument("model_dir", type=Path)
    gate.add_argument("--signature", type=Path, required=True)
    gate.add_argument("--public-key", type=Path, required=True)
    cost = sub.add_parser("cost", help="báo cáo chi phí theo model")
    cost.add_argument("usage", type=Path)
    cost.add_argument("config", type=Path)
    cost.add_argument("--out", type=Path, default=Path("reports"))
    args = parser.parse_args(argv)
    if args.command == "sign":
        from eta.platform.signing import sign as do_sign

        do_sign(args.model_dir, args.key, args.out)
        print(args.out)
        return 0
    if args.command == "gate":
        from eta.platform.gate import deploy_gate, docker_modelscan

        decision = deploy_gate(args.model_dir, args.signature, args.public_key, docker_modelscan)
        print(json.dumps(decision, ensure_ascii=False))
        return 0 if decision["allowed"] else 1
    from eta.platform.cost import cost_report, load_usage, render_markdown

    report = cost_report(load_usage(args.usage), yaml.safe_load(args.config.read_text(encoding="utf-8")))
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "cost.yaml").write_text(yaml.safe_dump(report, sort_keys=False, allow_unicode=True), encoding="utf-8")
    (args.out / "cost.md").write_text(render_markdown(report), encoding="utf-8")
    print(args.out / "cost.yaml")
    return 0


if __name__ == "__main__":
    sys.exit(main())

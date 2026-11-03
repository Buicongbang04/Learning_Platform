import argparse
import json
import sys
from pathlib import Path

import pandas as pd

from eta.config import Config, load_config
from eta.logs import get_logger, log_event

EXIT_REJECTED = 3
logger = get_logger("eta.cli")


def _sources(config: Config, input_dir: Path | None) -> dict[str, Path]:
    from eta.data import month_path

    if input_dir is None:
        return {m: month_path(config.data_dir, m) for m in config.months}
    return {m: Path(input_dir) / f"{m}.parquet" for m in config.months}


def load_training_frame(config: Config, input_dir: Path | None = None) -> tuple[pd.DataFrame, list[Path]]:
    from eta.data import load_month
    from eta.features import clean

    frames = []
    sources = _sources(config, input_dir)
    for month, path in sources.items():
        raw = pd.read_parquet(path) if input_dir is not None else load_month(path, config.sample_rows, config.seed)
        cleaned = clean(raw, month)
        log_event(logger, "month_loaded", month=month, path=str(path), rows=len(raw), rows_clean=len(cleaned))
        frames.append(cleaned)
    return pd.concat(frames, ignore_index=True), list(sources.values())


def cmd_train(args: argparse.Namespace) -> int:
    import joblib

    from eta.features import build_features
    from eta.lineage import data_version
    from eta.train import evaluate, time_split, train

    config = load_config(args.config)
    df, paths = load_training_frame(config, args.input)
    train_df, test_df = time_split(df)
    X, y = build_features(train_df)
    model = train(X, y, {"random_state": config.seed, **config.model_params})
    metrics = evaluate(model, *build_features(test_df))
    log_event(logger, "trained", rows_train=len(train_df), rows_test=len(test_df), **metrics)
    if args.model_out:
        Path(args.model_out).parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(model, args.model_out)
    if args.metrics_out:
        Path(args.metrics_out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.metrics_out).write_text(json.dumps(metrics, indent=2) + "\n", encoding="utf-8")
    result = dict(metrics)
    if args.register:
        from eta.registry import log_and_register

        result["model_version"] = log_and_register(model, metrics, config, data_version(paths))
    print(json.dumps(result))
    return 0


def cmd_prepare(args: argparse.Namespace) -> int:
    from eta.data import load_month, month_path

    config = load_config(args.config)
    df = load_month(month_path(config.data_dir, args.month), config.sample_rows, config.seed)
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(args.out, index=False)
    log_event(logger, "prepared", month=args.month, rows=len(df), out=str(args.out))
    return 0


def cmd_validate(args: argparse.Namespace) -> int:
    from pandera.errors import SchemaErrors

    from eta.validate import validate_month

    df = pd.read_parquet(args.parquet)
    try:
        validate_month(df, args.month)
    except SchemaErrors as err:
        failures = err.failure_cases[["column", "check"]].drop_duplicates().fillna("<dataframe>")
        for row in failures.itertuples(index=False):
            print(f"FAIL {args.parquet} {row.column}: {row.check}", file=sys.stderr)
        log_event(logger, "validation_failed", month=args.month, path=str(args.parquet), failures=len(failures))
        return 1
    report = {"month": args.month, "path": str(args.parquet), "rows": len(df), "status": "ok"}
    if args.report:
        Path(args.report).parent.mkdir(parents=True, exist_ok=True)
        Path(args.report).write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report))
    return 0


def cmd_promote(args: argparse.Namespace) -> int:
    import mlflow

    from eta.promotion import Policy, promote_if_better

    config = load_config(args.config)
    mlflow.set_tracking_uri(config.mlflow_uri)
    decision = promote_if_better(config.model_name, args.version, Policy())
    print(json.dumps({"version": args.version, "promote": decision.promote, "reasons": decision.reasons}, ensure_ascii=False))
    return 0 if decision.promote else EXIT_REJECTED


def cmd_champion(args: argparse.Namespace) -> int:
    from mlflow import MlflowClient
    from mlflow.exceptions import MlflowException

    from eta.registry import ALIAS

    config = load_config(args.config)
    try:
        version = str(MlflowClient(tracking_uri=config.mlflow_uri).get_model_version_by_alias(config.model_name, ALIAS).version)
    except MlflowException:
        version = None
    ok = version is not None and (args.expect is None or version == str(args.expect))
    print(json.dumps({"model_name": config.model_name, "champion": version, "expect": args.expect, "ok": ok}))
    return 0 if ok else 1


def cmd_experiment(args: argparse.Namespace) -> int:
    from eta.experiments import late_slice, retrain_on

    config = load_config(args.config)
    if args.kind == "late-slice":
        result = late_slice(args.month, args.as_of, config)
    else:
        if not args.train_month:
            raise SystemExit("--train-month bắt buộc với retrain")
        result = retrain_on(args.train_month, [m.strip() for m in args.month.split(",")], args.as_of, config)
    print(json.dumps(result, ensure_ascii=False))
    return 0


def cmd_replay(args: argparse.Namespace) -> int:
    from eta.clock import add_months, months_between
    from eta.flows import batch_score_flow, replay_flow
    from eta.quality import replay_summary

    out = Path(args.out)
    reference = args.reference or add_months(args.start, -1)
    rows = replay_flow(args.start, args.end, str(args.config), str(out))
    batch_score_flow(reference, str(args.config), str(out))
    summary = replay_summary(months_between(args.start, args.end), reference, args.end, load_config(args.config), out)
    summary.to_parquet(out / "summary.parquet", index=False)
    log_event(logger, "replayed", start=args.start, end=args.end, reference=reference, months=len(rows), out=str(out))
    print(summary.to_string(index=False, float_format=lambda v: f"{v:.4f}"))
    return 0


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(prog="eta")
    sub = root.add_subparsers(dest="command", required=True)
    p = sub.add_parser("train", help="train, đánh giá, in metric JSON")
    p.add_argument("--config", type=Path, required=True)
    p.add_argument("--input", type=Path, help="thư mục <month>.parquet đã prepare (bỏ qua bước lấy mẫu)")
    p.add_argument("--model-out", type=Path)
    p.add_argument("--metrics-out", type=Path)
    p.add_argument("--register", action="store_true", help="log run và đăng ký model vào MLflow")
    p.set_defaults(func=cmd_train)
    p = sub.add_parser("prepare", help="lấy mẫu một tháng thô ra parquet")
    p.add_argument("--config", type=Path, required=True)
    p.add_argument("--month", required=True)
    p.add_argument("--out", type=Path, required=True)
    p.set_defaults(func=cmd_prepare)
    p = sub.add_parser("validate", help="kiểm schema một tháng, exit 1 khi vi phạm")
    p.add_argument("parquet", type=Path)
    p.add_argument("--month", required=True)
    p.add_argument("--report", type=Path)
    p.set_defaults(func=cmd_validate)
    p = sub.add_parser("promote", help="so challenger với champion, đặt alias khi qua cổng")
    p.add_argument("--config", type=Path, required=True)
    p.add_argument("--version", required=True)
    p.set_defaults(func=cmd_promote)
    p = sub.add_parser("champion", help="in version đang mang alias champion; --expect: exit 1 khi khác")
    p.add_argument("--config", type=Path, required=True)
    p.add_argument("--expect")
    p.set_defaults(func=cmd_champion)
    p = sub.add_parser("experiment", help="thí nghiệm hỗ trợ quyết định, chỉ dùng nhãn đã công bố tại --as-of")
    p.add_argument("kind", choices=["late-slice", "retrain"])
    p.add_argument("--config", type=Path, required=True)
    p.add_argument("--month", required=True, help="tháng đánh giá (retrain: nhiều tháng cách nhau bằng dấu phẩy)")
    p.add_argument("--as-of", required=True)
    p.add_argument("--train-month", help="retrain: tháng dùng để train lại")
    p.set_defaults(func=cmd_experiment)
    p = sub.add_parser("replay", help="phát lại từng tháng, ghi summary.parquet (drift, chất lượng khi có nhãn)")
    p.add_argument("--config", type=Path, default=Path("params.yaml"))
    p.add_argument("--start", required=True)
    p.add_argument("--end", required=True)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--reference", help="tháng tham chiếu cho drift (mặc định: tháng trước start, tháng train)")
    p.set_defaults(func=cmd_replay)
    return root


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())

"""Helper chung của test capstone ETA: thư mục được chấm, import `eta` an toàn, dữ liệu giả, dữ liệu tháng lạ của M13,
dữ liệu sự cố dựng sẵn của M18, khoá ký và pickle độc hại đã vô hại hoá của M17.

Chạy như script để dựng dữ liệu: `uv run python tracks/mlops/capstone/project/tests/etakit.py assessment` (M13) hoặc
`... etakit.py incident` (M18).
"""

import importlib
import importlib.util
import sys
from pathlib import Path

if str(Path(__file__).resolve().parents[5]) not in sys.path:
    sys.path.append(str(Path(__file__).resolve().parents[5]))

import numpy as np
import pandas as pd
import pytest

from testkit import use_solution

CAPSTONE = Path(__file__).resolve().parents[2]
STRANGE_MONTH_SCRIPT = CAPSTONE / "solutions" / "assessment" / "strange_month.py"
SENIOR_INCIDENT_SCRIPT = CAPSTONE / "solutions" / "assessment" / "senior_incident.py"
PROJECT = CAPSTONE / "solutions" / "project" if use_solution() else CAPSTONE / "project"
COLUMNS = ["tpep_pickup_datetime", "tpep_dropoff_datetime", "PULocationID", "DOLocationID", "trip_distance"]


def need(module: str, *names: str):
    src = str(PROJECT / "src")
    if src not in sys.path:
        sys.path.insert(0, src)
    try:
        package = importlib.import_module("eta")
        where = Path(list(package.__path__)[0]).resolve()
        if where != (PROJECT / "src" / "eta").resolve():
            pytest.fail(f"Đang import eta từ {where}, không phải từ {PROJECT / 'src'}", pytrace=False)
        mod = importlib.import_module(f"eta.{module}")
    except ModuleNotFoundError as err:
        pytest.fail(f"Chưa import được eta.{module} từ {PROJECT.relative_to(CAPSTONE.parents[2])}/src: {err}", pytrace=False)
    missing = [n for n in names if not hasattr(mod, n)]
    if missing:
        pytest.fail(f"eta.{module} chưa có {missing}", pytrace=False)
    return mod


def require_file(*parts: str) -> Path:
    path = PROJECT.joinpath(*parts)
    if not path.is_file():
        pytest.fail(f"Chưa có tệp {path.relative_to(CAPSTONE.parents[2])}", pytrace=False)
    return path


def synthetic_month(n: int, month: str = "2019-01", seed: int = 0, extra_columns: bool = True) -> pd.DataFrame:
    """Chuyến giả cho test: thời lượng phụ thuộc khoảng cách, giờ cao điểm và cặp zone, mọi dòng đều sạch."""
    rng = np.random.default_rng(seed)
    start = pd.Timestamp(f"{month}-01")
    days = (start + pd.offsets.MonthBegin(1) - start).days
    pickup = start + pd.to_timedelta(np.sort(rng.integers(0, days * 86_400 - 4 * 3600, n)), unit="s")
    pu = rng.choice([132, 138, 161, 162, 230, 236, 237, 48, 79, 186], n)
    do = rng.choice([132, 138, 161, 162, 230, 236, 237, 48, 79, 170], n)
    distance = np.round(rng.gamma(2.0, 1.5, n) + 0.2, 2)
    rush = np.isin(pickup.hour, [8, 9, 17, 18]).astype(float)
    airport = (np.isin(pu, [132, 138]) | np.isin(do, [132, 138])).astype(float)
    duration = 120 + distance * 160 * (1 + 0.4 * rush) + 600 * airport + rng.normal(0, 40, n)
    duration = np.clip(duration, 90, 9000).round()
    frame = pd.DataFrame(
        {
            "VendorID": rng.integers(1, 3, n),
            "tpep_pickup_datetime": pickup.astype("datetime64[us]"),
            "tpep_dropoff_datetime": (pickup + pd.to_timedelta(duration, unit="s")).astype("datetime64[us]"),
            "passenger_count": rng.integers(1, 5, n).astype(float),
            "trip_distance": distance,
            "PULocationID": pu.astype("int64"),
            "DOLocationID": do.astype("int64"),
            "fare_amount": np.round(2.5 + distance * 2.5, 2),
        }
    )
    return frame if extra_columns else frame[COLUMNS]


PREDICTION_LOG_COLUMNS = ["request_id", "ts", "model_version", "variant", "PULocationID", "DOLocationID",
                          "pickup_datetime", "trip_distance", "eta_s"]


def write_months(raw: Path, months: list[str], n: int = 1_500, seed: int = 0) -> Path:
    """Ghi tệp `yellow_tripdata_<month>.parquet` giả cho từng tháng vào `raw`."""
    raw.mkdir(parents=True, exist_ok=True)
    for i, month in enumerate(months):
        synthetic_month(n, month=month, seed=seed + i).to_parquet(raw / f"yellow_tripdata_{month}.parquet", index=False)
    return raw


def write_config(path: Path, raw: Path, months: list[str], mlflow_uri: str, model_name: str, **extra) -> Path:
    """Tệp params.yaml nhỏ cho flow: mẫu 1 200 dòng, model 20 vòng."""
    import yaml

    params = {"data_dir": str(raw), "months": months, "sample_rows": 1_200, "seed": 0,
              "model_params": {"max_iter": 20}, "mlflow_uri": mlflow_uri, "model_name": model_name, **extra}
    path.write_text(yaml.safe_dump(params, sort_keys=False), encoding="utf-8")
    return path


def local_registry(tmp_path: Path, prefix: str = "eta") -> tuple[str, str]:
    """MLflow SQLite trong `tmp_path` và tên model ngẫu nhiên; experiment cùng tên lưu artifact trong `tmp_path`."""
    import uuid

    import mlflow

    import mlopskit

    uri = mlopskit.mlflow_local(tmp_path)
    name = f"{prefix}-{uuid.uuid4().hex[:8]}"
    mlflow.create_experiment(name, artifact_location=(tmp_path / "artifacts" / name).as_uri())
    return uri, name


def _load_script(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _strange_month():
    return _load_script("eta_assessment_strange_month", STRANGE_MONTH_SCRIPT)


def _senior_incident():
    return _load_script("eta_assessment_senior_incident", SENIOR_INCIDENT_SCRIPT)


def assessment_month() -> str:
    """Tháng lạ của M13."""
    return _strange_month().MONTH


def injected_causes() -> set[str]:
    """Nhãn `cause` của các lỗi cài trong tháng lạ (test M13 dùng; người học đừng in ra)."""
    return set(_strange_month().FAULTS)


def assessment_data(dest: Path) -> Path:
    """Dựng thư mục dữ liệu M13 trong `dest`: symlink tới các tháng thật xung quanh và tệp tháng lạ sinh từ dữ liệu thật."""
    import mlopskit

    module = _strange_month()
    dest = Path(dest)
    dest.mkdir(parents=True, exist_ok=True)
    for month, dataset in module.CONTEXT.items():
        link = dest / f"yellow_tripdata_{month}.parquet"
        target = mlopskit.real_month(dataset, month)
        if link.is_symlink() or link.exists():
            link.unlink()
        link.symlink_to(target)
    module.build(mlopskit.real_month(*module.SOURCE), dest / f"yellow_tripdata_{module.MONTH}.parquet")
    return dest


def incident_facts() -> dict:
    """Phần đáp án M18 không tính được từ dữ liệu (test M18 dùng; người học đừng in ra)."""
    module = _senior_incident()
    return {"date": module.DAY, "markets": list(module.MARKETS.values()), "causes": set(module.CAUSES),
            "trigger": module.TRIGGER, "decision": module.DECISION, "detected_at": module.DETECTED,
            "roles": dict(module.ROLES), "people": list(module.PEOPLE)}


def incident_data(dest: Path) -> Path:
    """Dựng thư mục dữ liệu sự cố M18 trong `dest` từ ngày thật 2019-11-14 và tháng tham chiếu 2019-10 của `nyc-tlc`."""
    import hashlib

    import mlopskit

    module = _senior_incident()
    source = mlopskit.real_month(*module.SOURCE)
    reference = mlopskit.real_month(*module.REFERENCE)
    lookup = source.parent / module.LOOKUP
    if not lookup.is_file():
        pytest.skip(f"Chưa có {module.LOOKUP}. Chạy: uv run python data/download_dataset.py {module.SOURCE[0]}")
    if hashlib.sha256(lookup.read_bytes()).hexdigest() != module.LOOKUP_SHA256:
        pytest.fail(f"sha256 của {lookup} không khớp: xoá tệp và tải lại bộ {module.SOURCE[0]}", pytrace=False)
    return module.build(source, reference, lookup, Path(dest))


def ec_keypair(folder: Path, name: str) -> tuple[Path, Path]:
    """M17: cặp khoá EC P-256 sinh offline trong `folder`, khoá riêng quyền 0600; trả `(private.pem, public.pub)`."""
    import os

    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric import ec

    folder.mkdir(parents=True, exist_ok=True)
    key = ec.generate_private_key(ec.SECP256R1())
    private, public = folder / f"{name}.pem", folder / f"{name}.pub"
    data = key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption())
    fd = os.open(private, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "wb") as handle:
        handle.write(data)
    public.write_bytes(key.public_key().public_bytes(serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo))
    return private, public


class _ExecMarker:
    """Payload vô hại: nạp vào là `exec` một dòng chỉ ghi chữ `pwned` vào tệp đánh dấu trong thư mục tạm của test."""

    def __init__(self, marker: Path):
        self.code = f"open({str(marker)!r}, 'w').write('pwned')"

    def __reduce__(self):
        import builtins

        return (builtins.exec, (self.code,))


class _PathMarker:
    """Payload vô hại qua `pathlib.Path.write_text` (không có trong danh sách chặn của modelscan 0.8.8)."""

    def __init__(self, marker: Path):
        self.marker = Path(marker)

    def __reduce__(self):
        return (Path.write_text, (self.marker, "pwned"))


def marker_pickle(marker: Path) -> bytes:
    """M17: pickle trông như checkpoint, modelscan bắt được (CRITICAL). Test không bao giờ nạp nó."""
    import pickle

    return pickle.dumps({"coef": [0.1, 0.2], "intercept": 1.5, "hook": _ExecMarker(marker)}, protocol=4)


def stealth_pickle(marker: Path) -> bytes:
    """M17: pickle modelscan không bắt; chỉ allowlist định dạng theo nội dung chặn được. Test không bao giờ nạp nó."""
    import pickle

    return pickle.dumps({"coef": [0.1, 0.2], "hook": _PathMarker(marker)}, protocol=4)


def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(prog="etakit", description="Tiện ích dữ liệu của capstone ETA")
    sub = parser.add_subparsers(dest="command", required=True)
    build = sub.add_parser("assessment", help="M13: dựng thư mục dữ liệu có tháng lạ")
    build.add_argument("--out", type=Path, default=CAPSTONE / "project" / "data" / "assessment")
    incident = sub.add_parser("incident", help="M18: dựng thư mục dữ liệu sự cố dựng sẵn")
    incident.add_argument("--out", type=Path, default=CAPSTONE / "project" / "data" / "incident")
    args = parser.parse_args(argv)
    try:
        out = assessment_data(args.out) if args.command == "assessment" else incident_data(args.out)
    except BaseException as err:
        if type(err).__name__ in ("Skipped", "Failed"):
            print(getattr(err, "msg", str(err)), file=sys.stderr)
            return 1
        raise
    for path in sorted(out.glob("yellow_tripdata_*.parquet") if args.command == "assessment" else out.iterdir()):
        print(path)
    return 0


if __name__ == "__main__":
    sys.exit(main())

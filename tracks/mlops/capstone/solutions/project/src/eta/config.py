import json
import os
import re
from dataclasses import dataclass, field, fields
from pathlib import Path

import yaml

MONTH = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")


@dataclass
class Config:
    data_dir: Path
    months: list[str]
    sample_rows: int | None = 200_000
    seed: int = 0
    model_params: dict = field(default_factory=dict)
    mlflow_uri: str = "http://127.0.0.1:25000"
    model_name: str = "eta"


ENV_PARSERS = {
    "data_dir": lambda v: Path(v),
    "months": lambda v: [m.strip() for m in v.split(",") if m.strip()],
    "sample_rows": lambda v: None if v.lower() in ("", "none", "null") else int(v),
    "seed": int,
    "model_params": json.loads,
    "mlflow_uri": str,
    "model_name": str,
}


def load_config(path: Path) -> Config:
    path = Path(path)
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    known = {f.name for f in fields(Config)}
    unknown = sorted(set(raw) - known)
    if unknown:
        raise ValueError(f"{path}: khoá không hợp lệ {unknown}")
    if "data_dir" in raw:
        data_dir = Path(raw["data_dir"])
        raw["data_dir"] = data_dir if data_dir.is_absolute() else (path.parent / data_dir).resolve()
    for name, parse in ENV_PARSERS.items():
        value = os.environ.get(f"ETA_{name.upper()}")
        if value is not None:
            raw[name] = parse(value)
    missing = [name for name in ("data_dir", "months") if name not in raw]
    if missing:
        raise ValueError(f"{path}: thiếu {missing}")
    config = Config(**raw)
    config.data_dir = Path(config.data_dir)
    config.months = [str(m) for m in config.months]
    bad = [m for m in config.months if not MONTH.match(m)]
    if bad or not config.months:
        raise ValueError(f"months phải là danh sách YYYY-MM không rỗng, có {config.months}")
    config.model_params = dict(config.model_params or {})
    return config

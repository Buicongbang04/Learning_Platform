import os
from dataclasses import dataclass, fields, replace
from pathlib import Path
from typing import Mapping

import yaml

ENV_PREFIX = "ETA_"


@dataclass(frozen=True)
class Settings:
    data_path: Path
    model_dir: Path = Path("models")
    seed: int = 0
    max_iter: int = 100
    log_level: str = "INFO"


PATH_FIELDS = {"data_path", "model_dir"}
INT_FIELDS = {"seed", "max_iter"}


def _coerce(name: str, value, base: Path):
    try:
        if name in INT_FIELDS:
            return int(value)
        if name in PATH_FIELDS:
            path = Path(str(value))
            return path if path.is_absolute() else base / path
        return str(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name}: giá trị {value!r} không hợp lệ") from exc


def load_settings(yaml_path: Path | None = None, env: Mapping[str, str] | None = None) -> Settings:
    env = os.environ if env is None else env
    known = {f.name for f in fields(Settings)}
    values: dict = {}
    if yaml_path is not None:
        yaml_path = Path(yaml_path)
        raw = yaml.safe_load(yaml_path.read_text(encoding="utf-8")) or {}
        unknown = sorted(set(raw) - known)
        if unknown:
            raise ValueError(f"Khoá lạ trong {yaml_path.name}: {unknown}")
        for name, value in raw.items():
            values[name] = _coerce(name, value, yaml_path.resolve().parent)
    for name in known:
        key = ENV_PREFIX + name.upper()
        if key in env:
            values[name] = _coerce(name, env[key], Path.cwd())
    if "data_path" not in values:
        raise ValueError("Thiếu data_path (đặt trong YAML hoặc ETA_DATA_PATH)")
    settings = Settings(**values)
    model_dir = settings.model_dir if "model_dir" in values else Path.cwd() / settings.model_dir
    return replace(settings, data_path=settings.data_path.resolve(), model_dir=model_dir.resolve())

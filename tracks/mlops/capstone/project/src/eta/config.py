from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Config:
    data_dir: Path
    months: list[str]
    sample_rows: int | None = 200_000
    seed: int = 0
    model_params: dict = field(default_factory=dict)
    mlflow_uri: str = "http://127.0.0.1:25000"
    model_name: str = "eta"


def load_config(path: Path) -> Config:
    raise NotImplementedError("M01: đọc YAML, data_dir tương đối tính từ thư mục tệp config, biến ETA_* ghi đè")

from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

ENV_PREFIX = "ETA_"


@dataclass(frozen=True)
class Settings:
    data_path: Path
    model_dir: Path = Path("models")
    seed: int = 0
    max_iter: int = 100
    log_level: str = "INFO"


def load_settings(yaml_path: Path | None = None, env: Mapping[str, str] | None = None) -> Settings:
    # TODO: giá trị mặc định < tệp YAML < biến môi trường ETA_<TÊN_IN_HOA> (vd. ETA_SEED).
    # - env=None nghĩa là dùng os.environ.
    # - Khoá lạ trong YAML: ValueError nêu tên khoá (bắt lỗi gõ sai).
    # - Số không parse được: ValueError nêu tên trường. Thiếu data_path ở mọi nguồn: ValueError nêu "data_path".
    # - Đường dẫn tương đối trong YAML tính từ thư mục chứa tệp YAML, không từ thư mục đang chạy.
    # - Đường dẫn từ env hoặc mặc định tính từ thư mục đang chạy. Trả Settings với mọi đường dẫn đã resolve().
    raise NotImplementedError

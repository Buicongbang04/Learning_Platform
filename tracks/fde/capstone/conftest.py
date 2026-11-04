"""Thu thập test khi chạy cả thư mục capstone.

`tests/` là bộ chấm. `solutions/project/` là repo tham chiếu đứng riêng (người học tạo repo của mình ngoài repo học); test
riêng của nó (nếu có) chạy trong chính repo đó, nên khi chạy `uv run pytest tracks/fde/capstone` chúng bị bỏ qua. Gọi
thẳng đường dẫn bên trong `solutions/project` thì vẫn chạy.
"""

from pathlib import Path

PROJECT = Path(__file__).resolve().parent / "solutions" / "project"


def pytest_ignore_collect(collection_path: Path, config):
    if collection_path != PROJECT:
        return None
    base = Path(config.invocation_params.dir)
    targets = [(base / str(arg).split("::")[0]).resolve() for arg in config.args]
    if any(target == PROJECT or PROJECT in target.parents for target in targets):
        return None
    return True

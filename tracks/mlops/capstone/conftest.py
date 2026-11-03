"""Thu thập test khi chạy cả thư mục capstone.

`project/tests` là test chấm. `tests_own/` (của bạn và của bản tham chiếu) là test riêng của project, chạy trong job
`test` của CI (M08) với `PYTHONPATH=src`; khi chạy cả thư mục capstone chúng bị bỏ qua, vì chúng import `eta` theo đường
khác và làm sai việc kiểm nguồn import của `etakit.need`. Gọi thẳng đường dẫn `tests_own` thì vẫn chạy.
"""

from pathlib import Path


def pytest_ignore_collect(collection_path: Path, config):
    if collection_path.name != "tests_own":
        return None
    base = Path(config.invocation_params.dir)
    targets = [(base / str(arg).split("::")[0]).resolve() for arg in config.args]
    if any(target == collection_path or collection_path in target.parents for target in targets):
        return None
    return True

from mlflow import MlflowClient


def audit_run(tracking_uri: str, run_id: str) -> list[str]:
    """Trả các mục không đạt, theo thứ tự: commit, data_version, lockfile_hash, seed.

    Rỗng nghĩa là run đủ điều kiện tái lập. Chỉ đọc, không ghi gì vào run.
    """
    # TODO: đọc tags và params của run, áp luật của từng mục trong README
    raise NotImplementedError


def run_of_version(tracking_uri: str, model_name: str, version: int) -> str:
    """run_id của run đã tạo ra version đó; LookupError nêu tên model và version nếu không có."""
    # TODO
    raise NotImplementedError


def audit_model(tracking_uri: str, model_name: str, version: int) -> dict:
    """{"run_id": str, "missing": list[str], "reproducible": bool}."""
    # TODO
    raise NotImplementedError

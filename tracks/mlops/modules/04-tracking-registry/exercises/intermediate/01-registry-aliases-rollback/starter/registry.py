import mlflow
from mlflow import MlflowClient


def register_version(client: MlflowClient, model_name: str, model_uri: str, model_id: str,
                     run_id: str, tags: dict | None = None) -> int:
    """Đăng ký một model version mới, trả số version (int).

    Tạo registered model nếu chưa có (gọi lần hai với cùng tên không được lỗi). Version phải gắn
    `run_id`, `model_id`, tags, và chỉ trả về khi status là READY.
    """
    # TODO
    raise NotImplementedError


def promote(client: MlflowClient, model_name: str, version: int, alias: str = "champion") -> int | None:
    """Đặt `alias` cho `version`. Trả version đang giữ alias trước đó (None nếu chưa có).

    Trên version mới đặt tag `previous_<alias>` = số version cũ (chuỗi), để rollback biết đường lui.
    Không ghi tag khi chưa có version cũ.
    """
    # TODO
    raise NotImplementedError


def rollback(client: MlflowClient, model_name: str, alias: str = "champion") -> int:
    """Đưa `alias` về version được ghi trong tag `previous_<alias>` của version hiện giữ alias.

    Gắn tag `rolled_back` = "true" lên version bị gỡ. Trả version mới của alias.
    Alias chưa tồn tại, hoặc version hiện tại không có đường lui: raise LookupError.
    """
    # TODO
    raise NotImplementedError


def load_by_alias(client: MlflowClient, model_name: str, alias: str = "champion"):
    """Trả (model_pyfunc, version).

    Phân giải alias ra số version một lần, rồi nạp đúng `models:/<tên>/<version>` đó, để version
    trả về luôn là version đã nạp kể cả khi alias bị đổi giữa hai bước.
    """
    # TODO
    raise NotImplementedError

"""Cổng đăng ký model: quy ước tên, tag bắt buộc, model card, quyền theo đội."""

from mlflow import MlflowClient

TEAMS = {"eta", "pricing", "fraud", "search", "ads"}
PLATFORM_TEAM = "platform"
REQUIRED_TAGS = ("owner", "team", "cost_center")
CARD_SECTIONS = ("Intended use", "Training data", "Metrics", "Limitations")


def check_request(request: dict) -> list[str]:
    """Trả danh sách mã vi phạm đã sắp xếp; rỗng nghĩa là hợp lệ."""
    # TODO 1: tên model theo quy ước <team>-<tên>, tối đa 64 ký tự
    # TODO 2: tag bắt buộc: thiếu hay sai định dạng; tag team khớp tiền tố tên
    # TODO 3: người gửi chỉ đăng ký trong không gian tên của đội mình (trừ đội platform)
    # TODO 4: model card có đủ các phần trong CARD_SECTIONS
    return []


def register_if_allowed(client: MlflowClient, request: dict, source: str) -> tuple[str | None, list[str]]:
    """Đăng ký version mới khi hợp lệ; ngược lại không ghi gì vào registry."""
    # TODO 5
    raise NotImplementedError


def audit_registry(client: MlflowClient) -> dict[str, list[str]]:
    """Quét mọi version đã có trên registry, trả {"<tên>/<version>": [mã vi phạm]} cho version vi phạm."""
    # TODO 6
    return {}

import re

ORDER = [
    "sagemaker-endpoint", "vertex-endpoint", "azureml-endpoint",
    "sagemaker-endpoint-config", "sagemaker-model", "vertex-model",
    "sagemaker-notebook", "nat-gateway",
    "s3-bucket", "gcs-bucket", "azure-resource-group",
]
SAFE_NAME = re.compile(r"[a-z0-9][a-z0-9_-]{0,62}")


def plan_teardown(inventory: list[dict], lab: str) -> list[dict]:
    """Danh sách bước dọn có thứ tự: {"resource", "type", "command"}.

    Luật về tag, thứ tự, tên an toàn và lệnh cho từng loại nằm trong README.
    """
    # TODO
    raise NotImplementedError


def render_script(steps: list[dict]) -> str:
    """Nội dung script bash chạy các bước; mặc định chỉ in, chạy thật khi DRY_RUN=0."""
    # TODO
    raise NotImplementedError


def leftover_warnings(inventory: list[dict], lab: str) -> list[dict]:
    """Cảnh báo {"resource", "why"} cho thứ có thể còn tính tiền sau khi dọn."""
    # TODO
    raise NotImplementedError

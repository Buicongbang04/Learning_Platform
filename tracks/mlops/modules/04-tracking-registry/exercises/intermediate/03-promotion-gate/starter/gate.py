import json

from mlflow import MlflowClient


def collect_metrics(client: MlflowClient, model_name: str, version: int) -> dict:
    """Đọc số đo của một model version từ run đã sinh ra nó.

    Trả {"mae": float, "latency_p95_ms": float, "slices": {tên: {"mae": float, "n": int}}}.
    Metric của run: `mae`, `latency_p95_ms`, và với mỗi slice `mae_slice.<tên>`, `n_slice.<tên>`.
    """
    # TODO
    raise NotImplementedError


def lineage_problems(client: MlflowClient, model_name: str, version: int) -> list[str]:
    """Lý do version không đủ điều kiện về lineage; rỗng nghĩa là đạt.

    Đọc tag của run: `git_dirty == "true"` là một lý do (nêu chữ git_dirty), thiếu tag `data_version`
    hoặc `git_commit` cũng là lý do (nêu tên tag thiếu).
    """
    # TODO
    raise NotImplementedError


def gate_and_promote(client: MlflowClient, model_name: str, challenger_version: int, decide,
                     policy: dict | None = None, alias: str = "champion") -> dict:
    """Chạy cổng promotion cho một version và ghi quyết định vào registry.

    Trả {"promoted": bool, "reasons": list[str], "version": int}. Các bước, theo thứ tự:
    1. challenger_version đang giữ alias: raise ValueError.
    2. champion = version giữ alias (hoặc None). Số đo của cả hai qua collect_metrics.
    3. decision = decide(challenger, champion, policy) (đối tượng có `.promote` và `.reasons`).
       Thêm lineage_problems(challenger) vào reasons; có lý do lineage thì không promote bất kể decision.
    4. Ghi lên challenger các tag: `promotion.decision` ("promoted" hoặc "rejected"), `promotion.reasons`
       (JSON list), `promotion.compared_to` (số version champion dạng chuỗi, hoặc "none").
    5. Chỉ khi promote: đặt alias cho challenger; ghi `previous_<alias>` lên challenger và `superseded_by` lên
       champion cũ (chỉ khi có champion cũ).
    Rejected thì alias không đổi.
    """
    # TODO
    raise NotImplementedError

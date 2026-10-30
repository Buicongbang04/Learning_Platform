"""Kiểm log sự kiện so với tracking plan, chạy trên staging trước khi tính năng ra mắt."""
import pandas as pd

TYPES = {"string", "integer", "number", "boolean", "timestamp", "array"}


def validate_event(event: dict, plan: dict) -> list[str]:
    """Danh sách lỗi (đã sắp xếp) của một sự kiện `{"event": tên, "properties": {...}}` so với `plan`.

    - "unknown_event": tên không có trong plan["events"] (trả về chỉ lỗi này).
    - "missing:<thuộc tính>": thuộc tính required (chung hoặc riêng) thiếu hoặc là None.
    - "type:<thuộc tính>": sai kiểu. string: str; integer: int (không phải bool); number: int hoặc float (không
      phải bool); boolean: bool; timestamp: chuỗi ISO 8601 đọc được bằng datetime.fromisoformat; array: list.
    - "enum:<thuộc tính>": đúng kiểu nhưng giá trị không thuộc enum.
    - "extra:<thuộc tính>": thuộc tính không khai báo trong plan.
    Thuộc tính tuỳ chọn có giá trị None coi như không gửi.
    """
    # TODO
    raise NotImplementedError


def validate_log(events: list[dict], plan: dict) -> pd.DataFrame:
    """Đếm lỗi theo (event, issue): cột event, issue, count; sắp count giảm dần rồi event, issue tăng dần."""
    # TODO
    raise NotImplementedError

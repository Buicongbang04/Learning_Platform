"""raw -> processed: đọc workbook gốc, làm sạch, tính metric, ghi CSV. Chạy lại bao nhiêu lần cũng ra cùng tệp."""

from pathlib import Path

import pandas as pd  # noqa: F401

OUTPUT = "monthly_country_revenue.csv"


def build(raw_path, out_dir, sheet: str = "Year 2010-2011") -> Path:
    """Đọc sheet của workbook raw_path, ghi out_dir/monthly_country_revenue.csv, trả đường dẫn tệp đó.

    Tạo out_dir nếu chưa có. Không ghi gì vào thư mục chứa raw_path. Hai lần chạy liên tiếp cho tệp giống hệt nhau.
    """
    # TODO
    raise NotImplementedError

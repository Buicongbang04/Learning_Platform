"""Tự kiểm một repo dự án portfolio trước khi gửi nhà tuyển dụng (xem README của bài).

    uv run python portfolio_check.py <đường dẫn repo dự án>
"""

import re
import sys
from pathlib import Path

REQUIRED_SECTIONS = {
    "question": ("câu hỏi", "question", "problem", "bối cảnh"),
    "data": ("dữ liệu", "data"),
    "results": ("kết quả", "kết luận", "results", "findings"),
    "limitations": ("giới hạn", "hạn chế", "limitations"),
}
DEPENDENCY_FILES = ("requirements.txt", "pyproject.toml", "environment.yml", "environment.yaml")
SKIP_DIRS = {".git", ".venv", "__pycache__", ".ipynb_checkpoints"}
TEXT_SUFFIXES = {".py", ".ipynb", ".sql", ".md", ".txt", ".yml", ".yaml", ".toml", ".json", ".cfg", ".ini"}
SECRET_PATTERNS = [
    re.compile(r"sk-[A-Za-z0-9]{20,}"),                                                  # OpenAI-style key
    re.compile(r"AKIA[0-9A-Z]{16}"),                                                     # AWS access key id
    re.compile(r"(?i)(api[_-]?key|secret|password|token)\s*[=:]\s*['\"][^'\"]{8,}['\"]"),  # gán chuỗi cứng
]


def audit_project(path, max_mb: float = 50) -> list[str]:
    """Danh sách vấn đề (đã sort) của repo dự án tại path; rỗng là đạt."""
    # TODO: README.md ở gốc: thiếu -> "missing-readme"; có -> kiểm các heading "## " theo REQUIRED_SECTIONS
    #       ("missing-section:<khoá>") và giấy phép dữ liệu ("no-data-license")
    # TODO: không có tệp nào trong DEPENDENCY_FILES ở gốc -> "no-dependencies"
    # TODO: duyệt mọi tệp (bỏ SKIP_DIRS): "large-file:<rel>", "env-file:<rel>", "secret:<rel>" (rel dạng posix)
    raise NotImplementedError


if __name__ == "__main__":
    problems = audit_project(sys.argv[1] if len(sys.argv) > 1 else ".")
    print("\n".join(problems) if problems else "Đạt: không phát hiện vấn đề.")

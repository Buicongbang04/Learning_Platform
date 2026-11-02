"""Chọn thư mục được chấm: `capstone/project/` của bạn, hoặc bản tham chiếu `capstone/solutions/project/` khi SOLUTION=1."""

import sys
from pathlib import Path

import pytest

from testkit import use_solution

CAPSTONE = Path(__file__).resolve().parents[2]
if str(Path(__file__).parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).parent))


@pytest.fixture(scope="session")
def project_root() -> Path:
    return CAPSTONE / "solutions" / "project" if use_solution() else CAPSTONE / "project"

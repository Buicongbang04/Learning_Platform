"""Chọn thư mục được chấm: `capstone/project/` của bạn, hoặc bản tham chiếu `capstone/solutions/project/` khi SOLUTION=1."""

from pathlib import Path

import pytest

from testkit import use_solution

CAPSTONE = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="session")
def project_root() -> Path:
    return CAPSTONE / "solutions" / "project" if use_solution() else CAPSTONE / "project"

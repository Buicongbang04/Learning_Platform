import sys
from pathlib import Path

import pytest

import fdekit

sys.path.insert(0, str(Path(__file__).resolve().parent))


@pytest.fixture(scope="session")
def capstone() -> Path:
    """Repo capstone của bạn (`FDE_CAPSTONE_DIR`), hoặc lời giải tham chiếu khi `SOLUTION=1`."""
    return fdekit.capstone_dir().resolve()

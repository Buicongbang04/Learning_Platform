"""Test của package `legal_assistant`.

    uv run pytest tracks/ai-engineer/capstone/project/tests -q -rs

Capstone là dự án của bạn nên hàm còn `NotImplementedError` làm test tương ứng **skip** kèm lời nhắc (`-rs` để xem),
không fail. Test chạy offline trên bộ luật tí hon tự viết ở `fixtures/mini-legal/` (văn bản hư cấu, không trích Zalo)
và `llmkit.FakeLLM`; test trên bộ thật skip khi chưa tải `zalo-legal`.

Repo không có lời giải mẫu của capstone: `SOLUTION=1` skip cả thư mục. Muốn chạy test trên một bản cài đặt khác
(ví dụ repo portfolio của bạn), đặt `LEGAL_ASSISTANT_SRC=<thư mục chứa legal_assistant/>`.
"""

import importlib
import os
import sys
from pathlib import Path

import pytest

from testkit import use_solution

PROJECT = Path(__file__).resolve().parents[1]
FIXTURES = Path(__file__).resolve().parent / "fixtures"


def _source() -> Path:
    return Path(os.environ.get("LEGAL_ASSISTANT_SRC") or PROJECT).resolve()


@pytest.fixture(autouse=True)
def _reference_not_in_repo():
    if use_solution() and not os.environ.get("LEGAL_ASSISTANT_SRC"):
        pytest.skip("Capstone không có lời giải mẫu trong repo; đặt LEGAL_ASSISTANT_SRC để chạy trên bản cài đặt khác")


@pytest.fixture(scope="session")
def la():
    src = _source()
    if str(src) not in sys.path:
        sys.path.insert(0, str(src))
    package = importlib.import_module("legal_assistant")
    where = Path(package.__file__).resolve().parent
    if where.parent != src:
        pytest.fail(f"Đang import legal_assistant từ {where}, không phải từ {src}")
    return lambda name: importlib.import_module(f"legal_assistant.{name}")


@pytest.fixture(scope="session")
def mini() -> Path:
    return FIXTURES / "mini-legal"


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    report = outcome.get_result()
    if call.excinfo is not None and call.excinfo.errisinstance(NotImplementedError):
        report.outcome = "skipped"
        report.longrepr = (str(item.path), item.location[1] or 0, f"Chưa làm: {call.excinfo.value}")

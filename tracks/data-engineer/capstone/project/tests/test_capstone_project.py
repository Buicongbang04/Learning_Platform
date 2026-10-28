"""Smoke test cho khung capstone. Thêm test của bạn vào thư mục này.

    uv run pytest tracks/data-engineer/capstone/project/tests -q
"""

from pathlib import Path

PROJECT = Path(__file__).resolve().parents[1]


def test_project_layout():
    for name in ["ingestion", "models", "dags", "streaming", "infra", "dashboards", "tests"]:
        assert (PROJECT / name).is_dir(), f"Thiếu thư mục {name}/"


def test_ingestion_table_map():
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "capstone_load_postgres", PROJECT / "ingestion" / "load_postgres.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert len(module.TABLES) == 9

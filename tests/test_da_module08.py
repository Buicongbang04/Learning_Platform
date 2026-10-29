"""Kiểm tổng module 08 (Trực quan hoá & đọc biểu đồ) của track Data Analyst: cấu trúc bài, lời giải, notebook sạch."""
from pathlib import Path

import nbformat
import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
MODULE = ROOT / "tracks" / "data-analyst" / "modules" / "08-visualization-chart-reading"
LEVELS = ("basic", "intermediate", "advanced")
EXPECTED = {
    "basic": ["01-chart-chooser", "02-bike-chart-types", "03-order-value-distribution"],
    "intermediate": ["01-misleading-chart-audit", "02-retail-chart-reading", "03-simpson-and-funnel"],
    "advanced": ["01-revenue-drop-investigation", "02-redesign-for-stakeholder"],
}
SECTIONS = ["## Mục tiêu", "## Đề bài", "## Tiêu chí đạt", "## Gợi ý"]


def frontmatter(readme: Path) -> tuple[dict, str]:
    text = readme.read_text(encoding="utf-8")
    assert text.startswith("---\n"), f"{readme} thiếu frontmatter"
    _, head, body = text.split("---\n", 2)
    return yaml.safe_load(head) or {}, body


def exercises() -> list[Path]:
    return sorted(p for level in LEVELS for p in (MODULE / "exercises" / level).glob("*") if p.is_dir())


def solution_dir(ex: Path) -> Path:
    return MODULE / "solutions" / ex.parent.name / ex.name


def is_quiz_only(meta: dict) -> bool:
    return not any(f["path"].startswith(("starter/", "tests/")) for f in meta.get("files") or [])


EXERCISES = exercises()
IDS = [f"{p.parent.name}/{p.name}" for p in EXERCISES]


def test_module_has_expected_exercises():
    found = {level: sorted(p.name for p in (MODULE / "exercises" / level).glob("*") if p.is_dir()) for level in LEVELS}
    assert found == EXPECTED


def test_module_docs_exist():
    assert (MODULE / "README.md").is_file()
    assert (MODULE / "interview.md").is_file()


@pytest.mark.parametrize("ex", EXERCISES, ids=IDS)
def test_readme_frontmatter(ex):
    meta, body = frontmatter(ex / "README.md")
    assert {"title", "level", "services", "files", "run"} <= set(meta)
    assert isinstance(meta["title"], str) and meta["title"].strip()
    assert meta["level"] == ex.parent.name, "level phải khớp thư mục"
    assert isinstance(meta["services"], list) and isinstance(meta["files"], list) and isinstance(meta["run"], list)
    for f in meta["files"]:
        assert (ex / f["path"]).is_file(), f"frontmatter liệt kê {f['path']} nhưng không có tệp"
    for section in SECTIONS:
        assert section in body, f"thiếu {section}"


@pytest.mark.parametrize("ex", EXERCISES, ids=IDS)
def test_solution_layout(ex):
    meta, _ = frontmatter(ex / "README.md")
    sol = solution_dir(ex)
    assert (sol / "SOLUTION.md").is_file()
    if is_quiz_only(meta):
        assert (ex / "quiz.yaml").is_file()
        assert (sol / "quiz-answers.yaml").is_file()
        assert meta["files"] == [] and meta["run"] == []
        assert not (ex / "starter").exists() and not (ex / "tests").exists()
        return
    starter = sorted(p.name for p in (ex / "starter").iterdir() if p.is_file())
    assert starter, "bài có code phải có starter/"
    assert list((ex / "tests").glob("test_*.py")), "bài có code phải có tests/test_*.py"
    if ex.parent.name == "advanced":
        # Advanced: chỉ SOLUTION.md (hướng làm + rubric), không có tệp lời giải trùng starter
        assert not [name for name in starter if (sol / name).exists()]
    else:
        missing = [name for name in starter if not (sol / name).is_file()]
        assert not missing, f"thiếu lời giải trùng tên starter: {missing}"
    if (ex / "quiz.yaml").exists():
        assert (sol / "quiz-answers.yaml").is_file()


NOTEBOOKS = sorted(MODULE.glob("**/*.ipynb"))


@pytest.mark.parametrize("path", NOTEBOOKS, ids=lambda p: str(p.relative_to(MODULE)))
def test_notebook_committed_without_outputs(path):
    book = nbformat.read(path, as_version=4)
    for number, cell in enumerate(book.cells, start=1):
        if cell.cell_type == "code":
            assert cell.outputs == [], f"cell {number} còn output"
            assert cell.execution_count is None, f"cell {number} còn execution_count"

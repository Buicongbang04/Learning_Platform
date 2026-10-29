import math
from pathlib import Path

import pytest

from testkit import Exercise

FIXTURES = Path(__file__).parent / "fixtures" / "nb_exercise" / "exercises" / "basic"


def exercise(slug: str) -> Exercise:
    return Exercise(str(FIXTURES / slug / "tests" / "locate.py"))


def test_notebook_exec_skips_explore_and_magics(monkeypatch):
    monkeypatch.delenv("SOLUTION", raising=False)
    nb = exercise("01-demo").notebook("analysis.ipynb")
    assert nb.area(1) == pytest.approx(math.pi)
    assert nb.ANSWER == 42


def test_notebook_solution_mode(monkeypatch):
    monkeypatch.setenv("SOLUTION", "1")
    assert exercise("01-demo").notebook("analysis.ipynb").area(1) == -1.0


def test_two_exercises_same_filename_do_not_collide(monkeypatch):
    monkeypatch.delenv("SOLUTION", raising=False)
    assert exercise("01-demo").notebook("analysis.ipynb").area(1) == pytest.approx(math.pi)
    assert exercise("02-demo").notebook("analysis.ipynb").area(1) == 0.0


def test_module_still_works(monkeypatch):
    monkeypatch.delenv("SOLUTION", raising=False)
    assert exercise("01-demo").module("calc.py").double(4) == 8


def test_failed_load_is_not_cached(monkeypatch):
    monkeypatch.delenv("SOLUTION", raising=False)
    ex = exercise("01-demo")
    for _ in range(2):
        with pytest.raises(RuntimeError, match="top-level"):
            ex.notebook("broken.ipynb")


def test_jupyter_idioms_in_graded_cells(monkeypatch):
    monkeypatch.delenv("SOLUTION", raising=False)
    nb = exercise("01-demo").notebook("idioms.ipynb")
    assert nb.VALUE == 42


def test_traceback_points_to_notebook_cell(monkeypatch):
    import traceback

    monkeypatch.delenv("SOLUTION", raising=False)
    with pytest.raises(RuntimeError) as info:
        exercise("01-demo").notebook("broken.ipynb")
    frame = traceback.extract_tb(info.value.__traceback__)[-1]
    assert frame.filename.endswith("broken.ipynb[cell 1]")
    assert frame.lineno == 3
    assert frame.line == "raise RuntimeError('lỗi top-level')"

"""Chấm bộ check của bạn bằng mutation testing.

1. Mọi hàm check_* trong starter/checks.py phải PASS trên pipeline đúng (tests/fixtures/pipeline.py).
2. Với mỗi mutant trong tests/fixtures/mutants.py, ít nhất một check phải FAIL.
"""

import importlib.util
import inspect
import sys
from types import SimpleNamespace

import pytest

from testkit import Exercise

ex = Exercise(__file__)


def load_fixture(name):
    path = ex.fixtures / name
    unique = f"ex08_pipeline_testing_{path.stem}"
    if unique in sys.modules:
        return sys.modules[unique]
    spec = importlib.util.spec_from_file_location(unique, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[unique] = module
    spec.loader.exec_module(module)
    return module


PIPELINE = load_fixture("pipeline.py")
MUTANTS = load_fixture("mutants.py").MUTANTS


def as_namespace(**override):
    funcs = {n: getattr(PIPELINE, n) for n in ("clean_orders", "revenue_by_state", "load_orders")}
    funcs.update(override)
    return SimpleNamespace(**funcs)


def checks():
    module = ex.module("checks.py")
    found = {name: fn for name, fn in inspect.getmembers(module, inspect.isfunction)
             if name.startswith("check_") and fn.__module__ == module.__name__}
    return found


def test_has_enough_checks():
    assert len(checks()) >= 4, "Viết ít nhất 4 hàm check_*"


def test_checks_pass_on_correct_pipeline():
    failures = []
    for name, fn in checks().items():
        try:
            fn(as_namespace())
        except Exception as exc:  # noqa: BLE001
            failures.append(f"{name}: {type(exc).__name__}: {exc}")
    assert not failures, "Check fail trên pipeline ĐÚNG:\n" + "\n".join(failures)


@pytest.mark.parametrize("mutant", sorted(MUTANTS))
def test_mutant_is_killed(mutant):
    func_name, impl = MUTANTS[mutant]
    bad = as_namespace(**{func_name: impl})
    killed_by = []
    for name, fn in checks().items():
        try:
            fn(bad)
        except NotImplementedError:
            continue
        except Exception:  # noqa: BLE001
            killed_by.append(name)
    assert killed_by, f"Không check nào phát hiện mutant {mutant} (lỗi ở {func_name})"

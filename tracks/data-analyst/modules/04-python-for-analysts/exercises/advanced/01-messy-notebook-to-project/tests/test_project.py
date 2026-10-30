import ast
import hashlib
import importlib
import os
import re
import subprocess
import sys

import nbformat
import numpy as np
import pandas as pd
import pytest

from testkit import Exercise

ex = Exercise(__file__)
MODULES = ["clean", "metrics", "pipeline"]
README_HEADINGS = ["## Câu hỏi", "## Dữ liệu", "## Cách chạy", "## Cấu trúc", "## Kết quả",
                   "## Thay đổi so với notebook cũ"]
METRIC_COLUMNS = ["month", "Country", "revenue", "orders", "customers"]
ABSOLUTE_PATH = re.compile(r"(/Users/|/home/|[A-Za-z]:\\\\|~/Downloads)")


def project():
    return ex.path("project")


def load(name):
    """Import retail_report.<name> từ project/src của bạn (bỏ cache cũ)."""
    src = str(project() / "src")
    for key in [k for k in sys.modules if k == "retail_report" or k.startswith("retail_report.")]:
        del sys.modules[key]
    if src not in sys.path:
        sys.path.insert(0, src)
    return importlib.import_module(f"retail_report.{name}")


def tiny_tx():
    return pd.DataFrame({
        "Invoice": [1001, 1001, "C1002", 1003, 1004, 1005, 1006, 1006, "A1007"],
        "StockCode": ["A", "B", "A", "C", "A", "B", "C", "A", "B"],
        "InvoiceDate": pd.to_datetime(["2010-12-01 09:00", "2010-12-01 09:00", "2010-12-02 10:00", "2010-12-15 11:00",
                                       "2011-12-03 12:00", "2011-12-05 13:00", "2011-12-06 14:00", "2011-12-06 14:00",
                                       "2011-12-07 08:00"]),
        "Quantity": [2, 1, -2, 3, 1, 4, 5, 1, 1],
        "Price": [5.0, 10.0, 5.0, 0.0, 8.0, 2.5, 2.0, 6.0, -100.0],
        "Customer ID": [1.0, 1.0, 1.0, 2.0, 3.0, np.nan, 1.0, 1.0, np.nan],
        "Country": ["United Kingdom", "United Kingdom", "United Kingdom", "Germany", "Germany", "United Kingdom",
                    "United Kingdom", "United Kingdom", "United Kingdom"],
    })


# ---------- cấu trúc ----------

def test_structure():
    root = project()
    required = ["README.md", ".gitignore", "data/raw", "data/processed", "notebooks", "tests",
                *[f"src/retail_report/{m}.py" for m in ["__init__", *MODULES]]]
    missing = [p for p in required if not (root / p).exists()]
    assert not missing, f"Thiếu trong project/: {missing}"
    assert list((root / "notebooks").glob("*.ipynb")), "notebooks/ cần ít nhất một notebook"
    assert list((root / "tests").glob("test_*.py")), "tests/ cần ít nhất một tệp test_*.py"


def test_gitignore():
    lines = [ln.strip() for ln in (project() / ".gitignore").read_text(encoding="utf-8").splitlines()]
    rules = [ln for ln in lines if ln and not ln.startswith("#")]
    for needed in ["data/raw", "data/processed", ".ipynb_checkpoints"]:
        assert any(needed in r and not r.startswith("!") for r in rules), f".gitignore phải bỏ qua {needed}"


def test_readme():
    text = (project() / "README.md").read_text(encoding="utf-8")
    assert "TODO" not in text, "README còn TODO"
    positions = [text.find(h) for h in README_HEADINGS]
    missing = [h for h, p in zip(README_HEADINGS, positions) if p < 0]
    assert not missing, f"README thiếu mục: {missing}"
    assert positions == sorted(positions), "Các mục README phải theo đúng thứ tự"
    assert "CC BY 4.0" in text, "Mục Dữ liệu ghi giấy phép (CC BY 4.0)"
    changes = text.split("## Thay đổi so với notebook cũ", 1)[1].split("\n## ", 1)[0]
    bullets = [ln for ln in changes.splitlines() if re.match(r"\s*[-*] ", ln)]
    assert len(bullets) >= 4, "Mục 'Thay đổi so với notebook cũ' cần ít nhất 4 lỗi (gạch đầu dòng)"
    assert re.search(r"\d", changes), "Nêu con số đã đổi (trước/sau) cho ít nhất một lỗi"


def test_notebooks_and_src_are_clean():
    notebooks = list((project() / "notebooks").glob("*.ipynb")) if (project() / "notebooks").is_dir() else []
    assert notebooks, "notebooks/ cần ít nhất một notebook"
    for path in (project() / "src").rglob("*.py"):
        assert not ABSOLUTE_PATH.search(path.read_text(encoding="utf-8")), f"{path.name} có đường dẫn tuyệt đối"
    for path in notebooks:
        nb = nbformat.read(path, as_version=4)
        code = [c for c in nb.cells if c.cell_type == "code"]
        for number, cell in enumerate(code, start=1):
            assert not cell.get("outputs"), f"{path.name}: cell code {number} còn output (dùng nbstripout)"
            assert cell.get("execution_count") is None, f"{path.name}: cell code {number} còn execution_count"
            assert not ABSOLUTE_PATH.search(cell.source), f"{path.name}: cell code {number} có đường dẫn tuyệt đối"
        source = "\n".join(c.source for c in code)
        assert "retail_report" in source, f"{path.name} phải import hàm từ retail_report thay vì tự viết lại"
        assert 'startswith("C")' not in source and "startswith('C')" not in source, (
            f"{path.name}: quy tắc làm sạch chỉ nằm trong src/retail_report/clean.py")



# ---------- hàm trong src ----------

def test_clean_transactions():
    clean = load("clean")
    tx = tiny_tx()
    before = tx.copy()
    out = clean.clean_transactions(tx)
    pd.testing.assert_frame_equal(tx, before)
    assert out["Invoice"].tolist() == ["1001", "1001", "1004", "1005", "1006", "1006"]
    assert out["revenue"].tolist() == pytest.approx([10.0, 10.0, 8.0, 10.0, 10.0, 6.0])


def test_monthly_country_revenue():
    clean, metrics = load("clean"), load("metrics")
    out = metrics.monthly_country_revenue(clean.clean_transactions(tiny_tx()))
    assert list(out.columns) == METRIC_COLUMNS
    assert list(out.index) == list(range(len(out)))
    # tháng 12/2010 và 12/2011 phải là hai tháng khác nhau (lỗi .dt.month của notebook cũ)
    assert out["month"].tolist() == list(pd.to_datetime(["2010-12-01", "2011-12-01", "2011-12-01"]))
    assert out["Country"].tolist() == ["United Kingdom", "United Kingdom", "Germany"]
    assert out["revenue"].tolist() == pytest.approx([20.0, 26.0, 8.0])
    assert out["orders"].tolist() == [1, 2, 1]
    assert out["customers"].tolist() == [1, 1, 1]


@pytest.fixture()
def raw_workbook(tmp_path):
    raw = tmp_path / "data" / "raw" / "online_retail_II.xlsx"
    raw.parent.mkdir(parents=True)
    with pd.ExcelWriter(raw) as writer:
        tiny_tx().to_excel(writer, sheet_name="Year 2010-2011", index=False)
        tiny_tx().head(2).to_excel(writer, sheet_name="Year 2009-2010", index=False)
    return raw


def test_build_is_idempotent_and_leaves_raw_alone(raw_workbook, tmp_path):
    pipeline = load("pipeline")
    raw_hash = hashlib.sha256(raw_workbook.read_bytes()).hexdigest()
    raw_files = sorted(p.name for p in raw_workbook.parent.iterdir())
    out_dir = tmp_path / "data" / "processed" / "nested"
    first = pipeline.build(raw_workbook, out_dir)
    content = first.read_bytes()
    second = pipeline.build(raw_workbook, out_dir)
    assert first.name == "monthly_country_revenue.csv" and first.parent == out_dir
    assert second.read_bytes() == content, "Chạy build hai lần phải ra tệp giống hệt"
    assert hashlib.sha256(raw_workbook.read_bytes()).hexdigest() == raw_hash, "build không được sửa dữ liệu gốc"
    assert sorted(p.name for p in raw_workbook.parent.iterdir()) == raw_files, "build không được ghi vào data/raw"
    table = pd.read_csv(first)
    assert list(table.columns) == METRIC_COLUMNS
    assert table["revenue"].sum() == pytest.approx(54.0)


def test_learner_tests_pass():
    root = project()
    files = list((root / "tests").glob("test_*.py"))
    count = sum(1 for f in files for n in ast.parse(f.read_text(encoding="utf-8")).body
                if isinstance(n, ast.FunctionDef) and n.name.startswith("test_"))
    assert count >= 3, f"project/tests cần ít nhất 3 hàm test_*, hiện có {count}"
    env = {**os.environ, "PYTHONPATH": str(root / "src")}
    proc = subprocess.run([sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", "tests"],
                          cwd=root, capture_output=True, text=True, timeout=120, env=env)
    assert proc.returncode == 0, f"Test trong project/tests phải pass:\n{proc.stdout[-3000:]}"

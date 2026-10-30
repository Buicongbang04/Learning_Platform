import json
import re

import pytest

from testkit import Exercise

ex = Exercise(__file__)
GOOD_README = """# Nên cắt mã hàng nào năm 2012?

Kết luận: cắt 516 mã, mất 0.15% doanh thu.

## Câu hỏi business

Head of Merchandising muốn cắt 20% mã hàng.

## Dữ liệu

Online Retail II (UCI), giấy phép CC BY 4.0.

## Kết quả

Bảng và chart.

## Giới hạn

Không có giá vốn.
"""


@pytest.fixture(scope="module")
def check():
    return ex.module("portfolio_check.py")


def make(root, files):
    for rel, content in files.items():
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(content, bytes):
            p.write_bytes(content)
        else:
            p.write_text(content, encoding="utf-8")
    return root


def test_good_project_passes(check, tmp_path):
    make(tmp_path, {"README.md": GOOD_README, "pyproject.toml": "[project]\nname='x'\n",
                    "notebooks/analysis.ipynb": json.dumps({"cells": [{"source": ["import os\n", "key = os.environ['API_KEY']\n"]}]}),
                    "src/clean.py": "PASSWORD_ENV = 'DB_PASSWORD'  # tên biến, không phải mật khẩu\n"})
    assert check.audit_project(tmp_path) == []


def test_missing_readme_and_dependencies(check, tmp_path):
    make(tmp_path, {"analysis.py": "print(1)\n"})
    assert check.audit_project(tmp_path) == ["missing-readme", "no-dependencies"]


def test_missing_sections_and_license(check, tmp_path):
    readme = "# Dự án\n\n## Data\n\nKaggle.\n\n## Findings\n\nAOV tăng.\n"
    make(tmp_path, {"README.md": readme, "requirements.txt": "pandas\n"})
    assert check.audit_project(tmp_path) == ["missing-section:limitations", "missing-section:question", "no-data-license"]


def test_sections_matched_only_on_level_two_headings(check, tmp_path):
    readme = GOOD_README.replace("## Giới hạn", "### Giới hạn")
    make(tmp_path, {"README.md": readme, "requirements.txt": "pandas\n"})
    assert check.audit_project(tmp_path) == ["missing-section:limitations"]


def test_large_file_env_and_secrets(check, tmp_path):
    make(tmp_path, {
        "README.md": GOOD_README, "environment.yml": "name: x\n",
        "data/raw/big.csv": b"x" * (2 * 1024 * 1024 + 1),
        "data/raw/small.csv": b"x" * 1024,
        ".env": "OPENAI_API_KEY=abc\n",
        "notebooks/eda.ipynb": json.dumps({"cells": [{"source": ["client = OpenAI(api_key=\"sk-abcdefghijklmnopqrstuvwxyz123456\")\n"]}]}),
        "src/aws.py": "ID = 'AKIAABCDEFGHIJKLMNOP'\n",
        "src/db.py": "password = \"hunter2hunter2\"\n",
        "src/ok.py": "token = os.getenv('TOKEN')\n",
        ".git/config": "token = \"should-not-be-scanned\"\n",
    })
    assert check.audit_project(tmp_path, max_mb=2) == [
        "env-file:.env", "large-file:data/raw/big.csv", "secret:notebooks/eda.ipynb", "secret:src/aws.py", "secret:src/db.py",
    ]


def test_accepts_str_path(check, tmp_path):
    make(tmp_path, {"README.md": GOOD_README, "requirements.txt": "pandas\n"})
    assert check.audit_project(str(tmp_path)) == []


# ---------- PORTFOLIO_PLAN.md ----------

PLAN_HEADINGS = ["## Vai trò mục tiêu", "## Dự án", "## Kaggle", "## Khoá học và chứng chỉ", "## Networking",
                 "## Kế hoạch 90 ngày"]


@pytest.fixture(scope="module")
def plan():
    return ex.read("PORTFOLIO_PLAN.md")


def section(text, heading):
    start = text.index(heading) + len(heading)
    nxt = text.find("\n## ", start)
    return text[start:] if nxt == -1 else text[start:nxt]


def test_plan_complete(plan):
    assert "TODO" not in plan, "Còn dòng TODO trong PORTFOLIO_PLAN.md"
    words = len(plan.split())
    assert 400 <= words <= 1500, f"400-1500 từ, hiện có {words}"
    pos = [plan.find(h) for h in PLAN_HEADINGS]
    assert all(p >= 0 for p in pos), f"Thiếu mục: {[h for h, p in zip(PLAN_HEADINGS, pos) if p < 0]}"
    assert pos == sorted(pos), "Các mục phải theo đúng thứ tự của khung"


def test_plan_projects(plan):
    blocks = re.split(r"\n### ", section(plan, "## Dự án"))[1:]
    assert len(blocks) >= 3, "Mục Dự án cần ít nhất ba dự án, mỗi dự án một heading ###"
    for block in blocks:
        name = block.splitlines()[0]
        for field in ("Câu hỏi:", "Dữ liệu:", "Giấy phép:"):
            assert field in block, f"Dự án '{name}' thiếu dòng '{field}'"
        assert "http" in block, f"Dự án '{name}' cần link nguồn dữ liệu"


def test_plan_90_days(plan):
    lines = [l for l in section(plan, "## Kế hoạch 90 ngày").splitlines() if l.lstrip().startswith(("- ", "* ", "|"))]
    assert len(lines) >= 3, "Kế hoạch 90 ngày cần ít nhất ba mốc (gạch đầu dòng hoặc dòng bảng)"

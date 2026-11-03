import re

from testkit import Exercise

ex = Exercise(__file__)
LEGACY_PATHS = [
    "README.md", "requirements.txt", "config.py", "train.py", "utils.py", "app.py",
    "data/", "models/", "model_v7", "final_FINAL_v3.ipynb", "tests/", ".gitignore",
]


def sections(text: str) -> dict[str, str]:
    parts = re.split(r"^## ", text, flags=re.MULTILINE)[1:]
    return {part.splitlines()[0].strip(): "\n".join(part.splitlines()[1:]) for part in parts}


def items(body: str, pattern: str) -> list[str]:
    return [line.strip() for line in body.splitlines() if re.match(pattern, line.strip())]


def test_review_has_the_four_sections_filled():
    parts = sections(ex.read("review.md"))
    assert list(parts) == ["Phát hiện", "Kế hoạch refactor", "Thứ tự và lý do", "Không làm (và vì sao)"]
    for name, body in parts.items():
        assert "TODO" not in body, f"Mục '{name}' còn TODO"


def test_findings_are_graded_and_point_at_real_files():
    body = sections(ex.read("review.md"))["Phát hiện"]
    findings = items(body, r"^[-*]\s*\[P[012]\]")
    assert len(findings) >= 8, f"Cần ít nhất 8 phát hiện có mức [P0..P2], mới có {len(findings)}"
    assert any("[P0]" in f for f in findings), "Phải có ít nhất một [P0] (việc phải xử lý ngay)"
    touched = {path for path in LEGACY_PATHS if path in body}
    assert len(touched) >= 6, f"Phát hiện chỉ nhắc {len(touched)} vị trí trong repo, cần ít nhất 6: {sorted(touched)}"
    assert all(len(f) >= 60 for f in findings), "Mỗi phát hiện cần nêu triệu chứng và hậu quả, không chỉ một cụm từ"


def test_secret_in_config_is_flagged_as_p0():
    body = sections(ex.read("review.md"))["Phát hiện"]
    secret = [line for line in body.splitlines() if "config.py" in line and re.search(r"(?i)secret|mật khẩu|password|DB_URL|lộ", line)]
    assert secret and any("[P0]" in line for line in secret), "Mật khẩu DB nằm trong config.py (và trong lịch sử git) phải là [P0]"


def test_plan_is_numbered_and_each_step_has_a_check():
    body = sections(ex.read("review.md"))["Kế hoạch refactor"]
    steps = items(body, r"^\d+\.")
    assert len(steps) >= 5, f"Cần ít nhất 5 bước đánh số, mới có {len(steps)}"
    missing = [step[:40] for step in steps if "Kiểm:" not in step]
    assert not missing, f"Các bước thiếu 'Kiểm:': {missing}"


def test_ordering_and_non_goals_are_argued():
    parts = sections(ex.read("review.md"))
    assert len(parts["Thứ tự và lý do"].strip()) >= 300, "Giải thích thứ tự cần ít nhất 300 ký tự"
    assert len(items(parts["Không làm (và vì sao)"], r"^[-*]\s+\S{3}")) >= 2

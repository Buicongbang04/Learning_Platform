"""Kiểm mọi quiz.yaml trong tracks/ cùng quiz-answers.yaml tương ứng."""
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
KINDS = {"data", "knowledge"}
TYPES = {"single", "multi"}


def answers_path(quiz: Path) -> Path:
    parts = quiz.parent.as_posix().replace("/exercises/", "/solutions/")
    return Path(parts) / "quiz-answers.yaml"


def validate(quiz: Path) -> list[str]:
    errs: list[str] = []
    data = yaml.safe_load(quiz.read_text(encoding="utf-8")) or {}
    questions = data.get("questions") if isinstance(data, dict) else None
    if not isinstance(questions, list) or not questions:
        return ["cần ít nhất 1 câu trong questions"]
    ap = answers_path(quiz)
    if not ap.exists():
        return [f"thiếu {ap}"]
    key = yaml.safe_load(ap.read_text(encoding="utf-8")) or {}
    if not isinstance(key, dict):
        return ["quiz-answers.yaml phải là mapping"]
    ids = [q.get("id") for q in questions]
    for qid in {i for i in ids if ids.count(i) > 1}:
        errs.append(f"id câu trùng: {qid}")
    for q in questions:
        qid = q.get("id")
        if q.get("kind") not in KINDS:
            errs.append(f"{qid}: kind không hợp lệ")
        if q.get("type") not in TYPES:
            errs.append(f"{qid}: type không hợp lệ")
        opts = [o.get("id") for o in q.get("options") or []]
        if len(opts) < 2:
            errs.append(f"{qid}: cần ít nhất 2 lựa chọn")
        if len(set(opts)) != len(opts):
            errs.append(f"{qid}: id lựa chọn trùng")
        if qid not in key:
            errs.append(f"{qid}: thiếu đáp án")
            continue
        ans = key[qid]
        if not isinstance(ans, list) or not ans or not set(ans) <= set(opts):
            errs.append(f"{qid}: đáp án phải là tập con không rỗng của lựa chọn")
        elif len(set(ans)) != len(ans):
            errs.append(f"{qid}: đáp án lặp")
        elif q.get("type") == "single" and len(ans) != 1:
            errs.append(f"{qid}: single cần đúng 1 đáp án")
    for extra in set(key) - set(ids):
        errs.append(f"đáp án thừa: {extra}")
    return errs


QUIZZES = sorted((ROOT / "tracks").glob("**/exercises/*/*/quiz.yaml"))


@pytest.mark.parametrize("quiz", QUIZZES, ids=lambda p: p.parent.name)
def test_quiz_file_is_valid(quiz):
    assert validate(quiz) == []


def make(tmp_path, quiz: str, answers: str | None) -> Path:
    ex = tmp_path / "exercises" / "basic" / "x"
    ex.mkdir(parents=True)
    (ex / "quiz.yaml").write_text(quiz, encoding="utf-8")
    if answers is not None:
        sol = tmp_path / "solutions" / "basic" / "x"
        sol.mkdir(parents=True)
        (sol / "quiz-answers.yaml").write_text(answers, encoding="utf-8")
    return ex / "quiz.yaml"


GOOD = "questions:\n  - {id: q1, kind: data, type: single, prompt: p, options: [{id: a, text: A}, {id: b, text: B}]}\n"


def test_validator_accepts_good(tmp_path):
    assert validate(make(tmp_path, GOOD, "q1: [a]\n")) == []


@pytest.mark.parametrize(
    "quiz,answers,needle",
    [
        (GOOD, None, "thiếu"),
        (GOOD, "{}\n", "thiếu đáp án"),
        (GOOD, "q1: [a]\nq9: [a]\n", "đáp án thừa"),
        (GOOD, "q1: [z]\n", "tập con"),
        (GOOD, "q1: [a, b]\n", "single"),
        (GOOD.replace("kind: data", "kind: x"), "q1: [a]\n", "kind"),
        (GOOD.replace("type: single", "type: x"), "q1: [a]\n", "type"),
        (GOOD.replace("{id: b, text: B}", "{id: a, text: B}"), "q1: [a]\n", "trùng"),
        (GOOD.replace(", {id: b, text: B}", ""), "q1: [a]\n", "2 lựa chọn"),
        (GOOD + GOOD.split("\n")[1] + "\n", "q1: [a]\n", "id câu trùng"),
        ("questions: []\n", "{}\n", "ít nhất 1 câu"),
    ],
)
def test_validator_rejects_bad(tmp_path, quiz, answers, needle):
    errs = validate(make(tmp_path, quiz, answers))
    assert any(needle in e for e in errs), errs


def longest_answer_problems(quiz: Path) -> list[str]:
    """Đáp án đúng không được hay là lựa chọn dài nhất (người học đoán được mà không cần biết bài).

    Xét câu single có >= 3 lựa chọn: số câu có đáp án dài nhất hẳn (theo số ký tự) tối đa max(1, n // 3).
    """
    questions = yaml.safe_load(quiz.read_text(encoding="utf-8"))["questions"]
    key = yaml.safe_load(answers_path(quiz).read_text(encoding="utf-8"))
    eligible = [q for q in questions if q["type"] == "single" and len(q["options"]) >= 3]
    longest = []
    for q in eligible:
        lengths = {o["id"]: len(str(o["text"])) for o in q["options"]}
        correct = key[q["id"]][0]
        if lengths[correct] > max(n for oid, n in lengths.items() if oid != correct):
            longest.append(q["id"])
    limit = max(1, len(eligible) // 3)
    if len(longest) > limit:
        return [f"{len(longest)}/{len(eligible)} câu single có đáp án dài nhất (tối đa {limit}): {', '.join(longest)}"]
    return []


@pytest.mark.parametrize("quiz", QUIZZES, ids=lambda p: p.parent.name)
def test_correct_option_not_usually_longest(quiz):
    assert longest_answer_problems(quiz) == []


def test_longest_answer_guard_rejects(tmp_path):
    def q(i: int) -> str:
        return (f"  - {{id: q{i}, kind: knowledge, type: single, prompt: p, options: "
                f"[{{id: a, text: ngắn}}, {{id: b, text: đáp án đúng dài hơn hẳn}}, {{id: c, text: cũng ngắn}}]}}\n")
    quiz = "questions:\n" + "".join(q(i) for i in range(6))
    answers = "".join(f"q{i}: [b]\n" for i in range(6))
    path = make(tmp_path, quiz, answers)
    assert validate(path) == []
    errs = longest_answer_problems(path)
    assert errs and "6/6" in errs[0] and "tối đa 2" in errs[0]
    # còn trong giới hạn: chỉ 2 trên 6 câu có đáp án dài nhất
    shorter = "".join(f"q{i}: [{'b' if i < 2 else 'a'}]\n" for i in range(6))
    (tmp_path / "solutions" / "basic" / "x" / "quiz-answers.yaml").write_text(shorter, encoding="utf-8")
    assert longest_answer_problems(path) == []

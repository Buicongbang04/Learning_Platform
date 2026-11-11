import re
from datetime import date
from pathlib import Path

import pytest
import yaml

from testkit import Exercise

ex = Exercise(__file__)
FIXTURES = Path(__file__).parent / "fixtures"
MEMBERS = ["An", "Bình", "Chi", "Dũng", "Giang", "Hà"]
WEEKS = [date(2026, 11, 16), date(2026, 11, 23), date(2026, 11, 30), date(2026, 12, 7)]
STATES = ["normal", "caution", "freeze-features", "freeze-all"]
ON_LEAVE = ("Giang", date(2026, 11, 30))
TRAINEE = "Hà"
BUDGET_MINUTES = (1 - 0.999) * 28 * 24 * 60
SECTIONS = 7


def load(name: str):
    try:
        return yaml.safe_load(ex.read(name))
    except yaml.YAMLError as error:
        pytest.fail(f"{name} không phải YAML hợp lệ: {error}")


def state_for(policy: dict, remaining: float) -> str:
    for level in policy["thresholds"]:
        floor = level["remaining_above"]
        if floor is None or remaining > floor:
            return level["state"]
    return "?"


def policy_problems(policy) -> list[str]:
    if not isinstance(policy, dict) or not isinstance(policy.get("thresholds"), list):
        return ["policy.yaml cần slo, thresholds, exceptions"]
    found = []
    budget = (policy.get("slo") or {}).get("budget_minutes")
    if not isinstance(budget, (int, float)) or isinstance(budget, bool) or abs(budget - BUDGET_MINUTES) > 0.1:
        found.append("slo.budget_minutes chưa đúng với SLO 99,9% trong 28 ngày")
    levels = policy["thresholds"]
    if [level.get("state") for level in levels if isinstance(level, dict)] != STATES:
        return found + [f"thresholds phải có đúng các state theo thứ tự {STATES}"]
    floors = [level.get("remaining_above") for level in levels]
    numbers = floors[:-1]
    if floors[-1] is not None or not all(isinstance(f, (int, float)) and not isinstance(f, bool) for f in numbers):
        found.append("remaining_above là số cho ba mức đầu, null cho mức cuối (budget đã cạn)")
    elif numbers != sorted(numbers, reverse=True) or len(set(numbers)) != len(numbers) or numbers[-1] != 0:
        found.append("remaining_above giảm dần, mức freeze-features là 0")
    for level in levels:
        if not level.get("actions"):
            found.append(f"{level['state']}: cần ít nhất một action")
        allowed = set(level.get("allowed") or [])
        if not {"security-fix", "rollback"} <= allowed:
            found.append(f"{level['state']}: luôn cho phép security-fix và rollback")
    if levels[2].get("allowed") and "feature" in levels[2]["allowed"] or levels[3].get("allowed") and "feature" in levels[3]["allowed"]:
        found.append("Khi đóng băng không cho phép feature")
    exceptions = policy.get("exceptions") or {}
    if not isinstance(exceptions.get("approver"), str) or "TODO" in exceptions["approver"] \
            or not isinstance(exceptions.get("max_per_window"), int) or not 0 < exceptions["max_per_window"] <= 2:
        found.append("exceptions cần approver và max_per_window từ 1 tới 2")
    return found


def oncall_problems(oncall) -> list[str]:
    if not isinstance(oncall, dict) or not isinstance(oncall.get("weeks"), list):
        return ["oncall.yaml cần weeks"]
    found = []
    if oncall.get("members") != MEMBERS:
        found.append("Không sửa danh sách members")
    handoff = oncall.get("handoff") or {}
    if handoff.get("weekday") != "monday" or not re.fullmatch(r"(0\d|1\d|2[0-3]):[0-5]\d", str(handoff.get("time"))):
        found.append("handoff: weekday monday và time dạng HH:MM")
    weeks = oncall["weeks"]
    if [w.get("start") for w in weeks if isinstance(w, dict)] != WEEKS:
        return found + [f"weeks phải là bốn tuần bắt đầu {', '.join(map(str, WEEKS))}"]
    slots: dict[str, int] = {}
    previous: set[str] = set()
    for week in weeks:
        people = {week.get("primary"), week.get("secondary")}
        if not people <= set(MEMBERS) or len(people) != 2:
            found.append(f"{week['start']}: primary và secondary là hai người khác nhau trong members")
            continue
        if people & previous:
            found.append(f"{week['start']}: {', '.join(sorted(people & previous))} trực hai tuần liền")
        if week["start"] == ON_LEAVE[1] and ON_LEAVE[0] in people:
            found.append(f"{week['start']}: {ON_LEAVE[0]} đang nghỉ phép")
        if week["primary"] == TRAINEE:
            found.append(f"{week['start']}: {TRAINEE} mới vào, chỉ được làm secondary")
        for person in people:
            slots[person] = slots.get(person, 0) + 1
        previous = people
    missing = [m for m in MEMBERS if m not in slots]
    heavy = [m for m, n in slots.items() if n > 2]
    if missing or heavy:
        found.append(f"Mỗi người 1 tới 2 ca: thiếu {missing}, quá tải {heavy}")
    levels = oncall.get("escalation") or []
    minutes = [level.get("after_minutes") for level in levels if isinstance(level, dict)]
    if len(levels) < 3 or minutes[:1] != [0] or minutes != sorted(set(minutes)) or minutes[-1] > 30:
        found.append("escalation: ít nhất 3 mức, after_minutes bắt đầu 0, tăng dần, mức cuối không quá 30")
    budget = oncall.get("page_budget") or {}
    per_week, night = budget.get("per_week"), budget.get("night_per_week")
    if not isinstance(per_week, int) or not isinstance(night, int) or not 0 < night <= 2 or not night < per_week <= 14:
        found.append("page_budget: night_per_week từ 1 tới 2, per_week lớn hơn nó và không quá 14")
    return found


def section(doc: str, number: int) -> str:
    match = re.search(rf"^## {number}\..*?$(.*?)(?=^## |\Z)", doc, re.M | re.S)
    return match.group(1) if match else ""


def mermaid_edges(text: str) -> int:
    blocks = re.findall(r"```mermaid\n(.*?)```", text, re.S)
    return sum(len(re.findall(r"--+>|==+>|-\.->", block)) for block in blocks)


def doc_problems(doc: str, policy: dict, oncall: dict) -> list[str]:
    found = ["Còn TODO"] if "TODO" in doc else []
    for number in range(1, SECTIONS + 1):
        if not re.search(rf"^## {number}\. ", doc, re.M):
            found.append(f"Thiếu phần '## {number}.'")
    if not re.search(r"40[.,]3", section(doc, 2)):
        found.append("Phần 2: nêu số phút error budget của cửa sổ")
    third = section(doc, 3)
    missing = [s for s in STATES if f"`{s}`" not in third]
    if missing or "|" not in third:
        found.append(f"Phần 3: bảng các mức, mỗi state viết trong dấu `: thiếu {missing}")
    fourth = section(doc, 4).lower()
    approver = str((policy.get("exceptions") or {}).get("approver", "")).lower()
    if not approver or approver not in fourth:
        found.append("Phần 4: nêu người duyệt ngoại lệ như trong policy.yaml")
    fifth = section(doc, 5)
    budget = oncall.get("page_budget") or {}
    for key in ("per_week", "night_per_week"):
        if str(budget.get(key)) not in re.findall(r"\d+", fifth):
            found.append(f"Phần 5: nêu page_budget.{key} như trong oncall.yaml")
    if not re.search(r"handoff|bàn giao", fifth, re.I) or not re.search(r"bù|nghỉ bù|phụ cấp|compensat", fifth, re.I):
        found.append("Phần 5: nói về bàn giao ca và chế độ bù cho người trực")
    sixth = section(doc, 6)
    if mermaid_edges(sixth) < 4:
        found.append("Phần 6: sơ đồ mermaid quy trình sự cố, ít nhất 4 cạnh")
    if not all(f"SEV{n}" in sixth for n in (1, 2, 3)) or not re.search(r"incident commander", sixth, re.I):
        found.append("Phần 6: bảng mức độ SEV1 tới SEV3 và vai trò incident commander")
    seventh = section(doc, 7)
    if not re.search(r"toil", seventh, re.I) or not re.search(r"\d+\s*%", seventh):
        found.append("Phần 7: đặt giới hạn toil bằng phần trăm thời gian")
    return found


def test_policy_yaml():
    found = policy_problems(load("policy.yaml"))
    assert not found, "\n".join(found)


@pytest.mark.parametrize("remaining,state", [(0.9, "normal"), (0.3, "caution"), (0.1, "freeze-features"), (0.0, "freeze-all"),
                                             (-0.4, "freeze-all")])
def test_policy_states(remaining, state):
    policy = load("policy.yaml")
    assert not policy_problems(policy), "Sửa policy.yaml trước (xem test_policy_yaml)"
    assert state_for(policy, remaining) == state


def test_oncall_yaml():
    oncall = load("oncall.yaml")
    found = oncall_problems(oncall)
    if isinstance(oncall, dict) and (oncall.get("team"), oncall.get("timezone")) != ("checkout", "Asia/Ho_Chi_Minh"):
        found.append("Giữ team: checkout và timezone: Asia/Ho_Chi_Minh")
    assert not found, "\n".join(found)


def test_policy_document():
    found = doc_problems(ex.read("POLICY.md"), load("policy.yaml") or {}, load("oncall.yaml") or {})
    assert not found, "\n".join(found)


def test_checks_catch_bad_files():
    policy = yaml.safe_load((FIXTURES / "policy.bad.yaml").read_text(encoding="utf-8"))
    found = "\n".join(policy_problems(policy))
    for needle in ("budget_minutes", "giảm dần", "freeze-all: luôn cho phép", "Khi đóng băng không cho phép feature", "exceptions"):
        assert needle in found, f"Không bắt được: {needle}\n{found}"
    oncall = yaml.safe_load((FIXTURES / "oncall.bad.yaml").read_text(encoding="utf-8"))
    found = "\n".join(oncall_problems(oncall))
    for needle in ("trực hai tuần liền", "Giang đang nghỉ phép", "Hà mới vào", "quá tải ['An']", "escalation", "page_budget"):
        assert needle in found, f"Không bắt được: {needle}\n{found}"
    good_policy = yaml.safe_load((FIXTURES / "policy.good.yaml").read_text(encoding="utf-8"))
    good_oncall = yaml.safe_load((FIXTURES / "oncall.good.yaml").read_text(encoding="utf-8"))
    assert policy_problems(good_policy) == [] and oncall_problems(good_oncall) == []
    weak = "\n".join(doc_problems((FIXTURES / "POLICY.weak.md").read_text(encoding="utf-8"), good_policy, good_oncall))
    for needle in ("Phần 2: nêu số phút", "Phần 3: bảng các mức", "Phần 5: nêu page_budget.night_per_week", "Phần 6: sơ đồ mermaid",
                   "Phần 7: đặt giới hạn toil"):
        assert needle in weak, f"Không bắt được: {needle}\n{weak}"
    assert doc_problems((FIXTURES / "POLICY.good.md").read_text(encoding="utf-8"), good_policy, good_oncall) == []

import yaml

from testkit import Exercise

ex = Exercise(__file__)
ROLES = ["ds", "mlops", "de", "backend", "pm"]
VALUES = {"R", "A", "AR", "C", "I", "-"}
ACTIVITIES = [
    "define-problem-label",
    "ingest-data",
    "data-contract-change",
    "train-model",
    "promotion-gate",
    "build-serving-ci",
    "deploy-rollback",
    "monitoring-alerts",
    "model-quality-oncall",
    "retrain-vs-rollback-decision",
]
CONTESTED = ["promotion-gate", "model-quality-oncall", "retrain-vs-rollback-decision"]


def problems(doc: dict) -> list[str]:
    found = []
    acts = doc.get("activities") if isinstance(doc, dict) else None
    if not isinstance(acts, dict) or list(acts) != ACTIVITIES:
        return [f"activities phải có đúng các khoá theo thứ tự: {ACTIVITIES}"]
    for name, row in acts.items():
        if not isinstance(row, dict) or set(row) != set(ROLES) or not set(row.values()) <= VALUES:
            found.append(f"{name}: mỗi dòng có đủ {ROLES} với giá trị trong {sorted(VALUES)}")
            continue
        if sum(v in ("A", "AR") for v in row.values()) != 1:
            found.append(f"{name}: phải có đúng một A")
        if not any(v in ("R", "AR") for v in row.values()):
            found.append(f"{name}: phải có ít nhất một R")
    if found:
        return found
    who = lambda act, vals: {r for r, v in acts[act].items() if v in vals}
    owner = {a: next(iter(who(a, ("A", "AR")))) for a in acts}
    for role in ("ds", "mlops", "de", "backend"):
        if role not in owner.values():
            found.append(f"{role} không là A của hoạt động nào")
    for role in ROLES:
        if list(owner.values()).count(role) > 5:
            found.append(f"{role} là A của quá nửa hoạt động")
    if owner["promotion-gate"] in who("train-model", ("R", "AR")):
        found.append("promotion-gate: người A không được là người R của train-model (tách quyền làm và duyệt)")
    if acts["data-contract-change"]["ds"] == "-":
        found.append("data-contract-change: ds phải được C hoặc I khi schema đổi")
    if owner["data-contract-change"] != "de":
        found.append("data-contract-change: bên sở hữu dữ liệu (de) là A")
    for role in ("ds", "mlops"):
        if acts["model-quality-oncall"][role] == "-":
            found.append(f"model-quality-oncall: {role} không được để '-'")
    if owner["define-problem-label"] == "backend":
        found.append("define-problem-label: backend không thể là A của định nghĩa nhãn và thời điểm dự đoán")
    decisions = doc.get("decisions") or {}
    for name in CONTESTED:
        if len(str(decisions.get(name) or "").strip()) < 80:
            found.append(f"decisions.{name}: cần lý do ít nhất 80 ký tự")
    return found


def test_raci_matrix():
    doc = yaml.safe_load(ex.read("raci.yaml"))
    found = problems(doc)
    assert not found, "\n".join(found)


def test_checks_catch_empty_template():
    doc = yaml.safe_load((ex.dir / "starter" / "raci.yaml").read_text(encoding="utf-8"))
    assert problems(doc)

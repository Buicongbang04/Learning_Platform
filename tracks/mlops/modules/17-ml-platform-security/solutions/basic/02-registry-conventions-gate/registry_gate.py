"""Cổng đăng ký model: quy ước tên, tag bắt buộc, model card, quyền theo đội."""

import re

from mlflow import MlflowClient

TEAMS = {"eta", "pricing", "fraud", "search", "ads"}
PLATFORM_TEAM = "platform"
REQUIRED_TAGS = ("owner", "team", "cost_center")
CARD_SECTIONS = ("Intended use", "Training data", "Metrics", "Limitations")
NAME = re.compile(r"^([a-z]+)-[a-z0-9]+(-[a-z0-9]+)*$")
EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[a-z]{2,}$")
COST_CENTER = re.compile(r"^CC-[0-9]{4}$")
VALIDATORS = {
    "owner": lambda v: bool(EMAIL.fullmatch(v)),
    "team": lambda v: v in TEAMS,
    "cost_center": lambda v: bool(COST_CENTER.fullmatch(v)),
}


def name_team(name: str) -> str | None:
    match = NAME.fullmatch(name or "")
    if not match or len(name) > 64 or match.group(1) not in TEAMS:
        return None
    return match.group(1)


def card_violations(card: str | None) -> list[str]:
    if not card or not card.strip():
        return ["model-card-missing"]
    headings = {line[3:].strip().lower() for line in card.splitlines() if line.startswith("## ")}
    return [f"model-card-section:{s}" for s in CARD_SECTIONS if s.lower() not in headings]


def check_request(request: dict) -> list[str]:
    violations = []
    name = request.get("name") or ""
    team = name_team(name)
    if team is None:
        violations.append("name")
    tags = {k: str(v).strip() for k, v in (request.get("tags") or {}).items() if v is not None}
    for key in REQUIRED_TAGS:
        value = tags.get(key, "")
        if not value:
            violations.append(f"tag-missing:{key}")
        elif not VALIDATORS[key](value):
            violations.append(f"tag-invalid:{key}")
    if team and VALIDATORS["team"](tags.get("team", "")) and tags["team"] != team:
        violations.append("team-mismatch")
    requester = request.get("requested_by")
    if requester is not None and team and requester.get("team") not in (team, PLATFORM_TEAM):
        violations.append("permission")
    violations += card_violations(request.get("model_card"))
    return sorted(violations)


def register_if_allowed(client: MlflowClient, request: dict, source: str) -> tuple[str | None, list[str]]:
    violations = check_request(request)
    if violations:
        return None, violations
    name = request["name"]
    tags = {k: str(request["tags"][k]).strip() for k in REQUIRED_TAGS}
    if not client.search_registered_models(filter_string=f"name = '{name}'"):
        client.create_registered_model(name, tags=tags)
    version = client.create_model_version(name, source, tags=tags, description=request["model_card"])
    return str(version.version), []


def audit_registry(client: MlflowClient) -> dict[str, list[str]]:
    report = {}
    for version in client.search_model_versions():
        found = check_request({"name": version.name, "tags": version.tags, "model_card": version.description})
        if found:
            report[f"{version.name}/{version.version}"] = found
    return report

import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
import yaml

import testkit
from testkit import DockerLab, Exercise

ex = Exercise(__file__)
FIXTURES = Path(__file__).parent / "fixtures"
SEVERITIES = {"page", "ticket", "none"}
CAUSE = re.compile(r"cpu|memory|mem_|disk|filesystem|node_|load\d", re.I)
KEYWORDS = {
    1: (("triệu chứng", "symptom"), ("hành động", "actionable", "runbook")),
    3: (("group_by", "gộp"), ("inhibit",), ("watchdog", "deadman", "dead man")),
    4: (("leo thang", "escalat"), ("bàn giao", "handoff", "hand-off"), ("lịch", "rotation", "luân phiên")),
    5: (("page",), ("tuần", "tháng"), ("actionable", "hành động được", "nhiễu", "noise")),
}
MIN_BULLETS = {1: 3, 3: 3, 4: 4, 5: 3, 6: 3}
COLUMNS = ["alert", "service", "tín hiệu", "severity", "receiver", "runbook"]


def section(doc: str, number: int) -> str:
    match = re.search(rf"^## {number}\..*?$(.*?)(?=^## |\Z)", doc, re.M | re.S)
    return match.group(1) if match else ""


def bullets(text: str) -> list[str]:
    return [m.group(1).strip() for m in re.finditer(r"^\s*(?:-|\d+\.)\s+(.+)$", text, re.M)]


def split_row(line: str) -> list[str]:
    return [cell.strip().strip("`").strip() for cell in re.split(r"(?<!\\)\|", line.strip().strip("|"))]


def catalog(doc: str) -> tuple[list[str], list[dict]]:
    lines = [line for line in section(doc, 2).splitlines() if line.strip().startswith("|")]
    if len(lines) < 2:
        return [], []
    header = [cell.lower() for cell in split_row(lines[0])]
    rows = [dict(zip(header, split_row(line))) for line in lines[2:]]
    return header, rows


def doc_problems(doc: str) -> list[str]:
    found = ["Còn TODO"] if "TODO" in doc else []
    for number in range(1, 7):
        if not re.search(rf"^## {number}\. ", doc, re.M):
            found.append(f"Thiếu phần '## {number}.'")
    header, rows = catalog(doc)
    if header[:len(COLUMNS)] != COLUMNS:
        found.append(f"Phần 2: bảng cần đúng các cột {COLUMNS}")
        rows = []
    elif len(rows) < 6:
        found.append(f"Phần 2: cần ít nhất 6 alert trong bảng, có {len(rows)}")
    names = [r.get("alert", "") for r in rows]
    if len(set(names)) != len(names):
        found.append("Phần 2: tên alert bị trùng")
    for row in rows:
        name, severity = row.get("alert", ""), row.get("severity", "")
        if severity not in SEVERITIES:
            found.append(f"Phần 2: {name} có severity '{severity}', chỉ dùng {sorted(SEVERITIES)}")
        if severity in ("page", "ticket") and not row.get("runbook", "").startswith("https://"):
            found.append(f"Phần 2: {name} cần runbook là link https://")
        if severity == "page" and CAUSE.search(row.get("tín hiệu", "")):
            found.append(f"Phần 2: {name} page dựa trên tài nguyên máy (nguyên nhân), không phải triệu chứng người dùng thấy")
    severities = [r.get("severity") for r in rows]
    if rows and (severities.count("page") < 2 or severities.count("ticket") < 2):
        found.append("Phần 2: cần ít nhất 2 alert page và 2 alert ticket")
    if rows and not any(r.get("alert") == "Watchdog" and r.get("severity") == "none" for r in rows):
        found.append("Phần 2: cần dòng Watchdog với severity none")
    if rows and not any(r.get("alert") == "OlistServiceDown" and r.get("severity") == "page" for r in rows):
        found.append("Phần 2: cần dòng OlistServiceDown với severity page")
    for number, minimum in MIN_BULLETS.items():
        if len(bullets(section(doc, number))) < minimum:
            found.append(f"Phần {number}: ít nhất {minimum} gạch đầu dòng")
    for number, groups in KEYWORDS.items():
        text = " ".join(section(doc, number).split()).lower()
        for group in groups:
            if not any(word in text for word in group):
                found.append(f"Phần {number}: chưa nói tới {' / '.join(group)}")
    return found


def test_design_document():
    found = doc_problems(ex.read("ALERTING.md"))
    assert not found, "\n".join(found)


def test_checks_catch_template():
    found = doc_problems((FIXTURES / "ALERTING.template.md").read_text(encoding="utf-8"))
    assert "Còn TODO" in found and any(f.startswith("Phần 2: cần ít nhất 6 alert") for f in found)


def test_checks_catch_weak_document():
    found = "\n".join(doc_problems((FIXTURES / "ALERTING.weak.md").read_text(encoding="utf-8")))
    for needle in ("page dựa trên tài nguyên máy", "cần runbook là link", "cần dòng Watchdog", "Phần 4: chưa nói tới leo thang",
                   "Phần 6: ít nhất 3"):
        assert needle in found, f"Không bắt được: {needle}\n{found}"


def test_good_document_passes():
    found = doc_problems((FIXTURES / "ALERTING.good.md").read_text(encoding="utf-8"))
    assert not found, "\n".join(found)


def config() -> dict:
    try:
        data = yaml.safe_load(ex.read("alertmanager.yml"))
    except yaml.YAMLError as error:
        pytest.fail(f"alertmanager.yml không phải YAML hợp lệ: {error}")
    assert isinstance(data, dict) and data.get("route"), "alertmanager.yml cần route"
    return data


def receiver_of(labels: dict) -> str:
    args = [f"{k}={v}" for k, v in labels.items()]
    result = testkit.amtool("config", "routes", "test", "--config.file=alertmanager.yml", *args, cwd=ex.target)
    assert result.returncode == 0, result.stdout + result.stderr
    return result.stdout.strip().splitlines()[0].strip() if result.stdout.strip() else ""


def test_config_valid():
    config()
    result = testkit.amtool("check-config", "alertmanager.yml", cwd=ex.target)
    assert result.returncode == 0, result.stdout + result.stderr


def test_routes_match_catalog():
    _, rows = catalog(ex.read("ALERTING.md"))
    assert rows, "Hoàn thiện bảng ở phần 2 của ALERTING.md trước"
    receivers = {r.get("name"): r for r in config().get("receivers") or []}
    wrong = []
    for row in rows:
        receiver = row.get("receiver", "")
        entry = receivers.get(receiver)
        if not entry or not any(k.endswith("_configs") and entry[k] for k in entry):
            wrong.append(f"{row.get('alert')}: receiver '{receiver}' không có trong alertmanager.yml hoặc không có *_configs")
            continue
        labels = {"alertname": row.get("alert"), "severity": row.get("severity")}
        if row.get("service") not in ("", "-"):
            labels["service"] = row["service"]
        got = receiver_of(labels)
        if got != receiver:
            wrong.append(f"{row.get('alert')}: bảng ghi receiver '{receiver}', Alertmanager định tuyến tới '{got}'")
    assert not wrong, "\n".join(wrong)


def test_unknown_severity_does_not_page():
    _, rows = catalog(ex.read("ALERTING.md"))
    pagers = {r.get("receiver") for r in rows if r.get("severity") == "page"}
    assert pagers, "Bảng phần 2 chưa có alert page"
    for labels in ({"alertname": "OlistSomethingNew", "service": "olist-api"},
                   {"alertname": "OlistSomethingNew", "service": "olist-api", "severity": "Page"}):
        got = receiver_of(labels)
        assert got and got not in pagers, f"Alert {labels} rơi vào receiver page '{got}': nhãn lạ không được đánh thức người"


def post_alerts(base: str, alerts: list[dict]) -> None:
    import httpx

    now = datetime.now(timezone.utc)
    body = [{"labels": labels, "annotations": {"summary": "test"},
             "startsAt": now.isoformat(), "endsAt": (now + timedelta(minutes=10)).isoformat()} for labels in alerts]
    with httpx.Client(trust_env=False, timeout=10) as client:
        response = client.post(base + "/api/v2/alerts", json=body)
    assert response.status_code == 200, response.text


def states(base: str) -> dict:
    import httpx

    with httpx.Client(trust_env=False, timeout=10) as client:
        alerts = client.get(base + "/api/v2/alerts").json()
    return {(a["labels"]["alertname"], a["labels"].get("service")): bool(a["status"]["inhibitedBy"]) for a in alerts}


def test_inhibition_in_real_alertmanager(tmp_path):
    config()
    image = testkit.OBS_IMAGES["alertmanager"]
    ex.require_image(image)
    down = {"alertname": "OlistServiceDown", "service": "olist-api", "severity": "page"}
    same = [{"alertname": "OlistApiHighErrorRate", "service": "olist-api", "severity": "page"},
            {"alertname": "OlistApiSlowOrders", "service": "olist-api", "severity": "ticket"}]
    other = [{"alertname": "OlistApiHighErrorRate", "service": "olist-worker", "severity": "page"},
             {"alertname": "OlistWorkerJobsFailing", "service": "olist-worker", "severity": "page"}]
    with DockerLab() as lab:
        lab.start("alertmanager", image, "--config.file=/etc/am/alertmanager.yml", "--storage.path=/alertmanager",
                  "--cluster.listen-address=", ports=[9093], mounts=[(ex.target, "/etc/am")])
        base = f"http://127.0.0.1:{lab.port('alertmanager', 9093)}"
        lab.wait_http("alertmanager", base + "/-/ready", timeout=60)
        post_alerts(base, [*same, *other])
        before = states(base)
        assert not any(before.values()), f"Khi chưa có OlistServiceDown, không alert nào được bị inhibit: {before}"
        post_alerts(base, [down])
        after = states(base)
        assert not after[("OlistServiceDown", "olist-api")], "OlistServiceDown không được tự inhibit chính nó"
        for labels in same:
            assert after[(labels["alertname"], "olist-api")], f"{labels['alertname']} của olist-api phải bị inhibit khi olist-api down"
        for labels in other:
            assert not after[(labels["alertname"], "olist-worker")], \
                f"{labels['alertname']} của olist-worker không được bị inhibit khi chỉ olist-api down"

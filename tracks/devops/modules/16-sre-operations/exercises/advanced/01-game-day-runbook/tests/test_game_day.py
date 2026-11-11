import re
import shutil
import threading
import time
from pathlib import Path

import pytest
import yaml

import testkit
from testkit import DockerLab, Exercise, FaultInjector, ObsStack

ex = Exercise(__file__)
FIXTURES = Path(__file__).parent / "fixtures"
APP = testkit.ROOT / "tracks" / "devops" / "sample-app"
SEEDS = [14, 18, 23, 24]
FAULT_SERVICES = ["api", "redis"]
ACTIONS = ("start", "restart", "recreate")
SERVICES = ("api", "worker", "postgres", "redis")
ID = re.compile(r"[a-z0-9]([-a-z0-9]{0,40}[a-z0-9])?")
SECTIONS = ("Triệu chứng", "Chẩn đoán", "Khôi phục", "Xác nhận", "Leo thang")
PM_SECTIONS = 7
TIME = re.compile(r"^\|\s*(\d{2}):(\d{2}):(\d{2})\s*\|")
DATE = re.compile(r"\b20\d{2}-\d{2}-\d{2}\b")
BLAME = ("lỗi của anh", "lỗi của chị", "lỗi của em", "cẩu thả", "bất cẩn", "sơ suất của", "đáng lẽ phải biết", "tại người trực")
LATENCY = 0.5
HEALTHY_WINDOW = 10
DETECT_TIMEOUT = 120
RECOVER_TIMEOUT = 120


def flat(text: str) -> str:
    return " ".join(text.split())


def runbook_problems(data) -> list[str]:
    if not isinstance(data, dict) or not isinstance(data.get("entries"), list):
        return ["runbook.yaml phải có khoá entries là danh sách"]
    entries = data["entries"]
    found = [] if 2 <= len(entries) <= 10 else [f"runbook.yaml cần 2 tới 10 entry, có {len(entries)}"]
    seen = set()
    for index, entry in enumerate(entries, 1):
        where = f"entry {index}"
        if not isinstance(entry, dict) or set(entry) != {"id", "detect", "action"}:
            found.append(f"{where}: cần đúng ba khoá id, detect, action")
            continue
        if not isinstance(entry["id"], str) or not ID.fullmatch(entry["id"]) or entry["id"] in seen:
            found.append(f"{where}: id {entry['id']!r} phải là chữ thường, số, '-', không trùng")
        seen.add(entry["id"])
        detect = entry["detect"]
        if not isinstance(detect, dict) or len(detect) != 1 or not set(detect) <= {"promql", "logql"}:
            found.append(f"{where}: detect cần đúng một khoá promql hoặc logql")
        else:
            (kind, query), = detect.items()
            if not isinstance(query, str) or not query.strip() or "TODO" in query:
                found.append(f"{where}: detect.{kind} còn trống")
            elif kind == "logql" and not query.strip().startswith("{"):
                found.append(f"{where}: detect.logql phải là log query bắt đầu bằng {{...}}")
        action = entry["action"]
        if not isinstance(action, dict) or set(action) != {"do", "service"}:
            found.append(f"{where}: action cần đúng hai khoá do, service")
        elif action["do"] not in ACTIONS or action["service"] not in SERVICES:
            found.append(f"{where}: action.do thuộc {ACTIONS}, action.service thuộc {SERVICES}")
    return found


def load_runbook() -> list[dict]:
    try:
        data = yaml.safe_load(ex.read("runbook.yaml"))
    except yaml.YAMLError as error:
        pytest.fail(f"runbook.yaml không phải YAML hợp lệ: {error}")
    problems = runbook_problems(data)
    assert not problems, "\n".join(problems)
    return data["entries"]


def section(doc: str, pattern: str, level: int = 2) -> str:
    marks = "#" * level
    match = re.search(rf"^{marks} {pattern}\s*$(.*?)(?=^#{{1,{level}}} |\Z)", doc, re.M | re.S)
    return match.group(1) if match else ""


def runbook_md_problems(doc: str, entries: list[dict]) -> list[str]:
    found = ["Còn TODO"] if "TODO" in doc else []
    for entry in entries:
        body = section(doc, re.escape(entry["id"]))
        if not body.strip():
            found.append(f"Thiếu phần '## {entry['id']}'")
            continue
        for name in SECTIONS:
            text = section(body, re.escape(name), 3)
            if len(flat(text)) < 40:
                found.append(f"{entry['id']}: phần '### {name}' thiếu hoặc quá ngắn (ít nhất 40 ký tự)")
        query = next(iter(entry["detect"].values()))
        if flat(query) not in flat(section(body, re.escape("Chẩn đoán"), 3)):
            found.append(f"{entry['id']}: phần Chẩn đoán phải chép nguyên truy vấn detect của entry")
        recover = section(body, re.escape("Khôi phục"), 3)
        if entry["action"]["service"] not in recover or entry["action"]["do"] not in recover:
            found.append(f"{entry['id']}: phần Khôi phục phải nêu hành động {entry['action']['do']} {entry['action']['service']}")
    return found


def bullets(text: str) -> list[str]:
    return [m.group(1) for m in re.finditer(r"^\s*(?:-|\d+\.)\s+(.+)$", text, re.M)]


def table_rows(text: str) -> list[list[str]]:
    rows = [line for line in text.splitlines() if line.strip().startswith("|")]
    return [[cell.strip() for cell in row.strip().strip("|").split("|")] for row in rows[2:]]


def prose(text: str) -> str:
    return "\n".join(line for line in text.splitlines() if not line.strip().startswith(("|", "```", "-", "#"))).strip()


def pm_section(doc: str, number: int) -> str:
    match = re.search(rf"^## {number}\..*?$(.*?)(?=^## |\Z)", doc, re.M | re.S)
    return match.group(1) if match else ""


def postmortem_problems(doc: str, entry_ids: set[str]) -> list[str]:
    found = ["Còn TODO"] if "TODO" in doc else []
    for number in range(1, PM_SECTIONS + 1):
        if not re.search(rf"^## {number}\. ", doc, re.M):
            found.append(f"Thiếu phần '## {number}.'")
    if len(prose(pm_section(doc, 1))) < 200:
        found.append("Phần 1: tóm tắt cần ít nhất 200 ký tự văn xuôi")
    if not re.search(r"\bseed\s*\d+", pm_section(doc, 1), re.I):
        found.append("Phần 1: ghi seed của lần game day")
    impact = flat(pm_section(doc, 2)).lower()
    if not ("budget" in impact and re.search(r"\d", impact)):
        found.append("Phần 2: tác động cần số liệu và phần error budget đã tiêu")
    times = [tuple(map(int, m.groups())) for line in pm_section(doc, 3).splitlines() if (m := TIME.match(line.strip()))]
    if len(times) < 5:
        found.append(f"Phần 3: timeline cần ít nhất 5 dòng bảng bắt đầu bằng giờ HH:MM:SS, có {len(times)}")
    elif times != sorted(times):
        found.append("Phần 3: timeline phải theo thứ tự thời gian")
    if len(bullets(pm_section(doc, 4))) < 2:
        found.append("Phần 4: nguyên nhân cần ít nhất 2 gạch đầu dòng")
    if not any(f"`{i}`" in pm_section(doc, 5) for i in entry_ids):
        found.append("Phần 5: nêu entry nào của runbook.yaml đã phát hiện sự cố (viết id trong dấu `)")
    if len(bullets(pm_section(doc, 6))) < 3:
        found.append("Phần 6: bài học cần ít nhất 3 gạch đầu dòng")
    actions = table_rows(pm_section(doc, 7))
    if len(actions) < 3:
        found.append(f"Phần 7: cần ít nhất 3 action item trong bảng, có {len(actions)}")
    elif not all(len(row) >= 3 and row[1] and DATE.search(" ".join(row)) for row in actions):
        found.append("Phần 7: mỗi action item cần người phụ trách (cột 2) và hạn dạng YYYY-MM-DD")
    lowered = doc.lower()
    blamed = [phrase for phrase in BLAME if phrase in lowered]
    if blamed:
        found.append(f"Postmortem không đổ lỗi cho người: bỏ cụm {', '.join(blamed)}")
    return found


def test_runbook_yaml():
    load_runbook()


def test_runbook_md_sections():
    found = runbook_md_problems(ex.read("RUNBOOK.md"), load_runbook())
    assert not found, "\n".join(found)


def test_postmortem():
    found = postmortem_problems(ex.read("POSTMORTEM.md"), {e["id"] for e in load_runbook()})
    assert not found, "\n".join(found)


def test_runbook_checks_catch_bad_files():
    data = yaml.safe_load((FIXTURES / "runbook.bad.yaml").read_text(encoding="utf-8"))
    found = "\n".join(runbook_problems(data))
    for needle in ("entry 1: id", "entry 2: detect cần đúng một khoá", "entry 3: action.do", "entry 4: detect.logql",
                   "entry 5: cần đúng ba khoá"):
        assert needle in found, f"Không bắt được: {needle}\n{found}"
    assert runbook_problems({"entries": []}) and runbook_problems(["x"])


def test_runbook_md_checks_catch_weak_file():
    entries = yaml.safe_load((FIXTURES / "runbook.good.yaml").read_text(encoding="utf-8"))["entries"]
    good = (FIXTURES / "RUNBOOK.good.md").read_text(encoding="utf-8")
    assert runbook_md_problems(good, entries) == []
    found = "\n".join(runbook_md_problems((FIXTURES / "RUNBOOK.weak.md").read_text(encoding="utf-8"), entries))
    for needle in ("Thiếu phần '## db-down'", "phần '### Leo thang' thiếu", "Chẩn đoán phải chép nguyên", "Khôi phục phải nêu"):
        assert needle in found, f"Không bắt được: {needle}\n{found}"


def test_postmortem_checks_catch_template_and_weak():
    ids = {"db-down", "api-slow"}
    template = "\n".join(postmortem_problems((FIXTURES / "POSTMORTEM.template.md").read_text(encoding="utf-8"), ids))
    assert "Còn TODO" in template and "Phần 3: timeline cần" in template
    weak = "\n".join(postmortem_problems((FIXTURES / "POSTMORTEM.weak.md").read_text(encoding="utf-8"), ids))
    for needle in ("Phần 1: ghi seed", "Phần 3: timeline phải theo thứ tự", "Phần 5: nêu entry", "Phần 7: mỗi action item",
                   "không đổ lỗi"):
        assert needle in weak, f"Không bắt được: {needle}\n{weak}"
    assert postmortem_problems((FIXTURES / "POSTMORTEM.good.md").read_text(encoding="utf-8"), ids) == []


class Traffic(threading.Thread):
    """Khách giả: tra đơn, gọi /readyz, thỉnh thoảng đẩy job; ghi (thời điểm, loại, đạt) cho từng request."""

    def __init__(self, base: str) -> None:
        super().__init__(daemon=True)
        self.base = base
        self.samples: list[tuple[float, str, bool]] = []
        self.stopping = threading.Event()

    def probe(self, client, kind: str, method: str, path: str, ok_status: tuple[int, ...]) -> None:
        import httpx

        start = time.monotonic()
        try:
            response = client.request(method, self.base + path)
            ok = response.status_code in ok_status and time.monotonic() - start < LATENCY
        except httpx.HTTPError:
            ok = False
        self.samples.append((time.monotonic(), kind, ok))

    def run(self) -> None:
        import httpx

        with httpx.Client(trust_env=False, timeout=3) as client:
            turn = 0
            while not self.stopping.is_set():
                self.probe(client, "orders", "GET", f"/orders/gd-{turn % 50:03d}", (200, 404))
                self.probe(client, "readyz", "GET", "/readyz", (200,))
                if turn % 4 == 0:
                    self.probe(client, "jobs", "POST", "/jobs/recompute", (202,))
                turn += 1
                self.stopping.wait(0.2)

    def healthy(self, since: float) -> bool:
        now = time.monotonic()
        start = max(since, now - HEALTHY_WINDOW)
        if now - since < HEALTHY_WINDOW:
            return False
        recent = [s for s in list(self.samples) if s[0] >= start]
        kinds = {kind: [ok for _, k, ok in recent if k == kind] for kind in ("orders", "readyz", "jobs")}
        return len(kinds["orders"]) >= 8 and len(kinds["readyz"]) >= 5 and len(kinds["jobs"]) >= 1 and all(
            all(values) for values in kinds.values())

    def wait_healthy(self, since: float, timeout: float) -> float | None:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if self.healthy(since):
                return time.monotonic()
            time.sleep(1)
        return None


def olist_project(tmp_path: Path) -> Path:
    project = tmp_path / "project"
    shutil.copytree(APP / "olist_shop", project / "olist_shop", ignore=shutil.ignore_patterns("__pycache__"))
    shutil.copy(APP / "requirements.txt", project)
    shutil.copy(testkit.KUBE_OLIST_DOCKERFILE, project / "Dockerfile")
    shutil.copy(FIXTURES / "compose.yaml", project / "compose.yaml")
    return project


def matched(stack: ObsStack, entry: dict, since: float) -> bool:
    (kind, query), = entry["detect"].items()
    if kind == "promql":
        return bool(stack.prom_query(query))
    return bool(stack.loki_query(query, since=max(since, 5), limit=1))


def act(project, action: dict) -> None:
    service = action["service"]
    if action["do"] == "recreate":
        result = project.run("up", "-d", "--no-deps", "--force-recreate", "--no-build", "--pull", "never", service, timeout=180)
    else:
        result = project.run(action["do"], service, timeout=180)
    assert result.returncode == 0, f"docker compose {action['do']} {service} lỗi: {result.stderr.strip()[-2000:]}"


@pytest.mark.parametrize("seed", SEEDS, ids=[f"seed-{s}" for s in SEEDS])
def test_game_day(seed, tmp_path):
    entries = load_runbook()
    for image in (testkit.KUBE_IMAGES["postgres"], testkit.KUBE_IMAGES["redis"], "python:3.12.16-slim-trixie"):
        ex.require_image(image)
    ex.require_image(testkit.FAULT_NETEM_IMAGE, f"Build image tc của FaultInjector bằng: {testkit.FAULT_NETEM_BUILD}")
    with DockerLab() as lab:
        stack = ObsStack(lab, project=olist_project(tmp_path))
        traffic = Traffic(f"http://127.0.0.1:{stack.project.port('api', 8000)}")
        started = time.monotonic()
        traffic.start()
        try:
            assert traffic.wait_healthy(started, 90), "Olist Shop chưa ổn định trước game day (lỗi môi trường, không phải runbook)"
            time.sleep(10)
            noisy = [e["id"] for e in entries if matched(stack, e, time.monotonic() - started)]
            assert not noisy, f"Entry {', '.join(noisy)} khớp khi hệ thống đang khoẻ: detect phải im lặng ở trạng thái bình thường"
            with FaultInjector(lab, seed=seed, services=FAULT_SERVICES) as injector:
                code = injector.inject()
                injected = time.monotonic()
                hit = None
                while hit is None and time.monotonic() - injected < DETECT_TIMEOUT:
                    time.sleep(2)
                    hit = next((e for e in entries if matched(stack, e, time.monotonic() - injected)), None)
                assert hit is not None, f"Seed {seed}: không entry nào trong runbook.yaml phát hiện sự cố sau {DETECT_TIMEOUT} giây"
                detected = time.monotonic()
                assert any(not ok for at, _, ok in list(traffic.samples) if at >= injected), \
                    f"Seed {seed}: chưa thấy request nào hỏng sau khi bơm lỗi (lỗi môi trường, không phải runbook)"
                act(stack.project, hit["action"])
                acted = time.monotonic()
                recovered = traffic.wait_healthy(acted, RECOVER_TIMEOUT)
                assert recovered is not None, (f"Seed {seed}: hệ thống chưa khôi phục sau hành động của entry '{hit['id']}' "
                                               f"({hit['action']['do']} {hit['action']['service']}) trong {RECOVER_TIMEOUT} giây")
                print(f"\nGame day seed {seed}: lỗi {code} vào {injector.resource}; entry '{hit['id']}' phát hiện sau "
                      f"{detected - injected:.0f} giây; khôi phục sau {recovered - acted:.0f} giây kể từ hành động")
        finally:
            traffic.stopping.set()
            traffic.join(10)
    assert testkit.docker_leftovers(lab.id) == []

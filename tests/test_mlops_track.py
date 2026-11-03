"""Validator nội dung track MLOps: track.json, README, module, bài tập, test không gọi docker trần."""

import json
import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
TRACK = ROOT / "tracks" / "mlops"
MODULES_DIR = TRACK / "modules"

MODULE_IDS = [
    "00-introduction",
    "01-engineering-foundations",
    "02-containers-for-ml",
    "03-data-versioning-quality",
    "04-tracking-registry",
    "05-training-pipelines",
    "06-feature-stores",
    "07-model-serving",
    "08-cicd-for-ml",
    "09-monitoring-observability",
    "10-drift-incidents",
    "11-deep-learning-serving",
    "12-ml-platform-governance",
    "13-kubernetes-for-ml",
    "14-kubernetes-ml-production",
    "15-distributed-training",
    "16-streaming-realtime-ml",
    "17-ml-platform-security",
    "18-senior-system-design",
]
MILESTONE_AFTER = {
    "m01": "01-engineering-foundations",
    "m02": "02-containers-for-ml",
    "m03": "03-data-versioning-quality",
    "m04": "04-tracking-registry",
    "m05": "05-training-pipelines",
    "m06": "06-feature-stores",
    "m07": "07-model-serving",
    "m08": "08-cicd-for-ml",
    "m09": "09-monitoring-observability",
    "m10": "10-drift-incidents",
    "m11": "12-ml-platform-governance",
    "m12": "13-kubernetes-for-ml",
    "m13": "13-kubernetes-for-ml",
    "m14": "14-kubernetes-ml-production",
    "m15": "15-distributed-training",
    "m16": "16-streaming-realtime-ml",
    "m17": "17-ml-platform-security",
    "m18": "18-senior-system-design",
}
PHASE1_MODULES = MODULE_IDS[:5]
PHASE1_MILESTONES = ["m01", "m02", "m03", "m04"]
NO_BASIC_MINIMUM = {"00-introduction"}

LEVELS = ("basic", "intermediate", "advanced")
EXERCISE_HEADINGS = ["Mục tiêu", "Đề bài", "Tiêu chí đạt", "Gợi ý"]
MILESTONE_HEADINGS = ["Mục tiêu", "Việc cần làm", "Kết quả nộp", "Tiêu chí đạt"]
INSTALL_HEADING = "0. Cài đặt"
REFERENCES = re.compile(r"^\d+\.\s+Tài liệu tham khảo$")
SLUG = re.compile(r"^\d{2}-[a-z0-9]+(?:-[a-z0-9]+)*$")
FENCE = re.compile(r"^(```|~~~)")
H2 = re.compile(r"^## (?!#)(.+)$")
FRONTMATTER = re.compile(r"^---\n([\s\S]*?)\n---\n?")
CURL_SUDO = re.compile(r"\b(?:curl|wget)\b.*\|\s*sudo\b(?:\s+-\S+)*\s+(?:ba|z|da)?sh\b")
IGNORED_PARTS = {"__pycache__", ".pytest_cache"}


def h2_titles(text: str) -> list[str]:
    titles = []
    in_fence = False
    for line in text.replace("\r\n", "\n").split("\n"):
        if FENCE.match(line.strip()):
            in_fence = not in_fence
            continue
        match = None if in_fence else H2.match(line)
        if match:
            titles.append(match.group(1).strip())
    return titles


def mermaid_blocks(text: str) -> int:
    return sum(1 for line in text.splitlines() if line.strip() == "```mermaid")


def split_frontmatter(text: str) -> tuple[dict | None, str]:
    text = text.replace("\r\n", "\n")
    match = FRONTMATTER.match(text)
    if not match:
        return None, text
    try:
        data = yaml.safe_load(match.group(1))
    except yaml.YAMLError:
        return None, text[match.end():]
    return (data if isinstance(data, dict) else None), text[match.end():]


def visible_files(folder: Path) -> list[Path]:
    return sorted(
        p.relative_to(folder)
        for p in folder.rglob("*")
        if p.is_file() and not IGNORED_PARTS & set(p.parts) and p.suffix != ".pyc"
    )


def check_module_readme(path: Path) -> list[str]:
    if not path.is_file():
        return [f"{path}: thiếu README.md"]
    text = path.read_text(encoding="utf-8")
    errors = []
    if not text.startswith("# "):
        errors.append(f"{path}: dòng đầu phải là '# Tên module'")
    titles = h2_titles(text)
    if INSTALL_HEADING in titles[1:]:
        errors.append(f"{path}: '## {INSTALL_HEADING}' phải là phần đầu tiên")
    sections = [t for t in titles if t != INSTALL_HEADING]
    if not 5 <= len(sections) <= 8:
        errors.append(f"{path}: có {len(sections)} phần '## ' (không tính Cài đặt), cần 5–8")
    if mermaid_blocks(text) < 2:
        errors.append(f"{path}: cần ít nhất 2 khối mermaid, có {mermaid_blocks(text)}")
    if not sections or not REFERENCES.match(sections[-1]):
        errors.append(f"{path}: phần cuối phải là '## N. Tài liệu tham khảo'")
    return errors


def check_interview(path: Path) -> list[str]:
    if not path.is_file():
        return [f"{path}: thiếu interview.md"]
    text = path.read_text(encoding="utf-8")
    errors = []
    if not text.startswith("# "):
        errors.append(f"{path}: dòng đầu phải là '# Câu hỏi phỏng vấn: ...'")
    count = len(h2_titles(text))
    if count < 12:
        errors.append(f"{path}: có {count} câu hỏi, cần ít nhất 12")
    return errors


def check_exercise(ex_dir: Path) -> list[str]:
    level = ex_dir.parent.name
    readme = ex_dir / "README.md"
    if not SLUG.match(ex_dir.name):
        return [f"{ex_dir}: tên thư mục bài phải dạng NN-slug"]
    if not readme.is_file():
        return [f"{ex_dir}: thiếu README.md"]
    data, body = split_frontmatter(readme.read_text(encoding="utf-8"))
    if data is None:
        return [f"{readme}: thiếu frontmatter YAML hợp lệ"]
    errors = []
    for key in ("title", "level", "files", "run"):
        if key not in data:
            errors.append(f"{readme}: frontmatter thiếu '{key}'")
    if "level" in data and data["level"] != level:
        errors.append(f"{readme}: level '{data['level']}' không khớp thư mục '{level}'")
    if "run" in data and not isinstance(data["run"], list):
        errors.append(f"{readme}: 'run' phải là danh sách")
    files = data.get("files")
    if "files" in data and not isinstance(files, list):
        errors.append(f"{readme}: 'files' phải là danh sách")
        files = []
    for item in files or []:
        rel = item if isinstance(item, str) else item.get("path") if isinstance(item, dict) else None
        if not rel:
            errors.append(f"{readme}: mục files thiếu 'path'")
        elif not (ex_dir / rel).exists():
            errors.append(f"{readme}: files có '{rel}' nhưng tệp không tồn tại")
    titles = h2_titles(body)
    if titles != EXERCISE_HEADINGS:
        errors.append(f"{readme}: heading '## ' phải đúng {EXERCISE_HEADINGS}, đang là {titles}")
    solution = ex_dir.parents[2] / "solutions" / level / ex_dir.name
    if not (solution / "SOLUTION.md").is_file():
        errors.append(f"{solution}: thiếu SOLUTION.md")
    if level in ("basic", "intermediate") and (ex_dir / "starter").is_dir():
        for rel in visible_files(ex_dir / "starter"):
            if not (solution / rel).is_file():
                errors.append(f"{solution}: thiếu lời giải trùng tên starter/{rel.as_posix()}")
    if (ex_dir / "quiz.yaml").is_file() and not (solution / "quiz-answers.yaml").is_file():
        errors.append(f"{solution}: có quiz.yaml nhưng thiếu quiz-answers.yaml")
    return errors


def exercise_dirs(module_dir: Path) -> list[Path]:
    root = module_dir / "exercises"
    if not root.is_dir():
        return []
    return sorted(d for level in root.iterdir() if level.is_dir() for d in level.iterdir() if d.is_dir())


def check_exercise_layout(module_dir: Path) -> list[str]:
    root = module_dir / "exercises"
    if not root.is_dir():
        return [f"{module_dir}: thiếu exercises/"]
    errors = [f"{p}: mức không hợp lệ, chỉ có {LEVELS}" for p in sorted(root.iterdir()) if p.name not in LEVELS]
    counts = {level: len([d for d in (root / level).iterdir() if d.is_dir()]) if (root / level).is_dir() else 0 for level in LEVELS}
    total = sum(counts.values())
    if not 4 <= total <= 9:
        errors.append(f"{module_dir}: có {total} bài, cần 4–9")
    if counts["basic"] < 3 and module_dir.name not in NO_BASIC_MINIMUM:
        errors.append(f"{module_dir}: có {counts['basic']} bài basic, cần ít nhất 3")
    if counts["advanced"] < 2:
        errors.append(f"{module_dir}: có {counts['advanced']} bài advanced, cần ít nhất 2")
    return errors


DIRECT_DOCKER = re.compile(
    r"""\b_docker\s*\(|[\[(]\s*["']docker["']\s*,|\b(?:subprocess\.\w+|os\.system|os\.popen|Popen)\s*\(\s*f?["']docker\s"""
)


def check_docker_via_lab(path: Path) -> list[str]:
    """Test bài tập và capstone chỉ được dùng Docker qua mlopskit hoặc testkit.DockerLab (nhãn, tiền tố, dọn dẹp)."""
    return [
        f"{path}:{n}: gọi docker trực tiếp; dùng mlopskit hoặc testkit.DockerLab"
        for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1)
        if DIRECT_DOCKER.search(line)
    ]


def check_no_curl_sudo(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8").replace("\\\n", " ")
    return [
        f"{path}:{n}: không hướng dẫn cài bằng curl ... | sudo sh"
        for n, line in enumerate(text.splitlines(), 1)
        if CURL_SUDO.search(line)
    ]


def check_milestone_doc(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8")
    errors = []
    if not text.startswith("# "):
        errors.append(f"{path}: dòng đầu phải là '# Tiêu đề'")
    titles = h2_titles(text)
    missing = [h for h in MILESTONE_HEADINGS if h not in titles]
    if missing:
        errors.append(f"{path}: thiếu phần {missing}")
    return errors


def check_track_json(data: dict) -> list[str]:
    errors = []
    expected = {"id": "mlops", "name": "MLOps", "icon": "workflow", "status": "active", "order": 6, "source": "https://roadmap.sh/mlops"}
    for key, value in expected.items():
        if data.get(key) != value:
            errors.append(f"track.json: '{key}' phải là {value!r}, đang là {data.get(key)!r}")
    if not data.get("description"):
        errors.append("track.json: thiếu description")
    modules = data.get("modules") or []
    ids = [m.get("id") for m in modules]
    if ids != MODULE_IDS:
        errors.append(f"track.json: module ids phải đúng thứ tự {MODULE_IDS}, đang là {ids}")
    for module in modules:
        if not module.get("title") or not module.get("summary") or not module.get("topics"):
            errors.append(f"track.json: module {module.get('id')} thiếu title, summary hoặc topics")
    capstone = data.get("capstone") or {}
    if capstone.get("readme") != "capstone/README.md" or not capstone.get("title"):
        errors.append("track.json: capstone cần title và readme 'capstone/README.md'")
    milestones = capstone.get("milestones") or []
    if [m.get("id") for m in milestones] != list(MILESTONE_AFTER):
        errors.append(f"track.json: milestones phải là {list(MILESTONE_AFTER)}")
    for m in milestones:
        mid = m.get("id")
        if mid in MILESTONE_AFTER and m.get("after") != MILESTONE_AFTER[mid]:
            errors.append(f"track.json: {mid} phải after {MILESTONE_AFTER[mid]}, đang là {m.get('after')}")
        if not m.get("title") or not re.fullmatch(rf"capstone/milestones/{mid}-[a-z0-9-]+\.md", str(m.get("doc"))):
            errors.append(f"track.json: {mid} cần title và doc 'capstone/milestones/{mid}-<slug>.md'")
    return errors


def load_track() -> dict:
    return json.loads((TRACK / "track.json").read_text(encoding="utf-8"))


def modules_on_disk() -> list[Path]:
    if not MODULES_DIR.is_dir():
        return []
    return sorted(d for d in MODULES_DIR.iterdir() if d.is_dir())


def assert_clean(errors: list[str]) -> None:
    assert not errors, "\n".join(errors)


def test_track_json_declaration():
    assert_clean(check_track_json(load_track()))


def test_track_readme():
    text = (TRACK / "README.md").read_text(encoding="utf-8")
    assert text.startswith("# ")
    assert mermaid_blocks(text) >= 2
    for module_id in MODULE_IDS:
        assert module_id in text, module_id


def test_capstone_readme():
    text = (TRACK / "capstone" / "README.md").read_text(encoding="utf-8")
    assert text.startswith("# ")
    assert mermaid_blocks(text) >= 1
    assert "capstone/project/tests" in text
    assert "SOLUTION=1" in text
    for milestone in MILESTONE_AFTER:
        assert milestone.upper() in text, milestone


def test_module_dirs_are_declared():
    assert_clean([f"{d}: không có trong track.json" for d in modules_on_disk() if d.name not in MODULE_IDS])


def test_module_readmes():
    assert_clean([e for d in modules_on_disk() for e in check_module_readme(d / "README.md")])


def test_module_interviews():
    assert_clean([e for d in modules_on_disk() for e in check_interview(d / "interview.md")])


def test_module_exercise_layout():
    assert_clean([e for d in modules_on_disk() for e in check_exercise_layout(d)])


def test_exercises():
    assert_clean([e for d in modules_on_disk() for ex in exercise_dirs(d) for e in check_exercise(ex)])


def test_docker_only_through_helpers():
    files = [p for p in TRACK.rglob("*.py") if "tests" in p.relative_to(TRACK).parts]
    assert_clean([e for p in files for e in check_docker_via_lab(p)])


def test_no_curl_pipe_sudo_in_markdown():
    assert_clean([e for p in TRACK.rglob("*.md") for e in check_no_curl_sudo(p)])


def test_milestone_docs_on_disk():
    docs = [TRACK / m["doc"] for m in load_track()["capstone"]["milestones"]]
    assert_clean([e for p in docs if p.is_file() for e in check_milestone_doc(p)])


def test_phase1_present():
    missing = [m for m in PHASE1_MODULES if not (MODULES_DIR / m).is_dir()]
    docs = {m["id"]: TRACK / m["doc"] for m in load_track()["capstone"]["milestones"]}
    missing += [docs[m].relative_to(ROOT).as_posix() for m in PHASE1_MILESTONES if not docs[m].is_file()]
    assert not missing, f"Phase 1 còn thiếu: {missing}"


README_OK = (
    "# Module\n\nMở đầu.\n\n## 0. Cài đặt\n\nx\n\n"
    + "".join(f"## {i}. Phần {i}\n\nNội dung.\n\n" for i in range(1, 5))
    + "```mermaid\nflowchart LR\n  a --> b\n```\n\n```mermaid\nflowchart LR\n  b --> c\n```\n\n"
    + "## 5. Tài liệu tham khảo\n\n- link\n"
)


def write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def test_h2_titles_ignores_fenced_code():
    text = "# T\n## A\n```bash\n## not a heading\n```\n~~~\n## nor this\n~~~\n## B\n### sub\n"
    assert h2_titles(text) == ["A", "B"]


def test_module_readme_valid(tmp_path):
    assert check_module_readme(write(tmp_path / "README.md", README_OK)) == []


def test_module_readme_missing(tmp_path):
    assert check_module_readme(tmp_path / "README.md")


def test_module_readme_first_line(tmp_path):
    errors = check_module_readme(write(tmp_path / "README.md", "Mở đầu\n" + README_OK))
    assert any("dòng đầu" in e for e in errors)


def test_module_readme_too_few_sections(tmp_path):
    text = README_OK.replace("## 4. Phần 4\n", "Phần 4\n")
    errors = check_module_readme(write(tmp_path / "README.md", text))
    assert any("có 4 phần" in e for e in errors)


def test_module_readme_install_not_counted(tmp_path):
    text = README_OK.replace("## 5. Tài liệu", "## 5. Thêm\n\n## 6. Thêm\n\n## 7. Thêm\n\n## 8. Tài liệu")
    assert check_module_readme(write(tmp_path / "README.md", text)) == []
    text = text.replace("## 0. Cài đặt", "## 0. Cài đặt khác")
    assert any("có 9 phần" in e for e in check_module_readme(write(tmp_path / "README.md", text)))


def test_module_readme_install_must_be_first(tmp_path):
    text = README_OK.replace("## 0. Cài đặt\n\nx\n\n", "").replace("## 5. Tài liệu", "## 0. Cài đặt\n\n## 5. Tài liệu")
    errors = check_module_readme(write(tmp_path / "README.md", text))
    assert any("phần đầu tiên" in e for e in errors)


def test_module_readme_needs_two_mermaid(tmp_path):
    text = README_OK.replace("```mermaid\nflowchart LR\n  b --> c\n```", "```text\nb\n```")
    errors = check_module_readme(write(tmp_path / "README.md", text))
    assert any("mermaid" in e for e in errors)


def test_module_readme_last_section_references(tmp_path):
    text = README_OK + "\n## 6. Phụ lục\n"
    errors = check_module_readme(write(tmp_path / "README.md", text))
    assert any("Tài liệu tham khảo" in e for e in errors)


def test_interview_counts_questions(tmp_path):
    good = "# Câu hỏi phỏng vấn: X\n\n" + "".join(f"## Câu {i}?\n\nĐáp.\n\n" for i in range(12))
    assert check_interview(write(tmp_path / "interview.md", good)) == []
    bad = good.replace("## Câu 11?", "Câu 11?")
    assert any("11 câu" in e for e in check_interview(write(tmp_path / "interview.md", bad)))
    assert check_interview(tmp_path / "missing.md")


EXERCISE_BODY = "\n## Mục tiêu\n\nx\n\n## Đề bài\n\nx\n\n## Tiêu chí đạt\n\n- x\n\n## Gợi ý\n\n### Gợi ý 1\n\nx\n"


def make_exercise(module: Path, level: str = "basic", slug: str = "01-demo", front: str | None = None, body: str = EXERCISE_BODY) -> Path:
    ex = module / "exercises" / level / slug
    sol = module / "solutions" / level / slug
    if front is None:
        front = f"title: Demo\nlevel: {level}\nservices: []\nfiles:\n  - path: starter/run.sh\n    note: 2 TODO\n  - path: tests/test_run.py\n    note: Không sửa\nrun:\n  - uv run pytest x -q\n"
    write(ex / "README.md", f"---\n{front}---\n{body}")
    write(ex / "starter" / "run.sh", "#!/usr/bin/env bash\n")
    write(ex / "tests" / "test_run.py", "def test_x():\n    pass\n")
    write(sol / "SOLUTION.md", "# Lời giải\n")
    write(sol / "run.sh", "#!/usr/bin/env bash\n")
    return ex


def test_exercise_valid(tmp_path):
    assert check_exercise(make_exercise(tmp_path)) == []


def test_exercise_ignores_pycache_in_starter(tmp_path):
    ex = make_exercise(tmp_path)
    write(ex / "starter" / "__pycache__" / "x.cpython-312.pyc", "")
    assert check_exercise(ex) == []


def test_exercise_bad_slug(tmp_path):
    ex = make_exercise(tmp_path, slug="demo")
    assert any("NN-slug" in e for e in check_exercise(ex))


def test_exercise_missing_frontmatter_keys(tmp_path):
    ex = make_exercise(tmp_path, front="title: Demo\nlevel: basic\n")
    errors = check_exercise(ex)
    assert any("thiếu 'files'" in e for e in errors)
    assert any("thiếu 'run'" in e for e in errors)


def test_exercise_no_frontmatter(tmp_path):
    ex = make_exercise(tmp_path)
    write(ex / "README.md", EXERCISE_BODY)
    assert any("frontmatter" in e for e in check_exercise(ex))


def test_exercise_level_mismatch(tmp_path):
    ex = make_exercise(tmp_path, level="intermediate", front="title: D\nlevel: basic\nfiles: []\nrun: []\n")
    assert any("không khớp" in e for e in check_exercise(ex))


def test_exercise_files_path_must_exist(tmp_path):
    ex = make_exercise(tmp_path)
    (ex / "starter" / "run.sh").unlink()
    assert any("starter/run.sh" in e and "không tồn tại" in e for e in check_exercise(ex))


def test_exercise_extra_heading(tmp_path):
    ex = make_exercise(tmp_path, body=EXERCISE_BODY + "\n## Bối cảnh\n\nx\n")
    assert any("heading" in e for e in check_exercise(ex))


def test_exercise_missing_heading(tmp_path):
    ex = make_exercise(tmp_path, body=EXERCISE_BODY.replace("## Gợi ý", "Gợi ý"))
    assert any("heading" in e for e in check_exercise(ex))


def test_exercise_basic_needs_solution_for_every_starter(tmp_path):
    ex = make_exercise(tmp_path)
    write(ex / "starter" / "conf" / "nginx.conf", "")
    errors = check_exercise(ex)
    assert any("starter/conf/nginx.conf" in e for e in errors)


def test_exercise_advanced_needs_solution_md_only(tmp_path):
    ex = make_exercise(tmp_path, level="advanced", front="title: D\nlevel: advanced\nfiles: []\nrun: []\n")
    sol = tmp_path / "solutions" / "advanced" / "01-demo"
    (sol / "run.sh").unlink()
    assert check_exercise(ex) == []
    (sol / "SOLUTION.md").unlink()
    assert any("SOLUTION.md" in e for e in check_exercise(ex))


def test_exercise_quiz_needs_answers(tmp_path):
    ex = make_exercise(tmp_path)
    write(ex / "quiz.yaml", "questions: []\n")
    assert any("quiz-answers.yaml" in e for e in check_exercise(ex))


def test_exercise_layout_counts(tmp_path):
    for i in range(3):
        make_exercise(tmp_path, "basic", f"0{i + 1}-b")
    make_exercise(tmp_path, "intermediate", "04-i")
    make_exercise(tmp_path, "advanced", "05-a")
    errors = check_exercise_layout(tmp_path)
    assert any("advanced" in e for e in errors)
    make_exercise(tmp_path, "advanced", "06-a")
    assert check_exercise_layout(tmp_path) == []
    for i in range(4):
        make_exercise(tmp_path, "intermediate", f"1{i}-i")
    assert any("có 10 bài" in e for e in check_exercise_layout(tmp_path))


def test_exercise_layout_basic_minimum_and_bad_level(tmp_path):
    for i, level in enumerate(["basic", "basic", "intermediate", "advanced", "advanced"]):
        make_exercise(tmp_path, level, f"0{i}-x")
    (tmp_path / "exercises" / "expert").mkdir()
    errors = check_exercise_layout(tmp_path)
    assert any("basic" in e for e in errors)
    assert any("expert" in e for e in errors)
    assert check_exercise_layout(tmp_path / "nothing")


def test_direct_docker_detection(tmp_path):
    bad = [
        'from testkit import _docker\nresult = _docker("run", "--rm", "nginx")\n',
        'subprocess.run(["docker", "run", "--rm", "nginx"])\n',
        "subprocess.run(('docker', 'ps', '-a'))\n",
        'subprocess.check_output("docker run --rm nginx", shell=True)\n',
        "os.system('docker rm -f x')\n",
        'testkit._docker ("ps")\n',
    ]
    for i, text in enumerate(bad):
        assert check_docker_via_lab(write(tmp_path / f"bad{i}.py", text)), text
    good = (
        'ex.require_tool("docker")\n'
        'with DockerLab() as lab:\n    lab.start("web", "nginx:1.30.6-alpine", ports=[80])\n'
        'shutil.which("docker")\n'
        '# docker run trong chú thích\n'
    )
    assert check_docker_via_lab(write(tmp_path / "good.py", good)) == []


def test_curl_pipe_sudo_detection(tmp_path):
    bad = [
        "curl -fsSL https://x.sh | sudo bash",
        "curl https://x | sudo sh",
        "wget -qO- https://x | sudo -E bash",
        "curl -fsSL https://x \\\n  | sudo bash",
    ]
    for i, line in enumerate(bad):
        assert check_no_curl_sudo(write(tmp_path / f"{i}.md", f"```bash\n{line}\n```\n")), line
    good = "curl -fLO https://x/tool.tar.gz\nsha256sum -c tool.sha256\ncurl -s localhost | jq .\nsudo bash -c 'x'\n"
    assert check_no_curl_sudo(write(tmp_path / "ok.md", good)) == []


def test_milestone_doc_sections(tmp_path):
    good = "# M01\n\n## Mục tiêu\n\n## Việc cần làm\n\n## Kết quả nộp\n\n## Tiêu chí đạt\n"
    assert check_milestone_doc(write(tmp_path / "m.md", good)) == []
    bad = good.replace("## Kết quả nộp\n", "")
    assert any("Kết quả nộp" in e for e in check_milestone_doc(write(tmp_path / "m.md", bad)))


def valid_track() -> dict:
    return {
        "id": "mlops",
        "name": "MLOps",
        "icon": "workflow",
        "status": "active",
        "order": 6,
        "source": "https://roadmap.sh/mlops",
        "description": "x",
        "modules": [{"id": m, "title": "t", "summary": "s", "topics": ["a"]} for m in MODULE_IDS],
        "capstone": {
            "title": "Dịch vụ ETA cho taxi NYC",
            "readme": "capstone/README.md",
            "milestones": [{"id": k, "title": "t", "after": v, "doc": f"capstone/milestones/{k}-x.md"} for k, v in MILESTONE_AFTER.items()],
        },
    }


def test_track_json_check_valid():
    assert check_track_json(valid_track()) == []


def test_track_json_check_catches_defects():
    data = valid_track()
    data["status"] = "soon"
    assert any("status" in e for e in check_track_json(data))
    data = valid_track()
    data["modules"][4]["id"] = "04-networking-dns"
    assert any("module ids" in e for e in check_track_json(data))
    data = valid_track()
    data["capstone"]["milestones"][4]["after"] = "08-cicd-for-ml"
    assert any("m05" in e for e in check_track_json(data))
    data = valid_track()
    data["capstone"]["milestones"][0]["doc"] = "capstone/milestones/m02-x.md"
    assert any("m01" in e for e in check_track_json(data))
    data = valid_track()
    del data["modules"][0]["topics"]
    assert any("00-introduction" in e for e in check_track_json(data))


def test_exercise_layout_module_00_exempt_from_basic_minimum(tmp_path):
    intro = tmp_path / "00-introduction"
    for i, level in enumerate(["basic", "intermediate", "advanced", "advanced"]):
        make_exercise(intro, level, f"0{i}-x")
    assert check_exercise_layout(intro) == []
    other = tmp_path / "01-engineering-foundations"
    for i, level in enumerate(["basic", "intermediate", "advanced", "advanced"]):
        make_exercise(other, level, f"0{i}-x")
    assert any("basic" in e for e in check_exercise_layout(other))


def test_exercise_layout_too_few(tmp_path):
    for i, level in enumerate(["basic", "advanced", "advanced"]):
        make_exercise(tmp_path, level, f"0{i}-x")
    assert any("có 3 bài" in e for e in check_exercise_layout(tmp_path))


def test_track_json_check_milestone_m11_m13_after():
    data = valid_track()
    assert data["capstone"]["milestones"][10]["after"] == "12-ml-platform-governance"
    assert data["capstone"]["milestones"][12]["after"] == "13-kubernetes-for-ml"
    data["capstone"]["milestones"][10]["after"] = "11-deep-learning-serving"
    assert any("m11" in e for e in check_track_json(data))

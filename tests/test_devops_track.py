"""Validator nội dung track DevOps: track.json, README, module, bài tập, test dùng Docker."""

import ast
import json
import re
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
TRACK = ROOT / "tracks" / "devops"
MODULES_DIR = TRACK / "modules"

MODULE_IDS = [
    "00-introduction",
    "01-linux-terminal",
    "02-scripting",
    "03-git-vcs-hosting",
    "04-networking-protocols",
    "05-web-server-proxy",
    "06-containers",
    "07-cicd-artifacts",
    "08-iac-provisioning",
    "09-config-management",
    "10-kubernetes-core",
    "11-kubernetes-production",
    "12-gitops-secrets",
    "13-observability",
    "14-cloud-serverless",
    "15-service-mesh-patterns",
    "16-sre-operations",
]
MILESTONE_AFTER = {
    "m01": "02-scripting",
    "m02": "05-web-server-proxy",
    "m03": "06-containers",
    "m04": "07-cicd-artifacts",
    "m05": "09-config-management",
    "m06": "11-kubernetes-production",
    "m07": "12-gitops-secrets",
    "m08": "13-observability",
    "m09": "16-sre-operations",
}
PHASE1_MODULES = MODULE_IDS[:6]
PHASE1_MILESTONES = ["m01", "m02"]

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
    if not 5 <= total <= 9:
        errors.append(f"{module_dir}: có {total} bài, cần 5–9")
    if counts["basic"] < 3:
        errors.append(f"{module_dir}: có {counts['basic']} bài basic, cần ít nhất 3")
    if counts["advanced"] < 2:
        errors.append(f"{module_dir}: có {counts['advanced']} bài advanced, cần ít nhất 2")
    return errors


TOOLS = ("docker", "kind", "act", "kubectl", "helm", "tofu")
SANDBOX_HELPERS = {"run_sandboxed", "sandbox_command"}
TESTKIT_HELPERS = SANDBOX_HELPERS | {"kind_node_exec", "kind_node_cp"}
SHELLS = {"sh", "bash", "dash", "zsh"}
WRAPPERS = {
    "nice": {"-n", "--adjustment"},
    "taskset": set(),
    "timeout": {"-s", "-k", "--signal", "--kill-after"},
    "env": {"-u", "-C", "--unset", "--chdir"},
    "sudo": {"-u", "-g", "-C", "-h", "-p", "-U", "-D"},
    "stdbuf": {"-i", "-o", "-e"},
    "ionice": {"-c", "-n", "-p", "-P", "-u"},
    "chrt": {"-T", "-P", "-D"},
}
SHELL_SEPARATORS = re.compile(r"[;&|()`\n]")
ASSIGNMENT = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=")
NUMERIC = re.compile(r"^[\d.,:\-]+[smhd]?$")


def call_name(node: ast.AST) -> str:
    func = node.func if isinstance(node, ast.Call) else node
    if isinstance(func, ast.Attribute):
        prefix = func.value.id if isinstance(func.value, ast.Name) else ""
        return f"{prefix}.{func.attr}" if prefix else func.attr
    return func.id if isinstance(func, ast.Name) else ""


def is_command_sink(node: ast.Call) -> bool:
    name = call_name(node)
    if name.split(".")[-1] in TESTKIT_HELPERS:
        return False
    if name.startswith(("subprocess.", "os.exec", "os.spawn", "asyncio.create_subprocess_")) or name in {"os.system", "os.popen"}:
        return True
    if isinstance(node.func, ast.Name):
        lowered = node.func.id.lower()
        return node.func.id == "Popen" or "run" in lowered or "exec" in lowered
    return False


def string_value(node: ast.AST) -> str | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.JoinedStr):
        return "".join(v.value if isinstance(v, ast.Constant) else "{}" for v in node.values)
    return None


def command_tool(words: list[str | None]) -> str | None:
    """Công cụ bị cấm mà argv `words` thực sự chạy, sau khi bỏ `VAR=x`, wrapper (nice, taskset, timeout, env, sudo,
    stdbuf, ionice, chrt) cùng tuỳ chọn của nó, và đi vào `sh/bash -<cờ>c "<script>"`. `None` trong `words` là giá trị
    không biết lúc tĩnh."""
    i = 0
    while i < len(words) and words[i] is not None and ASSIGNMENT.match(words[i]):
        i += 1
    while i < len(words) and words[i] is not None:
        name = Path(words[i]).name
        if name in TOOLS:
            return name
        if name in SHELLS:
            for j in range(i + 1, len(words)):
                flag = words[j]
                if flag is None or not flag.startswith("-"):
                    return None
                if not flag.startswith("--") and "c" in flag[1:]:
                    script = words[j + 1] if j + 1 < len(words) else None
                    return shell_tool(script) if script is not None else None
            return None
        if name not in WRAPPERS:
            return None
        options = WRAPPERS[name]
        i += 1
        while i < len(words) and words[i] is not None:
            word = words[i]
            if word.startswith("-"):
                i += 2 if word in options else 1
            elif ASSIGNMENT.match(word) or NUMERIC.match(word):
                i += 1
            else:
                break
    return None


def shell_tool(script: str) -> str | None:
    for segment in SHELL_SEPARATORS.split(script):
        tool = command_tool([word.strip("'\"") for word in segment.split()])
        if tool:
            return tool
    return None


def which_aliases(tree: ast.AST) -> dict[str, str]:
    names = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            tool = which_tool(node.value)
            if tool:
                names.update({t.id: tool for t in node.targets if isinstance(t, ast.Name)})
    return names


def which_tool(node: ast.AST) -> str | None:
    if isinstance(node, ast.Call) and call_name(node) == "shutil.which" and node.args:
        return string_value(node.args[0])
    return None


def assigned_values(tree: ast.AST) -> dict[str, list[ast.AST]]:
    values: dict[str, list[ast.AST]] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    values.setdefault(target.id, []).append(node.value)
    return values


def command_candidates(node: ast.AST, values: dict[str, list[ast.AST]], depth: int = 0) -> list[ast.AST]:
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
        return command_candidates(node.left, values, depth)
    if isinstance(node, ast.Name) and depth < 3:
        return [c for value in values.get(node.id, []) for c in command_candidates(value, values, depth + 1)]
    return [node]


def element_word(node: ast.AST, aliases: dict[str, str]) -> str | None:
    if isinstance(node, ast.Name):
        return aliases.get(node.id)
    return which_tool(node) or string_value(node)


def candidate_tool(node: ast.AST, aliases: dict[str, str]) -> str | None:
    if isinstance(node, (ast.List, ast.Tuple)):
        return command_tool([element_word(e, aliases) for e in node.elts])
    if isinstance(node, ast.Name) and node.id in aliases:
        return aliases[node.id]
    text = which_tool(node) or string_value(node)
    return shell_tool(text) if text is not None else None


def sink_argument(node: ast.Call) -> ast.AST | None:
    if node.args:
        return node.args[0]
    return next((kw.value for kw in node.keywords if kw.arg in {"args", "cmd"}), None)


def check_tool_calls(path: Path) -> list[str]:
    """Test của module và capstone không gọi docker, kind, act, kubectl, helm, tofu trực tiếp; đi qua helper của testkit
    (DockerLab, run_sandboxed, sandbox_command, act_run, TofuLab, AnsibleLab, KubeLab, kind_node_exec, kind_node_cp).

    Chỉ xét lệnh thực sự được chạy: tham số đầu (hoặc `args=`/`cmd=`) của một "điểm chạy lệnh": `subprocess.*`,
    `os.system`, `os.popen`, `os.exec*`, `os.spawn*`, `asyncio.create_subprocess_*`, `Popen`, hay hàm cục bộ gọi trần
    có tên chứa `run`/`exec`. Tham số đó là list/tuple, chuỗi (kể cả f-string), `shutil.which(...)`, hoặc biến gán từ
    các thứ đó (`["docker"] + extra` lấy vế trái). Lệnh bị bắt khi, sau khi bỏ `VAR=x` và wrapper (nice, taskset,
    timeout, env, sudo, stdbuf, ionice, chrt) cùng tuỳ chọn, phần tử đầu có `Path(x).name` là công cụ bị cấm, hoặc là
    `sh/bash -<cờ>c "<script>"` mà script có lệnh như vậy ở đầu một đoạn (tách theo `;`, `&`, `|`, `(`, `)`, backtick,
    xuống dòng). Ngoài ra mọi chỗ nhắc tới `_docker` của testkit đều bị bắt.

    Vì vậy tuple/list dữ liệu (`for t in ("docker", "kind")`, `parametrize("tool", ["kind"])`, `("kubectl", "1.34")`),
    dict binary giả, chuỗi, chú thích, `require_tool`, `require_image`, `shutil.which` đứng riêng không bị bắt.
    `run_sandboxed(`/`sandbox_command(` không phải điểm chạy lệnh: lệnh trong đó chạy trong bwrap, socket Docker và
    thông tin đăng nhập bị che, nên `run_sandboxed(["tofu", "plan"], ...)` hợp lệ. `kind_node_exec(`/`kind_node_cp(` cũng không
    phải: testkit chỉ nhận node `devops-lab-*` và argv không qua shell. Phương thức của lab (`lab.kubectl(...)`, `lab.helm(...)`)
    là lời gọi thuộc tính nên không bao giờ bị xét.
    """
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    except SyntaxError as error:
        return [f"{path}:{error.lineno}: không parse được: {error.msg}"]
    aliases = which_aliases(tree)
    values = assigned_values(tree)
    found: set[tuple[int, str]] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and is_command_sink(node):
            argument = sink_argument(node)
            for candidate in command_candidates(argument, values) if argument is not None else []:
                tool = candidate_tool(candidate, aliases)
                if tool:
                    found.add((node.lineno, tool))
        if isinstance(node, ast.Name) and node.id == "_docker" or isinstance(node, ast.Attribute) and node.attr == "_docker":
            found.add((node.lineno, "_docker"))
        elif isinstance(node, ast.alias) and node.name == "_docker":
            found.add((node.lineno, "_docker"))
    return [
        f"{path}:{line}: gọi {tool} trực tiếp; dùng helper của testkit (DockerLab, run_sandboxed, ...)"
        for line, tool in sorted(found)
    ]


def track_test_files() -> list[Path]:
    roots = [MODULES_DIR, TRACK / "capstone"]
    return sorted(p for root in roots if root.is_dir() for p in root.rglob("*.py") if "tests" in p.relative_to(root).parts)


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
    expected = {"id": "devops", "name": "DevOps", "icon": "container", "status": "active", "order": 5, "source": "https://roadmap.sh/devops"}
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


def test_tools_only_through_helpers():
    assert_clean([e for p in track_test_files() for e in check_tool_calls(p)])


def test_no_curl_pipe_sudo_in_markdown():
    assert_clean([e for p in TRACK.rglob("*.md") for e in check_no_curl_sudo(p)])


def test_milestone_docs_on_disk():
    docs = [TRACK / m["doc"] for m in load_track()["capstone"]["milestones"]]
    assert_clean([e for p in docs if p.is_file() for e in check_milestone_doc(p)])


def test_phase1_modules_present():
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


TOOL_DENYLIST_BAD = {
    "list-docker": 'subprocess.run(["docker", "run", "--rm", "nginx"])\n',
    "tuple-docker": "subprocess.run(('docker', 'ps', '-a'))\n",
    "list-kind": 'subprocess.run(["kind", "get", "clusters"], check=True)\n',
    "list-act-via-variable": 'cmd = ["act", "-j", "test"]\nsubprocess.run(cmd)\n',
    "list-act": 'subprocess.run(["act", "push", "-j", "build", "-P", "ubuntu-latest=node:24"])\n',
    "local-run-act": 'def run_workflow(c):\n    return subprocess.run(c)\nrun_workflow(["act", "push"])\n',
    "list-kubectl": 'subprocess.check_output(["kubectl", "get", "pods"])\n',
    "list-helm": 'subprocess.call(["helm", "install", "x", "chart"])\n',
    "list-tofu": 'subprocess.check_call(["tofu", "apply", "-auto-approve"])\n',
    "list-docker-starred": 'subprocess.run(["docker", *args])\n',
    "list-concat": 'subprocess.run(["docker"] + extra)\n',
    "args-keyword": 'subprocess.run(args=["helm", "list"])\n',
    "popen-list": 'Popen(["kubectl", "logs", "-f", "x"])\n',
    "os-execvp": 'os.execvp("docker", ["docker", "ps"])\n',
    "asyncio-exec": 'await asyncio.create_subprocess_exec("kubectl", "get", "pods")\n',
    "local-run-wrapper": 'def run_cmd(c):\n    return subprocess.run(c)\nrun_cmd(["kind", "get", "clusters"])\n',
    "local-exec-wrapper": 'exec_tool(("tofu", "plan"))\n',
    "string-subprocess": 'subprocess.check_output("docker run --rm nginx", shell=True)\n',
    "string-os-system": "os.system('docker rm -f x')\n",
    "string-os-popen": "os.popen('kubectl get ns').read()\n",
    "string-popen": 'Popen("helm list", shell=True)\n',
    "fstring-subprocess": 'subprocess.run(f"kind delete cluster --name {name}", shell=True)\n',
    "string-after-and": 'subprocess.run("cd x && docker compose up -d", shell=True)\n',
    "string-newline": 'subprocess.run("echo hi\\ndocker ps", shell=True)\n',
    "string-backtick": 'subprocess.run("echo `kubectl get ns`", shell=True)\n',
    "string-variable": 'script = "set -e; helm upgrade x chart"\nsubprocess.run(script, shell=True)\n',
    "shell-c-list": 'subprocess.run(["bash", "-c", "kubectl apply -f x.yaml"])\n',
    "shell-lc-list": 'subprocess.run(["bash", "-lc", "helm list"])\n',
    "shell-ec-list": 'subprocess.run(["/bin/sh", "-ec", "tofu init"])\n',
    "shell-separate-flags": 'subprocess.run(["bash", "-e", "-c", "act -j build"])\n',
    "wrapper-nice": 'subprocess.run(["nice", "-n", "15", "docker", "build", "."])\n',
    "wrapper-taskset": 'subprocess.run(["taskset", "-c", "12-35", "kind", "create", "cluster"])\n',
    "wrapper-chain": 'subprocess.run(["nice", "-n", "15", "taskset", "-c", "12-35", "docker", "run", "x"])\n',
    "wrapper-timeout": 'subprocess.run(["timeout", "-s", "KILL", "30", "kubectl", "get", "pods"])\n',
    "wrapper-env": 'subprocess.run(["env", "-i", "KUBECONFIG=/x", "kubectl", "get", "ns"])\n',
    "wrapper-sudo": 'subprocess.run(["sudo", "-u", "root", "docker", "ps"])\n',
    "wrapper-stdbuf": 'subprocess.run(["stdbuf", "-oL", "act", "-l"])\n',
    "wrapper-ionice": 'subprocess.run(["ionice", "-c", "3", "tofu", "apply"])\n',
    "wrapper-chrt": 'subprocess.run(["chrt", "-i", "0", "helm", "list"])\n',
    "wrapper-in-shell-string": 'subprocess.run("nice -n 15 docker build .", shell=True)\n',
    "assignment-in-shell-string": 'subprocess.run("KUBECONFIG=/x kubectl apply -f y", shell=True)\n',
    "absolute-path-list": 'subprocess.run(["/usr/bin/docker", "ps"])\n',
    "absolute-path-string": 'subprocess.run("/usr/local/bin/kubectl get pods", shell=True)\n',
    "which-alias": 'KUBECTL = shutil.which("kubectl")\nsubprocess.run([KUBECTL, "get", "pods"])\n',
    "which-inline": 'subprocess.run([shutil.which("docker"), "ps"])\n',
    "private-docker-call": 'from testkit import _docker\nresult = _docker("run", "--rm", "nginx")\n',
    "private-docker-attr": 'testkit._docker ("ps")\n',
    "private-docker-alias": 'from testkit import _docker as d\n',
    "kind-node-via-docker": 'subprocess.run(["docker", "exec", "devops-lab-control-plane", "etcdctl", "version"])\n',
    "kind-kubeconfig-direct": 'subprocess.run(["kind", "get", "kubeconfig", "--name", "devops-lab"], capture_output=True)\n',
    "kubectl-learner-kubeconfig": 'subprocess.run(["kubectl", "--kubeconfig", str(lab.kubeconfig), "get", "pods"])\n',
    "helm-direct": 'run_helm = subprocess.run\nrun_helm(["helm", "upgrade", "--install", "api", "chart"])\n',
}

TOOL_DENYLIST_GOOD = {
    "docker-lab": 'with DockerLab() as lab:\n    lab.start("web", "nginx:1.30.6-alpine", ports=[80])\n    lab.exec("web", "nginx", "-t")\n',
    "require-tool": 'ex.require_tool("docker")\nex.require_tool("kind")\n',
    "require-image": 'ex.require_image("nginx:1.30.6-alpine")\n',
    "shutil-which": 'if shutil.which("kubectl") is None:\n    pytest.skip("x")\n',
    "comment-and-string": '# docker run trong chú thích\nmessage = "chạy docker run --rm hoặc kubectl apply"\n',
    "fake-binaries-dict": 'FAKES = {"docker": FAKE, "kubectl": FAKE}\n',
    "subscript-key": 'assert result["kind"] == "nxdomain"\n',
    "data-tuple-loop": 'for t in ("docker", "kind"):\n    ex.require_tool(t)\n',
    "data-parametrize": '@pytest.mark.parametrize("tool", ["kind", "helm"])\ndef test_x(tool):\n    pass\n',
    "data-version-pairs": 'PINS = (("kubectl", "1.34"), ("helm", "3.19"))\n',
    "data-list-unused": 'TOOLS = ["docker", "kind"]\nexpected = ["kubectl", "apply", "-f", "x"]\nassert parse(line) == expected\n',
    "run-sandboxed-tofu": 'run_sandboxed(["tofu", "plan"], writable=[t], cwd=t, env={})\n',
    "run-sandboxed-keyword": 'testkit.run_sandboxed(cmd=["kubectl", "version"], writable=[t], cwd=t, env={})\n',
    "run-sandboxed-variable": 'cmd = ["tofu", "plan"]\nrun_sandboxed(cmd, writable=[t], cwd=t, env={})\n',
    "sandbox-command-docker": 'argv = sandbox_command(["docker", "version"], writable=[t], cwd=t, env={})\n',
    "tofu-lab": 'with TofuLab(ex.path("infra")) as lab:\n    lab.init()\n    lab.apply()\n    assert lab.output("bucket")\n',
    "act-run-helper": 'result = act_run(tmp_path / "project", job="build")\nassert act_job_results(result) == {"build": True}\n',
    "testkit-act-run": 'testkit.act_run(project, event="push", secrets={"DEPLOY_TOKEN": "x"}, timeout=300)\n',
    "run-sandboxed-shell-c": 'run_sandboxed(["bash", "-c", "tofu init && tofu plan"], writable=[t], cwd=t, env={})\n',
    "other-argv": 'subprocess.run(["git", "status"])\nsubprocess.run(["bash", "-c", "echo docker"])\n',
    "nice-python": 'subprocess.run(["nice", "-n", "15", "python3", "x.py"])\n',
    "wrapper-learner-script": 'subprocess.run(["timeout", "30", "bash", "deploy.sh", "docker"])\n',
    "learner-script-string": 'subprocess.run("./deploy.sh docker", shell=True)\n',
    "echo-mentions-tool": 'subprocess.run("echo use kubectl here", shell=True)\n',
    "kube-lab": 'with KubeLab() as lab:\n    lab.apply_learner(ex.path("k8s"))\n    lab.kubectl("get", "deploy", "api")\n    lab.helm("list")\n',
    "kube-lab-run-script": 'with KubeLab() as lab:\n    lab.run(["bash", "deploy.sh"], readonly=[ex.target])\n',
    "kind-node-exec": 'kind_node_exec("devops-lab-control-plane", "etcdctl", "version")\n',
    "kind-node-exec-kubectl-argv": 'kind_node_exec("devops-lab-control-plane", "kubectl", "--kubeconfig", "/etc/kubernetes/admin.conf", "get", "nodes")\n',
    "testkit-kind-node-exec": 'testkit.kind_node_exec("devops-lab-worker", "crictl", "ps")\n',
    "kind-node-cp": 'kind_node_cp("devops-lab-control-plane", "/var/lib/etcd-backup/snap.db", tmp_path / "snap.db")\n',
    "require-cluster": 'ex.require_cluster()\nex.require_tool("kubectl", "1.33")\nex.require_tool("helm", "3.18")\n',
}


@pytest.mark.parametrize("name", TOOL_DENYLIST_BAD)
def test_validator_tool_denylist(tmp_path, name):
    errors = check_tool_calls(write(tmp_path / "test_x.py", TOOL_DENYLIST_BAD[name]))
    assert errors, name
    assert all("test_x.py:" in e for e in errors)


@pytest.mark.parametrize("name", TOOL_DENYLIST_GOOD)
def test_validator_tool_denylist_allows(tmp_path, name):
    assert check_tool_calls(write(tmp_path / "test_x.py", TOOL_DENYLIST_GOOD[name])) == []


def test_validator_allows_require_tool_with_version(tmp_path):
    text = 'ex.require_tool("docker", "24")\nex.require_tool("kubectl", min_version="1.34")\nex.require_tool("tofu", "1.10")\n'
    assert check_tool_calls(write(tmp_path / "test_x.py", text)) == []


def test_validator_reports_line_numbers(tmp_path):
    errors = check_tool_calls(write(tmp_path / "test_x.py", 'x = 1\n\nsubprocess.run(["helm", "list"])\n'))
    assert len(errors) == 1 and "test_x.py:3:" in errors[0] and "helm" in errors[0]


def test_validator_reports_syntax_error(tmp_path):
    assert check_tool_calls(write(tmp_path / "test_x.py", "def broken(:\n"))


def test_validator_scans_module_and_capstone_tests_only():
    files = track_test_files()
    assert files and all("tests" in p.relative_to(TRACK).parts for p in files)
    assert {p.relative_to(TRACK).parts[0] for p in files} <= {"modules", "capstone"}
    assert any(p.relative_to(TRACK).parts[0] == "capstone" for p in files)


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
        "id": "devops",
        "name": "DevOps",
        "icon": "container",
        "status": "active",
        "order": 5,
        "source": "https://roadmap.sh/devops",
        "description": "x",
        "modules": [{"id": m, "title": "t", "summary": "s", "topics": ["a"]} for m in MODULE_IDS],
        "capstone": {
            "title": "Olist Shop",
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
    data["capstone"]["milestones"][4]["after"] = "08-iac-provisioning"
    assert any("m05" in e for e in check_track_json(data))
    data = valid_track()
    data["capstone"]["milestones"][0]["doc"] = "capstone/milestones/m02-x.md"
    assert any("m01" in e for e in check_track_json(data))
    data = valid_track()
    del data["modules"][0]["topics"]
    assert any("00-introduction" in e for e in check_track_json(data))

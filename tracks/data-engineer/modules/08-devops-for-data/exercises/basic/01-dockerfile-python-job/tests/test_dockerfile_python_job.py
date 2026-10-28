import json
import re

from testkit import Exercise

ex = Exercise(__file__)


def parse_dockerfile(text: str) -> list[tuple[str, str]]:
    """Trả về danh sách (INSTRUCTION, args), đã nối dòng có `\\` và bỏ comment."""
    instructions, buffer = [], ""
    for raw in text.splitlines():
        line = raw.strip()
        if not buffer and (not line or line.startswith("#")):
            continue
        if line.startswith("#"):
            continue
        if line.endswith("\\"):
            buffer += line[:-1] + " "
            continue
        buffer += line
        if buffer.strip():
            word, _, rest = buffer.strip().partition(" ")
            instructions.append((word.upper(), rest.strip()))
        buffer = ""
    return instructions


def instructions():
    return parse_dockerfile(ex.read("Dockerfile"))


def index_of(instrs, pred):
    for i, (cmd, args) in enumerate(instrs):
        if pred(cmd, args):
            return i
    return -1


def test_base_image_pinned():
    froms = [args for cmd, args in instructions() if cmd == "FROM"]
    assert len(froms) == 1, "Bài này chỉ cần một stage FROM"
    image = froms[0].split()[0]
    assert ":" in image or "@sha256:" in image, "Base image phải có tag"
    tag = image.split("@")[0].split(":", 1)[1] if ":" in image.split("@")[0] else ""
    assert tag != "latest", "Không dùng tag latest"
    assert re.search(r"\d", tag), f"Tag {tag!r} cần có số phiên bản, vd. 3.12-slim"


def test_workdir():
    assert any(cmd == "WORKDIR" for cmd, _ in instructions())


def test_layer_order_for_cache():
    instrs = instructions()
    copy_req = index_of(instrs, lambda c, a: c == "COPY" and "requirements" in a)
    pip = index_of(instrs, lambda c, a: c == "RUN" and "pip install" in a)
    copy_src = index_of(
        instrs,
        lambda c, a: c == "COPY" and "requirements" not in a
        and (re.match(r"(--\S+\s+)*(\./)?src\b", a) or re.match(r"(--\S+\s+)*\.\s", a)),
    )
    assert copy_req >= 0, "Cần COPY requirements.txt riêng"
    assert pip >= 0, "Cần RUN pip install"
    assert copy_src >= 0, "Cần COPY mã nguồn (src/ hoặc .)"
    assert copy_req < pip < copy_src, "Thứ tự phải là COPY requirements -> pip install -> COPY code"


def test_pip_no_cache():
    pips = [a for c, a in instructions() if c == "RUN" and "pip install" in a]
    assert pips
    for args in pips:
        for part in args.split("&&"):
            if "pip install" in part:
                assert "--no-cache-dir" in part, f"Thiếu --no-cache-dir: {part.strip()}"


def test_non_root_user():
    instrs = instructions()
    users = [(i, a) for i, (c, a) in enumerate(instrs) if c == "USER"]
    assert users, "Cần USER không phải root"
    i, last_user = users[-1]
    assert last_user.split(":")[0] not in {"root", "0"}
    pip = index_of(instrs, lambda c, a: c == "RUN" and "pip install" in a)
    assert i > pip, "USER đặt sau bước cài đặt"


def test_exec_form_entrypoint():
    instrs = [(c, a) for c, a in instructions() if c in {"CMD", "ENTRYPOINT"}]
    assert instrs, "Cần CMD hoặc ENTRYPOINT"
    joined = []
    for cmd, args in instrs:
        try:
            parsed = json.loads(args)
        except json.JSONDecodeError:
            raise AssertionError(f"{cmd} phải dùng exec form (mảng JSON): {args}")
        assert isinstance(parsed, list)
        joined += parsed
    assert "src.ingest_orders" in joined, "Phải chạy module src.ingest_orders"


def test_no_secret_in_image():
    for cmd, args in instructions():
        if cmd in {"ENV", "ARG"}:
            assert not re.search(r"PASSWORD|SECRET|TOKEN", args, re.I), f"Secret trong {cmd}: {args}"


def test_dockerignore():
    lines = {line.strip().rstrip("/") for line in ex.read(".dockerignore").splitlines()
             if line.strip() and not line.startswith("#")}
    for needed in [".git", "__pycache__", ".venv", "data"]:
        assert any(line.lstrip("*/").rstrip("/*") == needed for line in lines), f".dockerignore thiếu {needed}"

"""Sự cố tại bệnh viện: chỉ có support bundle và vài lệnh nhờ khách gõ.

Bước 1, điều tra (chạy từ gốc repo): `PYTHONPATH=. uv run python <tệp này> [--seed N]` dựng cảnh, in ticket và seed,
lưu bundle vào `.fde-lab/08-field-incident/`, rồi mở kênh `tools/ask_customer.py` cho tới khi bạn nhấn Enter.
Bước 2, chấm: `FDE_08_INCIDENT_SEED=N uv run pytest <thư mục bài>` dựng lại đúng cảnh của seed đó và chấm `incident.yaml`.
"""

import importlib.util
import json
import os
import random
import secrets
import shlex
import socket
import sys
import threading
import time
from pathlib import Path

import pytest
import yaml

import fdekit
from testkit import ROOT, Exercise

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fieldkit  # noqa: E402

ex = Exercise(__file__)
SEED_ENV = "FDE_08_INCIDENT_SEED"
WORKDIR = ROOT / ".fde-lab" / "08-field-incident"
REFERENCE = ROOT / "tracks" / "fde" / "modules" / "08-field-troubleshooting" / "solutions" / "intermediate" / \
    "01-field-incident"
MAX_COMMANDS = 4
MIN_EVIDENCE, MAX_EVIDENCE = 2, 6
MIN_TEXT = 6
MIN_SUMMARY = 40


def scenarios() -> dict:
    spec = importlib.util.spec_from_file_location("fde08_incident_scenarios", REFERENCE / "scenarios.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.SCENARIOS


def load_incident(path: Path) -> dict:
    if not path.is_file():
        pytest.fail(f"Không có {path}")
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as error:
        pytest.fail(f"{path.name} không phải YAML hợp lệ: {error}")
    if not isinstance(data, dict):
        pytest.fail(f"{path.name}: cần một mapping YAML")
    cause = data.get("cause")
    if cause not in fieldkit.CAUSES:
        pytest.fail(f"{path.name}: cause phải là một trong {', '.join(fieldkit.CAUSES)}; có {cause!r}")
    summary = data.get("summary")
    if not isinstance(summary, str) or len(summary.strip()) < MIN_SUMMARY:
        pytest.fail(f"{path.name}: summary cần ít nhất {MIN_SUMMARY} ký tự")
    steps = data.get("next_steps")
    if not isinstance(steps, list) or not steps or not all(isinstance(s, str) and s.strip() for s in steps):
        pytest.fail(f"{path.name}: next_steps cần là danh sách chuỗi không rỗng")
    commands = data.get("customer_commands") or []
    if not isinstance(commands, list) or not all(isinstance(c, str) for c in commands):
        pytest.fail(f"{path.name}: customer_commands cần là danh sách chuỗi")
    if len(commands) > MAX_COMMANDS:
        pytest.fail(f"{path.name}: khách chỉ gõ giúp tối đa {MAX_COMMANDS} lệnh, bạn nhờ {len(commands)}")
    for command in commands:
        argv, reason = fieldkit.check_command(command)
        if argv is None:
            pytest.fail(f"{path.name}: khách từ chối lệnh {command!r}: {reason}")
    evidence = data.get("evidence")
    if not isinstance(evidence, list) or not MIN_EVIDENCE <= len(evidence) <= MAX_EVIDENCE:
        pytest.fail(f"{path.name}: evidence cần {MIN_EVIDENCE}–{MAX_EVIDENCE} mục")
    for i, item in enumerate(evidence, 1):
        if not isinstance(item, dict) or not isinstance(item.get("source"), str) or not isinstance(item.get("text"), str):
            pytest.fail(f"{path.name}: evidence[{i}] cần source và text (chuỗi)")
        if len(item["text"].strip()) < MIN_TEXT or "\n" in item["text"].strip():
            pytest.fail(f"{path.name}: evidence[{i}].text cần ≥ {MIN_TEXT} ký tự, trên một dòng")
        source = item["source"]
        if source.startswith("customer:"):
            index = source.split(":", 1)[1]
            if not index.isdigit() or not 1 <= int(index) <= len(commands):
                pytest.fail(f"{path.name}: evidence[{i}].source {source!r} không trỏ tới lệnh nào trong customer_commands")
        elif not source.startswith("bundle:"):
            pytest.fail(f"{path.name}: evidence[{i}].source phải là bundle:<đường dẫn> hoặc customer:<số>")
    return data


def find_line(text: str, needle: str) -> bool:
    return any(needle in line for line in text.splitlines())


def grade(scene: fieldkit.Scene, scenario, incident: dict, bundle: dict[str, str]) -> None:
    outputs = []
    for command in incident.get("customer_commands") or []:
        allowed, output = scene.customer_runs(command)
        assert allowed, f"Khách từ chối {command!r}: {output}"
        outputs.append(output)
    direct = False
    for i, item in enumerate(incident["evidence"], 1):
        source, needle = item["source"], item["text"].strip()
        if source.startswith("bundle:"):
            name = source.split(":", 1)[1].strip().lstrip("/")
            assert name in bundle, f"evidence[{i}]: bundle không có tệp {name!r} (có {sorted(bundle)})"
            haystack, canonical, command = bundle[name], f"bundle:{name}", ""
        else:
            index = int(source.split(":", 1)[1]) - 1
            haystack, canonical = outputs[index], f"customer:{index + 1}"
            command = incident["customer_commands"][index].lower()
        assert find_line(haystack, needle), (
            f"evidence[{i}]: không thấy {needle!r} trong một dòng của {source} khi dựng lại cảnh (đoạn trích phải "
            "nằm nguyên trong một dòng và không chứa phần đổi theo lần chạy: thời gian, PID, id, cổng)")
        for src, text in scenario.direct:
            if not src.search(canonical):
                continue
            for match in text.finditer(needle):
                span = match.group(0)
                if not command or span.startswith("/") or span.lower() not in command:
                    direct = True
    assert incident["cause"] in scenario.accepted, \
        f"cause {incident['cause']!r} không giải thích được sự cố này; xem lại bằng chứng"
    assert direct, "Không bằng chứng nào chỉ thẳng vào nguyên nhân (mới là triệu chứng); thêm dấu vết của nguyên nhân"


def build_scene(site: fdekit.Site, seed: int, name: str, workdir: Path) -> tuple[fieldkit.Scene, dict[str, str]]:
    scene = fieldkit.Scene(site, seed)
    scenarios()[name].build(scene)
    bundle = scene.bundle(workdir / "bundle.tar.gz")
    return scene, bundle


def run_case(tmp_path: Path, seed: int, name: str, incident_path: Path) -> None:
    incident = load_incident(incident_path)
    with fdekit.customer_site("hospital", base=fdekit.derived(fieldkit.SNAPSHOT), memory_mb=fieldkit.MEMORY_MB,
                              forwards=(18080,)) as site:
        scene, bundle = build_scene(site, seed, name, tmp_path)
        grade(scene, scenarios()[name], incident, bundle)


def cases() -> list:
    if os.environ.get("SOLUTION") == "1":
        return [pytest.param(name, id=name) for name in sorted(scenarios())]
    return [pytest.param(None, id="seed")]


@pytest.mark.parametrize("forced", cases())
def test_incident_report(forced, tmp_path):
    names = sorted(scenarios())
    if forced is not None:
        seed = secrets.randbelow(10**6)
        print(f"{SEED_ENV}={seed} (lời giải tham chiếu cho cảnh {forced})")
        run_case(tmp_path, seed, forced, REFERENCE / "incidents" / f"{forced}.yaml")
        return
    raw = os.environ.get(SEED_ENV, "")
    if not raw.isdigit():
        pytest.skip(f"Bước 1: dựng cảnh và điều tra (README mục Đề bài), rồi chấm bằng {SEED_ENV}=<seed> uv run pytest …")
    seed = int(raw)
    incident = load_incident(ex.path("incident.yaml"))
    check_asked(seed, incident.get("customer_commands") or [], WORKDIR / "ask-log.jsonl")
    run_case(tmp_path, seed, fieldkit.pick_scenario(seed, names), ex.path("incident.yaml"))


def asked(log_path: Path, seed: int) -> list[str]:
    """Lệnh khách đã gõ (được chấp nhận) trong các buổi điều tra của seed này, theo nhật ký của ask_customer."""
    commands = []
    if log_path.is_file():
        for line in log_path.read_text(encoding="utf-8").splitlines():
            try:
                record = json.loads(line)
            except ValueError:
                continue
            if isinstance(record, dict) and record.get("seed") == seed and record.get("allowed") is True:
                commands.append(record.get("command"))
    return commands


def check_asked(seed: int, commands: list[str], log_path: Path) -> None:
    done = asked(log_path, seed)
    if len(done) > MAX_COMMANDS:
        pytest.fail(f"Với seed {seed} bạn đã nhờ khách gõ {len(done)} lệnh (nhật ký {log_path.relative_to(ROOT)}), "
                    f"tối đa {MAX_COMMANDS}; điều tra lại bằng seed khác")
    missing = [c for c in commands if c not in done]
    if missing:
        pytest.fail(f"customer_commands phải là lệnh bạn đã thật sự nhờ khách gõ cho seed {seed} qua ask_customer.py; "
                    f"không thấy trong nhật ký: {missing}")


def serve(scene: fieldkit.Scene, sock_path: Path, log_path: Path, stop: threading.Event) -> None:
    sock_path.unlink(missing_ok=True)
    server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    server.bind(str(sock_path))
    sock_path.chmod(0o600)
    server.listen(4)
    server.settimeout(0.5)
    count = len(asked(log_path, scene.seed))
    while not stop.is_set():
        try:
            conn, _ = server.accept()
        except socket.timeout:
            continue
        with conn:
            raw = b""
            while not raw.endswith(b"\n"):
                chunk = conn.recv(65536)
                if not chunk:
                    break
                raw += chunk
            try:
                command = json.loads(raw)["command"]
                if count >= MAX_COMMANDS:
                    allowed, output = False, f"khách đã gõ giúp {MAX_COMMANDS} lệnh cho sự cố này, không gõ thêm"
                else:
                    allowed, output = scene.customer_runs(command)
                    count += allowed
                    fieldkit.log_line(log_path, {"ts": time.strftime("%Y-%m-%dT%H:%M:%S"), "seed": scene.seed,
                                                 "n": count if allowed else None, "command": command,
                                                 "allowed": allowed})
                reply = {"allowed": allowed, "output": output, "count": count, "limit": MAX_COMMANDS}
            except BaseException as error:
                reply = {"allowed": False, "output": f"lỗi khi chuyển lệnh tới khách: {error}", "count": count,
                         "limit": MAX_COMMANDS}
            try:
                conn.sendall(json.dumps(reply, ensure_ascii=False).encode() + b"\n")
            except OSError:
                pass
    server.close()
    sock_path.unlink(missing_ok=True)


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Dựng cảnh sự cố tại bệnh viện để điều tra")
    parser.add_argument("--seed", type=int, default=None)
    args = parser.parse_args()
    seed = args.seed if args.seed is not None else random.SystemRandom().randrange(10**6)
    name = fieldkit.pick_scenario(seed, sorted(scenarios()))
    WORKDIR.mkdir(parents=True, exist_ok=True)
    for old in ("bundle", "bundle.tar.gz", "ticket.txt"):
        target = WORKDIR / old
        if target.is_dir():
            for path in sorted(target.rglob("*"), reverse=True):
                path.unlink() if path.is_file() else path.rmdir()
            target.rmdir()
        else:
            target.unlink(missing_ok=True)
    print(f"Seed: {seed}  (chấm bằng {SEED_ENV}={seed})\nĐang dựng máy của khách (~2 phút)…", flush=True)
    with fdekit.customer_site("hospital", base=fdekit.derived(fieldkit.SNAPSHOT), memory_mb=fieldkit.MEMORY_MB,
                              forwards=(18080,)) as site:
        scene, bundle = build_scene(site, seed, name, WORKDIR)
        fieldkit.extract(bundle, WORKDIR / "bundle")
        ticket = scenarios()[name].ticket
        (WORKDIR / "ticket.txt").write_text(f"seed: {seed}\n\n{ticket}\n")
        stop = threading.Event()
        thread = threading.Thread(target=serve, args=(scene, WORKDIR / "ask.sock", WORKDIR / "ask-log.jsonl", stop),
                                  daemon=True)
        thread.start()
        print(f"""
Ticket của IT bệnh viện:
  {ticket}

Support bundle khách gửi: {WORKDIR / 'bundle'}  (và {WORKDIR / 'bundle.tar.gz'})
Nhờ khách gõ lệnh:        uv run python {shlex.quote(str(ex.dir / 'tools' / 'ask_customer.py'))} "df -h"
Nhật ký các lệnh đã nhờ:  {WORKDIR / 'ask-log.jsonl'}
Chấm:                     {SEED_ENV}={seed} uv run pytest {ex.dir.relative_to(ROOT)} -q

Nhấn Enter để dọn máy của khách.""", flush=True)
        try:
            input()
        finally:
            stop.set()
            thread.join(timeout=5)


if __name__ == "__main__":
    main()

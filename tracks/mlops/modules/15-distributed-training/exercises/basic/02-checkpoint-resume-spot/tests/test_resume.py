import json
import re

import distkit
import pytest
import torch

from testkit import Exercise

ex = Exercise(__file__)
STEPS = 120
EVERY = 10
KILL_AFTER = 40
DELAY = 0.05
TIMEOUT = 240
CKPT = re.compile(r"^step-(\d{6})\.pt$")


def args(out):
    return ["--out", out, "--steps", STEPS, "--every", EVERY, "--step-delay", DELAY]


def checkpoints(out):
    folder = out / "ckpt"
    if not folder.is_dir():
        return {}
    return {int(m.group(1)): p for p in folder.iterdir() if (m := CKPT.match(p.name))}


def starts(out):
    path = out / "log.jsonl"
    lines = [json.loads(line) for line in path.read_text().splitlines() if line.strip()] if path.is_file() else []
    return [line["from_step"] for line in lines if line.get("event") == "start"], lines


@pytest.fixture(scope="module")
def runs(tmp_path_factory):
    script = ex.path("train_resumable.py")
    base = tmp_path_factory.mktemp("resume")
    straight, broken = base / "straight", base / "broken"
    report = {"straight": distkit.torchrun(script, args(straight), workdir=base, timeout=TIMEOUT)}

    with distkit.launched(script, args(broken), workdir=base) as job:
        reached = distkit.wait_until(lambda: any(s >= KILL_AFTER for s in checkpoints(broken)), TIMEOUT, job)
        report["alive_at_kill"] = job.proc.poll() is None
        run_id = job.run_id
    report["reached"] = reached
    report["leftover_after_kill"] = distkit.marked(run_id)
    report["final_after_kill"] = (broken / "final.pt").exists()

    saved = checkpoints(broken)
    report["corrupt_step"] = None
    if saved:
        newest = max(saved)
        corrupt = newest + EVERY
        blob = saved[newest].read_bytes()
        (broken / "ckpt" / f"step-{corrupt:06d}.pt").write_bytes(blob[: len(blob) // 2])
        report["corrupt_step"] = corrupt
        report["readable_step"] = newest

    report["resumed"] = distkit.torchrun(script, args(broken), workdir=base, timeout=TIMEOUT)
    report["again"] = distkit.torchrun(script, args(broken), workdir=base, timeout=TIMEOUT)
    return straight, broken, report


def ran(result):
    assert result.ok, f"torchrun không chạy xong (timeout={result.timed_out}, mã {result.returncode}):\n{result.tail()}"
    assert not result.leftover, "Còn tiến trình của lần chạy sau khi dọn"


def test_uninterrupted_run_finishes(runs):
    straight, _, report = runs
    ran(report["straight"])
    assert (straight / "final.pt").is_file()
    assert sorted(checkpoints(straight)) == list(range(EVERY, STEPS + 1, EVERY))


def test_job_was_really_killed_midway(runs):
    _, _, report = runs
    assert report["reached"], f"Không thấy checkpoint bước >= {KILL_AFTER} trước khi job dừng"
    assert report["alive_at_kill"], "Job đã tự kết thúc trước khi bị kill; không kiểm được resume"
    assert not report["final_after_kill"]
    assert report["leftover_after_kill"] == [], "Còn worker sống sau khi kill cả job"


def test_resume_continues_from_newest_readable_checkpoint(runs):
    _, broken, report = runs
    ran(report["resumed"])
    begun, _ = starts(broken)
    assert len(begun) >= 2 and begun[0] == 0
    assert report["corrupt_step"] is not None
    assert begun[1] == report["readable_step"], "Lần chạy lại không tiếp từ checkpoint mới nhất còn đọc được"


def test_resumed_result_equals_uninterrupted(runs):
    straight, broken, report = runs
    ran(report["resumed"])
    a = torch.load(straight / "final.pt", weights_only=True)
    b = torch.load(broken / "final.pt", weights_only=True)
    assert set(a) == set(b)
    same = all(torch.allclose(a[k], b[k], atol=1e-6, rtol=0) for k in a)
    assert same, "Kết quả sau khi resume khác kết quả chạy liền một mạch"
    _, straight_log = starts(straight)
    _, broken_log = starts(broken)
    last = [line["loss"] for line in straight_log if line.get("step") == STEPS - 1]
    last_resumed = [line["loss"] for line in broken_log if line.get("step") == STEPS - 1]
    assert last and last_resumed and last[0] == pytest.approx(last_resumed[-1], abs=1e-6)


def test_rerun_after_completion_changes_nothing(runs):
    straight, broken, report = runs
    ran(report["again"])
    begun, lines = starts(broken)
    assert len(begun) == 3 and begun[2] == STEPS
    after_last_start = lines[max(i for i, line in enumerate(lines) if line.get("event") == "start") + 1:]
    assert not any("step" in line for line in after_last_start), "Job đã xong mà chạy lại vẫn huấn luyện thêm"
    a = torch.load(straight / "final.pt", weights_only=True)
    b = torch.load(broken / "final.pt", weights_only=True)
    assert all(torch.allclose(a[k], b[k], atol=1e-6, rtol=0) for k in a)


def test_every_checkpoint_is_loadable(runs):
    _, broken, report = runs
    ran(report["again"])
    expected = set(ex.module("train_resumable.py").build_model().state_dict())
    saved = checkpoints(broken)
    assert sorted(saved) == list(range(EVERY, STEPS + 1, EVERY))
    for step, path in saved.items():
        state = torch.load(path, weights_only=True)
        assert set(state) == {"step", "model", "optimizer"} and state["step"] == step
        assert set(state["model"]) == expected

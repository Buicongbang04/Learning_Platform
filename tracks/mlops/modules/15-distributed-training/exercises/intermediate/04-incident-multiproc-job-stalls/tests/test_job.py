"""Ca hồi quy dựa vào việc gloo chờ mãi khi hai rank đứng ở hai collective khác nhau (đã kiểm trên torch 2.14.1+cpu).

Bản torch sau mà biến tình huống đó thành lỗi ngay thì bản gốc thoát lỗi thay vì treo và ca hồi quy cần sửa.
"""

import json

import distkit
import pytest

from testkit import Exercise

ex = Exercise(__file__)
ORIGINAL = ex.fixtures / "train_job.original.py"
STEPS = 40
STALL_TIMEOUT = 30
TIMEOUT = 90


def read(path):
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()] if path.is_file() else []


def ran(result):
    assert not result.leftover, "Còn tiến trình của lần chạy sau khi dọn"
    assert result.ok, f"torchrun không chạy xong (timeout={result.timed_out}, mã {result.returncode}):\n{result.tail()}"


@pytest.fixture(scope="module")
def two(tmp_path_factory):
    base = tmp_path_factory.mktemp("two")
    return base / "out", distkit.torchrun(ex.path("train_job.py"), ["--out", base / "out", "--steps", STEPS],
                                          workdir=base, timeout=TIMEOUT)


def test_regression_original_runs_alone_but_stalls_with_two_workers(tmp_path):
    alone = distkit.torchrun(ORIGINAL, ["--out", tmp_path / "one", "--steps", STEPS], workdir=tmp_path, nproc=1,
                             timeout=TIMEOUT)
    ran(alone)
    stalled = distkit.torchrun(ORIGINAL, ["--out", tmp_path / "two", "--steps", STEPS], workdir=tmp_path,
                               timeout=STALL_TIMEOUT)
    assert stalled.timed_out
    assert stalled.leftover == [], "Worker treo vẫn còn sau khi dọn"
    progressed = [len(read(tmp_path / "two" / f"rank{r}.jsonl")) for r in (0, 1)]
    assert max(progressed) <= 1


def test_two_workers_finish(two):
    out, result = two
    ran(result)
    assert (out / "model.pt").is_file()
    for rank in (0, 1):
        assert [r["step"] for r in read(out / f"rank{rank}.jsonl")] == list(range(STEPS))


def test_metrics_are_the_mean_over_workers(two):
    out, result = two
    ran(result)
    mod = ex.module("train_job.py")
    traces = {rank: {r["step"]: r["loss"] for r in read(out / f"rank{rank}.jsonl")} for rank in (0, 1)}
    metrics = read(out / "metrics.jsonl")
    assert [m["step"] for m in metrics] == list(range(0, STEPS, mod.LOG_EVERY))
    for m in metrics:
        expected = (traces[0][m["step"]] + traces[1][m["step"]]) / 2
        assert m["loss"] == pytest.approx(expected, rel=1e-5)


def test_single_worker_still_works(tmp_path):
    result = distkit.torchrun(ex.path("train_job.py"), ["--out", tmp_path / "out", "--steps", 20], workdir=tmp_path,
                              nproc=1, timeout=TIMEOUT)
    ran(result)
    trace = {r["step"]: r["loss"] for r in read(tmp_path / "out" / "rank0.jsonl")}
    metrics = read(tmp_path / "out" / "metrics.jsonl")
    assert [m["step"] for m in metrics] == [0, 10]
    assert all(m["loss"] == pytest.approx(trace[m["step"]], rel=1e-5) for m in metrics)

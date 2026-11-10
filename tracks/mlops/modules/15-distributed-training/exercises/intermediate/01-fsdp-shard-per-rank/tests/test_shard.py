import json

import distkit
import pytest

from testkit import Exercise

ex = Exercise(__file__)
TIMEOUT = 240


@pytest.fixture(scope="module")
def result(tmp_path_factory):
    base = tmp_path_factory.mktemp("shard")
    done = distkit.torchrun(ex.path("shard_report.py"), ["--out", base / "out"], workdir=base, timeout=TIMEOUT)
    return base / "out", done


def reports(result):
    out, done = result
    assert not done.leftover, "Còn tiến trình của lần chạy sau khi dọn"
    assert done.ok, f"torchrun không chạy xong (timeout={done.timed_out}, mã {done.returncode}):\n{done.tail()}"
    found = {}
    for strategy in ("ddp", "fsdp"):
        for rank in (0, 1):
            path = out / f"{strategy}-rank{rank}.json"
            assert path.is_file(), f"Không thấy {path.name}"
            found[strategy, rank] = json.loads(path.read_text())
    return found


@pytest.fixture(scope="module")
def total():
    return sum(p.numel() for p in ex.module("shard_report.py").build_model().parameters())


def test_ddp_keeps_a_full_replica_on_every_rank(result, total):
    found = reports(result)
    for rank in (0, 1):
        report = found["ddp", rank]
        assert report["param_numel"] == total
        assert report["grad_numel"] == total
        assert report["optimizer_numel"] == 2 * total


def test_fsdp_splits_parameters_between_ranks(result, total):
    found = reports(result)
    a, b = found["fsdp", 0], found["fsdp", 1]
    for key, factor in (("param_numel", 1), ("grad_numel", 1), ("optimizer_numel", 2)):
        assert a[key] + b[key] == factor * total, f"{key}: tổng hai rank khác kích thước model"
        for report in (a, b):
            assert 0.45 * factor * total <= report[key] <= 0.55 * factor * total, f"{key}: một rank giữ không gần một nửa"
    assert a["param_types"] == b["param_types"] == ["DTensor"]


def test_fsdp_halves_model_state_memory(result):
    found = reports(result)
    for rank in (0, 1):
        ratio = found["fsdp", rank]["model_state_bytes"] / found["ddp", rank]["model_state_bytes"]
        assert 0.45 <= ratio <= 0.55


def test_fsdp_trains_exactly_like_ddp(result):
    found = reports(result)
    for rank in (0, 1):
        ddp, fsdp = found["ddp", rank]["losses"], found["fsdp", rank]["losses"]
        assert len(ddp) == len(fsdp) == ex.module("shard_report.py").STEPS
        assert fsdp == pytest.approx(ddp, rel=1e-4, abs=1e-6), "Loss FSDP lệch DDP trên cùng dữ liệu và khởi tạo"
    assert found["ddp", 0]["losses"][-1] < found["ddp", 0]["losses"][0]


def test_wrap_rejects_unknown_strategy():
    mod = ex.module("shard_report.py")
    with pytest.raises(ValueError):
        mod.wrap(mod.build_model(), "zero3")

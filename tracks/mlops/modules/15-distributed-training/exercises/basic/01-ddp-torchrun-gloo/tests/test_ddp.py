import json

import distkit
import pytest
import torch

from testkit import Exercise

ex = Exercise(__file__)
STEPS = 60
TIMEOUT = 240


@pytest.fixture(scope="module")
def result(tmp_path_factory):
    out = tmp_path_factory.mktemp("ddp")
    done = distkit.torchrun(ex.path("train_ddp.py"), ["--out", out / "out", "--steps", STEPS], workdir=out, timeout=TIMEOUT)
    return out / "out", done


def finished(result):
    out, done = result
    assert not done.leftover, "Còn tiến trình của lần chạy sau khi dọn"
    assert done.ok, f"torchrun không chạy xong (timeout={done.timed_out}, mã {done.returncode}):\n{done.tail()}"
    logs = {}
    for rank in (0, 1):
        path = out / f"rank{rank}.jsonl"
        assert path.is_file(), f"Không thấy {path.name}"
        logs[rank] = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
    return out, logs


def test_each_rank_knows_who_it_is(result):
    run = finished(result)
    out, _ = run
    for rank in (0, 1):
        meta = json.loads((out / f"rank{rank}-meta.json").read_text())
        assert meta == {"rank": rank, "local_rank": rank, "world_size": 2, "backend": "gloo"}


def test_every_step_logged_on_both_ranks(result):
    run = finished(result)
    _, logs = run
    for rank in (0, 1):
        assert [r["step"] for r in logs[rank]] == list(range(STEPS))


def test_parameters_identical_across_ranks_after_every_step(result):
    run = finished(result)
    _, logs = run
    same = all(a["digest"] == b["digest"] for a, b in zip(logs[0], logs[1], strict=True))
    assert same, "Tham số hai rank lệch nhau sau ít nhất một bước"


def test_ranks_split_the_data(result):
    run = finished(result)
    _, logs = run
    mod = ex.module("train_ddp.py")
    per_epoch = mod.N_SAMPLES // 2 // mod.BATCH_PER_RANK
    for a, b in zip(logs[0], logs[1], strict=True):
        assert len(a["indices"]) == mod.BATCH_PER_RANK and len(b["indices"]) == mod.BATCH_PER_RANK
        assert not set(a["indices"]) & set(b["indices"]), "Hai rank dùng chung mẫu trong cùng một bước"
    seen = [i for rank in (0, 1) for r in logs[rank][:per_epoch] for i in r["indices"]]
    assert sorted(seen) == list(range(mod.N_SAMPLES)), "Epoch đầu không đi qua mỗi mẫu đúng một lần"
    assert logs[0][0]["indices"] != logs[0][per_epoch]["indices"], "Epoch sau lặp lại đúng thứ tự epoch trước"
    assert {r["epoch"] for r in logs[0]} == {0, 1}


def test_loss_goes_down(result):
    run = finished(result)
    _, logs = run
    mean = [(a["loss"] + b["loss"]) / 2 for a, b in zip(logs[0], logs[1])]
    assert sum(mean[-10:]) / 10 < 0.6 * sum(mean[:5]) / 5


def test_result_equals_single_process_on_the_global_batch(result):
    run = finished(result)
    out, logs = run
    mod = ex.module("train_ddp.py")
    x, y, _ = mod.make_dataset().tensors
    model = mod.build_model()
    optimizer = torch.optim.SGD(model.parameters(), lr=mod.LR)
    for a, b in zip(logs[0], logs[1]):
        idx = torch.tensor(a["indices"] + b["indices"])
        loss = torch.nn.functional.mse_loss(model(x[idx]), y[idx])
        optimizer.zero_grad()
        loss.backward()
        optimizer.step()
    final = torch.load(out / "rank0-final.pt", weights_only=True)
    reference = model.state_dict()
    assert set(final) == set(reference), "rank0-final.pt không phải state_dict của model gốc (chưa bỏ lớp bọc?)"
    close = all(torch.allclose(final[k], reference[k], atol=1e-4) for k in reference)
    assert close, "Kết quả DDP khác huấn luyện một tiến trình trên batch toàn cục"

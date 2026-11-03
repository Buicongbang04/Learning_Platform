import hashlib
import json
import os

import pytest

from testkit import Exercise

ex = Exercise(__file__)
HEADER = "distance_km,duration_s\n"


def rows(n, start=0):
    return "".join(f"{1 + (start + i) % 9}.5,{300 + 20 * ((start + i) % 9)}\n" for i in range(n))


class TrainBroke(Exception):
    pass


class Trainer:
    def __init__(self, fail=False):
        self.paths = []
        self.fail = fail

    def __call__(self, path):
        self.paths.append(path)
        if self.fail:
            raise TrainBroke("train hỏng")
        return {"mae": 12.5}


@pytest.fixture(scope="module")
def mod():
    return ex.module("trigger.py")


@pytest.fixture
def env(tmp_path):
    data = tmp_path / "trips.csv"
    data.write_text(HEADER + rows(100))
    return data, tmp_path / "state.json"


def run(mod, env, trainer, **kwargs):
    data, state = env
    return mod.ct_flow(str(data), str(state), trainer, **kwargs)


def test_file_sha256_matches_hashlib(mod, env):
    data, _ = env
    assert mod.file_sha256(str(data)) == hashlib.sha256(data.read_bytes()).hexdigest()


def test_first_run_trains_and_records_hash_and_rows(mod, env):
    trainer = Trainer()
    result = run(mod, env, trainer)
    data, state = env
    assert result["status"] == "trained"
    assert result["data_sha256"] == hashlib.sha256(data.read_bytes()).hexdigest()
    assert trainer.paths == [str(data)]
    assert json.loads(state.read_text()) == {"last_data_sha256": result["data_sha256"], "rows": 100}


def test_unchanged_data_is_skipped(mod, env):
    trainer = Trainer()
    run(mod, env, trainer)
    result = run(mod, env, trainer)
    assert result["status"] == "skipped" and result["reason"] == "unchanged"
    assert len(trainer.paths) == 1


def test_touching_the_file_does_not_retrain(mod, env):
    trainer = Trainer()
    run(mod, env, trainer)
    data, _ = env
    os.utime(data, (1_000_000_000, 1_000_000_000))
    assert run(mod, env, trainer)["status"] == "skipped"
    assert len(trainer.paths) == 1


def test_changed_content_retrains_and_updates_state(mod, env):
    trainer = Trainer()
    run(mod, env, trainer)
    data, state = env
    data.write_text(HEADER + rows(150))
    result = run(mod, env, trainer)
    assert result["status"] == "trained"
    assert len(trainer.paths) == 2
    assert json.loads(state.read_text())["rows"] == 150
    assert run(mod, env, trainer)["status"] == "skipped"


def test_failed_training_keeps_old_state_so_next_run_retries(mod, env):
    ok = Trainer()
    run(mod, env, ok)
    data, state = env
    before = state.read_text()
    data.write_text(HEADER + rows(150))
    with pytest.raises(TrainBroke):
        run(mod, env, Trainer(fail=True))
    assert state.read_text() == before
    retry = Trainer()
    assert run(mod, env, retry)["status"] == "trained"
    assert len(retry.paths) == 1


def test_failed_first_training_writes_no_state(mod, env):
    _, state = env
    with pytest.raises(TrainBroke):
        run(mod, env, Trainer(fail=True))
    assert not state.exists()


def test_force_trains_even_when_unchanged(mod, env):
    trainer = Trainer()
    run(mod, env, trainer)
    result = run(mod, env, trainer, force=True)
    assert result["status"] == "trained"
    assert len(trainer.paths) == 2


def test_too_few_new_rows_is_skipped_without_recording_the_hash(mod, env):
    trainer = Trainer()
    run(mod, env, trainer, min_new_rows=50)
    data, state = env
    before = state.read_text()
    data.write_text(HEADER + rows(120))
    result = run(mod, env, trainer, min_new_rows=50)
    assert result["status"] == "skipped" and result["reason"] == "too_few_new_rows"
    assert state.read_text() == before
    data.write_text(HEADER + rows(160))
    assert run(mod, env, trainer, min_new_rows=50)["status"] == "trained"
    assert len(trainer.paths) == 2


def test_min_new_rows_exactly_at_threshold_trains(mod, env):
    trainer = Trainer()
    run(mod, env, trainer)
    data, _ = env
    data.write_text(HEADER + rows(150))
    assert run(mod, env, trainer, min_new_rows=50)["status"] == "trained"


def test_first_run_ignores_min_new_rows(mod, env):
    trainer = Trainer()
    assert run(mod, env, trainer, min_new_rows=10_000)["status"] == "trained"


def test_force_overrides_min_new_rows(mod, env):
    trainer = Trainer()
    run(mod, env, trainer)
    data, _ = env
    data.write_text(HEADER + rows(101))
    assert run(mod, env, trainer, min_new_rows=50, force=True)["status"] == "trained"


def test_missing_or_header_only_data_raises_before_training(mod, env):
    data, state = env
    trainer = Trainer()
    data.write_text(HEADER)
    with pytest.raises(ValueError):
        run(mod, env, trainer)
    data.unlink()
    with pytest.raises(FileNotFoundError):
        run(mod, env, trainer)
    assert trainer.paths == [] and not state.exists()

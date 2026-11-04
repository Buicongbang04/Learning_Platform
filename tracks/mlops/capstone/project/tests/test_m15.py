"""M15: retrain ETA bằng Ray Tune nhiều worker, checkpoint định kỳ, chịu một worker bị kill giữa chừng.

Đề ở capstone/milestones/m15-ray-retrain.md. Test chạy `eta.distributed.retrain` một lần trên Ray cục bộ 2 CPU
(`mlopskit.ray_local`), kill thật (SIGKILL) một worker đang chạy trial khi trial đó đã có checkpoint, rồi đọc kết quả
từng trial mà Tune ghi trong `storage_path`.
"""

import json
import math
import os
import signal
import threading
import time
import uuid
from pathlib import Path

import mlflow
import numpy as np
import pandas as pd
import pytest
from etakit import PROJECT, local_registry, need, synthetic_month

import mlopskit

NAME = "eta-retrain-m15"
WORKERS = 2
ROUNDS = 200
EVERY = 20
MAX_FAILURES = 2
KILL_AFTER_REPORTS = 3
TIMEOUT_S = 240
ROWS = 40_000
MAE_REGRESSION = 0.03
AIRPORT_REGRESSION = 0.05
ZONE_BASELINE_MARGIN = 0.8
LEFTOVER_GRACE_S = 15


class Watchdog(BaseException):
    pass


EXPIRED = {"hit": False}


def expire(signum, frame):
    EXPIRED["hit"] = True
    raise Watchdog


def frames() -> tuple[pd.DataFrame, pd.DataFrame]:
    frame = synthetic_month(ROWS, month="2019-03", seed=15, extra_columns=False)
    frame["duration_s"] = (frame["tpep_dropoff_datetime"] - frame["tpep_pickup_datetime"]).dt.total_seconds()
    frame = frame.sort_values("tpep_pickup_datetime", kind="mergesort").reset_index(drop=True)
    cut = int(len(frame) * 0.8)
    return frame.iloc[:cut].reset_index(drop=True), frame.iloc[cut:].reset_index(drop=True)


def reports(trial: Path) -> list[dict]:
    path = trial / "result.json"
    if not path.is_file():
        return []
    rows = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        try:
            rows.append(json.loads(line))
        except ValueError:
            continue
    return rows


def trials(root: Path) -> dict[str, list[dict]]:
    if not root.is_dir():
        return {}
    return {d.name: reports(d) for d in sorted(root.iterdir()) if d.is_dir()}


def ray_worker(pid: int) -> bool:
    try:
        cmdline = Path(f"/proc/{pid}/cmdline").read_bytes()
        owner = Path(f"/proc/{pid}").stat().st_uid
    except OSError:
        return False
    return owner == os.getuid() and cmdline.startswith(b"ray::")


def kill_worker(pid: int) -> bool:
    """SIGKILL qua pidfd, chỉ khi tiến trình đó vẫn là worker Ray của user này (PID không bị tái sử dụng nhầm)."""
    try:
        fd = os.pidfd_open(pid)
    except OSError:
        return False
    try:
        if not ray_worker(pid):
            return False
        signal.pidfd_send_signal(fd, signal.SIGKILL)
        return True
    except OSError:
        return False
    finally:
        os.close(fd)


class Killer(threading.Thread):
    """Theo dõi `storage/NAME`: trial đầu tiên đã báo đủ KILL_AFTER_REPORTS lần, chưa xong và đã có checkpoint thì bị kill."""

    def __init__(self, root: Path):
        super().__init__(daemon=True)
        self.root = root
        self.stop = threading.Event()
        self.victim: dict | None = None

    def run(self) -> None:
        while not self.stop.is_set() and self.victim is None:
            if self.root.is_dir():
                for trial in sorted(self.root.iterdir()):
                    if trial.is_dir() and self.try_kill(trial):
                        return
            time.sleep(0.05)

    def try_kill(self, trial: Path) -> bool:
        rows = reports(trial)
        if len(rows) < KILL_AFTER_REPORTS or rows[-1].get("done") or rows[-1].get("trees") == ROUNDS:
            return False
        try:
            if not any(p.name.startswith("checkpoint_") for p in trial.iterdir()):
                return False
        except OSError:
            return False
        pid = rows[-1].get("pid")
        if not isinstance(pid, int) or not kill_worker(pid):
            return False
        self.victim = {"trial": trial.name, "pid": pid, "reports_before": len(rows)}
        return True


def alive(pids: set[int]) -> list[int]:
    return sorted(p for p in pids if ray_worker(p))


@pytest.fixture(scope="module")
def outcome(tmp_path_factory):
    """Chạy retrain một lần cho cả module, chỉ khi test đầu tiên cần; lỗi thành dict `failed` để test fail, không ERROR."""
    cache: dict = {}

    def run() -> dict:
        if cache:
            return cache
        distributed = need("distributed", "retrain", "register")
        train, valid = frames()
        with pytest.MonkeyPatch.context() as patch:
            patch.setenv("PYTHONPATH", os.pathsep.join(filter(None, [str(PROJECT / "src"), os.environ.get("PYTHONPATH")])))
            with mlopskit.ray_local(num_cpus=WORKERS) as storage:
                killer = Killer(storage / NAME)
                killer.start()
                previous = signal.signal(signal.SIGALRM, expire)
                signal.alarm(TIMEOUT_S)
                started = time.monotonic()
                try:
                    result = distributed.retrain(train, valid, str(storage), name=NAME, workers=WORKERS, rounds=ROUNDS,
                                                 every=EVERY, max_failures=MAX_FAILURES)
                    cache.update(result=result)
                except (Watchdog, Exception) as error:
                    if EXPIRED["hit"]:
                        cache.update(failed=f"retrain chưa xong sau {TIMEOUT_S} giây (trial chờ tài nguyên mãi, hoặc treo)")
                    else:
                        cache.update(failed=f"retrain lỗi: {type(error).__name__}: {str(error)[:1500]}")
                finally:
                    signal.alarm(0)
                    signal.signal(signal.SIGALRM, previous)
                    killer.stop.set()
                    killer.join(timeout=5)
                cache.update(seconds=time.monotonic() - started, victim=killer.victim, trials=trials(storage / NAME))
            pids = {r["pid"] for rows in cache["trials"].values() for r in rows if isinstance(r.get("pid"), int)}
            deadline = time.monotonic() + LEFTOVER_GRACE_S
            while alive(pids) and time.monotonic() < deadline:
                time.sleep(0.5)
            cache.update(leftover=alive(pids))
        cache.update(train=train, valid=valid)
        return cache

    return run


def finished(outcome) -> dict:
    result = outcome()
    if "failed" in result:
        pytest.fail(result["failed"], pytrace=False)
    return result


def intervals(rows: list[dict]) -> dict[int, tuple[float, float]]:
    spans: dict[int, list[float]] = {}
    for row in rows:
        pid, stamp = row.get("pid"), row.get("timestamp")
        if isinstance(pid, int) and isinstance(stamp, (int, float)):
            spans.setdefault(pid, []).append(float(stamp))
    return {pid: (min(s), max(s)) for pid, s in spans.items()}


def test_m15_trials_run_in_parallel(project, outcome):
    result = finished(outcome)
    runs = result["trials"]
    assert len(runs) >= WORKERS, f"cần ít nhất {WORKERS} trial trong {NAME}, có {len(runs)}"
    assert all(rows for rows in runs.values()), "có trial không ghi kết quả nào vào storage_path"
    spans = [(name, pid, span) for name, rows in runs.items() for pid, span in intervals(rows).items()]
    overlap = any(a[0] != b[0] and a[1] != b[1] and a[2][0] <= b[2][1] and b[2][0] <= a[2][1]
                  for i, a in enumerate(spans) for b in spans[i + 1:])
    assert overlap, f"không có hai trial nào chạy cùng lúc trên hai worker khác nhau: cần {WORKERS} worker song song"
    for name, rows in runs.items():
        last = rows[-1]
        assert last.get("trees") == ROUNDS, f"trial {name} báo `trees` cuối là {last.get('trees')}, cần {ROUNDS}"
        trees = [r.get("trees") for r in rows]
        assert all(isinstance(t, int) for t in trees), f"trial {name}: mỗi lần report cần trường `trees` (số nguyên)"
    assert not result["leftover"], f"còn tiến trình worker Ray sau khi Ray tắt: {result['leftover']}"
    print(f"\nretrain {len(runs)} trial, {result['seconds']:.1f} giây")


def test_m15_killed_worker_resumes_from_checkpoint(project, outcome):
    result = finished(outcome)
    victim = result["victim"]
    assert victim is not None, (f"không kill được worker nào: không trial nào vừa còn chạy, vừa đã báo {KILL_AFTER_REPORTS} "
                                "lần, vừa có thư mục checkpoint trong storage_path")
    rows = result["trials"].get(victim["trial"], [])
    before = [r for r in rows if r.get("pid") == victim["pid"]]
    after = [r for r in rows if r.get("pid") != victim["pid"]]
    assert after, "trial bị kill không chạy tiếp trên worker mới (cần FailureConfig max_failures > 0)"
    assert after[-1].get("trees") == ROUNDS, f"trial bị kill dừng ở {after[-1].get('trees')} cây, cần {ROUNDS}"
    saved = [r["trees"] for r in before if r.get("checkpoint_dir_name") and isinstance(r.get("trees"), int)]
    assert saved, "trước khi bị kill, trial chưa report checkpoint nào"
    first_after = after[0].get("trees")
    resumed = first_after == max(saved) + EVERY and len(after) == (ROUNDS - max(saved)) // EVERY
    assert resumed, (f"sau khi worker bị kill, trial chạy lại với các mốc cây {[r.get('trees') for r in after]}; checkpoint "
                     f"mới nhất trước đó ở {max(saved)} cây: phần chạy lại phải tiếp từ checkpoint mới nhất, mỗi lần "
                     f"report thêm đúng `every` = {EVERY} cây")
    print(f"\nkill pid {victim['pid']} sau {victim['reports_before']} lần report; checkpoint {max(saved)} cây, "
          f"chạy lại từ {first_after} cây")


def reference_metrics(result: dict) -> tuple[dict, float]:
    features = need("features", "build_features")
    train = need("train", "train", "evaluate")
    X, y = features.build_features(result["train"])
    X_valid, y_valid = features.build_features(result["valid"])
    single = train.train(X, y, {"max_iter": ROUNDS, "random_state": 0})
    pairs = result["train"].groupby(["PULocationID", "DOLocationID"])["duration_s"].median()
    keys = pd.MultiIndex.from_frame(result["valid"][["PULocationID", "DOLocationID"]])
    guess = pairs.reindex(keys).fillna(result["train"]["duration_s"].median()).to_numpy()
    zone_mae = float(np.mean(np.abs(guess - y_valid.to_numpy())))
    return train.evaluate(single, X_valid, y_valid), zone_mae


def test_m15_model_passes_baseline(project, outcome):
    result = finished(outcome)
    retrained = result["result"]
    features = need("features", "build_features")
    train = need("train", "evaluate")
    X_valid, y_valid = features.build_features(result["valid"])
    own = train.evaluate(retrained.model, X_valid, y_valid)
    for key in ("mae", "p90_abs_err", "mae_airport"):
        assert float(retrained.metrics.get(key, math.nan)) == pytest.approx(own[key], rel=1e-6), \
            f"metrics[{key!r}] phải là metric của chính model trả về, đo trên valid bằng eta.train.evaluate"
    reference, zone_mae = reference_metrics(result)
    print(f"\nRay: mae {own['mae']:.1f}, mae_airport {own['mae_airport']:.1f}; một tiến trình: mae {reference['mae']:.1f}, "
          f"mae_airport {reference['mae_airport']:.1f}; trung vị cặp zone: {zone_mae:.1f}")
    assert own["mae"] <= reference["mae"] * (1 + MAE_REGRESSION), \
        f"mae {own['mae']:.1f} tệ hơn model train một tiến trình ({reference['mae']:.1f}) quá {MAE_REGRESSION:.0%}"
    assert own["mae_airport"] <= reference["mae_airport"] * (1 + AIRPORT_REGRESSION), \
        f"mae_airport {own['mae_airport']:.1f} tệ hơn model train một tiến trình ({reference['mae_airport']:.1f}) quá {AIRPORT_REGRESSION:.0%}"
    assert own["mae"] < ZONE_BASELINE_MARGIN * zone_mae, \
        f"mae {own['mae']:.1f} chưa thắng rõ baseline trung vị cặp zone ({zone_mae:.1f})"
    params = retrained.params
    assert isinstance(params, dict) and int(params.get("max_iter", -1)) == ROUNDS, \
        f"params phải là tham số model của trial tốt nhất, gồm max_iter = {ROUNDS}"


def test_m15_registered_with_lineage(project, outcome, tmp_path):
    result = finished(outcome)
    retrained = result["result"]
    distributed = need("distributed", "register")
    config = need("config", "Config")
    features = need("features", "build_features")
    from mlflow import MlflowClient

    uri, name = local_registry(tmp_path, "eta-m15")
    data_version = f"m15-{uuid.uuid4().hex[:8]}"
    cfg = config.Config(data_dir=tmp_path, months=["2019-03"], sample_rows=ROWS, seed=0, model_params={},
                        mlflow_uri=uri, model_name=name)
    version = str(distributed.register(retrained, cfg, data_version))
    client = MlflowClient(tracking_uri=uri)
    found = client.get_model_version(name, version)
    tags = found.tags
    assert tags.get("data_version") == data_version, f"model version cần tag data_version = chuỗi truyền vào, có {tags}"
    assert tags.get("git_commit"), f"model version cần tag git_commit không rỗng, có {tags}"
    run = client.get_run(found.run_id)
    assert run.data.metrics.get("mae") == pytest.approx(retrained.metrics["mae"], rel=1e-6), \
        "run của version phải log metric mae của model đã retrain"
    for key, value in retrained.params.items():
        assert run.data.params.get(f"model.{key}") == str(value), \
            f"run phải log tham số model.{key} = {value} của trial tốt nhất (như M04)"
    loaded = mlflow.sklearn.load_model(f"models:/{name}/{version}")
    X_valid, _ = features.build_features(result["valid"])
    assert np.allclose(loaded.predict(X_valid), retrained.model.predict(X_valid)), \
        "model trong registry phải dự đoán đúng như model retrain trả về"

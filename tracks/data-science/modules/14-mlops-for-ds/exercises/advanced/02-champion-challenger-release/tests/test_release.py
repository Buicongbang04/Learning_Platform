import os

os.environ.setdefault("MLFLOW_DISABLE_AGENT_HINT", "1")

import numpy as np
import pandas as pd
import pytest
from mlflow import MlflowClient
from mlflow.exceptions import MlflowException
from sklearn.metrics import roc_auc_score

from testkit import Exercise

ex = Exercise(__file__)


def make_shadow_log(n: int, seed: int, challenger_gain: float = 0.5, labeled_share: float = 0.7,
                    challenger_latency: float = 8.0) -> pd.DataFrame:
    """Log shadow: mỗi request được chấm bởi cả champion (trả cho khách) và challenger (chỉ ghi lại)."""
    rng = np.random.default_rng(seed)
    y = (rng.random(n) < 0.12).astype(float)
    signal = rng.normal(0, 1, n) + 1.2 * y + rng.normal(0, 1.2, n)      # phần hai model cùng thấy
    champ = 1 / (1 + np.exp(-(-2.2 + 0.8 * signal)))
    # challenger = champion + tín hiệu thêm ở đơn xấu + chút nhiễu riêng
    chall = 1 / (1 + np.exp(-(-2.2 + 0.8 * (signal + challenger_gain * y + rng.normal(0, 0.15, n)))))
    label = np.where(rng.random(n) < labeled_share, y, np.nan)     # review chưa về thì chưa có nhãn
    return pd.DataFrame({
        "order_id": [f"o{i}" for i in range(n)],
        "champion_score": champ, "challenger_score": chall,
        "champion_latency_ms": rng.gamma(4, 1.5, n), "challenger_latency_ms": rng.gamma(4, challenger_latency / 4, n),
        "label": label,
    })


@pytest.fixture(scope="module")
def release():
    return ex.module("release.py")


def test_shadow_report_values(release):
    log = make_shadow_log(5000, seed=1)
    rep = release.shadow_report(log, threshold=0.3)
    labeled = log.dropna(subset=["label"])
    assert rep["n"] == 5000
    assert rep["n_labeled"] == len(labeled)
    assert rep["auc_champion"] == pytest.approx(roc_auc_score(labeled.label, labeled.champion_score))
    assert rep["auc_challenger"] == pytest.approx(roc_auc_score(labeled.label, labeled.challenger_score))
    flips = ((log.champion_score >= 0.3) != (log.challenger_score >= 0.3)).mean()
    assert rep["flip_rate"] == pytest.approx(flips)
    assert rep["p95_latency_challenger_ms"] == pytest.approx(np.percentile(log.challenger_latency_ms, 95))
    assert rep["p95_latency_champion_ms"] == pytest.approx(np.percentile(log.champion_latency_ms, 95))
    assert rep["score_psi"] >= 0


def test_shadow_report_no_labels_yet(release):
    log = make_shadow_log(800, seed=2, labeled_share=0.0)
    rep = release.shadow_report(log, threshold=0.3)
    assert rep["n_labeled"] == 0
    assert np.isnan(rep["auc_champion"]) and np.isnan(rep["auc_challenger"])


def test_identical_models_have_zero_flip_and_psi(release):
    log = make_shadow_log(2000, seed=3)
    log["challenger_score"] = log["champion_score"]
    rep = release.shadow_report(log, threshold=0.3)
    assert rep["flip_rate"] == 0 and rep["score_psi"] == pytest.approx(0.0, abs=1e-12)


def test_decision_promote(release):
    rep = release.shadow_report(make_shadow_log(6000, seed=4, challenger_gain=0.8), threshold=0.3)
    assert rep["auc_challenger"] - rep["auc_champion"] > 0.01
    assert release.promotion_decision(rep) == "promote"


def test_decision_need_more_data(release):
    rep = release.shadow_report(make_shadow_log(6000, seed=5, challenger_gain=0.8, labeled_share=0.05), threshold=0.3)
    assert release.promotion_decision(rep) == "need_more_data"


def test_decision_keep_when_not_better_or_too_slow(release):
    same = release.shadow_report(make_shadow_log(6000, seed=6, challenger_gain=0.0), threshold=0.3)
    assert release.promotion_decision(same) == "keep"
    slow = release.shadow_report(make_shadow_log(6000, seed=7, challenger_gain=0.8, challenger_latency=40.0), threshold=0.3)
    assert slow["p95_latency_challenger_ms"] > 50
    assert release.promotion_decision(slow) == "keep"


def test_decision_manual_review_when_behaviour_changes_a_lot(release):
    rep = {"n": 6000, "n_labeled": 4000, "auc_champion": 0.70, "auc_challenger": 0.73, "score_psi": 0.6,
           "flip_rate": 0.35, "p95_latency_champion_ms": 12.0, "p95_latency_challenger_ms": 14.0}
    assert release.promotion_decision(rep) == "manual_review"
    assert release.promotion_decision(rep, max_flip_rate=0.5) == "promote"


def _registry(tmp_path, n_versions: int):
    uri = f"sqlite:///{tmp_path / 'reg.db'}"
    client = MlflowClient(uri)
    client.create_registered_model("bad-review")
    for i in range(n_versions):
        client.create_model_version("bad-review", source=(tmp_path / f"v{i + 1}").as_uri())
    return uri, client


def test_apply_promote_moves_aliases(release, tmp_path):
    uri, client = _registry(tmp_path, 2)
    client.set_registered_model_alias("bad-review", "champion", "1")
    client.set_registered_model_alias("bad-review", "challenger", "2")
    aliases = release.apply_decision(uri, "bad-review", challenger_version=2, decision="promote")
    assert aliases == {"champion": 2, "previous_champion": 1}
    assert str(client.get_model_version_by_alias("bad-review", "champion").version) == "2"
    assert str(client.get_model_version_by_alias("bad-review", "previous_champion").version) == "1"
    with pytest.raises(MlflowException):
        client.get_model_version_by_alias("bad-review", "challenger")


@pytest.mark.parametrize("decision", ["keep", "need_more_data", "manual_review"])
def test_apply_other_decisions_change_nothing(release, tmp_path, decision):
    uri, client = _registry(tmp_path, 2)
    client.set_registered_model_alias("bad-review", "champion", "1")
    client.set_registered_model_alias("bad-review", "challenger", "2")
    aliases = release.apply_decision(uri, "bad-review", challenger_version=2, decision=decision)
    assert aliases == {"champion": 1, "challenger": 2}


def test_rollback(release, tmp_path):
    uri, client = _registry(tmp_path, 3)
    client.set_registered_model_alias("bad-review", "champion", "1")
    release.apply_decision(uri, "bad-review", challenger_version=2, decision="promote")
    release.apply_decision(uri, "bad-review", challenger_version=3, decision="promote")
    assert str(client.get_model_version_by_alias("bad-review", "champion").version) == "3"
    assert release.rollback(uri, "bad-review") == 2
    assert str(client.get_model_version_by_alias("bad-review", "champion").version) == "2"
    with pytest.raises(ValueError):
        release.rollback(uri, "bad-review")            # không rollback hai lần liên tiếp mà không có đích rõ ràng


def test_release_doc_written():
    text = ex.read("RELEASE.md")
    assert "TODO" not in text
    assert len(text.split()) >= 450

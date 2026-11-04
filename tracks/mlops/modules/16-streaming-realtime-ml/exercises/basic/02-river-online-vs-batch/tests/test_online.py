import numpy as np
import pytest
from sklearn.linear_model import LogisticRegression

from testkit import Exercise

ex = Exercise(__file__)
N = 4_000
TRAIN_N = 1_000
W_BEFORE = np.array([2.0, -1.0, 0.5])
W_AFTER = np.array([-1.5, 2.0, 0.5])


@pytest.fixture(scope="module")
def online():
    return ex.module("online.py")


def generate(drift, seed, n=N):
    rng = np.random.default_rng(seed)
    X = rng.normal(size=(n, 3))
    noise = rng.normal(0, 0.5, n)
    stream = []
    for i in range(n):
        w = W_AFTER if drift and i >= n // 2 else W_BEFORE
        stream.append(({f"x{j}": float(X[i, j]) for j in range(3)}, int(X[i] @ w + noise[i] > 0)))
    return stream


class Spy:
    def __init__(self):
        self.calls = []
        self.memory = {}

    def predict_one(self, x):
        self.calls.append(("predict", x["i"]))
        return self.memory.get(x["i"], 0)

    def learn_one(self, x, y):
        self.calls.append(("learn", x["i"]))
        self.memory[x["i"]] = y


def test_online_model_learns_one_sample_at_a_time(online):
    model = online.make_online_model()
    assert type(model).__module__.split(".")[0] == "river"
    x, y = generate(False, 9, 50)[0]
    model.learn_one(x, y)
    assert model.predict_one(x) in (0, 1, True, False)


def test_prequential_predicts_before_learning(online):
    spy = Spy()
    stream = [({"i": i}, 1) for i in range(5)]
    assert online.prequential(stream, spy) == 0.0
    assert spy.calls == [(kind, i) for i in range(5) for kind in ("predict", "learn")]


def test_prequential_scores_from_start(online):
    stream = [({"i": i}, y) for i, y in enumerate([0, 0, 0, 1, 1])]
    assert online.prequential(stream, Spy()) == pytest.approx(0.6)
    spy = Spy()
    assert online.prequential(stream, spy, start=3) == 0.0
    assert len(spy.calls) == 10


def test_frozen_batch_matches_sklearn(online):
    stream = generate(True, 5)
    X = np.array([[x[k] for k in sorted(x)] for x, _ in stream])
    y = np.array([label for _, label in stream])
    expected = (LogisticRegression().fit(X[:TRAIN_N], y[:TRAIN_N]).predict(X[TRAIN_N:]) == y[TRAIN_N:]).mean()
    assert online.frozen_batch(stream, TRAIN_N) == pytest.approx(expected, abs=0.005)


class AlwaysOne:
    def predict_one(self, x):
        return 1

    def learn_one(self, x, y):
        pass


def test_compare_scores_online_on_the_same_segment(online, monkeypatch):
    monkeypatch.setattr(online, "make_online_model", AlwaysOne)
    stream = generate(False, 11, 2_000)
    labels = [y for _, y in stream]
    result = online.compare(stream, 500)
    assert result["online"] == pytest.approx(sum(labels[500:]) / 1_500)


@pytest.mark.parametrize("seed", [0, 1, 2])
def test_online_wins_under_drift(online, seed):
    result = online.compare(generate(True, seed), TRAIN_N)
    assert set(result) == {"online", "batch"}
    assert result["online"] >= result["batch"] + 0.15
    assert online.choose(result) == "online"


@pytest.mark.parametrize("seed", [0, 1, 2])
def test_batch_holds_when_stable(online, seed):
    result = online.compare(generate(False, seed), TRAIN_N)
    assert result["batch"] >= 0.9
    assert result["batch"] - 0.05 <= result["online"] <= result["batch"] + 0.02
    assert online.choose(result) == "batch"


def test_choose_margin(online):
    assert online.choose({"online": 0.90, "batch": 0.86}) == "batch"
    assert online.choose({"online": 0.92, "batch": 0.86}) == "online"
    assert online.choose({"online": 0.75, "batch": 0.5}, margin=0.25) == "batch"
    assert online.choose({"online": 0.875, "batch": 0.5}, margin=0.25) == "online"
    assert online.choose({"online": 0.70, "batch": 0.86}, margin=0.0) == "batch"

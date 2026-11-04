"""Online learning với River so với model batch huấn luyện một lần, trên cùng một luồng."""

from river import linear_model, optim, preprocessing
from sklearn.linear_model import LogisticRegression


def make_online_model():
    return preprocessing.StandardScaler() | linear_model.LogisticRegression(optimizer=optim.SGD(0.05))


def prequential(stream, model, start: int = 0) -> float:
    correct = total = 0
    for i, (x, y) in enumerate(stream):
        y_pred = model.predict_one(x)
        if i >= start:
            correct += int(y_pred == y)
            total += 1
        model.learn_one(x, y)
    return correct / total if total else float("nan")


def frozen_batch(stream, train_n: int) -> float:
    names = sorted(stream[0][0])
    X = [[x[k] for k in names] for x, _ in stream]
    y = [label for _, label in stream]
    model = LogisticRegression().fit(X[:train_n], y[:train_n])
    rest = model.predict(X[train_n:])
    return float(sum(int(p == t) for p, t in zip(rest, y[train_n:])) / len(rest))


def compare(stream, train_n: int) -> dict:
    return {"online": prequential(stream, make_online_model(), start=train_n), "batch": frozen_batch(stream, train_n)}


def choose(result: dict, margin: float = 0.05) -> str:
    return "online" if result["online"] > result["batch"] + margin else "batch"

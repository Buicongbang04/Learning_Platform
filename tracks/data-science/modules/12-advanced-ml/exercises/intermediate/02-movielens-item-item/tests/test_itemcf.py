import numpy as np
import pandas as pd
import pytest

from testkit import Exercise

ex = Exercise(__file__)


@pytest.fixture(scope="module")
def nb():
    return ex.notebook("itemcf.ipynb")


SMALL = pd.DataFrame({
    "userId":    [1, 1, 1, 1, 1, 2, 2, 2, 3, 3, 3],
    "movieId":   [10, 20, 30, 40, 50, 10, 20, 60, 30, 10, 40],
    "rating":    [4.0, 3.5, 5.0, 2.0, 4.5, 3.0, 4.0, 5.0, 1.0, 4.0, 3.0],
    "timestamp": [5, 1, 3, 3, 9, 7, 2, 4, 1, 1, 8],
})


def random_ratings(seed: int, n_users: int = 30, n_items: int = 25) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    rows = []
    for u in range(1, n_users + 1):
        k = rng.integers(3, 12)
        # vài item phổ biến hơn để có cấu trúc
        items = rng.choice(np.arange(100, 100 + n_items), size=k, replace=False,
                           p=np.linspace(2, 1, n_items) / np.linspace(2, 1, n_items).sum())
        for m in items:
            rows.append((u, int(m), float(rng.integers(1, 6)), int(rng.integers(0, 1000))))
    return pd.DataFrame(rows, columns=["userId", "movieId", "rating", "timestamp"])


def brute_force_scores(train: pd.DataFrame, user) -> dict:
    """Điểm item-item của mọi phim user chưa xem, tính bằng ma trận dày."""
    users = sorted(train.userId.unique())
    items = sorted(train.movieId.unique())
    X = np.zeros((len(users), len(items)))
    for u, m in zip(train.userId, train.movieId):
        X[users.index(u), items.index(m)] = 1
    Xn = X / np.linalg.norm(X, axis=0)
    hist = np.flatnonzero(X[users.index(user)])
    score = (Xn.T @ Xn)[:, hist].sum(axis=1)
    return {items[j]: score[j] for j in range(len(items)) if j not in hist}


def assert_top_k(recs: list, scores: dict, k: int):
    """recs phải là k phim điểm cao nhất, đúng thứ tự. So điểm với sai số 1e-9 để không phụ thuộc thứ
    tự cộng số thực (hai phim điểm bằng nhau có thể đổi chỗ)."""
    expected = sorted(scores, key=lambda m: (-round(scores[m], 9), m))[:k]
    assert len(recs) == len(expected)
    assert len(set(recs)) == len(recs)
    for got, want in zip(recs, expected):
        assert got in scores, f"gợi ý phim đã xem {got}"
        assert scores[got] == pytest.approx(scores[want], abs=1e-9)


def test_split_takes_newest_fraction_per_user(nb):
    train, test = nb.split_last_fraction(SMALL, frac=0.2)
    # mỗi user: ceil(0.2 · n) = 1 dòng test, là dòng có timestamp lớn nhất (9, 7, 8)
    assert sorted(zip(test.userId, test.movieId)) == [(1, 50), (2, 10), (3, 40)]
    assert len(train) + len(test) == len(SMALL)
    assert set(train.columns) == set(SMALL.columns)


def test_split_tie_break_by_movie_id(nb):
    df = pd.DataFrame({"userId": [7, 7, 7, 7], "movieId": [3, 1, 4, 2], "rating": [1.0] * 4, "timestamp": [5] * 4})
    _, test = nb.split_last_fraction(df, frac=0.5)
    assert sorted(test.movieId) == [3, 4]


def test_popularity_excludes_seen_and_breaks_ties(nb):
    recs = nb.popularity_recs(SMALL, [1, 2, 3, 99], k=3)
    # số rating: 10 → 3, 20 → 2, 30 → 2, 40 → 2, 50 → 1, 60 → 1
    assert recs[1] == [60]                    # user 1 đã xem 10..50
    assert recs[2] == [30, 40, 50]
    assert recs[3] == [20, 50, 60]
    assert recs[99] == [10, 20, 30]           # user lạ: danh sách phổ biến


def test_item_item_hand_example(nb):
    recs = nb.item_item_recs(SMALL, [2, 3], k=2)
    for u in (2, 3):
        assert_top_k(recs[u], brute_force_scores(SMALL, u), 2)


@pytest.mark.parametrize("seed", [0, 1, 2])
def test_item_item_matches_brute_force(nb, seed):
    df = random_ratings(seed)
    users = sorted(df.userId.unique())
    recs = nb.item_item_recs(df, users, k=5)
    for u in users:
        assert_top_k(recs[u], brute_force_scores(df, u), 5)


def test_item_item_never_recommends_seen_and_unknown_user_gets_empty(nb):
    df = random_ratings(5)
    recs = nb.item_item_recs(df, [1, 2, 12345], k=10)
    for u in (1, 2):
        assert not set(recs[u]) & set(df[df.userId == u].movieId)
        assert len(recs[u]) == len(set(recs[u]))
    assert recs[12345] == []


def test_evaluate(nb):
    test = pd.DataFrame({"userId": [1, 1, 2, 3], "movieId": [10, 20, 30, 40]})
    recs = {1: [10, 99, 20], 2: [31, 32], 9: [40]}
    out = nb.evaluate(recs, test, k=2)
    # user 1: top-2 = [10, 99] → 1 hit; user 2: 0; user 3 không có gợi ý → 0
    assert out["precision"] == pytest.approx((1 / 2) / 3)
    assert out["recall"] == pytest.approx((1 / 2) / 3)
    assert out["coverage"] == 5             # {10, 99, 31, 32, 40}: cắt ở k = 2


def test_real_movielens(nb):
    ratings = pd.read_csv(ex.dataset("movielens") / "ratings.csv")
    train, test = nb.split_last_fraction(ratings)
    assert (len(train), len(test)) == (80419, 20417)
    users = sorted(test.userId.unique())
    pop = nb.evaluate(nb.popularity_recs(train, users), test)
    ii = nb.evaluate(nb.item_item_recs(train, users), test)
    assert pop["precision"] == pytest.approx(0.0748, abs=0.001)
    assert ii["precision"] == pytest.approx(0.0970, abs=0.001)
    assert ii["recall"] > pop["recall"]
    assert ii["coverage"] > 4 * pop["coverage"]

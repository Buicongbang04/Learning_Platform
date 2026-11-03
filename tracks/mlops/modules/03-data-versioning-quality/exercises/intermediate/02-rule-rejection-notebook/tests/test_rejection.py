import pandas as pd

from testkit import Exercise

ex = Exercise(__file__)
RULES = ["duration", "distance", "pickup_month", "zone_range", "zone_unknown"]


def small():
    t = pd.Timestamp
    return pd.DataFrame(
        {
            "tpep_pickup_datetime": [t("2019-01-05 10:00"), t("2019-01-05 10:00"), t("2018-12-31 23:00"), t("2019-01-31 23:59"),
                                     t("2019-01-07 09:00"), t("2019-01-08 09:00"), t("2019-02-01 00:00")],
            "tpep_dropoff_datetime": [t("2019-01-05 10:10"), t("2019-01-05 09:50"), t("2018-12-31 23:20"), t("2019-02-01 00:10"),
                                      t("2019-01-07 09:00"), t("2019-01-08 09:30"), t("2019-02-01 00:05")],
            "trip_distance": [2.0, 1.0, 3.0, 0.0, 0.0, 1.5, 2.0],
            "PULocationID": [100, 100, 100, 265, 0, 50, 264],
            "DOLocationID": [200, 200, 200, 7, 266, 50, 1],
        }
    )


def test_rule_masks_flag_each_rule():
    nb = ex.notebook("rejection.ipynb")
    masks = nb.rule_masks(small(), "2019-01")
    assert list(masks) == RULES
    assert masks["duration"].tolist() == [False, True, False, False, True, False, False]
    assert masks["distance"].tolist() == [False, False, False, True, True, False, False]
    assert masks["pickup_month"].tolist() == [False, False, True, False, False, False, True]
    assert masks["zone_range"].tolist() == [False, False, False, False, True, False, False]
    assert masks["zone_unknown"].tolist() == [False, False, False, True, False, False, True]


def test_counts_are_independent_and_kept_is_union():
    nb = ex.notebook("rejection.ipynb")
    df = small()
    assert nb.rejection_counts(df, "2019-01") == {
        "duration": 2, "distance": 2, "pickup_month": 2, "zone_range": 1, "zone_unknown": 2,
    }
    assert nb.rows_kept(df, "2019-01") == 2


def test_load_sample_columns_size_and_seed(tmp_path):
    nb = ex.notebook("rejection.ipynb")
    path = tmp_path / "month.parquet"
    big = pd.DataFrame({c: range(1000) for c in nb.COLUMNS})
    big["extra_column"] = 1
    big.to_parquet(path)
    a = nb.load_sample(path, n=100, seed=0)
    b = nb.load_sample(path, n=100, seed=0)
    c = nb.load_sample(path, n=100, seed=1)
    assert list(a.columns) == nb.COLUMNS
    assert len(a) == 100
    pd.testing.assert_frame_equal(a, b)
    assert not a.index.equals(c.index)


def test_real_month_counts():
    root = ex.dataset("nyc-tlc")
    nb = ex.notebook("rejection.ipynb")
    sample = nb.load_sample(root / "yellow_tripdata_2019-01.parquet")
    assert len(sample) == 200_000
    assert nb.rejection_counts(sample, nb.MONTH) == {
        "duration": 172, "distance": 1416, "pickup_month": 13, "zone_range": 0, "zone_unknown": 4826,
    }
    assert nb.rows_kept(sample, nb.MONTH) == 194142

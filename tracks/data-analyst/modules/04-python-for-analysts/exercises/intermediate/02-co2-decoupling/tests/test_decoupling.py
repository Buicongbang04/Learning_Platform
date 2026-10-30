import numpy as np
import pandas as pd
import pytest

from testkit import Exercise

ex = Exercise(__file__)
COLS = ["co2", "consumption_co2", "gdp"]


@pytest.fixture(scope="module")
def nb():
    return ex.notebook("decoupling.ipynb")


def tiny():
    rows = [
        # country, year, iso, co2, cons, gdp, pop
        ("A", 2005, "AAA", 100.0, 100.0, 1000.0, 20e6),
        ("A", 2022, "AAA", 80.0, 110.0, 1500.0, 21e6),
        ("B", 2005, "BBB", 50.0, 60.0, 500.0, 30e6),
        ("B", 2022, "BBB", 60.0, 66.0, 750.0, 32e6),
        ("C", 2005, "CCC", 10.0, 10.0, 100.0, 5e6),       # dân số năm cuối < 10 triệu
        ("C", 2022, "CCC", 5.0, 5.0, 200.0, 6e6),
        ("D", 2005, "DDD", 40.0, np.nan, 400.0, 12e6),    # thiếu consumption năm đầu
        ("D", 2022, "DDD", 30.0, 30.0, 500.0, 12e6),
        ("E", 2005, "EEE", 20.0, 20.0, 300.0, 15e6),
        ("E", 2022, "EEE", 30.0, 25.0, 270.0, 9e6),       # dân số năm đầu lớn, năm cuối < 10 triệu
        ("F", 2005, "FFF", 30.0, 30.0, 300.0, 11e6),
        ("F", 2022, "FFF", 15.0, 24.0, 240.0, 11e6),
        ("World", 2005, None, 250.0, 250.0, 3000.0, 6e9),
        ("World", 2022, None, 220.0, 260.0, 4000.0, 8e9),
        ("A", 2010, "AAA", 90.0, 95.0, 1200.0, 20e6),
    ]
    return pd.DataFrame(rows, columns=["country", "year", "iso_code", "co2", "consumption_co2", "gdp", "population"])


def test_period_change(nb):
    df = tiny()
    before = df.copy()
    out = nb.period_change(df, 2005, 2022, COLS)
    pd.testing.assert_frame_equal(df, before)
    assert list(out.columns) == COLS
    assert out.index.name == "country"
    assert list(out.index) == ["A", "B", "F"]
    assert out.loc["A"].tolist() == pytest.approx([-0.2, 0.1, 0.5])
    assert out.loc["B"].tolist() == pytest.approx([0.2, 0.1, 0.5])
    assert out.loc["F"].tolist() == pytest.approx([-0.5, -0.2, -0.2])


def test_period_change_population_threshold_and_cols(nb):
    out = nb.period_change(tiny(), 2005, 2022, ["co2", "gdp"], min_population=1e6)
    assert list(out.columns) == ["co2", "gdp"]
    assert list(out.index) == ["A", "B", "C", "D", "E", "F"]      # D đủ dữ liệu vì không cần consumption
    assert out.loc["E"].tolist() == pytest.approx([0.5, -0.1])


def test_period_change_rejects_duplicate_country_year(nb):
    df = pd.concat([tiny(), tiny().iloc[[0]]], ignore_index=True)
    with pytest.raises(ValueError):      # merge validate="one_to_one" báo MergeError (một ValueError)
        nb.period_change(df, 2005, 2022, COLS)


def change_fixture():
    return pd.DataFrame({
        "co2": [-0.1, 0.2, 0.5, 0.3, -0.3, 0.5],
        "consumption_co2": [0.05, -0.1, 0.6, 0.3, -0.2, 0.2],
        "gdp": [0.4, 0.5, 0.4, 0.3, 0.0, -0.1],
    }, index=pd.Index(["P", "Q", "R", "S", "T", "U"], name="country"))


def test_classify(nb):
    ch = change_fixture()
    out = nb.classify(ch)
    assert out.name == "decoupling"
    assert list(out.index) == list(ch.index)
    # S: co2 tăng bằng gdp -> coupled; T: gdp = 0 -> gdp_decline dù co2 giảm
    assert out.tolist() == ["absolute", "relative", "coupled", "coupled", "gdp_decline", "gdp_decline"]
    assert nb.classify(ch, "consumption_co2").tolist() == [
        "relative", "absolute", "coupled", "coupled", "gdp_decline", "gdp_decline"]


def test_decoupling_table(nb):
    ch = change_fixture()
    before = ch.copy()
    out = nb.decoupling_table(ch)
    pd.testing.assert_frame_equal(ch, before)
    assert list(out.columns) == [*COLS, "production", "consumption", "offshoring"]
    assert out["offshoring"].tolist() == [True, False, False, False, False, False]
    assert out["production"].tolist()[:2] == ["absolute", "relative"]


@pytest.fixture(scope="module")
def co2():
    return pd.read_csv(ex.dataset("owid-co2") / "owid-co2-data.csv")


def test_real_period_change(nb, co2):
    change = nb.period_change(co2, 2005, 2022, COLS)
    assert len(change) == 75
    assert change.loc["United Kingdom"].tolist() == pytest.approx([-0.4547, -0.3433, 0.2097], abs=1e-3)
    assert change.loc["Vietnam", "co2"] == pytest.approx(2.3665, abs=1e-3)


def test_real_decoupling(nb, co2):
    change = nb.period_change(co2, 2005, 2022, COLS)
    table = nb.decoupling_table(change)
    assert table["production"].value_counts().to_dict() == {
        "relative": 39, "absolute": 17, "coupled": 16, "gdp_decline": 3}
    both = ((table["production"] == "absolute") & (table["consumption"] == "absolute")).sum()
    assert both == 14
    assert set(table.index[table["offshoring"]]) == {"Australia", "Mexico", "Poland"}
    assert table.loc["Vietnam", ["production", "consumption"]].tolist() == ["coupled", "coupled"]
    assert table.loc["China", "production"] == "relative"
    assert set(table.index[table["production"] == "gdp_decline"]) == {"Greece", "Ukraine", "Venezuela"}
    wide = nb.period_change(co2, 2005, 2022, COLS, min_population=1e6)
    assert len(wide) == 117 and (nb.classify(wide) == "absolute").sum() == 37

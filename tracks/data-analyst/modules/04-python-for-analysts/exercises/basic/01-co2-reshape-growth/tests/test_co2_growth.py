import numpy as np
import pandas as pd
import pytest

from testkit import Exercise

ex = Exercise(__file__)
ASEAN = ["Brunei", "Cambodia", "East Timor", "Indonesia", "Laos", "Malaysia", "Myanmar", "Philippines",
         "Singapore", "Thailand", "Vietnam"]


@pytest.fixture(scope="module")
def nb():
    return ex.notebook("co2_growth.ipynb")


def tiny():
    # hai nước, một dòng tổng (World, iso_code rỗng); nước B thiếu năm 2021
    return pd.DataFrame({
        "country": ["A", "A", "A", "B", "B", "World", "World", "World"],
        "year": [2020, 2021, 2022, 2020, 2022, 2020, 2021, 2022],
        "iso_code": ["AAA", "AAA", "AAA", "BBB", "BBB", None, None, None],
        "co2": [100.0, 110.0, 121.0, 50.0, 72.0, 150.0, 160.0, 193.0],
    }, index=[10, 11, 12, 20, 21, 30, 31, 32])


def test_countries_only_drops_aggregates(nb):
    df = tiny()
    before = df.copy()
    out = nb.countries_only(df)
    pd.testing.assert_frame_equal(df, before)
    assert list(out.index) == [10, 11, 12, 20, 21]
    assert set(out.country) == {"A", "B"}
    assert list(out.columns) == list(df.columns)


def test_to_wide_shape_order_and_missing(nb):
    df = tiny()[lambda d: d.iso_code.notna()]
    wide = nb.to_wide(df, "co2")
    assert wide.index.name == "country" and wide.columns.name == "year"
    assert list(wide.columns) == [2020, 2021, 2022]
    assert wide.loc["A"].tolist() == [100.0, 110.0, 121.0]
    assert np.isnan(wide.loc["B", 2021])
    picked = nb.to_wide(df, "co2", countries=["B", "C", "A"], years=[2022, 2020])
    assert list(picked.index) == ["B", "C", "A"]
    assert list(picked.columns) == [2022, 2020]
    assert picked.loc["B"].tolist() == [72.0, 50.0]
    assert picked.loc["C"].isna().all()


def test_to_wide_rejects_duplicate_keys(nb):
    df = pd.concat([tiny(), tiny().iloc[[0]]])
    with pytest.raises(ValueError):
        nb.to_wide(df, "co2")


def test_to_long_roundtrip(nb):
    df = tiny()[lambda d: d.iso_code.notna()]
    long = nb.to_long(nb.to_wide(df, "co2"), "co2")
    assert list(long.columns) == ["country", "year", "co2"]
    assert list(long.index) == list(range(5))
    assert long["year"].tolist() == [2020, 2021, 2022, 2020, 2022]
    assert pd.api.types.is_integer_dtype(long["year"])
    assert long["co2"].tolist() == [100.0, 110.0, 121.0, 50.0, 72.0]


def test_growth_table(nb):
    wide = pd.DataFrame({2020: [100.0, 50.0, np.nan, 0.0], 2022: [121.0, 72.0, 5.0, 3.0]},
                        index=pd.Index(["A", "B", "C", "D"], name="country"))
    out = nb.growth_table(wide, 2020, 2022)
    assert list(out.columns) == ["start", "end", "pct_change", "cagr"]
    assert list(out.index) == ["B", "A"]          # C thiếu năm đầu, D bắt đầu từ 0: bỏ; sắp cagr giảm dần
    assert out.loc["A", "pct_change"] == pytest.approx(0.21)
    assert out.loc["A", "cagr"] == pytest.approx(0.10)
    assert out.loc["B", "cagr"] == pytest.approx(0.20)


def test_yoy_uses_previous_year_not_previous_row(nb):
    long = pd.DataFrame({
        "country": ["B", "A", "B", "A", "A"],
        "year": [2022, 2021, 2020, 2020, 2022],
        "co2": [72.0, 110.0, 50.0, 100.0, 121.0],
        "note": list("vwxyz"),
    }, index=[5, 6, 7, 8, 9])
    before = long.copy()
    out = nb.yoy(long, "co2")
    pd.testing.assert_frame_equal(long, before)
    assert list(out.index) == [5, 6, 7, 8, 9]
    assert out["note"].tolist() == list("vwxyz")
    # B 2022: không có 2021 -> NaN dù có dòng 2020 ngay trước
    assert np.isnan(out.loc[5, "yoy"])
    assert out.loc[6, "yoy"] == pytest.approx(0.10)
    assert np.isnan(out.loc[7, "yoy"]) and np.isnan(out.loc[8, "yoy"])
    assert out.loc[9, "yoy"] == pytest.approx(0.10)


@pytest.fixture(scope="module")
def nations(nb):
    co2 = pd.read_csv(ex.dataset("owid-co2") / "owid-co2-data.csv")
    return co2, nb


def test_real_countries_only(nations):
    co2, nb = nations
    out = nb.countries_only(co2)
    assert out.country.nunique() == 218
    assert out.loc[out.year == 2024, "co2"].sum() == pytest.approx(37_398.07, abs=0.1)
    assert "World" not in set(out.country)


def test_real_asean_growth(nations):
    co2, nb = nations
    wide = nb.to_wide(nb.countries_only(co2), "co2", countries=ASEAN, years=[2014, 2024])
    out = nb.growth_table(wide, 2014, 2024)
    assert list(out.index[:3]) == ["Laos", "Cambodia", "Vietnam"]
    assert out.index[-1] == "Thailand"
    assert out.loc["Vietnam", "pct_change"] == pytest.approx(1.0602, abs=1e-4)
    assert out.loc["Vietnam", "cagr"] == pytest.approx(0.07496, abs=1e-5)
    assert wide[2024].sum() == pytest.approx(2_060.54, abs=0.01)


def test_real_yoy(nations):
    co2, nb = nations
    nat = nb.countries_only(co2)
    vn = nb.yoy(nat.loc[nat.country == "Vietnam", ["country", "year", "co2"]], "co2").set_index("year")
    assert vn.loc[2019, "yoy"] == pytest.approx(0.3282, abs=1e-4)
    assert vn.loc[2021, "yoy"] == pytest.approx(-0.1335, abs=1e-4)
    er = nat.loc[nat.country == "Eritrea", ["country", "year", "co2"]].dropna()
    er = nb.yoy(er, "co2").set_index("year")
    assert np.isnan(er.loc[1994, "yoy"])
    assert er.loc[1995, "yoy"] == pytest.approx(0.1174, abs=1e-3)

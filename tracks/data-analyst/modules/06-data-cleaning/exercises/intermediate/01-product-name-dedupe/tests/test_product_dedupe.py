import os
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from testkit import Exercise

ex = Exercise(__file__)


@pytest.fixture(scope="module")
def nb():
    return ex.notebook("product_dedupe.ipynb")


def test_normalize_description(nb):
    s = pd.Series(["  white hanging heart t-light holder ", "PAPER CRAFT , LITTLE BIRDIE", "SET/6 RED SPOTTY CUPS",
                   "50'S CHRISTMAS  KIT", "HOME & GARDEN", None])
    out = nb.normalize_description(s)
    assert out.iloc[:5].tolist() == ["WHITE HANGING HEART T LIGHT HOLDER", "PAPER CRAFT LITTLE BIRDIE", "SET 6 RED SPOTTY CUPS",
                                     "50 S CHRISTMAS KIT", "HOME & GARDEN"]
    assert pd.isna(out.iloc[5])
    assert list(out.index) == list(s.index)


def lines():
    return pd.DataFrame({
        "StockCode": ["23196", "23196", "23196", "23196", "22197", "22197", "22197", "85123A", "85123A", "99999"],
        "Description": ["VINTAGE LEAF MAGNETIC NOTEPAD", "vintage leaf magnetic notepad ", "RETRO LEAVES MAGNETIC NOTEPAD",
                        "RETO LEAVES MAGNETIC NOTEPAD", "POPCORN HOLDER", "SMALL POPCORN HOLDER", "SMALL POPCORN HOLDER",
                        "WHITE HANGING HEART T-LIGHT HOLDER", "CREAM HANGING HEART T-LIGHT HOLDER", None],
    })


def test_canonical_names(nb):
    out = nb.canonical_names(lines())
    assert list(out.columns) == ["name", "n_variants"]
    assert sorted(out.index) == ["22197", "23196", "85123A"]                 # mã chỉ có mô tả thiếu thì không có tên
    assert out.loc["23196"].tolist() == ["VINTAGE LEAF MAGNETIC NOTEPAD", 3]  # 2 dòng sau chuẩn hoá là cùng tên
    assert out.loc["22197"].tolist() == ["SMALL POPCORN HOLDER", 2]
    # hoà số dòng: lấy tên nhỏ nhất theo thứ tự chữ cái
    assert out.loc["85123A"].tolist() == ["CREAM HANGING HEART T LIGHT HOLDER", 2]


def test_canonical_names_does_not_mutate_input(nb):
    df = lines()
    before = df.copy()
    nb.canonical_names(df)
    pd.testing.assert_frame_equal(df, before)


def test_fuzzy_pairs(nb):
    names = pd.Series(["RETRO LEAVES MAGNETIC NOTEPAD", "RETRO LEAVS MAGNETIC NOTEPAD", "GARDENIA 1 WICK MORRIS BOXED CANDLE",
                       "GARDENIA 3 WICK MORRIS BOXED CANDLE", "RETRO LEAVS MAGNETIC NOTEPAD", "PARTY BUNTING", "PARTY BUNTINGS",
                       "SPOTTY BUNTING", None])
    out = nb.fuzzy_pairs(names, threshold=0.9)
    assert list(out.columns) == ["a", "b", "score"]
    pairs = list(zip(out["a"], out["b"]))
    assert pairs == [
        ("RETRO LEAVES MAGNETIC NOTEPAD", "RETRO LEAVS MAGNETIC NOTEPAD"),       # tên trùng lặp chỉ so một lần
        ("GARDENIA 1 WICK MORRIS BOXED CANDLE", "GARDENIA 3 WICK MORRIS BOXED CANDLE"),
        ("PARTY BUNTING", "PARTY BUNTINGS"),
    ]
    assert out["score"].tolist() == pytest.approx([56 / 57, 68 / 70, 26 / 27])


def test_fuzzy_pairs_blocking(nb):
    # block theo từ đầu tiên: chỉ so các tên cùng từ đầu, nên lỗi gõ ở từ đầu bị bỏ sót (đánh đổi lấy tốc độ)
    assert nb.fuzzy_pairs(pd.Series(["PARTY BUNTING", "SPOTTY BUNTING"]), threshold=0.5).empty
    assert nb.fuzzy_pairs(pd.Series(["RETRO LEAVES MAGNETIC NOTEPAD", "RETO LEAVES MAGNETIC NOTEPAD"]), threshold=0.9).empty
    assert list(nb.fuzzy_pairs(pd.Series(["A B", "X Y"]), threshold=0.1).columns) == ["a", "b", "score"]


def test_likely_same(nb):
    assert nb.likely_same("RETRO LEAVES MAGNETIC NOTEPAD", "RETO LEAVES MAGNETIC NOTEPAD")
    assert nb.likely_same("FOLDING UMBRELLA RED WHITE POLKADOT", "FOLDING UMBRELLA WHITE RED POLKADOT")
    assert nb.likely_same("ASSORTED COLOUR BIRD ORNAMENT", "ASSORTED COLOR BIRD ORNAMENT")
    assert not nb.likely_same("PINK CHRISTMAS TREE 30CM", "PINK CHRISTMAS TREE 60CM")       # khác số: khác cỡ
    assert not nb.likely_same("LETTER A BLING KEY RING", "LETTER B BLING KEY RING")         # từ khác quá ngắn
    assert not nb.likely_same("VINTAGE RED ENAMEL TRIM JUG", "VINTAGE RED ENAMEL TRIM MUG")
    assert not nb.likely_same("12 PENCILS SMALL TUBE", "12 PENCILS TALL TUBE")              # SMALL/TALL giống 0.67
    assert not nb.likely_same("JUMBO BAG RED RETROSPOT", "JUMBO BAG PINK POLKADOT")         # khác hai từ


def read_sheet(sheet: str) -> pd.DataFrame:
    """Sheet gốc (Invoice, StockCode, Description là chuỗi), cache parquet trong thư mục tạm: xlsx đọc mất 30-60 giây."""
    src = ex.dataset("online-retail-ii") / "online_retail_II.xlsx"
    st = src.stat()
    cache = Path(tempfile.gettempdir()) / "da-cache" / f"online_retail_II-{sheet.replace(' ', '_')}-{st.st_size}-{st.st_mtime_ns}.parquet"
    if not cache.exists():
        df = pd.read_excel(src, sheet_name=sheet, dtype={"Invoice": str, "StockCode": str, "Description": str})
        cache.parent.mkdir(parents=True, exist_ok=True)
        tmp = cache.with_name(f"{cache.name}.{os.getpid()}.tmp")
        df.to_parquet(tmp, index=False)
        os.replace(tmp, cache)
    return pd.read_parquet(cache)


@pytest.fixture(scope="module")
def real_valid(nb):
    return nb.valid_lines(read_sheet("Year 2010-2011"))       # valid_lines cho sẵn trong notebook


def test_real_canonical(nb, real_valid):
    assert len(real_valid) == 527_789
    names = nb.canonical_names(real_valid)
    assert len(names) == 3_803
    assert (names["n_variants"] > 1).sum() == 193
    assert names["n_variants"].idxmax() == "23196"
    assert names.loc["23196", "name"] == "VINTAGE LEAF MAGNETIC NOTEPAD"


def test_real_fuzzy(nb, real_valid):
    pairs = nb.fuzzy_pairs(nb.canonical_names(real_valid)["name"], threshold=0.9)
    assert len(pairs) == 589
    assert pairs["score"].min() >= 0.9
    same = [nb.likely_same(a, b) for a, b in zip(pairs["a"], pairs["b"])]
    assert sum(same) == 0

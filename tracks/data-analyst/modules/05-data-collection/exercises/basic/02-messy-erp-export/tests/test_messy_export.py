"""Fixture `ventes_france_2011-11.csv`: 1 580 dòng thật của Online Retail II (UCI, CC BY 4.0), khách Pháp tháng
11/2011, xuất lại theo định dạng một hệ thống ERP kiểu Pháp (cp1252, `;`, dấu thập phân `,`, ngày dd/mm/yyyy,
2 dòng mở đầu, 1 dòng tổng ở cuối). Nội dung từng dòng giữ nguyên bộ gốc."""
import codecs

import pandas as pd
import pytest

from testkit import Exercise

ex = Exercise(__file__)
EXPORT = ex.fixtures / "ventes_france_2011-11.csv"
COLUMNS = ["Invoice", "StockCode", "Description", "Quantity", "InvoiceDate", "Price", "Customer ID", "Country"]


@pytest.fixture(scope="module")
def nb():
    return ex.notebook("messy_export.ipynb")


def test_detect_encoding(nb):
    assert nb.detect_encoding(codecs.BOM_UTF8 + "Quantité;Prix".encode("utf-8")) == "utf-8-sig"
    assert nb.detect_encoding("Quantité;Prix".encode("utf-8")) == "utf-8"
    assert nb.detect_encoding("Quantité;Prix".encode("cp1252")) == "cp1252"
    assert nb.detect_encoding(b"Invoice,Price") == "utf-8"


def test_sniff_delimiter(nb):
    assert nb.sniff_delimiter("Facture;Code article;Désignation;Quantité") == ";"
    assert nb.sniff_delimiter("Invoice,StockCode,Description") == ","
    assert nb.sniff_delimiter("Invoice\tStockCode\tPrice") == "\t"
    assert nb.sniff_delimiter("Invoice|StockCode|Price") == "|"
    with pytest.raises(ValueError):
        nb.sniff_delimiter("chỉ một cột")


TINY_FR = (
    "Export ERP;Pays : France\r\n"
    "Facture;Code article;Désignation;Quantité;Date facture;Prix unitaire;N° client;Pays\r\n"
    "573867;02113;BOÎTE À THÉ;12;03/11/2011 09:05;2,55;12674;France\r\n"
    "C573868;POST;POSTAGE;-1;13/11/2011 10:00;18,00;12674;France\r\n"
    "573869;85123A;\"LANTERN; WHITE\";4;30/11/2011 16:47;1250,50;;France\r\n"
    "Total lignes;3\r\n"
)


def test_read_export_french_cp1252(nb, tmp_path):
    path = tmp_path / "tiny.csv"
    path.write_bytes(TINY_FR.encode("cp1252"))
    df = nb.read_export(path)
    assert list(df.columns) == COLUMNS
    assert len(df) == 3
    # mã giữ nguyên dạng chuỗi: số 0 đầu không mất, mã huỷ "C..." không làm hỏng cột
    assert df["Invoice"].tolist() == ["573867", "C573868", "573869"]
    assert df["StockCode"].tolist() == ["02113", "POST", "85123A"]
    assert df["Description"].tolist() == ["BOÎTE À THÉ", "POSTAGE", "LANTERN; WHITE"]
    # dd/mm: 03/11 là 3 tháng 11, không phải 11 tháng 3
    assert df["InvoiceDate"].tolist() == list(pd.to_datetime(["2011-11-03 09:05", "2011-11-13 10:00",
                                                              "2011-11-30 16:47"]))
    assert df["Price"].tolist() == pytest.approx([2.55, 18.0, 1250.5])
    assert pd.api.types.is_integer_dtype(df["Quantity"])
    assert str(df["Customer ID"].dtype) == "Int64"
    assert df["Customer ID"].iloc[0] == 12674 and pd.isna(df["Customer ID"].iloc[2])


def test_read_export_utf8_bom_comma(nb, tmp_path):
    text = ("Facture,Code article,Désignation,Quantité,Date facture,Prix unitaire,N° client,Pays\n"
            "581001,22423,REGENCY CAKESTAND 3 TIER,2,09/12/2011 08:00,12.75,17850,United Kingdom\n")
    path = tmp_path / "uk.csv"
    path.write_bytes(codecs.BOM_UTF8 + text.encode("utf-8"))
    df = nb.read_export(path)
    assert list(df.columns) == COLUMNS
    assert df["Price"].tolist() == [12.75]
    assert df["InvoiceDate"].iloc[0] == pd.Timestamp("2011-12-09 08:00")
    assert df["StockCode"].iloc[0] == "22423"


def test_control_total(nb, tmp_path):
    path = tmp_path / "tiny.csv"
    path.write_bytes(TINY_FR.encode("cp1252"))
    assert nb.control_total(path) == 3


def test_summarize_tiny(nb):
    df = pd.DataFrame({
        "Invoice": ["1", "1", "C2", "3", "3"],
        "Quantity": [2, 3, -1, 4, 1],
        "Price": [10.0, 5.0, 8.0, 2.5, 0.0],
        "Customer ID": pd.array([7, 7, 7, pd.NA, pd.NA], dtype="Int64"),
    })
    before = df.copy()
    out = nb.summarize(df)
    pd.testing.assert_frame_equal(df, before)
    assert out == {"rows": 5, "invoices": 3, "cancelled_invoices": 1, "customers": 1, "valid_lines": 3,
                   "revenue": pytest.approx(45.0)}


def test_real_export_matches_control_and_source(nb):
    df = nb.read_export(EXPORT)
    assert list(df.columns) == COLUMNS
    assert len(df) == nb.control_total(EXPORT) == 1580
    assert df["InvoiceDate"].min() == pd.Timestamp("2011-11-01 12:12")
    assert df["InvoiceDate"].max() == pd.Timestamp("2011-11-30 16:47")
    assert (df["InvoiceDate"].dt.month == 11).all()
    assert int(df["Customer ID"].isna().sum()) == 49
    assert nb.summarize(df) == {"rows": 1580, "invoices": 76, "cancelled_invoices": 12, "customers": 40,
                                "valid_lines": 1544, "revenue": pytest.approx(31758.71, abs=0.01)}

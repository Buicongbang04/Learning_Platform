"""Chấm grocery_star.sql trên schema Grocery Sales: bảng nhỏ sinh trong test (cùng tên cột) và bộ thật (chỉ đối soát cấu trúc)."""
import duckdb
import pandas as pd
import pytest

from testkit import Exercise

ex = Exercise(__file__)
TABLES = {
    "dim_date": ["date_key", "full_date", "year", "month", "day_of_week"],
    "dim_product": ["product_key", "product_id", "product_name", "category_name", "class", "list_price",
                    "is_allergic", "vitality_days"],
    "dim_customer": ["customer_key", "customer_id", "customer_name", "city_name", "country_name"],
    "dim_employee": ["employee_key", "employee_id", "employee_name", "city_name", "hire_date"],
    "fct_sales": ["sales_id", "transaction_number", "date_key", "customer_key", "product_key", "salesperson_key",
                  "quantity", "unit_price", "discount", "net_amount"],
}
HEADINGS = ["## Grain", "## Bảng và khoá", "## Quyết định với dữ liệu nguồn", "## Data test", "## Không rút insight"]
RAW = ["sales", "products", "categories", "customers", "cities", "countries", "employees"]


def small_raw() -> dict[str, pd.DataFrame]:
    ts = pd.Timestamp
    return {
        "countries": pd.DataFrame({"CountryID": [1, 2], "CountryName": ["Atlantis", "Lemuria"], "CountryCode": ["AT", "LM"]}),
        "cities": pd.DataFrame({"CityID": [10, 11, 12], "CityName": ["Alpha", "Beta", "Gamma"],
                                "Zipcode": ["001", "002", "003"], "CountryID": [1, 1, 2]}),
        "categories": pd.DataFrame({"CategoryID": [1, 2], "CategoryName": ["Dairy", "Snacks"]}),
        "products": pd.DataFrame({
            "ProductID": [100, 101, 102], "ProductName": ["Milk", "Chips", "Cheese"], "Price": [2.0, 1.5, 10.0],
            "CategoryID": [1, 2, 1], "Class": ["Low", "Medium", "High"],
            "ModifyDate": [ts("2018-01-01"), ts("2018-02-01"), ts("2018-03-01")],
            "Resistant": ["Durable", "Weak", "Unknown"], "IsAllergic": ["False", "Unknown", "True"],
            "VitalityDays": [7.0, 0.0, 30.0]}),
        "customers": pd.DataFrame({"CustomerID": [1, 2], "FirstName": ["An", "Binh"], "MiddleInitial": ["T", None],
                                   "LastName": ["Le", "Tran"], "CityID": [10, 12], "Address": ["x", "y"]}),
        "employees": pd.DataFrame({"EmployeeID": [7, 8], "FirstName": ["Chi", "Dung"], "MiddleInitial": ["K", "M"],
                                   "LastName": ["Pham", "Vo"], "BirthDate": [ts("1980-01-01"), ts("1990-01-01")],
                                   "Gender": ["F", "M"], "CityID": [11, 10],
                                   "HireDate": [ts("2015-05-01"), ts("2016-06-01")]}),
        "sales": pd.DataFrame({
            "SalesID": [1, 2, 3, 4, 5],
            "SalesPersonID": [7, 8, 7, 9, 8],               # 9 không có trong employees
            "CustomerID": [1, 2, 1, 2, 3],                  # 3 không có trong customers
            "ProductID": [100, 101, 102, 100, 999],         # 999 không có trong products
            "Quantity": [3, 10, 1, 4, 2],
            "Discount": [0.0, 0.1, 0.2, 0.0, 0.0],
            "TotalPrice": [0.0, 0.0, 0.0, 0.0, 0.0],        # cột tổng của nguồn luôn bằng 0
            "SalesDate": [ts("2018-01-01 09:00"), ts("2018-01-03 10:00"), pd.NaT, ts("2018-01-03 18:00"),
                          ts("2018-01-02 12:00")],
            "TransactionNumber": ["T1", "T2", "T3", "T4", "T5"]}),
    }


def build(raw: dict[str, pd.DataFrame | str]) -> duckdb.DuckDBPyConnection:
    con = duckdb.connect()
    for name, src in raw.items():
        if isinstance(src, str):
            con.execute(f"CREATE VIEW raw_{name} AS SELECT * FROM read_csv('{src}')")
        else:
            con.register(f"df_{name}", src)
            con.execute(f"CREATE TABLE raw_{name} AS SELECT * FROM df_{name}")
    con.execute(ex.read("grocery_star.sql"))
    return con


def rows(con, sql):
    return con.execute(sql).fetchall()


@pytest.fixture(scope="module")
def small():
    return build(small_raw())


def test_tables_and_columns(small):
    for table, cols in TABLES.items():
        got = [r[0] for r in rows(small, f"DESCRIBE {table}")]
        assert got[:len(cols)] == cols, f"{table}: cần các cột đầu tiên {cols}, đang có {got}"
    assert rows(small, "SELECT count(*) FROM fct_sales") == [(5,)], "Grain: một dòng mỗi SalesID, không bỏ dòng nào"


def test_unknown_members(small):
    for dim, key in [("dim_date", "date_key"), ("dim_product", "product_key"), ("dim_customer", "customer_key"),
                     ("dim_employee", "employee_key")]:
        assert rows(small, f"SELECT count(*) FROM {dim} WHERE {key} = -1") == [(1,)], f"{dim} cần dòng unknown member -1"
    got = rows(small, "SELECT sales_id, date_key, customer_key, product_key, salesperson_key FROM fct_sales ORDER BY sales_id")
    assert [r[1] for r in got] == [20180101, 20180103, -1, 20180103, 20180102]
    assert got[4][2] == -1 and got[4][3] == -1 and got[3][4] == -1
    assert got[0][2] != -1 and got[0][3] != -1 and got[0][4] != -1


def test_flattened_dimensions(small):
    assert rows(small, """SELECT customer_name, city_name, country_name FROM dim_customer WHERE customer_id = 2""") == \
        [("Binh Tran", "Gamma", "Lemuria")]
    assert rows(small, "SELECT customer_name FROM dim_customer WHERE customer_id = 1") == [("An T Le",)]
    assert rows(small, "SELECT product_name, category_name, list_price FROM dim_product WHERE product_id = 102") == \
        [("Cheese", "Dairy", 10.0)]
    assert rows(small, "SELECT employee_name, city_name FROM dim_employee WHERE employee_id = 7") == [("Chi K Pham", "Beta")]
    dates = rows(small, "SELECT date_key FROM dim_date WHERE date_key <> -1 ORDER BY 1")
    assert [r[0] for r in dates] == [20180101, 20180102, 20180103]


def test_net_amount(small):
    got = rows(small, "SELECT sales_id, unit_price, net_amount FROM fct_sales ORDER BY sales_id")
    assert [r[1] for r in got[:4]] == pytest.approx([2.0, 1.5, 10.0, 2.0])
    assert [r[2] for r in got[:4]] == pytest.approx([6.0, 13.5, 8.0, 8.0])
    assert got[4][1] is None and got[4][2] is None, "Sản phẩm không có trong products: giá và net_amount để NULL, không bịa"


def check_integrity(con):
    assert rows(con, "SELECT count(*) FROM fct_sales")[0][0] > 0, "fct_sales đang rỗng"
    for dim, key, fk in [("dim_date", "date_key", "date_key"), ("dim_product", "product_key", "product_key"),
                         ("dim_customer", "customer_key", "customer_key"), ("dim_employee", "employee_key", "salesperson_key")]:
        assert rows(con, f"SELECT count(*) - count(DISTINCT {key}) FROM {dim}") == [(0,)], f"{dim}.{key} phải unique"
        orphan = rows(con, f"SELECT count(*) FROM fct_sales f LEFT JOIN {dim} d ON f.{fk} = d.{key} WHERE d.{key} IS NULL")
        assert orphan == [(0,)], f"fct_sales.{fk} có khoá không có trong {dim}"
    assert rows(con, "SELECT count(*) - count(DISTINCT sales_id) FROM fct_sales") == [(0,)]


def test_integrity_small(small):
    check_integrity(small)


def test_rerunnable(small):
    small.execute(ex.read("grocery_star.sql"))
    assert rows(small, "SELECT count(*) FROM fct_sales") == [(5,)]


def test_real_schema_reconciles():
    """Bộ thật (sinh giả, 6.76 triệu dòng sales): chỉ đối soát cấu trúc, không tính chỉ số kinh doanh nào."""
    folder = ex.dataset("grocery-sales-synthetic")
    con = build({name: (folder / f"{name}.csv").as_posix() for name in RAW})
    check_integrity(con)
    n, unknown_date, unknown_other = rows(con, """
        SELECT count(*), count(*) FILTER (WHERE date_key = -1),
               count(*) FILTER (WHERE customer_key = -1 OR product_key = -1 OR salesperson_key = -1)
        FROM fct_sales""")[0]
    assert n == 6_758_125 and unknown_date == 67_526 and unknown_other == 0


def test_design_doc():
    doc = ex.read("DESIGN.md")
    assert "TODO" not in doc, "Còn TODO trong DESIGN.md"
    words = len(doc.split())
    assert 250 <= words <= 1200, f"DESIGN.md 250-1200 từ, hiện có {words}"
    for heading in HEADINGS:
        assert heading in doc, f"Thiếu mục {heading}"

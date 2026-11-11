import pytest

from testkit import Exercise

ex = Exercise(__file__)
DATA = ex.dir / "data" / "olist-api-2026-10.csv"
SLO = 0.997
TIERS = [(99.9, 0), (99.0, 10), (95.0, 25), (0, 100)]


@pytest.fixture(scope="module")
def budget():
    return ex.module("budget.py")


def month(budget) -> list[dict]:
    return budget.load(DATA)


def hour(day: int, h: int) -> str:
    return f"2026-10-{day:02d}T{h:02d}:00:00Z"


def row(h: str, requests: int, errors: int = 0, slow: int = 0, maintenance: bool = False) -> dict:
    return {"hour": h, "requests": requests, "errors": errors, "slow": slow, "maintenance": maintenance}


def test_load_types_and_length(budget):
    rows = month(budget)
    assert len(rows) == 744
    first = rows[0]
    assert first["hour"] == hour(1, 0) and rows[-1]["hour"] == hour(31, 23)
    assert all(isinstance(r[k], int) and not isinstance(r[k], bool) for r in rows for k in ("requests", "errors", "slow"))
    assert all(isinstance(r["maintenance"], bool) for r in rows)
    assert [r["hour"] for r in rows if r["maintenance"]] == [hour(19, 19)]


def test_load_rejects_bad_files(budget, tmp_path):
    bad_columns = tmp_path / "a.csv"
    bad_columns.write_text("hour,requests,errors\n2026-10-01T00:00:00Z,10,1\n", encoding="utf-8")
    with pytest.raises(ValueError):
        budget.load(bad_columns)
    too_many = tmp_path / "b.csv"
    too_many.write_text("hour,requests,errors,slow,maintenance\n2026-10-01T00:00:00Z,10,6,5,0\n", encoding="utf-8")
    with pytest.raises(ValueError):
        budget.load(too_many)


def test_sli_month(budget):
    rows = month(budget)
    assert budget.sli(rows) == pytest.approx(0.9962365, abs=1e-6)
    assert budget.sli([row(hour(1, 0), 1000, 3, 7)]) == pytest.approx(0.99)
    with pytest.raises(ValueError):
        budget.sli([row(hour(1, 0), 0)])


def test_budget_report_month(budget):
    rows = month(budget)
    report = budget.budget_report(rows, SLO)
    assert report["total"] == 4053685 and report["bad"] == 15256
    assert report["allowed_bad"] == pytest.approx(12161.055, abs=0.01)
    assert report["consumed"] == pytest.approx(1.2545, abs=1e-4)
    assert report["remaining"] == pytest.approx(-0.2545, abs=1e-4)
    assert report["exhausted_at"] == hour(24, 2)


def test_budget_report_small_cases(budget):
    rows = [row(hour(1, 0), 1000, 1), row(hour(1, 1), 1000, 2), row(hour(1, 2), 1000, 3)]
    report = budget.budget_report(rows, 0.998)
    assert report["allowed_bad"] == pytest.approx(6) and report["remaining"] == pytest.approx(0)
    assert report["exhausted_at"] is None, "Tiêu vừa đủ budget chưa phải là vượt"
    report = budget.budget_report(rows + [row(hour(1, 3), 1000, 3)], 0.998)
    assert report["exhausted_at"] == hour(1, 3)
    for slo in (0.0, 1.0, 99.7):
        with pytest.raises(ValueError):
            budget.budget_report(rows, slo)


def test_burn_rates(budget):
    rows = month(budget)
    rates = budget.burn_rates(rows, SLO, hour(28, 12))
    assert set(rates) == {1, 6, 24, 72}
    assert rates[1] == pytest.approx(7.7336, abs=1e-3)
    assert rates[6] == pytest.approx(4.7109, abs=1e-3)
    assert rates[24] == pytest.approx(2.2870, abs=1e-3)
    assert rates[72] == pytest.approx(1.2741, abs=1e-3)
    latency = budget.burn_rates(rows, SLO, hour(23, 4), windows=(1, 6))
    assert latency[1] == pytest.approx(41.399, abs=1e-2) and latency[6] == pytest.approx(26.254, abs=1e-2)


def test_burn_rates_rejects_bad_window(budget):
    rows = month(budget)
    with pytest.raises(ValueError):
        budget.burn_rates(rows, SLO, hour(1, 2), windows=(6,))
    with pytest.raises(ValueError):
        budget.burn_rates(rows, SLO, "2026-11-01T00:00:00Z")


def test_sla_availability_excludes_maintenance(budget):
    rows = month(budget)
    assert budget.sla_availability(rows) == pytest.approx(1 - 3 / 743)
    first_week = [r for r in rows if r["hour"] < hour(8, 0)]
    assert budget.sla_availability(first_week) == pytest.approx(1 - 2 / 168)
    small = [row(hour(1, 0), 100, 5), row(hour(1, 1), 100, 6), row(hour(1, 2), 100, 100, maintenance=True)]
    assert budget.sla_availability(small) == pytest.approx(0.5), "Đúng 5% chưa tính là sập; giờ bảo trì không tính"


@pytest.mark.parametrize("availability,credit", [(0.9995, 0), (0.999, 0), (0.99896, 10), (0.99, 10), (0.9895, 25),
                                                 (0.95, 25), (0.9, 100)])
def test_sla_credit(budget, availability, credit):
    assert budget.sla_credit(availability, TIERS) == credit


def test_sla_credit_month(budget):
    rows = month(budget)
    assert budget.sla_credit(budget.sla_availability(rows), TIERS) == 10


@pytest.mark.parametrize("remaining,state", [(0.9, "normal"), (0.51, "normal"), (0.5, "caution"), (0.01, "caution"),
                                             (0.0, "freeze"), (-0.25, "freeze")])
def test_policy(budget, remaining, state):
    assert budget.policy({"remaining": remaining}) == state


def test_policy_month(budget):
    rows = month(budget)
    assert budget.policy(budget.budget_report(rows, SLO)) == "freeze"

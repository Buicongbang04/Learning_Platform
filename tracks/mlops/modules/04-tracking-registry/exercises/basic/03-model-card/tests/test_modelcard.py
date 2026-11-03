import pytest

from testkit import Exercise

ex = Exercise(__file__)

SHA = "a" * 39 + "b"
INFO = {
    "name": "taxi-eta",
    "version": 7,
    "owner": "ml-platform@example.com",
    "intended_use": "Ước lượng thời gian chuyến yellow taxi NYC lúc khách đặt xe.",
    "out_of_scope": ["Chuyến ngoài 5 quận", "Dự đoán giá cước"],
    "training_data": {"data_version": "c0ffee01", "rows": 200000, "period": "2019-01"},
    "metrics": {"mae": 200.0, "latency_p95_ms": 41.5},
    "slices": {
        "short": {"mae": 90.0, "n": 20000},
        "airport": {"mae": 330.0, "n": 5000},
        "night": {"mae": 250.0, "n": 3000},
        "rare": {"mae": 900.0, "n": 20},
    },
    "limitations": ["Train trên dữ liệu trước COVID", "Không có dữ liệu giao thông thời gian thực"],
    "lineage": {"run_id": "r1", "git_commit": SHA},
}


@pytest.fixture(scope="module")
def mod():
    return ex.module("modelcard.py")


def test_worst_slices_order_and_filter(mod):
    result = mod.worst_slices(INFO["slices"], 200.0, k=2)
    assert [name for name, _ in result] == ["airport", "night"]
    assert result[0][1] == pytest.approx(1.65)


def test_worst_slices_min_n_is_configurable(mod):
    result = mod.worst_slices(INFO["slices"], 200.0, k=1, min_n=10)
    assert result[0][0] == "rare"


def test_card_structure(mod):
    card = mod.build_model_card(INFO)
    assert card.splitlines()[0] == "# Model card: taxi-eta v7"
    positions = [card.index(h) for h in mod.REQUIRED_HEADINGS]
    assert positions == sorted(positions)
    assert "c0ffee01" in card and SHA in card


def test_card_slice_table_worst_first_with_ratio(mod):
    card = mod.build_model_card(INFO)
    rows = [l for l in card.splitlines() if l.startswith("| ") and "---" not in l and "Slice" not in l]
    names = [r.split("|")[1].strip() for r in rows]
    assert names == ["rare", "airport", "night", "short"]
    assert "1.65x" in rows[1]


def test_card_without_limitations_refused(mod):
    with pytest.raises(ValueError):
        mod.build_model_card({**INFO, "limitations": []})


def test_generated_card_passes_its_own_linter(mod):
    assert mod.card_problems(mod.build_model_card(INFO)) == []


def test_linter_catches_each_problem(mod):
    good = mod.build_model_card(INFO)
    assert any("Lineage" in p for p in mod.card_problems(good.replace("## Lineage", "## Nguồn gốc")))
    assert any("TODO" in p for p in mod.card_problems(good + "\nTODO: điền\n"))
    no_bullets = good.replace("- Train trên dữ liệu trước COVID", "Train trên dữ liệu trước COVID").replace(
        "- Không có dữ liệu giao thông thời gian thực", "Không có dữ liệu giao thông")
    assert any("gạch đầu dòng" in p for p in mod.card_problems(no_bullets))
    no_table = "\n".join(l for l in good.splitlines() if not l.startswith("|"))
    assert any("bảng" in p for p in mod.card_problems(no_table))
    assert any("git_commit" in p for p in mod.card_problems(good.replace(SHA, "abc123")))


def test_linter_reports_all_problems_at_once(mod):
    assert len(mod.card_problems("# Model card: x v1\n")) >= 5


def test_card_has_exactly_one_table(mod):
    card = mod.build_model_card(INFO)
    performance = card.split("## Hiệu năng")[1].split("## Hạn chế")[0]
    blocks = [b for b in performance.split("\n\n") if b.lstrip().startswith("|")]
    assert len(blocks) == 1
    assert card.count("\n|") == performance.count("\n|")

import re

import pytest

from testkit import Exercise

ex = Exercise(__file__)

PORTABLE = ["parquet", "iceberg", "delta", "terraform", "opentofu", "airflow", "dbt", "spark",
            "kubernetes", "kafka", "trino", "duckdb", "beam", "postgres"]


def dec():
    return ex.module("decision.py")


def doc():
    return ex.read("comparison.md")


def section(text, number):
    match = re.search(rf"^## {number}\..*?(?=^## |\Z)", text, flags=re.M | re.S)
    return match.group(0) if match else ""


# ---------- decision.py ----------

def test_scores_and_weights_filled():
    mod = dec()
    assert set(mod.SCORES) == {"aws", "azure", "gcp"}
    criteria = set(mod.SCORES["aws"])
    assert len(criteria) >= 5, "Cần ít nhất 5 tiêu chí"
    assert {"cost", "team_skills"} <= criteria
    for cloud, row in mod.SCORES.items():
        assert set(row) == criteria, f"{cloud} phải có cùng bộ tiêu chí"
        assert all(isinstance(v, int) and 1 <= v <= 5 for v in row.values()), f"Điểm {cloud} phải là số nguyên 1-5"
    assert set(mod.WEIGHTS) == criteria
    assert all(w >= 0 for w in mod.WEIGHTS.values()) and sum(mod.WEIGHTS.values()) > 0


SAMPLE = {
    "aws": {"cost": 3, "team_skills": 2, "ecosystem": 5},
    "azure": {"cost": 4, "team_skills": 5, "ecosystem": 3},
    "gcp": {"cost": 5, "team_skills": 3, "ecosystem": 4},
}


def test_weighted_scores_normalizes():
    result = dec().weighted_scores(SAMPLE, {"cost": 2, "team_skills": 1, "ecosystem": 1})
    assert result == {"aws": 3.25, "azure": 4.0, "gcp": 4.25}
    same = dec().weighted_scores(SAMPLE, {"cost": 0.5, "team_skills": 0.25, "ecosystem": 0.25})
    assert same == result


def test_weighted_scores_rounding_and_zero_weight():
    result = dec().weighted_scores(SAMPLE, {"cost": 1, "team_skills": 1, "ecosystem": 1, })
    assert result["aws"] == round(10 / 3, 3)
    only_skills = dec().weighted_scores(SAMPLE, {"cost": 0, "team_skills": 1, "ecosystem": 0})
    assert only_skills == {"aws": 2.0, "azure": 5.0, "gcp": 3.0}


@pytest.mark.parametrize(
    "scores, weights",
    [
        (SAMPLE, {"cost": -1, "team_skills": 1, "ecosystem": 1}),
        (SAMPLE, {"cost": 0, "team_skills": 0, "ecosystem": 0}),
        (SAMPLE, {"cost": 1, "latency": 1}),
        ({**SAMPLE, "gcp": {"cost": 6, "team_skills": 3, "ecosystem": 4}}, {"cost": 1}),
        ({**SAMPLE, "gcp": {"cost": 0, "team_skills": 3, "ecosystem": 4}}, {"cost": 1}),
    ],
)
def test_weighted_scores_errors(scores, weights):
    with pytest.raises(ValueError):
        dec().weighted_scores(scores, weights)


def test_rank_order_and_ties():
    ranked = dec().rank(SAMPLE, {"cost": 2, "team_skills": 1, "ecosystem": 1})
    assert ranked == [("gcp", 4.25), ("azure", 4.0), ("aws", 3.25)]
    tie = {"gcp": {"cost": 3}, "aws": {"cost": 3}, "azure": {"cost": 4}}
    assert dec().rank(tie, {"cost": 1}) == [("azure", 4.0), ("aws", 3.0), ("gcp", 3.0)]


# ---------- comparison.md ----------

def test_document_complete():
    text = doc()
    assert "TODO" not in text, "Còn TODO trong comparison.md"
    for number in range(1, 6):
        assert section(text, number), f"Thiếu mục ## {number}."


def test_mapping_table():
    mapping = section(doc(), 1)
    rows = [line for line in mapping.splitlines() if line.strip().startswith("|")]
    assert rows, "Mục 1 cần bảng Markdown"
    header = rows[0].lower()
    for cloud in ("aws", "azure", "gcp"):
        assert cloud in header, f"Header bảng cần cột {cloud.upper()}"
    data = [r for r in rows[1:] if not re.fullmatch(r"\|[\s:|-]+\|?", r.strip())]
    assert len(data) >= 8, f"Bảng ánh xạ cần ≥ 8 dòng, đang có {len(data)}"
    for row in data:
        cells = [c.strip() for c in row.strip().strip("|").split("|")]
        assert len(cells) >= 4 and all(cells[:4]), f"Dòng thiếu ô: {row}"


def test_lock_in_section():
    lock = section(doc(), 4).lower()
    found = [p for p in PORTABLE if p in lock]
    assert len(found) >= 3, f"Mục lock-in cần ≥ 3 công nghệ di động, thấy {found}"


def test_recommendation_mentions_top_cloud():
    mod = dec()
    top = mod.rank(mod.SCORES, mod.WEIGHTS)[0][0]
    names = {"aws": ["aws", "amazon"], "azure": ["azure", "microsoft"], "gcp": ["gcp", "google"]}
    rec = section(doc(), 5).lower()
    assert any(n in rec for n in names[top]), f"Mục khuyến nghị nên nêu {top} (đứng đầu rank())"

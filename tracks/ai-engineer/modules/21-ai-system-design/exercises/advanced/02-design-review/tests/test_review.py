import re

import pytest
import yaml

from testkit import Exercise

ex = Exercise(__file__)
KINDS = {"cost_per_1k", "monthly_cost", "kv_bytes_per_token", "weights_bytes", "concurrency", "gpus"}


@pytest.fixture(scope="module")
def rv():
    return ex.module("review.py")


def example_claims():
    return yaml.safe_load((ex.fixtures / "claims_example.yaml").read_text(encoding="utf-8"))["claims"]


def test_recompute_each_kind(rv):
    by_id = {c["id"]: c for c in example_claims()}
    assert rv.recompute(by_id["A"]) == pytest.approx(4.0)
    assert rv.recompute(by_id["B"]) == pytest.approx(2.65)  # token cache là một phần của input
    assert rv.recompute(by_id["C"]) == pytest.approx(3000.0)
    assert rv.recompute(by_id["D"]) == pytest.approx(36_864)
    assert rv.recompute(by_id["E"]) == pytest.approx(6.2e9)
    assert rv.recompute(by_id["F"]) == pytest.approx(120.0)
    assert rv.recompute(by_id["G"]) == pytest.approx(10.0)


def test_recompute_rejects_unknown(rv):
    with pytest.raises(ValueError):
        rv.recompute({"id": "X", "kind": "vibes", "inputs": {}, "claimed": 1})
    with pytest.raises(ValueError):
        rv.recompute({"id": "Y", "kind": "concurrency", "inputs": {"rps": 3}, "claimed": 1})


def test_check_claims(rv):
    res = rv.check_claims(example_claims())
    assert [r["id"] for r in res] == list("ABCDEFGH")
    assert {r["id"] for r in res if not r["ok"]} == {"B", "D", "F", "H"}
    by_id = {r["id"]: r for r in res}
    assert by_id["D"]["rel_error"] == pytest.approx(7.0)  # (294 912 - 36 864) / 36 864
    assert by_id["C"]["rel_error"] == pytest.approx(1 / 30)
    assert by_id["H"]["rel_error"] == pytest.approx(0.2)
    assert by_id["B"]["recomputed"] == pytest.approx(2.65) and by_id["B"]["claimed"] == 4.0
    # dung sai chặt hơn: C (lệch 3.3%) cũng bị đánh dấu
    strict = rv.check_claims(example_claims(), rel_tol=0.01)
    assert {r["id"] for r in strict if not r["ok"]} == {"B", "C", "D", "F", "H"}


def test_review_written(rv):
    claims = yaml.safe_load(ex.read("claims.yaml"))["claims"]
    text = ex.read("claims.yaml")
    assert "TODO" not in text, "còn TODO trong claims.yaml"
    assert len(claims) >= 6, "trích ít nhất 6 claim định lượng"
    assert len({c["kind"] for c in claims} & KINDS) >= 5, "các claim phải phủ ít nhất 5 kind"
    review = ex.read("REVIEW.md")
    assert "TODO" not in review, "còn TODO trong REVIEW.md"
    assert len(re.findall(r"^## Vấn đề \d+", review, re.M)) >= 6, "ít nhất 6 mục `## Vấn đề N: ...`"
    assert len(review.split()) >= 700, f"REVIEW.md mới có {len(review.split())} từ (cần >= 700)"
    flagged = [r["id"] for r in rv.check_claims(claims) if not r["ok"]]
    assert flagged, "check_claims không tìm ra claim sai nào trong doc"
    for cid in flagged:
        assert re.search(rf"\b{re.escape(str(cid))}\b", review), f"REVIEW.md chưa nhắc claim sai {cid}"

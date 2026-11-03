"""M10: drift, chất lượng theo nhãn về muộn, phát lại 2019-07..2020-06 trên dữ liệu thật, quyết định, runbook, postmortem.

Đề ở capstone/milestones/m10-drift-replay.md.
"""

import json
import math
import re

import numpy as np
import pandas as pd
import pytest
import yaml
from etakit import PROJECT, local_registry, need, require_file, write_config

import mlopskit

START, END, REFERENCE = "2019-07", "2020-06", "2019-06"
REPLAY = {"sample_rows": 50_000, "seed": 0, "model_params": {"max_iter": 100}}
SUMMARY_COLUMNS = ["month", "model_version", "n_scored", "psi_trip_distance", "psi_pickup_hour", "psi_eta_s",
                   "ks_trip_distance", "n_labeled", "mae", "p90_abs_err", "mae_airport", "bias_s", "as_of"]
DECISIONS = {"retrain", "rollback", "keep"}
EVIDENCE = ["psi_trip_distance", "mae_before", "mae_after", "as_of"]
RUNBOOK_HEADINGS = ["Triệu chứng", "Kiểm tra", "Hành động", "Leo thang"]
POSTMORTEM_HEADINGS = ["Tóm tắt", "Dòng thời gian", "Nguyên nhân", "Tác động", "Việc cần làm"]


def hand_psi(r, c):
    r, c = np.maximum(np.asarray(r, float), 1e-4), np.maximum(np.asarray(c, float), 1e-4)
    return float(np.sum((c - r) * np.log(c / r)))


def test_m10_psi_matches_reference(project):
    drift = need("drift", "psi", "drift_table")
    ref = pd.Series([1, 2, 3, 4, 5, 6, 7, 8, 9, 10, np.nan], dtype="float64")
    assert drift.psi(ref, pd.Series(range(1, 9), dtype="float64"), bins=2) == pytest.approx(hand_psi([0.5, 0.5], [5 / 8, 3 / 8]), abs=1e-6)
    assert drift.psi(ref, pd.Series([1.0, 2.0, 3.0]), bins=2) == pytest.approx(hand_psi([0.5, 0.5], [1.0, 0.0]), abs=1e-6), \
        "bin rỗng: tỉ lệ được nâng lên 1e-4"
    ties = pd.Series([0, 0, 0, 0, 0, 0, 1, 2, 3, 4], dtype="float64")
    assert drift.psi(ties, pd.Series(range(10), dtype="float64"), bins=4) == pytest.approx(hand_psi([0.7, 0.3], [0.2, 0.8]), abs=1e-6), \
        "biên quantile trùng nhau phải gộp (np.unique)"
    x = pd.Series(np.random.default_rng(0).gamma(2.0, 1.5, 5_000))
    assert drift.psi(x, x) == pytest.approx(0.0, abs=1e-12)
    assert drift.psi(x, x * 1.5) > 0.1
    from scipy.stats import ks_2samp

    ref_df = pd.DataFrame({"a": x, "b": x * 2})
    cur_df = pd.DataFrame({"a": x * 1.5, "b": x * 2})
    table = drift.drift_table(ref_df, cur_df, ["a", "b"])
    assert list(table.columns) == ["feature", "psi", "ks_stat"] and table["feature"].tolist() == ["a", "b"]
    assert table["psi"].tolist() == pytest.approx([drift.psi(x, x * 1.5), 0.0], abs=1e-9)
    assert table["ks_stat"].tolist() == pytest.approx([ks_2samp(x, x * 1.5).statistic, 0.0], abs=1e-9)


def test_m10_join_labels_and_quality(project):
    quality = need("quality", "join_labels", "monthly_quality")
    predictions = pd.DataFrame({
        "request_id": ["a", "b", "c", "d", "e"],
        "model_version": "1",
        "PULocationID": [132, 161, 161, 138, 161],
        "DOLocationID": [236, 236, 230, 161, 162],
        "eta_s": [1000.0, 500.0, 300.0, 900.0, 400.0],
    })
    labels = pd.DataFrame({"request_id": ["a", "b", "c", "d", "z"], "duration_s": [1200.0, 450.0, 330.0, 600.0, 999.0]})
    joined = quality.join_labels(predictions, labels)
    assert sorted(joined["request_id"]) == ["a", "b", "c", "d"], "request thiếu nhãn (e) và nhãn không có request (z) bị loại"
    assert {"eta_s", "duration_s", "PULocationID", "DOLocationID"} <= set(joined.columns)
    result = quality.monthly_quality(joined)
    err = np.array([200.0, 50.0, 30.0, 300.0])
    assert {"mae", "p90_abs_err", "mae_airport", "n"} <= set(result)
    assert result["n"] == 4
    assert result["mae"] == pytest.approx(err.mean())
    assert result["p90_abs_err"] == pytest.approx(np.quantile(err, 0.9))
    assert result["mae_airport"] == pytest.approx((200.0 + 300.0) / 2)


@pytest.fixture(scope="module")
def replay(tmp_path_factory, prefect_harness):
    """Phát lại một lần cho cả module; chạy khi test gọi `replay()` để thiếu code thì test fail thay vì ERROR."""
    cache = {}

    def run():
        if "result" not in cache:
            cache["result"] = run_replay(tmp_path_factory.mktemp("m10-replay"))
        return cache["result"]

    return run


def run_replay(base):
    clock = need("clock", "months_between")
    cli = need("cli", "main")
    raw = base / "raw"
    raw.mkdir()
    for month in clock.months_between(REFERENCE, END):
        dataset = "nyc-tlc" if month < "2020" else "nyc-tlc-2020"
        (raw / f"yellow_tripdata_{month}.parquet").symlink_to(mlopskit.real_month(dataset, month))
    uri, name = local_registry(base, "eta-m10")
    config = write_config(base / "params.yaml", raw, [REFERENCE], uri, name, **REPLAY)
    out = base / "replay"
    code = cli.main(["replay", "--config", str(config), "--start", START, "--end", END, "--out", str(out)])
    assert code == 0, "eta.cli replay phải trả 0"
    path = out / "summary.parquet"
    assert path.is_file(), "replay phải ghi summary.parquet vào --out"
    return pd.read_parquet(path), out


def test_m10_replay_summary_real(project, replay):
    summary, out = replay()
    missing = [c for c in SUMMARY_COLUMNS if c not in summary.columns]
    assert not missing, f"summary.parquet thiếu cột {missing}"
    clock = need("clock", "months_between")
    assert summary["month"].tolist() == clock.months_between(START, END)
    assert (summary["n_scored"] > 0).all() and (summary["as_of"] == END).all()
    by = summary.set_index("month")
    assert by.loc["2020-04", "psi_trip_distance"] > by.loc["2019-12", "psi_trip_distance"], \
        "PSI trip_distance của 2020-04 (COVID) phải lớn hơn 2019-12 (mùa vụ)"
    assert math.isnan(by.loc[END, "mae"]) and by.loc[END, "n_labeled"] == 0, \
        "tháng cuối chưa có nhãn tại as_of: mae NaN, n_labeled 0"
    labeled = summary[summary["month"] < END]
    assert labeled["mae"].notna().all() and (labeled["n_labeled"] == labeled["n_scored"]).all()
    rows = json.loads((out / "replay.json").read_text(encoding="utf-8"))
    flow_mae = {r["month"]: r["mae"] for r in rows}
    for month, mae in labeled.set_index("month")["mae"].items():
        assert mae == pytest.approx(flow_mae[month], rel=1e-6), f"{month}: mae của summary khác mae của replay_flow"


def decision_files() -> list:
    folder = PROJECT / "reports" / "decisions"
    require_file("reports", "decisions", "2020-03.yaml")
    files = sorted(folder.glob("*.yaml"))
    assert len(files) >= 2, "cần 2020-03.yaml và ít nhất một quyết định khác (ví dụ tháng mùa vụ 2019-12)"
    return files


def close(actual, expected) -> bool:
    return math.isclose(float(actual), float(expected), rel_tol=0.01)


def test_m10_decision_files_valid(project, replay):
    labels = need("labels", "published")
    clock = need("clock", "add_months")
    files = decision_files()
    by = replay()[0].set_index("month")
    for path in files:
        month = path.stem
        assert month in by.index, f"{path.name}: tên tệp phải là một tháng trong {START}..{END}"
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        assert data.get("decision") in DECISIONS, f"{path.name}: decision phải thuộc {sorted(DECISIONS)}"
        reasons = data.get("reasons") or []
        assert len(reasons) >= 2 and all(isinstance(r, str) and len(r.split()) >= 6 for r in reasons), \
            f"{path.name}: cần ≥2 lý do, mỗi lý do là một câu có số liệu"
        evidence = data.get("evidence") or {}
        assert all(k in evidence for k in EVIDENCE), f"{path.name}: evidence cần {EVIDENCE}"
        as_of = str(evidence["as_of"])
        assert labels.published(month, as_of) and as_of <= END, \
            f"{path.name}: as_of {as_of} phải là lúc nhãn tháng {month} đã công bố (và không sau {END})"
        before = clock.add_months(month, -1)
        assert before in by.index, f"{path.name}: tháng trước {before} không có trong phát lại"
        expected = {"psi_trip_distance": by.loc[month, "psi_trip_distance"], "mae_after": by.loc[month, "mae"],
                    "mae_before": by.loc[before, "mae"]}
        for key, value in expected.items():
            assert close(evidence[key], value), f"{path.name}: evidence.{key} = {evidence[key]}, summary.parquet cho {value:.4f}"
        ratio = float(evidence["mae_after"]) / float(evidence["mae_before"])
        if ratio <= 1.0:
            assert data["decision"] == "keep", f"{path.name}: MAE không xấu đi (drift không phải lý do) thì decision là keep"
        if ratio > 1.5:
            assert data["decision"] != "keep", f"{path.name}: MAE xấu đi {ratio - 1:.0%} thì không được keep"


def heading_texts(text: str) -> list[str]:
    out, fenced = [], False
    for line in text.splitlines():
        if line.startswith("```"):
            fenced = not fenced
        elif not fenced and re.match(r"^#{1,4} ", line):
            out.append(line.lstrip("#").strip())
    return out


def check_doc(path, headings: list[str]) -> str:
    text = path.read_text(encoding="utf-8")
    found = heading_texts(text)
    missing = [h for h in headings if not any(t.startswith(h) or re.match(rf"^\d+(\.\d+)*\.? {re.escape(h)}", t) for t in found)]
    assert not missing, f"{path.name} thiếu heading {missing}"
    assert "TODO" not in text, f"{path.name} còn TODO"
    assert len(text.split()) >= 300, f"{path.name} quá ngắn (dưới 300 từ)"
    return text


def test_m10_docs_structure(project):
    runbook = check_doc(require_file("docs", "runbook.md"), RUNBOOK_HEADINGS)
    rules = PROJECT / "monitoring" / "rules" / "eta.rules.yml"
    if rules.is_file():
        alerts = [r["alert"] for g in yaml.safe_load(rules.read_text(encoding="utf-8"))["groups"] for r in g.get("rules", []) if "alert" in r]
        missing = [a for a in alerts if a not in runbook]
        assert not missing, f"runbook chưa nói cách xử lý alert {missing}"
    postmortem = check_doc(require_file("docs", "postmortem-covid.md"), POSTMORTEM_HEADINGS)
    assert "2020-03" in postmortem and "2020-04" in postmortem, "postmortem cần mốc 2020-03 và 2020-04 của phát lại"

"""M13: đánh giá độc lập mức junior trên một tháng dữ liệu lạ: chẩn đoán bằng pipeline có sẵn, bằng chứng có số, quyết định.

Đề ở capstone/milestones/m13-junior-assessment.md. Tháng lạ dựng bằng `etakit.assessment_data` từ dữ liệu thật.
"""

import math
import re

import pandas as pd
import pytest
import yaml
from etakit import PROJECT, assessment_data, assessment_month, injected_causes, local_registry, need, require_file, write_config

MONTH, BEFORE, START, END, TRAIN = "2019-10", "2019-09", "2019-09", "2019-11", "2019-08"
ASSESSMENT = {"sample_rows": 50_000, "seed": 0, "model_params": {"max_iter": 100}}
DECISIONS = {"keep", "retrain", "rollback"}
FINDING_KEYS = ["symptom", "evidence", "cause", "action"]
REQUIRED = {
    "unit_change": ["psi_trip_distance", "median_trip_distance", "median_trip_distance_before"],
    "timezone_shift": ["psi_pickup_hour", "peak_pickup_hour", "peak_pickup_hour_before"],
    "clock_error": ["negative_duration_share"],
    "outside_month": ["outside_month_share"],
    "duplicate_rows": ["duplicate_share"],
    "truncated_month": ["days_with_pickups"],
    "missing_zone": ["zone", "zone_share", "zone_share_before"],
    "seasonal_drift": ["mae", "mae_before"],
    "concept_drift": ["mae", "mae_before", "bias_s"],
}
MODEL_CAUSES = {"seasonal_drift", "concept_drift"}
SUMMARY_KEYS = {
    "psi_trip_distance": (MONTH, "psi_trip_distance"), "ks_trip_distance": (MONTH, "ks_trip_distance"),
    "psi_pickup_hour": (MONTH, "psi_pickup_hour"), "psi_eta_s": (MONTH, "psi_eta_s"), "mae": (MONTH, "mae"),
    "bias_s": (MONTH, "bias_s"), "mae_airport": (MONTH, "mae_airport"), "n_scored": (MONTH, "n_scored"),
    "mae_before": (BEFORE, "mae"), "bias_s_before": (BEFORE, "bias_s"),
}
INTEGER_KEYS = {"peak_pickup_hour", "peak_pickup_hour_before", "days_with_pickups", "zone", "n_scored"}
DOC_HEADINGS = ["Tóm tắt", "Cách điều tra", "Phát hiện", "Quyết định", "Phòng ngừa"]


def words(value) -> int:
    return len(str(value).split()) if isinstance(value, str) else 0


def load_diagnosis() -> dict:
    path = require_file("reports", "assessment", "diagnosis.yaml")
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(data, dict), "diagnosis.yaml phải là một mapping YAML"
    return data


def test_m13_diagnosis_valid(project):
    data = load_diagnosis()
    assert str(data.get("month")) == assessment_month() == MONTH, f"month phải là tháng lạ {MONTH}"
    findings = data.get("findings")
    assert isinstance(findings, list) and findings, "findings phải là danh sách không rỗng"
    causes = []
    for i, finding in enumerate(findings):
        assert isinstance(finding, dict) and all(k in finding for k in FINDING_KEYS), f"findings[{i}] cần đủ {FINDING_KEYS}"
        cause = finding["cause"]
        assert cause in REQUIRED, f"findings[{i}].cause {cause!r} không thuộc tập nhãn cho phép {sorted(REQUIRED)}"
        assert words(finding["symptom"]) >= 6 and words(finding["action"]) >= 6, \
            f"findings[{i}] ({cause}): symptom và action là câu đầy đủ (≥6 từ)"
        evidence = finding["evidence"]
        assert isinstance(evidence, dict), f"findings[{i}] ({cause}): evidence là mapping khoá → số"
        missing = [k for k in REQUIRED[cause] if k not in evidence]
        assert not missing, f"findings[{i}] ({cause}): evidence thiếu {missing}"
        causes.append(cause)
    assert len(set(causes)) == len(causes), "mỗi cause chỉ một finding (gộp bằng chứng vào cùng finding)"
    assert data.get("decision") in DECISIONS, f"decision phải thuộc {sorted(DECISIONS)}"
    reasons = data.get("reasons") or []
    assert len(reasons) >= 2 and all(words(r) >= 6 for r in reasons), "cần ≥2 reasons, mỗi lý do là một câu có số liệu"
    assert isinstance(data.get("quarantine"), bool), "quarantine phải là true hoặc false"
    if set(causes) - MODEL_CAUSES:
        assert data["quarantine"] is True, "có lỗi dữ liệu thì phải cách ly tháng (quarantine: true)"
        assert data["decision"] != "retrain", "có lỗi dữ liệu thì không train lại trên tháng đó (decision khác retrain)"


def test_m13_finds_injected_faults(project):
    data = load_diagnosis()
    claimed = {f.get("cause") for f in data.get("findings") or [] if isinstance(f, dict)}
    injected = injected_causes()
    missed = len(injected - claimed)
    extra = len(claimed - injected)
    assert missed == 0, f"còn {missed} lỗi trong tháng lạ chưa có finding với cause đúng"
    assert extra == 0, f"có {extra} cause không có trong tháng lạ (dương tính giả)"


@pytest.fixture(scope="module")
def assessment(tmp_path_factory, prefect_harness):
    """Dựng dữ liệu và phát lại một lần cho cả module; chạy khi test gọi `assessment()` để thiếu code thì fail, không ERROR."""
    cache = {}

    def run():
        if "result" not in cache:
            cache["result"] = run_assessment(tmp_path_factory.mktemp("m13-assessment"))
        return cache["result"]

    return run


def run_assessment(base):
    cli = need("cli", "main")
    data_dir = assessment_data(base / "data")
    uri, name = local_registry(base, "eta-m13")
    config = write_config(base / "params.yaml", data_dir, [TRAIN], uri, name, **ASSESSMENT)
    out = base / "replay"
    code = cli.main(["replay", "--config", str(config), "--start", START, "--end", END, "--out", str(out)])
    assert code == 0, "eta.cli replay phải trả 0"
    path = out / "summary.parquet"
    assert path.is_file(), "replay phải ghi summary.parquet vào --out"
    return pd.read_parquet(path).set_index("month"), data_dir


def sample_facts(raw: pd.DataFrame, month: str, zone: int | None) -> dict:
    start = pd.Timestamp(f"{month}-01")
    end = start + pd.offsets.MonthBegin(1)
    pickup, dropoff = raw["tpep_pickup_datetime"], raw["tpep_dropoff_datetime"]
    inside = (pickup >= start) & (pickup < end)
    facts = {
        "negative_duration_share": float((dropoff < pickup).mean()),
        "outside_month_share": float((~inside).mean()),
        "duplicate_share": float(raw.duplicated().mean()),
        "median_trip_distance": float(raw["trip_distance"].median()),
        "peak_pickup_hour": int(pickup.dt.hour.value_counts().sort_index().idxmax()),
        "days_with_pickups": int(pickup[inside].dt.date.nunique()),
    }
    if zone is not None:
        facts["zone_share"] = float(((raw["PULocationID"] == zone) | (raw["DOLocationID"] == zone)).mean())
    return facts


def recomputed(summary: pd.DataFrame, data_dir, zone: int | None) -> dict:
    data = need("data", "load_month")
    values = {key: summary.loc[month, column] for key, (month, column) in SUMMARY_KEYS.items()}
    for month, suffix in ((MONTH, ""), (BEFORE, "_before")):
        raw = data.load_month(data_dir / f"yellow_tripdata_{month}.parquet", ASSESSMENT["sample_rows"], ASSESSMENT["seed"])
        values.update({key + suffix: value for key, value in sample_facts(raw, month, zone).items()})
    if zone is not None:
        values["zone"] = zone
    return values


def matches(key: str, claimed, expected) -> bool:
    if key in INTEGER_KEYS:
        return isinstance(claimed, (int, float)) and float(claimed) == float(expected)
    if not isinstance(claimed, (int, float)) or isinstance(claimed, bool):
        return False
    return math.isclose(float(claimed), float(expected), rel_tol=0.01, abs_tol=1e-9)


def test_m13_evidence_matches_recomputed(project, assessment):
    data = load_diagnosis()
    findings = [f for f in data.get("findings") or [] if isinstance(f, dict) and isinstance(f.get("evidence"), dict)]
    summary, data_dir = assessment()
    assert summary.loc[MONTH, "n_labeled"] > 0, f"{MONTH} phải có nhãn tại as_of {END}"
    for finding in findings:
        evidence = finding["evidence"]
        zone = evidence.get("zone") if isinstance(evidence.get("zone"), int) else None
        expected = recomputed(summary, data_dir, zone)
        for key, claimed in evidence.items():
            if key in expected:
                ok = matches(key, claimed, expected[key])
                assert ok, \
                    f"{finding.get('cause')}: evidence.{key} = {claimed} không khớp số tính lại theo đề " \
                    f"({'bằng đúng' if key in INTEGER_KEYS else 'sai số tương đối 1%'})"
    if data.get("decision") == "rollback":
        versions = set(summary["model_version"].astype(str))
        assert len(versions) > 1, f"champion không đổi trong phát lại (version {sorted(versions)}): không có gì để rollback"


def heading_texts(text: str) -> list[str]:
    out, fenced = [], False
    for line in text.splitlines():
        if line.startswith("```"):
            fenced = not fenced
        elif not fenced and re.match(r"^#{1,4} ", line):
            out.append(line.lstrip("#").strip())
    return out


def test_m13_assessment_doc(project):
    path = require_file("docs", "assessment.md")
    text = path.read_text(encoding="utf-8")
    found = heading_texts(text)
    missing = [h for h in DOC_HEADINGS if not any(t.startswith(h) or re.match(rf"^\d+(\.\d+)*\.? {re.escape(h)}", t) for t in found)]
    assert not missing, f"assessment.md thiếu heading {missing}"
    assert "TODO" not in text and len(text.split()) >= 400, "assessment.md cần ít nhất 400 từ, không còn TODO"
    for command in ("eta.cli validate", "eta.cli replay"):
        assert command in text, f"assessment.md cần lệnh đã chạy: {command}"
    causes = [f.get("cause") for f in load_diagnosis().get("findings") or [] if isinstance(f, dict)]
    absent = [c for c in causes if c and c not in text]
    assert not absent, f"assessment.md cần giải thích từng cause trong diagnosis.yaml: thiếu {absent}"

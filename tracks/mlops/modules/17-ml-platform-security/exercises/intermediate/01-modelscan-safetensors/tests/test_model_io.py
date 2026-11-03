import json
import pickle
import subprocess

import numpy as np
import pytest
from safetensors import safe_open
from sklearn.datasets import load_diabetes
from sklearn.linear_model import Ridge

import mlopskit
import seckit
from testkit import Exercise

ex = Exercise(__file__)
MEASURED = "hành vi đo trên modelscan 0.8.8; xem README module mục 5"


@pytest.fixture(scope="module")
def mio():
    return ex.module("model_io.py")


@pytest.fixture
def marker(tmp_path):
    path = tmp_path / "marker" / "pwned.txt"
    path.parent.mkdir()
    return path


def model_dir(tmp_path, name="model"):
    return seckit.safetensors_model(tmp_path / name)


def fake_scan(returncode, report):
    calls = []

    def scan(path):
        calls.append(path)
        stdout = report if isinstance(report, str) else json.dumps(report)
        return subprocess.CompletedProcess(["modelscan"], returncode, stdout, "")

    scan.calls = calls
    return scan


def report(issues=(), errors=(), scanned=()):
    return {"summary": {"scanned": {"total_scanned": len(scanned), "scanned_files": list(scanned)}},
            "issues": list(issues), "errors": list(errors)}


def issue(severity, module="builtins", operator="exec"):
    return {"description": "x", "operator": operator, "module": module, "source": "w.pkl", "severity": severity}


def test_export_and_load_linear_matches_sklearn(mio, tmp_path):
    X, y = load_diabetes(return_X_y=True)
    model = Ridge(alpha=0.5).fit(X, y)
    path = tmp_path / "ridge.safetensors"
    mio.export_linear(model, path)
    with safe_open(str(path), framework="numpy") as handle:
        assert handle.metadata().get("format") == "linear"
        assert set(handle.keys()) == {"coef", "intercept"}
    predict = mio.load_linear(path)
    assert np.allclose(predict(X), model.predict(X))


def test_loading_a_pickle_runs_code(tmp_path):
    flag = tmp_path / "loaded.txt"
    data = seckit.marker_pickle(flag)
    pickle.loads(data)
    assert flag.read_text() == "pwned"


def test_sniff_by_content_not_extension(mio, tmp_path, marker):
    folder = model_dir(tmp_path)
    (folder / "sub").mkdir()
    (folder / "sub" / "legacy.pkl").write_bytes(seckit.plain_pickle())
    (folder / "weights.safetensors").write_bytes(seckit.marker_pickle(marker))
    (folder / "notes.txt").write_bytes(b"\x00\x01binary")
    (folder / "config.bin").write_text('{"a": 1}', encoding="utf-8")
    (folder / "link.json").symlink_to(folder / "config.json")
    assert mio.file_formats(folder) == {
        "model.safetensors": "safetensors",
        "config.json": "json",
        "config.bin": "json",
        "sub/legacy.pkl": "pickle",
        "weights.safetensors": "pickle",
        "notes.txt": "other",
        "link.json": "symlink",
    }
    assert not marker.exists()


def test_safetensors_model_passes(mio, tmp_path):
    folder = model_dir(tmp_path)
    decision = mio.gate(folder, mlopskit.modelscan_run)
    assert decision == {"allowed": True, "reasons": []}


def test_malicious_pickle_blocked_by_scanner_even_when_pickle_allowed(mio, tmp_path, marker):
    folder = model_dir(tmp_path)
    (folder / "preprocess.pkl").write_bytes(seckit.marker_pickle(marker))
    decision = mio.gate(folder, mlopskit.modelscan_run, allow_pickle=True)
    assert decision == {"allowed": False, "reasons": ["scan-issue:builtins.exec"]}
    assert not marker.exists()


def test_malicious_pickle_blocked_twice_by_default(mio, tmp_path, marker):
    folder = model_dir(tmp_path)
    (folder / "preprocess.pkl").write_bytes(seckit.marker_pickle(marker))
    decision = mio.gate(folder, mlopskit.modelscan_run)
    assert decision == {"allowed": False, "reasons": ["format:preprocess.pkl", "scan-issue:builtins.exec"]}
    assert not marker.exists()


def test_scanner_alone_misses_a_payload_that_the_allowlist_stops(mio, tmp_path, marker):
    folder = model_dir(tmp_path)
    (folder / "preprocess.pkl").write_bytes(seckit.stealth_pickle(marker))
    raw = mlopskit.modelscan_run(folder)
    assert raw.returncode == 0 and json.loads(raw.stdout)["issues"] == [], MEASURED
    decision = mio.gate(folder, mlopskit.modelscan_run)
    assert decision == {"allowed": False, "reasons": ["format:preprocess.pkl"]}
    assert not marker.exists()


def test_known_residual_risk_of_the_pickle_path(mio, tmp_path, marker):
    folder = model_dir(tmp_path)
    (folder / "preprocess.pkl").write_bytes(seckit.stealth_pickle(marker))
    decision = mio.gate(folder, mlopskit.modelscan_run, allow_pickle=True)
    assert decision == {"allowed": True, "reasons": []}, MEASURED
    assert not marker.exists()


def test_disguised_pickle_blocked(mio, tmp_path, marker):
    folder = model_dir(tmp_path)
    (folder / "model.safetensors").write_bytes(seckit.marker_pickle(marker))
    raw = mlopskit.modelscan_run(folder)
    assert raw.returncode == 3, MEASURED
    decision = mio.gate(folder, mlopskit.modelscan_run, allow_pickle=True)
    assert decision["allowed"] is False
    assert decision["reasons"] == ["unscanned:model.safetensors"]
    assert not marker.exists()


def test_legacy_plain_pickle_allowed_only_when_scanned(mio, tmp_path):
    folder = model_dir(tmp_path)
    (folder / "legacy.pkl").write_bytes(seckit.plain_pickle())
    assert mio.gate(folder, mlopskit.modelscan_run, allow_pickle=True) == {"allowed": True, "reasons": []}
    (folder / "legacy.pkl").rename(folder / "legacy.bin")
    decision = mio.gate(folder, mlopskit.modelscan_run, allow_pickle=True)
    assert decision == {"allowed": False, "reasons": ["unscanned:legacy.bin"]}, MEASURED


def test_gate_scans_the_model_directory(mio, tmp_path):
    folder = model_dir(tmp_path)
    scan = fake_scan(3, report())
    assert mio.gate(folder, scan)["allowed"] is True
    assert len(scan.calls) == 1 and str(scan.calls[0]) == str(folder)


SCAN_FAILURES = {
    "tool-error": (2, report()),
    "unsupported": (4, report()),
    "not-json": (0, "Traceback (most recent call last): ..."),
    "empty-output": (0, ""),
    "parse-errors": (3, report(errors=[{"category": "PICKLE_GENOPS", "description": "x", "source": "w.pkl"}])),
    "issues-flag-without-issues": (1, report()),
    "json-not-object": (0, "[]"),
}


@pytest.mark.parametrize("case", list(SCAN_FAILURES))
def test_scan_failure_fails_closed(mio, tmp_path, case):
    code, body = SCAN_FAILURES[case]
    decision = mio.gate(model_dir(tmp_path), fake_scan(code, body))
    blocked = decision["allowed"] is False and decision["reasons"] == ["scan-error"]
    assert blocked, f"ca {case}"


def test_low_severity_finding_does_not_block(mio, tmp_path):
    folder = model_dir(tmp_path)
    decision = mio.gate(folder, fake_scan(1, report(issues=[issue("LOW", "collections", "OrderedDict")])))
    assert decision == {"allowed": True, "reasons": []}
    decision = mio.gate(folder, fake_scan(1, report(issues=[issue("MEDIUM", "webbrowser", "open"), issue("HIGH")])))
    assert decision == {"allowed": False, "reasons": ["scan-issue:builtins.exec", "scan-issue:webbrowser.open"]}


def test_empty_or_symlinked_model_blocked(mio, tmp_path):
    empty = tmp_path / "empty"
    empty.mkdir()
    assert mio.gate(empty, fake_scan(3, report())) == {"allowed": False, "reasons": ["empty"]}
    folder = model_dir(tmp_path)
    (folder / "extra.json").symlink_to(tmp_path / "outside.json")
    (tmp_path / "outside.json").write_text("{}", encoding="utf-8")
    assert mio.gate(folder, fake_scan(3, report())) == {"allowed": False, "reasons": ["format:extra.json"]}

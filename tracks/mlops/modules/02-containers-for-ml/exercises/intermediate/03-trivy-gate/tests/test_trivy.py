import json
from pathlib import Path

import pytest

from testkit import Exercise, run_sandboxed

ex = Exercise(__file__)

POLICY = {"fail_on": ["CRITICAL", "HIGH"], "ignore_unfixed": True, "allow": ["CVE-2025-0003"]}


def vuln(vuln_id: str, severity: str, fixed: str = "1.0.1") -> dict:
    return {"VulnerabilityID": vuln_id, "Severity": severity, "FixedVersion": fixed, "PkgName": "libfoo"}


def report(*groups) -> dict:
    return {"Results": [{"Target": f"layer{i}", "Vulnerabilities": group} for i, group in enumerate(groups)]}


def test_gate_blocks_fixable_high_and_critical():
    gate = ex.module("triage.py").gate
    result = gate(report([vuln("CVE-2025-0001", "HIGH"), vuln("CVE-2025-0002", "CRITICAL")]), POLICY)
    assert result == {"decision": "fail", "blocking": ["CVE-2025-0001", "CVE-2025-0002"], "ignored": []}


def test_gate_ignores_low_and_medium():
    gate = ex.module("triage.py").gate
    result = gate(report([vuln("CVE-2025-0004", "MEDIUM"), vuln("CVE-2025-0005", "LOW")]), POLICY)
    assert result == {"decision": "pass", "blocking": [], "ignored": []}


def test_gate_ignores_unfixed_and_allowlisted_but_reports_them():
    gate = ex.module("triage.py").gate
    data = report([vuln("CVE-2025-0006", "HIGH", fixed=""), vuln("CVE-2025-0003", "CRITICAL")])
    assert gate(data, POLICY) == {"decision": "pass", "blocking": [], "ignored": ["CVE-2025-0003", "CVE-2025-0006"]}


def test_gate_unfixed_counts_when_policy_says_so():
    gate = ex.module("triage.py").gate
    policy = {**POLICY, "ignore_unfixed": False}
    assert gate(report([vuln("CVE-2025-0006", "HIGH", fixed="")]), policy)["decision"] == "fail"


def test_gate_deduplicates_across_targets_and_prefers_blocking():
    gate = ex.module("triage.py").gate
    data = report([vuln("CVE-2025-0001", "HIGH")], [vuln("CVE-2025-0001", "HIGH", fixed="")])
    assert gate(data, POLICY) == {"decision": "fail", "blocking": ["CVE-2025-0001"], "ignored": []}


def test_gate_handles_clean_scan_with_null_vulnerabilities():
    gate = ex.module("triage.py").gate
    clean = {"Results": [{"Target": "os", "Vulnerabilities": None}, {"Target": "python"}]}
    assert gate(clean, POLICY) == {"decision": "pass", "blocking": [], "ignored": []}
    assert gate({}, POLICY)["decision"] == "pass"


def test_dockerfile_has_no_trivy_misconfigurations(tmp_path):
    ex.require_tool("trivy", "0.60")
    (tmp_path / "scan").mkdir()
    (tmp_path / "scan" / "Dockerfile").write_text(ex.read("Dockerfile"))
    result = run_sandboxed(
        ["trivy", "config", "--format", "json", "--quiet", "--cache-dir", str(tmp_path / "cache"), "--skip-version-check",
         str(tmp_path / "scan")],
        writable=[tmp_path], cwd=tmp_path, env={}, timeout=120,
    )
    assert result.returncode == 0, result.stderr[-800:]
    findings = [
        f"{m['ID']} ({m['Severity']}): {m['Title']}"
        for item in json.loads(result.stdout).get("Results", [])
        for m in item.get("Misconfigurations", [])
        if m["Status"] == "FAIL"
    ]
    assert not findings, "trivy config còn báo:\n" + "\n".join(findings)


def test_dockerfile_still_installs_flask_pinned():
    text = ex.read("Dockerfile")
    assert "flask==" in text, "Giữ pip install flask nhưng ghim phiên bản"

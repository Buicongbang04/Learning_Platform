def gate(report: dict, policy: dict) -> dict:
    """Quyết định pass/fail từ báo cáo `trivy image --format json` theo policy.

    policy = {"fail_on": ["CRITICAL", "HIGH"], "ignore_unfixed": True, "allow": ["CVE-2024-0001"]}
    Trả về {"decision": "pass" | "fail", "blocking": [...], "ignored": [...]}, hai danh sách là
    VulnerabilityID đã sắp xếp, không trùng.
    """
    fail_on = set(policy.get("fail_on", []))
    allow = set(policy.get("allow", []))
    blocking: set[str] = set()
    ignored: set[str] = set()
    for result in report.get("Results") or []:
        for vuln in result.get("Vulnerabilities") or []:
            if vuln["Severity"] not in fail_on:
                continue
            vuln_id = vuln["VulnerabilityID"]
            unfixed = not vuln.get("FixedVersion")
            if vuln_id in allow or (policy.get("ignore_unfixed") and unfixed):
                ignored.add(vuln_id)
            else:
                blocking.add(vuln_id)
    ignored -= blocking
    return {"decision": "fail" if blocking else "pass", "blocking": sorted(blocking), "ignored": sorted(ignored)}

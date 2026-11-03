def gate(report: dict, policy: dict) -> dict:
    """Quyết định pass/fail từ báo cáo `trivy image --format json` theo policy.

    policy = {"fail_on": ["CRITICAL", "HIGH"], "ignore_unfixed": True, "allow": ["CVE-2024-0001"]}
    Trả về {"decision": "pass" | "fail", "blocking": [...], "ignored": [...]}, hai danh sách là
    VulnerabilityID đã sắp xếp, không trùng.
    """
    # TODO
    raise NotImplementedError

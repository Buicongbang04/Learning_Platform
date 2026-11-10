import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
REQUIREMENTS = yaml.safe_load((ROOT / "survey" / "REQUIREMENTS.yaml").read_text(encoding="utf-8"))
SURVEY = json.loads((ROOT / "reports" / "survey-lawfirm-staging.json").read_text(encoding="utf-8"))

spec = importlib.util.spec_from_file_location("preflight", ROOT / "survey" / "preflight.py")
preflight = importlib.util.module_from_spec(spec)
spec.loader.exec_module(preflight)


def checks(findings: list[dict], severity: str) -> set[str]:
    return {f["check"] for f in findings if f["severity"] == severity}


def test_staging_has_no_blocker():
    findings = preflight.preflight(SURVEY, REQUIREMENTS)
    assert checks(findings, "blocker") == set()
    assert {"egress", "compose"} <= checks(findings, "warning")


def test_small_vm_is_blocked_on_memory():
    findings = preflight.preflight(SURVEY | {"mem_mb": 1900}, REQUIREMENTS)
    assert "mem" in checks(findings, "blocker")


def test_old_os_and_missing_runtime_are_blockers():
    findings = preflight.preflight(SURVEY | {"os_id": "centos", "os_version": "7", "runtime": None}, REQUIREMENTS)
    assert {"os", "runtime"} <= checks(findings, "blocker")


def test_cli_exit_code(tmp_path):
    data = tmp_path / "survey.json"
    data.write_text(json.dumps(SURVEY | {"cpus": 1}), encoding="utf-8")
    result = subprocess.run([sys.executable, ROOT / "survey" / "preflight.py", data, ROOT / "survey" / "REQUIREMENTS.yaml"],
                            capture_output=True, text=True, check=False)
    assert result.returncode == 1
    assert "cpus" in checks(json.loads(result.stdout), "blocker")

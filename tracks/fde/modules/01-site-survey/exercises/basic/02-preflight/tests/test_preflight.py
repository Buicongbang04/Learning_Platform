import copy
import json

import pytest
import yaml

import fdekit
from testkit import ROOT, Exercise

ex = Exercise(__file__)
REQUIREMENTS_PATH = ROOT / "tracks" / "fde" / "product" / "REQUIREMENTS.yaml"
REQUIREMENTS = yaml.safe_load(REQUIREMENTS_PATH.read_text(encoding="utf-8"))
CHECKS = ("os", "cpus", "mem", "disk", "runtime", "sudo", "selinux", "egress", "gpu")
NUMERIC = {"cpus": ("cpus", "min_cpus"), "mem": ("mem_mb", "min_mem_mb"), "disk": ("disk_free_gb_max", "min_disk_free_gb")}
OPTIONAL_WARNING = {None, "warning"}
MEASURED = {"lab-open": (1963, 17.5), "hospital": (1971, 6.0), "bank": (1778, 17.5), "lawfirm-staging": (1963, 27.2)}
GOOD = {
    "os_id": "ubuntu", "os_version": "22.04", "kernel_major": "5.15", "glibc": "2.35", "cpus": 8, "mem_mb": 15990,
    "disk_free_gb_max": 120.0, "gpu": None, "proxy_url": None, "sudo": True, "selinux": "n/a", "runtime": "docker",
    "egress": "open",
}


def site(name: str) -> dict:
    survey = dict(fdekit.PROFILES[name].facts)
    survey["mem_mb"], survey["disk_free_gb_max"] = MEASURED[name]
    return survey


def machine(**changes) -> dict:
    return {**GOOD, **changes}


def requirements(**changes) -> dict:
    return {**copy.deepcopy(REQUIREMENTS), **changes}


@pytest.fixture(scope="module")
def mod():
    return ex.module("preflight.py")


def run(mod, survey: dict, req: dict | None = None) -> dict[str, dict]:
    req = REQUIREMENTS if req is None else req
    findings = mod.preflight(copy.deepcopy(survey), copy.deepcopy(req))
    assert isinstance(findings, list), f"preflight() phải trả list, nhận {type(findings).__name__}"
    by_check = {}
    for item in findings:
        assert isinstance(item, dict) and set(item) == {"check", "severity", "detail"}, (
            f"Mỗi phát hiện là dict đúng ba khoá check/severity/detail, nhận {item!r}")
        assert item["check"] in CHECKS, f"check {item['check']!r} không thuộc {CHECKS}"
        assert item["severity"] in ("blocker", "warning"), f"severity {item['severity']!r} phải là blocker hoặc warning"
        assert isinstance(item["detail"], str) and item["detail"].strip(), f"detail của {item['check']} rỗng"
        assert item["check"] not in by_check, f"check {item['check']!r} xuất hiện hai lần"
        by_check[item["check"]] = item
    for check, (survey_key, req_key) in NUMERIC.items():
        if check in by_check and by_check[check]["severity"] == "blocker":
            detail = by_check[check]["detail"]
            for value in (survey[survey_key], req[req_key]):
                assert str(value) in detail, f"detail của {check} phải ghi giá trị {value}: {detail!r}"
    return by_check


def expect(by_check: dict[str, dict], **accepted) -> None:
    for check in CHECKS:
        allowed = accepted.get(check, {None})
        got = by_check[check]["severity"] if check in by_check else None
        assert got in allowed, f"{check}: nhận {got!r}, chấp nhận {sorted(allowed, key=str)} (None = không báo)"


def test_good_machine_has_no_findings(mod):
    expect(run(mod, GOOD))


def test_lab_open_default_vm(mod):
    expect(run(mod, site("lab-open")), mem={"blocker"})


def test_hospital_small_disk_is_a_blocker(mod):
    expect(run(mod, site("hospital")), mem={"blocker"}, disk={"blocker"}, egress=OPTIONAL_WARNING)


def test_bank_no_sudo_with_podman_is_not_a_blocker(mod):
    expect(run(mod, site("bank")), mem={"blocker"}, sudo=OPTIONAL_WARNING, selinux=OPTIONAL_WARNING,
           egress=OPTIONAL_WARNING)


def test_lawfirm_staging(mod):
    expect(run(mod, site("lawfirm-staging")), mem={"blocker"}, egress=OPTIONAL_WARNING)


@pytest.mark.parametrize("os_id, version, ok", [
    ("ubuntu", "20.04", True), ("ubuntu", "24.04", True), ("ubuntu", "18.04", False), ("rocky", "8.10", True),
    ("rocky", "9.4", True), ("debian", "11", True), ("debian", "10", False), ("centos", "7", False),
])
def test_os_support(mod, os_id, version, ok):
    expect(run(mod, machine(os_id=os_id, os_version=version)), os={None} if ok else {"blocker"})


def test_os_version_is_compared_as_numbers(mod):
    newer = requirements(os=[{"id": "rocky", "min": "8.9"}, {"id": "ubuntu", "min": "20.04"}])
    expect(run(mod, machine(os_id="rocky", os_version="8.10"), newer))
    expect(run(mod, machine(os_id="rocky", os_version="8.8"), newer), os={"blocker"})


@pytest.mark.parametrize("mem, accepted", [(3900, {"warning", "blocker"}), (3500, {"blocker"}), (4096, {None})])
def test_memtotal_versus_nominal_ram(mod, mem, accepted):
    expect(run(mod, machine(mem_mb=mem)), mem=accepted)


def test_cpus_below_minimum(mod):
    expect(run(mod, machine(cpus=1)), cpus={"blocker"})


@pytest.mark.parametrize("disk, accepted", [(9.9, {"blocker"}), (10.0, OPTIONAL_WARNING), (14.5, OPTIONAL_WARNING),
                                            (25.0, {None})])
def test_disk_thresholds(mod, disk, accepted):
    expect(run(mod, machine(disk_free_gb_max=disk)), disk=accepted)


def test_missing_runtime_is_a_blocker(mod):
    expect(run(mod, machine(runtime=None)), runtime={"blocker"})


def test_no_sudo_with_docker_needs_attention(mod):
    expect(run(mod, machine(sudo=False)), sudo={"warning", "blocker"})


def test_no_sudo_without_runtime(mod):
    expect(run(mod, machine(sudo=False, runtime=None)), runtime={"blocker"}, sudo={None, "warning", "blocker"})


@pytest.mark.parametrize("selinux", ["permissive", "disabled"])
def test_selinux_not_enforcing_is_fine(mod, selinux):
    expect(run(mod, machine(os_id="rocky", os_version="9.4", selinux=selinux)))


def test_gpu_is_optional(mod):
    expect(run(mod, machine(gpu="NVIDIA A10")))
    expect(run(mod, machine(gpu=None)))


def test_requirements_are_read_not_hardcoded(mod):
    relaxed = requirements(min_mem_mb=1024, min_disk_free_gb=5)
    expect(run(mod, site("hospital"), relaxed), egress=OPTIONAL_WARNING)
    podman_only = requirements(runtime=["podman>=4.0"], os=[{"id": "rocky", "min": "8"}])
    expect(run(mod, site("lab-open"), podman_only), os={"blocker"}, mem={"blocker"}, runtime={"blocker"})
    expect(run(mod, machine(cpus=4), requirements(min_cpus=8)), cpus={"blocker"})


def test_cli_prints_json_and_exit_code(mod, tmp_path, capsys):
    for survey, code in ((site("hospital"), 1), (GOOD, 0)):
        path = tmp_path / "survey.json"
        path.write_text(json.dumps(survey), encoding="utf-8")
        assert mod.main([str(path), str(REQUIREMENTS_PATH)]) == code
        printed = json.loads(capsys.readouterr().out)
        assert printed == mod.preflight(copy.deepcopy(survey), copy.deepcopy(REQUIREMENTS))

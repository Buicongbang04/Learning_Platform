import json
import subprocess
import sys

import pytest

from testkit import Exercise, run_sandboxed

ex = Exercise(__file__)
ERRORS = {"no_driver", "driver_too_old", "require_cuda_blocks", "cuda_drops_gpu", "driver_drops_gpu", "no_toolkit",
          "cdi_unsupported"}
LLAMA_CUDA_BRANCHES = [470, 535, 550, 560, 565]
WARNINGS = {"minor_version_compat", "cdi_needs_daemon_config", "toolkit_cve"}
SAFE = "1.19.1"


def host(driver="550.163.01", cuda="12.4.1", toolkit=SAFE, cc="8.6", access="gpus", docker="29.1.2", **extra):
    return {"driver": driver, "cuda": cuda, "toolkit": toolkit, "compute_capability": cc, "access": access,
            "docker": docker, **extra}


CASES = [
    ("laptop-driver-broken", host(driver=None), {"no_driver"}),
    ("rtx3060-cuda12.4", host(), set()),
    ("rtx3060-cuda12.8-minor-compat", host(cuda="12.8.1"), {"minor_version_compat"}),
    ("llama-cuda-image-on-550", host(cuda="12.8.1", require_branches=LLAMA_CUDA_BRANCHES), {"minor_version_compat"}),
    ("llama-cuda-image-on-545-blocked", host(driver="545.29.06", cuda="12.8.1", require_branches=LLAMA_CUDA_BRANCHES),
     {"require_cuda_blocks"}),
    ("llama-cuda-image-on-555-disable-require", host(driver="555.58.02", cuda="12.8.1", require_branches=LLAMA_CUDA_BRANCHES,
                                                     disable_require=True), {"minor_version_compat"}),
    ("llama-cuda-image-on-570-exact", host(driver="570.172.08", cuda="12.8.1", require_branches=LLAMA_CUDA_BRANCHES), set()),
    ("require-list-irrelevant-below-major", host(driver="470.256.02", cuda="12.8.1", require_branches=LLAMA_CUDA_BRANCHES),
     {"driver_too_old"}),
    ("driver535-cuda13", host(driver="535.183.01", cuda="13.0.1"), {"driver_too_old"}),
    ("driver470-cuda12.2", host(driver="470.256.02", cuda="12.2.2"), {"driver_too_old"}),
    ("driver470-cuda11.8-minor-compat", host(driver="470.256.02", cuda="11.8.0"), {"minor_version_compat"}),
    ("driver450.51-cuda11.2", host(driver="450.51.05", cuda="11.2.2", cc="7.0"), {"driver_too_old"}),
    ("driver450.51-cuda11.0", host(driver="450.51.05", cuda="11.0.3", cc="7.0"), set()),
    ("driver525.60.13-cuda12.0-boundary", host(driver="525.60.13", cuda="12.0.0"), set()),
    ("driver525.60.12-cuda12.0-below", host(driver="525.60.12", cuda="12.0.0"), {"driver_too_old"}),
    ("p100-cuda13", host(driver="580.95.05", cuda="13.0.1", cc="6.0"), {"cuda_drops_gpu"}),
    ("p100-driver590", host(driver="590.44.01", cuda="12.4.1", cc="6.0"), {"driver_drops_gpu"}),
    ("v100-driver580-cuda12.9", host(driver="580.95.05", cuda="12.9.1", cc="7.0"), set()),
    ("k80-driver470-cuda11.4", host(driver="470.256.02", cuda="11.4.4", cc="3.7"), set()),
    ("k80-driver535-cuda11.8", host(driver="535.183.01", cuda="11.8.0", cc="3.7"), {"driver_drops_gpu"}),
    ("k80-cuda12", host(driver="470.256.02", cuda="12.2.2", cc="3.7"), {"driver_too_old", "cuda_drops_gpu"}),
    ("no-toolkit", host(toolkit=None), {"no_toolkit"}),
    ("old-toolkit", host(toolkit="1.17.3"), {"toolkit_cve"}),
    ("cdi-toolkit-too-old", host(toolkit="1.11.0", access="cdi", docker="28.3.0"), {"cdi_unsupported", "toolkit_cve"}),
    ("cdi-docker24", host(access="cdi", docker="24.0.7"), {"cdi_unsupported"}),
    ("cdi-docker27-needs-config", host(access="cdi", docker="27.5.1"), {"cdi_needs_daemon_config"}),
    ("cdi-docker28.1-needs-config", host(access="cdi", docker="28.1.1"), {"cdi_needs_daemon_config"}),
    ("cdi-docker28.2-default-on", host(access="cdi", docker="28.2.0"), set()),
    ("cdi-docker28.3", host(access="cdi", docker="28.3.0"), set()),
    ("gpus-ignores-docker-version", host(docker="20.10.24"), set()),
    ("cuda13.1-on-580-minor-compat", host(driver="580.95.05", cuda="13.1.0"), {"minor_version_compat"}),
    ("cuda13.0.3-on-580.126", host(driver="580.126.20", cuda="13.0.3"), set()),
    ("cuda12.6-update-uses-ga", host(driver="560.28.03", cuda="12.6.3"), set()),
]


@pytest.fixture(scope="module")
def mod():
    return ex.module("cuda_compat.py")


@pytest.mark.parametrize("given,want", [(h, w) for _, h, w in CASES], ids=[c[0] for c in CASES])
def test_cases(mod, given, want):
    result = mod.check(dict(given))
    assert isinstance(result, dict) and {"compatible", "issues"} <= set(result), "check() trả dict có compatible, issues"
    codes = [item["code"] for item in result["issues"]]
    assert len(codes) == len(set(codes)), f"Mỗi code tối đa một lần: {codes}"
    assert set(codes) == want, f"{given}: cần {sorted(want)}, nhận {sorted(codes)}"
    for item in result["issues"]:
        want_severity = "error" if item["code"] in ERRORS else "warning"
        assert item.get("severity") == want_severity, f"{item['code']} có severity {want_severity}"
        assert isinstance(item.get("detail"), str) and item["detail"], f"{item['code']} cần detail (lý do)"
    assert result["compatible"] is (not want & ERRORS), f"compatible sai với {sorted(want)}"


@pytest.mark.parametrize("given", [host(cuda="12.7.0"), host(cuda="10.2.89"), host(access="nvidia")],
                         ids=["cuda-12.7-does-not-exist", "cuda-10-not-in-table", "bad-access"])
def test_unknown_input_raises(mod, given):
    with pytest.raises(ValueError):
        mod.check(given)


def test_cli(tmp_path):
    good, bad = tmp_path / "good.json", tmp_path / "bad.json"
    good.write_text(json.dumps(host(cuda="12.8.1")))
    bad.write_text(json.dumps(host(driver="535.183.01", cuda="13.0.1")))
    script = ex.path("cuda_compat.py")
    results = {}
    for name, path in (("good", good), ("bad", bad)):
        try:
            results[name] = run_sandboxed([sys.executable, script, path], writable=[tmp_path], cwd=tmp_path, env={},
                                          timeout=60)
        except subprocess.TimeoutExpired:
            pytest.fail("cuda_compat.py chạy quá 60 s")
    assert results["good"].returncode == 0, f"Tương thích thì mã thoát 0\n{results['good'].stderr[-1000:]}"
    assert results["bad"].returncode == 1, f"Không tương thích thì mã thoát 1\n{results['bad'].stderr[-1000:]}"
    assert {i["code"] for i in json.loads(results["good"].stdout)["issues"]} == {"minor_version_compat"}
    assert {i["code"] for i in json.loads(results["bad"].stdout)["issues"]} == {"driver_too_old"}

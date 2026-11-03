import importlib.metadata as md
import sys

import pytest

from testkit import Exercise

ex = Exercise(__file__)
SERVING = """\
# serving image của pricing-tip-amount
fastapi==0.115.6
uvicorn[standard]==0.34.0 ; python_version >= "3.10"
numpy==2.2.1 \\
    --hash=sha256:0000000000000000000000000000000000000000000000000000000000000000
Scikit_Learn
safetensors>=0.4
"""
SERVING_V2 = """\
uvicorn[standard]==0.34.0
numpy==2.3.0
Scikit_Learn
safetensors>=0.4
pyarrow==18.1.0
"""
RUNTIME = ["numpy", "scikit-learn", "safetensors", "model-signing", "mlflow"]


@pytest.fixture(scope="module")
def sb():
    return ex.module("sbom.py")


@pytest.fixture(scope="module")
def workdir(tmp_path_factory):
    folder = tmp_path_factory.mktemp("sbom")
    (folder / "requirements.txt").write_text(SERVING, encoding="utf-8")
    return folder


_CACHE = {}


def lock_sbom(sb, workdir):
    if "lock" not in _CACHE:
        _CACHE["lock"] = sb.generate(workdir / "requirements.txt", workdir / "sbom.json", kind="requirements")
    return _CACHE["lock"], workdir


def env_sbom(sb, workdir):
    if "env" not in _CACHE:
        _CACHE["env"] = sb.generate(sys.executable, workdir / "env.json", kind="environment")
    return _CACHE["env"], workdir


def test_requirements_sbom_is_cyclonedx_1_6(sb, workdir):
    sbom, folder = lock_sbom(sb, workdir)
    assert (folder / "sbom.json").is_file()
    assert sbom["bomFormat"] == "CycloneDX" and sbom["specVersion"] == "1.6"
    assert sbom["serialNumber"].startswith("urn:uuid:")


def test_requirements_sbom_lists_pinned_versions(sb, workdir):
    sbom, _ = lock_sbom(sb, workdir)
    assert sb.packages(sbom) == {
        "fastapi": "0.115.6",
        "uvicorn": "0.34.0",
        "numpy": "2.2.1",
        "scikit-learn": None,
        "safetensors": None,
    }
    purls = {c["name"].lower(): c.get("purl") for c in sbom["components"]}
    assert purls["fastapi"] == "pkg:pypi/fastapi@0.115.6"


def test_unpinned_requirements_are_reported(sb, workdir):
    assert sb.unpinned(lock_sbom(sb, workdir)[0]) == ["safetensors", "scikit-learn"]


def test_environment_sbom_matches_installed_versions(sb, workdir):
    sbom, _ = env_sbom(sb, workdir)
    found = sb.packages(sbom)
    assert sbom["specVersion"] == "1.6"
    assert len(found) >= 100
    for name in RUNTIME:
        assert found.get(name) == md.version(name), name
    assert sb.unpinned(sbom) == []


def test_check_environment_against_required_pins(sb, workdir):
    sbom, _ = env_sbom(sb, workdir)
    required = {name: md.version(name) for name in RUNTIME}
    assert sb.check(sbom, required) == []
    drifted = {**required, "numpy": "1.0.0", "Model_Signing": "0.0.1", "not-a-real-package": "1.0"}
    assert sb.check(sbom, drifted) == ["mismatch:model-signing", "mismatch:numpy", "missing:not-a-real-package"]


def test_check_flags_unpinned_lock(sb, workdir):
    sbom, _ = lock_sbom(sb, workdir)
    problems = sb.check(sbom, {"numpy": "2.2.1", "fastapi": "0.115.6"})
    assert problems == ["unpinned:safetensors", "unpinned:scikit-learn"]


def test_diff_between_two_releases(sb, workdir):
    old, folder = lock_sbom(sb, workdir)
    (folder / "requirements-v2.txt").write_text(SERVING_V2, encoding="utf-8")
    new = sb.generate(folder / "requirements-v2.txt", folder / "sbom-v2.json", kind="requirements")
    assert sb.diff(old, new) == {"added": ["pyarrow"], "removed": ["fastapi"], "changed": {"numpy": ["2.2.1", "2.3.0"]}}
    assert sb.diff(old, old) == {"added": [], "removed": [], "changed": {}}


def test_generate_rejects_unknown_kind(sb, tmp_path):
    with pytest.raises(ValueError):
        sb.generate(tmp_path / "x.txt", tmp_path / "x.json", kind="poetry")


def test_generate_failure_is_not_an_empty_sbom(sb, tmp_path):
    with pytest.raises(Exception):
        sb.generate(tmp_path / "missing-requirements.txt", tmp_path / "x.json", kind="requirements")

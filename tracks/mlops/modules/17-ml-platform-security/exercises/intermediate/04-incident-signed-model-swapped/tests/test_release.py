import filecmp
import importlib.util
import shutil
from pathlib import Path

import pytest
from model_signing import signing, verifying

import seckit
from testkit import Exercise

ex = Exercise(__file__)
FIXTURES = Path(__file__).parent / "fixtures"


def load(path):
    spec = importlib.util.spec_from_file_location(f"release_{path.parent.name}_{path.stem.replace('.', '_')}", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def release():
    return ex.module("release.py")


@pytest.fixture
def world(tmp_path):
    private, public = seckit.ec_keypair(tmp_path / "keys", "release")
    other_private, _ = seckit.ec_keypair(tmp_path / "keys", "other")
    registry = tmp_path / "registry"
    bundle = seckit.safetensors_model(registry / "pricing-tip-amount" / "7", seed=7)
    signature = registry / "pricing-tip-amount" / "7.sig"
    signing.Config().use_elliptic_key_signer(private_key=private).sign(bundle, signature)
    pristine = tmp_path / "pristine"
    shutil.copytree(bundle, pristine)
    return {"bundle": bundle, "signature": signature, "public": public, "other_private": other_private,
            "cache": tmp_path / "node" / "models", "pristine": pristine}


def verifies(folder, world):
    try:
        verifying.Config().use_elliptic_key_verifier(public_key=world["public"]).verify(folder, world["signature"])
    except Exception:
        return False
    return True


def same_tree(a, b):
    files_a = sorted(p.relative_to(a) for p in Path(a).rglob("*") if p.is_file())
    files_b = sorted(p.relative_to(b) for p in Path(b).rglob("*") if p.is_file())
    return files_a == files_b and all(filecmp.cmp(a / f, b / f, shallow=False) for f in files_a)


def flip_byte(folder):
    path = folder / "model.safetensors"
    data = bytearray(path.read_bytes())
    data[-3] ^= 0x10
    path.write_bytes(bytes(data))


SWAPS = {
    "weights-edited": flip_byte,
    "file-added": lambda f: (f / "extra.json").write_text("{}", encoding="utf-8"),
    "file-removed": lambda f: (f / "config.json").unlink(),
}


def stage(module, world):
    return Path(module.stage(world["bundle"], world["signature"], world["public"], world["cache"]))


def test_regression_original_reproduces_the_symptom(world):
    original = load(FIXTURES / "release.original.py")
    served = stage(original, world)
    flip_byte(served)
    again = stage(original, world)
    assert again == served
    assert verifies(world["bundle"], world)
    assert not verifies(again, world)


def test_first_release_on_a_node(release, world):
    served = stage(release, world)
    assert served.is_dir() and served.resolve().is_relative_to(world["cache"].resolve())
    assert served.resolve() != world["bundle"].resolve()
    assert verifies(served, world) and same_tree(served, world["pristine"])


def test_second_release_reuses_local_copy(release, world):
    served = stage(release, world)
    before = (served / "model.safetensors").stat()
    again = stage(release, world)
    after = (again / "model.safetensors").stat()
    assert again == served
    assert (before.st_ino, before.st_mtime_ns) == (after.st_ino, after.st_mtime_ns)


@pytest.mark.parametrize("case", list(SWAPS))
def test_second_release_matches_signed_content(release, world, case):
    served = stage(release, world)
    SWAPS[case](served)
    again = stage(release, world)
    ok = again.resolve().is_relative_to(world["cache"].resolve()) and verifies(again, world)
    assert ok and same_tree(again, world["pristine"]), f"ca {case}"


@pytest.mark.parametrize("case", list(SWAPS))
def test_changed_registry_bundle_is_rejected(release, world, case):
    SWAPS[case](world["bundle"])
    with pytest.raises(release.Rejected):
        stage(release, world)
    leftover = [p for p in world["cache"].glob("*")] if world["cache"].exists() else []
    assert leftover == [], f"ca {case}"


def test_warm_node_with_changed_registry_bundle(release, world):
    stage(release, world)
    flip_byte(world["bundle"])
    try:
        served = stage(release, world)
    except release.Rejected:
        return
    assert verifies(served, world) and same_tree(served, world["pristine"])


@pytest.mark.parametrize("content", [None, b"", b"{}", b"garbage"])
def test_bad_signature_is_rejected(release, world, content):
    if content is None:
        world["signature"].unlink()
    else:
        world["signature"].write_bytes(content)
    with pytest.raises(release.Rejected):
        stage(release, world)


def test_signature_from_another_key_is_rejected(release, world):
    signing.Config().use_elliptic_key_signer(private_key=world["other_private"]).sign(world["bundle"], world["signature"])
    with pytest.raises(release.Rejected):
        stage(release, world)

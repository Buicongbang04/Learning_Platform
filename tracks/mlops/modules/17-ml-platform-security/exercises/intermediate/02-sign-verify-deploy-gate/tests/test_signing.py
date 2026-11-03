import json
import subprocess

import pytest
from model_signing import verifying

import mlopskit
import seckit
from testkit import Exercise

ex = Exercise(__file__)


@pytest.fixture(scope="module")
def sig():
    return ex.module("signing.py")


@pytest.fixture
def lab(tmp_path):
    keys = tmp_path / "keys"
    private, public = seckit.ec_keypair(keys, "release")
    other_private, other_public = seckit.ec_keypair(keys, "intruder")
    model = seckit.safetensors_model(tmp_path / "model")
    signature = tmp_path / "out" / "model.sig"
    signature.parent.mkdir()
    marker = tmp_path / "marker" / "pwned.txt"
    marker.parent.mkdir()
    return {"private": private, "public": public, "other_private": other_private, "other_public": other_public,
            "model": model, "signature": signature, "marker": marker}


def fake_scan(returncode, body):
    calls = []

    def scan(path):
        calls.append(path)
        return subprocess.CompletedProcess(["modelscan"], returncode, body if isinstance(body, str) else json.dumps(body), "")

    scan.calls = calls
    return scan


CLEAN = {"summary": {"scanned": {"total_scanned": 0}}, "issues": [], "errors": []}


def test_signature_is_a_standard_model_signing_bundle(sig, lab):
    sig.sign(lab["model"], lab["private"], lab["signature"])
    bundle = json.loads(lab["signature"].read_text(encoding="utf-8"))
    assert "dsseEnvelope" in bundle
    verifying.Config().use_elliptic_key_verifier(public_key=lab["public"]).verify(lab["model"], lab["signature"])


def test_untouched_model_verifies_and_deploys(sig, lab):
    sig.sign(lab["model"], lab["private"], lab["signature"])
    assert sig.verify(lab["model"], lab["public"], lab["signature"]) is True
    decision = sig.deploy_gate(lab["model"], lab["signature"], lab["public"], mlopskit.modelscan_run)
    assert decision == {"allowed": True, "reasons": []}


def flip_byte(model):
    path = model / "model.safetensors"
    data = bytearray(path.read_bytes())
    data[-1] ^= 0x01
    path.write_bytes(bytes(data))


TAMPER = {
    "flip-one-weight-byte": flip_byte,
    "edit-config": lambda m: (m / "config.json").write_text('{"features": 10, "target": "fare"}\n', encoding="utf-8"),
    "add-file": lambda m: (m / "tokenizer.json").write_text("{}", encoding="utf-8"),
    "delete-file": lambda m: (m / "config.json").unlink(),
    "rename-file": lambda m: (m / "config.json").rename(m / "config.v2.json"),
}


@pytest.mark.parametrize("case", list(TAMPER))
def test_change_after_signing_is_blocked(sig, lab, case):
    sig.sign(lab["model"], lab["private"], lab["signature"])
    TAMPER[case](lab["model"])
    blocked = sig.verify(lab["model"], lab["public"], lab["signature"]) is False
    decision = sig.deploy_gate(lab["model"], lab["signature"], lab["public"], fake_scan(3, CLEAN))
    assert blocked and decision == {"allowed": False, "reasons": ["signature"]}, f"ca {case}"


def test_signed_with_another_key_is_blocked(sig, lab):
    sig.sign(lab["model"], lab["other_private"], lab["signature"])
    assert sig.verify(lab["model"], lab["public"], lab["signature"]) is False
    assert sig.verify(lab["model"], lab["other_public"], lab["signature"]) is True


@pytest.mark.parametrize("content", [None, b"", b"not a bundle", b'{"mediaType": "x"}'])
def test_bad_or_missing_signature_fails_closed(sig, lab, content):
    if content is not None:
        lab["signature"].write_bytes(content)
    assert sig.verify(lab["model"], lab["public"], lab["signature"]) is False
    decision = sig.deploy_gate(lab["model"], lab["signature"], lab["public"], fake_scan(3, CLEAN))
    assert decision == {"allowed": False, "reasons": ["signature"]}


def test_signature_inside_model_dir_is_refused(sig, lab):
    inside = lab["model"] / "model.sig"
    with pytest.raises(ValueError):
        sig.sign(lab["model"], lab["private"], inside)
    assert not inside.exists()


def test_signed_but_malicious_model_is_blocked_by_scan(sig, lab):
    (lab["model"] / "preprocess.pkl").write_bytes(seckit.marker_pickle(lab["marker"]))
    sig.sign(lab["model"], lab["private"], lab["signature"])
    assert sig.verify(lab["model"], lab["public"], lab["signature"]) is True
    decision = sig.deploy_gate(lab["model"], lab["signature"], lab["public"], mlopskit.modelscan_run)
    assert decision == {"allowed": False, "reasons": ["scan"]}
    assert not lab["marker"].exists()


def test_tampered_and_malicious_reports_both(sig, lab):
    sig.sign(lab["model"], lab["private"], lab["signature"])
    (lab["model"] / "preprocess.pkl").write_bytes(seckit.marker_pickle(lab["marker"]))
    decision = sig.deploy_gate(lab["model"], lab["signature"], lab["public"], mlopskit.modelscan_run)
    assert decision == {"allowed": False, "reasons": ["signature", "scan"]}
    assert not lab["marker"].exists()


SCAN_BAD = {
    "tool-error": (2, CLEAN),
    "unsupported": (4, CLEAN),
    "not-json": (0, "oops"),
    "parse-errors": (3, {**CLEAN, "errors": [{"category": "PICKLE_GENOPS", "description": "x", "source": "a"}]}),
    "issue": (1, {**CLEAN, "issues": [{"module": "builtins", "operator": "eval", "severity": "CRITICAL"}]}),
    "issue-code-without-list": (1, CLEAN),
}


@pytest.mark.parametrize("case", list(SCAN_BAD))
def test_scan_problem_blocks_signed_model(sig, lab, case):
    sig.sign(lab["model"], lab["private"], lab["signature"])
    scan = fake_scan(*SCAN_BAD[case])
    decision = sig.deploy_gate(lab["model"], lab["signature"], lab["public"], scan)
    assert decision == {"allowed": False, "reasons": ["scan"]}, f"ca {case}"
    assert len(scan.calls) == 1 and str(scan.calls[0]) == str(lab["model"])

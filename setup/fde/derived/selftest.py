"""Snapshot tự kiểm của fdekit (tests/test_fdekit.py::test_derived_boot_roundtrip): lab-open có /home/fde/marker."""

PROFILE = "lab-open"
INPUTS = ["selftest-v1"]
SITE = False
MEMORY_MB = 1024


def build(target):
    target.ssh("echo selftest > /home/fde/marker", check=True)

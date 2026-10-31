"""Test cho helper DevOps của testkit: phiên bản công cụ, docker, cpuset, cluster kind."""

import subprocess

import pytest

import testkit


def fake_run(outputs):
    def run(cmd, **kwargs):
        key = " ".join(cmd[1:])
        out = outputs.get(key)
        if out is None:
            raise AssertionError(f"lệnh không giả lập: {cmd}")
        code, stdout, stderr = out
        return subprocess.CompletedProcess(cmd, code, stdout, stderr)

    return run


def patch_tool(monkeypatch, outputs, present=True):
    monkeypatch.setattr(testkit.shutil, "which", lambda name: f"/usr/bin/{name}" if present else None)
    monkeypatch.setattr(testkit.subprocess, "run", fake_run(outputs))


@pytest.mark.parametrize(
    "text,expected",
    [
        ("nginx version: nginx/1.27.3", (1, 27, 3)),
        ("ShellCheck - shell script analysis tool\nversion: 0.10.0", (0, 10, 0)),
        ("Docker version 27.3.1, build ce12230", (27, 3, 1)),
        ("v0.13.2", (0, 13, 2)),
        ("OpenTofu v1.13.2\non linux_amd64", (1, 13, 2)),
        ("no version here", None),
    ],
)
def test_parse_version(text, expected):
    assert testkit.parse_version(text) == expected


def test_tool_version_reads_nginx_stderr(monkeypatch):
    patch_tool(monkeypatch, {"-v": (0, "", "nginx version: nginx/1.27.3")})
    assert testkit.tool_version("nginx") == (1, 27, 3)


def test_tool_version_missing_binary(monkeypatch):
    patch_tool(monkeypatch, {}, present=False)
    assert testkit.tool_version("helm") is None


def test_require_tool_missing_skips(monkeypatch):
    patch_tool(monkeypatch, {}, present=False)
    with pytest.raises(pytest.skip.Exception) as info:
        testkit.Exercise.require_tool("shellcheck")
    assert "setup/DEVOPS-TOOLS.md" in str(info.value)
    assert "shellcheck" in str(info.value)


def test_require_tool_too_old_skips(monkeypatch):
    patch_tool(monkeypatch, {"--version": (0, "version: 0.9.0", "")})
    with pytest.raises(pytest.skip.Exception) as info:
        testkit.Exercise.require_tool("shellcheck", "0.10")
    assert "0.10" in str(info.value)
    assert "0.9.0" in str(info.value)


def test_require_tool_ok(monkeypatch):
    patch_tool(monkeypatch, {"--version": (0, "version: 0.10.0", "")})
    testkit.Exercise.require_tool("shellcheck", "0.10")


def test_require_docker_daemon_down_skips(monkeypatch):
    patch_tool(
        monkeypatch,
        {"--version": (0, "Docker version 27.3.1, build x", ""), "info": (1, "", "permission denied")},
    )
    with pytest.raises(pytest.skip.Exception) as info:
        testkit.Exercise.require_tool("docker")
    assert "daemon" in str(info.value)


def test_require_docker_ok(monkeypatch):
    patch_tool(
        monkeypatch,
        {"--version": (0, "Docker version 27.3.1, build x", ""), "info": (0, "", "")},
    )
    testkit.Exercise.require_tool("docker", "24")


def test_cpu_args_env(monkeypatch):
    monkeypatch.setenv("DEVOPS_CPUSET", "0-3")
    assert testkit.docker_cpu_args() == ["--cpuset-cpus", "0-3"]
    monkeypatch.setenv("DEVOPS_CPUSET", "none")
    assert testkit.docker_cpu_args() == []


def test_cpu_args_small_machine(monkeypatch):
    monkeypatch.delenv("DEVOPS_CPUSET", raising=False)
    monkeypatch.setattr(testkit.os, "cpu_count", lambda: 8)
    assert testkit.docker_cpu_args() == []


def test_cpu_args_big_machine(monkeypatch):
    monkeypatch.delenv("DEVOPS_CPUSET", raising=False)
    monkeypatch.setattr(testkit.os, "cpu_count", lambda: 36)
    assert testkit.docker_cpu_args() == ["--cpuset-cpus", "12-35"]


def test_require_cluster_absent_skips(monkeypatch):
    patch_tool(
        monkeypatch,
        {"version": (0, "kind v0.24.0 go1.22 linux/amd64", ""), "get clusters": (0, "other\n", "")},
    )
    with pytest.raises(pytest.skip.Exception) as info:
        testkit.Exercise.require_cluster()
    assert "devops-lab" in str(info.value)


def test_require_cluster_present(monkeypatch):
    patch_tool(
        monkeypatch,
        {"version": (0, "kind v0.24.0", ""), "get clusters": (0, "devops-lab\n", "")},
    )
    testkit.Exercise.require_cluster()

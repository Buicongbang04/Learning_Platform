"""Test cho helper DevOps của testkit: phiên bản công cụ, docker, cpuset, cluster kind."""

import os
import subprocess
import sys

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


SANDBOX_REQUIRED = pytest.mark.skipif(testkit.sandbox_ready() is not None, reason="Máy này không có bwrap dùng được")


@pytest.fixture
def sentinel(tmp_path):
    outside = tmp_path / "outside"
    outside.mkdir()
    target = outside / "sentinel.txt"
    target.write_text("giữ")
    inside = tmp_path / "inside"
    inside.mkdir()
    return inside, target


@SANDBOX_REQUIRED
def test_sandbox_path_reset_cannot_delete_outside(sentinel):
    inside, target = sentinel
    script = f'PATH=/usr/bin:/bin; rm -rf "$HOME_OUTSIDE"; rm -f "{target}"; exit 0'
    result = testkit.run_sandboxed(["bash", "-c", script], writable=[inside], cwd=inside, env={"HOME_OUTSIDE": str(target.parent)})
    assert result.returncode == 0, result.stderr
    assert target.read_text() == "giữ"


@SANDBOX_REQUIRED
@pytest.mark.parametrize(
    "cmd",
    [
        ["env", "-i", "/bin/rm", "-f", "{t}"],
        ["{py}", "-c", "import os, sys; os.remove(sys.argv[1])", "{t}"],
        ["bash", "-c", ': > "$1"', "_", "{t}"],
    ],
)
def test_sandbox_blocks_other_deleters(sentinel, cmd):
    inside, target = sentinel
    argv = [c.format(t=target, py=sys.executable) for c in cmd]
    testkit.run_sandboxed(argv, writable=[inside], cwd=inside, env={})
    assert target.read_text() == "giữ"


@SANDBOX_REQUIRED
def test_sandbox_visible_paths_are_read_only(tmp_path):
    probe = testkit.ROOT / f".sandbox-probe-{os.getpid()}"
    try:
        result = testkit.run_sandboxed(["bash", "-c", f'touch "{probe}"'], writable=[tmp_path], cwd=tmp_path, env={})
        assert result.returncode != 0
        assert not probe.exists()
    finally:
        probe.unlink(missing_ok=True)


@SANDBOX_REQUIRED
def test_sandbox_writable_dir_under_tmp_is_writable(tmp_path):
    result = testkit.run_sandboxed(
        ["bash", "-c", 'echo ok > made.txt && mkdir -p sub && rm -f old.txt && pwd && echo "$HOME"'],
        writable=[tmp_path],
        cwd=tmp_path,
        env={},
    )
    assert result.returncode == 0, result.stderr
    assert (tmp_path / "made.txt").read_text() == "ok\n"
    assert (tmp_path / "sub").is_dir()
    assert result.stdout.split() == [str(tmp_path.resolve()), str(tmp_path.resolve())]


@SANDBOX_REQUIRED
def test_sandbox_hides_real_tmp(tmp_path):
    result = testkit.run_sandboxed(["bash", "-c", "ls -A /tmp"], writable=[tmp_path], cwd=tmp_path, env={})
    assert result.returncode == 0, result.stderr
    first = tmp_path.resolve().relative_to("/tmp").parts[0] if tmp_path.resolve().is_relative_to("/tmp") else None
    assert result.stdout.split() == ([first] if first else [])


@SANDBOX_REQUIRED
def test_sandbox_drops_bash_env_and_exported_functions(tmp_path, monkeypatch):
    marker = tmp_path / "bash_env_ran"
    hook = tmp_path / "hook.sh"
    hook.write_text(f'touch "{marker}"\n')
    monkeypatch.setenv("BASH_ENV", str(hook))
    monkeypatch.setenv("ENV", str(hook))
    monkeypatch.setenv("BASH_FUNC_x%%", "() { echo leaked; }")
    monkeypatch.setenv("BASH_FUNC_rm%%", "() { echo leaked-rm; }")
    result = testkit.run_sandboxed(
        ["bash", "-c", 'type x >/dev/null 2>&1 && echo leaked; type -t rm; echo "env=${BASH_ENV:-}"'],
        writable=[tmp_path],
        cwd=tmp_path,
        env=dict(os.environ),
    )
    assert result.returncode == 0, result.stderr
    assert "leaked" not in result.stdout
    assert result.stdout.split() == ["file", "env="]
    assert not marker.exists()


def test_sandbox_skips_without_bwrap(monkeypatch, tmp_path):
    monkeypatch.setattr(testkit.shutil, "which", lambda name: None)
    with pytest.raises(pytest.skip.Exception, match="bubblewrap"):
        testkit.run_sandboxed(["true"], writable=[tmp_path], cwd=tmp_path, env={})


def test_sandbox_skips_when_probe_fails(monkeypatch, tmp_path):
    monkeypatch.setattr(testkit.shutil, "which", lambda name: "/usr/bin/bwrap")
    monkeypatch.setattr(testkit.subprocess, "run", lambda cmd, **kw: subprocess.CompletedProcess(cmd, 1, "", "setting up uid map: Permission denied"))
    with pytest.raises(pytest.skip.Exception, match="user namespace"):
        testkit.run_sandboxed(["true"], writable=[tmp_path], cwd=tmp_path, env={})

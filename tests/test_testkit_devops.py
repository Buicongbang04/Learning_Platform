"""Test cho helper DevOps của testkit: phiên bản công cụ, docker, cpuset, cluster kind."""

import os
import shutil
import subprocess
import sys
from pathlib import Path

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
        ("OpenSSL 3.0.13 30 Jan 2024 (Library: OpenSSL 3.0.13 30 Jan 2024)", (3, 0, 13)),
        ("OpenSSL 1.1.1w  11 Sep 2023", (1, 1, 1)),
        ("DiG 9.18.30-0ubuntu0.24.04.2-Ubuntu", (9, 18, 30)),
        ("OpenSSH_9.6p1 Ubuntu-3ubuntu13.20, OpenSSL 3.0.13 30 Jan 2024", (9, 6)),
        ("no version here", None),
    ],
)
def test_parse_version(text, expected):
    assert testkit.parse_version(text) == expected


def test_tool_version_reads_nginx_stderr(monkeypatch):
    patch_tool(monkeypatch, {"-v": (0, "", "nginx version: nginx/1.27.3")})
    assert testkit.tool_version("nginx") == (1, 27, 3)


@pytest.mark.parametrize(
    "name,args,stdout,stderr,expected",
    [
        ("openssl", "version", "OpenSSL 3.0.13 30 Jan 2024 (Library: OpenSSL 3.0.13 30 Jan 2024)\n", "", (3, 0, 13)),
        ("dig", "-v", "", "DiG 9.18.30-0ubuntu0.24.04.2-Ubuntu\n", (9, 18, 30)),
        ("ssh", "-V", "", "OpenSSH_9.6p1 Ubuntu-3ubuntu13.20, OpenSSL 3.0.13 30 Jan 2024\n", (9, 6)),
    ],
)
def test_tool_version_networking_tools(monkeypatch, name, args, stdout, stderr, expected):
    patch_tool(monkeypatch, {args: (0, stdout, stderr)})
    assert testkit.tool_version(name) == expected


def test_require_openssl_1_1_1_accepts_3_0(monkeypatch):
    patch_tool(monkeypatch, {"version": (0, "OpenSSL 3.0.13 30 Jan 2024 (Library: OpenSSL 3.0.13 30 Jan 2024)", "")})
    testkit.Exercise.require_tool("openssl", "1.1.1")


def test_require_openssl_too_old_skips(monkeypatch):
    patch_tool(monkeypatch, {"version": (0, "OpenSSL 1.0.2k-fips  26 Jan 2017", "")})
    with pytest.raises(pytest.skip.Exception) as info:
        testkit.Exercise.require_tool("openssl", "1.1.1")
    assert "1.0.2" in str(info.value)


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
    """Tệp canh nằm ngoài /tmp (dưới gốc repo) nên NHÌN THẤY được trong sandbox, chỉ là không ghi được."""
    outside = testkit.ROOT / f".sandbox-sentinel-{os.getpid()}"
    outside.mkdir()
    target = outside / "sentinel.txt"
    target.write_text("giữ")
    inside = tmp_path / "inside"
    inside.mkdir()
    try:
        yield inside, target
    finally:
        shutil.rmtree(outside, ignore_errors=True)


def assert_visible(inside, target):
    seen = testkit.run_sandboxed(["cat", target], writable=[inside], cwd=inside, env={})
    assert seen.stdout == "giữ", "Tệp canh phải nhìn thấy được trong sandbox để phép thử có nghĩa"


@SANDBOX_REQUIRED
def test_sandbox_path_reset_cannot_delete_visible_file(sentinel):
    inside, target = sentinel
    assert_visible(inside, target)
    script = 'PATH=/usr/bin:/bin; rm -rf "$HOME_OUTSIDE"; rm -f "$TARGET"; exit 0'
    result = testkit.run_sandboxed(
        ["bash", "-c", script], writable=[inside], cwd=inside, env={"HOME_OUTSIDE": str(target.parent), "TARGET": str(target)}
    )
    assert result.returncode == 0, result.stderr
    assert "Read-only file system" in result.stderr
    assert target.read_text() == "giữ"


@SANDBOX_REQUIRED
@pytest.mark.parametrize(
    "cmd",
    [
        ["env", "-i", "/bin/rm", "-rf", "{d}"],
        ["{py}", "-c", "import os, sys; os.remove(sys.argv[1])", "{t}"],
        ["{py}", "-c", "import shutil, sys; shutil.rmtree(sys.argv[1])", "{d}"],
        ["bash", "-c", ': > "$1"', "_", "{t}"],
        ["bash", "-c", 'mv "$1" "$1.bak"', "_", "{t}"],
    ],
)
def test_sandbox_blocks_other_deleters_on_visible_file(sentinel, cmd):
    inside, target = sentinel
    assert_visible(inside, target)
    argv = [c.format(t=target, d=target.parent, py=sys.executable) for c in cmd]
    result = testkit.run_sandboxed(argv, writable=[inside], cwd=inside, env={})
    assert result.returncode != 0
    assert target.read_text() == "giữ"


@SANDBOX_REQUIRED
def test_sandbox_hides_host_daemon_sockets(tmp_path):
    uid = os.getuid()
    script = (
        f'for p in /run/docker.sock /var/run/docker.sock /run/user/{uid}/bus /run/user/{uid}/docker.sock /run/dbus/system_bus_socket; '
        'do [ -e "$p" ] && echo "visible $p"; done; ls -A "$REAL_HOME/.docker" 2>/dev/null; exit 0'
    )
    result = testkit.run_sandboxed(["bash", "-c", script], writable=[tmp_path], cwd=tmp_path, env={"REAL_HOME": str(Path.home())})
    assert result.returncode == 0, result.stderr
    assert result.stdout == ""
    if shutil.which("docker"):
        docker = testkit.run_sandboxed(["docker", "version", "--format", "{{.Server.Version}}"], writable=[tmp_path], cwd=tmp_path, env={})
        assert docker.returncode != 0, docker.stdout
        assert docker.stdout.strip() == ""


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


UNSAFE_VARS = {
    "BASH_ENV": "{hook}",
    "ENV": "{hook}",
    "BASH_FUNC_x%%": "() { echo leaked; }",
    "BASH_FUNC_rm%%": "() { echo leaked-rm; }",
    "LD_PRELOAD": "/nonexistent/libleak.so",
    "LD_LIBRARY_PATH": "/nonexistent",
    "SHELLOPTS": "xtrace",
    "BASHOPTS": "extglob",
    "PROMPT_COMMAND": "echo leaked",
    "PS4": "+leaked ",
}


@SANDBOX_REQUIRED
def test_sandbox_drops_dangerous_env(tmp_path):
    marker = tmp_path / "bash_env_ran"
    hook = tmp_path / "hook.sh"
    hook.write_text(f'touch "{marker}"\n')
    parent = dict(os.environ)
    parent.update({k: v.replace("{hook}", str(hook)) for k, v in UNSAFE_VARS.items()})
    result = testkit.run_sandboxed(
        ["bash", "-c", 'type x >/dev/null 2>&1 && echo leaked; type -t rm; env | cut -d= -f1'],
        writable=[tmp_path],
        cwd=tmp_path,
        env=parent,
    )
    assert result.returncode == 0, result.stderr
    assert "leaked" not in result.stdout + result.stderr
    lines = result.stdout.split()
    assert lines[0] == "file"
    assert not set(lines[1:]) & set(UNSAFE_VARS), lines
    assert not marker.exists()


def test_unsafe_env_filter_unit():
    cleaned = testkit._clean_env({**UNSAFE_VARS, "KEEP_ME": "1"}, Path("/x"))
    assert not set(cleaned) & set(UNSAFE_VARS)
    assert cleaned["KEEP_ME"] == "1"


def test_probe_uses_same_flags_as_run(monkeypatch, tmp_path):
    calls = []
    monkeypatch.setattr(testkit.shutil, "which", lambda name: "/usr/bin/bwrap")
    monkeypatch.setattr(testkit.subprocess, "run", lambda cmd, **kw: calls.append(cmd) or subprocess.CompletedProcess(cmd, 0, "", ""))
    argv = testkit.sandbox_command(["true"], writable=[tmp_path], cwd=tmp_path, env={})
    probe = calls[0]
    for flag in ("--dev", "--proc", "--clearenv", "--unshare-user", "--unshare-pid", "--new-session"):
        assert flag in probe and flag in argv, flag
    for mount in ("/tmp", "/run"):
        assert ["--tmpfs", mount] in [probe[i : i + 2] for i in range(len(probe))]
        assert ["--tmpfs", mount] in [argv[i : i + 2] for i in range(len(argv))]


def test_sandbox_skips_without_bwrap(monkeypatch, tmp_path):
    monkeypatch.setattr(testkit.shutil, "which", lambda name: None)
    with pytest.raises(pytest.skip.Exception, match="bubblewrap"):
        testkit.run_sandboxed(["true"], writable=[tmp_path], cwd=tmp_path, env={})


def test_sandbox_skips_when_probe_fails(monkeypatch, tmp_path):
    monkeypatch.setattr(testkit.shutil, "which", lambda name: "/usr/bin/bwrap")
    monkeypatch.setattr(testkit.subprocess, "run", lambda cmd, **kw: subprocess.CompletedProcess(cmd, 1, "", "setting up uid map: Permission denied"))
    with pytest.raises(pytest.skip.Exception, match="user namespace"):
        testkit.run_sandboxed(["true"], writable=[tmp_path], cwd=tmp_path, env={})


class FakeDocker:
    def __init__(self, fail_run: bool = False):
        self.calls: list[list[str]] = []
        self.fail_run = fail_run

    def __call__(self, cmd, **kwargs):
        self.calls.append(list(cmd))
        failed = self.fail_run and cmd[1] == "run"
        return subprocess.CompletedProcess(cmd, 1 if failed else 0, "", "boom" if failed else "")


def test_docker_lab_run_args(monkeypatch, tmp_path):
    monkeypatch.setenv("DEVOPS_CPUSET", "2-3")
    lab = testkit.DockerLab()
    args = lab.run_args("nginx", "nginx:1.30.6-alpine", "-g", "daemon off;", mounts=[(tmp_path / "a.conf", "/etc/nginx/nginx.conf")],
                        publish=[(80, 41234)], env={"INSTANCE": "a"}, entrypoint="nginx")
    assert args[:4] == ["docker", "run", "--rm", "-d"]
    assert args[args.index("--name") + 1] == f"devops-ex-{lab.id}-nginx"
    assert args[args.index("--label") + 1] == "devops-ex=1"
    assert args[args.index("--network") + 1] == lab.network and lab.network.startswith("devops-ex-")
    assert args[args.index("--cpuset-cpus") + 1] == "2-3"
    assert args[args.index("--memory") + 1] == "256m"
    assert args[args.index("--pids-limit") + 1] == "256"
    custom = lab.run_args("big", "x:1", memory="1g", pids_limit=1024)
    assert custom[custom.index("--memory") + 1] == "1g" and custom[custom.index("--pids-limit") + 1] == "1024"
    assert args[args.index("-v") + 1] == f"{(tmp_path / 'a.conf').resolve()}:/etc/nginx/nginx.conf:ro"
    assert args[args.index("-p") + 1] == "127.0.0.1:41234:80"
    assert args[args.index("--entrypoint") + 1] == "nginx"
    assert args[-3:] == ["nginx:1.30.6-alpine", "-g", "daemon off;"]
    once = lab.run_args("check", "nginx:1.30.6-alpine", "-t", detach=False)
    assert "-d" not in once and "--rm" in once


def test_docker_lab_names_are_unique():
    assert testkit.DockerLab().id != testkit.DockerLab().id


def test_docker_lab_cleans_up_even_when_run_fails(monkeypatch):
    fake = FakeDocker(fail_run=True)
    monkeypatch.setattr(testkit.subprocess, "run", fake)
    lab = testkit.DockerLab()
    with pytest.raises(pytest.fail.Exception):
        with lab:
            lab.start("api", "python:3.12.16-alpine3.24", ports=[8000])
    removed = [c for c in fake.calls if c[1:3] == ["rm", "-f"]]
    assert [f"devops-ex-{lab.id}-api"] in [c[3:] for c in removed]
    assert fake.calls[-1] == ["docker", "network", "rm", lab.network]
    assert all(c[1] != "rm" or c[3].startswith(f"devops-ex-{lab.id}") for c in fake.calls if c[1] == "rm")


def test_docker_lab_publishes_on_loopback_free_port(monkeypatch):
    fake = FakeDocker()
    monkeypatch.setattr(testkit.subprocess, "run", fake)
    with testkit.DockerLab() as lab:
        lab.start("web", "nginx:1.30.6-alpine", ports=[80, 443])
        run = next(c for c in fake.calls if c[1] == "run")
        published = [run[i + 1] for i, a in enumerate(run) if a == "-p"]
        assert published == [f"127.0.0.1:{lab.port('web', 80)}:80", f"127.0.0.1:{lab.port('web', 443)}:443"]
        assert lab.port("web", 80) != lab.port("web", 443)


def test_require_image_missing_skips(monkeypatch):
    patch_tool(monkeypatch, {"info": (0, "", ""), "image inspect nginx:1.30.6-alpine": (1, "", "No such image")})
    with pytest.raises(pytest.skip.Exception) as info:
        testkit.Exercise.require_image("nginx:1.30.6-alpine")
    assert "docker pull nginx:1.30.6-alpine" in str(info.value)


def test_docker_lab_refuses_start_outside_with(monkeypatch):
    fake = FakeDocker()
    monkeypatch.setattr(testkit.subprocess, "run", fake)
    lab = testkit.DockerLab()
    with pytest.raises(RuntimeError):
        lab.start("api", "python:3.12.16-alpine3.24")
    with pytest.raises(RuntimeError):
        lab.run_once("check", "nginx:1.30.6-alpine", "-t")
    assert fake.calls == []


def test_docker_lab_enter_cleans_up_when_network_fails(monkeypatch):
    calls = []

    def run(cmd, **kwargs):
        calls.append(list(cmd))
        return subprocess.CompletedProcess(cmd, 1 if cmd[1:3] == ["network", "create"] else 0, "", "boom")

    monkeypatch.setattr(testkit.subprocess, "run", run)
    lab = testkit.DockerLab()
    with pytest.raises(pytest.fail.Exception):
        with lab:
            pass
    assert calls[-1] == ["docker", "network", "rm", lab.network]


def test_docker_lab_real_cleanup_after_error_inside_with():
    if not shutil.which("docker") or not testkit.docker_ready():
        pytest.skip("Cần Docker daemon")
    image = "python:3.12.16-alpine3.24"
    if testkit._docker("image", "inspect", image).returncode != 0:
        pytest.skip(f"Chưa có image {image}")
    lab = testkit.DockerLab()
    with pytest.raises(RuntimeError):
        with lab:
            lab.start("sleeper", image, "sleep", "300")
            assert testkit.docker_leftovers(lab.id)
            raise RuntimeError("lỗi giữa chừng")
    assert testkit.docker_leftovers(lab.id) == []

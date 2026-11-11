"""Test cho helper DevOps của testkit: phiên bản công cụ, docker, cpuset, cluster kind."""

import base64
import json
import os
import pwd
import re
import shutil
import socket
import subprocess
import sys
import time
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
    assert cleaned["KEEP_ME"] == "1" and cleaned["PYTHONNOUSERSITE"] == "1"


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
    assert args[:3] == ["docker", "run", "-d"]
    assert "--rm" not in args, "Container nền không dùng --rm để còn đọc được log khi chết; close() xoá nó"
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
    removed = [c for c in fake.calls if c[1:4] == ["rm", "-f", "-v"]]
    assert [f"devops-ex-{lab.id}-api"] in [c[4:] for c in removed]
    assert fake.calls[-1] == ["docker", "network", "rm", lab.network]
    assert all(c[-1].startswith(f"devops-ex-{lab.id}") for c in fake.calls if c[1] == "rm")


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


def test_act_run_skips_with_build_command_when_runner_missing(monkeypatch, tmp_path):
    monkeypatch.setattr(testkit.Exercise, "require_tool", staticmethod(lambda name, v=None: None))
    monkeypatch.setattr(testkit, "_docker", lambda *args, timeout=60: subprocess.CompletedProcess(args, 1, "", "No such image"))
    project = tmp_path / "p"
    (project / ".github" / "workflows").mkdir(parents=True)
    (project / ".github" / "workflows" / "ci.yml").write_text("name: ci\non: push\njobs: {}\n", encoding="utf-8")
    with pytest.raises(pytest.skip.Exception) as info:
        testkit.act_run(project)
    assert testkit.ACT_IMAGE_BUILD in str(info.value) and "setup/act-runner" in str(info.value)
    assert "docker pull devops-track" not in str(info.value)


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


@pytest.fixture(autouse=True)
def fresh_sandbox_probe():
    testkit._SANDBOX_OK.clear()
    yield
    testkit._SANDBOX_OK.clear()


@pytest.mark.parametrize(
    "have,need,expected",
    [
        ((1, 27), (1, 27, 0), True),
        ((1, 27, 0), (1, 27), True),
        ((1, 27, 1), (1, 27), True),
        ((1, 26, 9), (1, 27), False),
        ((1, 27), (1, 27, 1), False),
        ((2,), (1, 99, 99), True),
    ],
)
def test_version_padding(have, need, expected):
    assert testkit.version_at_least(have, need) is expected


@pytest.mark.parametrize("output,need", [("kubectl v1.27", "1.27.0"), ("Client Version: v1.27.0", "1.27")])
def test_require_tool_pads_versions(monkeypatch, output, need):
    patch_tool(monkeypatch, {"--version": (0, output, "")})
    try:
        testkit.Exercise.require_tool("shellcheck", need)
    except pytest.skip.Exception as skipped:
        pytest.fail(f"{output} phải đạt mức {need}: {skipped}")


def test_unreadable_version_message(monkeypatch):
    patch_tool(monkeypatch, {"--version": (0, "build abc, không có số phiên bản", "")})
    with pytest.raises(pytest.skip.Exception) as info:
        testkit.Exercise.require_tool("shellcheck", "0.10")
    message = str(info.value)
    assert "Không đọc được phiên bản" in message
    assert "shellcheck --version" in message
    assert "cũ hơn" not in message


def test_real_homes_without_passwd(monkeypatch, tmp_path):
    def missing(uid):
        raise KeyError(f"getpwuid(): uid not found: {uid}")

    monkeypatch.setattr(pwd, "getpwuid", missing)
    monkeypatch.setenv("HOME", str(tmp_path))
    assert testkit._real_homes() == [tmp_path.resolve()]
    assert "pwd" not in vars(testkit), "import pwd phải nằm trong hàm để testkit import được khi không có module pwd"


def test_sandbox_ready_is_cached(monkeypatch):
    calls = []
    monkeypatch.setattr(testkit.shutil, "which", lambda name: "/usr/bin/bwrap")
    monkeypatch.setattr(testkit.subprocess, "run", lambda cmd, **kw: calls.append(cmd) or subprocess.CompletedProcess(cmd, 0, "", ""))
    assert testkit.sandbox_ready() is None
    assert testkit.sandbox_ready() is None
    assert len(calls) == 1


def test_sandbox_ready_retries_after_transient_failure(monkeypatch):
    outcomes = [subprocess.TimeoutExpired("bwrap", 10), subprocess.CompletedProcess("bwrap", 1, "", "lỗi tạm"), None]
    calls = []

    def run(cmd, **kw):
        calls.append(cmd)
        outcome = outcomes[len(calls) - 1]
        if isinstance(outcome, BaseException):
            raise outcome
        return outcome or subprocess.CompletedProcess(cmd, 0, "", "")

    monkeypatch.setattr(testkit.shutil, "which", lambda name: "/usr/bin/bwrap")
    monkeypatch.setattr(testkit.subprocess, "run", run)
    assert testkit.sandbox_ready() is not None
    assert "lỗi tạm" in testkit.sandbox_ready()
    assert testkit.sandbox_ready() is None
    assert testkit.sandbox_ready() is None
    assert len(calls) == 3, "Chỉ cache lần thử thành công"


CREDENTIAL_DIRS = (".docker", ".kube", ".aws", ".ssh", ".config/gcloud", ".azure", ".config/gh", ".terraform.d", ".config/sops",
                   ".gnupg")
CREDENTIAL_FILES = (".git-credentials", ".netrc", ".vault-token")


@pytest.fixture
def fake_home():
    """Home giả ngoài /tmp (dưới gốc repo) có đủ thư mục và tệp thông tin đăng nhập."""
    home = testkit.ROOT / f".sandbox-home-{os.getpid()}"
    for rel in CREDENTIAL_DIRS:
        (home / rel).mkdir(parents=True)
        (home / rel / "secret").write_text(f"bí mật {rel}")
    for rel in CREDENTIAL_FILES:
        (home / rel).write_text(f"bí mật {rel}")
    (home / "visible.txt").write_text("thấy")
    try:
        yield home
    finally:
        shutil.rmtree(home, ignore_errors=True)


@pytest.fixture
def outside_tmp():
    """Thư mục ngoài /tmp (dưới ~/.cache) làm đích cho symlink tuyệt đối, như ~/.kube -> /mnt/c/... trên WSL."""
    base = Path.home() / ".cache" / f"devops-sandbox-test-{os.getpid()}"
    base.mkdir(parents=True)
    try:
        yield base.resolve()
    finally:
        shutil.rmtree(base, ignore_errors=True)


def flag_targets(argv, flag):
    if flag == "--tmpfs":
        return {argv[i + 1] for i, a in enumerate(argv) if a == flag}
    return {argv[i + 2] for i, a in enumerate(argv) if a == "--ro-bind" and argv[i + 1] == "/dev/null"}


def test_sandbox_hides_cloud_credentials_flags(monkeypatch, fake_home, tmp_path):
    under_tmp = tmp_path / "home-in-tmp"
    (under_tmp / ".kube").mkdir(parents=True)
    partial = testkit.ROOT / f".sandbox-partial-{os.getpid()}"
    (partial / ".aws").mkdir(parents=True)
    try:
        monkeypatch.setattr(testkit, "_real_homes", lambda: [fake_home, under_tmp, partial])
        argv = testkit._base_flags("/usr/bin/bwrap")
        tmpfs = flag_targets(argv, "--tmpfs")
        assert {str(fake_home / rel) for rel in CREDENTIAL_DIRS} <= tmpfs
        assert {str(fake_home / rel) for rel in CREDENTIAL_FILES} <= flag_targets(argv, "--ro-bind")
        assert str(partial / ".aws") in tmpfs
        assert not any(t.startswith(str(partial / ".kube")) or t.startswith(str(under_tmp)) for t in tmpfs), tmpfs
    finally:
        shutil.rmtree(partial, ignore_errors=True)


def test_sandbox_credential_symlinks_mount_resolved_target(monkeypatch, fake_home, outside_tmp, tmp_path):
    (outside_tmp / "kube").mkdir()
    (outside_tmp / "netrc").write_text("x")
    shutil.rmtree(fake_home / ".kube")
    (fake_home / ".kube").symlink_to(outside_tmp / "kube")
    shutil.rmtree(fake_home / ".aws")
    (fake_home / "stash" / "aws").mkdir(parents=True)
    (fake_home / ".aws").symlink_to(Path("stash") / "aws")
    (fake_home / ".netrc").unlink()
    (fake_home / ".netrc").symlink_to(outside_tmp / "netrc")
    shutil.rmtree(fake_home / ".ssh")
    (tmp_path / "ssh").mkdir()
    (fake_home / ".ssh").symlink_to(tmp_path / "ssh")
    shutil.rmtree(fake_home / ".azure")
    (fake_home / ".azure").symlink_to(outside_tmp / "khong-ton-tai")
    monkeypatch.setattr(testkit, "_real_homes", lambda: [fake_home])
    argv = testkit._base_flags("/usr/bin/bwrap")
    tmpfs = flag_targets(argv, "--tmpfs")
    assert str(outside_tmp / "kube") in tmpfs and str(fake_home / ".kube") not in tmpfs
    assert str(fake_home / "stash" / "aws") in tmpfs and str(fake_home / ".aws") not in tmpfs
    assert str(outside_tmp / "netrc") in flag_targets(argv, "--ro-bind")
    assert not any("ssh" in t for t in tmpfs), "Đích dưới /tmp đã bị che sẵn"
    assert not any("azure" in t or "khong-ton-tai" in t for t in tmpfs), "Symlink hỏng thì bỏ qua"


@SANDBOX_REQUIRED
def test_sandbox_hides_cloud_credentials(monkeypatch, fake_home, outside_tmp, tmp_path):
    (outside_tmp / "kube").mkdir()
    (outside_tmp / "kube" / "secret").write_text("bí mật .kube")
    shutil.rmtree(fake_home / ".kube")
    (fake_home / ".kube").symlink_to(outside_tmp / "kube")
    shutil.rmtree(fake_home / ".aws")
    (fake_home / "stash" / "aws").mkdir(parents=True)
    (fake_home / "stash" / "aws" / "secret").write_text("bí mật .aws")
    (fake_home / ".aws").symlink_to(Path("stash") / "aws")
    monkeypatch.setattr(testkit, "_real_homes", lambda: [fake_home])
    assert testkit.sandbox_ready() is None, "Symlink tuyệt đối không được làm hỏng sandbox"
    paths = [f"{rel}/secret" for rel in CREDENTIAL_DIRS] + list(CREDENTIAL_FILES)
    script = 'cat "$H/visible.txt"; for f in ' + " ".join(paths) + '; do cat "$H/$f" 2>/dev/null | grep -q . && echo " lộ $f"; done; exit 0'
    result = testkit.run_sandboxed(["bash", "-c", script], writable=[tmp_path], cwd=tmp_path, env={"H": str(fake_home)})
    assert result.returncode == 0, result.stderr
    assert result.stdout == "thấy", result.stdout
    assert (outside_tmp / "kube" / "secret").read_text() == "bí mật .kube"
    for rel in CREDENTIAL_FILES:
        assert (fake_home / rel).read_text() == f"bí mật {rel}"


def test_docker_lab_no_new_privileges(monkeypatch):
    lab = testkit.DockerLab()
    for args in (lab.run_args("web", "x:1"), lab.run_args("check", "x:1", detach=False)):
        pairs = [args[i : i + 2] for i in range(len(args))]
        assert ["--security-opt", "no-new-privileges"] in pairs, args


def test_docker_lab_run_once_limits(monkeypatch):
    fake = FakeDocker()
    monkeypatch.setattr(testkit.subprocess, "run", fake)
    with testkit.DockerLab() as lab:
        lab.run_once("check", "python:3.12.16-alpine3.24", "true", memory="64m", pids_limit=32)
    run = next(c for c in fake.calls if c[1] == "run")
    assert run[run.index("--memory") + 1] == "64m"
    assert run[run.index("--pids-limit") + 1] == "32"
    assert "--rm" in run and "-d" not in run


def test_docker_lab_close_removes_every_container(monkeypatch):
    fake = FakeDocker()
    monkeypatch.setattr(testkit.subprocess, "run", fake)
    with pytest.raises(KeyboardInterrupt):
        with testkit.DockerLab() as lab:
            lab.start("a", "x:1")
            lab.start("b", "x:1")
            raise KeyboardInterrupt
    removed = [c[4] for c in fake.calls if c[1:4] == ["rm", "-f", "-v"]]
    assert removed == [lab.name("a"), lab.name("b")]


def require_real_docker(image="python:3.12.16-alpine3.24"):
    if not shutil.which("docker") or not testkit.docker_ready():
        pytest.skip("Cần Docker daemon")
    if testkit._docker("image", "inspect", image).returncode != 0:
        pytest.skip(f"Chưa có image {image}")
    return image


@pytest.mark.parametrize("wait", ["wait_log", "wait_http"])
def test_docker_lab_logs_on_failure(wait):
    image = require_real_docker()
    lab = testkit.DockerLab()
    with pytest.raises(pytest.fail.Exception) as info:
        with lab:
            lab.start("crash", image, "sh", "-c", "for i in $(seq 1 60); do echo dong-$i; done; echo boot-loi-cau-hinh; exit 3")
            if wait == "wait_log":
                lab.wait_log("crash", "san-sang", timeout=20)
            else:
                lab.wait_http("crash", f"http://127.0.0.1:{testkit.free_port()}/", timeout=20)
    message = str(info.value)
    assert "boot-loi-cau-hinh" in message, message
    assert "dong-60" in message and "dong-20" not in message, "Chỉ kèm 40 dòng log cuối"
    assert testkit.docker_leftovers(lab.id) == []


def test_docker_lab_logs_on_timeout():
    image = require_real_docker()
    lab = testkit.DockerLab()
    with pytest.raises(pytest.fail.Exception) as info:
        with lab:
            lab.start("slow", image, "sh", "-c", "echo dang-khoi-dong; sleep 300")
            lab.wait_log("slow", "san-sang", timeout=2)
    assert "dang-khoi-dong" in str(info.value)
    assert testkit.docker_leftovers(lab.id) == []


def test_docker_lab_exited_container_kept_until_close():
    image = require_real_docker()
    with testkit.DockerLab() as lab:
        lab.start("done", image, "true")
        deadline = testkit.time.monotonic() + 20
        while lab.running("done") and testkit.time.monotonic() < deadline:
            testkit.time.sleep(0.2)
        assert lab.name("done") in testkit.docker_leftovers(lab.id), "Container đã thoát vẫn phải còn để đọc log"
    assert testkit.docker_leftovers(lab.id) == []


def test_safe_git_config_value():
    assert testkit.SAFE_GIT_CONFIG == (
        "-c", "core.hooksPath=/dev/null", "-c", "core.fsmonitor=false", "-c", "commit.gpgsign=false", "-c", "init.defaultBranch=main",
    )


def test_git_env_is_built_from_scratch(monkeypatch, tmp_path):
    monkeypatch.setenv("GIT_DIR", "/nonexistent")
    monkeypatch.setenv("GITHUB_TOKEN", "x")
    env = testkit.git_env(tmp_path / "home")
    assert env["HOME"] == str(tmp_path / "home")
    assert env["GIT_CONFIG_GLOBAL"] == env["GIT_CONFIG_SYSTEM"] == "/dev/null"
    assert env["GIT_CEILING_DIRECTORIES"] == str(tmp_path.resolve())
    assert env["GIT_AUTHOR_DATE"] == env["GIT_COMMITTER_DATE"]
    assert "GIT_DIR" not in env and "GITHUB_TOKEN" not in env
    dated = testkit.git_env(tmp_path / "home", date="2026-03-02T09:00:00+00:00")
    assert dated["GIT_AUTHOR_DATE"] == dated["GIT_COMMITTER_DATE"] == "2026-03-02T09:00:00+00:00"


def plant_smudge_filter(repo: Path, marker: Path) -> None:
    """Giả lập script người học cài filter driver: checkout chạy lệnh tuỳ ý, SAFE_GIT_CONFIG không chặn được."""
    with (repo / ".git" / "config").open("a") as handle:
        handle.write(f"[filter \"evil\"]\n\tsmudge = \"touch '{marker}'; cat\"\n\tclean = cat\n")
    (repo / ".git" / "info").mkdir(exist_ok=True)
    (repo / ".git" / "info" / "attributes").write_text("*.txt filter=evil\n")


@pytest.mark.skipif(shutil.which("git") is None, reason="Cần git")
def test_git_repo_runs_directly_before_taint(monkeypatch, tmp_path):
    repo = testkit.GitRepo(tmp_path / "repo", tmp_path / "home")
    (tmp_path / "repo").mkdir()
    (tmp_path / "home").mkdir()
    monkeypatch.setattr(testkit, "run_sandboxed", lambda *a, **kw: pytest.fail("chưa taint thì không qua sandbox"))
    assert repo.git("init", "-q").returncode == 0
    assert repo.out("symbolic-ref", "--short", "HEAD") == "main"
    with pytest.raises(AssertionError, match="git rev-parse"):
        repo.out("rev-parse", "--verify", "nope")


@SANDBOX_REQUIRED
@pytest.mark.skipif(shutil.which("git") is None, reason="Cần git")
def test_git_repo_taint_switches_to_sandbox(monkeypatch, tmp_path, tmp_path_factory):
    path, home = tmp_path / "repo", tmp_path / "home"
    path.mkdir()
    home.mkdir()
    repo = testkit.GitRepo(path, home, writable=[tmp_path])
    repo.out("init", "-q")
    (path / "a.txt").write_text("v1\n")
    repo.out("add", "a.txt")
    repo.out("commit", "-q", "-m", "one")
    (path / "a.txt").write_text("v2\n")
    repo.out("commit", "-q", "-am", "two")
    marker = tmp_path_factory.mktemp("outside-sandbox") / "pwned"
    plant_smudge_filter(path, marker)
    repo.taint()
    sandboxed = []
    real = testkit.run_sandboxed
    monkeypatch.setattr(testkit, "run_sandboxed", lambda cmd, **kw: sandboxed.append(cmd) or real(cmd, **kw))
    repo.out("checkout", "-q", "HEAD~1")
    assert sandboxed and sandboxed[0][: 1 + len(testkit.SAFE_GIT_CONFIG)] == ["git", *testkit.SAFE_GIT_CONFIG]
    assert (path / "a.txt").read_text() == "v1\n"
    assert not marker.exists(), "Sau taint(), lệnh git của test phải chạy trong sandbox"
    subprocess.run(["git", *testkit.SAFE_GIT_CONFIG, "checkout", "-q", "main"], cwd=path, env=testkit.git_env(home), capture_output=True)
    assert marker.exists(), "Kiểm tra vô nghĩa: filter giả không chạy cả khi gọi git trực tiếp"


def test_docker_lab_log_tail_survives_docker_errors(monkeypatch):
    lab = testkit.DockerLab()

    def boom(*args, **kwargs):
        raise subprocess.TimeoutExpired(["docker", "logs"], 60)

    monkeypatch.setattr(testkit, "_docker", boom)
    assert "Không lấy được docker logs" in lab._log_tail("api")
    monkeypatch.setattr(testkit, "_docker", lambda *a, **kw: (_ for _ in ()).throw(OSError("không có docker")))
    assert "Không lấy được docker logs" in lab._log_tail("api")


def test_docker_lab_log_tail_is_capped(monkeypatch):
    lab = testkit.DockerLab()
    huge = "x" * 10000 + "CUOI"
    monkeypatch.setattr(testkit, "_docker", lambda *a, **kw: subprocess.CompletedProcess(a, 0, huge, ""))
    tail = lab._log_tail("api")
    assert tail.endswith("CUOI") and len(tail) < 4200


BASE = "python:3.12.16-alpine3.24"


def build_fake(fail_build: bool = False):
    calls = []

    def run(cmd, **kwargs):
        calls.append(list(cmd))
        if cmd[1:3] == ["context", "show"]:
            return subprocess.CompletedProcess(cmd, 0, "default\n", "")
        if cmd[1:3] == ["buildx", "inspect"]:
            return subprocess.CompletedProcess(cmd, 0, "Name:          default\nDriver:        docker\n", "")
        if cmd[1:3] == ["buildx", "build"] and fail_build:
            return subprocess.CompletedProcess(cmd, 1, "", "#5 ERROR: process did not complete successfully\n")
        if cmd[1:3] == ["images", "-q"]:
            return subprocess.CompletedProcess(cmd, 0, "abc123\nabc123\n", "")
        return subprocess.CompletedProcess(cmd, 0, "", "")

    return run, calls


def write_dockerfile(path: Path, body: str) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    (path / "Dockerfile").write_text(f"FROM {BASE}\n{body}\n", encoding="utf-8")
    return path


def test_docker_lab_build_argv(monkeypatch, tmp_path):
    monkeypatch.setenv("DEVOPS_CPUSET", "2-3")
    monkeypatch.setattr(testkit, "_BUILDER", None)
    monkeypatch.setenv("BUILDX_BUILDER", "may-cua-nguoi-hoc")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "bi-mat")
    run, calls = build_fake()
    seen_env = {}
    monkeypatch.setattr(testkit.subprocess, "run", lambda cmd, **kw: (seen_env.update({tuple(cmd[:3]): kw.get("env")}), run(cmd, **kw))[1])
    context = write_dockerfile(tmp_path / "app", "RUN true")
    with testkit.DockerLab() as lab:
        tag = lab.build(context, "api", build_args={"APP_VERSION": "1.2.3"})
        assert tag == f"devops-ex-{lab.id}/api:test"
    build = next(c for c in calls if c[1:3] == ["buildx", "build"])
    pairs = [build[i : i + 2] for i in range(len(build))]
    assert ["--builder", "default"] in pairs, "Luôn dùng builder driver docker của context hiện tại, không theo BUILDX_BUILDER"
    assert "--pull=false" in build and "--load" in build
    assert ["--label", "devops-ex=1"] in pairs and ["--label", f"devops-ex.lab={lab.id}"] in pairs
    assert ["--cpuset-cpus", "2-3"] in pairs and ["--memory", testkit.DOCKER_BUILD_MEMORY] in pairs
    assert ["--build-arg", "APP_VERSION=1.2.3"] in pairs and ["-t", tag] in pairs
    assert build[-1] == str(context.resolve())
    for forbidden in ("--network", "--ssh", "--secret", "--allow", "--add-host", "--privileged"):
        assert not any(a == forbidden or a.startswith(forbidden + "=") for a in build), forbidden
    env = seen_env[("docker", "buildx", "build")]
    assert env is not None and "AWS_SECRET_ACCESS_KEY" not in env and "BUILDX_BUILDER" not in env
    removed = [c for c in calls if c[1:3] == ["rmi", "-f"]]
    assert removed[0] == ["docker", "rmi", "-f", tag]
    assert removed[1] == ["docker", "rmi", "-f", "abc123"], "Lọc theo nhãn của đúng lab này làm dự phòng"
    listed = next(c for c in calls if c[1:3] == ["images", "-q"])
    assert listed[-1] == f"label=devops-ex.lab={lab.id}"


def test_docker_lab_build_rejects_bad_alias_and_outside(monkeypatch, tmp_path):
    monkeypatch.setattr(testkit, "_BUILDER", None)
    run, calls = build_fake()
    monkeypatch.setattr(testkit.subprocess, "run", run)
    context = write_dockerfile(tmp_path / "app", "RUN true")
    (tmp_path / "Dockerfile.outside").write_text(f"FROM {BASE}\n", encoding="utf-8")
    with testkit.DockerLab() as lab:
        with pytest.raises(ValueError):
            lab.build(context, "API Server")
        with pytest.raises(pytest.fail.Exception, match="ngoài"):
            lab.build(context, "api", dockerfile="../Dockerfile.outside")
    assert not any(c[1:3] == ["buildx", "build"] for c in calls)


def test_docker_lab_build_refuses_outside_with(tmp_path):
    with pytest.raises(RuntimeError):
        testkit.DockerLab().build(tmp_path, "api")


def test_docker_lab_build_failure_reports_log_and_cleans(monkeypatch, tmp_path):
    monkeypatch.setattr(testkit, "_BUILDER", None)
    run, calls = build_fake(fail_build=True)
    monkeypatch.setattr(testkit.subprocess, "run", run)
    context = write_dockerfile(tmp_path / "app", "RUN exit 3")
    with pytest.raises(pytest.fail.Exception, match="process did not complete"):
        with testkit.DockerLab() as lab:
            lab.build(context, "api")
    assert ["docker", "rmi", "-f", f"devops-ex-{lab.id}/api:test"] in calls


def build_cpuset() -> str:
    count = os.cpu_count() or 1
    return "12-13" if count >= 36 else str(count - 1)


def test_docker_lab_build_tags_labels_and_removes(monkeypatch, tmp_path):
    require_real_docker(BASE)
    cpuset = build_cpuset()
    monkeypatch.setenv("DEVOPS_CPUSET", cpuset)
    context = write_dockerfile(
        tmp_path / "app",
        "ARG GREETING\nARG NONCE\nRUN echo \"$NONCE\" > /nonce && cat /sys/fs/cgroup/cpuset.cpus.effective > /build-cpuset "
        "&& cat /sys/fs/cgroup/memory.max > /build-mem && echo \"$GREETING\" > /greeting\n"
        "LABEL org.opencontainers.image.title=olist",
    )
    with testkit.DockerLab() as lab:
        tag = lab.build(context, "api", build_args={"GREETING": "xin-chao", "NONCE": lab.id})
        assert tag == f"devops-ex-{lab.id}/api:test"
        labels = lab.image_inspect(tag)["Config"]["Labels"]
        assert labels["devops-ex"] == "1" and labels["devops-ex.lab"] == lab.id
        assert labels["org.opencontainers.image.title"] == "olist"
        history = lab.history(tag)
        assert isinstance(history, list) and any("GREETING" in step.get("CreatedBy", "") for step in history)
        out = lab.run_once("check", tag, "sh", "-c", "cat /nonce /build-cpuset /build-mem /greeting; grep NoNewPrivs /proc/self/status")
        nonce, *lines = out.stdout.split("\n")
        assert nonce == lab.id, "Bước RUN phải chạy lại mỗi lần (không lấy từ cache), nếu không giới hạn cũ vẫn lọt qua"
        assert lines[0] == cpuset, f"Bước RUN của build phải bị ghim vào {cpuset}: {out.stdout}"
        assert int(lines[1]) == 1024 ** 3, f"Bước RUN của build phải bị giới hạn {testkit.DOCKER_BUILD_MEMORY}: {out.stdout}"
        assert lines[2] == "xin-chao"
        assert lines[3].split() == ["NoNewPrivs:", "1"]
        assert lab.name("check") not in testkit.docker_leftovers(lab.id)
        assert testkit.docker_leftovers(lab.id)
    assert testkit._docker("image", "inspect", tag).returncode != 0
    assert testkit.docker_leftovers(lab.id) == []


def test_docker_lab_build_real_error_cleans_up(tmp_path):
    require_real_docker(BASE)
    context = write_dockerfile(tmp_path / "app", "RUN echo buoc-build-hong && exit 3")
    lab = testkit.DockerLab()
    with pytest.raises(pytest.fail.Exception) as info:
        with lab:
            lab.build(context, "api")
    assert "buoc-build-hong" in str(info.value)
    assert testkit.docker_leftovers(lab.id) == []


def test_docker_lab_close_keeps_foreign_images(tmp_path):
    require_real_docker(BASE)
    context = write_dockerfile(tmp_path / "app", "RUN echo ok > /ok")
    with testkit.DockerLab() as lab:
        lab.build(context, "api")
    assert testkit._docker("image", "inspect", BASE).returncode == 0, "Không bao giờ xoá image base của người học"


def write_compose(path: Path, text: str) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    file = path / "compose.yaml"
    file.write_text(text, encoding="utf-8")
    return file


WEB_COMPOSE = f"""
name: shop-cua-nguoi-hoc
services:
  web:
    image: {BASE}
    container_name: web-co-dinh
    command: ["python", "-m", "http.server", "8000"]
    ports: ["0.0.0.0:8080:8000"]
    cpuset: "${{DEVOPS_CPUSET:-}}"
    mem_limit: 2g
    environment:
      GREETING: ${{GREETING:-mac-dinh}}
      LEAK: ${{AWS_SECRET_ACCESS_KEY:-khong-co}}
    volumes: ["./site:/srv/site:ro", "data:/data"]
  api:
    build: ./api
    image: shop-api:dev
    command: ["sh", "-c", "cat /built && sleep 300"]
volumes:
  data: {{}}
"""


def inspect_container(name: str) -> dict:
    import json

    result = testkit._docker("inspect", name)
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)[0]


def test_docker_lab_compose_override_pins_and_loopback(monkeypatch, tmp_path):
    require_real_docker(BASE)
    import httpx

    cpuset = build_cpuset()
    monkeypatch.setenv("DEVOPS_CPUSET", cpuset)
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "bi-mat-that")
    file = write_compose(tmp_path / "proj", WEB_COMPOSE)
    (tmp_path / "proj" / "site").mkdir()
    write_dockerfile(tmp_path / "proj" / "api", "RUN echo built > /built")
    with testkit.DockerLab() as lab:
        project = lab.compose(file, env={"GREETING": "xin-chao"})
        assert project.name == f"devops-ex-{lab.id}"
        port = project.port("web", 8000)
        assert port != 8080
        deadline = testkit.time.monotonic() + 30
        while testkit.time.monotonic() < deadline:
            try:
                assert httpx.get(f"http://127.0.0.1:{port}/", timeout=2).status_code == 200
                break
            except httpx.HTTPError:
                testkit.time.sleep(0.2)
        else:
            pytest.fail("web không trả lời trên cổng loopback")
        web = inspect_container(project.container("web"))
        assert web["Name"].lstrip("/").startswith(f"devops-ex-{lab.id}"), "container_name cố định bị bỏ để không đụng tên khác"
        host = web["HostConfig"]
        assert host["CpusetCpus"] == cpuset
        assert host["Memory"] == 256 * 1024 ** 2 and host["PidsLimit"] == 256
        assert "no-new-privileges:true" in host["SecurityOpt"]
        assert [b["HostIp"] for b in host["PortBindings"]["8000/tcp"]] == ["127.0.0.1"]
        assert web["Config"]["Labels"]["devops-ex"] == "1"
        env = dict(item.split("=", 1) for item in web["Config"]["Env"])
        assert env["GREETING"] == "xin-chao"
        assert env["LEAK"] == "khong-co", "Compose chạy với env dựng từ đầu, không đọc biến cloud của người học"
        assert project.exec("web", "sh", "-c", "grep NoNewPrivs /proc/self/status").stdout.split() == ["NoNewPrivs:", "1"]
        api = inspect_container(project.container("api"))
        assert api["Config"]["Image"] == f"devops-ex-{lab.id}/api:test", "Service có build: được build bằng DockerLab.build"
        assert project.exec("api", "cat", "/built").stdout.strip() == "built"
        assert "built" in project.logs("api")
        assert {row["Service"] for row in project.ps()} == {"web", "api"}
        assert testkit._docker("image", "inspect", "shop-api:dev").returncode != 0, "Không tạo tag cố định của người học"
    assert testkit.docker_leftovers(lab.id) == []


def test_docker_lab_compose_cleanup_on_error(tmp_path):
    require_real_docker(BASE)
    file = write_compose(tmp_path / "proj", f"""
services:
  sleeper:
    image: {BASE}
    command: ["sleep", "300"]
    volumes: ["data:/data"]
volumes:
  data: {{}}
""")
    lab = testkit.DockerLab()
    with pytest.raises(RuntimeError):
        with lab:
            lab.compose(file)
            leftovers = testkit.docker_leftovers(lab.id)
            assert any(name.endswith("_data") for name in leftovers), leftovers
            raise RuntimeError("lỗi giữa chừng")
    assert testkit.docker_leftovers(lab.id) == []


def test_docker_lab_compose_up_failure_shows_logs(tmp_path):
    require_real_docker(BASE)
    file = write_compose(tmp_path / "proj", f"""
services:
  crash:
    image: {BASE}
    command: ["sh", "-c", "echo cau-hinh-sai; exit 3"]
""")
    lab = testkit.DockerLab()
    with pytest.raises(pytest.fail.Exception) as info:
        with lab:
            lab.compose(file)
    assert "cau-hinh-sai" in str(info.value)
    assert testkit.docker_leftovers(lab.id) == []


@pytest.mark.parametrize(
    "service,expected",
    [
        ("    privileged: true\n", "privileged"),
        ("    network_mode: host\n", "network_mode: host"),
        ("    pid: host\n", "pid: host"),
        ("    volumes: ['/etc:/hostetc:ro']\n", "/etc"),
        ("    volumes: ['/var/run/docker.sock:/var/run/docker.sock']\n", "docker.sock"),
        ("    cap_add: [SYS_ADMIN]\n", "cap_add"),
        ("    devices: ['/dev/kmsg:/dev/kmsg']\n", "devices"),
        ("    security_opt: ['seccomp=unconfined']\n", "security_opt"),
        ("    device_cgroup_rules: ['b *:* rwm']\n", "device_cgroup_rules"),
        ("    build: ..\n", "build"),
        ("    env_file: [../secret.env]\n", "env_file"),
    ],
)
def test_docker_lab_compose_refuses_unsafe(tmp_path, service, expected):
    require_real_docker(BASE)
    (tmp_path / "secret.env").write_text("TOKEN=bi-mat\n", encoding="utf-8")
    (tmp_path / "Dockerfile").write_text(f"FROM {BASE}\n", encoding="utf-8")
    file = write_compose(tmp_path / "proj", f"services:\n  bad:\n    image: {BASE}\n    command: ['sleep', '300']\n{service}")
    lab = testkit.DockerLab()
    with pytest.raises(pytest.fail.Exception) as info:
        with lab:
            lab.compose(file)
    message = str(info.value)
    assert expected in message and "bad" in message, message
    assert testkit.docker_leftovers(lab.id) == []


@pytest.mark.parametrize(
    "top,expected",
    [
        ("networks:\n  default:\n    name: nguoi-hoc-mang-khac\n    external: true\n", "external"),
        ("volumes:\n  data:\n    external: true\n", "external"),
        ("volumes:\n  data:\n    driver_opts: {type: none, o: bind, device: /etc}\n", "driver_opts"),
    ],
)
def test_docker_lab_compose_refuses_foreign_resources(tmp_path, top, expected):
    require_real_docker(BASE)
    file = write_compose(tmp_path / "proj", f"services:\n  app:\n    image: {BASE}\n    volumes: ['data:/data']\n{top}")
    if "volumes:\n" not in top:
        file.write_text(file.read_text() + "volumes:\n  data: {}\n", encoding="utf-8")
    lab = testkit.DockerLab()
    with pytest.raises(pytest.fail.Exception, match=expected):
        with lab:
            lab.compose(file)
    assert testkit.docker_leftovers(lab.id) == []


LAB = "abcd1234"


def base_config(root: Path, **service) -> dict:
    return {
        "name": f"devops-ex-{LAB}",
        "services": {"app": {"image": "x", "command": None, "entrypoint": None, "networks": {"default": None}, **service}},
        "networks": {"default": {"name": f"devops-ex-{LAB}_default", "ipam": {}}},
        "volumes": {"data": {"name": f"devops-ex-{LAB}_data"}},
    }


@pytest.mark.parametrize(
    "service,expected",
    [
        ({"device_cgroup_rules": ["b *:* rwm"]}, "device_cgroup_rules"),
        ({"gpus": [{"driver": "nvidia", "count": -1}]}, "gpus"),
        ({"runtime": "nvidia"}, "runtime"),
        ({"devices": [{"source": "/dev/sda", "target": "/dev/sda", "permissions": "rwm"}]}, "devices"),
        ({"privileged": True}, "privileged"),
        ({"cap_add": ["NET_ADMIN"]}, "cap_add"),
        ({"security_opt": ["label=disable"]}, "security_opt"),
        ({"network_mode": "host"}, "network_mode: host"),
        ({"network_mode": "container:portainer"}, "network_mode: container:portainer"),
        ({"pid": "host"}, "pid: host"),
        ({"ipc": "host"}, "ipc: host"),
        ({"uts": "host"}, "uts: host"),
        ({"userns_mode": "host"}, "userns_mode: host"),
        ({"cgroup": "host"}, "cgroup: host"),
        ({"cgroup_parent": "/system.slice"}, "cgroup_parent"),
        ({"volumes_from": ["container:portainer"]}, "volumes_from"),
        ({"sysctls": {"net.ipv4.ip_forward": "1"}}, "sysctls"),
        ({"khoa_la": "x"}, "khoa_la"),
        ({"deploy": {"resources": {"reservations": {"devices": [{"capabilities": ["gpu"]}]}}}}, "reservations"),
        ({"deploy": {"mode": "global"}}, "mode"),
        ({"logging": {"driver": "syslog"}}, "syslog"),
        ({"ulimits": {"memlock": -1}}, "memlock"),
        ({"volumes": [{"type": "bind", "source": "/var/run/docker.sock", "target": "/var/run/docker.sock"}]}, "docker.sock"),
        ({"volumes": [{"type": "bind", "source": "/etc", "target": "/hostetc"}]}, "/etc"),
        ({"volumes": [{"type": "npipe", "source": "x", "target": "/x"}]}, "npipe"),
        ({"build": {"context": "/", "dockerfile": "Dockerfile"}}, "build context"),
        ({"build": {"context": "{root}", "dockerfile": "Dockerfile", "network": "host"}}, "network"),
        ({"env_file": [{"path": "/home/x/.aws/credentials"}]}, "env_file"),
    ],
)
def test_compose_problems_refuses_service_key(tmp_path, service, expected):
    root = tmp_path / "proj"
    root.mkdir()
    if "build" in service and service["build"]["context"] == "{root}":
        service = {"build": {**service["build"], "context": str(root)}}
    problems = testkit._compose_problems(base_config(root, **service), root, LAB)
    joined = "\n".join(problems)
    assert expected in joined and "service app" in joined, joined


@pytest.mark.parametrize(
    "kind,spec,expected",
    [
        ("volumes", {"name": "nguoi-hoc-volume-that"}, "name: nguoi-hoc-volume-that"),
        ("volumes", {"name": "devops-ex-ffffffff_data"}, "devops-ex-ffffffff_data"),
        ("networks", {"name": "nguoi-hoc-mang-that"}, "name: nguoi-hoc-mang-that"),
        ("volumes", {"name": "x", "external": True}, "external"),
        ("networks", {"name": "x", "external": True}, "external"),
        ("volumes", {"name": f"devops-ex-{LAB}_data", "driver_opts": {"type": "none", "o": "bind", "device": "/etc"}}, "driver_opts"),
        ("volumes", {"name": f"devops-ex-{LAB}_data", "driver": "nfs"}, "driver nfs"),
        ("networks", {"name": f"devops-ex-{LAB}_n", "driver": "host"}, "driver host"),
        ("networks", {"name": f"devops-ex-{LAB}_n", "driver": "macvlan"}, "driver macvlan"),
        ("networks", {"name": f"devops-ex-{LAB}_n", "ipam": {"config": [{"subnet": "10.0.0.0/8"}]}}, "ipam"),
    ],
)
def test_compose_problems_refuses_foreign_top_level(tmp_path, kind, spec, expected):
    root = tmp_path / "proj"
    config = base_config(root)
    config[kind] = {"thu": spec}
    joined = "\n".join(testkit._compose_problems(config, root, LAB))
    assert expected in joined and f"{kind} thu" in joined, joined


@pytest.mark.parametrize("key", ["configs", "secrets", "include", "khoa_la"])
def test_compose_problems_refuses_unknown_top_level(tmp_path, key):
    config = base_config(tmp_path)
    config[key] = {"x": {"file": "/etc/shadow"}}
    assert any(f"`{key}`" in p for p in testkit._compose_problems(config, tmp_path, LAB))


OLIST_LIKE = """
name: olist-shop
x-app-env: &app-env
  DATABASE_URL: postgresql+psycopg://olist:olist@postgres:5432/olist
  REDIS_URL: redis://redis:6379/0
services:
  postgres:
    image: postgres:16
    cpuset: "${DEVOPS_CPUSET:-}"
    environment: {POSTGRES_USER: olist, POSTGRES_PASSWORD: olist, POSTGRES_DB: olist}
    ports: ["127.0.0.1:25432:5432"]
    volumes: ["pgdata:/var/lib/postgresql/data", "./initdb:/docker-entrypoint-initdb.d:ro"]
    healthcheck: {test: ["CMD-SHELL", "pg_isready -U olist"], interval: 3s, timeout: 3s, retries: 20}
    logging: {driver: json-file, options: {max-size: 10m}}
  redis:
    image: redis:7
    healthcheck: {test: ["CMD", "redis-cli", "ping"], interval: 3s}
    tmpfs: [/tmp]
    cap_drop: [ALL]
    read_only: true
  api:
    build: {context: ., dockerfile: Dockerfile, args: {APP_VERSION: "1.0"}}
    image: olist-shop:dev
    container_name: olist-api
    restart: unless-stopped
    init: true
    user: "1000:1000"
    environment: *app-env
    env_file: [.env.app]
    ports: ["127.0.0.1:28000:8000"]
    ulimits: {nofile: {soft: 1024, hard: 2048}}
    depends_on:
      postgres: {condition: service_healthy}
      redis: {condition: service_healthy}
    deploy: {replicas: 1, resources: {limits: {cpus: "1", memory: 512m}}}
    networks: {default: {aliases: [shop-api]}, backend: {}}
networks:
  backend: {internal: true}
volumes:
  pgdata: {}
"""


def compose_config(file: Path, lab_id: str) -> dict:
    import json

    result = subprocess.run(["docker", "compose", "-p", f"devops-ex-{lab_id}", "-f", str(file), "config", "--no-env-resolution",
                             "--format", "json"], capture_output=True, text=True, timeout=60, env=testkit._docker_env())
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)


def test_compose_problems_accepts_olist_like_project(tmp_path):
    if not shutil.which("docker") or testkit._compose_version_ok():
        pytest.skip("Cần docker compose v2")
    root = tmp_path / "proj"
    file = write_compose(root, OLIST_LIKE)
    (root / "initdb").mkdir()
    (root / ".env.app").write_text("LOG_LEVEL=INFO\n", encoding="utf-8")
    write_dockerfile(root, "RUN true")
    assert testkit._compose_problems(compose_config(file, LAB), root, LAB) == []
    sample = testkit.ROOT / "tracks" / "devops" / "sample-app"
    assert testkit._compose_problems(compose_config(sample / "compose.yaml", LAB), sample, LAB) == []


def test_compose_override_reset_restart_readonly_binds_and_labels(tmp_path):
    lab = testkit.DockerLab()
    config = base_config(tmp_path, restart="always", volumes=[
        {"type": "bind", "source": str(tmp_path / "conf"), "target": "/c", "bind": {}},
        {"type": "volume", "source": "data", "target": "/d", "volume": {}},
    ])
    override, _ = lab._compose_override(config, {}, "2-3", "256m", 256)
    text = testkit._dump_override(override)
    app = override["services"]["app"]
    assert isinstance(app["restart"], testkit._Reset) and "restart: !reset" in text
    binds = [v for v in app["volumes"] if v["type"] == "bind"]
    assert binds and all(v["read_only"] for v in binds) and "volumes: !override" in text
    assert [v for v in app["volumes"] if v["type"] == "volume"][0].get("read_only") is None
    for kind, key in (("volumes", "data"), ("networks", "default")):
        assert override[kind][key]["labels"] == {"devops-ex": "1", "devops-ex.lab": lab.id}


def test_dockerfile_bases():
    text = """# syntax=docker/dockerfile:1
ARG PY=3.12.16
ARG UNSET
ARG BASE
FROM --platform=$BUILDPLATFORM python:${PY}-alpine3.24 AS builder
RUN echo a \\
  && echo b
FROM builder AS test
FROM $UNSET
FROM scratch
FROM nginx:${NG:-1.30.6}-alpine
from ${BASE}
FROM python:3.12.16-alpine3.24
"""
    assert testkit._dockerfile_bases(text) == ["python:3.12.16-alpine3.24", "nginx:1.30.6-alpine"]
    assert testkit._dockerfile_bases(text, {"PY": "3.13.1", "BASE": "debian:13"})[:3] == [
        "python:3.13.1-alpine3.24", "nginx:1.30.6-alpine", "debian:13"]


def test_docker_lab_build_skips_when_base_missing(monkeypatch, tmp_path):
    monkeypatch.setattr(testkit, "_BUILDER", None)
    run, calls = build_fake()

    def no_base(cmd, **kw):
        if cmd[1:3] == ["image", "inspect"]:
            calls.append(list(cmd))
            return subprocess.CompletedProcess(cmd, 1, "", "No such image")
        if cmd[1:2] == ["info"]:
            return subprocess.CompletedProcess(cmd, 0, "", "")
        return run(cmd, **kw)

    monkeypatch.setattr(testkit.subprocess, "run", no_base)
    monkeypatch.setattr(testkit.shutil, "which", lambda name: f"/usr/bin/{name}")
    context = tmp_path / "app"
    context.mkdir()
    (context / "Dockerfile").write_text("FROM ghcr.io/khong-co/base:9 AS b\nFROM b\n", encoding="utf-8")
    with pytest.raises(pytest.skip.Exception, match="docker pull ghcr.io/khong-co/base:9"):
        with testkit.DockerLab() as lab:
            lab.build(context, "api")
    assert not any(c[1:3] == ["buildx", "build"] for c in calls), "Thiếu image base thì không build (không tự pull)"


def test_docker_lab_compose_uses_copy_and_readonly_binds(tmp_path):
    require_real_docker(BASE)
    root = tmp_path / "proj"
    (root / "site").mkdir(parents=True)
    (root / "site" / "index.html").write_text("ban-goc", encoding="utf-8")
    file = write_compose(root, f"""
services:
  web:
    image: {BASE}
    command: ["sleep", "300"]
    restart: always
    volumes: ["./site:/srv/site", "data:/data"]
    tmpfs: [/scratch]
volumes:
  data: {{}}
""")
    with testkit.DockerLab() as lab:
        project = lab.compose(file)
        info = inspect_container(project.container("web"))
        bind = next(m for m in info["Mounts"] if m["Destination"] == "/srv/site")
        assert not Path(bind["Source"]).is_relative_to(root.resolve()), "Compose phải chạy từ bản chép, không phải thư mục gốc"
        assert Path(bind["Source"]).is_relative_to(Path(tempfile_root())) and bind["RW"] is False
        assert info["HostConfig"]["RestartPolicy"]["Name"] in ("", "no"), "restart bị bỏ để container không tự sống lại"
        write = project.exec("web", "sh", "-c", "echo hong > /srv/site/index.html")
        assert write.returncode != 0 and "Read-only" in write.stderr
        assert project.exec("web", "sh", "-c", "echo ok > /data/x && echo ok > /scratch/x").returncode == 0
        volume = next(m for m in info["Mounts"] if m["Destination"] == "/data")
        labels = testkit._docker("volume", "inspect", "-f", "{{json .Labels}}", volume["Name"]).stdout
        assert '"devops-ex":"1"' in labels and f'"devops-ex.lab":"{lab.id}"' in labels
    assert (root / "site" / "index.html").read_text(encoding="utf-8") == "ban-goc"
    assert testkit.docker_leftovers(lab.id) == []


def tempfile_root() -> str:
    import tempfile

    return str(Path(tempfile.gettempdir()).resolve())


def test_docker_lab_compose_refuses_outside_with(tmp_path):
    with pytest.raises(RuntimeError):
        testkit.DockerLab().compose(tmp_path / "compose.yaml")


def test_docker_lab_stop_measures_grace_period_and_exit_code():
    image = require_real_docker()
    with testkit.DockerLab() as lab:
        lab.start("ignores", image, "sleep", "300")
        lab.start("traps", image, "sh", "-c", "trap 'echo da-dung; exit 0' TERM; echo san-sang; while :; do sleep 0.2; done")
        lab.wait_log("traps", "san-sang", timeout=20)
        slow = lab.stop("ignores", timeout=3)
        fast = lab.stop("traps", timeout=3)
        assert slow >= 2.5, f"sleep là PID 1 không có handler SIGTERM, phải chờ hết 3 giây rồi bị SIGKILL ({slow:.1f}s)"
        assert lab.state("ignores")["ExitCode"] == 137
        assert fast < 2.5, f"Container bắt SIGTERM phải dừng ngay ({fast:.1f}s)"
        assert lab.state("traps")["ExitCode"] == 0
        assert "da-dung" in lab.logs("traps")
    assert testkit.docker_leftovers(lab.id) == []


def test_docker_lab_stop_refuses_outside_with():
    lab = testkit.DockerLab()
    with pytest.raises(RuntimeError):
        lab.stop("x")


BUILD_LOGS = Path(__file__).parent / "fixtures" / "build_logs"


@pytest.mark.parametrize("log,expected", [
    ("pip-offline.log", True),
    ("apt-offline.log", True),
    ("pip-retry-then-missing-package.log", False),
])
def test_build_failed_on_network(log, expected):
    assert testkit.build_failed_on_network((BUILD_LOGS / log).read_text(encoding="utf-8")) is expected


def test_build_failed_on_network_ignores_other_steps():
    text = (
        "#5 [2/3] RUN pip install six\n#5 1.0 WARNING: Retrying after NewConnectionError: Failed to establish a new connection\n"
        "#5 2.0 Successfully installed six-1.16.0\n#5 DONE 2.1s\n"
        "#6 [3/3] RUN python -c 'import nope'\n#6 0.5 ModuleNotFoundError: No module named 'nope'\n"
        "#6 ERROR: process \"/bin/sh -c python -c 'import nope'\" did not complete successfully: exit code: 1\n"
    )
    assert testkit.build_failed_on_network(text) is False


def write_project(root: Path, workflow: str, files: dict[str, str] | None = None) -> Path:
    project = root / "project"
    (project / ".github" / "workflows").mkdir(parents=True)
    (project / ".github" / "workflows" / "ci.yml").write_text(workflow, encoding="utf-8")
    for name, text in (files or {}).items():
        (project / name).write_text(text, encoding="utf-8")
    return project


SIMPLE_WORKFLOW = """
name: ci
on: push
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: echo "chay-xong"
"""


class FakeActProcess:
    def __init__(self, argv, output="", returncode=0, raise_on_wait=None, kwargs=None):
        self.args = list(argv)
        self.kwargs = kwargs or {}
        self.pid = 4242
        self.returncode = returncode
        self._stdout = output
        self._raise = raise_on_wait

    def communicate(self, timeout=None):
        if self._raise is not None:
            error, self._raise = self._raise, None
            raise error
        return self._stdout, ""

    def wait(self, timeout=None):
        return self.returncode


class FakeActWorld:
    def __init__(self, monkeypatch, stdout="[build] 🏁  Job succeeded\n", returncode=0, raise_on_wait=None):
        self.docker_calls: list[list[str]] = []
        self.processes: list[FakeActProcess] = []
        self.required: list[tuple] = []
        self.killed: list[tuple[int, int]] = []
        monkeypatch.setattr(testkit.Exercise, "require_tool", staticmethod(lambda name, v=None: self.required.append(("tool", name, v))))
        monkeypatch.setattr(testkit.Exercise, "require_image", staticmethod(lambda image, hint=None: self.required.append(("image", image))))
        monkeypatch.setattr(testkit, "_docker", self.docker)
        monkeypatch.setattr(testkit.os, "killpg", lambda pid, sig: self.killed.append((pid, sig)))

        real_popen = subprocess.Popen

        def popen(argv, **kwargs):
            if argv[0] != "act":
                return real_popen(argv, **kwargs)
            process = FakeActProcess(argv, stdout, returncode, raise_on_wait, kwargs)
            process.repo_files = sorted(str(p.relative_to(kwargs["cwd"])) for p in Path(kwargs["cwd"]).rglob("*") if ".git" not in p.parts)
            process.workflows = {p.name: p.read_text(encoding="utf-8") for p in Path(kwargs["cwd"]).glob(".github/workflows/*.yml")}
            self.processes.append(process)
            return process

        monkeypatch.setattr(testkit.subprocess, "Popen", popen)

    def docker(self, *args, timeout=60):
        self.docker_calls.append(list(args))
        run_id = next((a.split("=")[-1] for a in args if a.startswith(f"label={testkit.ACT_RUN_LABEL}=")), None)
        prefix = next((a.split("=", 1)[1] for a in args if a.startswith("name=act-devops-ex-")), None)
        if args[:2] == ("context", "inspect"):
            return subprocess.CompletedProcess(args, 0, "unix:///run/user/1000/docker.sock\n", "")
        if args[:1] == ("ps",) and run_id:
            names = f"act-devops-ex-{run_id}-ci-build-abc\nact-ci-build-abc\n"
            return subprocess.CompletedProcess(args, 0, names, "")
        if args[:2] == ("volume", "ls") and prefix:
            names = f"{prefix}-ci-build-abc\n{prefix}-ci-build-abc-env\nx-{prefix}-la\nact-toolcache\n"
            return subprocess.CompletedProcess(args, 0, names, "")
        if args[:2] == ("network", "ls") and run_id:
            return subprocess.CompletedProcess(args, 0, f"devops-ex-{run_id}\nnguoi-hoc\n", "")
        return subprocess.CompletedProcess(args, 0, "", "")


def flag(argv: list[str], name: str) -> str:
    return argv[argv.index(name) + 1]


def test_act_run_pins_image_and_limits(monkeypatch, tmp_path):
    monkeypatch.setenv("DEVOPS_CPUSET", "2-3")
    world = FakeActWorld(monkeypatch)
    project = write_project(tmp_path, SIMPLE_WORKFLOW)
    result = testkit.act_run(project, job="build", env={"APP_ENV": "ci"})
    argv = world.processes[0].args
    assert ("image", testkit.ACT_IMAGE) in world.required
    assert ("tool", "act", testkit.ACT_MIN_VERSION) in world.required
    assert argv[:2] == ["act", "push"]
    assert flag(argv, "-P") == f"ubuntu-latest={testkit.ACT_IMAGE}"
    assert "--pull=false" in argv
    assert flag(argv, "--container-daemon-socket") == "-"
    assert flag(argv, "--container-options-policy") == "restrict"
    options = flag(argv, "--container-options").split()
    pairs = [options[i : i + 2] for i in range(len(options))]
    run_id = next(o.split("=", 1)[1] for o in options if o.startswith(f"{testkit.ACT_RUN_LABEL}="))
    for expected in (["--cpuset-cpus", "2-3"], ["--memory", "1g"], ["--pids-limit", "512"],
                     ["--security-opt", "no-new-privileges"], ["--label", "devops-ex=1"], ["--label", f"{testkit.ACT_RUN_LABEL}={run_id}"]):
        assert expected in pairs, expected
    assert flag(argv, "--network") == f"devops-ex-{run_id}"
    assert ["network", "create", "--label", "devops-ex=1", "--label", f"{testkit.ACT_RUN_LABEL}={run_id}", f"devops-ex-{run_id}"] in world.docker_calls
    assert flag(argv, "--action-cache-path") == str(testkit.act_cache_dir())
    for name in ("--action-offline-mode", "--no-cache-server", "--rm", "--log-prefix-job-id"):
        assert name in argv, name
    for name in ("--env-file", "--secret-file", "--var-file", "--input-file"):
        assert flag(argv, name) == "/dev/null", name
    assert flag(argv, "-j") == "build"
    assert "--no-recurse" in argv and flag(argv, "-W") == f"{Path(flag(argv, '-C')) / '.github' / 'workflows'}/"
    assert flag(argv, "--env") == "APP_ENV=ci"
    repo = Path(flag(argv, "-C"))
    assert repo != project and not repo.is_relative_to(project)
    assert world.processes[0].kwargs["cwd"] == repo
    assert world.processes[0].kwargs["start_new_session"] is True
    assert world.processes[0].kwargs["stdin"] is subprocess.DEVNULL
    assert result.returncode == 0 and testkit.act_job_results(result) == {"build": True}
    assert not repo.exists(), "Bản chép tạm của repo phải bị xoá sau khi chạy"


def test_act_run_clean_env_unit(monkeypatch, tmp_path):
    for key, value in {"GITHUB_TOKEN": "gh-ro-ri", "ACTIONS_RUNTIME_TOKEN": "x", "AWS_SECRET_ACCESS_KEY": "y", "DOCKER_CONFIG": "/z",
                       "XDG_CONFIG_HOME": "/cfg", "ACT_LOG": "debug"}.items():
        monkeypatch.setenv(key, value)
    world = FakeActWorld(monkeypatch)
    project = write_project(tmp_path, SIMPLE_WORKFLOW, {".actrc": "-P ubuntu-latest=evil:latest\n", "app.py": "print(1)\n"})
    testkit.act_run(project, secrets={"DEPLOY_TOKEN": "sieu-bi-mat"})
    process = world.processes[0]
    env = process.kwargs["env"]
    assert set(env) == {"PATH", "HOME", "LANG", "LC_ALL", "DOCKER_HOST", "DEPLOY_TOKEN", "GITHUB_TOKEN"}
    assert env["GITHUB_TOKEN"] == testkit.ACT_DUMMY_GITHUB_TOKEN
    assert env["DOCKER_HOST"] == "unix:///run/user/1000/docker.sock"
    assert env["DEPLOY_TOKEN"] == "sieu-bi-mat"
    home = Path(env["HOME"])
    assert home != Path.home() and home.name == "home"
    assert flag(process.args, "-s") == "DEPLOY_TOKEN", "Giá trị secret đi qua env của act, không nằm trên argv"
    assert "sieu-bi-mat" not in " ".join(process.args)
    assert ".actrc" not in process.repo_files and "app.py" in process.repo_files


@pytest.mark.parametrize("leak", ["GH_TOKEN", "GITHUB_TOKEN", "GH_ENTERPRISE_TOKEN", "GH_CONFIG_DIR", "DBUS_SESSION_BUS_ADDRESS", "XDG_RUNTIME_DIR"])
def test_act_run_env_has_no_gh_credentials(monkeypatch, tmp_path, leak):
    monkeypatch.setenv(leak, "/ro-ri-tu-may")
    world = FakeActWorld(monkeypatch)
    testkit.act_run(write_project(tmp_path, SIMPLE_WORKFLOW))
    env = world.processes[0].kwargs["env"]
    assert "/ro-ri-tu-may" not in env.values()
    assert leak == "GITHUB_TOKEN" or leak not in env


def test_act_run_always_passes_github_token_secret(monkeypatch, tmp_path):
    world = FakeActWorld(monkeypatch)
    project = write_project(tmp_path, SIMPLE_WORKFLOW)
    testkit.act_run(project)
    testkit.act_run(project, secrets={"DEPLOY_TOKEN": "sieu-bi-mat"}, github_token="token-cua-nguoi-goi")
    for process, token in zip(world.processes, [testkit.ACT_DUMMY_GITHUB_TOKEN, "token-cua-nguoi-goi"]):
        pairs = [process.args[i + 1] for i, a in enumerate(process.args) if a == "-s"]
        assert pairs.count("GITHUB_TOKEN") == 1
        assert process.kwargs["env"]["GITHUB_TOKEN"] == token
        assert token not in " ".join(process.args)
        shim = process.kwargs["env"]["PATH"].split(":")[0]
        assert shim.endswith("gh-shim")
    assert sorted(pairs) == ["DEPLOY_TOKEN", "GITHUB_TOKEN"]


def test_act_run_refuses_short_github_token(monkeypatch, tmp_path):
    world = FakeActWorld(monkeypatch)
    with pytest.raises(pytest.fail.Exception) as info:
        testkit.act_run(write_project(tmp_path, SIMPLE_WORKFLOW), github_token="abc")
    assert "GITHUB_TOKEN" in str(info.value)
    assert world.processes == []


def test_act_gh_shim_marks_and_fails(tmp_path):
    shim = testkit._act_gh_shim(tmp_path)
    env = {"PATH": f"{shim}:/usr/local/bin:/usr/bin:/bin", "HOME": str(tmp_path)}
    assert shutil.which("gh", path=env["PATH"]) == str(shim / "gh")
    called = subprocess.run(["gh", "auth", "token"], env=env, capture_output=True, text=True)
    assert called.returncode != 0 and called.stdout == ""
    assert (tmp_path / testkit.ACT_GH_SHIM_MARKER).exists()


def test_act_run_fails_when_act_calls_gh(monkeypatch, tmp_path):
    world = FakeActWorld(monkeypatch)
    fake_popen = testkit.subprocess.Popen

    def popen(argv, **kwargs):
        if argv[0] == "act":
            subprocess.run(["gh", "auth", "token"], env=kwargs["env"], capture_output=True)
        return fake_popen(argv, **kwargs)

    monkeypatch.setattr(testkit.subprocess, "Popen", popen)
    with pytest.raises(pytest.fail.Exception) as info:
        testkit.act_run(write_project(tmp_path, SIMPLE_WORKFLOW))
    assert "gh" in str(info.value)
    assert len(world.processes) == 1


def test_act_run_rejects_bad_secret_names(monkeypatch, tmp_path):
    FakeActWorld(monkeypatch)
    project = write_project(tmp_path, SIMPLE_WORKFLOW)
    for name in ("PATH", "GITHUB_X", "co dau cach"):
        with pytest.raises(pytest.fail.Exception):
            testkit.act_run(project, secrets={name: "x"})


def test_act_run_scrubs_secret_values_from_output(monkeypatch, tmp_path):
    FakeActWorld(monkeypatch, stdout="[build]   | lo ra sieu-bi-mat\n[build] 🏁  Job succeeded\n")
    project = write_project(tmp_path, SIMPLE_WORKFLOW)
    result = testkit.act_run(project, secrets={"DEPLOY_TOKEN": "sieu-bi-mat"})
    assert "sieu-bi-mat" not in result.stdout and "***" in result.stdout


@pytest.mark.parametrize("workflow,expected", [
    (SIMPLE_WORKFLOW.replace("ubuntu-latest", "windows-latest"), "runs-on"),
    (SIMPLE_WORKFLOW.replace("actions/checkout@v4", "docker://alpine:3.20"), "docker://alpine:3.20"),
    (SIMPLE_WORKFLOW.replace("actions/checkout@v4", "someone/build-image@v1"), "someone/build-image@v1"),
    (SIMPLE_WORKFLOW.replace("    steps:", "    services:\n      db:\n        image: postgres:16.9\n    steps:"), "services"),
    (SIMPLE_WORKFLOW.replace("    steps:", "    container: alpine:3.20\n    steps:"), "container"),
    ("name: ci\non: push\njobs:\n  call:\n    uses: org/repo/.github/workflows/x.yml@main\n", "org/repo"),
])
def test_act_run_refuses_unsupported_workflows(monkeypatch, tmp_path, workflow, expected):
    world = FakeActWorld(monkeypatch)
    project = write_project(tmp_path, workflow)
    with pytest.raises(pytest.fail.Exception) as info:
        testkit.act_run(project)
    assert expected in str(info.value)
    assert world.processes == []


def test_act_run_skips_when_action_missing_offline(monkeypatch, tmp_path):
    output = (
        "[build]   ☁  git clone 'https://github.com/actions/setup-node' # ref=v4\n"
        "[build] Unable to clone https://github.com/actions/setup-node refs/heads/v4: Get \"https://github.com/actions/setup-node/info/refs"
        "?service=git-upload-pack\": dial tcp: lookup github.com on 127.0.0.53:53: dial udp 127.0.0.53:53: connect: network is unreachable\n"
        "[build] 🏁  Job failed\n"
    )
    FakeActWorld(monkeypatch, stdout=output, returncode=1)
    project = write_project(tmp_path, SIMPLE_WORKFLOW)
    with pytest.raises(pytest.skip.Exception) as info:
        testkit.act_run(project)
    assert "actions/setup-node" in str(info.value) and str(testkit.act_cache_dir()) in str(info.value)


def test_act_run_cleanup_on_interrupt(monkeypatch, tmp_path):
    world = FakeActWorld(monkeypatch, raise_on_wait=KeyboardInterrupt())
    project = write_project(tmp_path, SIMPLE_WORKFLOW)
    with pytest.raises(KeyboardInterrupt):
        testkit.act_run(project)
    argv = world.processes[0].args
    run_id = next(o.split("=", 1)[1] for o in flag(argv, "--container-options").split() if o.startswith(f"{testkit.ACT_RUN_LABEL}="))
    assert world.killed and world.killed[0][0] == 4242
    prefix = f"act-devops-ex-{run_id}"
    removals = [c for c in world.docker_calls if c[:2] in (["rm", "-f"], ["volume", "rm"], ["network", "rm"])]
    assert removals == [
        ["rm", "-f", f"{prefix}-ci-build-abc"],
        ["volume", "rm", f"{prefix}-ci-build-abc", f"{prefix}-ci-build-abc-env"],
        ["network", "rm", f"devops-ex-{run_id}"],
    ], "Chỉ xoá thứ vừa có nhãn vừa có tên riêng của lần chạy; không bao giờ xoá act-toolcache hay tên của người khác"
    assert not Path(flag(argv, "-C")).exists()


def test_act_run_never_removes_shared_names(monkeypatch, tmp_path):
    world = FakeActWorld(monkeypatch)
    testkit.act_run(write_project(tmp_path, SIMPLE_WORKFLOW))
    removed = [name for c in world.docker_calls if c[:2] in (["rm", "-f"], ["volume", "rm"], ["network", "rm"]) for name in c[2:]]
    assert removed and all(n.startswith("act-devops-ex-") or n.startswith("devops-ex-") for n in removed), removed
    assert "act-toolcache" not in removed and "act-ci-build-abc" not in removed


def test_act_run_renames_workflows_in_copy(monkeypatch, tmp_path):
    world = FakeActWorld(monkeypatch)
    unnamed = "on: push\njobs:\n  build:\n    runs-on: ubuntu-latest\n    steps:\n      - run: echo hi\n"
    project = write_project(tmp_path, SIMPLE_WORKFLOW.replace("name: ci", "name: >-\n  CI chính\n  của shop"))
    (project / ".github" / "workflows" / "release.yml").write_text(unnamed, encoding="utf-8")
    testkit.act_run(project)
    argv = world.processes[0].args
    run_id = next(o.split("=", 1)[1] for o in flag(argv, "--container-options").split() if o.startswith(f"{testkit.ACT_RUN_LABEL}="))
    import yaml

    renamed = {name: yaml.safe_load(text) for name, text in world.processes[0].workflows.items()}
    assert renamed["ci.yml"]["name"] == f"devops-ex-{run_id}-CI chính của shop"
    assert renamed["release.yml"]["name"] == f"devops-ex-{run_id}-release"
    assert renamed["ci.yml"]["jobs"] == yaml.safe_load(SIMPLE_WORKFLOW)["jobs"]
    assert "name: >-" in (project / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8"), "Tệp gốc giữ nguyên"
    assert yaml.safe_load((project / ".github" / "workflows" / "release.yml").read_text(encoding="utf-8")).get("name") is None


def test_act_run_refuses_nested_workflows(monkeypatch, tmp_path):
    world = FakeActWorld(monkeypatch)
    project = write_project(tmp_path, SIMPLE_WORKFLOW)
    nested = project / ".github" / "workflows" / "sub"
    nested.mkdir()
    (nested / "evil.yaml").write_text(SIMPLE_WORKFLOW, encoding="utf-8")
    with pytest.raises(pytest.fail.Exception) as info:
        testkit.act_run(project)
    assert "sub/evil.yaml" in str(info.value) and "thư mục con" in str(info.value)
    assert world.processes == []


GUARDED_PUSH = """
name: ci
on: push
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: echo "devops-ex-output tag=sha-$(git rev-parse --short HEAD 2>/dev/null || echo local)"
      - uses: docker/build-push-action@v6
        {guard}
        with:
          push: true
"""


def test_act_run_allows_actions_only_when_skipped_locally(monkeypatch, tmp_path):
    world = FakeActWorld(monkeypatch)
    testkit.act_run(write_project(tmp_path / "a", GUARDED_PUSH.format(guard="if: ${{ !env.ACT }}")))
    testkit.act_run(write_project(tmp_path / "b", GUARDED_PUSH.format(guard="if: github.ref == 'refs/heads/main' && !env.ACT")))
    assert len(world.processes) == 2
    argv = world.processes[0].args
    stubs = [argv[i + 1] for i, a in enumerate(argv) if a == "--local-repository"]
    assert sorted(s.split("=", 1)[0] for s in stubs) == ["actions/checkout@v4", "docker/build-push-action@v6"]
    for guard in ("", "if: ${{ env.ACT }}", "if: github.ref == 'refs/heads/main'"):
        with pytest.raises(pytest.fail.Exception) as info:
            testkit.act_run(write_project(tmp_path / f"c{len(guard)}", GUARDED_PUSH.format(guard=guard)))
        assert "docker/build-push-action@v6" in str(info.value) and "!env.ACT" in str(info.value)


def test_act_run_refuses_short_secrets(monkeypatch, tmp_path):
    world = FakeActWorld(monkeypatch)
    with pytest.raises(pytest.fail.Exception) as info:
        testkit.act_run(write_project(tmp_path, SIMPLE_WORKFLOW), secrets={"PIN": "123", "TOKEN": "du-dai-roi"})
    assert "PIN" in str(info.value) and "TOKEN" not in str(info.value) and str(testkit.ACT_SECRET_MIN_LENGTH) in str(info.value)
    assert world.processes == []


def test_act_outputs_parses_marked_lines():
    output = (
        "[build] ⭐ Run Main echo \"devops-ex-output tag=$TAG\"\n"
        "[build]   | devops-ex-output tag=sha-abc123\n"
        "[build]   | devops-ex-output image.name=olist-shop/api\n"
        "[lint]   | devops-ex-output ok=true\r\n"
        "[lint]   | khong devops-ex-output x=1\n"
        "[lint]   | devops-ex-output khong hop le\n"
        "[build]   | devops-ex-output tag=sha-def456\n"
    )
    result = subprocess.CompletedProcess([], 0, output, "")
    assert testkit.act_outputs(result) == {"build": {"tag": "sha-def456", "image.name": "olist-shop/api"}, "lint": {"ok": "true"}}


def test_act_run_timeout_fails_with_output(monkeypatch, tmp_path):
    world = FakeActWorld(monkeypatch, stdout="[build]   | bat-dau\n", raise_on_wait=subprocess.TimeoutExpired(["act"], 5))
    with pytest.raises(pytest.fail.Exception) as info:
        testkit.act_run(write_project(tmp_path, SIMPLE_WORKFLOW), timeout=5)
    assert "bat-dau" in str(info.value) and "5" in str(info.value)
    assert world.killed


def test_act_job_results_parses_job_ids():
    output = "[lint] 🏁  Job succeeded\n[test-1] 🏁  Job failed\n[x]   | 🏁  Job succeeded in log\n"
    assert testkit.act_job_results(subprocess.CompletedProcess([], 1, output, "")) == {"lint": True, "test-1": False}


def require_real_act():
    if shutil.which("act") is None:
        pytest.skip("Chưa cài act")
    if not testkit.docker_ready():
        pytest.skip("Cần Docker daemon")
    if testkit._docker("image", "inspect", testkit.ACT_IMAGE).returncode != 0:
        pytest.skip(f"Chưa có image {testkit.ACT_IMAGE}")


def act_volumes() -> set[str]:
    """Volume `act-*` trên máy, trừ `act-toolcache`: cache dùng chung act tự tạo, testkit cố ý không bao giờ xoá."""
    names = testkit._docker("volume", "ls", "--filter", "name=act-", "--format", "{{.Name}}").stdout.split()
    return set(names) - {"act-toolcache"}


def act_containers() -> set[str]:
    return set(testkit._docker("ps", "-a", "--filter", "name=act-", "--format", "{{.Names}}").stdout.split())


def devops_networks() -> set[str]:
    return set(testkit._docker("network", "ls", "--filter", "name=devops-ex-", "--format", "{{.Name}}").stdout.split())


def test_act_run_clean_env(monkeypatch, tmp_path):
    require_real_act()
    leaks = {"GITHUB_TOKEN": "gh-ro-ri-111", "ACTIONS_RUNTIME_TOKEN": "act-ro-ri-222", "AWS_SECRET_ACCESS_KEY": "aws-ro-ri-333",
             "DOCKER_CONFIG": str(tmp_path / "docker-ro-ri-444")}
    for key, value in leaks.items():
        monkeypatch.setenv(key, value)
    fake_home = tmp_path / "fake-home"
    (fake_home / ".config" / "act").mkdir(parents=True)
    (fake_home / ".actrc").write_text("--env FROM_HOME_ACTRC=home-ro-ri-555\n", encoding="utf-8")
    (fake_home / ".config" / "act" / "actrc").write_text("--env FROM_XDG_ACTRC=xdg-ro-ri-666\n", encoding="utf-8")
    monkeypatch.setenv("HOME", str(fake_home))
    workflow = """
name: ci
on: push
jobs:
  check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: echo "token=[$(printf '%s' "$TOK" | sha256sum | cut -c1-64)]"
        env:
          TOK: ${{ secrets.GITHUB_TOKEN }}
      - run: |
          env | rev
          echo "workspace=$(ls | tr '\\n' ' ')"
          echo "da-kiem-env"
"""
    project = write_project(tmp_path, workflow, {
        ".actrc": "--env FROM_PROJECT_ACTRC=proj-ro-ri-777\n",
        ".env": "FROM_DOTENV=dotenv-ro-ri-888\n",
        ".secrets": "GITHUB_TOKEN=secrets-ro-ri-999\n",
        "app.py": "print('xin chao')\n",
    })
    result = testkit.act_run(project, timeout=300)
    output = result.stdout + result.stderr
    assert testkit.act_job_results(result) == {"check": True}, output[-3000:]
    assert "da-kiem-env" in output and f"token=[{token_digest(testkit.ACT_DUMMY_GITHUB_TOKEN)}]" in output
    assert "app.py" in output
    for value in [*leaks.values(), "home-ro-ri-555", "xdg-ro-ri-666", "proj-ro-ri-777", "dotenv-ro-ri-888", "secrets-ro-ri-999"]:
        assert value not in output and value[::-1] not in output, value


def token_digest(value: str) -> str:
    import hashlib

    return hashlib.sha256(value.encode()).hexdigest()


GH_TOKEN_PROBE_WORKFLOW = """
name: ci
on: push
jobs:
  probe:
    runs-on: ubuntu-latest
    steps:
      - run: |
          for name in TOK GITHUB_TOKEN; do
            value=$(printenv "$name" || true)
            case "$value" in gho_*|ghp_*|ghs_*|ghu_*|ghr_*|github_pat_*) real=yes ;; *) real=no ;; esac
            echo "devops-ex-output ${name}_set=$(printenv "$name" >/dev/null && echo yes || echo no)"
            echo "devops-ex-output ${name}_real=$real"
            echo "devops-ex-output ${name}_len=${#value}"
            echo "devops-ex-output ${name}_sha=$(printf '%s' "$value" | sha256sum | cut -c1-64)"
          done
        env:
          TOK: ${{ secrets.GITHUB_TOKEN }}
"""


def test_act_run_never_reaches_host_gh_token(tmp_path):
    require_real_act()
    result = testkit.act_run(write_project(tmp_path, GH_TOKEN_PROBE_WORKFLOW), timeout=300)
    assert testkit.act_job_results(result) == {"probe": True}
    probe = testkit.act_outputs(result)["probe"]
    dummy = testkit.ACT_DUMMY_GITHUB_TOKEN
    assert probe["TOK_real"] == "no" and probe["GITHUB_TOKEN_real"] == "no"
    assert probe["TOK_set"] == "yes"
    assert probe["TOK_len"] == str(len(dummy)) and probe["TOK_sha"] == token_digest(dummy)
    if probe["GITHUB_TOKEN_set"] == "yes":
        assert probe["GITHUB_TOKEN_sha"] == token_digest(dummy)


def test_act_gh_shim_catches_fallback_without_explicit_token(monkeypatch, tmp_path):
    require_real_act()
    real_command = testkit._act_command

    def without_token(*args, **kwargs):
        argv = real_command(*args, **kwargs)
        assert argv[-2:] == ["-s", "GITHUB_TOKEN"]
        return argv[:-2]

    monkeypatch.setattr(testkit, "_act_command", without_token)
    with pytest.raises(pytest.fail.Exception) as info:
        testkit.act_run(write_project(tmp_path, GH_TOKEN_PROBE_WORKFLOW), timeout=300)
    assert "`gh`" in str(info.value)


def test_act_run_job_container_limits_and_secret_masking(monkeypatch, tmp_path):
    require_real_act()
    monkeypatch.setenv("DEVOPS_CPUSET", "12-13")
    workflow = """
name: ci
on: push
jobs:
  ok:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: |
          echo "cpuset=$(cat /sys/fs/cgroup/cpuset.cpus.effective)"
          echo "memory=$(cat /sys/fs/cgroup/memory.max)"
          echo "pids=$(cat /sys/fs/cgroup/pids.max)"
          grep NoNewPrivs /proc/self/status
          test -e /var/run/docker.sock && echo "co-docker-sock" || echo "khong-docker-sock"
          echo "secret=${{ secrets.DEPLOY_TOKEN }}"
          echo "secret-env=$DEPLOY"
          echo "app-env=$APP_ENV"
        env:
          DEPLOY: ${{ secrets.DEPLOY_TOKEN }}
  broken:
    runs-on: ubuntu-latest
    steps:
      - run: echo "sap-loi"; exit 3
"""
    project = write_project(tmp_path, workflow)
    before = act_volumes()
    result = testkit.act_run(project, env={"APP_ENV": "ci-local"}, secrets={"DEPLOY_TOKEN": "tok-sieu-bi-mat-42"}, timeout=300)
    output = result.stdout + result.stderr
    assert testkit.act_job_results(result) == {"ok": True, "broken": False}, output[-3000:]
    assert result.returncode != 0
    assert "cpuset=12-13" in output and "memory=1073741824" in output and "pids=512" in output
    assert "NoNewPrivs:\t1" in output and "khong-docker-sock" in output
    assert "app-env=ci-local" in output
    assert "tok-sieu-bi-mat-42" not in output and "secret=***" in output and "secret-env=***" in output
    assert act_volumes() <= before


def test_act_run_cleans_containers(tmp_path):
    require_real_act()
    marker = testkit.uuid.uuid4().hex[:8]
    foreign_volume = f"act-foreign-{marker}"
    foreign_container = f"act-foreign-{marker}"
    workflow = f"""
name: cleanup-{marker}
on: push
jobs:
  slow:
    runs-on: ubuntu-latest
    steps:
      - run: echo "bat-dau"; sleep 300
"""
    project = write_project(tmp_path, workflow)
    assert testkit._docker("volume", "create", foreign_volume).returncode == 0
    created = testkit._docker("create", "--name", foreign_container, "--label", "devops-ex=1", "--label", f"{testkit.ACT_RUN_LABEL}=khac",
                              testkit.ACT_IMAGE, "true")
    assert created.returncode == 0, created.stderr
    try:
        volumes, containers, networks = act_volumes(), act_containers(), devops_networks()
        with pytest.raises(pytest.fail.Exception) as info:
            testkit.act_run(project, timeout=20)
        assert "bat-dau" in str(info.value), "Container của job phải đã chạy trước khi bị ngắt"
        assert not [v for v in act_volumes() if f"cleanup-{marker}" in v]
        assert not [c for c in act_containers() if f"cleanup-{marker}" in c]
        assert act_volumes() == volumes and act_containers() == containers and devops_networks() == networks
    finally:
        testkit._docker("rm", "-f", foreign_container)
        testkit._docker("volume", "rm", foreign_volume)


def test_require_registry_down_skips(monkeypatch):
    monkeypatch.setattr(testkit, "service_up", lambda name, timeout=0.5: False)
    with pytest.raises(pytest.skip.Exception) as info:
        testkit.Exercise.require_registry()
    assert "docker compose -f setup/docker-compose.yml --profile devops up -d registry" in str(info.value)


def test_require_registry_other_server_skips(monkeypatch):
    monkeypatch.setattr(testkit, "service_up", lambda name, timeout=0.5: True)
    monkeypatch.setattr(testkit, "_registry_request", lambda method, path, headers=None: (200, {}))
    with pytest.raises(pytest.skip.Exception) as info:
        testkit.Exercise.require_registry()
    assert "15000" in str(info.value) and "DEVOPS_REGISTRY_PORT" in str(info.value)


def test_require_registry_returns_address(monkeypatch):
    monkeypatch.setenv("DEVOPS_REGISTRY_PORT", "15123")
    monkeypatch.setattr(testkit, "service_up", lambda name, timeout=0.5: True)
    monkeypatch.setattr(testkit, "_registry_request",
                        lambda method, path, headers=None: (200, {"docker-distribution-api-version": "registry/2.0"}))
    assert testkit.Exercise.require_registry() == "localhost:15123"


def test_docker_lab_push_tags_per_lab_and_deletes(monkeypatch):
    fake = FakeDocker()
    requests = []
    monkeypatch.setattr(testkit.Exercise, "require_registry", staticmethod(lambda: "localhost:15000"))

    def run(cmd, **kwargs):
        result = fake(cmd, **kwargs)
        if cmd[1] == "push":
            return subprocess.CompletedProcess(cmd, 0, "test: digest: sha256:" + "a" * 64 + " size: 528\n", "")
        return result

    monkeypatch.setattr(testkit.subprocess, "run", run)
    monkeypatch.setattr(testkit, "_registry_request", lambda method, path, headers=None: (requests.append((method, path)), (202, {}))[1])
    with pytest.raises(RuntimeError):
        testkit.DockerLab().push("x:1", "web")
    with testkit.DockerLab() as lab:
        built = f"devops-ex-{lab.id}/web:test"
        ref = lab.push(built, "web")
        assert ref == f"localhost:15000/devops-ex-{lab.id}/web:test"
        with pytest.raises(ValueError):
            lab.push(built, "Sai Ten")
    assert ["docker", "tag", built, ref] in fake.calls
    assert ["docker", "push", ref] in fake.calls
    assert ("DELETE", f"/v2/devops-ex-{lab.id}/web/manifests/sha256:{'a' * 64}") in requests
    assert ["docker", "rmi", ref] in fake.calls


def test_docker_lab_push_refuses_foreign_images(monkeypatch):
    fake = FakeDocker()
    monkeypatch.setattr(testkit.subprocess, "run", fake)
    monkeypatch.setattr(testkit.Exercise, "require_registry", staticmethod(lambda: "localhost:15000"))
    with testkit.DockerLab() as lab:
        other = testkit.DockerLab()
        for image in ("postgres:16.9", f"{other.network}/api:test", "olist-shop:dev", f"x/{lab.network}/api:test"):
            with pytest.raises(pytest.fail.Exception) as info:
                lab.push(image, "api")
            assert image in str(info.value)
    assert not [c for c in fake.calls if c[1] in ("tag", "push")]


def test_docker_lab_push_real_registry(tmp_path):
    require_real_docker()
    address = testkit.Exercise.require_registry()
    context = tmp_path / "ctx"
    context.mkdir()
    (context / "Dockerfile").write_text("FROM scratch\nCOPY hello.txt /hello.txt\n", encoding="utf-8")
    (context / "hello.txt").write_text("xin chao\n", encoding="utf-8")
    accept = {"Accept": ", ".join(testkit.REGISTRY_MANIFEST_TYPES)}
    with testkit.DockerLab() as lab:
        ref = lab.push(lab.build(context, "hello"), "hello")
        repo = f"devops-ex-{lab.id}/hello"
        assert ref == f"{address}/{repo}:test"
        assert testkit._registry_request("HEAD", f"/v2/{repo}/manifests/test", accept)[0] == 200
    assert testkit._registry_request("HEAD", f"/v2/{repo}/manifests/test", accept)[0] == 404
    assert testkit._docker("image", "inspect", ref).returncode != 0
    assert testkit.docker_leftovers(lab.id) == []


def act_original_name(workflow: str, job: str) -> str:
    """Tên container act tự đặt khi không đổi `name:` (act 0.2.94, createContainerName): `act-<wf>-<job>-<sha256>`."""
    import hashlib
    import re

    name = re.sub(r"[^a-zA-Z0-9]", "-", f"act-{workflow}/{job}").replace("--", "-")
    return f"{name[:63].strip('-')}-{hashlib.sha256(name.encode()).hexdigest()}"


def test_act_original_name_matches_act():
    assert act_original_name("CI", "build") == "act-CI-build-03727a8f260608c14dbfbecd23630d3cd3cc939c3150870ab3631218246ce38f"


def test_act_run_spares_resources_with_act_original_names(tmp_path):
    require_real_act()
    workflow_name = f"ci-{testkit.uuid.uuid4().hex[:8]}"
    original = act_original_name(workflow_name, "build")
    project = write_project(tmp_path, SIMPLE_WORKFLOW.replace("name: ci", f"name: {workflow_name}"))
    volumes = [original, f"{original}-env"]
    try:
        for volume in volumes:
            assert testkit._docker("volume", "create", volume).returncode == 0
        created = testkit._docker("create", "--name", original, "--label", "devops-ex=1", testkit.ACT_IMAGE, "true")
        assert created.returncode == 0, created.stderr
        result = testkit.act_run(project, timeout=300)
        assert testkit.act_job_results(result) == {"build": True}, (result.stdout + result.stderr)[-3000:]
        assert original in act_containers(), "Container trùng tên gốc của act phải còn nguyên"
        assert set(volumes) <= act_volumes(), "Volume trùng tên gốc của act phải còn nguyên"
    finally:
        testkit._docker("rm", "-f", original)
        testkit._docker("volume", "rm", *volumes)


def test_act_run_concurrent_runs_of_same_workflow(tmp_path):
    require_real_act()
    from concurrent.futures import ThreadPoolExecutor

    project = write_project(tmp_path, SIMPLE_WORKFLOW.replace('echo "chay-xong"', 'sleep 4; echo "chay-xong"'))
    before = act_volumes(), act_containers(), devops_networks()
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: testkit.act_run(project, timeout=300), range(2)))
    for result in results:
        assert testkit.act_job_results(result) == {"build": True}, (result.stdout + result.stderr)[-3000:]
        assert "chay-xong" in result.stdout + result.stderr
    assert (act_volumes(), act_containers(), devops_networks()) == before


def test_act_run_outputs_and_guarded_steps(tmp_path):
    require_real_act()
    workflow = """
name: ci
on: push
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: echo "devops-ex-output tag=sha-$(cat VERSION)"
      - name: Build và push (chỉ chạy trên GitHub)
        if: ${{ !env.ACT }}
        uses: docker/build-push-action@v6
        with:
          push: true
      - if: ${{ !env.ACT }}
        run: echo "khong-duoc-chay"
"""
    project = write_project(tmp_path, workflow, {"VERSION": "1.4.2\n"})
    result = testkit.act_run(project, timeout=300)
    output = result.stdout + result.stderr
    assert testkit.act_job_results(result) == {"build": True}, output[-3000:]
    assert testkit.act_outputs(result) == {"build": {"tag": "sha-1.4.2"}}
    assert "| khong-duoc-chay" not in output
    assert "git clone 'https://github.com/docker/build-push-action'" not in output, "Bước bị bỏ qua không được tải action"


@pytest.mark.parametrize("condition", [
    "${{ !env.ACT }}",
    "!env.ACT",
    "${{ ! env.ACT }}",
    "!env.ACT && github.ref == 'refs/heads/main'",
    "github.ref == 'refs/heads/main' && !env.ACT",
    "${{ github.event_name == 'push' && !env.ACT && github.ref == 'a || b' }}",
    "${{ !cancelled() && !env.ACT }}",
    "failure() && !env.ACT",
    "always() && !env.ACT",
    "success() && github.ref == 'refs/heads/main' && !env.ACT",
    "cancelled() && !env.ACT",
])
def test_act_guard_accepts(condition):
    assert testkit.act_skipped_locally(condition)


@pytest.mark.parametrize("condition", [
    None,
    "",
    "${{ env.ACT }}",
    "true || !env.ACT",
    "${{ true || !env.ACT }}",
    "(!env.ACT) == false",
    "!env.ACT == false",
    "!env.ACT != true",
    "github.ref == '!env.ACT'",
    "github.ref == 'x && !env.ACT'",
    "contains('!env.ACT', 'x')",
    '"!env.ACT"',
    "!!env.ACT",
    "!env.ACTION",
    "${{ !env.ACT }} || true",
    "${{ !env.ACT }} && ${{ true }}",
    "!(x&&!env.ACT&&y)",
    "always() || !env.ACT",
    "contains(github.ref, 'x') && !env.ACT",
    "always() && (!env.ACT)",
    "!always() && !env.ACT && x()",
    "!env.ACT && hashFiles('a')",
    "env[1&&!env.ACT&&2]",
    "${{ env['ACT'] && !env.ACT }}",
])
def test_act_guard_refuses_bypasses(condition):
    assert not testkit.act_skipped_locally(condition)


@pytest.mark.parametrize("uses", [
    "docker://node:24.22.2-trixie-slim",
    "./.github/actions/build",
    "../outside",
    "o/r/../../../../ESCAPED@v1",
    "o/r/./x@v1",
    "../r@v1",
    "o/..@v1",
    "o//x@v1",
    "o/r@",
])
def test_act_run_refuses_unsafe_uses_even_when_guarded(monkeypatch, tmp_path, uses):
    world = FakeActWorld(monkeypatch)
    project = write_project(tmp_path, GUARDED_PUSH.format(guard="if: ${{ !env.ACT }}").replace("docker/build-push-action@v6", uses))
    with pytest.raises(pytest.fail.Exception) as info:
        testkit.act_run(project)
    assert uses in str(info.value)
    assert world.processes == []
    assert not list(Path("/").glob("ESCAPED")) and not [p for p in tmp_path.rglob("ESCAPED")]


def test_act_guarded_stubs_never_write_outside(tmp_path):
    root = tmp_path / "a" / "b" / "c" / "root"
    repo = root / "repo"
    (repo / ".github" / "workflows").mkdir(parents=True)
    steps = "      - if: ${{ !env.ACT }}\n        uses: o/r/../../../../ESCAPED@v1\n"
    (repo / ".github" / "workflows" / "ci.yml").write_text(
        f"name: ci\non: push\njobs:\n  build:\n    runs-on: ubuntu-latest\n    steps:\n{steps}", encoding="utf-8")
    with pytest.raises(pytest.fail.Exception):
        testkit._act_guarded_stubs(repo, root)
    assert not list(tmp_path.rglob("ESCAPED")) and not list(tmp_path.rglob("action.yml"))
    for uses in ("o/r/sub/dir@v1", "o/r@v1"):
        (repo / ".github" / "workflows" / "ci.yml").write_text(
            f"name: ci\non: push\njobs:\n  build:\n    runs-on: ubuntu-latest\n    steps:\n"
            f"      - if: ${{{{ !env.ACT }}}}\n        uses: {uses}\n", encoding="utf-8")
        args = testkit._act_guarded_stubs(repo, root)
        assert args[0] == "--local-repository" and args[1].startswith("o/r@v1=")
    written = sorted(str(p.relative_to(root)) for p in root.rglob("action.yml"))
    assert written == ["stubs/0/action.yml", "stubs/0/sub/dir/action.yml"]


@pytest.mark.parametrize("header", ["---\n", "%YAML 1.2\n---\n", "# chu thich\n---\n", "%YAML 1.2\n--- # bat dau\n"])
def test_act_rename_after_document_start(tmp_path, header):
    import yaml

    path = tmp_path / "ci.yml"
    path.write_text(header + SIMPLE_WORKFLOW.lstrip("\n"), encoding="utf-8")
    testkit._act_rename_workflow(path, "devops-ex-abcd1234")
    text = path.read_text(encoding="utf-8")
    data = yaml.safe_load(text)
    assert data["name"] == "devops-ex-abcd1234-ci"
    assert data["jobs"] == yaml.safe_load(SIMPLE_WORKFLOW)["jobs"]
    assert text.startswith(header)


@pytest.mark.parametrize("uses", ["o/r/x@v\n", "o/r@v1\n", "o/r@v1 ", " o/r@v1", "o/r@v 1", "o/r@v1\textra"])
def test_act_remote_action_rejects_whitespace(uses):
    assert testkit._act_remote_action(uses) is None


@pytest.mark.parametrize("uses_yaml", [
    '"o/r/x@v\\n"',
    "|\n          o/r/x@v",
    '"actions/checkout@v4\\n"',
    '"docker/build-push-action@v6 "',
    '""',
])
def test_act_run_refuses_uses_with_whitespace(monkeypatch, tmp_path, uses_yaml):
    world = FakeActWorld(monkeypatch)
    workflow = GUARDED_PUSH.format(guard="if: ${{ !env.ACT }}").replace("docker/build-push-action@v6", uses_yaml)
    with pytest.raises(pytest.fail.Exception) as info:
        testkit.act_run(write_project(tmp_path, workflow))
    assert "khoảng trắng" in str(info.value)
    assert world.processes == []


ENV_OVERRIDE_BASE = """
name: ci
on: push
{workflow_env}jobs:
  build:
    runs-on: ubuntu-latest
{job_env}    steps:
      - run: echo hi
{step_env}      - if: ${{{{ !env.ACT }}}}
        uses: docker/build-push-action@v6
"""


@pytest.mark.parametrize("level,key", [
    ("workflow", "ACT"), ("job", "ACT"), ("step", "ACT"), ("workflow", "act"), ("job", "Act"), ("step", "aCt"),
])
def test_act_run_refuses_act_env_override(monkeypatch, tmp_path, level, key):
    world = FakeActWorld(monkeypatch)
    blocks = {
        "workflow_env": f"env:\n  {key}: ''\n" if level == "workflow" else "",
        "job_env": f"    env:\n      {key}: ''\n" if level == "job" else "",
        "step_env": f"        env:\n          {key}: ''\n" if level == "step" else "",
    }
    with pytest.raises(pytest.fail.Exception) as info:
        testkit.act_run(write_project(tmp_path, ENV_OVERRIDE_BASE.format(**blocks)))
    assert "`ACT`" in str(info.value) and "!env.ACT" in str(info.value)
    assert world.processes == []


def test_act_run_refuses_expression_env(monkeypatch, tmp_path):
    world = FakeActWorld(monkeypatch)
    workflow = ENV_OVERRIDE_BASE.format(workflow_env="", job_env="    env: ${{ fromJSON('{\"ACT\":\"\"}') }}\n", step_env="")
    with pytest.raises(pytest.fail.Exception) as info:
        testkit.act_run(write_project(tmp_path, workflow))
    assert "biểu thức" in str(info.value)
    assert world.processes == []


def test_act_run_allows_other_env(monkeypatch, tmp_path):
    world = FakeActWorld(monkeypatch)
    blocks = {"workflow_env": "env:\n  ACTOR_NAME: x\n", "job_env": "    env:\n      REACT: y\n", "step_env": "        env:\n          ACTION: z\n"}
    testkit.act_run(write_project(tmp_path, ENV_OVERRIDE_BASE.format(**blocks)))
    assert len(world.processes) == 1


@pytest.mark.parametrize("kind,name", [("env", "ACT"), ("env", "act"), ("secrets", "ACT"), ("secrets", "Act"), ("env", "FOO\n"), ("secrets", "X\n")])
def test_act_run_refuses_act_and_bad_names_from_caller(monkeypatch, tmp_path, kind, name):
    world = FakeActWorld(monkeypatch)
    with pytest.raises(pytest.fail.Exception):
        testkit.act_run(write_project(tmp_path, SIMPLE_WORKFLOW), **{kind: {name: "gia-tri-du-dai"}})
    assert world.processes == []


def test_act_run_refuses_event_with_newline(monkeypatch, tmp_path):
    FakeActWorld(monkeypatch)
    with pytest.raises(ValueError):
        testkit.act_run(write_project(tmp_path, SIMPLE_WORKFLOW), event="push\n")


@pytest.mark.parametrize("checkout,expected", [
    ("        with:\n          ref: ${{ github.sha }}\n", "ref"),
    ("        with:\n          repository: x/y\n", "repository"),
    ("        with:\n          token: abc\n          fetch-depth: 0\n", "token"),
    ("        with: x\n", "không phải bảng"),
])
def test_act_run_refuses_checkout_that_act_would_clone(monkeypatch, tmp_path, checkout, expected):
    world = FakeActWorld(monkeypatch)
    project = write_project(tmp_path, SIMPLE_WORKFLOW.replace("      - uses: actions/checkout@v4\n",
                                                              "      - uses: actions/checkout@v4\n" + checkout))
    with pytest.raises(pytest.fail.Exception) as info:
        testkit.act_run(project)
    assert "actions/checkout" in str(info.value) and expected in str(info.value)
    assert world.processes == []


def test_act_run_allows_safe_checkout_inputs(monkeypatch, tmp_path):
    world = FakeActWorld(monkeypatch)
    checkout = "        with:\n          fetch-depth: 0\n          persist-credentials: false\n"
    project = write_project(tmp_path, SIMPLE_WORKFLOW.replace("      - uses: actions/checkout@v4\n",
                                                              "      - uses: actions/checkout@v4\n" + checkout))
    testkit.act_run(project)
    argv = world.processes[0].args
    assert flag(argv, "--local-repository").startswith("actions/checkout@v4=")


def act_result(text: str) -> subprocess.CompletedProcess:
    return subprocess.CompletedProcess(["act"], 1, text, "")


SETUP_STEPS = ("Cài uv", "Cài Python và dependency")


def test_act_failed_on_network_in_setup_step():
    text = (
        "[test] ⭐ Run Main Cài uv\n"
        "[test]   | Tải lỗi: ENOTFOUND\n"
        "[test]   ❌  Failure - Main Cài uv [1.2s]\n"
        "[test] 🏁  Job failed\n"
    )
    assert testkit.act_failed_on_network(act_result(text), SETUP_STEPS) is True


def test_act_failed_on_network_uv_dns_error():
    text = (
        "[test] ⭐ Run Main Cài Python và dependency\n"
        "[test]   | error: Failed to fetch: `https://pypi.org/simple/fastapi/`\n"
        "[test]   |   Caused by: dns error: failed to lookup address information\n"
        "[test]   ❌  Failure - Main Cài Python và dependency [3.0s]\n"
    )
    assert testkit.act_failed_on_network(act_result(text), SETUP_STEPS) is True


@pytest.mark.parametrize("text", [
    "[test] ⭐ Run Main Test\n[test]   | ConnectionError: Could not connect to redis\n[test]   ❌  Failure - Main Test [1s]\n",
    "[test] ⭐ Run Main Cài uv\n[test]   | /tmp/uv.tar.gz: FAILED\n[test]   ❌  Failure - Main Cài uv [1s]\n",
    "[test] ⭐ Run Main Cài uv\n[test]   | Tải lỗi: ENOTFOUND\n[test]   ✅  Success - Main Cài uv [1s]\n"
    "[test] ⭐ Run Main Test\n[test]   | 1 failed\n[test]   ❌  Failure - Main Test [1s]\n",
    "[test] ⭐ Run Main Cài Python và dependency\n[test]   | dns error\n[test]   | Downloaded fastapi\n"
    "[test]   | error: No solution found when resolving dependencies\n[test]   ❌  Failure - Main Cài Python và dependency [1s]\n",
    "[a] ⭐ Run Main Cài uv\n[b]   | ENOTFOUND\n[a]   ❌  Failure - Main Cài uv [1s]\n",
])
def test_act_failed_on_network_only_for_setup_step_network_errors(text):
    assert testkit.act_failed_on_network(act_result(text), SETUP_STEPS) is False


OFFLINE_WORKFLOW = """
name: offline
on: push
jobs:
  offline:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Không có Internet
        run: |
          node -e 'fetch("https://pypi.org/simple/").then(() => process.exit(1), () => console.log("devops-ex-output internet=none"))'
      - name: Python và wheel từ image
        run: |
          uv venv --python 3.12.13 "$RUNNER_TEMP/venv"
          uv pip install --python "$RUNNER_TEMP/venv/bin/python" -r requirements.txt
          "$RUNNER_TEMP/venv/bin/python" -c 'import fastapi, yaml; print("devops-ex-output imported=" + fastapi.__version__)'
"""


@pytest.mark.skipif(os.environ.get("DEVOPS_ACT_OFFLINE_PROOF") != "1", reason="Chỉ chạy khi DEVOPS_ACT_OFFLINE_PROOF=1")
def test_act_runner_works_without_internet(monkeypatch, tmp_path):
    real = testkit._docker

    def internal(*args, timeout=60):
        if args[:2] == ("network", "create") and any(str(a).startswith(f"{testkit.ACT_RUN_LABEL}=") for a in args):
            args = ("network", "create", "--internal", *args[2:])
        return real(*args, timeout=timeout)

    monkeypatch.setattr(testkit, "_docker", internal)
    project = write_project(tmp_path, OFFLINE_WORKFLOW,
                            {"requirements.txt": (testkit.ROOT / "setup" / "act-runner" / "requirements-ci.txt").read_text(encoding="utf-8")})
    result = testkit.act_run(project, timeout=300)
    assert testkit.act_job_results(result) == {"offline": True}, result.stdout[-3000:]
    assert testkit.act_outputs(result)["offline"] == {"internet": "none", "imported": "0.143.1"}
    assert "Downloading" not in result.stdout


TOFU_REQUIRED = pytest.mark.skipif(
    shutil.which("tofu") is None or testkit.sandbox_ready() is not None, reason="Cần tofu và bwrap dùng được")
TOFU_PROVIDER = f"""
terraform {{
  required_providers {{
    aws = {{ source = "hashicorp/aws", version = "{testkit.TOFU_AWS_PROVIDER}" }}
  }}
}}
variable "prefix" {{
  type = string
}}
"""
CALLER_IDENTITY = (
    '<GetCallerIdentityResponse xmlns="https://sts.amazonaws.com/doc/2011-06-15/"><GetCallerIdentityResult>'
    "<Arn>arn:aws:iam::123456789012:user/devops-ex</Arn><UserId>AIDADEVOPSEX</UserId><Account>123456789012</Account>"
    "</GetCallerIdentityResult><ResponseMetadata><RequestId>devops-ex</RequestId></ResponseMetadata></GetCallerIdentityResponse>"
)


@pytest.fixture
def recorder():
    """Endpoint AWS giả trên loopback: ghi lại mọi request, trả lời như STS GetCallerIdentity."""
    import threading
    from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

    seen: list[str] = []

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            body = self.rfile.read(int(self.headers.get("Content-Length") or 0)).decode("utf-8", "replace")
            seen.append(f"{self.headers.get('Host')} {body}")
            data = CALLER_IDENTITY.encode()
            self.send_response(200)
            self.send_header("Content-Type", "text/xml")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def log_message(self, *args):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_address[1]}", seen
    finally:
        server.shutdown()
        server.server_close()


def test_tofu_env_isolated(monkeypatch, tmp_path):
    for key, value in {"AWS_PROFILE": "prod", "AWS_ENDPOINT_URL": "https://real.example", "TF_CLI_CONFIG_FILE": "/home/x/.terraformrc",
                       "TF_PLUGIN_CACHE_DIR": "/elsewhere", "AWS_SESSION_TOKEN": "secret", "HTTPS_PROXY": "http://corp:3128"}.items():
        monkeypatch.setenv(key, value)
    monkeypatch.setenv("LOCALSTACK_DEVOPS_PORT", "24566")
    home = tmp_path / "home"
    env = testkit.tofu_env(home, prefix="devops-ex-abc12345")
    for key, value in {"AWS_ACCESS_KEY_ID": "test", "AWS_SECRET_ACCESS_KEY": "test", "AWS_REGION": "us-east-1",
                       "AWS_CONFIG_FILE": "/dev/null", "AWS_SHARED_CREDENTIALS_FILE": "/dev/null", "AWS_EC2_METADATA_DISABLED": "true",
                       "TF_IN_AUTOMATION": "1", "TF_INPUT": "0", "TF_VAR_prefix": "devops-ex-abc12345", "HOME": str(home),
                       "AWS_ENDPOINT_URL": "http://127.0.0.1:24566"}.items():
        assert env[key] == value, key
    assert not {"AWS_PROFILE", "AWS_SESSION_TOKEN", "TF_PLUGIN_CACHE_DIR"} & env.keys()
    config = Path(env["TF_CLI_CONFIG_FILE"])
    assert config.is_relative_to(home) and config.is_file()
    text = config.read_text(encoding="utf-8")
    assert "disable_checkpoint = true" in text and "filesystem_mirror" in text and str(testkit.tofu_plugin_dir()) in text
    assert "plugin_cache_dir" not in text and "direct" not in text
    proxy = env["HTTPS_PROXY"]
    assert proxy.startswith("http://127.0.0.1:") and env["HTTP_PROXY"] == env["https_proxy"] == env["http_proxy"] == proxy
    assert env["NO_PROXY"] == env["no_proxy"] and "127.0.0.1" in env["NO_PROXY"].split(",")
    assert str(Path.home()) not in "".join(v for k, v in env.items() if k != "TF_CLI_CONFIG_FILE").replace(str(testkit.tofu_plugin_dir()), "")


def test_tofu_env_fetch_mode_uses_shared_cache(tmp_path):
    env = testkit.tofu_env(tmp_path, prefix="devops-ex-abc12345", fetch=True)
    assert env["TF_PLUGIN_CACHE_DIR"] == str(testkit.tofu_plugin_dir())
    text = Path(env["TF_CLI_CONFIG_FILE"]).read_text(encoding="utf-8")
    assert f'plugin_cache_dir = "{testkit.tofu_plugin_dir()}"' in text and "filesystem_mirror" not in text
    assert "HTTPS_PROXY" not in env and env["AWS_ENDPOINT_URL"].startswith("http://127.0.0.1:")


def test_tofu_plugin_dir_follows_xdg(monkeypatch, tmp_path):
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path))
    assert testkit.tofu_plugin_dir() == tmp_path / "devops-track" / "tofu-plugins"


def test_tofu_blackhole_proxy_refuses_connections():
    import socket
    import urllib.parse

    url = urllib.parse.urlsplit(testkit.tofu_env(Path(testkit.tempfile.mkdtemp()), prefix="devops-ex-x")["HTTPS_PROXY"])
    with pytest.raises(ConnectionRefusedError):
        socket.create_connection((url.hostname, url.port), timeout=2)


def test_tofu_lab_prefix_is_unique_and_scoped():
    first, second = testkit.TofuLab(), testkit.TofuLab()
    assert first.prefix != second.prefix
    assert all(re.fullmatch(r"devops-ex-[0-9a-f]{8}", lab.prefix) for lab in (first, second))


def test_tofu_lab_refuses_use_outside_with():
    with pytest.raises(RuntimeError):
        testkit.TofuLab().init()


def test_localstack_devops_separate_from_de(monkeypatch):
    import yaml

    data = yaml.safe_load((testkit.ROOT / "setup" / "docker-compose.yml").read_text(encoding="utf-8"))
    de, devops = data["services"]["localstack"], data["services"]["localstack-devops"]
    assert devops["image"] == de["image"] == "localstack/localstack:4.4.0"
    assert devops["profiles"] == ["devops"] and "devops" not in de["profiles"]
    assert devops["ports"] == ["127.0.0.1:${LOCALSTACK_DEVOPS_PORT:-14566}:4566"]
    assert devops["cpuset"] == "${DEVOPS_CPUSET:-}"
    assert {"s3", "iam", "sts", "dynamodb", "kms"} <= set(devops["environment"]["SERVICES"].split(","))
    volume = devops["volumes"][0].split(":")[0]
    assert volume != "localstack_data" and data["volumes"][volume]["name"] == "devops-track-localstack-data"
    assert de["volumes"] == ["localstack_data:/var/lib/localstack"] and data["volumes"]["localstack_data"] is None
    assert "healthcheck" in devops
    assert testkit.SERVICES["localstack-devops"] == ("LOCALSTACK_DEVOPS_HOST", "localhost", "LOCALSTACK_DEVOPS_PORT", 14566)
    monkeypatch.delenv("LOCALSTACK_DEVOPS_PORT", raising=False)
    monkeypatch.delenv("LOCALSTACK_PORT", raising=False)
    assert testkit.localstack_devops_endpoint() == "http://127.0.0.1:14566"
    assert testkit._port("localstack") != testkit._port("localstack-devops")


def test_localstack_sweep_refuses_de_port(monkeypatch):
    monkeypatch.setenv("LOCALSTACK_PORT", "4566")
    monkeypatch.setenv("LOCALSTACK_DEVOPS_PORT", "4566")
    import boto3

    monkeypatch.setattr(boto3, "client", lambda *a, **k: pytest.fail("không được gọi boto3 khi cổng trùng DE"))
    with pytest.raises(RuntimeError, match="localstack"):
        testkit.localstack_sweep("devops-ex-abc12345")


@pytest.mark.parametrize("prefix", ["", "devops-ex-", "devops-ex", "prod-", "devops-ex-ab", "devops-ex-abc1234567",
                                    "devops-ex-ABC12345", "devops-ex-zzzzzzzz", "devops-ex-abc12345-x"])
def test_localstack_sweep_refuses_broad_prefix(prefix):
    with pytest.raises(ValueError):
        testkit.localstack_sweep(prefix)


def test_localstack_sweep_targets_devops_endpoint_only(monkeypatch):
    monkeypatch.setenv("LOCALSTACK_DEVOPS_PORT", "24566")
    monkeypatch.setenv("LOCALSTACK_PORT", "4566")
    import boto3

    endpoints = []

    class Empty:
        def get_paginator(self, name):
            return self

        def paginate(self, **kwargs):
            return []

        def list_event_buses(self, **kwargs):
            return {"EventBuses": []}

        def list_buckets(self, **kwargs):
            return {"Buckets": [{"Name": "devops-ex-other999-b"}, {"Name": "de-data"}]}

    def client(service, **kwargs):
        endpoints.append((service, kwargs["endpoint_url"]))
        return Empty()

    monkeypatch.setattr(boto3, "client", client)
    assert testkit.localstack_sweep("devops-ex-abc12345") == []
    assert endpoints and {e for _, e in endpoints} == {"http://127.0.0.1:24566"}


def test_require_localstack_devops_skips_on_de_port(monkeypatch):
    monkeypatch.setenv("LOCALSTACK_PORT", "4566")
    monkeypatch.setenv("LOCALSTACK_DEVOPS_PORT", "4566")
    with pytest.raises(pytest.skip.Exception, match="LOCALSTACK_DEVOPS_PORT"):
        testkit.Exercise.require_localstack_devops()


def test_require_localstack_devops_skips_when_down(monkeypatch):
    monkeypatch.setattr(testkit, "service_up", lambda name, timeout=0.5: False)
    with pytest.raises(pytest.skip.Exception, match="--profile devops up -d --wait localstack-devops"):
        testkit.Exercise.require_localstack_devops()


def test_require_localstack_devops_rejects_other_server(monkeypatch):
    monkeypatch.setattr(testkit, "service_up", lambda name, timeout=0.5: True)
    health = {"services": {"s3": "available", "dynamodb": "disabled"}, "edition": "community"}
    monkeypatch.setattr(testkit, "_localstack_health", lambda endpoint: health)
    with pytest.raises(pytest.skip.Exception, match="không phải localstack-devops"):
        testkit.Exercise.require_localstack_devops()


@pytest.mark.parametrize("text,expected", [
    ("could not connect to registry.opentofu.org: failed to request discovery document", True),
    ('Get "https://github.com/x": dial tcp: lookup github.com: no such host', True),
    ("proxyconnect tcp: dial tcp 127.0.0.1:9: connect: connection refused", True),
    ("net/http: TLS handshake timeout", True),
    ("Error: Unsupported argument\n  on main.tf line 3", False),
    ("no available releases match the given constraints >= 99.0.0", False),
])
def test_tofu_network_error_detection(text, expected):
    assert testkit.tofu_failed_on_network(text) is expected


@TOFU_REQUIRED
def test_tofu_lab_ignores_user_terraformrc(tmp_path, recorder):
    endpoint, _ = recorder
    with testkit.TofuLab(endpoint=endpoint) as lab:
        for where in (lab.home, lab.workdir):
            (where / ".terraformrc").write_text("this is { not valid\n", encoding="utf-8")
        clean = lab.run("version")
        assert "problems with the CLI configuration" not in clean.stdout + clean.stderr
        control = testkit.run_sandboxed(["tofu", "version"], writable=[lab.home], cwd=lab.home, env={})
        assert "problems with the CLI configuration" in control.stdout + control.stderr, "Phép đối chứng phải đọc được .terraformrc"


@TOFU_REQUIRED
def test_tofu_provider_without_endpoint_cannot_reach_real_aws(recorder):
    endpoint, seen = recorder
    with testkit.TofuLab(endpoint=endpoint) as lab:
        lab.write("main.tf", TOFU_PROVIDER + """
provider "aws" {}
data "aws_caller_identity" "me" {}
output "account" { value = data.aws_caller_identity.me.account_id }
output "prefix" { value = var.prefix }
""")
        lab.init()
        lab.apply()
        assert lab.output() == {"account": "123456789012", "prefix": lab.prefix}
        assert any("GetCallerIdentity" in request for request in seen)
        count = len(seen)
        lab.write("main.tf", TOFU_PROVIDER + """
provider "aws" {
  max_retries = 1
  endpoints {
    sts = "https://sts.us-east-1.amazonaws.com"
  }
}
data "aws_caller_identity" "me" {}
""")
        result = lab.plan(check=False)
        assert result.returncode != 0
        assert "proxyconnect" in result.stdout + result.stderr
        assert len(seen) == count
        lab.write("main.tf", TOFU_PROVIDER + 'provider "aws" {}\n')


@TOFU_REQUIRED
def test_tofu_init_offline_after_first_fetch(monkeypatch, recorder):
    endpoint, _ = recorder
    config = TOFU_PROVIDER + 'provider "aws" {}\n'
    with testkit.TofuLab(endpoint=endpoint) as first:
        first.write("main.tf", config)
        first.init()
    monkeypatch.setattr(testkit, "tofu_fetch_providers", lambda: pytest.fail("provider đã có trong mirror, không được tải lại"))
    with testkit.TofuLab(endpoint=endpoint) as second:
        second.write("main.tf", config)
        result = second.init()
        assert f"Installed hashicorp/aws v{testkit.TOFU_AWS_PROVIDER}" in result.stdout
        assert second.env["HTTPS_PROXY"].startswith("http://127.0.0.1:")
        assert (second.workdir / ".terraform" / "providers").is_dir()


@TOFU_REQUIRED
def test_tofu_init_skips_when_provider_missing_and_offline(monkeypatch, tmp_path, recorder):
    endpoint, _ = recorder
    monkeypatch.setattr(testkit, "tofu_plugin_dir", lambda: tmp_path / "empty-plugins")
    original = testkit._tofu_fetch_env

    def offline(home):
        env = original(home)
        proxy = testkit.tofu_env(home, prefix="devops-ex-00000000", endpoint=endpoint)["HTTPS_PROXY"]
        return {**env, "HTTPS_PROXY": proxy, "https_proxy": proxy, "HTTP_PROXY": proxy, "http_proxy": proxy}

    monkeypatch.setattr(testkit, "_tofu_fetch_env", offline)
    with testkit.TofuLab(endpoint=endpoint) as lab:
        lab.write("main.tf", TOFU_PROVIDER + 'provider "aws" {}\n')
        with pytest.raises(pytest.skip.Exception, match="cần mạng"):
            lab.init()
    assert not any((tmp_path / "empty-plugins").rglob("terraform-provider-aws*"))


@TOFU_REQUIRED
def test_tofu_loose_constraint_resolves_to_pinned_provider(recorder):
    endpoint, _ = recorder
    with testkit.TofuLab(endpoint=endpoint) as lab:
        lab.write("main.tf", TOFU_PROVIDER.replace(f'version = "{testkit.TOFU_AWS_PROVIDER}"', 'version = "~> 6.0"')
                  + 'provider "aws" {}\n')
        lab.init()
        assert f'version     = "{testkit.TOFU_AWS_PROVIDER}"' in (lab.workdir / ".terraform.lock.hcl").read_text(encoding="utf-8")


@TOFU_REQUIRED
def test_tofu_other_provider_version_fails_clearly_without_download(monkeypatch, recorder):
    endpoint, _ = recorder
    monkeypatch.setattr(testkit, "tofu_fetch_providers", lambda: pytest.fail("không được tải provider khác"))
    with testkit.TofuLab(endpoint=endpoint) as lab:
        lab.write("main.tf", TOFU_PROVIDER.replace(f'version = "{testkit.TOFU_AWS_PROVIDER}"', 'version = "= 6.20.0"')
                  + 'provider "aws" {}\n')
        with pytest.raises(pytest.fail.Exception, match=rf"{re.escape(testkit.TOFU_AWS_PROVIDER)}.*LocalStack 4\.4\.0"):
            lab.init()
    assert not (testkit.tofu_plugin_dir() / "registry.opentofu.org" / "hashicorp" / "aws" / "6.20.0").exists()


def test_tofu_lock_version_check(tmp_path):
    lock = tmp_path / ".terraform.lock.hcl"
    lock.write_text('provider "registry.opentofu.org/hashicorp/aws" {\n  version     = "6.20.0"\n  constraints = ">= 6.0"\n}\n')
    assert testkit._tofu_locked_versions(lock) == {"registry.opentofu.org/hashicorp/aws": "6.20.0"}


@pytest.mark.parametrize("snippet", [
    'provider "aws" {\n  http_proxy = "http://corp:3128"\n}\n',
    'provider "aws" {\n  https_proxy = "http://corp:3128"\n}\n',
    'provider "aws" {\n  no_proxy = "*"\n}\n',
    'terraform {\n  backend "s3" {\n    custom_ca_bundle = "/x.pem"\n  }\n}\n',
    '{"provider": {"aws": {"no_proxy": "*"}}}',
    'provider "aws" { no_proxy = "*" }\n',
    'terraform { backend "s3" { custom_ca_bundle = "/x.pem" } }\n',
    'provider "aws" { region = "us-east-1"; https_proxy = "http://corp:3128" }\n',
    'locals { a = { b = 1, http_proxy = "x" } }\n',
    'provider "aws" {\n  no_proxy\t   =   "*"\n}\n',
    'provider "aws" { endpoints { s3 = "http://x" } } /* c */ provider "aws" { alias = "b"; no_proxy = "*" }\n',
    'provider "aws" {\n region = "/*"\n no_proxy = "*"\n x = "*/"\n}\n',
    'locals {\n  a = <<-EOT\n    /*\n  EOT\n}\nprovider "aws" {\n  https_proxy = "http://corp:3128"\n}\nlocals {\n  b = <<-EOT\n    */\n  EOT\n}\n',
    '{\n  "terraform": {\n    "backend": {\n      "s3": {\n        "custom_ca_bundle" :  "/x.pem"\n      }\n    }\n  }\n}\n',
])
def test_tofu_refuses_proxy_overrides(tmp_path, snippet):
    name = "main.tf.json" if snippet.startswith("{") else "main.tf"
    (tmp_path / "modules" / "x").mkdir(parents=True)
    (tmp_path / "modules" / "x" / name).write_text(snippet, encoding="utf-8")
    problems = testkit.tofu_config_problems(tmp_path)
    assert problems and "modules/x/" in problems[0] and "proxy" in problems[0].lower() + "proxy"


@pytest.mark.parametrize("text", [
    '# no_proxy = "*"\nprovider "aws" {}\n',
    'provider "aws" {} // https_proxy = "x"\n',
    '/* custom_ca_bundle = "x" */\nprovider "aws" {}\n',
])
def test_tofu_refuses_forbidden_assignment_even_in_comments(tmp_path, text):
    (tmp_path / "main.tf").write_text(text, encoding="utf-8")
    problems = testkit.tofu_config_problems(tmp_path)
    assert len(problems) == 1 and "kể cả khi nằm trong chú thích" in problems[0]


@pytest.mark.parametrize("text", [
    '# đặt no_proxy cho LocalStack là không cần\nprovider "aws" {}\n',
    '// không dùng https_proxy hay http_proxy trong lab\nprovider "aws" {}\n',
    'variable "no_proxy_note" {}\noutput "x" { value = var.no_proxy_note }\n',
])
def test_tofu_allows_forbidden_words_without_assignment(tmp_path, text):
    (tmp_path / "main.tf").write_text(text, encoding="utf-8")
    assert testkit.tofu_config_problems(tmp_path) == []


@pytest.mark.parametrize("name", ["main.tf.json", "main.tofu.json"])
def test_tofu_refuses_unicode_escaped_json_key(tmp_path, name):
    (tmp_path / name).write_text('{"provider": {"aws": {"no\\u005fproxy": "*"}}}', encoding="utf-8")
    problems = testkit.tofu_config_problems(tmp_path)
    assert problems and all(p.startswith(f"{name}:") for p in problems)
    assert any("\\u" in p and "escape" in p for p in problems)
    assert any("khoá JSON" in p and "no_proxy" in p for p in problems)


def test_tofu_refuses_unicode_escape_in_json_value_only(tmp_path):
    (tmp_path / "main.tf.json").write_text('{"provider": {"aws": {"region": "us-east-\\u0031"}}}', encoding="utf-8")
    problems = testkit.tofu_config_problems(tmp_path)
    assert len(problems) == 1 and problems[0].startswith("main.tf.json:1:") and "\\u" in problems[0]


def test_tofu_allows_escaped_slash_key_that_tofu_itself_rejects(tmp_path):
    (tmp_path / "main.tf.json").write_text('{"provider": {"aws": {"no_proxy\\/": "*"}}}', encoding="utf-8")
    assert testkit.tofu_config_problems(tmp_path) == []


@pytest.mark.parametrize("text", [
    '{"terraform": [{"backend": {"s3": [{"bucket": "b", "Custom_CA_Bundle": "/x.pem"}]}}]}',
    '{"provider": {"aws": [{"region": "x"}, {"alias": "b", "assume_role": {"x": {"y": {"HTTPS_PROXY": 1}}}}]}}',
])
def test_tofu_refuses_forbidden_json_key_at_depth(tmp_path, text):
    (tmp_path / "modules" / "m").mkdir(parents=True)
    (tmp_path / "modules" / "m" / "main.tf.json").write_text(text, encoding="utf-8")
    problems = testkit.tofu_config_problems(tmp_path)
    assert any(p.startswith("modules/m/main.tf.json:") and "khoá JSON" in p for p in problems)


def test_tofu_refuses_invalid_json_config(tmp_path):
    (tmp_path / "main.tf.json").write_text('{"provider": {"aws": {"region": "x",}}}', encoding="utf-8")
    problems = testkit.tofu_config_problems(tmp_path)
    assert len(problems) == 1 and "JSON không hợp lệ" in problems[0]


def test_tofu_allows_clean_json_config(tmp_path):
    (tmp_path / "main.tf.json").write_text(json.dumps({
        "terraform": {"required_providers": {"aws": {"source": "hashicorp/aws", "version": "~> 6.0"}}},
        "provider": {"aws": {"region": "us-east-1", "endpoints": [{"s3": "http://localhost:4566/"}]}},
        "variable": {"no_proxy_note": {"default": "không dùng proxy"}},
    }, ensure_ascii=False), encoding="utf-8")
    assert testkit.tofu_config_problems(tmp_path) == []


def test_tofu_refuses_deeply_nested_json_cleanly(tmp_path):
    (tmp_path / "main.tf.json").write_text("[" * 100_000 + "]" * 100_000, encoding="utf-8")
    problems = testkit.tofu_config_problems(tmp_path)
    assert len(problems) == 1 and problems[0].startswith("main.tf.json:") and "JSON lồng quá sâu" in problems[0]


@pytest.mark.parametrize("name", ["x.tftest.hcl", "x.tofutest.hcl"])
def test_tofu_refuses_proxy_override_in_test_file(tmp_path, name):
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / name).write_text('provider "aws" { no_proxy = "*" }\n', encoding="utf-8")
    problems = testkit.tofu_config_problems(tmp_path)
    assert len(problems) == 1 and problems[0].startswith(f"tests/{name}:1:")


@pytest.mark.parametrize("name", ["x.tftest.json", "x.tofutest.json"])
def test_tofu_applies_json_rules_to_json_test_file(tmp_path, name):
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / name).write_text('{"provider": {"aws": {"no\\u005fproxy": "*"}}}', encoding="utf-8")
    problems = testkit.tofu_config_problems(tmp_path)
    assert any("escape" in p for p in problems) and any("khoá JSON" in p and "no_proxy" in p for p in problems)


def test_tofu_forbidden_line_number_survives_block_comment(tmp_path):
    (tmp_path / "main.tf").write_text('/* a\nb\n*/\nprovider "aws" { no_proxy = "*" }\n', encoding="utf-8")
    assert testkit.tofu_config_problems(tmp_path)[0].startswith("main.tf:4:")


@SANDBOX_REQUIRED
def test_sandbox_readonly_paths_visible_not_writable(tmp_path):
    shared = tmp_path / "shared"
    shared.mkdir()
    (shared / "data.txt").write_text("giữ", encoding="utf-8")
    work = tmp_path / "work"
    work.mkdir()
    result = testkit.run_sandboxed(["sh", "-c", f"cat {shared}/data.txt; touch {shared}/new && echo WROTE"],
                                   writable=[work], readonly=[shared], cwd=work, env={})
    assert result.stdout.startswith("giữ") and "WROTE" not in result.stdout
    assert "Read-only file system" in result.stderr
    assert not (shared / "new").exists()
    argv = testkit.sandbox_command(["true"], writable=[work], readonly=[shared], cwd=work, env={})
    assert argv.index(str(shared.resolve())) > argv.index("/run")


@TOFU_REQUIRED
def test_tofu_learner_run_cannot_write_mirror_under_tmp(monkeypatch, tmp_path, recorder):
    endpoint, _ = recorder
    real = testkit.tofu_plugin_dir()
    if not testkit.tofu_providers_present():
        pytest.skip("Cần provider đã có trong mirror chung")
    mirror = tmp_path / "mirror"
    for source, version in testkit.TOFU_PROVIDERS.items():
        target = mirror / testkit.TOFU_REGISTRY / source / version
        target.mkdir(parents=True)
        platform = testkit._tofu_platform()
        (target / platform).symlink_to(real / testkit.TOFU_REGISTRY / source / version / platform)
    monkeypatch.setattr(testkit, "tofu_plugin_dir", lambda: mirror)
    with testkit.TofuLab(endpoint=endpoint) as lab:
        lab.write("main.tf", f"""
resource "terraform_data" "probe" {{
  provisioner "local-exec" {{
    command = "ls {mirror}/{testkit.TOFU_REGISTRY} && touch {mirror}/pwned"
  }}
}}
""")
        lab.init()
        result = lab.apply(check=False)
        assert result.returncode != 0
        assert "Read-only file system" in result.stdout + result.stderr
    assert not (mirror / "pwned").exists()


def test_tofu_allows_normal_config(tmp_path):
    (tmp_path / "main.tf").write_text('# http_proxy chỉ là chữ\nprovider "aws" {\n  region = "us-east-1"\n}\nvariable "no_proxy_note" {}\n')
    assert testkit.tofu_config_problems(tmp_path) == []


@TOFU_REQUIRED
def test_tofu_lab_refuses_proxy_override_before_running(recorder):
    endpoint, seen = recorder
    with testkit.TofuLab(endpoint=endpoint) as lab:
        lab.write("main.tf", TOFU_PROVIDER + 'provider "aws" {\n  no_proxy = "*"\n}\n')
        with pytest.raises(pytest.fail.Exception, match="no_proxy"):
            lab.init()
    assert seen == []


@TOFU_REQUIRED
def test_tofu_lab_destroy_failure_fails_passing_test(monkeypatch, recorder):
    endpoint, _ = recorder
    original = testkit.TofuLab._execute

    def broken_destroy(self, args, env, writable, timeout):
        if args[0] == "destroy":
            return subprocess.CompletedProcess(["tofu", *args], 1, "", "Error: destroy hỏng")
        return original(self, args, env, writable, timeout)

    monkeypatch.setattr(testkit.TofuLab, "_execute", broken_destroy)
    with pytest.raises(pytest.fail.Exception, match="destroy hỏng"):
        with pytest.warns(UserWarning, match="destroy"):
            with testkit.TofuLab(endpoint=endpoint) as lab:
                lab.write("main.tf", TOFU_PROVIDER + 'provider "aws" {}\n')
                lab.init()
    with pytest.raises(RuntimeError, match="lỗi gốc"):
        with pytest.warns(UserWarning, match="destroy hỏng"):
            with testkit.TofuLab(endpoint=endpoint) as lab:
                lab.write("main.tf", TOFU_PROVIDER + 'provider "aws" {}\n')
                lab.init()
                raise RuntimeError("lỗi gốc")


@SANDBOX_REQUIRED
def test_sandbox_resolves_dns(tmp_path):
    import socket

    try:
        socket.getaddrinfo("registry.opentofu.org", 443)
    except OSError:
        pytest.skip("Máy không có mạng hay DNS")
    code = "import socket; print(socket.getaddrinfo('registry.opentofu.org', 443)[0][4][0])"
    result = testkit.run_sandboxed([sys.executable, "-c", code], writable=[tmp_path], cwd=tmp_path, env={})
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip()


def test_sandbox_binds_only_resolv_conf_file(monkeypatch, tmp_path):
    flags = testkit._base_flags("/usr/bin/bwrap")
    target = Path("/etc/resolv.conf").resolve()
    if target.is_relative_to("/run"):
        index = flags.index("--tmpfs", flags.index("/proc"))
        assert flags[index:index + 4] == ["--tmpfs", "/tmp", "--tmpfs", "/run"]
        assert ["--ro-bind", str(target), str(target)] == flags[flags.index(str(target)) - 1:flags.index(str(target)) + 2]
        assert flags.index(str(target)) > flags.index("/run")
    assert not any(f == "/run/systemd/resolve" for f in flags)


@pytest.mark.skipif(os.environ.get("DEVOPS_TOFU_FETCH_PROOF") != "1", reason="Chỉ chạy khi DEVOPS_TOFU_FETCH_PROOF=1 (tải ~150 MB)")
@TOFU_REQUIRED
def test_tofu_fetch_into_empty_mirror_then_offline(monkeypatch, tmp_path, recorder):
    endpoint, _ = recorder
    mirror = tmp_path / "mirror"
    monkeypatch.setattr(testkit, "tofu_plugin_dir", lambda: mirror)
    with testkit.TofuLab(endpoint=endpoint) as lab:
        lab.write("main.tf", TOFU_PROVIDER.replace(f'version = "{testkit.TOFU_AWS_PROVIDER}"', 'version = "~> 6.0"')
                  + 'provider "aws" {}\n')
        result = lab.init()
        assert f"Installed hashicorp/aws v{testkit.TOFU_AWS_PROVIDER}" in result.stdout
    versions = sorted(p.name for p in (mirror / "registry.opentofu.org" / "hashicorp" / "aws").iterdir())
    assert versions == [testkit.TOFU_AWS_PROVIDER]
    monkeypatch.setattr(testkit, "tofu_fetch_providers", lambda: pytest.fail("không được tải lại"))
    with testkit.TofuLab(endpoint=endpoint) as lab:
        lab.write("main.tf", TOFU_PROVIDER + 'provider "aws" {}\n')
        assert f"Installed hashicorp/aws v{testkit.TOFU_AWS_PROVIDER}" in lab.init().stdout


def test_localstack_sweep_never_matches_longer_prefix(monkeypatch):
    import boto3

    deleted = []

    class Fake:
        def get_paginator(self, name):
            return self

        def paginate(self, **kwargs):
            return []

        def list_event_buses(self, **kwargs):
            return {"EventBuses": []}

        def list_buckets(self, **kwargs):
            return {"Buckets": [{"Name": n} for n in ("devops-ex-abc123456-x", "devops-ex-abc12345x", "devops-ex-abc12345-data",
                                                      "devops-ex-abc12345")]}

        def delete_bucket(self, Bucket):
            deleted.append(Bucket)

    monkeypatch.setattr(boto3, "client", lambda service, **kwargs: Fake())
    assert testkit.localstack_sweep("devops-ex-abc12345") == ["s3:devops-ex-abc12345-data", "s3:devops-ex-abc12345"]
    assert deleted == ["devops-ex-abc12345-data", "devops-ex-abc12345"]


@pytest.mark.parametrize("name,owned", [
    ("devops-ex-abc12345", True), ("devops-ex-abc12345-x", True), ("/devops-ex-abc12345/p", True), ("devops-ex-abc12345/p", True),
    ("alias/devops-ex-abc12345-k", True), ("devops-ex-abc123456", False), ("devops-ex-abc12345x", False), ("/other/devops-ex-abc12345", False),
])
def test_localstack_owned_names(name, owned):
    assert testkit._owned_by(name, "devops-ex-abc12345") is owned


@TOFU_REQUIRED
def test_tofu_init_real_error_fails_not_skips(recorder):
    endpoint, _ = recorder
    with testkit.TofuLab(endpoint=endpoint) as lab:
        lab.write("main.tf", TOFU_PROVIDER + 'provider "aws" {\n  no_such_argument = 1\n}\nresource "x" {\n')
        with pytest.raises(pytest.fail.Exception):
            lab.init()


LOCALSTACK_REQUIRED = pytest.mark.skipif(
    shutil.which("tofu") is None or not testkit.service_up("localstack-devops"), reason="Cần tofu và localstack-devops đang chạy")
BUCKET_CONFIG = TOFU_PROVIDER + """
provider "aws" {}
resource "aws_s3_bucket" "data" {
  bucket = "${var.prefix}-data"
}
output "bucket" {
  value = aws_s3_bucket.data.bucket
}
"""


def localstack_client(service):
    import boto3

    return boto3.client(service, endpoint_url=testkit.localstack_devops_endpoint(), region_name="us-east-1",
                        aws_access_key_id="test", aws_secret_access_key="test")


def buckets_with(prefix):
    return [b["Name"] for b in localstack_client("s3").list_buckets()["Buckets"] if b["Name"].startswith(prefix)]


@LOCALSTACK_REQUIRED
def test_tofu_lab_apply_and_destroy_bucket():
    with testkit.TofuLab() as lab:
        lab.write("main.tf", BUCKET_CONFIG)
        lab.init()
        lab.apply()
        assert lab.output("bucket") == f"{lab.prefix}-data"
        assert buckets_with(lab.prefix) == [f"{lab.prefix}-data"]
        assert "aws_s3_bucket.data" in lab.state("list").stdout.split()
    assert lab.destroy_result is not None and lab.destroy_result.returncode == 0
    assert lab.swept == []
    assert buckets_with(lab.prefix) == []
    assert not lab.root.exists()


@LOCALSTACK_REQUIRED
def test_tofu_lab_destroys_on_error():
    lab = testkit.TofuLab()
    with pytest.raises(RuntimeError, match="giữa chừng"):
        with lab:
            lab.write("main.tf", BUCKET_CONFIG)
            lab.init()
            lab.apply()
            assert buckets_with(lab.prefix) == [f"{lab.prefix}-data"]
            raise RuntimeError("lỗi giữa chừng")
    assert lab.destroy_result.returncode == 0
    assert buckets_with(lab.prefix) == []


@LOCALSTACK_REQUIRED
def test_tofu_lab_sweep_removes_orphans_with_its_prefix_only():
    testkit.Exercise.require_localstack_devops()
    keep = f"devops-ex-keep{os.getpid()}"
    s3, dynamodb, iam = localstack_client("s3"), localstack_client("dynamodb"), localstack_client("iam")
    ssm, secrets, kms = localstack_client("ssm"), localstack_client("secretsmanager"), localstack_client("kms")
    s3.create_bucket(Bucket=keep)
    try:
        with testkit.TofuLab() as lab:
            s3.create_bucket(Bucket=f"{lab.prefix}-orphan")
            s3.put_object(Bucket=f"{lab.prefix}-orphan", Key="x.txt", Body=b"x")
            dynamodb.create_table(TableName=f"{lab.prefix}-lock", BillingMode="PAY_PER_REQUEST",
                                  KeySchema=[{"AttributeName": "LockID", "KeyType": "HASH"}],
                                  AttributeDefinitions=[{"AttributeName": "LockID", "AttributeType": "S"}])
            iam.create_role(RoleName=f"{lab.prefix}-role", AssumeRolePolicyDocument='{"Version":"2012-10-17","Statement":[]}')
            iam.put_role_policy(RoleName=f"{lab.prefix}-role", PolicyName="inline", PolicyDocument=(
                '{"Version":"2012-10-17","Statement":[{"Effect":"Allow","Action":"s3:ListBucket","Resource":"*"}]}'))
            ssm.put_parameter(Name=f"/{lab.prefix}/db/password", Value="x", Type="SecureString")
            ssm.put_parameter(Name=f"{lab.prefix}-flag", Value="x", Type="String")
            secrets.create_secret(Name=f"{lab.prefix}-token", SecretString="x")
            key = kms.create_key()["KeyMetadata"]["KeyId"]
            kms.create_alias(AliasName=f"alias/{lab.prefix}-state", TargetKeyId=key)
            ssm.put_parameter(Name=f"/{keep}/p", Value="x", Type="String")
        assert sorted(lab.swept) == sorted([
            f"s3:{lab.prefix}-orphan", f"dynamodb:{lab.prefix}-lock", f"iam-role:{lab.prefix}-role",
            f"ssm:/{lab.prefix}/db/password", f"ssm:{lab.prefix}-flag", f"secretsmanager:{lab.prefix}-token",
            f"kms-alias:alias/{lab.prefix}-state"])
        assert kms.describe_key(KeyId=key)["KeyMetadata"]["KeyState"] == "PendingDeletion"
        assert not [a for a in kms.list_aliases()["Aliases"] if a["AliasName"].startswith(f"alias/{lab.prefix}")]
        assert not [s for s in secrets.list_secrets()["SecretList"] if s["Name"].startswith(lab.prefix)]
        assert [p["Name"] for p in ssm.describe_parameters()["Parameters"] if keep in p["Name"]] == [f"/{keep}/p"]
        assert buckets_with(lab.prefix) == []
        assert not [t for t in dynamodb.list_tables()["TableNames"] if t.startswith(lab.prefix)]
        assert not [r for r in iam.list_roles()["Roles"] if r["RoleName"].startswith(lab.prefix)]
        assert keep in buckets_with(keep)
    finally:
        s3.delete_bucket(Bucket=keep)
        ssm.delete_parameter(Name=f"/{keep}/p")


@pytest.mark.parametrize("alias_fails", [False, True])
def test_localstack_sweep_schedules_key_only_after_alias_removed(monkeypatch, alias_fails):
    import boto3
    from botocore.exceptions import ClientError

    calls = []

    class Fake:
        def __init__(self, service):
            self.service = service

        def get_paginator(self, name):
            return self

        def paginate(self, **kwargs):
            if self.service == "kms":
                return [{"Aliases": [{"AliasName": "alias/devops-ex-abc12345-state", "TargetKeyId": "k1"}]}]
            return []

        def list_event_buses(self, **kwargs):
            return {"EventBuses": []}

        def list_buckets(self, **kwargs):
            return {"Buckets": []}

        def delete_alias(self, AliasName):
            calls.append(("delete_alias", AliasName))
            if alias_fails:
                raise ClientError({"Error": {"Code": "X", "Message": "x"}}, "DeleteAlias")

        def schedule_key_deletion(self, KeyId, PendingWindowInDays):
            calls.append(("schedule", KeyId))

    monkeypatch.setattr(boto3, "client", lambda service, **kwargs: Fake(service))
    removed = testkit.localstack_sweep("devops-ex-abc12345")
    if alias_fails:
        assert removed == [] and calls == [("delete_alias", "alias/devops-ex-abc12345-state")]
    else:
        assert removed == ["kms-alias:alias/devops-ex-abc12345-state"]
        assert calls == [("delete_alias", "alias/devops-ex-abc12345-state"), ("schedule", "k1")]


def test_localstack_client_refuses_de_port(monkeypatch):
    monkeypatch.setenv("LOCALSTACK_DEVOPS_PORT", "4566")
    monkeypatch.setenv("LOCALSTACK_PORT", "4566")
    with pytest.raises(RuntimeError, match="trùng cổng localstack"):
        testkit.localstack_client("s3")


def test_localstack_client_ignores_learner_aws_env(monkeypatch, tmp_path):
    monkeypatch.setenv("LOCALSTACK_DEVOPS_PORT", "24566")
    monkeypatch.setenv("LOCALSTACK_PORT", "4566")
    broken = tmp_path / "config"
    broken.write_text("[profile x\nendpoint_url = http://203.0.113.9:1\n", encoding="utf-8")
    monkeypatch.setenv("AWS_PROFILE", "khong-ton-tai")
    monkeypatch.setenv("AWS_CONFIG_FILE", str(broken))
    monkeypatch.setenv("AWS_ENDPOINT_URL", "http://203.0.113.9:1")
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "AKIAREALKEY")
    client = testkit.localstack_client("s3")
    assert client.meta.endpoint_url == "http://127.0.0.1:24566"
    assert client._request_signer._credentials.access_key == "test"
    assert os.environ["AWS_PROFILE"] == "khong-ton-tai" and os.environ["AWS_CONFIG_FILE"] == str(broken)
    assert os.environ["AWS_ACCESS_KEY_ID"] == "AKIAREALKEY"


@TOFU_REQUIRED
def test_tofu_lab_plan_json(recorder):
    endpoint, _ = recorder
    with testkit.TofuLab(endpoint=endpoint) as lab:
        lab.write("main.tf", 'variable "prefix" {\n  type = string\n}\nresource "terraform_data" "marker" {\n  input = var.prefix\n}\n')
        lab.init()
        plan = lab.plan_json()
        changes = {r["address"]: r["change"]["actions"] for r in plan["resource_changes"]}
        assert changes == {"terraform_data.marker": ["create"]}
        assert not list(lab.workdir.glob("*.tfplan"))
        lab.write("broken.tf", 'resource "terraform_data" "x" {\n  input = var.khong_co\n}\n')
        with pytest.raises(pytest.fail.Exception, match="tofu plan"):
            lab.plan_json()
        assert not list(lab.workdir.glob("*.tfplan"))


def test_parse_version_ansible_banner():
    banner = "ansible-playbook [core 2.21.5]\n  config file = None\n  python version = 3.12.13 (main)"
    assert testkit.parse_version(banner) == (2, 21, 5)


@pytest.mark.skipif(not shutil.which("ansible-playbook"), reason="Cần ansible-playbook")
def test_ansible_version_does_not_touch_user_home(tmp_path, monkeypatch):
    home = tmp_path / "home"
    home.mkdir()
    (tmp_path / "ansible.cfg").write_text("[defaults\nkhông phải ini\n", encoding="utf-8")
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("ANSIBLE_CONFIG", str(tmp_path / "ansible.cfg"))
    monkeypatch.chdir(tmp_path)
    version = testkit.tool_version("ansible-playbook")
    assert version and version >= (2, 21)
    assert not (home / ".ansible").exists()


def ansible_tree(tmp_path: Path, files: dict[str, str]) -> Path:
    root = tmp_path / "project"
    for rel, text in files.items():
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    return root


@pytest.mark.parametrize(
    "rel,text,needle",
    [
        ("inventory/hosts.yml", "all:\n  hosts:\n    worker-1:\n      ansible_connection: local\n", "ansible_connection"),
        ("inventory/hosts.ini", "[workers]\nworker-1 ansible_host=10.0.0.5\n", "ansible_host"),
        ("inventory/hosts", "[workers]\nworker-1 ansible_port=2222\n", "ansible_port"),
        ("inventory/hosts.yml", "all:\n  hosts:\n    localhost:\n", "localhost"),
        ("inventory/hosts.ini", "[workers]\n127.0.0.1\n", "127.0.0.1"),
        ("inventory/hosts.ini", "[workers]\n::1\n", "::1"),
        ("site.yml", "- hosts: localhost\n  tasks: []\n", "localhost"),
        ("site.yml", "- hosts: workers\n  connection: local\n  tasks: []\n", "connection"),
        ("site.yml", "- {hosts: workers, connection: local}\n", "connection"),
        ("site.yml", "- hosts: all\n  tasks:\n    - ansible.builtin.ping:\n      delegate_to: worker-2\n", "delegate_to"),
        ("site.yml", "- hosts: all\n  tasks:\n    - local_action: ansible.builtin.command id\n", "local_action"),
        ("site.yml", "- hosts: all\n  tasks:\n    - ansible.builtin.add_host:\n        name: x\n", "add_host"),
        ("group_vars/all.yml", "ansible_ssh_common_args: -o StrictHostKeyChecking=no\n", "ansible_ssh_common_args"),
        ("group_vars/all.yml", "ansible_host_key_checking: false\n", "host_key_checking"),
        ("roles/r/vars/main.yml", "ansible_python_interpreter: /usr/bin/python3\nansible_private_key_file: /x\n",
         "ansible_private_key_file"),
        ("site.yml", "- hosts: all\n  tasks:\n    - ansible.builtin.debug:\n        msg: \"{{ lookup('pipe', 'id') }}\"\n",
         "pipe"),
        ("site.yml", "- hosts: all\n  tasks:\n    - ansible.builtin.debug:\n        msg: \"{{ query('ansible.builtin.lines', 'id') }}\"\n",
         "lines"),
        ("site.yml", "- hosts: all\n  vars:\n    x: \"{{ lookup( 'pipe' , 'id') }}\"\n", "pipe"),
        ("site.yml", "- hosts: all\n  vars:\n    url: http://localhost:8000\n", "localhost"),
        ("inventory/hosts.ini", "[workers]\nw1 x=127.1\n", "127.1"),
        ("inventory/hosts.ini", "[workers]\nw1 x=127.0.0.01\n", "127.0.0.01"),
        ("group_vars/all.yml", "bind: 0.0.0.0\n", "0.0.0.0"),
        ("group_vars/all.yml", "addr: 0x7f000001\n", "0x7f000001"),
        ("group_vars/all.yml", "addr: 2130706433\n", "2130706433"),
        ("group_vars/all.yml", "addr: \"::ffff:127.0.0.1\"\n", "::ffff:127.0.0.1"),
        ("group_vars/all.yml", "addr: \"[::]\"\n", "[::]"),
        ("site.yml", "- hosts: all\n  vars:\n    \"ansible\\u005fconnection\": local\n", "u005f"),
        ("inventory/hosts.json", "{\"all\": {\"vars\": {\"ansible\\u005fhost\": \"x\"}}}\n", "u005f"),
        ("group_vars/all.yml", "\"ansible\\x5fport\": 22\n", "x5f"),
    ],
)
def test_ansible_problems_reject(tmp_path, rel, text, needle):
    root = ansible_tree(tmp_path, {rel: text})
    problems = testkit.ansible_problems(root)
    assert problems and any(needle in p and rel in p for p in problems), problems


@pytest.mark.parametrize(
    "rel,text,needle",
    [
        ("site.yml", "- hosts: all\n  roles: [../home/rl/r]\n", "`..`"),
        ("site.yml", "- hosts: all\n  roles:\n    - \"..\\/home/rl/r\"\n", "`..`"),
        ("site.yml", "- hosts: all\n  roles:\n    - \".\\\n      ./home/rl/r\"\n", "'../home/rl/r'"),
        ("site.yml", "- hosts: all\n  roles:\n    - \"{{ lookup('env', 'HOME') }}/rl/r\"\n", "`roles`"),
        ("site.yml", "- {hosts: all, roles: [{role: '{{ r }}'}]}\n", "`roles`"),
        ("site.yml", "- hosts: all\n  roles:\n    - role: /tmp/x/r\n", "/tmp/x/r"),
        ("site.yml", "- hosts: all\n  roles:\n    - name: ~/rl/r\n", "~/rl/r"),
        ("site.yml", "- hosts: all\n  tasks:\n    - ansible.builtin.include_role:\n        name: $HOME/rl/r\n", "$HOME/rl/r"),
        ("site.yml", "- hosts: all\n  tasks:\n    - import_role:\n        name: r\n        tasks_from: /tmp/x\n", "/tmp/x"),
        ("site.yml", "- hosts: all\n  tasks:\n    - include_tasks: \"{{ x }}.yml\"\n", "`include_tasks`"),
        ("site.yml", "- hosts: all\n  tasks:\n    - ansible.legacy.import_tasks: ../x.yml\n", "`..`"),
        ("site.yml", "- import_playbook: /tmp/p.yml\n", "/tmp/p.yml"),
        ("site.yml", "- hosts: all\n  vars_files:\n    - /etc/x.yml\n", "/etc/x.yml"),
        ("site.yml", "- hosts: all\n  tasks:\n    - ansible.builtin.include_vars:\n        dir: \"{{ playbook_dir }}\"\n",
         "`include_vars`"),
        ("roles/r/meta/main.yml", "dependencies:\n  - role: \"{{ d }}\"\n", "`dependencies`"),
        ("site.yml", "- hosts: all\n  vars:\n    r: &a \"{{ lookup('env', 'HOME') }}/rl/r\"\n  roles:\n    - *a\n", "`roles` trỏ tới"),
        ("site.yml", "- hosts: all\n  roles:\n    - !vault |\n      $ANSIBLE_VAULT;1.1;AES256\n      3132\n", "!vault"),
        ("site.yml", "- hosts: all\n  tasks:\n    - include_tasks: group_vars/all/vault.yml\n", "thư mục dữ liệu"),
        ("tasks/x.yml", "$ANSIBLE_VAULT;1.1;AES256\n6162\n", "$ANSIBLE_VAULT"),
        ("site.yml", "# roles_path: /tmp\n- hosts: all\n", "roles_path"),
    ],
)
def test_ansible_problems_reject_outside_references(tmp_path, rel, text, needle):
    root = ansible_tree(tmp_path, {rel: text})
    problems = testkit.ansible_problems(root)
    assert problems and any(needle in p and rel in p for p in problems), problems


@pytest.mark.parametrize("folder", ["callback_plugins", "roles/r/filter_plugins", "connection_plugins", "collections", "library",
                                    "roles/r/library", "module_utils", "roles/r/module_utils", "shell_plugins"])
def test_ansible_problems_reject_plugin_dirs(tmp_path, folder):
    root = ansible_tree(tmp_path, {f"{folder}/x.py": "X = 1\n", "site.yml": "- hosts: all\n  tasks: []\n"})
    problems = testkit.ansible_problems(root)
    assert problems and folder.split("/")[-1] in problems[0], problems


def test_ansible_problems_accept_normal_project(tmp_path):
    root = ansible_tree(tmp_path, {
        "inventory/hosts.yml": "workers:\n  hosts:\n    worker-1:\n    worker-2:\n",
        "site.yml": (
            "- hosts: workers\n  become: true\n  tasks:\n"
            "    - name: Chờ connection ổn định\n      ansible.builtin.wait_for_connection:\n        timeout: 30\n"
            "    - ansible.builtin.debug:\n        msg: \"{{ ansible_hostname }} {{ inventory_hostname }} {{ lookup('ansible.builtin.env', 'X') }}\"\n"
            "    - ansible.builtin.lineinfile:\n        path: /etc/x\n        regexp: '^ratio=\\d+\\.0$'\n        line: ratio=1.0.0 0.0\n"
        ),
        "roles/r/templates/worker.env.j2": "REDIS_URL=redis://localhost:6379/0\nBIND=127.0.0.1\n",
        "roles/r/files/hosts": "127.0.0.1 localhost\n",
        "README.md": "Không dùng delegate_to hay connection local trong lab.\n",
        "play.yml": (
            "- import_playbook: site.yml\n- hosts: workers\n  vars_files:\n    - vars/common.yml\n  roles:\n"
            "    - r\n    - role: r\n      vars:\n        dest: /opt/olist\n        level: \"{{ olist_level }}\"\n"
            "  tasks:\n    - ansible.builtin.include_tasks: tasks/extra.yml\n"
            "    - ansible.builtin.include_role:\n        name: r\n        tasks_from: config\n"
            "    - ansible.builtin.include_vars:\n        file: vars/common.yml\n...\n"
        ),
        "roles/r/meta/main.yml": "dependencies: []\n",
        "roles/r/templates/notes.j2": "role: {{ olist_role }}\n",
        "inventory/group_vars/workers/vault.yml": "$ANSIBLE_VAULT;1.2;AES256;prod\n6162\n",
    })
    assert testkit.ansible_problems(root) == []


def ansible_events() -> list[dict]:
    return [
        {"type": "task", "host": "w1", "task": "Tạo user", "action": "ansible.builtin.user", "status": "ok", "changed": True,
         "handler": False, "role": "olist_worker", "tags": ["setup"]},
        {"type": "task", "host": "w1", "task": "Restart", "action": "ansible.builtin.systemd_service", "status": "skipped",
         "changed": False, "handler": True, "role": "olist_worker", "tags": []},
        {"type": "task", "host": "w2", "task": "Tạo user", "action": "ansible.builtin.user", "status": "ok", "changed": False,
         "handler": False, "role": "olist_worker", "tags": ["setup"]},
        {"type": "stats", "host": "w1", "ok": 3, "changed": 1, "unreachable": 0, "failures": 0, "skipped": 1, "rescued": 0,
         "ignored": 0},
        {"type": "stats", "host": "w2", "ok": 2, "changed": 0, "unreachable": 0, "failures": 0, "skipped": 0, "rescued": 0,
         "ignored": 0},
    ]


def test_ansible_run_recap_and_tasks():
    run = testkit.AnsibleRun(["ansible-playbook"], 0, "out", "", ansible_events())
    assert run.recap == {"w1": {"ok": 3, "changed": 1, "unreachable": 0, "failures": 0, "skipped": 1, "rescued": 0, "ignored": 0},
                         "w2": {"ok": 2, "changed": 0, "unreachable": 0, "failures": 0, "skipped": 0, "rescued": 0, "ignored": 0}}
    assert run.changed == {"w1": 1, "w2": 0}
    assert [t["task"] for t in run.tasks(changed=True)] == ["Tạo user"]
    assert [t["host"] for t in run.tasks(handler=True)] == ["w1"]
    assert [t["host"] for t in run.tasks("Tạo user")] == ["w1", "w2"]
    assert run.hosts == {"w1", "w2"}


ANSIBLE_REQUIRED = pytest.mark.skipif(
    not (shutil.which("ansible-playbook") and shutil.which("docker") and shutil.which("bwrap")),
    reason="Cần ansible-playbook, docker và bwrap",
)


def test_ansible_lab_refuses_use_outside_with():
    with pytest.raises(RuntimeError):
        testkit.AnsibleLab().run("ansible", "--version")


@pytest.mark.parametrize("env", [{"ANSIBLE_CONFIG": "/x"}, {"HOME": "/x"}, {"ANSIBLE_VAULT_PASSWORD_FILE": "/x"}, {"PATH": "/x"}])
def test_ansible_lab_run_env_cannot_override_lab(env):
    with testkit.AnsibleLab() as lab:
        with pytest.raises(ValueError, match="lab tự quản"):
            lab.run("ansible-inventory", "--list", env=env)


@ANSIBLE_REQUIRED
def test_ansible_lab_stage_skips_docs_and_checks_the_rest(tmp_path):
    root = ansible_tree(tmp_path, {
        "site.yml": "- hosts: all\n  tasks: []\n",
        "SOLUTION.md": "Ở production dùng `delegate_to: localhost` để gọi API.\n",
        "roles/r/README.md": "connection: local chỉ để thử\n",
        "roles/r/tasks/main.yml": "- ansible.builtin.ping:\n",
    })
    with testkit.AnsibleLab() as lab:
        staged = lab.stage(root)
        assert sorted(p.relative_to(staged).as_posix() for p in staged.rglob("*") if p.is_file()) == [
            "roles/r/tasks/main.yml", "site.yml"]
        (root / "notes.txt").write_text("delegate_to: localhost\n", encoding="utf-8")
        with pytest.raises(pytest.fail.Exception, match="delegate_to"):
            lab.stage(root, "again")


@ANSIBLE_REQUIRED
def test_ansible_lab_run_passes_extra_env():
    with testkit.AnsibleLab() as lab:
        script = lab.write("inv/inventory.py", "#!/usr/bin/env python3\nimport json, os\n"
                           "print(json.dumps({'g': {'hosts': [os.environ['DEMO_HOST']]}, '_meta': {'hostvars': {}}}))\n")
        script.chmod(0o755)
        result = lab.run("ansible-inventory", "-i", str(script), "--list", env={"DEMO_HOST": "w9"}, cwd=script.parent)
        assert result.returncode == 0, result.stderr
        assert json.loads(result.stdout)["g"]["hosts"] == ["w9"]


def test_ansible_files_pin_ssh(tmp_path):
    control, work = tmp_path / "ctl", tmp_path / "work"
    files = testkit._ansible_files(control, work, {"w1": 41001, "w2": 41002}, {"w1": "ssh-ed25519 AAAA1", "w2": "ssh-ed25519 AAAA2"})
    ssh = files["ssh_config"]
    for line in ("StrictHostKeyChecking yes", "IdentitiesOnly yes", "IdentityAgent none", "GlobalKnownHostsFile /dev/null",
                 "UpdateHostKeys no", "BatchMode yes", f'UserKnownHostsFile "{control / "known_hosts"}"',
                 f'IdentityFile "{control / "id_ed25519"}"'):
        assert line in ssh
    assert files["known_hosts"].splitlines() == ["[127.0.0.1]:41001 ssh-ed25519 AAAA1", "[127.0.0.1]:41002 ssh-ed25519 AAAA2"]
    assert files["lab.ini"].splitlines() == ["w1", "w2"]
    assert files["allowed"].splitlines() == ["127.0.0.1 41001", "127.0.0.1 41002"]
    assert (f'ProxyCommand "{Path(sys.executable).resolve()}" -I "{control / "devops_ex_proxy.py"}" %h %p "{control / "allowed"}"'
            in ssh)
    assert files["devops_ex_proxy.py"] == testkit._ANSIBLE_PROXY
    assert files["callbacks/devops_ex_events.py"] == testkit._ANSIBLE_CALLBACK
    assert set(files) == set(testkit._ANSIBLE_CONTROL) - {"id_ed25519", "id_ed25519.pub"}
    pinned = json.loads(files["lab-conn.yml"])
    assert set(testkit.ANSIBLE_PINNED_VARS) <= set(pinned)
    assert pinned["ansible_connection"] == "ansible.builtin.ssh" and pinned["ansible_user"] == pinned["ansible_ssh_user"] == "root"
    assert pinned["devops_ex_lab_port"] == {"w1": 41001, "w2": 41002}
    assert pinned["devops_ex_lab_addr"] == {"w1": "127.0.0.1", "w2": "127.0.0.1"}
    assert pinned["ansible_host"] == pinned["ansible_ssh_host"] and "default('0.0.0.0')" in pinned["ansible_host"]
    assert pinned["ansible_port"] == pinned["ansible_ssh_port"] and "default(1)" in pinned["ansible_port"]
    assert pinned["ansible_ssh_common_args"] == pinned["ansible_ssh_extra_args"] == pinned["ansible_ssh_pkcs11_provider"] == ""
    assert pinned["ansible_private_key"] is None and pinned["ansible_ssh_private_key"] is None
    assert pinned["ansible_ssh_private_key_file"] == pinned["ansible_private_key_file"] == str(control / "id_ed25519")
    assert pinned["ansible_control_path_dir"] == str(work / "cp") and pinned["ansible_control_path"] == "%(directory)s/%%C"
    assert pinned["ansible_host_key_checking"] is True and pinned["ansible_ssh_executable"] == "ssh"
    assert pinned["ansible_sftp_executable"] == "sftp" and pinned["ansible_scp_executable"] == "scp"
    assert pinned["ansible_ssh_pipelining"] is True and pinned["ansible_ssh_transfer_method"] == "smart"
    assert pinned["ansible_ssh_args"].startswith(f"-F {control / 'ssh_config'}")
    config = files["ansible.cfg"]
    assert f"-F {control / 'ssh_config'}" in config and "host_key_checking = True" in config
    assert f"collections_path = {control / 'collections'}" in config and f"roles_path = {control / 'roles'}" in config
    assert f"callback_plugins = {control / 'callbacks'}" in config and f"control_path_dir = {work / 'cp'}" in config
    assert f"local_tmp = {work / 'home' / '.ansible' / 'tmp'}" in config and "collections_scan_sys_path = False" in config
    for name in testkit._ANSIBLE_PLUGIN_PATHS:
        assert f"{name} = {control / 'plugins' / name}" in config


def test_ansible_env_from_scratch(tmp_path, monkeypatch):
    monkeypatch.setenv("ANSIBLE_CONFIG", "/home/x/.ansible.cfg")
    monkeypatch.setenv("ANSIBLE_VAULT_PASSWORD_FILE", "/home/x/.vault")
    env = testkit._ansible_env(tmp_path / "ctl", tmp_path / "work", tmp_path / "work" / "events.jsonl")
    assert env["ANSIBLE_CONFIG"] == str(tmp_path / "ctl" / "ansible.cfg")
    assert env["HOME"] == str(tmp_path / "work" / "home")
    assert env["ANSIBLE_HOME"] == str(tmp_path / "ctl" / "ansible-home")
    assert "ANSIBLE_VAULT_PASSWORD_FILE" not in env and "SSH_AUTH_SOCK" not in env
    assert env["DEVOPS_EX_EVENTS"] == str(tmp_path / "work" / "events.jsonl")
    assert env["PYTHONNOUSERSITE"] == "1"
    assert not {"ansible_user", "ansible_ssh_user"} & set(json.loads(env["DEVOPS_EX_PINNED"]))
    assert {"ansible_ssh_host", "ansible_ssh_port", "ansible_control_path"} <= set(json.loads(env["DEVOPS_EX_PINNED"]))


def test_ansible_target_wheels_match_sample_app():
    sample = (testkit.ROOT / "tracks" / "devops" / "sample-app" / "requirements.txt").read_text(encoding="utf-8").split()
    worker = (testkit.ANSIBLE_TARGET_DIR / "requirements-worker.txt").read_text(encoding="utf-8").split()
    assert worker and set(worker) <= set(sample)


@pytest.fixture(scope="module")
def ansible_lab():
    testkit.Exercise.require_tool("ansible-playbook", testkit.ANSIBLE_MIN_VERSION)
    with testkit.AnsibleLab(["node-a", "node-b"]) as lab:
        yield lab
    assert testkit.docker_leftovers(lab.docker.id) == []
    assert not lab.root.exists() and not lab.work.exists()


@ANSIBLE_REQUIRED
def test_ansible_lab_runs_playbook_twice(ansible_lab):
    project = ansible_lab.write("project/site.yml", (
        "- hosts: all\n  gather_facts: false\n  roles:\n    - demo\n"
    )).parent
    ansible_lab.write("project/roles/demo/tasks/main.yml", (
        "- name: Ghi tệp\n  ansible.builtin.copy:\n    dest: /etc/devops-ex.txt\n    content: \"{{ inventory_hostname }}\\n\"\n"
        "  notify: Báo đổi\n"
    ))
    ansible_lab.write("project/roles/demo/handlers/main.yml", (
        "- name: Báo đổi\n  ansible.builtin.command: \"true\"\n  when: false\n"
    ))
    first = ansible_lab.playbook("site.yml", cwd=project)
    assert first.returncode == 0, first.tail()
    assert first.changed == {"node-a": 1, "node-b": 1}
    assert sorted((t["host"], t["role"], t["changed"]) for t in first.tasks("Ghi tệp")) == [("node-a", "demo", True),
                                                                                            ("node-b", "demo", True)]
    assert sorted((t["host"], t["status"]) for t in first.tasks("Báo đổi", handler=True)) == [("node-a", "skipped"), ("node-b", "skipped")]
    second = ansible_lab.playbook("site.yml", cwd=project)
    assert second.changed == {"node-a": 0, "node-b": 0}, second.tail()
    assert ansible_lab.read("node-b", "/etc/devops-ex.txt") == "node-b\n"
    assert ansible_lab.read("node-b", "/khong/co") is None
    assert ansible_lab.exec("node-a", "cat", "/proc/self/status").stdout.count("NoNewPrivs:\t1") == 1


@ANSIBLE_REQUIRED
def test_ansible_lab_ignores_user_config(ansible_lab):
    result = ansible_lab.run("ansible-config", "dump", "--only-changed", cwd=ansible_lab.root)
    assert result.returncode == 0, result.stderr
    assert str(ansible_lab.control / "ansible.cfg") in result.stdout
    assert str(Path.home()) not in result.stdout.replace(str(ansible_lab.work), "").replace(str(ansible_lab.control), "")


@ANSIBLE_REQUIRED
def test_ansible_lab_rejects_unpinned_host(ansible_lab):
    ansible_lab.docker.start("rogue", ansible_lab.image, ports=[22], env={"DEVOPS_EX_AUTHORIZED_KEY": ansible_lab.public_key})
    ansible_lab.docker.wait_log("rogue", "Server listening")
    port = ansible_lab.docker.port("rogue", 22)
    rogue = ansible_lab.write("rogue/inventory.ini", f"rogue ansible_host=127.0.0.1 ansible_port={port} ansible_user=root\n")
    ansible_lab.write("rogue/site.yml", "- hosts: rogue\n  gather_facts: false\n  tasks:\n    - ansible.builtin.ping:\n")
    with pytest.raises(pytest.fail.Exception) as info:
        ansible_lab.playbook("site.yml", inventory=[str(rogue)], cwd=rogue.parent)
    message = str(info.value)
    assert "host ngoài lab: rogue" in message and "ssh tới 0.0.0.0:1 bị chặn" in message and "unreachable=1" in message
    assert "inventory host vars trên rogue đặt `ansible_host`" in message


@ANSIBLE_REQUIRED
def test_ansible_lab_host_key_pinning_blocks_allowed_port(ansible_lab):
    ansible_lab.docker.start("rogue2", ansible_lab.image, ports=[22], env={"DEVOPS_EX_AUTHORIZED_KEY": ansible_lab.public_key})
    ansible_lab.docker.wait_log("rogue2", "Server listening")
    port = ansible_lab.docker.port("rogue2", 22)
    allowed = ansible_lab.control / "allowed"
    original = allowed.read_text(encoding="utf-8")
    allowed.write_text(original + f"127.0.0.1 {port}\n", encoding="utf-8")
    try:
        result = testkit.run_sandboxed(["ssh", "-F", str(ansible_lab.control / "ssh_config"), "-p", str(port), "127.0.0.1",
                                        "true"], writable=[ansible_lab.root], readonly=[ansible_lab.control],
                                       cwd=ansible_lab.root, env={}, timeout=60)
    finally:
        allowed.write_text(original, encoding="utf-8")
    assert result.returncode != 0 and "Host key verification failed" in result.stderr, result.stderr


def bypass_project(lab, name: str, files: dict[str, str]) -> Path:
    for rel, text in files.items():
        path = lab.write(f"{name}/{rel}", text)
        if rel.endswith(".py"):
            path.chmod(0o755)
    return lab.root / name


LOCAL_MARKER = "- name: Ghi dấu\n      ansible.builtin.copy:\n        dest: {marker}\n        content: chạy ở đây\n"


def assert_bypass_blocked(lab, project: Path, needles: tuple[str, ...], inventory=(), on_lab_host: str | None = None):
    marker = lab.root / f"{project.name}-pwned"
    site = (project / "site.yml").read_text(encoding="utf-8").replace("MARKER", str(marker))
    (project / "site.yml").write_text(site, encoding="utf-8")
    for host in lab.hosts:
        assert lab.exec(host, "mkdir", "-p", str(lab.root)).returncode == 0
    with pytest.raises(pytest.fail.Exception) as info:
        lab.playbook("site.yml", inventory=list(inventory), cwd=project)
    message = str(info.value)
    assert "bị lab đánh dấu lỗi" in message
    for needle in needles:
        assert needle in message, message
    assert not marker.exists(), "Task đã chạy trên máy điều khiển"
    if on_lab_host:
        assert lab.read(on_lab_host, str(marker)) == "chạy ở đây", "Task phải chạy trên target qua ssh"


@ANSIBLE_REQUIRED
def test_ansible_bypass_templated_set_fact_key(ansible_lab):
    project = bypass_project(ansible_lab, "bypass-setfact", {"site.yml": (
        "- hosts: node-a\n  gather_facts: false\n  tasks:\n"
        "    - ansible.builtin.set_fact:\n        \"{{ 'ansible_' ~ 'connection' }}\": local\n"
        "        \"{{ 'ansible_ssh_' ~ 'common_args' }}\": -o StrictHostKeyChecking=no\n"
        "        \"{{ 'ansible_' ~ 'port' }}\": 22\n"
        "    " + LOCAL_MARKER.format(marker="MARKER")
    )})
    assert_bypass_blocked(ansible_lab, project, ("ansible_facts trên node-a đặt `ansible_connection`",
                                                 "`ansible_ssh_common_args`", "`ansible_port`"), on_lab_host="node-a")


@ANSIBLE_REQUIRED
def test_ansible_bypass_escaped_key(ansible_lab):
    project = bypass_project(ansible_lab, "bypass-escape", {"site.yml": (
        "- hosts: node-a\n  gather_facts: false\n  vars:\n    \"ansible\\u005fconnection\": local\n"
        "    \"ansible\\u005fhost\": 127.0.0.1\n  tasks:\n"
        "    " + LOCAL_MARKER.format(marker="MARKER")
    )})
    assert testkit.ansible_problems(project), "phép quét tĩnh phải bắt escape"
    assert_bypass_blocked(ansible_lab, project, ("play vars đặt `ansible_connection`", "play vars đặt `ansible_host`"),
                          on_lab_host="node-a")


@ANSIBLE_REQUIRED
def test_ansible_bypass_dynamic_inventory_script(ansible_lab):
    script = ("#!/usr/bin/env python3\nimport json\nprint(json.dumps({'all': {'hosts': ['node-a', 'evil']}, '_meta': {'hostvars': {"
              "'node-a': {'ansible_connection': 'local'}, 'evil': {'ansible_connection': 'local', 'ansible_host': '127.0.0.1'}}}}))\n")
    project = bypass_project(ansible_lab, "bypass-inventory", {
        "inventory.py": script,
        "site.yml": "- hosts: all\n  gather_facts: false\n  tasks:\n    " + LOCAL_MARKER.format(marker="MARKER"),
    })
    assert_bypass_blocked(ansible_lab, project, (
        "inventory host vars trên node-a đặt `ansible_connection`", "host ngoài lab: evil", "ssh tới 0.0.0.0:1 bị chặn"),
        inventory=[str(project / "inventory.py")], on_lab_host="node-a")


@ANSIBLE_REQUIRED
def test_ansible_bypass_templated_localhost(ansible_lab):
    project = bypass_project(ansible_lab, "bypass-localhost", {"site.yml": (
        "- hosts: \"{{ 'local' ~ 'host' }}\"\n  gather_facts: false\n  connection: local\n  tasks:\n"
        "    " + LOCAL_MARKER.format(marker="MARKER")
        + "    - ansible.builtin.ping:\n      delegate_to: \"{{ 'local' ~ 'host' }}\"\n"
    )})
    assert_bypass_blocked(ansible_lab, project, ("host ngoài lab: localhost", "ssh tới 0.0.0.0:1 bị chặn",
                                                 "play connection đặt `local`"))


@ANSIBLE_REQUIRED
def test_ansible_bypass_legacy_ssh_aliases(ansible_lab):
    other = ansible_lab.ports["node-b"]
    project = bypass_project(ansible_lab, "bypass-alias", {"site.yml": (
        "- hosts: node-a\n  gather_facts: false\n  tasks:\n"
        "    - ansible.builtin.set_fact:\n        \"{{ 'ansible_ssh_' ~ 'host' }}\": 127.0.0.1\n"
        f"        \"{{{{ 'ansible_ssh_' ~ 'port' }}}}\": {other}\n"
        "        \"{{ 'ansible_' ~ 'control_path' }}\": /tmp/x\n"
        "    " + LOCAL_MARKER.format(marker="MARKER")
    )})
    assert_bypass_blocked(ansible_lab, project, ("ansible_facts trên node-a đặt `ansible_ssh_host`", "`ansible_ssh_port`",
                                                 "`ansible_control_path`"), on_lab_host="node-a")
    assert ansible_lab.read("node-b", str(ansible_lab.root / "bypass-alias-pwned")) is None, "Kết nối bị chuyển sang node-b"


CONTROL_ATTACK = """#!/usr/bin/env python3
import errno
import base64
import json
import os
import sys

control = os.environ["DEVOPS_EX_CONTROL"]
results = {}
for name in ("lab-conn.yml", "callbacks/devops_ex_events.py", "devops_ex_proxy.py", "known_hosts", "allowed", "ssh_config",
             "ansible.cfg", "callbacks/evil.py"):
    path = os.path.join(control, name)
    try:
        with open(path, "w") as handle:
            handle.write("{}\\n")
        results[name] = "written"
    except OSError as error:
        results[name] = errno.errorcode.get(error.errno, str(error.errno))
with open(os.environ["DEVOPS_EX_REPORT"], "w") as handle:
    json.dump(results, handle)
print(json.dumps({"all": {"hosts": ["node-a"]}, "_meta": {"hostvars": {}}}))
"""


@ANSIBLE_REQUIRED
def test_ansible_control_files_read_only_in_sandbox(ansible_lab):
    before = {name: (ansible_lab.control / name).read_bytes() for name in testkit._ANSIBLE_CONTROL}
    project = bypass_project(ansible_lab, "control-attack", {
        "inventory.py": CONTROL_ATTACK,
        "site.yml": "- hosts: node-a\n  gather_facts: false\n  tasks:\n    " + LOCAL_MARKER.format(marker="MARKER"),
    })
    marker = ansible_lab.root / "control-attack-pwned"
    (project / "site.yml").write_text((project / "site.yml").read_text(encoding="utf-8").replace("MARKER", str(marker)),
                                      encoding="utf-8")
    assert ansible_lab.exec("node-a", "mkdir", "-p", str(ansible_lab.root)).returncode == 0
    report = ansible_lab.work / "home" / "control-attack.json"
    env = {"DEVOPS_EX_CONTROL": str(ansible_lab.control), "DEVOPS_EX_REPORT": str(report)}
    runs = [ansible_lab.playbook("site.yml", inventory=[str(project / "inventory.py")], cwd=project, env=env) for _ in range(2)]
    assert json.loads(report.read_text(encoding="utf-8")) == {
        name: "EROFS" for name in ("lab-conn.yml", "callbacks/devops_ex_events.py", "devops_ex_proxy.py", "known_hosts",
                                   "allowed", "ssh_config", "ansible.cfg", "callbacks/evil.py")}
    assert {name: (ansible_lab.control / name).read_bytes() for name in testkit._ANSIBLE_CONTROL} == before
    second = runs[1]
    assert second.returncode == 0, second.tail()
    events = second.tasks("Ghi dấu")
    assert [(e["host"], e["connection"], e["address"], e["port"]) for e in events] == [
        ("node-a", "ansible.builtin.ssh", "127.0.0.1", str(ansible_lab.ports["node-a"]))]
    assert second.connections and all(c["allowed"] and c["port"] == str(ansible_lab.ports["node-a"]) for c in second.connections)
    assert not marker.exists() and ansible_lab.read("node-a", str(marker)) == "chạy ở đây"


def test_ansible_lab_restores_control_files(tmp_path):
    if not (shutil.which("ansible-playbook") and shutil.which("bwrap")):
        pytest.skip("Cần ansible-playbook và bwrap")
    with testkit.AnsibleLab() as lab:
        original = (lab.control / "lab-conn.yml").read_bytes()
        (lab.control / "lab-conn.yml").write_text("{}\n", encoding="utf-8")
        (lab.control / "callbacks" / "evil.py").write_text("X = 1\n", encoding="utf-8")
        (lab.control / "plugins" / "connection_plugins" / "ssh.py").write_text("X = 1\n", encoding="utf-8")
        (lab.control / "plugins" / "extra").mkdir()
        (lab.control / "ansible.cfg").unlink()
        result = lab.run("ansible", "--version")
        assert result.returncode == 0, result.stderr
        assert (lab.control / "lab-conn.yml").read_bytes() == original
        assert not (lab.control / "callbacks" / "evil.py").exists()
        assert not any((lab.control / "plugins" / "connection_plugins").iterdir())
        assert not (lab.control / "plugins" / "extra").exists() and (lab.control / "ansible.cfg").is_file()
        assert not [p for p in lab.control.rglob(".write-*")]
    assert not lab.control.exists() and not lab.root.exists() and not lab.work.exists()


SHADOW_SSH = """from ansible.plugins.connection.local import Connection as Local


class Connection(Local):
    transport = "ssh"
"""

SHADOW_ATTACK = """#!/usr/bin/env python3
import base64
import json
import os

results = {}
for target in (os.path.join(os.environ["HOME"], ".ansible", "plugins", "connection", "ssh.py"),
               os.path.join(os.environ["DEVOPS_EX_PROJECT"], "connection_plugins", "ssh.py"),
               os.path.join(os.environ["DEVOPS_EX_PROJECT"], "action_plugins", "copy.py")):
    try:
        os.makedirs(os.path.dirname(target), exist_ok=True)
        with open(target, "w") as handle:
            handle.write(os.environ["DEVOPS_EX_SHADOW"])
        results[target] = "written"
    except OSError as error:
        results[target] = type(error).__name__ + ":" + str(error.errno)
with open(os.path.join(os.environ["HOME"], "shadow.json"), "a") as handle:
    handle.write(json.dumps(results) + "\\n")
print(json.dumps({"all": {"hosts": ["node-a"]}, "_meta": {"hostvars": {}}}))
"""


@ANSIBLE_REQUIRED
def test_ansible_plugin_shadowing_does_not_change_connection(ansible_lab):
    project = bypass_project(ansible_lab, "shadow", {
        "inventory.py": SHADOW_ATTACK,
        "site.yml": "- hosts: node-a\n  gather_facts: false\n  tasks:\n    " + LOCAL_MARKER.format(marker="MARKER"),
    })
    marker = ansible_lab.root / "shadow-pwned"
    (project / "site.yml").write_text((project / "site.yml").read_text(encoding="utf-8").replace("MARKER", str(marker)),
                                      encoding="utf-8")
    assert ansible_lab.exec("node-a", "mkdir", "-p", str(ansible_lab.root)).returncode == 0
    env = {"DEVOPS_EX_PROJECT": str(project), "DEVOPS_EX_SHADOW": SHADOW_SSH}
    runs = [ansible_lab.playbook("site.yml", inventory=[str(project / "inventory.py")], cwd=project, env=env) for _ in range(2)]
    attempts = [json.loads(line) for line in (ansible_lab.work / "home" / "shadow.json").read_text(encoding="utf-8").splitlines()]
    home_plugin = str(ansible_lab.work / "home" / ".ansible" / "plugins" / "connection" / "ssh.py")
    assert attempts and all(a[home_plugin] == "written" for a in attempts), attempts
    assert all(v.startswith("OSError:30") or v.startswith("PermissionError") or v == "OSError:30"
               for a in attempts for k, v in a.items() if k != home_plugin), attempts
    for run in runs:
        assert run.returncode == 0, run.tail()
        events = run.tasks("Ghi dấu")
        assert [(e["host"], e["connection"], e["address"], e["port"]) for e in events] == [
            ("node-a", "ansible.builtin.ssh", "127.0.0.1", str(ansible_lab.ports["node-a"]))]
        assert run.connections and all(c["allowed"] for c in run.connections)
    assert not marker.exists() and ansible_lab.read("node-a", str(marker)) == "chạy ở đây"



HOME_ROLE_PLANT = """#!/usr/bin/env python3
import base64
import json
import os

home = os.environ["HOME"]
loads = os.path.join(home, "plugin-loads")
files = {
    "rl/r/tasks/main.yml": "- name: Lọc\\n  ansible.builtin.debug:\\n    msg: \\"{{ 'x' | devops_ex_f }}\\"\\n",
    "rl/r/vars_plugins/v.py": (
        f"with open({loads!r}, 'a') as handle:\\n    handle.write('vars\\\\n')\\n"
        "from ansible.plugins.vars import BaseVarsPlugin\\n\\n\\nclass VarsModule(BaseVarsPlugin):\\n"
        "    REQUIRES_ENABLED = False\\n\\n    def get_vars(self, loader, path, entities, cache=True):\\n        return {}\\n"
    ),
    "rl/r/filter_plugins/f.py": (
        f"with open({loads!r}, 'a') as handle:\\n    handle.write('filter\\\\n')\\n\\n\\nclass FilterModule:\\n"
        "    def filters(self):\\n        return {'devops_ex_f': lambda value: value}\\n"
    ),
}
for rel, text in files.items():
    path = os.path.join(home, rel)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as handle:
        handle.write(text)
print(json.dumps({"all": {"hosts": ["node-a"]}, "_meta": {"hostvars": {}}}))
"""


@ANSIBLE_REQUIRED
def test_ansible_role_in_home_is_refused_and_never_loaded(ansible_lab, tmp_path):
    home = ansible_lab.work / "home"
    loads = home / "plugin-loads"
    project = bypass_project(ansible_lab, "home-role", {
        "inventory.py": HOME_ROLE_PLANT,
        "site.yml": "- hosts: node-a\n  gather_facts: false\n  roles:\n    - demo2\n",
        "roles/demo2/tasks/main.yml": "- name: Trong bài\n  ansible.builtin.debug:\n    msg: \"{{ inventory_hostname }}\"\n",
    })
    runs = [ansible_lab.playbook("site.yml", inventory=[str(project / "inventory.py")], cwd=project) for _ in range(2)]
    assert (home / "rl" / "r" / "vars_plugins" / "v.py").is_file() and (home / "rl" / "r" / "filter_plugins" / "f.py").is_file()
    for run in runs:
        assert run.returncode == 0 and [e["host"] for e in run.tasks("Trong bài")] == ["node-a"], run.tail()
    assert not loads.exists(), "Plugin trong HOME đã được nạp khi bài chỉ dùng role trong bài"
    assert not (ansible_lab.root / "home").exists() and not home.is_relative_to(ansible_lab.root)

    for name, roles in (("ref-parent", "[../home/rl/r]"), ("ref-template", "[\"{{ lookup('env', 'HOME') }}/rl/r\"]"),
                        ("ref-absolute", f"[{home / 'rl' / 'r'}]")):
        source = ansible_tree(tmp_path / name, {"site.yml": f"- hosts: node-a\n  gather_facts: false\n  roles: {roles}\n"})
        with pytest.raises(pytest.fail.Exception, match="bị từ chối trước khi chạy") as info:
            ansible_lab.stage(source, name)
        assert "`roles`" in str(info.value) or "`..`" in str(info.value), str(info.value)
    assert not loads.exists()

    unscanned = bypass_project(ansible_lab, "home-role-parent", {
        "site.yml": "- hosts: node-a\n  gather_facts: false\n  roles: [../home/rl/r]\n"})
    parent = ansible_lab.playbook("site.yml", cwd=unscanned)
    assert parent.returncode != 0 and "../home/rl/r" in parent.output and "not found" in parent.output, parent.tail()
    assert not loads.exists(), "HOME phải không với tới được bằng đường dẫn tương đối từ bài"

    control = bypass_project(ansible_lab, "home-role-absolute", {
        "site.yml": f"- hosts: node-a\n  gather_facts: false\n  roles: [{home / 'rl' / 'r'}]\n"})
    loaded = ansible_lab.playbook("site.yml", cwd=control)
    assert loaded.returncode == 0, loaded.tail()
    assert {"vars", "filter"} <= set(loads.read_text(encoding="utf-8").split()), "Đối chứng: không qua phép quét thì plugin nạp"


USER_SITE_PLANT = """#!/usr/bin/env python3
import base64
import json
import os

site = os.environ["DEVOPS_EX_SITE"]
os.makedirs(site, exist_ok=True)
probe = "import json, os, sys; open(os.path.join(os.environ.get('HOME', '/nonexistent'), 'site-loads'), 'a').write(json.dumps([{who!r}, sys.argv]) + chr(10))"
with open(os.path.join(site, "usercustomize.py"), "w") as handle:
    handle.write(probe.format(who="usercustomize") + "\\n")
with open(os.path.join(site, "devops_ex.pth"), "w") as handle:
    handle.write(probe.format(who="pth") + "\\n")
print(json.dumps({"all": {"hosts": ["node-a"]}, "_meta": {"hostvars": {}}}))
"""


@ANSIBLE_REQUIRED
def test_ansible_proxy_ignores_user_site(ansible_lab):
    home = ansible_lab.work / "home"
    loads = home / "site-loads"
    version = f"python{sys.version_info.major}.{sys.version_info.minor}"
    site = home / ".local" / "lib" / version / "site-packages"
    project = bypass_project(ansible_lab, "user-site", {
        "inventory.py": USER_SITE_PLANT,
        "site.yml": "- hosts: node-a\n  gather_facts: false\n  tasks:\n    - ansible.builtin.ping:\n",
    })
    runs = [ansible_lab.playbook("site.yml", inventory=[str(project / "inventory.py")], cwd=project,
                                 env={"DEVOPS_EX_SITE": str(site)}) for _ in range(2)]
    assert (site / "usercustomize.py").is_file() and (site / "devops_ex.pth").is_file()
    for run in runs:
        assert run.returncode == 0, run.tail()
        assert run.connections and all(c["allowed"] for c in run.connections), run.connections
    seen = [json.loads(line) for line in loads.read_text(encoding="utf-8").splitlines()] if loads.exists() else []
    assert not [entry for entry in seen if any("devops_ex_proxy" in arg or "ansible" in arg for arg in entry[1])], seen
    assert "-I" in (ansible_lab.control / "ssh_config").read_text(encoding="utf-8").split("ProxyCommand", 1)[1].split()[:2]

    base = str(Path(sys.executable).resolve())
    bare = testkit.run_sandboxed([base, "-c", "pass"], writable=[home], cwd=home, env={"PYTHONNOUSERSITE": ""})
    assert bare.returncode == 0, bare.stderr
    assert {"usercustomize", "pth"} <= {entry[0] for entry in map(json.loads, loads.read_text(encoding="utf-8").splitlines())}, (
        "Đối chứng: python gốc không -I phải nạp user site đã cài")
    loads.unlink()
    for argv in ([base, "-I", "-c", "pass"], [base, "-c", "pass"]):
        result = testkit.run_sandboxed(argv, writable=[home], cwd=home, env={})
        assert result.returncode == 0 and not loads.exists(), (argv, result.stderr)

@ANSIBLE_REQUIRED
def test_ansible_lab_fails_on_host_outside_lab(ansible_lab):
    play = ansible_lab.write("implicit/site.yml", (
        "- hosts: \"{{ 'local' ~ 'host' }}\"\n  gather_facts: false\n  tasks:\n    - ansible.builtin.ping:\n"
    ))
    with pytest.raises(pytest.fail.Exception, match="ngoài lab"):
        ansible_lab.playbook("site.yml", cwd=play.parent)


@ANSIBLE_REQUIRED
def test_ansible_lab_stage_refuses_localhost(ansible_lab, tmp_path):
    root = ansible_tree(tmp_path, {"site.yml": "- hosts: localhost\n  tasks: []\n"})
    with pytest.raises(pytest.fail.Exception, match="localhost"):
        ansible_lab.stage(root, "bad")


@ANSIBLE_REQUIRED
def test_ansible_lab_cleans_up_on_error():
    testkit.Exercise.require_tool("ansible-playbook", testkit.ANSIBLE_MIN_VERSION)
    lab = testkit.AnsibleLab(["node-x"])
    with pytest.raises(RuntimeError, match="giữa chừng"):
        with lab:
            assert lab.docker.running("node-x")
            raise RuntimeError("lỗi giữa chừng")
    assert testkit.docker_leftovers(lab.docker.id) == []
    assert not lab.root.exists()


ADMIN_KUBECONFIG = """apiVersion: v1
kind: Config
clusters:
- name: kind-devops-lab
  cluster:
    server: https://127.0.0.1:46315
    certificate-authority-data: Q0EtREFUQQ==
users:
- name: kind-devops-lab
  user:
    client-certificate-data: Q0VSVA==
    client-key-data: S0VZ
contexts:
- name: kind-devops-lab
  context:
    cluster: kind-devops-lab
    user: kind-devops-lab
current-context: kind-devops-lab
"""

API_RESOURCES = (
    "clusterroles                                   rbac.authorization.k8s.io/v1   false   ClusterRole\n"
    "nodes                             no           v1                             false   Node\n"
    "widgets                           wd           example.com/v1                 false   Widget\n"
)


class KubeFake:
    """Giả lập docker, kind (subprocess.run thật của testkit) và kubectl, helm (run_sandboxed) cho test KubeLab không cần cluster."""

    def __init__(self, monkeypatch, *, docker_ok=True, clusters="devops-lab\n", nodes=None, ready=True, labels=None,
                 kind_version="kind v0.30.0 go1.24.6 linux/amd64", kubectl_version="Client Version: v1.34.13"):
        self.docker_ok = docker_ok
        self.kind_version = kind_version
        self.kubectl_version = kubectl_version
        self.clusters = clusters
        self.nodes = nodes if nodes is not None else {
            "devops-lab-control-plane": "running", "devops-lab-worker": "running", "devops-lab-worker2": "running"}
        self.ready = ready
        self.labels = labels if labels is not None else {name: "devops-lab" for name in self.nodes}
        self.host_calls: list[tuple[list[str], dict | None]] = []
        self.sandbox_calls: list[dict] = []
        monkeypatch.setattr(testkit.shutil, "which", lambda name: f"/usr/bin/{name}")
        monkeypatch.setattr(testkit.subprocess, "run", self.run)
        monkeypatch.setattr(testkit, "run_sandboxed", self.run_sandboxed)
        monkeypatch.setattr(testkit, "sandbox_ready", lambda: None)

    def run(self, cmd, **kwargs):
        cmd = [str(part) for part in cmd]
        self.host_calls.append((cmd, kwargs.get("env")))
        done = lambda code=0, out="", err="": subprocess.CompletedProcess(cmd, code, out, err)
        if cmd == ["kind", "version"]:
            return done(out=self.kind_version)
        if cmd == ["kubectl", "version", "--client"]:
            return done(out=self.kubectl_version)
        if cmd[:2] == ["docker", "info"]:
            return done(0 if self.docker_ok else 1, err="" if self.docker_ok else "Cannot connect to the Docker daemon")
        if cmd[:3] == ["kind", "get", "clusters"]:
            return done(out=self.clusters)
        if cmd[:3] == ["docker", "ps", "-a"]:
            return done(out="".join(f"{name}\t{state}\n" for name, state in self.nodes.items()))
        if cmd[:3] == ["kind", "get", "kubeconfig"]:
            return done(out=ADMIN_KUBECONFIG)
        if cmd[:2] == ["docker", "inspect"]:
            label = self.labels.get(cmd[-1])
            return done(0 if label is not None else 1, out=f"{label}\n" if label is not None else "", err="" if label else "No such object")
        if cmd[:2] in (["docker", "exec"], ["docker", "cp"]):
            return done(out="ok\n")
        raise AssertionError(f"lệnh không giả lập: {cmd}")

    def run_sandboxed(self, cmd, *, writable, cwd, env, timeout=30, input=None, readonly=()):
        cmd = [str(part) for part in cmd]
        self.sandbox_calls.append({"cmd": cmd, "env": dict(env), "writable": list(writable), "readonly": list(readonly),
                                   "cwd": cwd, "input": input})
        done = lambda code=0, out="", err="": subprocess.CompletedProcess(cmd, code, out, err)
        joined = " ".join(cmd)
        if "/readyz" in joined:
            return done(0, "ok") if self.ready else done(1, "", "Unable to connect to the server: dial tcp: i/o timeout")
        if "create token" in joined:
            return done(out="token-cua-lab\n")
        if "api-resources" in joined:
            return done(out=API_RESOURCES)
        if "--dry-run=server" in cmd:
            name = json.loads(input)["metadata"]["name"]
            suffix = next((s for s in ("-pv", "-rbac", "-routes", "-argocd", "-mesh") if name.endswith(f"-probe{s}")), "")
            probe = name.removesuffix(f"-probe{suffix}") + suffix
            return done(1, "", f"ValidatingAdmissionPolicy '{probe}' with binding '{probe}' denied request")
        if cmd[1:3] == ["auth", "can-i"]:
            return done(out="yes\n")
        return done()

    def calls_with(self, *words):
        return [c for c in self.sandbox_calls if all(w in c["cmd"] for w in words)]


def assert_skip(info, *needles):
    text = str(info.value)
    for needle in needles:
        assert needle in text, text


def test_require_cluster_docker_down(monkeypatch):
    KubeFake(monkeypatch, docker_ok=False)
    with pytest.raises(pytest.skip.Exception) as info:
        testkit.Exercise.require_cluster()
    assert_skip(info, "Docker chưa chạy", "devops-lab")


def test_require_cluster_missing(monkeypatch):
    KubeFake(monkeypatch, clusters="other\n")
    with pytest.raises(pytest.skip.Exception) as info:
        testkit.Exercise.require_cluster()
    assert_skip(info, "Chưa có cluster kind devops-lab", "kind create cluster --config setup/kind/devops-lab.yaml")


def test_require_cluster_stopped_nodes(monkeypatch):
    fake = KubeFake(monkeypatch, nodes={"devops-lab-control-plane": "running", "devops-lab-worker": "exited",
                                        "devops-lab-worker2": "exited"})
    with pytest.raises(pytest.skip.Exception) as info:
        testkit.Exercise.require_cluster()
    assert_skip(info, "node đang dừng", "docker start devops-lab-worker devops-lab-worker2")
    assert fake.sandbox_calls == []


def test_require_cluster_messages_are_distinct(monkeypatch):
    messages = []
    for kwargs in ({"docker_ok": False}, {"clusters": "\n"}, {"nodes": {"devops-lab-control-plane": "exited"}}, {"ready": False}):
        KubeFake(monkeypatch, **kwargs)
        with pytest.raises(pytest.skip.Exception) as info:
            testkit.Exercise.require_cluster()
        messages.append(str(info.value).split(".")[0])
    assert len(set(messages)) == 4, messages


def test_require_cluster_ready_through_temp_kubeconfig(monkeypatch, tmp_path):
    monkeypatch.setenv("KUBECONFIG", str(tmp_path / "sentinel"))
    fake = KubeFake(monkeypatch)
    testkit.Exercise.require_cluster()
    [call] = fake.sandbox_calls
    assert call["cmd"][:4] == ["kubectl", "get", "--raw", "/readyz"] and "--request-timeout=5s" in call["cmd"]
    assert call["env"]["KUBECONFIG"] != str(tmp_path / "sentinel")
    assert all(env is None or "KUBECONFIG" not in env for _, env in fake.host_calls)


@pytest.mark.parametrize("kwargs, needle", [
    ({"kind_version": "kind v0.29.0 go1.24.2 linux/amd64"}, f"kind 0.29.0 cũ hơn {testkit.KIND_MIN_VERSION}"),
    ({"kubectl_version": "Client Version: v1.32.4"}, f"kubectl 1.32.4 cũ hơn {testkit.KUBECTL_MIN_VERSION}"),
    ({"kubectl_version": "error: unknown"}, f"Không đọc được phiên bản của kubectl (bài này cần từ {testkit.KUBECTL_MIN_VERSION})"),
])
def test_require_cluster_skips_old_kind_or_kubectl(monkeypatch, kwargs, needle):
    fake = KubeFake(monkeypatch, **kwargs)
    with pytest.raises(pytest.skip.Exception) as info:
        testkit.Exercise.require_cluster()
    assert_skip(info, needle)
    assert not any(cmd[:2] == ["docker", "info"] for cmd, _ in fake.host_calls)
    assert fake.sandbox_calls == []


def test_require_cluster_accepts_min_versions(monkeypatch):
    fake = KubeFake(monkeypatch, kind_version=f"kind v{testkit.KIND_MIN_VERSION}.0 go1.24.6 linux/amd64",
                    kubectl_version=f"Client Version: v{testkit.KUBECTL_MIN_VERSION}.0")
    testkit.Exercise.require_cluster()
    assert ["kind", "version"] in [cmd for cmd, _ in fake.host_calls]
    assert ["kubectl", "version", "--client"] in [cmd for cmd, _ in fake.host_calls]


def test_require_cluster_not_ready(monkeypatch):
    KubeFake(monkeypatch, ready=False)
    with pytest.raises(pytest.skip.Exception) as info:
        testkit.Exercise.require_cluster()
    assert_skip(info, "chưa sẵn sàng", "/readyz")


_AUDIT_OPENED: list[str] = []
_AUDIT_ON: list[bool] = []


def _audit(event, args):
    if _AUDIT_ON and event in ("open", "os.listdir", "os.scandir") and args and isinstance(args[0], (str, bytes, os.PathLike)):
        _AUDIT_OPENED.append(os.fsdecode(args[0]))


sys.addaudithook(_audit)


def test_kube_lab_never_reads_user_kubeconfig(monkeypatch, tmp_path):
    sentinel = tmp_path / "sentinel-kubeconfig"
    sentinel.write_text(ADMIN_KUBECONFIG.replace("46315", "1"), encoding="utf-8")
    home = tmp_path / "home"
    (home / ".kube").mkdir(parents=True)
    (home / ".kube" / "config").write_text(ADMIN_KUBECONFIG.replace("46315", "2"), encoding="utf-8")
    monkeypatch.setenv("KUBECONFIG", str(sentinel))
    monkeypatch.setenv("HOME", str(home))
    fake = KubeFake(monkeypatch)
    _AUDIT_OPENED.clear()
    _AUDIT_ON.append(True)
    try:
        with testkit.KubeLab() as lab:
            lab.kubectl("get", "pods")
            lab.helm("list")
            lab.run(["sh", "-c", "kubectl get pods"])
            learner = lab.kubeconfig
            learner_text = learner.read_text(encoding="utf-8")
    finally:
        _AUDIT_ON.clear()
    touched = [p for p in _AUDIT_OPENED if p.startswith(str(sentinel)) or p.startswith(str(home / ".kube"))]
    assert touched == []
    assert all(env is None or "KUBECONFIG" not in env for _, env in fake.host_calls)
    for call in fake.sandbox_calls:
        assert call["env"]["KUBECONFIG"] != str(sentinel)
        assert Path(call["env"]["KUBECONFIG"]).is_relative_to(lab.root)
        assert str(sentinel) not in " ".join(call["cmd"]) and str(home / ".kube") not in " ".join(call["cmd"])
    learner_calls = [c for c in fake.sandbox_calls if c["env"]["KUBECONFIG"] == str(learner)]
    assert learner_calls and all(Path(c["env"]["HOME"]).is_relative_to(lab.root) for c in learner_calls)
    assert all(c["env"].get("KUBERC") == "off" for c in learner_calls)
    assert all(Path(c["env"][k]).is_relative_to(lab.root) for c in learner_calls
               for k in ("HELM_CACHE_HOME", "HELM_CONFIG_HOME", "HELM_DATA_HOME"))
    assert all(learner.parent in [Path(p) for p in c["readonly"]] for c in learner_calls)
    assert all(not Path(p).is_relative_to(learner.parent) for c in learner_calls for p in c["writable"])
    assert "token-cua-lab" in learner_text and "client-key-data" not in learner_text
    assert "127.0.0.1:46315" in learner_text and f"namespace: {lab.namespace}" in learner_text
    assert not lab.root.exists()


def test_kube_lab_admin_kubeconfig_never_mounted_for_learner(monkeypatch):
    fake = KubeFake(monkeypatch)
    with testkit.KubeLab() as lab:
        lab.kubectl("get", "pods")
        lab.run(["kubectl", "get", "pods"])
        admin = lab.admin_kubeconfig
    learner_calls = [c for c in fake.sandbox_calls if c["env"]["KUBECONFIG"] != str(admin)]
    assert learner_calls
    for call in learner_calls:
        assert not any(Path(p) == admin.parent or admin.is_relative_to(p) for p in [*call["readonly"], *call["writable"]])


def test_kube_lab_namespace_and_label(monkeypatch):
    fake = KubeFake(monkeypatch)
    with testkit.KubeLab() as lab:
        assert re.fullmatch(r"[0-9a-f]{8}", lab.id)
        assert lab.namespace == f"devops-ex-{lab.id}"
        assert lab.label == f"devops-ex={lab.id}"
    [bootstrap] = [c for c in fake.calls_with("apply") if c["input"] and '"Namespace"' in c["input"]]
    items = json.loads(bootstrap["input"])["items"]
    namespace = next(i for i in items if i["kind"] == "Namespace")
    assert namespace["metadata"]["name"] == lab.namespace
    labels = namespace["metadata"]["labels"]
    assert labels["devops-ex"] == lab.id and labels["pod-security.kubernetes.io/enforce"] == "baseline"
    assert all(i["metadata"]["labels"]["devops-ex"] == lab.id for i in items)
    assert {"ValidatingAdmissionPolicy", "ValidatingAdmissionPolicyBinding", "ServiceAccount", "RoleBinding"} <= {i["kind"] for i in items}
    binding = next(i for i in items if i["kind"] == "RoleBinding")
    assert binding["roleRef"] == {"apiGroup": "rbac.authorization.k8s.io", "kind": "Role", "name": "devops-ex-learner"}
    role = next(i for i in items if i["kind"] == "Role")
    verbs = {v for rule in role["rules"] for v in rule["verbs"]}
    resources = {r for rule in role["rules"] for r in rule["resources"]}
    assert not verbs & {"impersonate", "escalate", "bind", "*"} and "serviceaccounts/token" not in resources and "*" not in resources
    policies = {i["metadata"]["name"]: i for i in items if i["kind"] == "ValidatingAdmissionPolicy"}
    assert set(policies) == {lab.namespace, f"{lab.namespace}-pv", f"{lab.namespace}-rbac", f"{lab.namespace}-routes",
                             f"{lab.namespace}-argocd", f"{lab.namespace}-mesh"}
    rbac = policies[f"{lab.namespace}-rbac"]["spec"]
    assert f"'system:serviceaccounts:{lab.namespace}' in request.userInfo.groups" in rbac["matchConditions"][0]["expression"]
    assert {r["scope"] for r in rbac["matchConstraints"]["resourceRules"]} == {"*"}
    assert "aggregate-to-" in json.dumps(rbac["validations"])
    lab_condition = policies[lab.namespace]["spec"]["matchConditions"][0]["expression"]
    assert f"'system:serviceaccounts:{lab.namespace}' in request.userInfo.groups" in lab_condition
    pv_condition = policies[f"{lab.namespace}-pv"]["spec"]["matchConditions"][0]["expression"]
    assert pv_condition.startswith("!") and "system:serviceaccount:" in pv_condition and "request.dryRun == true" in pv_condition
    assert not any(i["kind"] == "ClusterRoleBinding" and i["roleRef"]["name"] in ("cluster-admin", "admin", "edit") for i in items)


def test_kube_lab_close_only_touches_own_label(monkeypatch):
    fake = KubeFake(monkeypatch)
    with testkit.KubeLab() as lab:
        pass
    deletes = fake.calls_with("delete")
    assert deletes
    for call in deletes:
        cmd = call["cmd"]
        assert ("namespace" in cmd and lab.namespace in cmd) or f"devops-ex={lab.id}" in cmd, cmd
        assert "--all" not in cmd and "--all-namespaces" not in cmd and "-A" not in cmd
        assert not any(part.split(",").count("nodes") for part in cmd)


def test_kube_lab_refuses_use_outside_with():
    lab = testkit.KubeLab()
    with pytest.raises(RuntimeError, match="with KubeLab"):
        lab.kubectl("get", "pods")


@pytest.mark.parametrize("args", [
    ("--kubeconfig", "/x", "get", "pods"),
    ("--kubeconfig=/x", "get", "pods"),
    ("get", "pods", "--context", "kind-prod"),
    ("get", "pods", "--context=kind-prod"),
    ("--cluster", "prod", "get", "pods"),
    ("--user", "admin", "get", "pods"),
    ("--server", "https://10.0.0.1:6443", "get", "pods"),
    ("-s", "https://10.0.0.1:6443", "get", "pods"),
    ("-shttps://10.0.0.1:6443", "get", "pods"),
    ("-s=https://10.0.0.1:6443", "get", "pods"),
    ("get", "pods", "-ws", "https://10.0.0.1:6443"),
    ("--token", "abc", "get", "pods"),
    ("--token=abc", "get", "pods"),
    ("--as", "system:admin", "get", "pods"),
    ("--as=system:admin", "get", "pods"),
    ("--as-group", "system:masters", "get", "pods"),
    ("--as-uid", "1", "get", "pods"),
    ("--username", "a", "get", "pods"),
    ("--password", "a", "get", "pods"),
    ("--client-certificate", "/x", "get", "pods"),
    ("--client-key", "/x", "get", "pods"),
    ("--certificate-authority", "/x", "get", "pods"),
    ("--insecure-skip-tls-verify", "get", "pods"),
    ("--tls-server-name", "x", "get", "pods"),
])
def test_kube_lab_refuses_context_switch_flags(monkeypatch, args):
    fake = KubeFake(monkeypatch)
    with testkit.KubeLab() as lab:
        before = len(fake.sandbox_calls)
        with pytest.raises(ValueError, match="kubeconfig của lab"):
            lab.kubectl(*args)
        assert len(fake.sandbox_calls) == before


@pytest.mark.parametrize("args", [
    ("list", "--kube-context", "prod"),
    ("list", "--kube-context=prod"),
    ("list", "--kubeconfig", "/x"),
    ("list", "--kube-apiserver", "https://10.0.0.1"),
    ("list", "--kube-token", "abc"),
    ("list", "--kube-as-user", "admin"),
    ("list", "--kube-as-group", "system:masters"),
    ("list", "--kube-ca-file", "/x"),
    ("list", "--kube-insecure-skip-tls-verify"),
    ("list", "--kube-tls-server-name", "x"),
])
def test_kube_lab_helm_refuses_context_switch_flags(monkeypatch, args):
    KubeFake(monkeypatch)
    with testkit.KubeLab() as lab:
        with pytest.raises(ValueError, match="kubeconfig của lab"):
            lab.helm(*args)


@pytest.mark.parametrize("args", [
    ("get", "pods", "-o", "jsonpath={.items[*].status.phase}"),
    ("get", "pods", "-ojsonpath={.items[*].status}"),
    ("logs", "deploy/api", "--since=1m"),
    ("get", "pods", "-l", "app=api", "-w"),
    ("exec", "pod/api", "--", "kubectl", "--server", "x", "--context", "y"),
    ("get", "nodes", "--show-labels"),
])
def test_kube_lab_allows_normal_flags(monkeypatch, args):
    fake = KubeFake(monkeypatch)
    with testkit.KubeLab() as lab:
        lab.kubectl(*args)
    assert fake.calls_with(*args)


@pytest.mark.parametrize("env", [{"KUBECONFIG": "/x"}, {"HOME": "/x"}, {"KUBERC": "on"}, {"HELM_CONFIG_HOME": "/x"}, {"PATH": "/x"},
                                 {"HELM_KUBECONTEXT": "prod"}, {"KUBECTL_EXTERNAL_DIFF": "x"}])
def test_kube_lab_run_env_cannot_override_lab(monkeypatch, env):
    KubeFake(monkeypatch)
    with testkit.KubeLab() as lab:
        with pytest.raises(ValueError, match="lab tự quản"):
            lab.run(["kubectl", "get", "pods"], env=env)


def test_kube_lab_run_learner_script_same_env(monkeypatch, tmp_path):
    fake = KubeFake(monkeypatch)
    with testkit.KubeLab() as lab:
        lab.kubectl("get", "pods")
        lab.run(["bash", "deploy.sh"], cwd=tmp_path, readonly=[tmp_path], env={"APP_VERSION": "1.2"})
    kubectl_call = fake.calls_with("kubectl", "get", "pods")[0]
    script_call = fake.calls_with("bash", "deploy.sh")[0]
    for key in ("KUBECONFIG", "HOME", "KUBERC", "HELM_CACHE_HOME", "HELM_CONFIG_HOME", "HELM_DATA_HOME"):
        assert script_call["env"][key] == kubectl_call["env"][key]
    assert script_call["env"]["APP_VERSION"] == "1.2"
    assert Path(tmp_path) in [Path(p) for p in script_call["readonly"]]


def kube_docs(text: str) -> list:
    import yaml

    return [d for d in yaml.safe_load_all(text) if d is not None]


POD = """apiVersion: v1
kind: Pod
metadata: {name: api%s}
spec:
  containers:
  - name: api
    image: nginx:1.30.6-alpine
%s"""

DEPLOY = """apiVersion: apps/v1
kind: Deployment
metadata: {name: api}
spec:
  selector: {matchLabels: {app: api}}
  template:
    metadata: {labels: {app: api}}
    spec:
%s      containers:
      - name: api
        image: nginx:1.30.6-alpine
"""

KUBE_BAD = {
    "foreign-namespace": ("apiVersion: v1\nkind: ConfigMap\nmetadata: {name: c, namespace: kube-system}\n", "kube-system"),
    "default-namespace": ("apiVersion: v1\nkind: ConfigMap\nmetadata: {name: c, namespace: default}\n", "default"),
    "unlabelled-cluster-role": ("apiVersion: rbac.authorization.k8s.io/v1\nkind: ClusterRole\nmetadata: {name: r}\nrules: []\n",
                                "devops-ex="),
    "cluster-role-not-allowed": ("apiVersion: rbac.authorization.k8s.io/v1\nkind: ClusterRole\nmetadata:\n  name: r\n  labels: "
                                 "{devops-ex: 'LABID'}\nrules: []\n", "allow"),
    "cluster-admin-binding": ("apiVersion: rbac.authorization.k8s.io/v1\nkind: ClusterRoleBinding\nmetadata:\n  name: b\n  labels: "
                              "{devops-ex: 'LABID'}\nroleRef: {apiGroup: rbac.authorization.k8s.io, kind: ClusterRole, name: "
                              "cluster-admin}\nsubjects:\n- {kind: ServiceAccount, name: default, namespace: LABNS}\n",
                              "cluster-admin"),
    "rolebinding-cluster-admin": ("apiVersion: rbac.authorization.k8s.io/v1\nkind: RoleBinding\nmetadata: {name: b}\nroleRef: "
                                  "{apiGroup: rbac.authorization.k8s.io, kind: ClusterRole, name: cluster-admin}\nsubjects:\n- "
                                  "{kind: ServiceAccount, name: default}\n", "cluster-admin"),
    "binding-system-group": ("apiVersion: rbac.authorization.k8s.io/v1\nkind: RoleBinding\nmetadata: {name: b}\nroleRef: "
                             "{apiGroup: rbac.authorization.k8s.io, kind: Role, name: r}\nsubjects:\n- {kind: Group, name: "
                             "system:authenticated, apiGroup: rbac.authorization.k8s.io}\n", "system:authenticated"),
    "binding-foreign-sa": ("apiVersion: rbac.authorization.k8s.io/v1\nkind: RoleBinding\nmetadata: {name: b}\nroleRef: "
                           "{apiGroup: rbac.authorization.k8s.io, kind: Role, name: r}\nsubjects:\n- {kind: ServiceAccount, name: "
                           "default, namespace: kube-system}\n", "kube-system"),
    "role-escalate": ("apiVersion: rbac.authorization.k8s.io/v1\nkind: Role\nmetadata: {name: r}\nrules:\n- {apiGroups: ['*'], "
                      "resources: ['*'], verbs: ['*']}\n", "*"),
    "role-impersonate": ("apiVersion: rbac.authorization.k8s.io/v1\nkind: Role\nmetadata: {name: r}\nrules:\n- {apiGroups: [''], "
                         "resources: [users], verbs: [impersonate]}\n", "impersonate"),
    "privileged-pod": (POD % ("", "    securityContext: {privileged: true}\n"), "privileged"),
    "privileged-init": (POD % ("", "  initContainers:\n  - name: i\n    image: x\n    securityContext: {privileged: true}\n"),
                        "privileged"),
    "host-network": (DEPLOY % "      hostNetwork: true\n", "hostNetwork"),
    "host-pid": (DEPLOY % "      hostPID: true\n", "hostPID"),
    "host-ipc": (DEPLOY % "      hostIPC: true\n", "hostIPC"),
    "host-path": (DEPLOY % "      volumes:\n      - name: root\n        hostPath: {path: /}\n", "hostPath"),
    "host-port": (POD % ("", "    ports:\n    - {containerPort: 80, hostPort: 80}\n"), "hostPort"),
    "cap-sys-admin": (POD % ("", "    securityContext: {capabilities: {add: [SYS_ADMIN]}}\n"), "SYS_ADMIN"),
    "proc-unmasked": (POD % ("", "    securityContext: {procMount: Unmasked}\n"), "procMount"),
    "seccomp-unconfined": (POD % ("", "    securityContext: {seccompProfile: {type: Unconfined}}\n"), "Unconfined"),
    "cronjob-host-path": ("apiVersion: batch/v1\nkind: CronJob\nmetadata: {name: c}\nspec:\n  schedule: '* * * * *'\n  jobTemplate:\n"
                          "    spec:\n      template:\n        spec:\n          restartPolicy: Never\n          volumes:\n          - name: "
                          "d\n            hostPath: {path: /var/run}\n          containers:\n          - {name: c, image: x}\n",
                          "hostPath"),
    "pv-host-path": ("apiVersion: v1\nkind: PersistentVolume\nmetadata:\n  name: pv\n  labels: {devops-ex: 'LABID'}\nspec:\n  "
                     "capacity: {storage: 1Gi}\n  accessModes: [ReadWriteOnce]\n  hostPath: {path: /}\n", "PersistentVolume"),
    "namespace": ("apiVersion: v1\nkind: Namespace\nmetadata:\n  name: other\n  labels: {devops-ex: 'LABID'}\n", "Namespace"),
    "namespace-psa": ("apiVersion: v1\nkind: Namespace\nmetadata:\n  name: kube-system\n  labels: {devops-ex: 'LABID'}\n", "Namespace"),
    "node": ("apiVersion: v1\nkind: Node\nmetadata:\n  name: devops-lab-worker\n  labels: {devops-ex: 'LABID'}\n", "Node"),
    "mutating-webhook": ("apiVersion: admissionregistration.k8s.io/v1\nkind: MutatingWebhookConfiguration\nmetadata:\n  name: m\n  "
                         "labels: {devops-ex: 'LABID'}\nwebhooks: []\n", "MutatingWebhookConfiguration"),
    "validating-webhook": ("apiVersion: admissionregistration.k8s.io/v1\nkind: ValidatingWebhookConfiguration\nmetadata:\n  name: "
                           "v\n  labels: {devops-ex: 'LABID'}\nwebhooks: []\n", "ValidatingWebhookConfiguration"),
    "crd-not-allowed": ("apiVersion: apiextensions.k8s.io/v1\nkind: CustomResourceDefinition\nmetadata:\n  name: "
                        "widgets.example.com\n  labels: {devops-ex: 'LABID'}\nspec: {}\n", "CustomResourceDefinition"),
    "discovered-cluster-kind": ("apiVersion: example.com/v1\nkind: Widget\nmetadata: {name: w}\n", "devops-ex="),
    "list-wrapper": ("apiVersion: v1\nkind: List\nitems:\n- apiVersion: v1\n  kind: ConfigMap\n  metadata: {name: c, namespace: "
                     "default}\n", "default"),
    "service-external-ips": ("apiVersion: v1\nkind: Service\nmetadata: {name: s}\nspec:\n  ports: [{port: 80}]\n  externalIPs: "
                             "[10.96.0.1]\n", "externalIPs"),
    "aggregation-rule": ("apiVersion: rbac.authorization.k8s.io/v1\nkind: ClusterRole\nmetadata:\n  name: r\n  labels: "
                         "{devops-ex: 'LABID'}\naggregationRule:\n  clusterRoleSelectors:\n  - matchLabels: "
                         "{rbac.authorization.k8s.io/aggregate-to-admin: 'true'}\n", "aggregationRule"),
    "storage-class": ("apiVersion: storage.k8s.io/v1\nkind: StorageClass\nmetadata:\n  name: s\n  labels: {devops-ex: 'LABID'}\n"
                      "provisioner: rancher.io/local-path\nparameters: {pathPattern: ../../run/containerd}\n", "StorageClass"),
    "priority-global-default": ("apiVersion: scheduling.k8s.io/v1\nkind: PriorityClass\nmetadata:\n  name: p\n  labels: "
                                "{devops-ex: 'LABID'}\nvalue: 1000\nglobalDefault: true\n", "globalDefault"),
    "aggregate-to-view": ("apiVersion: rbac.authorization.k8s.io/v1\nkind: ClusterRole\nmetadata:\n  name: r\n  labels: "
                          "{devops-ex: 'LABID', rbac.authorization.k8s.io/aggregate-to-view: 'true'}\nrules: []\n", "aggregate-to-view"),
    "role-aggregate-to-admin": ("apiVersion: rbac.authorization.k8s.io/v1\nkind: Role\nmetadata:\n  name: r\n  labels: "
                                "{rbac.authorization.k8s.io/aggregate-to-admin: 'true'}\nrules: []\n", "aggregate-to-admin"),
    "pv-nfs": ("apiVersion: v1\nkind: PersistentVolume\nmetadata:\n  name: pv\n  labels: {devops-ex: 'LABID'}\nspec:\n  capacity: "
               "{storage: 1Gi}\n  accessModes: [ReadWriteMany]\n  nfs: {server: 172.17.0.1, path: /}\n", "PersistentVolume"),
    "not-object": ("- a\n- b\n", "object"),
    "missing-kind": ("apiVersion: v1\nmetadata: {name: x}\n", "kind"),
}


def lab_text(text: str, lab_id: str, namespace: str) -> str:
    return text.replace("LABID", lab_id).replace("LABNS", namespace)


@pytest.mark.parametrize("name", KUBE_BAD)
def test_kube_manifest_problems_reject(name):
    text, needle = KUBE_BAD[name]
    problems = testkit.kube_manifest_problems(kube_docs(lab_text(text, "abcd1234", "devops-ex-abcd1234")), lab_id="abcd1234",
                                              namespace="devops-ex-abcd1234", cluster_kinds={"Widget"})
    assert problems and any(needle in p for p in problems), problems


def test_kube_lab_rejects_foreign_namespace(monkeypatch, tmp_path):
    fake = KubeFake(monkeypatch)
    manifest = tmp_path / "app.yaml"
    manifest.write_text("apiVersion: v1\nkind: ConfigMap\nmetadata: {name: ok}\n---\n"
                        "apiVersion: v1\nkind: ConfigMap\nmetadata: {name: c, namespace: kube-system}\n", encoding="utf-8")
    with testkit.KubeLab() as lab:
        before = len(fake.calls_with("apply"))
        with pytest.raises(pytest.fail.Exception, match="kube-system"):
            lab.apply_learner(manifest)
        assert len(fake.calls_with("apply")) == before


@pytest.mark.parametrize("name", ["privileged-pod", "host-path", "host-network", "cluster-admin-binding", "unlabelled-cluster-role"])
def test_kube_lab_apply_learner_refuses_before_apply(monkeypatch, tmp_path, name):
    fake = KubeFake(monkeypatch)
    with testkit.KubeLab(allow=("ClusterRole", "ClusterRoleBinding")) as lab:
        manifest = tmp_path / "x.yaml"
        manifest.write_text(lab_text(KUBE_BAD[name][0], lab.id, lab.namespace), encoding="utf-8")
        before = len(fake.calls_with("apply"))
        with pytest.raises(pytest.fail.Exception, match="từ chối"):
            lab.apply_learner(manifest)
        assert len(fake.calls_with("apply")) == before


KUBE_GOOD = """apiVersion: v1
kind: ConfigMap
metadata: {name: plain}
data: {a: "1"}
---
apiVersion: v1
kind: ConfigMap
metadata: {name: explicit, namespace: LABNS}
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: LABNS-reader
  labels: {devops-ex: 'LABID'}
rules:
- {apiGroups: [""], resources: [pods], verbs: [get, list]}
---
""" + DEPLOY % "      securityContext: {runAsNonRoot: true}\n"


def test_kube_lab_apply_learner_sends_exactly_what_was_checked(monkeypatch, tmp_path):
    fake = KubeFake(monkeypatch)
    with testkit.KubeLab(allow=("ClusterRole",)) as lab:
        manifest = tmp_path / "app.yaml"
        manifest.write_text(lab_text(KUBE_GOOD, lab.id, lab.namespace), encoding="utf-8")
        lab.apply_learner(manifest)
        call = fake.calls_with("apply")[-1]
    assert call["env"]["KUBECONFIG"] == str(lab.kubeconfig)
    assert call["cmd"][:2] == ["kubectl", "apply"] and "-f" in call["cmd"] and "-" in call["cmd"]
    assert ["-n", lab.namespace] == call["cmd"][call["cmd"].index("-n"):call["cmd"].index("-n") + 2]
    sent = json.loads(call["input"])
    assert sent["kind"] == "List" and sent["items"] == kube_docs(lab_text(KUBE_GOOD, lab.id, lab.namespace))


def test_kube_lab_apply_learner_directory(monkeypatch, tmp_path):
    fake = KubeFake(monkeypatch)
    (tmp_path / "a.yaml").write_text("apiVersion: v1\nkind: ConfigMap\nmetadata: {name: a}\n", encoding="utf-8")
    (tmp_path / "b.yml").write_text("apiVersion: v1\nkind: Secret\nmetadata: {name: b}\n", encoding="utf-8")
    (tmp_path / "README.md").write_text("kind: Namespace\n", encoding="utf-8")
    with testkit.KubeLab() as lab:
        lab.apply_learner(tmp_path)
        sent = json.loads(fake.calls_with("apply")[-1]["input"])
    assert [i["metadata"]["name"] for i in sent["items"]] == ["a", "b"]


def test_kube_lab_apply_learner_kustomize_rendered_then_checked(monkeypatch, tmp_path):
    fake = KubeFake(monkeypatch)
    rendered = "apiVersion: v1\nkind: ConfigMap\nmetadata: {name: c, namespace: kube-system}\n"
    original = fake.run_sandboxed

    def render(cmd, **kwargs):
        if list(map(str, cmd[:2])) == ["kubectl", "kustomize"]:
            fake.sandbox_calls.append({"cmd": list(map(str, cmd)), "env": dict(kwargs["env"]), "writable": kwargs["writable"],
                                       "readonly": list(kwargs.get("readonly", ())), "cwd": kwargs["cwd"], "input": None})
            return subprocess.CompletedProcess(cmd, 0, rendered, "")
        return original(cmd, **kwargs)

    monkeypatch.setattr(testkit, "run_sandboxed", render)
    (tmp_path / "kustomization.yaml").write_text("resources: [cm.yaml]\nnamespace: kube-system\n", encoding="utf-8")
    (tmp_path / "cm.yaml").write_text("apiVersion: v1\nkind: ConfigMap\nmetadata: {name: c}\n", encoding="utf-8")
    with testkit.KubeLab() as lab:
        before = len(fake.calls_with("apply"))
        with pytest.raises(pytest.fail.Exception, match="kube-system"):
            lab.apply_learner(tmp_path)
        assert len(fake.calls_with("apply")) == before
    [kustomize] = fake.calls_with("kustomize")
    assert Path(tmp_path) in [Path(p) for p in kustomize["readonly"]]


def test_kube_lab_apply_learner_refuses_symlink_and_alias(monkeypatch, tmp_path):
    fake = KubeFake(monkeypatch)
    secret = tmp_path / "secret.txt"
    secret.write_text("khoa-bi-mat: 1\n", encoding="utf-8")
    project = tmp_path / "k8s"
    project.mkdir()
    (project / "a.yaml").symlink_to(secret)
    bomb = tmp_path / "bomb.yaml"
    bomb.write_text("apiVersion: v1\nkind: ConfigMap\nmetadata: {name: c}\ndata:\n  a: &a x\n  b: *a\n", encoding="utf-8")
    deep = tmp_path / "deep.yaml"
    deep.write_text("apiVersion: v1\nkind: ConfigMap\nmetadata: {name: c}\ndata: " + "[" * 5000 + "]" * 5000 + "\n",
                    encoding="utf-8")
    with testkit.KubeLab() as lab:
        with pytest.raises(pytest.fail.Exception, match="symlink"):
            lab.apply_learner(project)
        with pytest.raises(pytest.fail.Exception, match="alias"):
            lab.apply_learner(bomb)
        with pytest.raises(pytest.fail.Exception, match="sâu|YAML"):
            lab.apply_learner(deep)
        assert fake.calls_with("apply", "-n") == []


@pytest.mark.parametrize("value", ["", "privileged", "Baseline"])
def test_kube_lab_rejects_bad_pod_security(value):
    with pytest.raises(ValueError):
        testkit.KubeLab(pod_security=value)


def test_kube_lab_rejects_unknown_allow():
    with pytest.raises(ValueError, match="Node"):
        testkit.KubeLab(allow=("Node",))
    with pytest.raises(ValueError, match="MutatingWebhookConfiguration"):
        testkit.KubeLab(allow=("MutatingWebhookConfiguration",))


@pytest.mark.parametrize("node", [
    "devops-lab", "devops-lab-", "devops-lab-worker-x", "devops-lab-workerx", "devops-lab-control-plane2", "devops-lab-worker2 ",
    " devops-lab-worker", "devops-lab-worker;id", "--privileged", "-u", "other-lab-worker", "de-learning-postgres-1", "portainer",
    "neo4j-fnb", "fnb-postgres-1", "DEVOPS-LAB-WORKER", "devops-lab-worker\n", "devops-lab-control-plane/../x",
])
def test_kind_node_exec_only_devops_lab(monkeypatch, node):
    fake = KubeFake(monkeypatch)
    with pytest.raises(ValueError, match="devops-lab"):
        testkit.kind_node_exec(node, "true")
    with pytest.raises(ValueError, match="devops-lab"):
        testkit.kind_node_cp(node, "/etc/hostname", Path("/tmp/x"))
    assert fake.host_calls == []


def test_kind_node_exec_requires_kind_label(monkeypatch):
    KubeFake(monkeypatch, labels={"devops-lab-worker": ""})
    with pytest.raises(ValueError, match="không phải node"):
        testkit.kind_node_exec("devops-lab-worker", "true")


@pytest.mark.parametrize("cmd", [(), ("sh", "-c", "id"), ("/bin/bash", "-c", "id"), ("bash", "x.sh"), ("dash",), ("busybox", "sh")])
def test_kind_node_exec_refuses_shell_and_empty(monkeypatch, cmd):
    fake = KubeFake(monkeypatch)
    with pytest.raises(ValueError):
        testkit.kind_node_exec("devops-lab-control-plane", *cmd)
    assert not any(c[:2] == ["docker", "exec"] for c, _ in fake.host_calls)


def test_kind_node_exec_argv_after_container(monkeypatch):
    fake = KubeFake(monkeypatch)
    testkit.kind_node_exec("devops-lab-worker2", "cat", "/etc/hostname; id")
    [(cmd, env)] = [(c, e) for c, e in fake.host_calls if c[:2] == ["docker", "exec"]]
    assert cmd[-3:] == ["devops-lab-worker2", "cat", "/etc/hostname; id"]
    assert env is not None and "KUBECONFIG" not in env


@pytest.mark.parametrize("node_path,local", [("etc/hostname", "/tmp/x"), ("/etc/hostname", "-"), ("-", "/tmp/x")])
def test_kind_node_cp_refuses_bad_paths(monkeypatch, node_path, local):
    KubeFake(monkeypatch)
    with pytest.raises(ValueError):
        testkit.kind_node_cp("devops-lab-control-plane", node_path, local)


def test_kind_node_cp_directions(monkeypatch, tmp_path):
    fake = KubeFake(monkeypatch)
    testkit.kind_node_cp("devops-lab-control-plane", "/etc/hostname", tmp_path / "h")
    testkit.kind_node_cp("devops-lab-control-plane", tmp_path / "h", "/tmp/in", to_node=True)
    cps = [c for c, _ in fake.host_calls if c[:2] == ["docker", "cp"]]
    assert cps[0][2:] == ["devops-lab-control-plane:/etc/hostname", str(tmp_path / "h")]
    assert cps[1][2:] == [str(tmp_path / "h"), "devops-lab-control-plane:/tmp/in"]


def test_kind_config_pinned_and_local_only():
    import yaml

    config = yaml.safe_load((testkit.ROOT / "setup" / "kind" / "devops-lab.yaml").read_text(encoding="utf-8"))
    assert config["name"] == "devops-lab"
    assert config["networking"]["apiServerAddress"] == "127.0.0.1"
    roles = [n["role"] for n in config["nodes"]]
    assert roles == ["control-plane", "worker", "worker"]
    assert {n["image"] for n in config["nodes"]} == {testkit.KIND_NODE_IMAGE}
    assert re.fullmatch(r"kindest/node:v1\.34\.\d+@sha256:[0-9a-f]{64}", testkit.KIND_NODE_IMAGE)
    mappings = [m for n in config["nodes"] for m in n.get("extraPortMappings", [])]
    assert mappings and all(m["listenAddress"] == "127.0.0.1" for m in mappings)


def test_kind_lifecycle_documented():
    doc = (testkit.ROOT / "setup" / "DEVOPS-TOOLS.md").read_text(encoding="utf-8")
    assert testkit.KUBE_CREATE in doc
    assert 'docker update --cpuset-cpus "$DEVOPS_CPUSET"' in doc
    for command in ("docker stop $(kind get nodes --name devops-lab)", "docker start $(kind get nodes --name devops-lab)",
                    "kind delete cluster --name devops-lab"):
        assert command in doc
    for version in (testkit.KUBECTL_VERSION, testkit.HELM_VERSION):
        assert f"v{version}" in doc
    assert "kind create cluster --config setup/kind/devops-lab.yaml\n" not in doc


KUBE_REQUIRED = pytest.mark.skipif(not shutil.which("kind") or not shutil.which("kubectl"), reason="Cần kind và kubectl")


def admin_kubectl(*args, input=None):
    """kubectl thô bằng kubeconfig admin tạm (lấy bằng kind get kubeconfig), không qua kiểm tĩnh hay quyền của KubeLab."""
    import tempfile

    text = subprocess.run(["kind", "get", "kubeconfig", "--name", "devops-lab"], capture_output=True, text=True, check=True,
                          env=testkit._docker_env()).stdout
    with tempfile.TemporaryDirectory(prefix="devops-ex-admin-") as tmp:
        path = Path(tmp) / "kubeconfig"
        path.write_text(text, encoding="utf-8")
        env = {"PATH": os.environ["PATH"], "HOME": tmp, "KUBECONFIG": str(path), "KUBERC": "off"}
        return subprocess.run(["kubectl", *args], capture_output=True, text=True, env=env, input=input, timeout=60)


PRIVILEGED_POD = """apiVersion: v1
kind: Pod
metadata: {name: escape}
spec:
  containers:
  - name: c
    image: registry.k8s.io/e2e-test-images/agnhost:2.53
    securityContext: {privileged: true}
"""

HOSTPATH_POD = """apiVersion: v1
kind: Pod
metadata: {name: hostroot}
spec:
  containers:
  - name: c
    image: registry.k8s.io/e2e-test-images/agnhost:2.53
    volumeMounts: [{name: root, mountPath: /host}]
  volumes:
  - name: root
    hostPath: {path: /}
"""


@KUBE_REQUIRED
def test_kube_lab_cleans_namespace():
    with testkit.KubeLab() as lab:
        lab.kubectl("create", "configmap", "probe", "--from-literal=a=1")
        assert lab.kubectl("get", "configmap", "probe", "-o", "jsonpath={.data.a}").stdout == "1"
        labels = json.loads(admin_kubectl("get", "namespace", lab.namespace, "-o", "json").stdout)["metadata"]["labels"]
        assert labels["devops-ex"] == lab.id and labels["pod-security.kubernetes.io/enforce"] == "baseline"
    assert testkit.kube_leftovers(lab.id) == []
    assert admin_kubectl("get", "namespace", lab.namespace).returncode != 0
    assert not lab.root.exists()


@KUBE_REQUIRED
def test_kube_lab_cleans_namespace_on_error():
    lab = testkit.KubeLab(allow=("ClusterRole",))
    with pytest.raises(RuntimeError, match="giữa chừng"):
        with lab:
            lab.kubectl("create", "configmap", "probe")
            lab.kubectl("apply", "-f", "-", input=json.dumps({
                "apiVersion": "rbac.authorization.k8s.io/v1", "kind": "ClusterRole",
                "metadata": {"name": f"{lab.namespace}-r", "labels": {"devops-ex": lab.id}}, "rules": []}))
            raise RuntimeError("lỗi giữa chừng")
    assert testkit.kube_leftovers(lab.id) == []
    assert admin_kubectl("get", "clusterrole", f"{lab.namespace}-r").returncode != 0


@KUBE_REQUIRED
@pytest.mark.parametrize("manifest,name", [(PRIVILEGED_POD, "escape"), (HOSTPATH_POD, "hostroot")])
def test_kube_lab_psa_blocks_host_access_without_static_check(manifest, name):
    with testkit.KubeLab() as lab:
        as_learner = lab.kubectl("apply", "-f", "-", input=manifest, check=False)
        assert as_learner.returncode != 0 and "violates PodSecurity" in as_learner.stderr, as_learner.stderr
        as_admin = admin_kubectl("-n", lab.namespace, "apply", "-f", "-", input=manifest)
        assert as_admin.returncode != 0 and "violates PodSecurity" in as_admin.stderr, as_admin.stderr
        assert admin_kubectl("-n", lab.namespace, "get", "pod", name).returncode != 0


@KUBE_REQUIRED
def test_kube_lab_learner_credentials_stay_in_namespace():
    with testkit.KubeLab() as lab:
        other = lab.kubectl("-n", "default", "create", "configmap", f"{lab.namespace}-x", check=False)
        assert other.returncode != 0 and "forbidden" in other.stderr.lower(), other.stderr
        label = lab.kubectl("label", "namespace", lab.namespace, "pod-security.kubernetes.io/enforce-", check=False)
        assert label.returncode != 0 and "forbidden" in label.stderr.lower(), label.stderr
        role = lab.kubectl("create", "clusterrolebinding", f"{lab.namespace}-x", "--clusterrole=cluster-admin",
                           f"--serviceaccount={lab.namespace}:default", check=False)
        assert role.returncode != 0 and "forbidden" in role.stderr.lower(), role.stderr
        assert lab.kubectl("auth", "can-i", "create", "pods", "--subresource=exec").stdout.strip() == "yes"
        assert lab.kubectl("auth", "can-i", "create", "pods", "-n", "kube-system", check=False).stdout.strip() == "no"
        assert lab.kubectl("auth", "can-i", "get", "secrets", "-n", "kube-system", check=False).stdout.strip() == "no"
        assert lab.kubectl("auth", "can-i", "patch", "nodes", check=False).stdout.strip() == "no"
        assert lab.kubectl("get", "nodes", "-o", "name").stdout.count("node/") == 3


@KUBE_REQUIRED
def test_kube_lab_cluster_scoped_objects_need_label_in_cluster():
    with testkit.KubeLab(allow=("ClusterRole",)) as lab:
        role = {"apiVersion": "rbac.authorization.k8s.io/v1", "kind": "ClusterRole", "metadata": {"name": f"{lab.namespace}-r"},
                "rules": []}
        unlabelled = lab.kubectl("apply", "-f", "-", input=json.dumps(role), check=False)
        assert unlabelled.returncode != 0 and "devops-ex" in unlabelled.stderr, unlabelled.stderr
        role["metadata"]["labels"] = {"devops-ex": lab.id}
        lab.kubectl("apply", "-f", "-", input=json.dumps(role))
        foreign = lab.kubectl("delete", "clusterrole", "view", check=False)
        assert foreign.returncode != 0, foreign.stderr
        relabel = lab.kubectl("label", "clusterrole", "edit", f"devops-ex={lab.id}", check=False)
        assert relabel.returncode != 0, relabel.stderr
    assert admin_kubectl("get", "clusterrole", "view").returncode == 0
    assert testkit.kube_leftovers(lab.id) == []


@KUBE_REQUIRED
def test_kube_lab_apply_learner_real(tmp_path):
    manifest = tmp_path / "app.yaml"
    manifest.write_text(DEPLOY.replace("nginx:1.30.6-alpine", "registry.k8s.io/e2e-test-images/agnhost:2.53") % "", encoding="utf-8")
    with testkit.KubeLab() as lab:
        lab.apply_learner(manifest)
        assert lab.kubectl("get", "deploy", "api", "-o", "jsonpath={.metadata.namespace}").stdout == lab.namespace


@KUBE_REQUIRED
def test_kube_lab_helm_install_checks_rendered_chart(tmp_path):
    chart = tmp_path / "chart"
    (chart / "templates").mkdir(parents=True)
    (chart / "Chart.yaml").write_text("apiVersion: v2\nname: probe\nversion: 0.1.0\n", encoding="utf-8")
    (chart / "values.yaml").write_text("privileged: false\n", encoding="utf-8")
    (chart / "templates" / "cm.yaml").write_text(
        "apiVersion: v1\nkind: ConfigMap\nmetadata: {name: {{ .Release.Name }}-cm}\ndata: {a: '1'}\n", encoding="utf-8")
    (chart / "templates" / "pod.yaml").write_text(
        "{{- if .Values.privileged }}\n" + PRIVILEGED_POD + "{{- end }}\n", encoding="utf-8")
    with testkit.KubeLab() as lab:
        lab.helm_install("probe", chart)
        assert lab.kubectl("get", "configmap", "probe-cm", "-o", "jsonpath={.data.a}").stdout == "1"
        assert "probe" in lab.helm("list", "-q").stdout
        with pytest.raises(pytest.fail.Exception, match="privileged"):
            lab.helm_install("probe2", chart, "--set", "privileged=true")
        assert "probe2" not in lab.helm("list", "-q").stdout
    assert testkit.kube_leftovers(lab.id) == []


@KUBE_REQUIRED
def test_kube_lab_ignores_user_kubeconfig_real(monkeypatch, tmp_path):
    sentinel = tmp_path / "sentinel"
    sentinel.write_text(ADMIN_KUBECONFIG.replace("46315", "1"), encoding="utf-8")
    home = tmp_path / "home"
    (home / ".kube").mkdir(parents=True)
    (home / ".kube" / "config").write_text(ADMIN_KUBECONFIG.replace("46315", "2"), encoding="utf-8")
    monkeypatch.setenv("KUBECONFIG", str(sentinel))
    monkeypatch.setenv("HOME", str(home))
    with testkit.KubeLab() as lab:
        server = lab.kubectl("config", "view", "--minify", "-o", "jsonpath={.clusters[0].cluster.server}").stdout
        assert server.startswith("https://127.0.0.1:") and not server.endswith((":1", ":2"))
        assert lab.kubectl("get", "--raw", "/readyz").stdout == "ok"
        script = lab.run(["sh", "-c", "kubectl config view --minify -o jsonpath='{.contexts[0].context.namespace}'; "
                                      "ls ~/.kube/config 2>/dev/null; echo; echo $KUBECONFIG"])
        lines = script.stdout.splitlines()
        assert lines[0] == lab.namespace and lines[-1] == str(lab.kubeconfig)
    assert sentinel.read_text(encoding="utf-8").count("127.0.0.1:1") == 1


@KUBE_REQUIRED
def test_kube_lab_kubeconfig_read_only_for_learner():
    with testkit.KubeLab() as lab:
        before = lab.kubeconfig.read_text(encoding="utf-8")
        result = lab.kubectl("config", "set-context", "--current", "--namespace=default", check=False)
        assert result.returncode != 0
        script = lab.run(["sh", "-c", f"echo x >> {lab.kubeconfig}"])
        assert script.returncode != 0
        assert lab.kubeconfig.read_text(encoding="utf-8") == before


@KUBE_REQUIRED
def test_kind_node_exec_and_cp_real(tmp_path):
    testkit.Exercise.require_cluster()
    result = testkit.kind_node_exec("devops-lab-control-plane", "cat", "/etc/kubernetes/manifests/etcd.yaml")
    assert result.returncode == 0 and "etcd" in result.stdout
    testkit.kind_node_cp("devops-lab-control-plane", "/etc/kubernetes/manifests/etcd.yaml", tmp_path / "etcd.yaml")
    assert "etcd" in (tmp_path / "etcd.yaml").read_text(encoding="utf-8")
    (tmp_path / "in.txt").write_text("devops-ex\n", encoding="utf-8")
    target = f"/root/devops-ex-{os.getpid()}.txt"
    testkit.kind_node_cp("devops-lab-worker", tmp_path / "in.txt", target, to_node=True)
    try:
        assert testkit.kind_node_exec("devops-lab-worker", "cat", target).stdout == "devops-ex\n"
    finally:
        testkit.kind_node_exec("devops-lab-worker", "rm", "-f", target)


@KUBE_REQUIRED
@pytest.mark.skipif(os.environ.get("DEVOPS_KIND_STOP_PROOF") != "1",
                    reason="Chỉ chạy khi DEVOPS_KIND_STOP_PROOF=1 (dừng rồi bật lại một worker của devops-lab)")
def test_require_cluster_stopped_node_real():
    testkit.Exercise.require_cluster()
    subprocess.run(["docker", "stop", "devops-lab-worker2"], check=True, capture_output=True, timeout=60)
    try:
        started = time.monotonic()
        with pytest.raises(pytest.skip.Exception) as info:
            testkit.Exercise.require_cluster()
        assert time.monotonic() - started < 15
        assert_skip(info, "node đang dừng", "docker start devops-lab-worker2")
    finally:
        subprocess.run(["docker", "start", "devops-lab-worker2"], check=True, capture_output=True, timeout=60)
    deadline = time.monotonic() + 120
    while time.monotonic() < deadline:
        ready = admin_kubectl("wait", "--for=condition=Ready", "node/devops-lab-worker2", "--timeout=10s")
        if ready.returncode == 0:
            break
    testkit.Exercise.require_cluster()


AGNHOST = "registry.k8s.io/e2e-test-images/agnhost:2.53"


def lab_pod(lab, name: str, *, service_account: str | None = None, volumes=(), node: str | None = None) -> None:
    spec = {"containers": [{"name": "c", "image": AGNHOST, "args": ["pause"],
                            "volumeMounts": [{"name": v, "mountPath": f"/mnt/{v}"} for v, _ in volumes]}],
            "volumes": [{"name": v, "persistentVolumeClaim": {"claimName": claim}} for v, claim in volumes],
            "terminationGracePeriodSeconds": 0}
    if service_account:
        spec["serviceAccountName"] = service_account
    if node:
        spec["nodeSelector"] = {"kubernetes.io/hostname": node}
    lab.kubectl("apply", "-f", "-", input=json.dumps({"apiVersion": "v1", "kind": "Pod", "metadata": {"name": name}, "spec": spec}))
    lab.kubectl("wait", "--for=condition=Ready", f"pod/{name}", "--timeout=180s", timeout=200)


def hostpath_pv(name: str, path: str, labels=None) -> str:
    return json.dumps({"apiVersion": "v1", "kind": "PersistentVolume", "metadata": {"name": name, "labels": labels or {}},
                       "spec": {"capacity": {"storage": "1Gi"}, "accessModes": ["ReadWriteOnce"], "hostPath": {"path": path},
                                "persistentVolumeReclaimPolicy": "Retain"}})


@KUBE_REQUIRED
def test_kube_lab_second_service_account_cannot_bypass_policy():
    with testkit.KubeLab(allow=("ClusterRoleBinding", "ClusterRole")) as lab:
        lab.kubectl("create", "serviceaccount", "foo")
        lab.kubectl("apply", "-f", "-", input=json.dumps({
            "apiVersion": "rbac.authorization.k8s.io/v1", "kind": "ClusterRoleBinding",
            "metadata": {"name": f"{lab.namespace}-foo", "labels": {"devops-ex": lab.id}},
            "roleRef": {"apiGroup": "rbac.authorization.k8s.io", "kind": "ClusterRole", "name": f"{lab.namespace}-write"},
            "subjects": [{"kind": "ServiceAccount", "name": "foo", "namespace": lab.namespace}]}))
        assert lab.kubectl("auth", "can-i", "create", "serviceaccounts", "--subresource=token", check=False).stdout.strip() == "no"
        assert lab.kubectl("auth", "can-i", "impersonate", "serviceaccounts", check=False).stdout.strip() == "no"
        token = lab.kubectl("create", "token", "foo", check=False)
        assert token.returncode != 0 and "forbidden" in token.stderr.lower(), token.stderr
        impersonated = lab.run(["kubectl", f"--as=system:serviceaccount:{lab.namespace}:foo", "get", "pods"])
        assert impersonated.returncode != 0 and "forbidden" in impersonated.stderr.lower(), impersonated.stderr
        lab_pod(lab, "tok", service_account="foo")
        secret = lab.kubectl("exec", "tok", "--", "cat", "/var/run/secrets/kubernetes.io/serviceaccount/token").stdout.strip()

        def as_foo(*args, input=None):
            return lab.run(["kubectl", f"--token={secret}", *args], input=input)

        assert as_foo("auth", "whoami", "-o", "jsonpath={.status.userInfo.username}").stdout == \
            f"system:serviceaccount:{lab.namespace}:foo"
        for pv in (hostpath_pv(f"{lab.namespace}-a", "/run/containerd"),
                   hostpath_pv(f"{lab.namespace}-b", "/run/containerd", {"devops-ex": lab.id})):
            created = as_foo("create", "-f", "-", input=pv)
            assert created.returncode != 0 and ("denied" in created.stderr or "forbidden" in created.stderr), created.stderr
        unlabelled = as_foo("create", "clusterrolebinding", f"{lab.namespace}-x", f"--clusterrole={lab.namespace}-write",
                            f"--serviceaccount={lab.namespace}:foo")
        assert unlabelled.returncode != 0 and "denied" in unlabelled.stderr, unlabelled.stderr
        removed = as_foo("delete", "clusterrolebinding", "cluster-admin", "--dry-run=server")
        assert removed.returncode != 0 and "denied" in removed.stderr, removed.stderr
    assert admin_kubectl("get", "clusterrolebinding", "cluster-admin").returncode == 0
    assert admin_kubectl("get", "pv", f"{lab.namespace}-a").returncode != 0


@KUBE_REQUIRED
def test_kube_lab_storage_class_refused():
    with pytest.raises(ValueError, match="StorageClass"):
        testkit.KubeLab(allow=("StorageClass",))
    traversal = {"apiVersion": "storage.k8s.io/v1", "kind": "StorageClass",
                 "metadata": {"name": "x", "labels": {"devops-ex": "abcd1234"}}, "provisioner": "rancher.io/local-path",
                 "parameters": {"pathPattern": "../../run/containerd"}}
    assert testkit.kube_manifest_problems([traversal], lab_id="abcd1234", namespace="devops-ex-abcd1234",
                                          allow=tuple(testkit.KUBE_ALLOWABLE))
    with testkit.KubeLab(allow=tuple(testkit.KUBE_ALLOWABLE)) as lab:
        traversal["metadata"] = {"name": f"{lab.namespace}-sc", "labels": {"devops-ex": lab.id}}
        created = lab.kubectl("create", "-f", "-", input=json.dumps(traversal), check=False)
        assert created.returncode != 0 and "forbidden" in created.stderr.lower(), created.stderr
    assert admin_kubectl("get", "storageclass", f"{lab.namespace}-sc").returncode != 0


def test_sandbox_cannot_read_documented_admin_kubeconfig(tmp_path):
    assert ".kube" in testkit.CREDENTIAL_PATHS and ".cache/devops-track/kube" in testkit.CREDENTIAL_PATHS
    assert testkit.KUBE_KUBECONFIG_HINT.startswith("~/.kube/")
    folder = Path(pwd.getpwuid(os.getuid()).pw_dir) / ".cache" / "devops-track" / "kube"
    created = not folder.exists()
    folder.mkdir(parents=True, exist_ok=True)
    probe = folder / f"probe-{os.getpid()}.yaml"
    probe.write_text("kind: Config\n", encoding="utf-8")
    try:
        result = testkit.run_sandboxed(["cat", str(probe)], writable=[tmp_path], cwd=tmp_path, env={})
        assert result.returncode != 0 and "kind: Config" not in result.stdout
    finally:
        probe.unlink()
        if created:
            folder.rmdir()


LOCAL_PV = {"name": "data", "capacity": "1Gi", "node": "devops-lab-worker"}


@pytest.mark.parametrize("change,needle", [
    ({"node": "devops-lab-control-plane"}, "control plane"),
    ({"node": "devops-lab-worker9"}, "worker"),
    ({"node": "de-learning-postgres-1"}, "worker"),
    ({"capacity": "1Ti"}, "capacity"),
    ({"capacity": "-1Gi"}, "capacity"),
    ({"name": "../x"}, "name"),
    ({"name": "Data"}, "name"),
    ({"accessModes": ["ReadWriteMany"]}, "accessModes"),
    ({"storageClassName": "standard"}, "storageClassName"),
    ({"claim": "a/b"}, "claim"),
    ({"path": "/"}, "không nhận"),
    ({"hostPath": {"path": "/"}}, "không nhận"),
])
def test_kube_lab_admin_local_pv_validates_spec(monkeypatch, change, needle):
    fake = KubeFake(monkeypatch)
    with testkit.KubeLab() as lab:
        before = len(fake.host_calls)
        with pytest.raises(ValueError, match=needle):
            lab.admin_local_pv({**LOCAL_PV, **change})
        assert not any(c[:2] == ["docker", "exec"] for c, _ in fake.host_calls[before:])
        assert not [c for c in fake.calls_with("apply") if c["input"] and '"kind": "PersistentVolume"' in c["input"]]


def test_kube_lab_admin_local_pv_object(monkeypatch):
    fake = KubeFake(monkeypatch)
    with testkit.KubeLab() as lab:
        name = lab.admin_local_pv({**LOCAL_PV, "claim": "db", "storageClassName": "lab-local"})
        [call] = [c for c in fake.calls_with("apply") if c["input"] and '"kind": "PersistentVolume"' in c["input"]]
    volume = json.loads(call["input"])
    assert name == volume["metadata"]["name"] == f"{lab.namespace}-data"
    assert call["env"]["KUBECONFIG"] == str(lab.admin_kubeconfig)
    spec = volume["spec"]
    assert spec["local"] == {"path": f"/srv/devops-lab-pv/{lab.id}/data"} and "hostPath" not in spec
    assert spec["claimRef"]["namespace"] == lab.namespace and spec["claimRef"]["name"] == "db"
    assert spec["nodeAffinity"]["required"]["nodeSelectorTerms"][0]["matchExpressions"][0]["values"] == ["devops-lab-worker"]
    assert volume["metadata"]["labels"] == {"devops-ex": lab.id} and spec["persistentVolumeReclaimPolicy"] == "Retain"
    execs = [c for c, _ in fake.host_calls if c[:2] == ["docker", "exec"]]
    assert ["docker", "exec", "devops-lab-worker", "mkdir", "-p", f"/srv/devops-lab-pv/{lab.id}/data"] in execs
    assert ["docker", "exec", "devops-lab-worker", "rm", "-rf", f"/srv/devops-lab-pv/{lab.id}"] in execs


@pytest.mark.parametrize("spec,needle", [
    ({"action": "cordon", "node": "devops-lab-control-plane"}, "control plane"),
    ({"action": "drain", "node": "devops-lab-control-plane"}, "control plane"),
    ({"action": "taint", "node": "devops-lab-control-plane", "taint": {"key": "a", "effect": "NoSchedule"}}, "control plane"),
    ({"action": "delete", "node": "devops-lab-worker"}, "action"),
    ({"action": "drain", "node": "devops-lab-worker", "flags": ["--disable-eviction"]}, "không nhận"),
    ({"action": "taint", "node": "devops-lab-worker"}, "taint"),
    ({"action": "cordon", "node": "devops-lab-worker", "taint": {"key": "a", "effect": "NoSchedule"}}, "taint"),
    ({"action": "taint", "node": "devops-lab-worker", "taint": {"key": "node.kubernetes.io/unschedulable", "effect": "NoSchedule"}},
     "taint"),
    ({"action": "taint", "node": "devops-lab-worker", "taint": {"key": "a", "effect": "Never"}}, "taint"),
    ({"action": "taint", "node": "devops-lab-worker", "taint": {"key": "a b", "effect": "NoSchedule"}}, "taint"),
    ({"action": "taint", "node": "devops-lab-worker", "taint": {"key": "a", "value": "x;y", "effect": "NoSchedule"}}, "taint"),
])
def test_kube_lab_node_action_validates_spec(monkeypatch, spec, needle):
    fake = KubeFake(monkeypatch)
    with testkit.KubeLab() as lab:
        before = len(fake.sandbox_calls)
        with pytest.raises(ValueError, match=needle):
            lab.node_action(spec)
        assert len(fake.sandbox_calls) == before


def test_kube_lab_node_action_argv_and_restore(monkeypatch):
    fake = KubeFake(monkeypatch)
    with testkit.KubeLab() as lab:
        lab.node_action({"action": "drain", "node": "devops-lab-worker2"})
        lab.node_action({"action": "taint", "node": "devops-lab-worker", "taint": {"key": "lab/gpu", "value": "a", "effect": "NoSchedule"}})
        lab.node_action({"action": "cordon", "node": "devops-lab-worker"})
        lab.node_action({"action": "uncordon", "node": "devops-lab-worker"})
        during = len(fake.sandbox_calls)
    cmds = [c["cmd"] for c in fake.sandbox_calls]
    assert ["kubectl", "drain", "devops-lab-worker2", "--ignore-daemonsets", "--delete-emptydir-data", "--timeout=120s"] in cmds
    assert ["kubectl", "taint", "nodes", "devops-lab-worker", "lab/gpu=a:NoSchedule"] in cmds
    assert not any("--disable-eviction" in c for c in cmds)
    after = [c["cmd"] for c in fake.sandbox_calls[during:]]
    assert ["kubectl", "uncordon", "devops-lab-worker2"] in after and ["kubectl", "uncordon", "devops-lab-worker"] not in after
    assert ["kubectl", "taint", "nodes", "devops-lab-worker", "lab/gpu:NoSchedule-"] in after
    assert all(c["env"]["KUBECONFIG"] == str(lab.admin_kubeconfig) for c in fake.sandbox_calls
               if c["cmd"][1:2] in (["drain"], ["taint"], ["cordon"], ["uncordon"]))


def local_pvc(name: str, volume: str = "", storage_class: str | None = "lab-local") -> str:
    spec = {"accessModes": ["ReadWriteOnce"], "resources": {"requests": {"storage": "100Mi"}}}
    if storage_class is not None:
        spec["storageClassName"] = storage_class
    if volume:
        spec["volumeName"] = volume
    return json.dumps({"apiVersion": "v1", "kind": "PersistentVolumeClaim", "metadata": {"name": name}, "spec": spec})


@KUBE_REQUIRED
def test_kube_lab_admin_local_pv_real():
    with testkit.KubeLab() as lab:
        with pytest.raises(ValueError, match="control plane"):
            lab.admin_local_pv({**LOCAL_PV, "node": "devops-lab-control-plane"})
        volume = lab.admin_local_pv({**LOCAL_PV, "storageClassName": "lab-local"})
        lab.kubectl("apply", "-f", "-", input=local_pvc("data"))
        lab_pod(lab, "writer", volumes=[("data", "data")])
        lab.kubectl("exec", "writer", "--", "sh", "-c", "echo devops-ex > /mnt/data/probe")
        assert lab.kubectl("get", "pvc", "data", "-o", "jsonpath={.spec.volumeName}").stdout == volume
        assert lab.kubectl("get", "pod", "writer", "-o", "jsonpath={.spec.nodeName}").stdout == "devops-lab-worker"
        stored = testkit.kind_node_exec("devops-lab-worker", "cat", f"/srv/devops-lab-pv/{lab.id}/data/probe")
        assert stored.stdout == "devops-ex\n"
    assert testkit.kube_leftovers(lab.id) == []
    assert admin_kubectl("get", "pv", volume).returncode != 0
    assert testkit.kind_node_exec("devops-lab-worker", "test", "-e", f"/srv/devops-lab-pv/{lab.id}").returncode != 0


@KUBE_REQUIRED
def test_kube_lab_pvc_volume_name_cannot_take_other_lab_volume():
    with testkit.KubeLab() as owner, testkit.KubeLab() as other:
        volume = owner.admin_local_pv({**LOCAL_PV, "storageClassName": "lab-local"})
        other.kubectl("apply", "-f", "-", input=local_pvc("data", volume))
        time.sleep(8)
        assert other.kubectl("get", "pvc", "data", "-o", "jsonpath={.status.phase}").stdout == "Pending"
        claim = json.loads(admin_kubectl("get", "pv", volume, "-o", "json").stdout)["spec"]["claimRef"]
        assert claim["namespace"] == owner.namespace
        local = other.kubectl("apply", "-f", "-", input=json.dumps({
            "apiVersion": "v1", "kind": "PersistentVolume", "metadata": {"name": f"{other.namespace}-x"},
            "spec": {"capacity": {"storage": "1Gi"}, "accessModes": ["ReadWriteOnce"],
                     "local": {"path": f"/srv/devops-lab-pv/{owner.id}/data"},
                     "nodeAffinity": {"required": {"nodeSelectorTerms": [{"matchExpressions": [
                         {"key": "kubernetes.io/hostname", "operator": "In", "values": ["devops-lab-worker"]}]}]}}}}), check=False)
        assert local.returncode != 0 and "forbidden" in local.stderr.lower(), local.stderr


@KUBE_REQUIRED
def test_kube_lab_sweeps_unlabelled_volume_of_its_claims():
    with testkit.KubeLab() as lab:
        lab.kubectl("apply", "-f", "-", input=local_pvc("dyn", storage_class="standard"))
        lab_pod(lab, "user", volumes=[("dyn", "dyn")])
        volume = lab.kubectl("get", "pvc", "dyn", "-o", "jsonpath={.spec.volumeName}").stdout
        assert volume and "devops-ex" not in json.loads(admin_kubectl("get", "pv", volume, "-o", "json").stdout)["metadata"].get(
            "labels", {})
    assert admin_kubectl("get", "pv", volume).returncode != 0


@KUBE_REQUIRED
def test_kube_lab_node_action_real():
    def node(name):
        return json.loads(admin_kubectl("get", "node", name, "-o", "json").stdout)["spec"]

    with testkit.KubeLab() as lab:
        with pytest.raises(ValueError, match="control plane"):
            lab.node_action({"action": "cordon", "node": "devops-lab-control-plane"})
        lab.node_action({"action": "taint", "node": "devops-lab-worker", "taint": {"key": "lab/maint", "effect": "NoSchedule"}})
        lab.node_action({"action": "drain", "node": "devops-lab-worker2"})
        assert node("devops-lab-worker2").get("unschedulable") is True
        assert any(t["key"] == "lab/maint" for t in node("devops-lab-worker").get("taints", []))
        assert node("devops-lab-control-plane").get("unschedulable") is not True
    assert node("devops-lab-worker2").get("unschedulable") is not True
    assert not any(t["key"] == "lab/maint" for t in node("devops-lab-worker").get("taints", []))


@KUBE_REQUIRED
def test_kube_lab_aggregation_and_open_bindings_refused_in_cluster():
    def view_rules():
        return json.dumps(json.loads(admin_kubectl("get", "clusterrole", "view", "-o", "json").stdout)["rules"])

    with testkit.KubeLab(allow=("ClusterRole", "ClusterRoleBinding")) as lab:
        before = view_rules()
        lab.kubectl("create", "role", "reader", "--verb=get", "--resource=pods")
        for label in ("view", "edit", "admin"):
            role = {"apiVersion": "rbac.authorization.k8s.io/v1", "kind": "ClusterRole",
                    "metadata": {"name": f"{lab.namespace}-agg-{label}",
                                 "labels": {"devops-ex": lab.id, f"rbac.authorization.k8s.io/aggregate-to-{label}": "true"}},
                    "rules": [{"apiGroups": [""], "resources": ["nodes"], "verbs": ["get"]}]}
            created = lab.run(["kubectl", "create", "-f", "-"], input=json.dumps(role))
            assert created.returncode != 0 and "denied" in created.stderr, created.stderr
        namespaced = lab.run(["kubectl", "label", "role", "reader", "rbac.authorization.k8s.io/aggregate-to-admin=true"])
        assert namespaced.returncode != 0 and "denied" in namespaced.stderr, namespaced.stderr
        rule = {"apiVersion": "rbac.authorization.k8s.io/v1", "kind": "ClusterRole",
                "metadata": {"name": f"{lab.namespace}-rule", "labels": {"devops-ex": lab.id}},
                "aggregationRule": {"clusterRoleSelectors": [{"matchLabels": {"rbac.authorization.k8s.io/aggregate-to-view": "true"}}]}}
        aggregated = lab.run(["kubectl", "create", "-f", "-"], input=json.dumps(rule))
        assert aggregated.returncode != 0 and ("denied" in aggregated.stderr or "aggregationRule" in aggregated.stderr), aggregated.stderr
        for subject in ("--group=system:authenticated", "--group=system:serviceaccounts", "--user=system:anonymous",
                        "--serviceaccount=kube-system:default"):
            bound = lab.run(["kubectl", "create", "rolebinding", "open", "--role=reader", subject])
            assert bound.returncode != 0 and "denied" in bound.stderr, subject + bound.stderr
        wide = lab.run(["kubectl", "create", "-f", "-"], input=json.dumps({
            "apiVersion": "rbac.authorization.k8s.io/v1", "kind": "ClusterRoleBinding",
            "metadata": {"name": f"{lab.namespace}-open", "labels": {"devops-ex": lab.id}},
            "roleRef": {"apiGroup": "rbac.authorization.k8s.io", "kind": "ClusterRole", "name": f"{lab.namespace}-read"},
            "subjects": [{"kind": "Group", "name": "system:authenticated", "apiGroup": "rbac.authorization.k8s.io"}]}))
        assert wide.returncode != 0 and "denied" in wide.stderr, wide.stderr
        jane = lab.run(["kubectl", "create", "rolebinding", "jane", "--role=reader", "--user=jane"])
        assert jane.returncode == 0, jane.stderr
        lab.kubectl("create", "rolebinding", "own", "--role=reader", f"--serviceaccount={lab.namespace}:default")
        assert view_rules() == before


@KUBE_REQUIRED
def test_kube_lab_learner_cannot_create_persistent_volume():
    with pytest.raises(ValueError, match="PersistentVolume"):
        testkit.KubeLab(allow=("PersistentVolume",))
    with testkit.KubeLab(allow=tuple(testkit.KUBE_ALLOWABLE)) as lab:
        assert lab.kubectl("auth", "can-i", "create", "persistentvolumes", check=False).stdout.strip() == "no"
        for source in ({"nfs": {"server": "172.17.0.1", "path": "/"}}, {"csi": {"driver": "x", "volumeHandle": "y"}}):
            volume = {"apiVersion": "v1", "kind": "PersistentVolume",
                      "metadata": {"name": f"{lab.namespace}-pv", "labels": {"devops-ex": lab.id}},
                      "spec": {"capacity": {"storage": "1Gi"}, "accessModes": ["ReadWriteMany"], **source,
                               "claimRef": {"namespace": "default", "name": "data"}}}
            created = lab.run(["kubectl", "create", "-f", "-"], input=json.dumps(volume))
            assert created.returncode != 0 and "forbidden" in created.stderr.lower(), created.stderr
    assert admin_kubectl("get", "pv", f"{lab.namespace}-pv").returncode != 0


@pytest.mark.parametrize("image,ref", [
    ("postgres:16.15-alpine", "docker.io/library/postgres:16.15-alpine"),
    ("devops-track/olist-shop:1.0", "docker.io/devops-track/olist-shop:1.0"),
    ("registry.k8s.io/pause:3.10", "registry.k8s.io/pause:3.10"),
    ("localhost:5000/api:1", "localhost:5000/api:1"),
    ("redis", "docker.io/library/redis:latest"),
    ("docker.io/library/nginx:1.30.6-alpine", "docker.io/library/nginx:1.30.6-alpine"),
])
def test_kind_image_ref(image, ref):
    assert testkit._kind_image_ref(image) == ref


def crictl_images(monkeypatch, per_node):
    calls = []

    def node_exec(node, *cmd, timeout=60, input=None):
        calls.append((node, cmd))
        assert cmd == ("crictl", "images", "-o", "json")
        tags = per_node.get(node, [])
        return subprocess.CompletedProcess(["docker", "exec", node, *cmd], 0,
                                           json.dumps({"images": [{"repoTags": [t]} for t in tags]}), "")

    monkeypatch.setattr(testkit, "kind_node_exec", node_exec)
    return calls


def test_require_kind_images_skips_with_load_command(monkeypatch):
    KubeFake(monkeypatch)
    calls = crictl_images(monkeypatch, {
        "devops-lab-worker": ["docker.io/devops-track/olist-shop:1.0", "docker.io/library/redis:7.4.12-alpine"],
        "devops-lab-worker2": ["docker.io/devops-track/olist-shop:1.0"],
    })
    with pytest.raises(pytest.skip.Exception) as info:
        testkit.Exercise.require_kind_images("devops-track/olist-shop:1.0", "redis:7.4.12-alpine")
    assert_skip(info, "redis:7.4.12-alpine", "devops-lab-worker2", "kind load docker-image redis:7.4.12-alpine --name devops-lab",
                "--nodes devops-lab-worker,devops-lab-worker2", "không bao giờ kéo image")
    assert "olist-shop:1.0 " not in str(info.value).split("kind load")[1].split("--name")[0] + " "
    assert {node for node, _ in calls} == {"devops-lab-worker", "devops-lab-worker2"}


def test_require_kind_images_olist_hint_has_build(monkeypatch):
    KubeFake(monkeypatch)
    crictl_images(monkeypatch, {})
    with pytest.raises(pytest.skip.Exception) as info:
        testkit.Exercise.require_kind_images(testkit.KUBE_IMAGES["olist"])
    assert_skip(info, testkit.KUBE_OLIST_BUILD)


def test_require_kind_images_present(monkeypatch):
    KubeFake(monkeypatch)
    tags = [testkit._kind_image_ref(i) for i in testkit.KUBE_IMAGES.values()]
    calls = crictl_images(monkeypatch, {"devops-lab-worker": tags, "devops-lab-worker2": tags})
    testkit.Exercise.require_kind_images(*testkit.KUBE_IMAGES.values())
    assert all(node != "devops-lab-control-plane" for node, _ in calls)


def test_require_kind_images_needs_cluster_first(monkeypatch):
    KubeFake(monkeypatch, clusters="\n")
    calls = crictl_images(monkeypatch, {})
    with pytest.raises(pytest.skip.Exception) as info:
        testkit.Exercise.require_kind_images("redis:7.4.12-alpine")
    assert_skip(info, "Chưa có cluster kind devops-lab")
    assert calls == []


def test_kube_images_documented_and_pinned():
    doc = (testkit.ROOT / "setup" / "DEVOPS-TOOLS.md").read_text(encoding="utf-8")
    assert testkit.KUBE_OLIST_BUILD in doc
    for image in testkit.KUBE_IMAGES.values():
        assert image in doc
        assert re.search(r":\d+\.\d+", image), image
    dockerfile = testkit.KUBE_OLIST_DOCKERFILE.read_text(encoding="utf-8")
    assert [line.split()[1] for line in dockerfile.splitlines() if line.startswith("FROM")] == ["python:3.12.16-slim-trixie"] * 2
    assert re.search(r"^USER 10001", dockerfile, re.M)


@KUBE_REQUIRED
def test_require_kind_images_real():
    testkit.Exercise.require_cluster()
    testkit.Exercise.require_kind_images("registry.k8s.io/pause:3.10", "kindest/kindnetd:v20250512-df8de77b")
    with pytest.raises(pytest.skip.Exception) as info:
        testkit.Exercise.require_kind_images("devops-track/khong-co-image:0.0")
    assert_skip(info, "devops-track/khong-co-image:0.0", "devops-lab-worker")


@KUBE_REQUIRED
def test_etcd_snapshot_argv_real(tmp_path):
    """argv cố định module 10 dùng: etcdctl nằm trong container etcd (image không có etcdutl), crictl chọn container theo tên,
    snapshot ghi vào /var/lib/etcd, mount ghi được duy nhất chung giữa container etcd và node."""
    import struct

    testkit.Exercise.require_cluster()
    with testkit.KubeLab() as lab:
        lab.kubectl("create", "configmap", "etcd-marker", "--from-literal=a=1")
        try:
            saved = testkit.kind_node_exec(
                "devops-lab-control-plane", "crictl", "exec", "-q", "--name", "^etcd$", "--state", "running", "etcdctl",
                "--endpoints=https://127.0.0.1:2379", "--cacert=/etc/kubernetes/pki/etcd/ca.crt",
                "--cert=/etc/kubernetes/pki/etcd/server.crt", "--key=/etc/kubernetes/pki/etcd/server.key",
                "snapshot", "save", "/var/lib/etcd/devops-ex-snapshot.db", timeout=120)
            assert saved.returncode == 0, saved.stderr
            assert "Snapshot saved at /var/lib/etcd/devops-ex-snapshot.db" in saved.stdout + saved.stderr
            testkit.kind_node_cp("devops-lab-control-plane", "/var/lib/etcd/devops-ex-snapshot.db", tmp_path / "snap.db")
        finally:
            testkit.kind_node_exec("devops-lab-control-plane", "rm", "-f", "/var/lib/etcd/devops-ex-snapshot.db",
                                   "/var/lib/etcd/devops-ex-snapshot.db.part")
        data = (tmp_path / "snap.db").read_bytes()
        assert struct.unpack_from("<I", data, 16)[0] == 0xED0CDAED
        assert f"/registry/configmaps/{lab.namespace}/etcd-marker".encode() in data
        status = testkit.kind_node_exec("devops-lab-control-plane", "crictl", "exec", "-q", "--name", "^etcd$", "--state",
                                        "running", "etcdutl", "version")
        assert status.returncode != 0


NS = "devops-ex-abc12345"


def ingress(host="devops-ex-abc12345.olist.test", cls="devops-traefik", **extra):
    spec = {"rules": [{"host": host, "http": {"paths": [{"path": "/", "pathType": "Prefix",
                                                         "backend": {"service": {"name": "api", "port": {"number": 8000}}}}]}}]}
    if cls is not None:
        spec["ingressClassName"] = cls
    spec.update(extra)
    return {"apiVersion": "networking.k8s.io/v1", "kind": "Ingress", "metadata": {"name": "web"}, "spec": spec}


def httproute(parents=None, hostnames=("devops-ex-abc12345.olist.test",)):
    spec = {"parentRefs": [{"name": "public", "namespace": "devops-gateway"}] if parents is None else parents,
            "rules": [{"backendRefs": [{"name": "api", "port": 8000}]}]}
    if hostnames is not None:
        spec["hostnames"] = list(hostnames)
    return {"apiVersion": "gateway.networking.k8s.io/v1", "kind": "HTTPRoute", "metadata": {"name": "web"}, "spec": spec}


def route_problems(doc):
    return testkit.kube_manifest_problems([doc], lab_id="abc12345", namespace=NS)


def test_routes_allowed_on_shared_class_and_gateway():
    assert route_problems(ingress()) == []
    assert route_problems(ingress(host="legacy.devops-ex-abc12345.olist.test")) == []
    assert route_problems(httproute()) == []
    assert route_problems(httproute(parents=[{"name": "public", "namespace": "devops-gateway", "kind": "Gateway",
                                              "group": "gateway.networking.k8s.io", "sectionName": "web"}])) == []


@pytest.mark.parametrize("doc,needle", [
    (ingress(cls=None), "ingressClassName"),
    (ingress(cls="nginx"), "ingressClassName"),
    (ingress(host=None), "host"),
    (ingress(host="shop.olist.test"), "host"),
    (ingress(host="devops-ex-other999.olist.test"), "host"),
    (ingress(host="xdevops-ex-abc12345.olist.test"), "host"),
    (ingress(defaultBackend={"service": {"name": "api", "port": {"number": 8000}}}), "defaultBackend"),
    (httproute(parents=[]), "parentRefs"),
    (httproute(parents=[{"name": "other", "namespace": "devops-gateway"}]), "parentRefs"),
    (httproute(parents=[{"name": "public"}]), "parentRefs"),
    (httproute(parents=[{"name": "public", "namespace": "devops-gateway", "kind": "Service"}]), "parentRefs"),
    (httproute(hostnames=None), "hostnames"),
    (httproute(hostnames=["*.olist.test"]), "hostnames"),
    ({"apiVersion": "gateway.networking.k8s.io/v1", "kind": "Gateway", "metadata": {"name": "mine"}, "spec": {}}, "Gateway"),
    ({"apiVersion": "gateway.networking.k8s.io/v1beta1", "kind": "ReferenceGrant", "metadata": {"name": "g"}, "spec": {}}, "ReferenceGrant"),
    ({"apiVersion": "gateway.networking.k8s.io/v1", "kind": "GatewayClass", "metadata": {"name": "c", "labels": {"devops-ex": "abc12345"}},
      "spec": {}}, "GatewayClass"),
])
def test_routes_refused_statically(doc, needle):
    problems = route_problems(doc)
    assert problems and any(needle in p for p in problems), problems


def test_kube_lab_bootstrap_has_routes_policy_and_httproute_rights(monkeypatch):
    fake = KubeFake(monkeypatch)
    with testkit.KubeLab() as lab:
        assert lab.hostname == f"{lab.namespace}.olist.test"
        [apply] = fake.calls_with("apply", "-f", "-")[:1]
        items = json.loads(apply["input"])["items"]
        policy = next(i for i in items if i["kind"] == "ValidatingAdmissionPolicy" and i["metadata"]["name"] == f"{lab.namespace}-routes")
        text = json.dumps(policy)
        for needle in ("ingresses", "httproutes", "devops-traefik", "devops-gateway", f"{lab.namespace}.olist.test", "defaultBackend"):
            assert needle in text, needle
        role = next(i for i in items if i["kind"] == "Role")
        assert {"apiGroups": ["gateway.networking.k8s.io"], "resources": ["httproutes"], "verbs": testkit._KUBE_RW} in role["rules"]
        assert not any("gateways" in r["resources"] or "referencegrants" in r["resources"] for r in role["rules"]
                       if r["apiGroups"] == ["gateway.networking.k8s.io"])
        assert fake.calls_with("--dry-run=server") and any(f"{lab.namespace}-probe-routes" in (c["input"] or "")
                                                             for c in fake.calls_with("--dry-run=server"))


def gateway_fake(monkeypatch, **answers):
    fake = KubeFake(monkeypatch)
    original = fake.run_sandboxed

    def run(cmd, **kwargs):
        joined = " ".join(map(str, cmd))
        for key, (code, out) in answers.items():
            if key in joined:
                return subprocess.CompletedProcess(cmd, code, out, "" if code == 0 else "NotFound")
        return original(cmd, **kwargs)

    monkeypatch.setattr(testkit, "run_sandboxed", run)
    return fake


GATEWAY_OK = {"crd": (0, "customresourcedefinition.apiextensions.k8s.io/httproutes.gateway.networking.k8s.io\n"),
              "ingressclass": (0, "ingressclass.networking.k8s.io/devops-traefik\n"),
              "deployment": (0, "1"), "gateway public": (0, "True")}


def test_require_gateway_ok(monkeypatch):
    gateway_fake(monkeypatch, **GATEWAY_OK)
    testkit.Exercise.require_gateway()


@pytest.mark.parametrize("broken,needle", [("crd", "CRD"), ("deployment", "traefik"), ("gateway public", "Gateway"),
                                           ("ingressclass", "IngressClass")])
def test_require_gateway_skips_with_setup(monkeypatch, broken, needle):
    answers = dict(GATEWAY_OK)
    answers[broken] = (1, "")
    gateway_fake(monkeypatch, **answers)
    with pytest.raises(pytest.skip.Exception) as info:
        testkit.Exercise.require_gateway()
    assert_skip(info, needle, "setup/kind/gateway/00-gateway-api-v1.6.3-standard-install.yaml",
                "setup/kind/gateway/10-traefik.yaml", "--server-side")


def test_gateway_setup_pinned_and_documented():
    folder = testkit.KUBE_GATEWAY_DIR
    sums = dict(reversed(line.split()) for line in (folder / "SHA256SUMS").read_text(encoding="utf-8").splitlines())
    import hashlib
    for name, digest in sums.items():
        assert hashlib.sha256((folder / name).read_bytes()).hexdigest() == digest, name
    assert set(sums) == {"00-gateway-api-v1.6.3-standard-install.yaml", "10-traefik.yaml"}
    crds = (folder / "00-gateway-api-v1.6.3-standard-install.yaml").read_text(encoding="utf-8")
    assert "gateway.networking.k8s.io/bundle-version: v1.6.3" in crds and "channel: standard" in crds
    traefik = (folder / "10-traefik.yaml").read_text(encoding="utf-8")
    assert f"image: {testkit.KUBE_GATEWAY_IMAGE}" in traefik and "from: Selector" in traefik and "key: devops-ex" in traefik
    doc = (testkit.ROOT / "setup" / "DEVOPS-TOOLS.md").read_text(encoding="utf-8")
    assert testkit.KUBE_GATEWAY_IMAGE_DIGEST in doc and "setup/kind/gateway/10-traefik.yaml" in doc


@KUBE_REQUIRED
def test_kube_lab_routes_policy_real():
    testkit.Exercise.require_cluster()
    testkit.Exercise.require_gateway()
    with testkit.KubeLab() as lab:
        good_route = json.dumps(httproute(hostnames=[lab.hostname]))
        assert lab.kubectl("apply", "-f", "-", input=good_route, check=False).returncode == 0
        good_ingress = json.dumps(ingress(host=f"legacy.{lab.hostname}"))
        assert lab.kubectl("apply", "-f", "-", input=good_ingress, check=False).returncode == 0
        for doc in (httproute(parents=[{"name": "public", "namespace": "kube-system"}], hostnames=[lab.hostname]),
                    httproute(hostnames=["shop.olist.test"]),
                    ingress(cls="nginx", host=lab.hostname),
                    ingress(host="victim.olist.test"),
                    {**ingress(host=lab.hostname), "metadata": {"name": "catch-all"},
                     "spec": {"ingressClassName": "devops-traefik",
                              "defaultBackend": {"service": {"name": "api", "port": {"number": 8000}}}}}):
            result = lab.kubectl("apply", "-f", "-", input=json.dumps(doc), check=False)
            assert result.returncode != 0 and f"{lab.namespace}-routes" in result.stderr, (doc, result.stderr)
        gateway = {"apiVersion": "gateway.networking.k8s.io/v1", "kind": "Gateway", "metadata": {"name": "mine"},
                   "spec": {"gatewayClassName": "devops-traefik", "listeners": [{"name": "w", "protocol": "HTTP", "port": 8000}]}}
        result = lab.kubectl("apply", "-f", "-", input=json.dumps(gateway), check=False)
        assert result.returncode != 0 and "forbidden" in result.stderr
        assert lab.kubectl("auth", "can-i", "create", "referencegrants.gateway.networking.k8s.io", check=False).stdout.strip() == "no"


@pytest.mark.parametrize("args", [
    ("create", "rolebinding", "jane", "--role=reader", "--user=jane"),
    ("create", "rolebinding", "jane", "--role=reader", "--user", "jane@olist.example"),
    ("create", "clusterrolebinding", "oncall", "--clusterrole=view", "--group=olist-oncall"),
    ("create", "rolebinding", "ci", "--role=reader", "--serviceaccount=devops-ex-x:ci"),
    ("create", "rolebinding", "many", "--role=reader", "--user=a", "--group=b", "--serviceaccount=ns:c", "--dry-run=client"),
])
def test_kube_lab_kubectl_allows_subject_flags_of_create_binding(monkeypatch, args):
    fake = KubeFake(monkeypatch)
    with testkit.KubeLab() as lab:
        lab.kubectl(*args)
        assert fake.calls_with(*args)


@pytest.mark.parametrize("args", [
    ("--user=x", "create", "rolebinding", "jane", "--role=reader"),
    ("--user", "x", "create", "rolebinding", "jane", "--role=reader", "--user=jane"),
    ("-n", "default", "create", "rolebinding", "jane", "--role=reader", "--user=jane"),
    ("create", "role", "reader", "--verb=get", "--resource=pods", "--user=admin"),
    ("get", "pods", "--user=admin"),
    ("get", "pods", "--group=system:masters"),
    ("set", "serviceaccount", "deployment/api", "ci", "--serviceaccount=x"),
    ("create", "rolebinding", "jane", "--role=reader", "--as=system:admin"),
    ("create", "rolebinding", "jane", "--role=reader", "--as-group=system:masters"),
    ("create", "rolebinding", "jane", "--role=reader", "--kubeconfig=/x"),
    ("auth", "can-i", "get", "pods", "--user=x"),
])
def test_kube_lab_kubectl_refuses_identity_flags_outside_create_binding(monkeypatch, args):
    fake = KubeFake(monkeypatch)
    with testkit.KubeLab() as lab:
        before = len(fake.sandbox_calls)
        with pytest.raises(ValueError, match="kubeconfig của lab"):
            lab.kubectl(*args)
        assert len(fake.sandbox_calls) == before


def test_kube_lab_can_i_runs_read_only_with_admin(monkeypatch):
    fake = KubeFake(monkeypatch)
    with testkit.KubeLab() as lab:
        assert lab.can_i("patch", "deployments", serviceaccount="ci-deployer") is True
        assert lab.can_i("get", "pods", subresource="log", user="jane@olist.example", groups=("olist-oncall",)) is True
        assert lab.can_i("list", "deployments.apps", serviceaccount="ci", all_namespaces=True) is True
    calls = [c for c in fake.sandbox_calls if c["cmd"][1:3] == ["auth", "can-i"] and any(a.startswith("--as=") for a in c["cmd"])]
    assert [c["cmd"][1:] for c in calls] == [
        ["auth", "can-i", "patch", "deployments", "-n", lab.namespace, f"--as=system:serviceaccount:{lab.namespace}:ci-deployer"],
        ["auth", "can-i", "get", "pods", "-n", lab.namespace, "--subresource=log", "--as=jane@olist.example",
         "--as-group=olist-oncall"],
        ["auth", "can-i", "list", "deployments.apps", "--all-namespaces", f"--as=system:serviceaccount:{lab.namespace}:ci"],
    ]
    assert all(c["env"]["KUBECONFIG"] == str(lab.admin_kubeconfig) for c in calls)


def test_kube_lab_can_i_answer_no(monkeypatch):
    fake = KubeFake(monkeypatch)
    original = fake.run_sandboxed

    def run(cmd, **kwargs):
        if any(str(a).startswith("--as=") for a in cmd):
            return subprocess.CompletedProcess(cmd, 1, "no\n", "")
        return original(cmd, **kwargs)

    monkeypatch.setattr(testkit, "run_sandboxed", run)
    with testkit.KubeLab() as lab:
        assert lab.can_i("get", "secrets", serviceaccount="ci-deployer") is False


@pytest.mark.parametrize("kwargs,needle", [
    ({"verb": "get", "resource": "pods"}, "serviceaccount hoặc user"),
    ({"verb": "get", "resource": "pods", "serviceaccount": "a", "user": "b"}, "serviceaccount hoặc user"),
    ({"verb": "get pods", "resource": "pods", "serviceaccount": "a"}, "verb"),
    ({"verb": "get", "resource": "--as=x", "serviceaccount": "a"}, "resource"),
    ({"verb": "get", "resource": "pods", "serviceaccount": "Bad Name"}, "serviceaccount"),
    ({"verb": "get", "resource": "pods", "serviceaccount": "kube-system:default"}, "serviceaccount"),
    ({"verb": "get", "resource": "pods", "user": "-x"}, "user"),
    ({"verb": "get", "resource": "pods", "user": "jane", "groups": ("a b",)}, "group"),
    ({"verb": "get", "resource": "pods", "user": "jane", "subresource": "--x"}, "subresource"),
])
def test_kube_lab_can_i_validates_arguments(monkeypatch, kwargs, needle):
    fake = KubeFake(monkeypatch)
    with testkit.KubeLab() as lab:
        before = len(fake.sandbox_calls)
        args = (kwargs.pop("verb"), kwargs.pop("resource"))
        with pytest.raises(ValueError, match=needle):
            lab.can_i(*args, **kwargs)
        assert len(fake.sandbox_calls) == before


def test_kube_lab_learner_role_writes_quota_and_limitrange(monkeypatch):
    fake = KubeFake(monkeypatch)
    with testkit.KubeLab() as lab:
        items = json.loads(fake.calls_with("apply", "-f", "-")[0]["input"])["items"]
    role = next(i for i in items if i["kind"] == "Role")
    rw = {r for rule in role["rules"] if rule["verbs"] == testkit._KUBE_RW and rule["apiGroups"] == [""] for r in rule["resources"]}
    assert {"resourcequotas", "limitranges"} <= rw


def test_kube_lab_crd_allow_grants_lab_api_group_only(monkeypatch):
    fake = KubeFake(monkeypatch)
    with testkit.KubeLab(allow=("CustomResourceDefinition",)) as lab:
        assert lab.api_group == f"{lab.namespace}.olist.test"
        items = json.loads(fake.calls_with("apply", "-f", "-")[0]["input"])["items"]
    role = next(i for i in items if i["kind"] == "Role")
    assert {"apiGroups": [lab.api_group], "resources": ["*"], "verbs": testkit._KUBE_RW} in role["rules"]
    policy = next(i for i in items if i["kind"] == "ValidatingAdmissionPolicy" and i["metadata"]["name"] == lab.namespace)
    assert any("customresourcedefinitions" in v["expression"] and f"'{lab.api_group}'" in v["expression"]
               for v in policy["spec"]["validations"])
    with testkit.KubeLab() as plain:
        items = json.loads(fake.calls_with("apply", "-f", "-")[-1]["input"])["items"]
    role = next(i for i in items if i["kind"] == "Role" and i["metadata"]["namespace"] == plain.namespace)
    assert not any(plain.api_group in rule["apiGroups"] for rule in role["rules"])


def crd(group: str, labels=None) -> dict:
    return {"apiVersion": "apiextensions.k8s.io/v1", "kind": "CustomResourceDefinition",
            "metadata": {"name": f"widgets.{group}", "labels": labels if labels is not None else {"devops-ex": "abc12345"}},
            "spec": {"group": group, "scope": "Namespaced",
                     "names": {"plural": "widgets", "singular": "widget", "kind": "Widget"},
                     "versions": [{"name": "v1", "served": True, "storage": True,
                                   "schema": {"openAPIV3Schema": {"type": "object", "x-kubernetes-preserve-unknown-fields": True}}}]}}


def test_crd_group_must_be_lab_group():
    group = "devops-ex-abc12345.olist.test"
    ok = testkit.kube_manifest_problems([crd(group)], lab_id="abc12345", namespace="devops-ex-abc12345",
                                        allow=("CustomResourceDefinition",), api_group=group)
    assert ok == []
    bad = testkit.kube_manifest_problems([crd("traefik.io")], lab_id="abc12345", namespace="devops-ex-abc12345",
                                         allow=("CustomResourceDefinition",), api_group=group)
    assert any("nhóm API" in p and group in p for p in bad), bad


def test_rbac_policy_accepts_rolebinding_service_account_without_namespace(monkeypatch):
    fake = KubeFake(monkeypatch)
    with testkit.KubeLab() as lab:
        items = json.loads(fake.calls_with("apply", "-f", "-")[0]["input"])["items"]
    policy = next(i for i in items if i["kind"] == "ValidatingAdmissionPolicy" and i["metadata"]["name"] == f"{lab.namespace}-rbac")
    binding = next(v["expression"] for v in policy["spec"]["validations"] if "subjects" in v["expression"])
    assert "request.resource.resource == 'rolebindings'" in binding and "!has(s.namespace)" in binding


def metrics_fake(monkeypatch, **answers):
    return gateway_fake(monkeypatch, **answers)


METRICS_OK = {"deployment metrics-server": (0, "1"), "apiservice": (0, "True"),
              "/apis/metrics.k8s.io/v1beta1/nodes": (0, json.dumps({"items": [{"metadata": {"name": "devops-lab-worker"}}]}))}


def test_require_metrics_ok(monkeypatch):
    metrics_fake(monkeypatch, **METRICS_OK)
    testkit.Exercise.require_metrics()


@pytest.mark.parametrize("broken,answer,needle", [
    ("deployment metrics-server", (1, ""), "metrics-server"),
    ("deployment metrics-server", (0, "0"), "metrics-server"),
    ("apiservice", (0, "False"), "APIService"),
    ("/apis/metrics.k8s.io/v1beta1/nodes", (0, json.dumps({"items": []})), "chưa có số liệu"),
    ("/apis/metrics.k8s.io/v1beta1/nodes", (1, ""), "chưa có số liệu"),
])
def test_require_metrics_skips_with_setup(monkeypatch, broken, answer, needle):
    answers = dict(METRICS_OK)
    answers[broken] = answer
    metrics_fake(monkeypatch, **answers)
    with pytest.raises(pytest.skip.Exception) as info:
        testkit.Exercise.require_metrics()
    assert_skip(info, needle, "kubectl --kubeconfig ~/.kube/devops-lab.yaml apply -k setup/kind/metrics-server", "image-archive")


def test_metrics_server_setup_pinned_and_documented():
    import hashlib

    folder = testkit.KUBE_METRICS_DIR
    sums = dict(reversed(line.split()) for line in (folder / "SHA256SUMS").read_text(encoding="utf-8").splitlines())
    assert set(sums) == {"00-metrics-server-v0.9.1-components.yaml", "kustomization.yaml"}
    for name, digest in sums.items():
        assert hashlib.sha256((folder / name).read_bytes()).hexdigest() == digest, name
    assert sums["00-metrics-server-v0.9.1-components.yaml"] == "3c7f57cdbee0f57fb0259a150e8f6d6cb4f29d72d1aa5dce8803151dd6d4c2a1"
    components = (folder / "00-metrics-server-v0.9.1-components.yaml").read_text(encoding="utf-8")
    assert f"image: {testkit.KUBE_METRICS_IMAGE}" in components
    kustomization = (folder / "kustomization.yaml").read_text(encoding="utf-8")
    assert "--kubelet-insecure-tls" in kustomization and "value: Never" in kustomization
    doc = (testkit.ROOT / "setup" / "DEVOPS-TOOLS.md").read_text(encoding="utf-8")
    assert testkit.KUBE_METRICS_IMAGE_DIGEST in doc and "setup/kind/metrics-server" in doc and "--kubelet-insecure-tls" in doc


def test_kube_lab_node_action_holds_node_lock(monkeypatch, tmp_path):
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path))
    monkeypatch.setattr(testkit, "KUBE_NODE_LOCK_TIMEOUT", 0.5)
    KubeFake(monkeypatch)
    with testkit.KubeLab() as first:
        first.node_action({"action": "cordon", "node": "devops-lab-worker"})
        assert (tmp_path / "devops-track" / "kube-nodes.lock").exists()
        with testkit.KubeLab() as second:
            with pytest.raises(pytest.fail.Exception, match="node_action"):
                second.node_action({"action": "cordon", "node": "devops-lab-worker2"})
    with testkit.KubeLab() as third:
        third.node_action({"action": "cordon", "node": "devops-lab-worker2"})


def test_kube_lab_without_node_action_takes_no_lock(monkeypatch, tmp_path):
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path))
    monkeypatch.setattr(testkit, "KUBE_NODE_LOCK_TIMEOUT", 0.5)
    KubeFake(monkeypatch)
    with testkit.KubeLab() as first:
        first.node_action({"action": "cordon", "node": "devops-lab-worker"})
        with testkit.KubeLab() as second:
            second.kubectl("get", "pods")


def test_kube_lab_close_waits_for_shared_components_after_node_action(monkeypatch, tmp_path):
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path))
    fake = KubeFake(monkeypatch)
    original = fake.run_sandboxed
    answers = iter([0, 1, 1])

    def run(cmd, **kwargs):
        if "deployments" in cmd and "json" in cmd:
            ready = next(answers, 1)
            item = {"metadata": {"name": "traefik"}, "spec": {"replicas": 1}, "status": {"availableReplicas": ready}}
            return subprocess.CompletedProcess(cmd, 0, json.dumps({"items": [item]}), "")
        return original(cmd, **kwargs)

    monkeypatch.setattr(testkit, "run_sandboxed", run)
    monkeypatch.setattr(testkit.time, "sleep", lambda s: None)
    with testkit.KubeLab() as lab:
        lab.node_action({"action": "drain", "node": "devops-lab-worker"})
    assert lab.cleanup_error is None
    assert next(answers, "done") == "done"


@KUBE_REQUIRED
def test_kube_lab_can_i_and_create_binding_real():
    with testkit.KubeLab() as lab:
        lab.kubectl("create", "serviceaccount", "ci")
        lab.kubectl("create", "role", "deployer", "--verb=get,list,patch", "--resource=deployments.apps")
        lab.kubectl("create", "rolebinding", "ci", "--role=deployer", f"--serviceaccount={lab.namespace}:ci")
        lab.kubectl("create", "rolebinding", "jane", "--role=deployer", "--user=jane@olist.example", "--group=olist-oncall")
        bare = {"apiVersion": "rbac.authorization.k8s.io/v1", "kind": "RoleBinding", "metadata": {"name": "bare"},
                "roleRef": {"apiGroup": "rbac.authorization.k8s.io", "kind": "Role", "name": "deployer"},
                "subjects": [{"kind": "ServiceAccount", "name": "bare"}]}
        lab.kubectl("apply", "-f", "-", input=json.dumps(bare))
        deadline = time.monotonic() + 30
        while not lab.can_i("patch", "deployments.apps", serviceaccount="ci") and time.monotonic() < deadline:
            time.sleep(1)
        assert lab.can_i("patch", "deployments.apps", serviceaccount="ci")
        assert lab.can_i("patch", "deployments.apps", serviceaccount="bare")
        assert not lab.can_i("delete", "deployments.apps", serviceaccount="ci")
        assert not lab.can_i("get", "secrets", serviceaccount="ci")
        assert not lab.can_i("list", "deployments.apps", serviceaccount="ci", all_namespaces=True)
        assert lab.can_i("list", "deployments.apps", user="someone", groups=("olist-oncall",))
        assert not lab.can_i("list", "deployments.apps", user="someone", groups=("other",))
        lab.kubectl("create", "resourcequota", "q", "--hard=pods=5")
        lab.kubectl("create", "-f", "-", input=json.dumps({"apiVersion": "v1", "kind": "LimitRange", "metadata": {"name": "l"},
                                                          "spec": {"limits": [{"type": "Container", "max": {"memory": "1Gi"}}]}}))


@KUBE_REQUIRED
def test_kube_lab_custom_resources_of_lab_group_real(tmp_path):
    with testkit.KubeLab(allow=("CustomResourceDefinition",)) as lab:
        (tmp_path / "crd.json").write_text(json.dumps(crd(lab.api_group, {"devops-ex": lab.id})), encoding="utf-8")
        lab.apply_learner(tmp_path / "crd.json")
        lab.kubectl("wait", "--for=condition=Established", f"crd/widgets.{lab.api_group}", "--timeout=60s")
        widget = {"apiVersion": f"{lab.api_group}/v1", "kind": "Widget", "metadata": {"name": "w"}, "spec": {"size": 1}}
        deadline = time.monotonic() + 30
        while lab.kubectl("apply", "-f", "-", input=json.dumps(widget), check=False).returncode != 0:
            assert time.monotonic() < deadline, "Không tạo được custom resource của nhóm API của lab"
            time.sleep(1)
        assert lab.kubectl("get", "widgets", "w", "-o", "jsonpath={.spec.size}").stdout == "1"
        foreign = crd("example.org", {"devops-ex": lab.id})
        foreign["metadata"]["name"] = f"widgets{lab.id}.example.org"
        foreign["spec"]["names"] = {"plural": f"widgets{lab.id}", "singular": f"widget{lab.id}", "kind": "Widget"}
        result = lab.kubectl("apply", "-f", "-", input=json.dumps(foreign), check=False)
        assert result.returncode != 0 and "denied" in result.stderr, result.stderr
    assert testkit.kube_leftovers(lab.id) == []


@KUBE_REQUIRED
def test_require_metrics_real():
    testkit.Exercise.require_cluster()
    testkit.Exercise.require_metrics()
    with testkit.KubeLab() as lab:
        assert "devops-lab-worker" in lab.kubectl("top", "nodes").stdout


@pytest.mark.parametrize("change,needle", [
    (lambda d: d["spec"].update(conversion={"strategy": "Webhook", "webhook": {"clientConfig": {"url": "https://127.0.0.1:2379/"},
                                                                         "conversionReviewVersions": ["v1"]}}), "conversion"),
    (lambda d: d["spec"].update(conversion={"strategy": "Webhook", "webhook": {
        "clientConfig": {"service": {"name": "x", "namespace": "kube-system"}}, "conversionReviewVersions": ["v1"]}}), "conversion"),
    (lambda d: d["spec"]["names"].update(categories=["all"]), "categories"),
    (lambda d: d["spec"]["names"].update(shortNames=["po"]), "shortNames"),
])
def test_crd_refuses_conversion_webhook_categories_short_names(change, needle):
    group = "devops-ex-abc12345.olist.test"
    doc = crd(group)
    change(doc)
    problems = testkit.kube_manifest_problems([doc], lab_id="abc12345", namespace="devops-ex-abc12345",
                                              allow=("CustomResourceDefinition",), api_group=group)
    assert any(needle in p for p in problems), problems


def test_crd_conversion_none_allowed():
    group = "devops-ex-abc12345.olist.test"
    doc = crd(group)
    doc["spec"]["conversion"] = {"strategy": "None"}
    assert testkit.kube_manifest_problems([doc], lab_id="abc12345", namespace="devops-ex-abc12345",
                                          allow=("CustomResourceDefinition",), api_group=group) == []


def test_crd_policy_refuses_conversion_and_names(monkeypatch):
    fake = KubeFake(monkeypatch)
    with testkit.KubeLab(allow=("CustomResourceDefinition",)) as lab:
        items = json.loads(fake.calls_with("apply", "-f", "-")[0]["input"])["items"]
    policy = next(i for i in items if i["kind"] == "ValidatingAdmissionPolicy" and i["metadata"]["name"] == lab.namespace)
    text = json.dumps(policy)
    for needle in ("object.spec.conversion.strategy == 'None'", "categories", "shortNames"):
        assert needle in text, needle


def test_kube_lab_node_action_drain_timeout_capped(monkeypatch, tmp_path):
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path))
    fake = KubeFake(monkeypatch)
    with testkit.KubeLab() as lab:
        lab.node_action({"action": "drain", "node": "devops-lab-worker"}, timeout=30)
        with pytest.raises(ValueError, match="timeout"):
            lab.node_action({"action": "drain", "node": "devops-lab-worker"}, timeout=900)
        with pytest.raises(ValueError, match="timeout"):
            lab.node_action({"action": "drain", "node": "devops-lab-worker"}, timeout=1)
    assert fake.calls_with("drain", "devops-lab-worker", "--timeout=30s")


def node_state(tmp_path) -> Path:
    return tmp_path / "devops-track" / "kube-nodes.state.json"


def test_kube_lab_node_state_recorded_and_cleared(monkeypatch, tmp_path):
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path))
    KubeFake(monkeypatch)
    with testkit.KubeLab() as lab:
        lab.node_action({"action": "taint", "node": "devops-lab-worker2", "taint": {"key": "olist.io/pool", "value": "f",
                                                                                     "effect": "NoSchedule"}})
        lab.node_action({"action": "cordon", "node": "devops-lab-worker"})
        state = json.loads(node_state(tmp_path).read_text())
        assert {"node": "devops-lab-worker", "cordon": True} in state["actions"]
        assert {"node": "devops-lab-worker2", "taint": ["olist.io/pool", "NoSchedule"]} in state["actions"]
    assert not node_state(tmp_path).exists()


def leftover(tmp_path, actions):
    path = node_state(tmp_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"actions": actions}))
    return path


LEFTOVER = [{"node": "devops-lab-worker", "cordon": True}, {"node": "devops-lab-worker2", "taint": ["olist.io/pool", "NoSchedule"]}]


class NodeCluster:
    """Trạng thái node giả cho KubeFake: get nodes trả cordon/taint hiện có, cordon/uncordon/taint đổi trạng thái."""

    def __init__(self, monkeypatch, *, cordoned=(), taints=(), fail_undo=False):
        self.fake = KubeFake(monkeypatch)
        self.cordoned = set(cordoned)
        self.taints = {(n, k, e) for n, k, e in taints}
        self.fail_undo = fail_undo
        self.original = self.fake.run_sandboxed
        monkeypatch.setattr(testkit, "run_sandboxed", self.run)

    def run(self, cmd, **kwargs):
        cmd = [str(c) for c in cmd]
        verb = cmd[1] if len(cmd) > 1 else ""
        done = lambda code=0, out="", err="": subprocess.CompletedProcess(cmd, code, out, err)
        if cmd[1:4] == ["get", "nodes", "-o"]:
            self.fake.sandbox_calls.append({"cmd": cmd, "env": dict(kwargs["env"]), "input": None})
            items = [{"metadata": {"name": n}, "spec": {"unschedulable": n in self.cordoned,
                                                         "taints": [{"key": k, "effect": e} for m, k, e in self.taints if m == n]}}
                     for n in ("devops-lab-worker", "devops-lab-worker2")]
            return done(out=json.dumps({"items": items}))
        if verb in ("cordon", "uncordon", "drain"):
            self.fake.sandbox_calls.append({"cmd": cmd, "env": dict(kwargs["env"]), "input": None})
            if verb == "uncordon" and self.fail_undo:
                return done(1, err="boom")
            (self.cordoned.discard if verb == "uncordon" else self.cordoned.add)(cmd[2])
            return done()
        if verb == "taint":
            self.fake.sandbox_calls.append({"cmd": cmd, "env": dict(kwargs["env"]), "input": None})
            node, spec = cmd[3], cmd[4]
            key, effect = spec.rstrip("-").split(":")
            key = key.split("=")[0]
            if spec.endswith("-"):
                if self.fail_undo:
                    return done(1, err="boom")
                self.taints.discard((node, key, effect))
            else:
                self.taints.add((node, key, effect))
            return done()
        return self.original(cmd, **kwargs)

    def cmds(self):
        return [c["cmd"] for c in self.fake.sandbox_calls]


def test_require_cluster_recovers_leftovers_then_exercise_proceeds(monkeypatch, tmp_path):
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path))
    path = leftover(tmp_path, LEFTOVER)
    cluster = NodeCluster(monkeypatch, cordoned={"devops-lab-worker"}, taints={("devops-lab-worker2", "olist.io/pool", "NoSchedule")})
    testkit.Exercise.require_cluster()
    assert not path.exists()
    assert cluster.cordoned == set() and cluster.taints == set()
    with testkit.KubeLab() as lab:
        lab.node_action({"action": "taint", "node": "devops-lab-worker2", "taint": {"key": "olist.io/pool", "value": "f",
                                                                                     "effect": "NoSchedule"}})
        assert ("devops-lab-worker2", "olist.io/pool", "NoSchedule") in cluster.taints
    assert cluster.taints == set() and not path.exists()


def test_require_cluster_skips_only_when_undo_fails(monkeypatch, tmp_path):
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path))
    path = leftover(tmp_path, LEFTOVER)
    NodeCluster(monkeypatch, cordoned={"devops-lab-worker"}, taints={("devops-lab-worker2", "olist.io/pool", "NoSchedule")},
                fail_undo=True)
    with pytest.raises(pytest.skip.Exception) as info:
        testkit.Exercise.require_cluster()
    assert_skip(info, "kubectl --kubeconfig ~/.kube/devops-lab.yaml uncordon devops-lab-worker",
                "kubectl --kubeconfig ~/.kube/devops-lab.yaml taint nodes devops-lab-worker2 olist.io/pool:NoSchedule-")
    assert path.exists()


def test_require_cluster_undoes_only_entries_still_present(monkeypatch, tmp_path):
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path))
    path = leftover(tmp_path, LEFTOVER)
    cluster = NodeCluster(monkeypatch, cordoned={"devops-lab-worker"})
    testkit.Exercise.require_cluster()
    assert ["kubectl", "uncordon", "devops-lab-worker"] in cluster.cmds()
    assert not any(c[1] == "taint" for c in cluster.cmds())
    assert not path.exists()


def test_require_cluster_ignores_state_while_lock_held(monkeypatch, tmp_path):
    import fcntl

    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path))
    path = leftover(tmp_path, LEFTOVER)
    cluster = NodeCluster(monkeypatch, cordoned={"devops-lab-worker"}, taints={("devops-lab-worker2", "olist.io/pool", "NoSchedule")})
    with open(path.parent / "kube-nodes.lock", "a+") as handle:
        fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        testkit.Exercise.require_cluster()
    assert path.exists() and cluster.cordoned == {"devops-lab-worker"}
    assert not any(c[1] in ("uncordon", "taint") for c in cluster.cmds())


def test_require_cluster_without_state_file_never_takes_lock_or_touches_state(monkeypatch, tmp_path):
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path))
    cluster = NodeCluster(monkeypatch)
    testkit.Exercise.require_cluster()
    assert not (tmp_path / "devops-track" / "kube-nodes.lock").exists()
    assert not any(c[1:3] == ["get", "nodes"] for c in cluster.cmds())


def test_state_rewritten_before_lock_is_reread_and_undone(monkeypatch, tmp_path):
    import fcntl

    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path))
    path = node_state(tmp_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("not json")
    cluster = NodeCluster(monkeypatch, cordoned={"devops-lab-worker"})
    original_flock = fcntl.flock

    def flock(handle, flags):
        result = original_flock(handle, flags)
        if flags & fcntl.LOCK_EX and not path.read_text().startswith("{"):
            path.write_text(json.dumps({"actions": [{"node": "devops-lab-worker", "cordon": True}]}))
        return result

    monkeypatch.setattr(fcntl, "flock", flock)
    testkit.Exercise.require_cluster()
    assert ["kubectl", "uncordon", "devops-lab-worker"] in cluster.cmds(), "Trạng thái phải được đọc lại sau khi giữ khoá"
    assert not path.exists()


def test_lock_nodes_undoes_only_entries_still_present(monkeypatch, tmp_path):
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path))
    cluster = NodeCluster(monkeypatch, taints={("devops-lab-worker2", "olist.io/pool", "NoSchedule")})
    with testkit.KubeLab() as lab:
        path = leftover(tmp_path, LEFTOVER)
        lab.node_action({"action": "cordon", "node": "devops-lab-worker2"})
        cmds = cluster.cmds()
        first = cmds.index(["kubectl", "cordon", "devops-lab-worker2"])
        assert ["kubectl", "taint", "nodes", "devops-lab-worker2", "olist.io/pool:NoSchedule-"] in cmds[:first]
        assert ["kubectl", "uncordon", "devops-lab-worker"] not in cmds, "Không gỡ thao tác đã không còn trên cluster"
    assert cluster.taints == set() and cluster.cordoned == set() and not path.exists()


@KUBE_REQUIRED
def test_kube_lab_crd_conversion_webhook_denied_real():
    with testkit.KubeLab(allow=("CustomResourceDefinition",)) as lab:
        for change in (lambda d: d["spec"].update(conversion={"strategy": "Webhook", "webhook": {
                           "clientConfig": {"url": "https://127.0.0.1:2379/"}, "conversionReviewVersions": ["v1"]}}),
                       lambda d: d["spec"]["names"].update(categories=["all"]),
                       lambda d: d["spec"]["names"].update(shortNames=["po"])):
            doc = crd(lab.api_group, {"devops-ex": lab.id})
            change(doc)
            result = lab.kubectl("apply", "-f", "-", input=json.dumps(doc), check=False)
            assert result.returncode != 0 and "denied" in result.stderr, result.stderr
    assert testkit.kube_leftovers(lab.id) == []


ANON_A = "a" * 64
ANON_B = "0123456789abcdef" * 4


class VolumeDocker(FakeDocker):
    def __init__(self, mounts: str, anonymous: str = ""):
        super().__init__()
        self.mounts = mounts
        self.anonymous = anonymous

    def __call__(self, cmd, **kwargs):
        self.calls.append(list(cmd))
        stdout = ""
        if cmd[1] == "inspect":
            stdout = self.mounts
        elif cmd[1:3] == ["volume", "ls"]:
            stdout = self.anonymous
        return subprocess.CompletedProcess(cmd, 0, stdout, "")


def test_docker_lab_close_removes_anonymous_volumes_unit(monkeypatch):
    named_hex = "f" * 64
    fake = VolumeDocker(f"{ANON_A} \n{ANON_B} {named_hex} devops-track-localstack-data act-toolcache\n",
                        anonymous=f"{ANON_A}\n{ANON_B}\n{'e' * 64}\n")
    monkeypatch.setattr(testkit.subprocess, "run", fake)
    with testkit.DockerLab() as lab:
        lab.start("db", "postgres:16.15-alpine")
    removed = [c for c in fake.calls if c[1] == "rm"]
    assert removed == [["docker", "rm", "-f", "-v", lab.name("db")]]
    volumes = [c for c in fake.calls if c[1:3] == ["volume", "rm"]]
    assert volumes == [["docker", "volume", "rm", ANON_A, ANON_B]], (
        "Chỉ xoá volume ẩn danh (64 ký tự hex, có nhãn com.docker.volume.anonymous) của container lab")
    listed = ["docker", "volume", "ls", "-q", "-f", "label=com.docker.volume.anonymous"]
    assert listed in fake.calls and fake.calls.index(listed) < fake.calls.index(volumes[0])
    inspect = next(c for c in fake.calls if c[1] == "inspect")
    assert inspect[-1] == lab.name("db") and fake.calls.index(inspect) < fake.calls.index(removed[0])


def test_docker_lab_close_without_volumes_skips_volume_rm(monkeypatch):
    fake = VolumeDocker("")
    monkeypatch.setattr(testkit.subprocess, "run", fake)
    with testkit.DockerLab() as lab:
        lab.start("web", "nginx:1.30.6-alpine")
    assert not [c for c in fake.calls if c[1:3] == ["volume", "rm"]]
    before = len(fake.calls)
    with testkit.DockerLab():
        pass
    assert not [c for c in fake.calls[before:] if c[1] in ("inspect", "rm")]


def test_docker_lab_close_removes_anonymous_volumes():
    image = require_real_docker("redis:7.4.12-alpine")
    lab = testkit.DockerLab()
    with lab:
        lab.start("cache", image, "300", entrypoint="sleep")
        mounts = testkit._docker("inspect", "--format", "{{json .Mounts}}", lab.name("cache")).stdout
        anonymous = [m["Name"] for m in json.loads(mounts) if m["Type"] == "volume"]
        assert anonymous, "Image redis có VOLUME /data nên container phải có volume ẩn danh"
    dangling = testkit._docker("volume", "ls", "-q", "-f", "dangling=true").stdout.split()
    existing = testkit._docker("volume", "ls", "-q").stdout.split()
    assert not set(anonymous) & (set(dangling) | set(existing))
    assert testkit.docker_leftovers(lab.id) == []


def test_sops_env_isolated_and_key_outside_repo(monkeypatch, tmp_path):
    host = {"SOPS_AGE_KEY": "AGE-SECRET-KEY-MAY-THAT", "SOPS_AGE_KEY_FILE": "/home/x/.config/sops/age/keys.txt",
            "SOPS_AGE_KEY_CMD": "cat /home/x/key", "SOPS_KMS_ARN": "arn:aws:kms:x", "AGE_PLUGIN": "x",
            "GNUPGHOME": "/home/x/.gnupg", "XDG_CONFIG_HOME": "/home/x/.config", "VAULT_TOKEN": "s.that"}
    for key, value in host.items():
        monkeypatch.setenv(key, value)
    home = tmp_path / "home"
    key = tmp_path / "keys" / "age.txt"
    env = testkit.sops_env(home, key)
    assert env["SOPS_AGE_KEY_FILE"] == str(key.resolve())
    assert env["HOME"] == str(home.resolve()) and env["XDG_CONFIG_HOME"] == f"{home.resolve()}/.config"
    assert not set(host.values()) & set(env.values())
    assert {k for k in env if k.startswith(("SOPS_", "AGE_"))} == {"SOPS_AGE_KEY_FILE"}
    assert not any(k.startswith("VAULT_") for k in env)
    assert env.get("GNUPGHOME", str(home.resolve())).startswith(str(home.resolve()))
    for inside in (testkit.ROOT / "tracks" / "devops" / "age.txt", testkit.ROOT / "age.txt"):
        with pytest.raises(ValueError, match="ngoài"):
            testkit.sops_env(home, inside)
    project = tmp_path / "repo"
    with pytest.raises(ValueError, match="ngoài"):
        testkit.sops_env(home, project / "keys" / "age.txt", outside=[project])
    assert testkit.sops_env(home, key, outside=[project])["SOPS_AGE_KEY_FILE"] == str(key.resolve())
    assert (home / ".gnupg").is_dir() and ((home / ".gnupg").stat().st_mode & 0o777) == 0o700
    assert env["GNUPGHOME"] == str((home / ".gnupg").resolve())


def _escape_into_root(tmp_path):
    up = "../" * len(tmp_path.resolve().parts)
    return Path(f"{tmp_path}/{up}{str(testkit.ROOT).lstrip('/')}/tracks/devops/keys")


def test_key_placement_rejects_symlink_and_dotdot_into_repo(tmp_path):
    link = tmp_path / "link"
    link.symlink_to(testkit.ROOT / "tracks")
    project = tmp_path / "repo"
    project.mkdir()
    project_link = tmp_path / "keys-link"
    project_link.symlink_to(project)
    dotdot = _escape_into_root(tmp_path)
    assert ".." in dotdot.parts and dotdot.resolve().is_relative_to(testkit.ROOT)
    home = tmp_path / "home"
    for key_dir in (link / "devops", dotdot):
        with pytest.raises(ValueError, match="ngoài"):
            testkit.sops_env(home, key_dir / "age.txt")
        with pytest.raises(ValueError, match="ngoài"):
            testkit.age_keypair(key_dir)
    with pytest.raises(ValueError, match="ngoài"):
        testkit.sops_env(home, project_link / "age.txt", outside=[project])
    with pytest.raises(ValueError, match="ngoài"):
        testkit.age_keypair(project_link / "keys", outside=[project])
    with pytest.raises(ValueError, match="ngoài"):
        testkit.sops_env(home, tmp_path / "x" / ".." / "repo" / "age.txt", outside=[project_link])
    assert not (testkit.ROOT / "tracks" / "devops" / "keys").exists()


def test_sandbox_hides_sops_vault_and_gpg_credentials():
    for rel in (".config/sops", ".gnupg", ".vault-token"):
        assert rel in testkit.CREDENTIAL_PATHS


def test_sops_and_age_versions():
    assert testkit.parse_version(testkit.SOPS_VERSION) >= testkit.parse_version(testkit.SOPS_MIN_VERSION)
    assert testkit.parse_version(testkit.AGE_VERSION) >= testkit.parse_version(testkit.AGE_MIN_VERSION)
    assert testkit.TOOL_VERSION_ARGS["sops"] == ["--version", "--disable-version-check"]


@SANDBOX_REQUIRED
def test_age_keypair_in_sandbox(monkeypatch, tmp_path):
    testkit.Exercise.require_tool("age-keygen", testkit.AGE_MIN_VERSION)
    calls = []
    real = testkit.run_sandboxed

    def spy(cmd, **kwargs):
        calls.append((list(map(str, cmd)), kwargs))
        return real(cmd, **kwargs)

    monkeypatch.setattr(testkit, "run_sandboxed", spy)
    keys = tmp_path / "keys"
    key, public = testkit.age_keypair(keys)
    assert key.parent == keys.resolve() and key.is_file()
    assert (key.stat().st_mode & 0o777) == 0o600, "Khoá riêng chỉ chủ sở hữu đọc, ghi được"
    assert re.fullmatch(r"age1[0-9a-z]{58}", public)
    assert f"# public key: {public}" in key.read_text(encoding="utf-8")
    assert calls and Path(calls[0][0][0]).name == "age-keygen" and calls[0][1]["writable"] == [keys.resolve()]
    with pytest.raises(ValueError, match="ngoài"):
        testkit.age_keypair(testkit.ROOT / "tracks" / "devops" / "keys")
    with pytest.raises(ValueError, match="ngoài"):
        testkit.age_keypair(tmp_path / "repo" / "keys", outside=[tmp_path / "repo"])


@SANDBOX_REQUIRED
def test_sops_roundtrip_with_lab_key_in_sandbox(monkeypatch, tmp_path):
    testkit.Exercise.require_tool("sops", testkit.SOPS_MIN_VERSION)
    testkit.Exercise.require_tool("age-keygen", testkit.AGE_MIN_VERSION)
    other, _ = testkit.age_keypair(tmp_path / "other")
    monkeypatch.setenv("SOPS_AGE_KEY_FILE", str(other))
    key, public = testkit.age_keypair(tmp_path / "keys")
    work = tmp_path / "work"
    work.mkdir()
    (work / "secret.yaml").write_text("password: khong-duoc-lo-ra\n", encoding="utf-8")
    env = testkit.sops_env(tmp_path / "home", key)
    encrypt = testkit.run_sandboxed(["sops", "encrypt", "--age", public, "--output", "enc.yaml", "secret.yaml"],
                                    writable=[work, tmp_path / "home"], cwd=work, env=env)
    assert encrypt.returncode == 0, encrypt.stderr
    assert "khong-duoc-lo-ra" not in (work / "enc.yaml").read_text(encoding="utf-8")
    hidden = testkit.run_sandboxed(["sops", "decrypt", "enc.yaml"], writable=[work, tmp_path / "home"], cwd=work, env=env)
    assert hidden.returncode != 0, "Thư mục khoá dưới /tmp không mount thì sandbox không thấy khoá"
    decrypt = testkit.run_sandboxed(["sops", "decrypt", "enc.yaml"], writable=[work, tmp_path / "home"], cwd=work, env=env,
                                    readonly=[key.parent])
    assert decrypt.returncode == 0, decrypt.stderr
    assert "khong-duoc-lo-ra" in decrypt.stdout
    wrong = testkit.run_sandboxed(["sops", "decrypt", "enc.yaml"], writable=[work, tmp_path / "home"], cwd=work,
                                  env=testkit.sops_env(tmp_path / "home", other), readonly=[other.parent])
    assert wrong.returncode != 0 and "khong-duoc-lo-ra" not in wrong.stdout + wrong.stderr


def test_vault_service_loopback_profile_devops(monkeypatch):
    import yaml

    data = yaml.safe_load((testkit.ROOT / "setup" / "docker-compose.yml").read_text(encoding="utf-8"))
    vault = data["services"]["vault-devops"]
    assert vault["profiles"] == ["devops"]
    assert vault["image"] == testkit.VAULT_IMAGE
    assert re.fullmatch(r"hashicorp/vault:\d+\.\d+\.\d+@sha256:[0-9a-f]{64}", vault["image"])
    assert vault["image"].split(":")[1].split("@")[0] == testkit.VAULT_VERSION
    assert vault["ports"] == ["127.0.0.1:${DEVOPS_VAULT_PORT:-18200}:8200"]
    assert vault["cpuset"] == "${DEVOPS_CPUSET:-}"
    assert vault["environment"]["VAULT_DEV_ROOT_TOKEN_ID"] == "${DEVOPS_VAULT_TOKEN:-devops-lab-root}"
    assert vault["environment"]["VAULT_DEV_LISTEN_ADDRESS"] == "0.0.0.0:8200"
    assert "healthcheck" in vault and "volumes" not in vault
    assert testkit.SERVICES["vault-devops"] == ("DEVOPS_VAULT_HOST", "localhost", "DEVOPS_VAULT_PORT", 18200)
    lines = (testkit.ROOT / "setup" / ".env.example").read_text(encoding="utf-8").splitlines()
    assert "# DEVOPS_VAULT_PORT=18200" in lines and "# DEVOPS_VAULT_TOKEN=devops-lab-root" in lines
    monkeypatch.delenv("DEVOPS_VAULT_PORT", raising=False)
    monkeypatch.delenv("DEVOPS_VAULT_HOST", raising=False)
    assert testkit.vault_devops_address() == "http://127.0.0.1:18200"


def test_vault_env_drops_host_vars(monkeypatch, tmp_path):
    for key, value in {"VAULT_ADDR": "https://vault.that.example:8200", "VAULT_TOKEN": "hvs.that",
                       "VAULT_NAMESPACE": "admin", "VAULT_CACERT": "/etc/that.pem"}.items():
        monkeypatch.setenv(key, value)
    monkeypatch.setenv("DEVOPS_VAULT_PORT", "28200")
    home = tmp_path / "vault-home"
    env = testkit.vault_env("lab-token", home)
    assert env == {"VAULT_ADDR": "http://127.0.0.1:28200", "VAULT_TOKEN": "lab-token", "HOME": str(home.resolve())}
    assert home.is_dir()
    with pytest.raises(ValueError):
        testkit.vault_env("", home)
    with pytest.raises(ValueError, match="ngoài repo"):
        testkit.vault_env("lab-token", testkit.ROOT / "tracks" / "devops")
    with pytest.raises(TypeError):
        testkit.vault_env("lab-token")


@SANDBOX_REQUIRED
def test_vault_env_home_keeps_token_file_out_of_project(tmp_path):
    project = tmp_path / "project"
    project.mkdir()
    env = testkit.vault_env("lab-token", tmp_path / "vault-home")
    result = testkit.run_sandboxed(["sh", "-c", 'printf x > "$HOME/.vault-token"'], writable=[project, tmp_path / "vault-home"],
                                   cwd=project, env=env)
    assert result.returncode == 0, result.stderr
    assert (tmp_path / "vault-home" / ".vault-token").is_file() and not (project / ".vault-token").exists()


def test_require_vault_devops_skips_when_down(monkeypatch):
    monkeypatch.setattr(testkit, "service_up", lambda name, timeout=0.5: False)
    with pytest.raises(pytest.skip.Exception, match="--profile devops up -d --wait vault-devops"):
        testkit.Exercise.require_vault_devops()


def test_require_vault_devops_rejects_other_server(monkeypatch):
    monkeypatch.setattr(testkit, "service_up", lambda name, timeout=0.5: True)
    monkeypatch.setattr(testkit, "_vault_health", lambda address: None)
    with pytest.raises(pytest.skip.Exception, match="không phải vault-devops"):
        testkit.Exercise.require_vault_devops()
    monkeypatch.setattr(testkit, "_vault_health", lambda address: {"initialized": True, "sealed": False})
    assert testkit.Exercise.require_vault_devops() == testkit.vault_devops_address()


RECIPIENT = "age1" + "q" * 58
ARGO_RESOURCES = "applications.argoproj.io\napplicationsets.argoproj.io\nappprojects.argoproj.io\n"


class ArgoFake(KubeFake):
    """KubeFake cộng ArgoCD: CRD argoproj.io, ConfigMap public key, pod git server, Application đọc bằng token của lab. Lệnh
    `git` trên máy (repo của lab trong thư mục tạm) chạy thật."""

    def __init__(self, monkeypatch, *, recipient=RECIPIENT, git_pods="git-5d46cfbbc8-58gjz", apps="", app_status=()):
        self.real_run = subprocess.run
        self.recipient = recipient
        self.git_pods = git_pods
        self.apps = apps
        self.app_status = list(app_status)
        super().__init__(monkeypatch)

    def run(self, cmd, **kwargs):
        if str(cmd[0]) == "git":
            return self.real_run(cmd, **kwargs)
        return super().run(cmd, **kwargs)

    def run_sandboxed(self, cmd, *, writable, cwd, env, timeout=30, input=None, readonly=()):
        joined = " ".join(map(str, cmd))
        answer = None
        if "api-resources --api-group=argoproj.io" in joined:
            answer = ARGO_RESOURCES
        elif f"configmap {testkit.KUBE_ARGOCD_AGE_PUBLIC}" in joined:
            answer = self.recipient
        elif "app.kubernetes.io/name=git" in joined:
            answer = self.git_pods
        elif "get applications.argoproj.io -o name" in joined:
            answer = self.apps
        elif "get applications.argoproj.io" in joined and "-o json" in joined:
            status = self.app_status.pop(0) if len(self.app_status) > 1 else (self.app_status or [{}])[0]
            answer = json.dumps({"metadata": {"name": "web"}, "status": status})
        if answer is None:
            return super().run_sandboxed(cmd, writable=writable, cwd=cwd, env=env, timeout=timeout, input=input, readonly=readonly)
        cmd = [str(part) for part in cmd]
        self.sandbox_calls.append({"cmd": cmd, "env": dict(env), "writable": list(writable), "readonly": list(readonly),
                                   "cwd": cwd, "input": input})
        return subprocess.CompletedProcess(cmd, 0, answer, "")


def bootstrap_items(fake) -> list:
    [apply] = [c for c in fake.calls_with("apply") if c["input"] and '"Namespace"' in c["input"]]
    return json.loads(apply["input"])["items"]


def test_argocd_project_restricts_destination_and_source(monkeypatch):
    fake = ArgoFake(monkeypatch)
    with testkit.KubeLab() as lab:
        assert lab.argocd_project() == lab.namespace
        [call] = [c for c in fake.calls_with("apply") if c["input"] and '"AppProject"' in c["input"]]
        assert call["env"]["KUBECONFIG"] == str(lab.admin_kubeconfig)
        project = json.loads(call["input"])
        assert project["metadata"] == {"name": lab.namespace, "namespace": "argocd", "labels": {"devops-ex": lab.id}}
        spec = project["spec"]
        assert lab.repo_url == f"git://git.devops-git.svc.cluster.local/{lab.namespace}.git"
        assert spec["sourceRepos"] == [lab.repo_url]
        assert spec["destinations"] == [{"server": "https://kubernetes.default.svc", "namespace": lab.namespace}]
        assert spec["sourceNamespaces"] == [lab.namespace]
        assert spec["clusterResourceWhitelist"] == []
        assert spec["destinationServiceAccounts"] == [{"server": "https://kubernetes.default.svc", "namespace": lab.namespace,
                                                       "defaultServiceAccount": "devops-ex-learner"}]
        assert "*" not in json.dumps(spec)
        assert not {"namespaceResourceWhitelist", "clusterResourceBlacklist", "permitOnlyProjectScopedClusters"} & set(spec)
    role = next(i for i in bootstrap_items(fake) if i["kind"] == "Role")
    argo = [r for r in role["rules"] if "argoproj.io" in r["apiGroups"]]
    assert argo == [{"apiGroups": ["argoproj.io"], "resources": ["applications"], "verbs": testkit._KUBE_RW}]
    deletes = [c["cmd"] for c in fake.calls_with("delete") if "appprojects.argoproj.io" in c["cmd"]]
    assert deletes and all(["-n", "argocd"] == c[1:3] and "-l" in c and f"devops-ex={lab.id}" in c for c in deletes)
    assert not any("appprojects.argoproj.io" in c["cmd"] and "--all" in c["cmd"] for c in fake.sandbox_calls)


def test_argocd_project_skips_without_argocd(monkeypatch):
    KubeFake(monkeypatch)
    with testkit.KubeLab() as lab:
        with pytest.raises(pytest.skip.Exception) as info:
            lab.argocd_project()
    assert_skip(info, "chưa có ArgoCD", "setup/kind/argocd", "devops-sops-age")


def gitops_tree(root: Path, value: str) -> Path:
    (root / "app").mkdir(parents=True, exist_ok=True)
    (root / "app" / "kustomization.yaml").write_text("resources: [cm.yaml]\n", encoding="utf-8")
    (root / "app" / "cm.yaml").write_text(f"apiVersion: v1\nkind: ConfigMap\nmetadata: {{name: web}}\ndata: {{v: '{value}'}}\n",
                                          encoding="utf-8")
    (root / ".git").mkdir(exist_ok=True)
    (root / ".git" / "config").write_text("[core]\n\thooksPath = /tmp/khong-duoc-dung\n", encoding="utf-8")
    return root


def lab_git(lab, *args) -> str:
    return lab._git_repo.out(*args)


def test_gitops_repo_isolated_per_lab(monkeypatch, tmp_path):
    fake = ArgoFake(monkeypatch)
    source = gitops_tree(tmp_path / "gitops", "1")
    with testkit.KubeLab() as a, testkit.KubeLab() as b:
        url_a, url_b = a.gitops_repo(source), b.gitops_repo(source)
        assert url_a == a.repo_url and url_b == b.repo_url and url_a != url_b
        for lab, other in ((a, b), (b, a)):
            writes = [c for c in fake.sandbox_calls if c["env"]["KUBECONFIG"] == str(lab.admin_kubeconfig)
                      and ("cp" in c["cmd"] or "exec" in c["cmd"])]
            text = "\n".join(" ".join(c["cmd"]) for c in writes)
            assert f"/srv/git/{lab.namespace}.git" in text and other.namespace not in text
            for call in writes:
                assert not {"sh", "bash", "dash"} & set(call["cmd"]), call["cmd"]
                assert lab.kubeconfig.parent not in map(Path, call["readonly"] + call["writable"])
            assert lab_git(lab, "ls-files").split() == ["app/cm.yaml", "app/kustomization.yaml"]
            assert re.fullmatch(r"[0-9a-f]{40}", lab.gitops_revision)
            assert not list(lab._admin.home.glob("*.bundle"))
        first = a.gitops_revision
        gitops_tree(source, "2")
        a.gitops_repo(source)
        assert a.gitops_revision != first and len(lab_git(a, "log", "--format=%H").split()) == 2
        assert "v: '2'" in (a.root / "gitops" / "repo" / "app" / "cm.yaml").read_text(encoding="utf-8")
        assert len(lab_git(b, "log", "--format=%H").split()) == 1
    removed = [" ".join(c["cmd"]) for c in fake.sandbox_calls if "rm" in c["cmd"] and "-rf" in c["cmd"]]
    assert any(f"/srv/git/{a.namespace}.git" in r for r in removed) and any(f"/srv/git/{b.namespace}.git" in r for r in removed)
    assert all(r.count("/srv/git/") == 1 for r in removed)


def test_gitops_repo_never_runs_learner_git_config(monkeypatch, tmp_path):
    ArgoFake(monkeypatch)
    source = gitops_tree(tmp_path / "gitops", "1")
    with testkit.KubeLab() as lab:
        lab.gitops_repo(source)
        config = (lab.root / "gitops" / "repo" / ".git" / "config").read_text(encoding="utf-8")
        assert "khong-duoc-dung" not in config


def test_gitops_repo_refuses_symlink_and_private_key(monkeypatch, tmp_path):
    ArgoFake(monkeypatch)
    source = gitops_tree(tmp_path / "gitops", "1")
    with testkit.KubeLab() as lab:
        (source / "app" / "link.yaml").symlink_to(source / "app" / "cm.yaml")
        with pytest.raises(pytest.fail.Exception, match="symlink"):
            lab.gitops_repo(source)
        (source / "app" / "link.yaml").unlink()
        secret_key = "AGE-SECRET-KEY-1" + "Q" * 58
        (source / "app" / "keys.txt").write_text(f"# public key: {RECIPIENT}\n{secret_key}\n", encoding="utf-8")
        with pytest.raises(pytest.fail.Exception) as info:
            lab.gitops_repo(source)
        assert "keys.txt" in str(info.value) and secret_key not in str(info.value)
        assert lab._git_repo is None


def argo_app(namespace: str, **change) -> dict:
    app = {"apiVersion": "argoproj.io/v1alpha1", "kind": "Application", "metadata": {"name": "web"},
           "spec": {"project": namespace,
                    "source": {"repoURL": testkit.kube_git_url(namespace), "path": "app", "targetRevision": "main"},
                    "destination": {"server": "https://kubernetes.default.svc", "namespace": namespace},
                    "syncPolicy": {"automated": {"prune": True, "selfHeal": True}}}}
    for key, value in change.items():
        if value is None:
            app["spec"].pop(key)
        else:
            app["spec"][key] = value
    return app


FOREIGN_APPS = {
    "project-default": ({"project": "default"}, "spec.project"),
    "project-other-lab": ({"project": "devops-ex-0000beef"}, "spec.project"),
    "dest-namespace": ({"destination": {"server": "https://kubernetes.default.svc", "namespace": "kube-system"}}, "destination"),
    "dest-cluster": ({"destination": {"server": "https://10.0.0.1:6443", "namespace": "NS"}}, "destination"),
    "dest-name": ({"destination": {"name": "prod", "namespace": "NS"}}, "destination"),
    "dest-missing-ns": ({"destination": {"server": "https://kubernetes.default.svc"}}, "destination"),
    "repo-other-lab": ({"source": {"repoURL": "git://git.devops-git.svc.cluster.local/devops-ex-0000beef.git", "path": "."}},
                       "repoURL"),
    "repo-github": ({"source": {"repoURL": "https://github.com/argoproj/argocd-example-apps.git", "path": "guestbook"}},
                    "repoURL"),
    "sources-one-bad": ({"source": None, "sources": [{"repoURL": "REPO", "path": "."},
                                                     {"repoURL": "https://github.com/x/y.git", "path": "."}]}, "repoURL"),
    "hydrator": ({"sourceHydrator": {"drySource": {"repoURL": "REPO"}}}, "sourceHydrator"),
}


@pytest.mark.parametrize("case", sorted(FOREIGN_APPS))
def test_application_with_foreign_project_refused(case):
    namespace = "devops-ex-abc12345"
    change, needle = FOREIGN_APPS[case]
    text = json.dumps(change).replace('"NS"', json.dumps(namespace)).replace('"REPO"', json.dumps(testkit.kube_git_url(namespace)))
    app = argo_app(namespace, **json.loads(text))
    assert testkit.kube_manifest_problems([argo_app(namespace)], lab_id="abc12345", namespace=namespace) == []
    problems = testkit.kube_manifest_problems([app], lab_id="abc12345", namespace=namespace)
    assert any(needle in p for p in problems), problems


@pytest.mark.parametrize("kind", ["AppProject", "ApplicationSet"])
def test_argocd_admin_kinds_refused_statically(kind):
    doc = {"apiVersion": "argoproj.io/v1alpha1", "kind": kind, "metadata": {"name": "x"}, "spec": {}}
    problems = testkit.kube_manifest_problems([doc], lab_id="abc12345", namespace="devops-ex-abc12345")
    assert problems and "bị từ chối" in problems[0]


def test_application_policy_in_cluster(monkeypatch):
    fake = ArgoFake(monkeypatch)
    with testkit.KubeLab() as lab:
        pass
    policy = next(i for i in bootstrap_items(fake) if i["kind"] == "ValidatingAdmissionPolicy"
                  and i["metadata"]["name"] == f"{lab.namespace}-argocd")
    spec = policy["spec"]
    assert spec["failurePolicy"] == "Fail"
    assert spec["matchConstraints"]["resourceRules"] == [{"apiGroups": ["argoproj.io"], "apiVersions": ["*"],
                                                          "resources": ["applications"], "operations": ["CREATE", "UPDATE"]}]
    assert f"'system:serviceaccounts:{lab.namespace}' in request.userInfo.groups" in spec["matchConditions"][0]["expression"]
    text = json.dumps(spec["validations"])
    for needle in (f"object.spec.project == '{lab.namespace}'", f"object.spec.destination.namespace == '{lab.namespace}'",
                   "https://kubernetes.default.svc", lab.repo_url, "sourceHydrator", "object.spec.sources.all"):
        assert needle in text, needle
    probes = [json.loads(c["input"]) for c in fake.calls_with("--dry-run=server")]
    [probe] = [p for p in probes if p["kind"] == "Application"]
    assert probe["metadata"]["name"] == f"{lab.namespace}-probe-argocd" and probe["spec"]["project"] == "default"


def test_application_policy_probe_only_with_argocd(monkeypatch):
    fake = KubeFake(monkeypatch)
    with testkit.KubeLab() as lab:
        pass
    assert any(i["metadata"]["name"] == f"{lab.namespace}-argocd" for i in bootstrap_items(fake))
    assert not any(json.loads(c["input"])["kind"] == "Application" for c in fake.calls_with("--dry-run=server"))
    assert not [c for c in fake.sandbox_calls if "applications.argoproj.io" in c["cmd"] and "delete" in c["cmd"]]


ARGOCD_OK = {
    "crd applications.argoproj.io": (0, "customresourcedefinition.apiextensions.k8s.io/applications.argoproj.io\n"),
    "argocd-cmd-params-cm": (0, "devops-ex-*"),
    "configmap argocd-cm -o": (0, "true"),
    "appprojects.argoproj.io default": (0, "[][]"),
    "statefulset argocd-application-controller": (0, "1"),
    "deployment argocd-repo-server": (0, "1"),
    "configmap devops-sops-age-public": (0, RECIPIENT),
    "deployment git": (0, "1"),
}


def argocd_fake(monkeypatch, answers):
    fake = KubeFake(monkeypatch)
    calls = []

    def run(cmd, **kwargs):
        joined = " ".join(map(str, cmd))
        calls.append(joined)
        for key, (code, out) in answers.items():
            if key in joined:
                return subprocess.CompletedProcess(cmd, code, out, "" if code == 0 else "NotFound")
        return fake.run_sandboxed(cmd, **kwargs)

    monkeypatch.setattr(testkit, "run_sandboxed", run)
    return calls


def test_require_argocd_ok_never_reads_private_key(monkeypatch):
    calls = argocd_fake(monkeypatch, ARGOCD_OK)
    testkit.Exercise.require_argocd()
    assert len([c for c in calls if c.startswith("kubectl")]) == len(ARGOCD_OK)
    assert not any(" secret" in c or "secrets" in c for c in calls), calls


@pytest.mark.parametrize("broken,answer,needle", [
    ("crd applications.argoproj.io", (1, ""), "CRD applications.argoproj.io"),
    ("argocd-cmd-params-cm", (0, ""), "application.namespaces"),
    ("argocd-cmd-params-cm", (0, "devops-ex-abc"), "application.namespaces"),
    ("configmap argocd-cm -o", (0, "false"), "impersonation"),
    ("appprojects.argoproj.io default", (0, "[\"*\"][{\"namespace\":\"*\",\"server\":\"*\"}]"), "AppProject default"),
    ("statefulset argocd-application-controller", (0, "0"), "application-controller"),
    ("deployment argocd-repo-server", (0, ""), "Secret argocd/devops-sops-age"),
    ("configmap devops-sops-age-public", (1, ""), "devops-sops-age-public"),
    ("configmap devops-sops-age-public", (0, "AGE-SECRET-KEY-1XYZ"), "devops-sops-age-public"),
    ("deployment git", (0, "0"), "git server"),
])
def test_require_argocd_messages(monkeypatch, broken, answer, needle):
    answers = dict(ARGOCD_OK)
    answers[broken] = answer
    argocd_fake(monkeypatch, answers)
    with pytest.raises(pytest.skip.Exception) as info:
        testkit.Exercise.require_argocd()
    assert_skip(info, needle, "kubectl --kubeconfig ~/.kube/devops-lab.yaml apply --server-side -k setup/kind/argocd",
                "20-default-project.yaml", "create secret generic devops-sops-age", "age-keygen -y", "image-archive")


def test_require_argocd_needs_cluster_first(monkeypatch):
    KubeFake(monkeypatch, clusters="\n")
    with pytest.raises(pytest.skip.Exception) as info:
        testkit.Exercise.require_argocd()
    assert_skip(info, "Chưa có cluster kind devops-lab")


def test_age_private_key_never_in_sandbox(monkeypatch, tmp_path):
    fake = ArgoFake(monkeypatch)
    with testkit.KubeLab() as lab:
        assert lab.sops_age_recipient == lab.age_public_key == RECIPIENT
        lab.kubectl("get", "pods")
        lab.run(["kubectl", "get", "applications"])
        learner = [c for c in fake.sandbox_calls if c["env"]["KUBECONFIG"] == str(lab.kubeconfig)]
    reads = [c["cmd"] for c in fake.sandbox_calls if "devops-sops-age-public" in c["cmd"]]
    assert reads == [[*reads[0][:1], "-n", "argocd", "get", "configmap", "devops-sops-age-public", "-o", "jsonpath={.data.recipient}"]]
    for call in fake.sandbox_calls:
        assert not {"secret", "secrets", "devops-sops-age"} & set(call["cmd"]), call["cmd"]
    assert learner
    for call in learner:
        assert all(Path(p).is_relative_to(lab.root) for p in call["readonly"] + call["writable"])
        assert not any("SOPS" in key or "AGE" in key for key in call["env"])


def test_age_private_key_only_in_cmp_sidecar():
    import yaml

    folder = testkit.KUBE_ARGOCD_DIR
    texts = {p.name: p.read_text(encoding="utf-8") for p in folder.iterdir() if p.is_file()}
    assert not any("AGE-SECRET-KEY" in text for text in texts.values())
    kustomization = yaml.safe_load(texts["kustomization.yaml"])
    [patch] = [p for p in kustomization["patches"] if p["target"]["name"] == "argocd-repo-server"]
    spec = yaml.safe_load(patch["patch"])["spec"]["template"]["spec"]
    [volume] = [v for v in spec["volumes"] if "secret" in v]
    assert volume["secret"]["secretName"] == testkit.KUBE_ARGOCD_AGE_SECRET
    mounting = [c["name"] for c in spec["containers"] + spec["initContainers"]
                if any(m["name"] == volume["name"] for m in c.get("volumeMounts", []))]
    assert mounting == [testkit.KUBE_ARGOCD_CMP]
    sidecar = next(c for c in spec["containers"] if c["name"] == testkit.KUBE_ARGOCD_CMP)
    assert all(m.get("readOnly") for m in sidecar["volumeMounts"] if m["name"] in (volume["name"], "custom-tools"))
    for name, text in texts.items():
        if name.endswith(".yaml"):
            for doc in yaml.safe_load_all(text):
                assert not (isinstance(doc, dict) and doc.get("kind") == "Secret"
                            and doc["metadata"]["name"] == testkit.KUBE_ARGOCD_AGE_SECRET), name


def test_argocd_wait_waits_for_latest_revision(monkeypatch, tmp_path):
    synced = {"health": {"status": "Healthy"}, "sync": {"status": "Synced", "revision": "a" * 40},
              "operationState": {"phase": "Succeeded"}}
    fake = ArgoFake(monkeypatch, app_status=[synced, synced])
    monkeypatch.setattr(testkit.time, "sleep", lambda s: None)
    with testkit.KubeLab() as lab:
        assert lab.argocd_wait("web") == synced
        lab.gitops_revision = "b" * 40
        later = {**synced, "sync": {"status": "Synced", "revision": "b" * 40}}
        running = {**later, "operationState": {"phase": "Running"}}
        fake.app_status = [synced, running, later]
        assert lab.argocd_wait("web")["sync"]["revision"] == "b" * 40
        reads = [c for c in fake.sandbox_calls if "applications.argoproj.io" in c["cmd"] and "json" in c["cmd"]]
        assert reads and all(c["env"]["KUBECONFIG"] == str(lab.kubeconfig) for c in reads)
        with pytest.raises(ValueError):
            lab.argocd_wait("Web; rm")


def test_argocd_wait_failure_message(monkeypatch):
    stuck = {"health": {"status": "Degraded"}, "sync": {"status": "OutOfSync", "revision": "c" * 40},
             "operationState": {"phase": "Failed", "message": "one or more objects failed to apply"},
             "conditions": [{"type": "SyncError", "message": "namespace default is not permitted"}],
             "resources": [{"kind": "Secret", "name": "db"}]}
    ArgoFake(monkeypatch, app_status=[stuck])
    monkeypatch.setattr(testkit.time, "sleep", lambda s: None)
    with testkit.KubeLab() as lab:
        clock = iter(range(0, 10_000, 100))
        monkeypatch.setattr(testkit.time, "monotonic", lambda: next(clock))
        with pytest.raises(pytest.fail.Exception) as info:
            lab.argocd_wait("web", timeout=5)
    text = str(info.value)
    for needle in ("health=Degraded", "sync=OutOfSync", "Failed", "namespace default is not permitted"):
        assert needle in text, text
    assert '"Secret"' not in text


def test_argocd_setup_pinned_and_documented():
    import hashlib

    folder = testkit.KUBE_ARGOCD_DIR
    sums = dict(reversed(line.split()) for line in (folder / "SHA256SUMS").read_text(encoding="utf-8").splitlines())
    assert set(sums) == {p.name for p in folder.iterdir() if p.is_file() and p.name != "SHA256SUMS"}
    for name, digest in sums.items():
        assert hashlib.sha256((folder / name).read_bytes()).hexdigest() == digest, name
    assert sums["00-argocd-v3.5.6-core-install.yaml"] == "d3d9d3555ad77eb4b6d27b1ec0d2af7978a91537e84d54631f983c227f0a3d31"
    text = "\n".join((folder / name).read_text(encoding="utf-8") for name in sums)
    images = set(re.findall(r"image: (\S+)", text))
    assert images == {testkit.KUBE_ARGOCD_IMAGE, testkit.KUBE_ARGOCD_REDIS_IMAGE, testkit.KUBE_ARGOCD_SOPS_IMAGE}
    kustomization = (folder / "kustomization.yaml").read_text(encoding="utf-8")
    for needle in ("application.namespaces: devops-ex-*", 'application.sync.impersonation.enabled: "true"', "unsetOnly"):
        assert needle in kustomization + (folder / "namespace.yaml").read_text(encoding="utf-8"), needle
    doc = (testkit.ROOT / "setup" / "DEVOPS-TOOLS.md").read_text(encoding="utf-8")
    for needle in (testkit.KUBE_ARGOCD_IMAGE_DIGEST, testkit.KUBE_ARGOCD_REDIS_IMAGE_DIGEST, testkit.KUBE_ARGOCD_SOPS_IMAGE_DIGEST,
                   "setup/kind/argocd", "devops-sops-age-public", sums["00-argocd-v3.5.6-core-install.yaml"][:16]):
        assert needle in doc, needle


@pytest.mark.skipif(not shutil.which("kubectl"), reason="Cần kubectl để render kustomization")
def test_argocd_rendered_manifests_fail_closed(tmp_path):
    import yaml

    env = {"PATH": os.environ["PATH"], "HOME": str(tmp_path), "KUBECONFIG": str(tmp_path / "none"), "KUBERC": "off"}
    result = subprocess.run(["kubectl", "kustomize", str(testkit.KUBE_ARGOCD_DIR)], capture_output=True, text=True, env=env,
                            timeout=120)
    assert result.returncode == 0, result.stderr
    docs = [d for d in yaml.safe_load_all(result.stdout) if d]
    namespaces = {d["metadata"].get("namespace") for d in docs} - {None}
    assert namespaces == {"argocd", "devops-git"}
    for doc in docs:
        if doc["kind"] in ("Deployment", "StatefulSet"):
            spec = doc["spec"]["template"]["spec"]
            for container in spec.get("initContainers", []) + spec["containers"]:
                assert container.get("imagePullPolicy") == "Never", (doc["metadata"]["name"], container["name"])
    git = next(d for d in docs if d["kind"] == "Deployment" and d["metadata"]["name"] == "git")
    command = git["spec"]["template"]["spec"]["containers"][0]["command"]
    assert command[:2] == ["git", "daemon"] and not any("receive-pack" in part for part in command)
    policy = next(d for d in docs if d["kind"] == "NetworkPolicy" and d["metadata"]["namespace"] == "devops-git")
    assert policy["spec"]["ingress"][0]["from"] == [{"namespaceSelector": {"matchLabels": {"kubernetes.io/metadata.name": "argocd"}},
                                                     "podSelector": {"matchLabels": {"app.kubernetes.io/name": "argocd-repo-server"}}}]
    labelled = [d["metadata"]["name"] for d in docs if "devops-ex" in (d["metadata"].get("labels") or {})]
    assert labelled == []
    appset = next(d for d in docs if d["metadata"]["name"] == "argocd-applicationset-controller" and d["kind"] == "Deployment")
    assert appset["spec"]["replicas"] == 0


def apply_as_learner(lab, doc: dict) -> subprocess.CompletedProcess:
    return lab.kubectl("apply", "-f", "-", input=json.dumps(doc), check=False)


@KUBE_REQUIRED
def test_argocd_application_syncs_only_into_lab_namespace_real(tmp_path):
    testkit.Exercise.require_argocd()
    source = gitops_tree(tmp_path / "gitops", "1")
    with testkit.KubeLab() as a, testkit.KubeLab() as b:
        a.argocd_project()
        b.argocd_project()
        a.gitops_repo(source)
        b.gitops_repo(source)
        assert apply_as_learner(a, argo_app(a.namespace)).returncode == 0
        started = time.monotonic()
        status = a.argocd_wait("web", timeout=120)
        first_sync = time.monotonic() - started
        assert status["sync"]["revision"] == a.gitops_revision
        assert a.kubectl("get", "configmap", "web", "-o", "jsonpath={.data.v}").stdout == "1"
        gitops_tree(source, "2")
        a.gitops_repo(source)
        started = time.monotonic()
        a.argocd_wait("web", timeout=120)
        resync = time.monotonic() - started
        assert a.kubectl("get", "configmap", "web", "-o", "jsonpath={.data.v}").stdout == "2"
        print(f"ArgoCD: sync đầu {first_sync:.1f}s, sync lại sau commit mới {resync:.1f}s")
        foreign = [
            argo_app(a.namespace, project="default"),
            argo_app(a.namespace, project=b.namespace),
            argo_app(a.namespace, destination={"server": "https://kubernetes.default.svc", "namespace": "default"}),
            argo_app(a.namespace, destination={"server": "https://kubernetes.default.svc", "namespace": b.namespace}),
            argo_app(a.namespace, destination={"server": "https://10.0.0.1:6443", "namespace": a.namespace}),
            argo_app(a.namespace, source={"repoURL": b.repo_url, "path": "app", "targetRevision": "main"}),
        ]
        for index, doc in enumerate(foreign):
            doc["metadata"]["name"] = f"foreign-{index}"
            result = apply_as_learner(a, doc)
            assert result.returncode != 0 and f"{a.namespace}-argocd" in result.stderr, (doc["spec"], result.stderr)
        assert not a.can_i("create", "appprojects.argoproj.io", serviceaccount="devops-ex-learner")
        assert not a.can_i("create", "applications.argoproj.io", serviceaccount="devops-ex-learner", all_namespaces=True)
        bypass = {
            "admin-default-project": argo_app(a.namespace, project="default"),
            "admin-foreign-namespace": argo_app(a.namespace, destination={"server": "https://kubernetes.default.svc",
                                                                         "namespace": b.namespace}),
            "admin-foreign-repo": argo_app(a.namespace, source={"repoURL": b.repo_url, "path": "app", "targetRevision": "main"}),
        }
        for name, doc in bypass.items():
            doc["metadata"].update(name=name, namespace=a.namespace)
            assert admin_kubectl("apply", "-f", "-", input=json.dumps(doc)).returncode == 0
        deadline = time.monotonic() + 60
        refused = {}
        while time.monotonic() < deadline and len(refused) < len(bypass):
            for name in bypass:
                got = json.loads(admin_kubectl("-n", a.namespace, "get", "applications.argoproj.io", name, "-o", "json").stdout)
                messages = " ".join(c.get("message", "") for c in (got.get("status") or {}).get("conditions") or [])
                if "not permitted" in messages or "do not match any of the allowed destinations" in messages:
                    refused[name] = messages
            time.sleep(2)
        assert set(refused) == set(bypass), refused
        assert b.kubectl("get", "configmap", "web", "--ignore-not-found", "-o", "name").stdout.strip() == ""
        escape = tmp_path / "escape"
        (escape / "app").mkdir(parents=True)
        (escape / "app" / "kustomization.yaml").write_text("resources: [objects.yaml]\n", encoding="utf-8")
        (escape / "app" / "objects.yaml").write_text(
            f"apiVersion: v1\nkind: ConfigMap\nmetadata: {{name: escaped, namespace: {b.namespace}}}\ndata: {{x: '1'}}\n---\n"
            f"apiVersion: rbac.authorization.k8s.io/v1\nkind: ClusterRole\nmetadata: {{name: {a.namespace}-escape, labels: "
            f"{{devops-ex: {a.id}}}}}\nrules: []\n---\n"
            "apiVersion: v1\nkind: ServiceAccount\nmetadata: {name: impersonated}\n", encoding="utf-8")
        a.gitops_repo(escape)
        with pytest.raises(pytest.fail.Exception) as info:
            a.argocd_wait("web", timeout=60)
        assert "not permitted in project" in str(info.value) or "is forbidden" in str(info.value), str(info.value)
        assert admin_kubectl("-n", b.namespace, "get", "configmap", "escaped").returncode != 0
        assert admin_kubectl("get", "clusterrole", f"{a.namespace}-escape").returncode != 0
    for lab in (a, b):
        assert testkit.kube_leftovers(lab.id) == []


@KUBE_REQUIRED
@SANDBOX_REQUIRED
def test_argocd_sops_secret_decrypted_on_sync_real(tmp_path):
    testkit.Exercise.require_argocd()
    testkit.Exercise.require_tool("sops", testkit.SOPS_MIN_VERSION)
    value = "mat-khau-" + os.urandom(6).hex()
    with testkit.KubeLab() as lab:
        lab.argocd_project()
        recipient = lab.sops_age_recipient
        assert re.fullmatch(r"age1[0-9a-z]{58}", recipient)
        repo = tmp_path / "repo"
        (repo / "app").mkdir(parents=True)
        (repo / ".sops.yaml").write_text(f"creation_rules:\n  - path_regex: .*\\.enc\\.yaml$\n    encrypted_regex: ^(data|stringData)$\n"
                                         f"    age: {recipient}\n", encoding="utf-8")
        (repo / "app" / "kustomization.yaml").write_text("resources: [secret.enc.yaml]\n", encoding="utf-8")
        (repo / "app" / "secret.enc.yaml").write_text(
            f"apiVersion: v1\nkind: Secret\nmetadata:\n  name: db\nstringData:\n  password: {value}\n", encoding="utf-8")
        home = tmp_path / "home"
        home.mkdir()
        encrypt = testkit.run_sandboxed(["sops", "encrypt", "--in-place", "app/secret.enc.yaml"], writable=[repo, home], cwd=repo,
                                        env={"HOME": str(home), "XDG_CONFIG_HOME": str(home / ".config")})
        assert encrypt.returncode == 0, encrypt.stderr
        assert not any(value in p.read_text(encoding="utf-8") for p in repo.rglob("*") if p.is_file())
        lab.gitops_repo(repo)
        app = argo_app(lab.namespace)
        app["spec"]["source"].update(plugin={"name": testkit.KUBE_ARGOCD_CMP})
        assert apply_as_learner(lab, app).returncode == 0
        status = lab.argocd_wait("web", timeout=120)
        assert value not in json.dumps(status)
        got = lab.kubectl("get", "secret", "db", "-o", "jsonpath={.data.password}").stdout
        assert base64.b64decode(got).decode() == value, "Secret sau khi sync không có đúng giá trị đã mã hoá"
        described = lab.kubectl("describe", "application.argoproj.io", "web").stdout
        assert value not in described
    assert testkit.kube_leftovers(lab.id) == []


@pytest.mark.parametrize("change,needle", [
    ({"operation": {"sync": {"source": {"repoURL": "git://git.devops-git.svc.cluster.local/devops-ex-0000beef.git"}}}},
     "operation.sync.source"),
    ({"operation": {"sync": {"sources": [{"repoURL": "https://github.com/x/y.git"}]}}}, "operation.sync.sources"),
    ({"operation": {"sync": {"manifests": ["apiVersion: v1\nkind: ConfigMap\n"]}}}, "operation.sync.manifests"),
    ({"status": {"health": {"status": "Healthy"}, "sync": {"status": "Synced"}}}, "status"),
])
def test_application_operation_source_and_status_refused(change, needle):
    namespace = "devops-ex-abc12345"
    ok = {**argo_app(namespace), "operation": {"sync": {"revision": "main", "prune": True}}}
    assert testkit.kube_manifest_problems([ok], lab_id="abc12345", namespace=namespace) == []
    problems = testkit.kube_manifest_problems([{**argo_app(namespace), **change}], lab_id="abc12345", namespace=namespace)
    assert any(needle in p for p in problems), problems


def test_application_policy_refuses_operation_source_and_status(monkeypatch):
    fake = ArgoFake(monkeypatch)
    with testkit.KubeLab() as lab:
        pass
    policy = next(i for i in bootstrap_items(fake) if i["metadata"]["name"] == f"{lab.namespace}-argocd"
                  and i["kind"] == "ValidatingAdmissionPolicy")
    expressions = [v["expression"] for v in policy["spec"]["validations"]]
    [operation] = [e for e in expressions if "object.operation" in e]
    for key in ("source", "sources", "manifests"):
        assert f"!has(object.operation.sync.{key})" in operation
    assert "object.operation == oldObject.operation" in operation
    [status] = [e for e in expressions if "object.status" in e]
    assert "request.operation == 'CREATE' ? !has(object.status)" in status and "object.status == oldObject.status" in status


def test_gitops_repo_size_cap(monkeypatch, tmp_path):
    ArgoFake(monkeypatch)
    monkeypatch.setattr(testkit, "KUBE_GITOPS_MAX_BYTES", 1000)
    monkeypatch.setattr(testkit, "KUBE_GITOPS_MAX_FILES", 5)
    big = tmp_path / "big"
    big.mkdir()
    (big / "blob.yaml").write_bytes(b"x" * 1001)
    many = tmp_path / "many"
    many.mkdir()
    for index in range(6):
        (many / f"f{index}.yaml").write_text("a: 1\n", encoding="utf-8")
    with testkit.KubeLab() as lab:
        for source in (big, many):
            with pytest.raises(pytest.fail.Exception, match="tối đa"):
                lab.gitops_repo(source)
        assert lab._git_repo is None
    assert testkit.KUBE_GITOPS_MAX_BYTES == 1000 and testkit.KUBE_GITOPS_MAX_FILES == 5


def test_close_releases_argocd_hook_finalizer(monkeypatch):
    fake = ArgoFake(monkeypatch, apps="application.argoproj.io/web\n")
    hooked = {"items": [
        {"apiVersion": "batch/v1", "kind": "Job", "metadata": {"name": "migrate", "finalizers": [
            testkit.KUBE_ARGOCD_HOOK_FINALIZER, "example.com/keep"]}},
        {"apiVersion": "v1", "kind": "Pod", "metadata": {"name": "hook-pod", "finalizers": [testkit.KUBE_ARGOCD_HOOK_FINALIZER]}},
        {"apiVersion": "v1", "kind": "ConfigMap", "metadata": {"name": "plain", "finalizers": ["example.com/keep"]}},
    ]}
    original = fake.run_sandboxed
    hook_lists = []

    def run_sandboxed(cmd, **kwargs):
        if "jobs.batch" in " ".join(map(str, cmd)) and "json" in cmd:
            hook_lists.append({"cmd": list(map(str, cmd)), "env": dict(kwargs["env"])})
            return subprocess.CompletedProcess(cmd, 0, json.dumps(hooked), "")
        return original(cmd, **kwargs)

    monkeypatch.setattr(testkit, "run_sandboxed", run_sandboxed)
    with testkit.KubeLab() as lab:
        pass
    [listed] = [c for c in hook_lists if "get" in c["cmd"]] or [None]
    assert listed is not None, "close() phải liệt kê hook trong namespace của lab"
    assert listed["cmd"][listed["cmd"].index("-n") + 1] == lab.namespace
    assert listed["env"]["KUBECONFIG"] == str(lab.admin_kubeconfig)
    kinds = [c for c in fake.calls_with("patch") if "--type=merge" in c["cmd"]]
    patches = {c["cmd"][c["cmd"].index("patch") + 1]: json.loads(c["cmd"][-1]) for c in kinds if "finalizers" in c["cmd"][-1]
               and "application.argoproj.io" not in c["cmd"][c["cmd"].index("patch") + 1]}
    assert patches == {"job.batch/migrate": {"metadata": {"finalizers": ["example.com/keep"]}},
                       "pod/hook-pod": {"metadata": {"finalizers": None}}}
    assert all(c["env"]["KUBECONFIG"] == str(lab.admin_kubeconfig) for c in kinds)
    order = [" ".join(c["cmd"]) for c in fake.sandbox_calls]
    first_patch = next(i for i, c in enumerate(order) if "job.batch/migrate" in c)
    namespace_delete = next(i for i, c in enumerate(order) if f"delete namespace {lab.namespace}" in c)
    assert first_patch < namespace_delete
    assert "argoproj.io" not in testkit._KUBE_HOOK_KINDS and "jobs.batch" in testkit._KUBE_HOOK_KINDS
    assert "gateway.networking.k8s.io" not in testkit._KUBE_HOOK_KINDS


@KUBE_REQUIRED
def test_kube_lab_close_releases_stuck_argocd_hook_real(tmp_path):
    testkit.Exercise.require_argocd()
    source = tmp_path / "gitops"
    (source / "app").mkdir(parents=True)
    (source / "app" / "kustomization.yaml").write_text("resources: [hook.yaml, web.yaml]\n", encoding="utf-8")
    (source / "app" / "web.yaml").write_text("apiVersion: v1\nkind: ConfigMap\nmetadata:\n  name: web\ndata:\n  v: '1'\n",
                                            encoding="utf-8")
    (source / "app" / "hook.yaml").write_text(
        "apiVersion: batch/v1\nkind: Job\nmetadata:\n  name: stuck\n  annotations:\n    argocd.argoproj.io/hook: PreSync\n"
        "spec:\n  template:\n    spec:\n      restartPolicy: Never\n      containers:\n        - name: c\n"
        f"          image: {testkit.KUBE_IMAGES['redis']}\n          envFrom: [{{configMapRef: {{name: missing}}}}]\n",
        encoding="utf-8")
    with testkit.KubeLab() as lab:
        lab.argocd_project()
        lab.gitops_repo(source)
        assert apply_as_learner(lab, argo_app(lab.namespace)).returncode == 0
        deadline = time.monotonic() + 90
        finalizers = []
        while time.monotonic() < deadline and testkit.KUBE_ARGOCD_HOOK_FINALIZER not in finalizers:
            got = lab.kubectl("get", "job", "stuck", "-o", "jsonpath={.metadata.finalizers}", check=False).stdout
            finalizers = json.loads(got) if got.strip() else []
            time.sleep(2)
        assert testkit.KUBE_ARGOCD_HOOK_FINALIZER in finalizers, "ArgoCD phải gắn hook-finalizer cho Job hook đang chạy"
    assert lab.cleanup_error is None, lab.cleanup_error
    assert admin_kubectl("get", "namespace", lab.namespace).returncode != 0
    assert testkit.kube_leftovers(lab.id) == []


def test_lab_entry_sweeps_gitops_of_killed_labs(monkeypatch):
    fake = ArgoFake(monkeypatch)
    original = fake.run_sandboxed
    alive, dead = "devops-ex-1111aaaa", "devops-ex-2222bbbb"

    def run(cmd, **kwargs):
        joined = " ".join(map(str, cmd))
        answer = None
        if joined.endswith("get namespaces -o name"):
            answer = f"namespace/default\nnamespace/{alive}\nnamespace/argocd\n"
        elif "get appprojects.argoproj.io -l devops-ex -o name" in joined:
            answer = f"appproject.argoproj.io/{alive}\nappproject.argoproj.io/{dead}\n"
        elif "ls -1A /srv/git /tmp" in joined:
            answer = f"/srv/git:\n{alive}.git\n{dead}.git\nnot-a-lab.git\n\n/tmp:\n{dead}.bundle\n"
        if answer is None:
            return original(cmd, **kwargs)
        fake.sandbox_calls.append({"cmd": list(map(str, cmd)), "env": dict(kwargs["env"]), "writable": [], "readonly": [],
                                   "cwd": None, "input": None})
        return subprocess.CompletedProcess(cmd, 0, answer, "")

    monkeypatch.setattr(testkit, "run_sandboxed", run)
    with testkit.KubeLab():
        pass
    deleted = [c["cmd"] for c in fake.sandbox_calls if "delete" in c["cmd"] and "appprojects.argoproj.io" in c["cmd"]
               and "-l" not in c["cmd"]]
    assert deleted == [[deleted[0][0], "-n", "argocd", "delete", "appprojects.argoproj.io", dead, "--ignore-not-found"]]
    removed = [c["cmd"] for c in fake.sandbox_calls if "rm" in c["cmd"] and "-rf" in c["cmd"]]
    assert len(removed) == 1
    assert removed[0][-2:] == [f"/srv/git/{dead}.git", f"/tmp/{dead}.bundle"]
    assert not any(alive in part or "not-a-lab" in part for part in removed[0])


def cmp_script() -> str:
    import yaml

    config = yaml.safe_load((testkit.KUBE_ARGOCD_DIR / "10-sops-cmp.yaml").read_text(encoding="utf-8"))
    plugin = yaml.safe_load(config["data"]["plugin.yaml"])
    command = plugin["spec"]["generate"]["command"]
    assert command == ["sh", "-c"]
    return plugin["spec"]["generate"]["args"][0]


@pytest.mark.parametrize("metadata,refused", [
    ("sops:\n    kms:\n        - arn: arn:aws:kms:us-east-1:1:key/x\n    age: []\n", True),
    ("sops:\n    hc_vault:\n        - vault_address: http://vault.example:8200\n", True),
    ("sops:\n    gcp_kms:\n        - resource_id: projects/x\n", True),
    ("sops:\n    azure_kv:\n        - vault_url: https://x.vault.azure.net\n", True),
    ("sops:\n    pgp:\n        - fp: ABCD\n", True),
    ('{"sops": {"key_groups": [{"kms": [{"arn": "x"}]}]}}\n', True),
    ("sops:\n    age:\n        - recipient: " + RECIPIENT + "\n          enc: x\n", False),
    ("sops:\n    'hc_vault':\n        - vault_address: http://vault.example:8200\n", False),
    ("sops:\n    ? hc_vault\n    : - vault_address: http://vault.example:8200\n", False),
    ('{"sops": {"hc_\\x76ault": [{"vault_address": "http://vault.example:8200"}]}}\n', False),
])
def test_cmp_accepts_only_age_recipients(tmp_path, metadata, refused):
    """Kiểm tên khoá trong script CMP chỉ là lớp từ chối sớm, kiểu denylist: ba cách viết cuối (khoá trong nháy đơn, khoá tường
    minh `? hc_vault`, escape trong chuỗi JSON) lọt qua grep. Ranh giới thật để sops không gọi ra ngoài là NetworkPolicy egress
    của repo-server cộng proxy chết (`test_argocd_repo_server_egress_and_git_locked_down`)."""
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "secret.enc.yaml").write_text("data:\n    password: ENC[AES256_GCM,data:x]\n" + metadata, encoding="utf-8")
    result = subprocess.run(["sh", "-c", cmp_script()], cwd=repo, capture_output=True, text=True, timeout=30,
                            env={"PATH": "/usr/bin:/bin"})
    assert result.returncode != 0
    assert ("Chỉ nhận tệp SOPS mã hoá bằng recipient age" in result.stderr) == refused, result.stderr


def test_argocd_repo_server_egress_and_git_locked_down():
    import yaml

    folder = testkit.KUBE_ARGOCD_DIR
    policy = yaml.safe_load((folder / "40-repo-server-egress.yaml").read_text(encoding="utf-8"))
    spec = policy["spec"]
    assert policy["metadata"]["namespace"] == "argocd" and spec["policyTypes"] == ["Egress"]
    assert spec["podSelector"] == {"matchLabels": {"app.kubernetes.io/name": "argocd-repo-server"}}
    allowed = {(rule["to"][0].get("podSelector", {}).get("matchLabels", {}).popitem()[1],
                tuple(sorted((p["port"], p["protocol"]) for p in rule["ports"]))) for rule in spec["egress"]}
    assert allowed == {("kube-dns", ((53, "TCP"), (53, "UDP"))), ("git", ((9418, "TCP"),)), ("argocd-redis", ((6379, "TCP"),))}
    kustomization = yaml.safe_load((folder / "kustomization.yaml").read_text(encoding="utf-8"))
    params = next(yaml.safe_load(p["patch"]) for p in kustomization["patches"] if p["target"]["name"] == "argocd-cmd-params-cm")
    assert params["data"]["reposerver.enable.git.submodule"] == "false"
    repo = next(yaml.safe_load(p["patch"]) for p in kustomization["patches"] if p["target"]["name"] == "argocd-repo-server")
    pod = repo["spec"]["template"]["spec"]
    containers = {c["name"]: c for c in pod["containers"]}
    sidecar_env = {e["name"]: e["value"] for e in containers["sops-kustomize"]["env"]}
    assert sidecar_env["GIT_CONFIG_KEY_0"] == "protocol.allow" and sidecar_env["GIT_CONFIG_VALUE_0"] == "never"
    assert sidecar_env["GIT_ALLOW_PROTOCOL"] == "none"
    main_env = {e["name"]: e["value"] for e in containers["argocd-repo-server"]["env"]}
    assert main_env["GIT_ALLOW_PROTOCOL"] == "git" and main_env["PATH"].startswith("/devops-tools:")
    assert {"name": "devops-repo-tools", "mountPath": "/devops-tools", "readOnly": True} in containers["argocd-repo-server"]["volumeMounts"]
    tools = yaml.safe_load((folder / "11-repo-tools.yaml").read_text(encoding="utf-8"))["data"]["kustomize"]
    assert "GIT_ALLOW_PROTOCOL=none" in tools and "GIT_CONFIG_VALUE_0=never" in tools and 'exec /usr/local/bin/kustomize "$@"' in tools
    for env in (main_env, sidecar_env):
        assert {env[k] for k in ("HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy")} == {"http://127.0.0.1:1"}
        assert env["NO_PROXY"] == ""
    assert containers["sops-kustomize"]["resources"]["limits"]["ephemeral-storage"] == "1Gi"
    tmp = next(v for v in pod["volumes"] if v["name"] == "cmp-tmp")
    assert tmp["emptyDir"]["sizeLimit"] == "512Mi"


def first_condition(lab, app: str, needles, timeout: float = 90) -> tuple[str, float]:
    started = time.monotonic()
    text = ""
    while time.monotonic() - started < timeout:
        got = json.loads(admin_kubectl("-n", lab.namespace, "get", "applications.argoproj.io", app, "-o", "json").stdout)
        status = got.get("status") or {}
        text = " ".join([c.get("message", "") for c in status.get("conditions") or []]
                        + [(status.get("operationState") or {}).get("message") or ""])
        if any(n in text for n in needles):
            return text, time.monotonic() - started
        time.sleep(1)
    return text, time.monotonic() - started


@KUBE_REQUIRED
def test_argocd_operation_status_and_remote_bases_refused_real(tmp_path):
    testkit.Exercise.require_argocd()
    with testkit.KubeLab() as a, testkit.KubeLab() as b:
        a.argocd_project()
        b.argocd_project()
        b.gitops_repo(gitops_tree(tmp_path / "b", "cua-lab-b"))
        a.gitops_repo(gitops_tree(tmp_path / "a", "1"))
        attack = argo_app(a.namespace)
        attack["metadata"]["name"] = "steal"
        attack["operation"] = {"sync": {"source": {"repoURL": b.repo_url, "path": "app", "targetRevision": "main"}}}
        result = apply_as_learner(a, attack)
        assert result.returncode != 0 and f"{a.namespace}-argocd" in result.stderr, result.stderr
        app = argo_app(a.namespace)
        app["spec"].pop("syncPolicy")
        assert apply_as_learner(a, app).returncode == 0
        a.argocd_wait("web", sync="OutOfSync", health=None, timeout=60)
        for patch in ({"operation": {"sync": {"sources": [{"repoURL": b.repo_url, "path": "app"}]}}},
                      {"operation": {"sync": {"manifests": ["apiVersion: v1\nkind: ConfigMap\nmetadata: {name: x}\n"]}}},
                      {"status": {"health": {"status": "Healthy"}, "sync": {"status": "Synced", "revision": a.gitops_revision}}}):
            result = a.kubectl("patch", "applications.argoproj.io", "web", "--type=merge", "-p", json.dumps(patch), check=False)
            assert result.returncode != 0 and f"{a.namespace}-argocd" in result.stderr, (patch, result.stderr)
        result = a.kubectl("patch", "applications.argoproj.io", "web", "--type=merge", "-p",
                           json.dumps({"operation": {"sync": {"revision": "main"}}}), check=False)
        assert result.returncode == 0, result.stderr
        a.argocd_wait("web", timeout=60)
        assert a.kubectl("get", "configmap", "web", "-o", "jsonpath={.data.v}").stdout == "1"
        assert a.kubectl("get", "configmap", "web", "-o", "jsonpath={.data.v}").stdout != "cua-lab-b"
        remote = tmp_path / "remote"
        (remote / "app").mkdir(parents=True)
        (remote / "app" / "kustomization.yaml").write_text(f"resources:\n  - git::{b.repo_url}//app?ref=main\n", encoding="utf-8")
        a.gitops_repo(remote)
        text, seconds = first_condition(a, "web", ("kustomize build",))
        assert seconds < 25 and "kustomize build" in text and "timeout after" not in text, text
        assert a.kubectl("get", "configmap", "web", "-o", "jsonpath={.data.v}").stdout == "1"
        print(f"Remote base trỏ repo của lab khác (git://) bị từ chối sau {seconds:.1f}s")
        (remote / "app" / "kustomization.yaml").write_text(
            "resources:\n  - https://github.com/kubernetes-sigs/kustomize//examples/helloWorld?ref=v5.0.0\n", encoding="utf-8")
        a.gitops_repo(remote)
        text, seconds = first_condition(a, "web", ("helloWorld",))
        assert seconds < 25 and "timeout after" not in text, text
        print(f"Remote base (built-in kustomize) bị từ chối sau {seconds:.1f}s: {text[:200]}")
        a.kubectl("patch", "applications.argoproj.io", "web", "--type=merge", "-p",
                  json.dumps({"spec": {"source": {"plugin": {"name": testkit.KUBE_ARGOCD_CMP}}}}))
        (remote / "app" / "kustomization.yaml").write_text(
            "resources:\n  - https://raw.githubusercontent.com/kubernetes-sigs/kustomize/v5.0.0/examples/helloWorld/deployment.yaml\n",
            encoding="utf-8")
        a.gitops_repo(remote)
        text, seconds = first_condition(a, "web", ("CMP processing failed",))
        assert seconds < 25 and "CMP processing failed" in text and "timeout after" not in text, text
        print(f"Remote URL (CMP) bị từ chối sau {seconds:.1f}s: {text[:200]}")
        assert a.kubectl("get", "deployment", "--ignore-not-found", "-o", "name").stdout.strip() == ""
    for lab in (a, b):
        assert testkit.kube_leftovers(lab.id) == []


def test_gitops_repo_caps_total_history(monkeypatch, tmp_path):
    ArgoFake(monkeypatch)
    monkeypatch.setattr(testkit, "KUBE_GITOPS_MAX_REPO_BYTES", 150_000)
    source = tmp_path / "gitops"
    source.mkdir()
    with testkit.KubeLab() as lab:
        (source / "blob.bin").write_bytes(os.urandom(100_000))
        lab.gitops_repo(source)
        first = lab.gitops_revision
        (source / "blob.bin").write_bytes(os.urandom(100_000))
        with pytest.raises(pytest.fail.Exception, match="cho cả lab"):
            lab.gitops_repo(source)
        assert lab.gitops_revision == first
        assert lab._git_repo.out("rev-parse", "HEAD") == first
        assert not list(lab._admin.home.glob("*.bundle"))


def test_gitops_repo_counts_bytes_read_not_reported_size(monkeypatch, tmp_path):
    ArgoFake(monkeypatch)
    monkeypatch.setattr(testkit, "KUBE_GITOPS_MAX_BYTES", 1000)
    source = tmp_path / "gitops"
    source.mkdir()
    grown = source / "grown.yaml"
    grown.write_bytes(b"x" * 5000)
    real_stat = Path.stat

    def small_stat(self, *args, **kwargs):
        result = real_stat(self, *args, **kwargs)
        if self == grown:
            return os.stat_result((result.st_mode, *tuple(result)[1:6], 10, *tuple(result)[7:]))
        return result

    monkeypatch.setattr(Path, "stat", small_stat)
    assert grown.stat().st_size == 10
    with testkit.KubeLab() as lab:
        with pytest.raises(pytest.fail.Exception, match="vượt 1000 byte"):
            lab.gitops_repo(source)
        assert lab._git_repo is None


OBS_SERVICES = {"otel-collector", "jaeger", "loki", "prometheus", "alertmanager", "grafana"}
OBS_DATA_DIRS = {"prometheus": "/prometheus", "alertmanager": "/alertmanager", "loki": "/loki", "jaeger": "/tmp"}


def obs_compose() -> dict:
    import yaml

    return yaml.safe_load((testkit.OBS_DIR / "compose.yaml").read_text(encoding="utf-8"))


def test_obs_images_pinned_by_digest_and_match_compose():
    assert set(testkit.OBS_IMAGES) == OBS_SERVICES == set(testkit.OBS_READY)
    for image in testkit.OBS_IMAGES.values():
        assert re.fullmatch(r"[a-z0-9./-]+:v?\d+\.\d+\.\d+@sha256:[0-9a-f]{64}", image), image
    services = obs_compose()["services"]
    assert {name: svc["image"] for name, svc in services.items()} == testkit.OBS_IMAGES
    for name, svc in services.items():
        assert all(port.startswith("127.0.0.1:") for port in svc.get("ports", [])), name
        assert all(volume.startswith("./") and volume.endswith(":ro") for volume in svc.get("volumes", [])), name
        assert svc["cpuset"] == "${DEVOPS_CPUSET:-}"
    for name, path in OBS_DATA_DIRS.items():
        assert any(t.split(":")[0] == path for t in services[name]["tmpfs"]), (
            f"{name}: image có VOLUME {path}, phải phủ tmpfs để không sinh volume ẩn danh")
    assert testkit.OBS_PULL.count("docker pull ") == len(testkit.OBS_IMAGES)


def test_obs_defaults_point_at_stack_services():
    import yaml

    prom = yaml.safe_load((testkit.OBS_DIR / "prometheus" / "prometheus.yml").read_text(encoding="utf-8"))
    targets = {c["job_name"]: c["static_configs"][0]["targets"] for c in prom["scrape_configs"]}
    assert targets["olist-api"] == ["api:8000"] and targets["olist-worker"] == ["worker:9101"]
    assert prom["alerting"]["alertmanagers"][0]["static_configs"][0]["targets"] == ["alertmanager:9093"]
    collector = yaml.safe_load((testkit.OBS_DIR / "otel-collector" / "config.yaml").read_text(encoding="utf-8"))
    pipelines = collector["service"]["pipelines"]
    assert "otlp/jaeger" in pipelines["traces"]["exporters"] and pipelines["logs"]["exporters"] == ["otlphttp/loki"]
    sources = yaml.safe_load((testkit.OBS_DIR / "grafana" / "provisioning" / "datasources" / "datasources.yaml").read_text(encoding="utf-8"))
    assert {d["uid"] for d in sources["datasources"]} == {"prometheus", "loki", "jaeger"}


OBS_PROJECT_COMPOSE = """
name: olist-cua-nguoi-hoc
services:
  api:
    build: .
    environment:
      OTEL_EXPORTER_OTLP_ENDPOINT: http://otel-collector:4317
    networks: [backend]
networks:
  backend: {}
"""


def test_obs_stage_merges_project_and_overlays_config(tmp_path):
    import yaml

    project = tmp_path / "project"
    write_compose(project, OBS_PROJECT_COMPOSE)
    rules = project / "observability" / "prometheus" / "rules"
    rules.mkdir(parents=True)
    (rules / "olist.yml").write_text("groups: []\n", encoding="utf-8")
    (project / "observability" / "otel-collector").mkdir()
    (project / "observability" / "otel-collector" / "config.yaml").write_text("receivers: {}\n", encoding="utf-8")
    (project / "Dockerfile").write_text("FROM scratch\n", encoding="utf-8")
    (project / "entrypoint.sh").write_text("#!/bin/sh\n", encoding="utf-8")
    (project / "entrypoint.sh").chmod(0o700)
    project.chmod(0o700)
    stage = tmp_path / "stage"
    stage.mkdir(mode=0o700)
    file = testkit._obs_stage(stage, project)
    merged = yaml.safe_load(file.read_text(encoding="utf-8"))
    assert "name" not in merged, "Tên project do DockerLab đặt (devops-ex-<id>), không lấy name: của người học"
    assert set(merged["services"]) == OBS_SERVICES | {"api"}
    assert merged["services"]["api"]["build"] == "."
    assert merged["services"]["prometheus"]["volumes"] == ["./observability/prometheus:/etc/prometheus:ro"]
    for name in OBS_SERVICES:
        assert merged["services"][name]["networks"] == ["default", "backend"]
    config = stage / "observability"
    assert (config / "prometheus" / "rules" / "watchdog.yml").is_file(), "Tệp mặc định vẫn còn khi người học thêm rule"
    assert (config / "prometheus" / "rules" / "olist.yml").read_text(encoding="utf-8") == "groups: []\n"
    assert (config / "otel-collector" / "config.yaml").read_text(encoding="utf-8") == "receivers: {}\n"
    assert not (config / "compose.yaml").exists()
    for path in [stage, *stage.rglob("*")]:
        wanted = 0o755 if path.is_dir() else 0o644
        assert path.stat().st_mode & wanted == wanted, f"{path}: container (uid khác) phải đọc được"
    assert (stage / "entrypoint.sh").stat().st_mode & 0o777 == 0o744, "Giữ bit thực thi của tệp người học"
    assert (project / "observability" / "otel-collector" / "config.yaml").read_text(encoding="utf-8") == "receivers: {}\n"


def test_obs_stage_without_project_has_only_stack(tmp_path):
    import yaml

    merged = yaml.safe_load(testkit._obs_stage(tmp_path, None).read_text(encoding="utf-8"))
    assert set(merged["services"]) == OBS_SERVICES
    assert all("networks" not in svc for svc in merged["services"].values())


@pytest.mark.parametrize("name", ["prometheus", "otel-collector"])
def test_obs_stage_refuses_service_clash(tmp_path, name):
    project = tmp_path / "project"
    write_compose(project, f"services:\n  {name}:\n    image: {BASE}\n")
    with pytest.raises(pytest.fail.Exception, match=f"service {name} trùng tên"):
        testkit._obs_stage(tmp_path / "stage", project)


def test_obs_stack_skips_without_images(monkeypatch):
    missing = testkit.OBS_IMAGES["grafana"]

    def fake(*args, **kwargs):
        return subprocess.CompletedProcess(args, 1 if missing in args else 0, "", "")

    monkeypatch.setattr(testkit, "_docker", fake)
    monkeypatch.setattr(testkit.Exercise, "require_tool", staticmethod(lambda *a, **k: None))
    with pytest.raises(pytest.skip.Exception) as info:
        with testkit.DockerLab() as lab:
            testkit.ObsStack(lab)
    assert f"Chưa có image {missing}" in str(info.value) and testkit.OBS_PULL in str(info.value)


@pytest.mark.parametrize("message,skipped", [
    (f"docker build api lỗi (mã 1). 40 dòng cuối:\n{(BUILD_LOGS / 'pip-offline.log').read_text(encoding='utf-8')}", True),
    (f"docker build api lỗi (mã 1). 40 dòng cuối:\n{(BUILD_LOGS / 'pip-retry-then-missing-package.log').read_text(encoding='utf-8')}", False),
    ("docker compose up lỗi: api unhealthy\napi-1 | psycopg.OperationalError: Could not resolve host postgres", False),
])
def test_obs_stack_skips_only_on_build_network_failure(monkeypatch, message, skipped):
    monkeypatch.setattr(testkit, "_docker", lambda *a, **k: subprocess.CompletedProcess(a, 0, "", ""))
    monkeypatch.setattr(testkit.Exercise, "require_image", staticmethod(lambda *a, **k: None))

    def compose(self, file, **kwargs):
        pytest.fail(message)

    monkeypatch.setattr(testkit.DockerLab, "compose", compose)
    expected = pytest.skip.Exception if skipped else pytest.fail.Exception
    with pytest.raises(expected) as info:
        with testkit.DockerLab() as lab:
            testkit.ObsStack(lab)
    assert ("cần mạng" in str(info.value)) is skipped


@pytest.mark.parametrize("where", ["observability/prometheus", "observability/prometheus/prometheus.yml"])
def test_obs_stage_symlink_over_default_fails_clearly(tmp_path, where):
    project = tmp_path / "project"
    target = project / where
    target.parent.mkdir(parents=True)
    (tmp_path / "elsewhere").mkdir()
    target.symlink_to(tmp_path / "elsewhere")
    with pytest.raises(pytest.fail.Exception, match="không chép được project"):
        testkit._obs_stage(tmp_path / "stage", project)


def require_obs_images():
    for image in testkit.OBS_IMAGES.values():
        require_real_docker(image)


def test_obs_stack_loopback_and_cleanup(monkeypatch):
    require_obs_images()
    monkeypatch.setenv("DEVOPS_CPUSET", build_cpuset())
    defaults = {int(port) for svc in obs_compose()["services"].values() for spec in svc.get("ports", [])
                for port in re.findall(r":-(\d+)\}", spec)}
    assert len(defaults) == 8
    lab = testkit.DockerLab()
    with lab:
        stack = testkit.ObsStack(lab)
        rows = stack.project.ps()
        assert {row["Service"] for row in rows} == OBS_SERVICES
        for row in rows:
            info = inspect_container(row["Name"])
            assert info["Config"]["Labels"]["devops-ex"] == "1"
            assert "no-new-privileges:true" in info["HostConfig"]["SecurityOpt"]
            assert info["HostConfig"]["CpusetCpus"] == build_cpuset()
            for bindings in (info["HostConfig"]["PortBindings"] or {}).values():
                assert all(b["HostIp"] == "127.0.0.1" for b in bindings), row["Name"]
                assert not {int(b["HostPort"]) for b in bindings} & defaults, f"{row['Name']} giữ cổng cố định"
            mounts = info["Mounts"]
            assert not [m for m in mounts if m["Type"] == "volume"], f"{row['Service']} tạo volume: {mounts}"
            assert all(not m["RW"] for m in mounts if m["Type"] == "bind"), row["Name"]
        assert "devops-obs-stack" in {d["uid"] for d in stack.grafana_dashboards()}
        assert "Watchdog" in {a["labels"]["alertname"] for a in stack.alerts(timeout=60)}
        up = {r["metric"]["job"]: r["value"][1] for r in stack.prom_query('up{job=~"prometheus|otel-collector"}', timeout=30)}
        assert up == {"prometheus": "1", "otel-collector": "1"}
        with pytest.raises(pytest.fail.Exception, match="prometheus /api/v1/query trả 400"):
            stack.prom_query("rate(")
        assert stack.jaeger_traces("khong-co-service") == []
    assert testkit.docker_leftovers(lab.id) == []
    project = testkit._docker("volume", "ls", "-q", "--filter", f"label=com.docker.compose.project=devops-ex-{lab.id}")
    assert project.stdout.split() == []


OBS_OLIST_COMPOSE = f"""
x-app: &app
  build: .
  environment:
    DATABASE_URL: postgresql+psycopg://olist:olist@postgres:5432/olist
    REDIS_URL: redis://redis:6379/0
    OTEL_EXPORTER_OTLP_ENDPOINT: http://otel-collector:4317
  depends_on:
    postgres: {{condition: service_healthy}}
    redis: {{condition: service_started}}
services:
  postgres:
    image: {testkit.KUBE_IMAGES["postgres"]}
    environment: {{POSTGRES_USER: olist, POSTGRES_PASSWORD: olist, POSTGRES_DB: olist}}
    tmpfs: ["/var/lib/postgresql/data"]
    healthcheck: {{test: ["CMD-SHELL", "pg_isready -U olist -d olist"], interval: 2s, retries: 30}}
  redis:
    image: {testkit.KUBE_IMAGES["redis"]}
    tmpfs: ["/data"]
  api:
    <<: *app
    ports: ["8000"]
  worker:
    <<: *app
    command: ["python", "-m", "olist_shop.worker"]
"""


def test_obs_stack_olist_trace_log_metric(monkeypatch, tmp_path):
    import httpx

    require_obs_images()
    for image in (testkit.KUBE_IMAGES["postgres"], testkit.KUBE_IMAGES["redis"], "python:3.12.16-slim-trixie"):
        require_real_docker(image)
    monkeypatch.setenv("DEVOPS_CPUSET", build_cpuset())
    app = testkit.ROOT / "tracks" / "devops" / "sample-app"
    project = tmp_path / "project"
    shutil.copytree(app / "olist_shop", project / "olist_shop", ignore=shutil.ignore_patterns("__pycache__"))
    shutil.copy(app / "requirements.txt", project)
    shutil.copy(testkit.KUBE_OLIST_DOCKERFILE, project / "Dockerfile")
    write_compose(project, OBS_OLIST_COMPOSE)
    lab = testkit.DockerLab()
    with lab:
        stack = testkit.ObsStack(lab, project=project)
        api = f"http://127.0.0.1:{stack.project.port('api', 8000)}"
        with httpx.Client(trust_env=False, timeout=10) as client:
            assert client.get(f"{api}/orders/khong-co", headers={"X-Request-ID": "obs-order"}).status_code == 404
            assert client.post(f"{api}/jobs/recompute", headers={"X-Request-ID": "obs-job"}).status_code == 202

        def order_traces():
            return [t for t in stack.jaeger_traces("olist-shop-api") if any(s["name"] == "GET /orders/{order_id}" for s in t["spans"])]

        trace = stack.eventually(order_traces, 60)
        assert trace, "Không thấy trace của GET /orders/{order_id} trong Jaeger"
        spans = trace[0]["spans"]
        server = next(s for s in spans if s["name"] == "GET /orders/{order_id}")
        db = [s for s in spans if s["attributes"].get("db.system.name") == "postgresql"]
        assert db and all(s["parentSpanID"] == server["spanID"] for s in db), "Trace phải có span DB là con của span HTTP"

        def job_traces():
            return [t for t in stack.jaeger_traces("olist-shop-worker") if any(s["name"] == "process olist:jobs" for s in t["spans"])]

        job = stack.eventually(job_traces, 60)
        assert job and {s["service"] for s in job[0]["spans"]} == {"olist-shop-api", "olist-shop-worker"}, \
            "Trace của job phải đi từ API qua Redis tới worker"
        trace_id = trace[0]["traceID"]
        logs = stack.loki_query(f'{{service_name="olist-shop-api"}} |= "{trace_id}"', timeout=60)
        lines = [json.loads(value) for stream in logs for _, value in stream["values"]]
        assert any(line["request_id"] == "obs-order" and line["trace_id"] == trace_id for line in lines), lines
        metric = stack.prom_query('http_requests_total{job="olist-api", path="/orders/{order_id}", status="404"}', timeout=30)
        assert metric and metric[0]["value"][1] == "1"
        spans = stack.prom_query('traces_span_metrics_calls_total{service_name="olist-shop-api", span_name="GET /orders/{order_id}"}',
                                 timeout=60)
        assert spans, "spanmetrics của Collector phải tới Prometheus"
    assert testkit.docker_leftovers(lab.id) == []


def test_promtool_amtool_argv(monkeypatch, tmp_path):
    fake = FakeDocker()
    monkeypatch.setattr(testkit.subprocess, "run", fake)
    monkeypatch.setattr(testkit.Exercise, "require_image", staticmethod(lambda *a, **k: None))
    monkeypatch.setenv("DEVOPS_CPUSET", "2-3")
    testkit.promtool("check", "rules", "rules.yml", cwd=tmp_path)
    testkit.amtool("check-config", "alertmanager.yml", cwd=tmp_path)
    runs = [c for c in fake.calls if c[:2] == ["docker", "run"]]
    assert len(runs) == 2
    for argv, image, entrypoint, args in ((runs[0], testkit.OBS_IMAGES["prometheus"], "/bin/promtool", ["check", "rules", "rules.yml"]),
                                          (runs[1], testkit.OBS_IMAGES["alertmanager"], "/bin/amtool", ["check-config", "alertmanager.yml"])):
        assert "--rm" in argv and argv[argv.index("-v") + 1] == f"{tmp_path.resolve()}:/work:ro"
        assert argv.count("-v") == 1 and "-p" not in argv
        assert argv[argv.index("--user") + 1] == f"{os.getuid()}:{os.getgid()}"
        assert argv[argv.index("--workdir") + 1] == "/work" and argv[argv.index("--entrypoint") + 1] == entrypoint
        assert argv[argv.index("--cpuset-cpus") + 1] == "2-3" and "no-new-privileges" in argv
        assert argv[argv.index("--network") + 1].startswith("devops-ex-")
        assert argv[-len(args) - 1:] == [image, *args]
    assert [c for c in fake.calls if c[1:3] == ["network", "rm"]], "Network của lab chạy promtool được dọn"


PROM_RULES = """groups:
  - name: olist
    rules:
      - alert: ApiDown
        expr: up{job="olist-api"} == 0
        for: 1m
"""
PROM_RULES_TEST = """rule_files: [rules.yml]
evaluation_interval: 1m
tests:
  - interval: 1m
    input_series:
      - series: 'up{job="olist-api", instance="api:8000"}'
        values: '0x5'
    alert_rule_test:
      - eval_time: 3m
        alertname: ApiDown
        exp_alerts:
          - exp_labels: {job: olist-api, instance: "api:8000"}
"""


def test_promtool_readonly_mount(tmp_path):
    require_real_docker(testkit.OBS_IMAGES["prometheus"])
    require_real_docker(testkit.OBS_IMAGES["alertmanager"])
    work = tmp_path / "work"
    work.mkdir(mode=0o700)
    (work / "rules.yml").write_text(PROM_RULES, encoding="utf-8")
    (work / "tests.yml").write_text(PROM_RULES_TEST, encoding="utf-8")
    (work / "data.om").write_text("# TYPE x counter\nx_total 1 1700000000\n# EOF\n", encoding="utf-8")
    (work / "alertmanager.yml").write_text("route: {receiver: default}\nreceivers: [{name: default}]\n", encoding="utf-8")
    checked = testkit.promtool("check", "rules", "rules.yml", cwd=work)
    assert checked.returncode == 0, checked.stdout + checked.stderr
    tested = testkit.promtool("test", "rules", "tests.yml", cwd=work)
    assert tested.returncode == 0 and "SUCCESS" in tested.stdout + tested.stderr, tested.stdout + tested.stderr
    (work / "tests.yml").write_text(PROM_RULES_TEST.replace("eval_time: 3m", "eval_time: 30s"), encoding="utf-8")
    assert testkit.promtool("test", "rules", "tests.yml", cwd=work).returncode != 0
    written = testkit.promtool("tsdb", "create-blocks-from", "openmetrics", "data.om", "blocks", cwd=work)
    assert written.returncode != 0 and "read-only file system" in (written.stdout + written.stderr).lower()
    assert sorted(p.name for p in work.iterdir()) == ["alertmanager.yml", "data.om", "rules.yml", "tests.yml"]
    config = testkit.amtool("check-config", "alertmanager.yml", cwd=work)
    assert config.returncode == 0, config.stdout + config.stderr
    (work / "alertmanager.yml").write_text("route: {receiver: missing}\nreceivers: [{name: default}]\n", encoding="utf-8")
    assert testkit.amtool("check-config", "alertmanager.yml", cwd=work).returncode != 0
    names = testkit._docker("ps", "-a", "--filter", "name=devops-ex-", "--format", "{{.Names}}").stdout.split()
    assert not [n for n in names if n.endswith(("-promtool", "-amtool"))]


LAMBDA_PROBE_HANDLER = '''import json
import os
import urllib.request

import boto3
from botocore.config import Config


def handler(event, context):
    sqs = boto3.client("sqs")
    real = boto3.client("sqs", endpoint_url="https://sqs.us-east-1.amazonaws.com", config=Config(retries={"max_attempts": 1}))
    try:
        real.list_queues()
        real_aws = "reachable"
    except Exception as error:
        real_aws = type(error).__name__
    try:
        urllib.request.urlopen("http://169.254.169.254/latest/meta-data/", timeout=2)
        metadata = "reachable"
    except Exception as error:
        metadata = type(error).__name__
    session = boto3.session.Session()
    credentials = session.get_credentials()
    return {
        "env": {k: v for k, v in os.environ.items() if k.startswith(("AWS_", "HTTP", "http", "NO_", "no_", "APP_", "DOCKER"))},
        "endpoint": sqs.meta.endpoint_url,
        "credentials": [credentials.access_key, credentials.secret_key, credentials.method],
        "region": session.region_name,
        "sockets": [p for p in ("/var/run/docker.sock", "/run/docker.sock") if os.path.exists(p)],
        "uid": os.getuid(),
        "real_aws": real_aws,
        "metadata": metadata,
        "writable_task": os.access("/var/task", os.W_OK),
    }
'''

LAMBDA_SQS_HANDLER = '''import json
import os

import boto3


def handler(event, context):
    if event.get("Records"):
        return {"orders": [json.loads(r["body"])["order_id"] for r in event["Records"]]}
    sqs = boto3.client("sqs")
    url = sqs.get_queue_url(QueueName=os.environ["QUEUE_NAME"])["QueueUrl"]
    seen = []
    for message in sqs.receive_message(QueueUrl=url, MaxNumberOfMessages=10, WaitTimeSeconds=2).get("Messages", []):
        seen.append(json.loads(message["Body"])["order_id"])
        sqs.delete_message(QueueUrl=url, ReceiptHandle=message["ReceiptHandle"])
    if event.get("boom"):
        raise ValueError("hỏng")
    if event.get("sleep"):
        import time
        time.sleep(event["sleep"])
    return {"orders": seen, "remaining_ms": context.get_remaining_time_in_millis()}
'''


def write_handler(directory: Path, text: str, requirements: str | None = None) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "app.py").write_text(text, encoding="utf-8")
    if requirements is not None:
        (directory / "requirements.txt").write_text(requirements, encoding="utf-8")
    return directory


def require_lambda_image():
    return require_real_docker(testkit.LAMBDA_IMAGE)


def test_lambda_image_pinned_by_digest():
    assert re.fullmatch(r"public\.ecr\.aws/lambda/python:3\.12\.\d{4}\.\d{2}\.\d{2}\.\d{2}@sha256:[0-9a-f]{64}", testkit.LAMBDA_IMAGE)
    assert testkit.LAMBDA_PULL == f"docker pull {testkit.LAMBDA_IMAGE}"
    assert "boto3" in testkit.LAMBDA_BUNDLED and "requests" not in testkit.LAMBDA_BUNDLED


@pytest.mark.parametrize("key", ["AWS_ENDPOINT_URL", "aws_access_key_id", "AWS_PROFILE", "AWS_LAMBDA_FUNCTION_TIMEOUT", "_HANDLER",
                                 "LAMBDA_TASK_ROOT", "HTTPS_PROXY", "no_proxy", "PYTHONPATH", "LD_PRELOAD", "PATH", "BAD-KEY",
                                 "X=Y"])
def test_lambda_lab_refuses_reserved_env(tmp_path, key):
    with pytest.raises(pytest.fail.Exception, match="không cho đặt biến"):
        testkit.LambdaLab(testkit.DockerLab(), tmp_path, "app.handler", env={key: "x"})


@pytest.mark.parametrize("handler", ["app", "app.", "../app.handler", "app.handler; rm", "-app.handler"])
def test_lambda_lab_refuses_bad_handler(tmp_path, handler):
    with pytest.raises(ValueError):
        testkit.LambdaLab(testkit.DockerLab(), tmp_path, handler)


@pytest.mark.parametrize("text,problems", [
    ("boto3==1.42.97\nbotocore>=1.40  # có sẵn\n\n# chú thích\nPython-Dateutil\n", 0),
    ("requests==2.32.0\nboto3\n", 1),
    ("-r other.txt\n--index-url https://x\n", 2),
    ("git+https://example.com/x.git\n./local\n", 2),
])
def test_lambda_requirements_only_bundled(tmp_path, text, problems):
    write_handler(tmp_path, "def handler(e, c):\n    return {}\n", text)
    assert len(testkit._lambda_requirement_problems(tmp_path)) == problems


def test_lambda_lab_run_args_hardened(monkeypatch, tmp_path):
    monkeypatch.setenv("DEVOPS_CPUSET", "12-35")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "host-secret")
    lab = testkit.DockerLab()
    fn = testkit.LambdaLab(lab, write_handler(tmp_path / "h", "def handler(e, c):\n    return {}\n"), "app.handler",
                           env={"APP_TABLE": "orders"}, memory="512m", timeout=7)
    fn.endpoint = "http://172.30.0.1:40000"
    assert fn.network == f"{lab.network}-lambda-net"
    isolated = " ".join(fn.run_args(41000))
    assert f"--network {lab.network}-lambda-net " in isolated and "-p " not in isolated
    shared = testkit.LambdaLab(lab, tmp_path / "h", "app.handler", isolated=False)
    assert f"--network {lab.network} " in " ".join(shared.run_args(41000)) and "-p 127.0.0.1:41000:8080" in " ".join(shared.run_args(41000))
    argv = fn.run_args(41000)
    joined = " ".join(argv)
    assert argv[:3] == ["docker", "run", "-d"] and argv[-2:] == [testkit.LAMBDA_IMAGE, "app.handler"]
    for flag in ("--read-only", "--cap-drop ALL", "--security-opt no-new-privileges", "--memory 512m", "--cpuset-cpus 12-35",
                 f"-v {tmp_path / 'h'}:/var/task:ro"):
        assert flag in joined
    assert "docker.sock" not in joined and "host-secret" not in joined and "--privileged" not in joined
    assert [a for a in argv if a.startswith("-v")] == ["-v"] and argv.count("-v") == 1
    env = dict(argv[i + 1].split("=", 1) for i, a in enumerate(argv) if a == "-e")
    assert env["AWS_ENDPOINT_URL"] == "http://172.30.0.1:40000"
    assert (env["AWS_ACCESS_KEY_ID"], env["AWS_SECRET_ACCESS_KEY"]) == ("test", "test")
    assert env["AWS_CONFIG_FILE"] == env["AWS_SHARED_CREDENTIALS_FILE"] == "/dev/null"
    assert env["AWS_EC2_METADATA_DISABLED"] == "true" and env["AWS_REGION"] == "us-east-1"
    assert env["AWS_LAMBDA_FUNCTION_TIMEOUT"] == "7" and env["AWS_LAMBDA_FUNCTION_MEMORY_SIZE"] == "512"
    assert env["HTTPS_PROXY"] == testkit.LAMBDA_DEAD_PROXY and env["NO_PROXY"] == "127.0.0.1,localhost,172.30.0.1"
    assert env["APP_TABLE"] == "orders"
    assert not {k for k in env if k.startswith("AWS_")} - {
        "AWS_ENDPOINT_URL", "AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY", "AWS_REGION", "AWS_DEFAULT_REGION", "AWS_CONFIG_FILE",
        "AWS_SHARED_CREDENTIALS_FILE", "AWS_EC2_METADATA_DISABLED", "AWS_LAMBDA_FUNCTION_NAME", "AWS_LAMBDA_FUNCTION_MEMORY_SIZE",
        "AWS_LAMBDA_FUNCTION_TIMEOUT"}


def test_lambda_lab_refuses_outside_docker_lab_with(tmp_path):
    fn = testkit.LambdaLab(testkit.DockerLab(), write_handler(tmp_path, "def handler(e, c):\n    return {}\n"), "app.handler")
    with pytest.raises(RuntimeError):
        fn.invoke({})
    with pytest.raises(RuntimeError):
        with fn:
            pass


def test_lambda_lab_refuses_extra_requirements(tmp_path):
    require_lambda_image()
    write_handler(tmp_path / "h", "def handler(e, c):\n    return {}\n", "requests==2.32.0\n")
    with testkit.DockerLab() as lab:
        with pytest.raises(pytest.fail.Exception, match="requests"):
            with testkit.LambdaLab(lab, tmp_path / "h", "app.handler"):
                pass
    assert testkit.docker_leftovers(lab.id) == []


def test_lambda_lab_no_socket_and_dummy_credentials(monkeypatch, tmp_path):
    require_lambda_image()
    for key, value in (("AWS_ACCESS_KEY_ID", "AKIAHOSTLEAK"), ("AWS_SECRET_ACCESS_KEY", "host-secret"), ("AWS_PROFILE", "prod"),
                       ("AWS_SESSION_TOKEN", "host-token"), ("DOCKER_HOST", "unix:///var/run/docker.sock")):
        monkeypatch.setenv(key, value)
    handler = write_handler(tmp_path / "h", LAMBDA_PROBE_HANDLER)
    with testkit.DockerLab() as lab:
        with testkit.LambdaLab(lab, handler, "app.handler", env={"APP_MODE": "test"}) as fn:
            inspect = json.loads(testkit._docker("inspect", lab.name("lambda")).stdout)[0]
            result = fn.invoke({})
        name = lab.name("lambda")
        assert testkit._docker("inspect", name).returncode != 0
    assert testkit.docker_leftovers(lab.id) == []
    mounts = inspect["Mounts"]
    assert [(m["Type"], m["Destination"], m["RW"]) for m in mounts] == [("bind", "/var/task", False)]
    assert not any("docker.sock" in (m.get("Source") or "") for m in mounts)
    host = inspect["HostConfig"]
    assert host["ReadonlyRootfs"] is True and host["CapDrop"] == ["ALL"] and host["Privileged"] is False
    assert "no-new-privileges" in host["SecurityOpt"]
    assert all(binding["HostIp"] == "127.0.0.1" for bindings in host["PortBindings"].values() for binding in bindings)
    config_env = "\n".join(inspect["Config"]["Env"])
    assert "AKIAHOSTLEAK" not in config_env and "host-secret" not in config_env and "host-token" not in config_env
    assert result["sockets"] == [] and result["writable_task"] is False and result["uid"] != 0
    assert result["credentials"][:2] == ["test", "test"] and result["region"] == "us-east-1"
    env = result["env"]
    assert "AWS_PROFILE" not in env and "DOCKER_HOST" not in env and env.get("AWS_SESSION_TOKEN", "") == ""
    assert env["AWS_CONFIG_FILE"] == env["AWS_SHARED_CREDENTIALS_FILE"] == "/dev/null"
    assert env["AWS_EC2_METADATA_DISABLED"] == "true" and env["APP_MODE"] == "test"
    assert result["metadata"] != "reachable"


def test_lambda_lab_endpoint_forced_to_localstack(monkeypatch, tmp_path):
    require_lambda_image()
    monkeypatch.setenv("AWS_ENDPOINT_URL", "https://sqs.us-east-1.amazonaws.com")
    handler = write_handler(tmp_path / "h", LAMBDA_PROBE_HANDLER)
    with pytest.raises(pytest.fail.Exception, match="AWS_ENDPOINT_URL"):
        testkit.LambdaLab(testkit.DockerLab(), handler, "app.handler", env={"AWS_ENDPOINT_URL": "https://example.com"})
    with testkit.DockerLab() as lab:
        with testkit.LambdaLab(lab, handler, "app.handler") as fn:
            gateway = testkit._docker("network", "inspect", "-f", "{{range .IPAM.Config}}{{.Gateway}}{{end}}",
                                      fn.network).stdout.strip()
            result = fn.invoke({})
            endpoint = fn.endpoint
    assert testkit.docker_leftovers(lab.id) == []
    assert int(endpoint.rsplit(":", 1)[1]) in testkit.lambda_forward_ports()
    assert endpoint.startswith(f"http://{gateway}:") and result["endpoint"] == endpoint
    assert result["env"]["AWS_ENDPOINT_URL"] == endpoint
    assert result["env"]["NO_PROXY"] == f"127.0.0.1,localhost,{gateway}"
    assert result["real_aws"] in {"ProxyConnectionError", "EndpointConnectionError", "ConnectionClosedError"}


def socket_server() -> socket.socket:
    server = socket.socket()
    server.bind(("127.0.0.1", 0))
    server.listen(4)
    return server


def test_lambda_forward_only_accepts_lab_subnet():
    target = socket_server()
    forward = testkit._Forward("127.0.0.1", "10.99.0.0/16", ("127.0.0.1", target.getsockname()[1]))
    try:
        with socket.create_connection(("127.0.0.1", forward.port), timeout=2) as client:
            client.settimeout(2)
            try:
                assert client.recv(10) == b""
            except ConnectionResetError:
                pass
        target.settimeout(0.5)
        with pytest.raises(TimeoutError):
            target.accept()
    finally:
        forward.close()
        target.close()
    with pytest.raises(OSError):
        socket.create_connection(("127.0.0.1", forward.port), timeout=2)


def test_lambda_forward_relays_both_ways():
    import threading

    server = socket_server()

    def echo():
        conn, _ = server.accept()
        with conn:
            while data := conn.recv(1024):
                conn.sendall(data.upper())

    threading.Thread(target=echo, daemon=True).start()
    forward = testkit._Forward("127.0.0.1", "127.0.0.0/8", ("127.0.0.1", server.getsockname()[1]))
    try:
        with socket.create_connection(("127.0.0.1", forward.port), timeout=2) as client:
            client.sendall(b"xin chao")
            client.shutdown(socket.SHUT_WR)
            received = b""
            while chunk := client.recv(1024):
                received += chunk
        assert received == b"XIN CHAO"
    finally:
        forward.close()
        server.close()
    assert forward.sockets == set()


def test_lambda_lab_invoke_roundtrip(tmp_path):
    require_lambda_image()
    testkit.Exercise.require_localstack_devops("sqs")
    handler = write_handler(tmp_path / "h", LAMBDA_SQS_HANDLER, "boto3\n")
    with testkit.DockerLab() as lab:
        queue = f"{lab.network}-orders"
        sqs = testkit.localstack_client("sqs")
        try:
            url = sqs.create_queue(QueueName=queue)["QueueUrl"]
            for order in ("o-1", "o-2"):
                sqs.send_message(QueueUrl=url, MessageBody=json.dumps({"order_id": order}))
            with testkit.LambdaLab(lab, handler, "app.handler", env={"QUEUE_NAME": queue}, timeout=3) as fn:
                first = fn.invoke({})
                event = {"Records": [{"messageId": "m1", "body": json.dumps({"order_id": "o-3"}), "eventSource": "aws:sqs"}]}
                from_event = fn.invoke(event)
                failed = fn.invoke({"boom": True})
                timed_out = fn.invoke({"sleep": 10})
                after_timeout = fn.invoke({})
                logs = fn.logs()
            attributes = sqs.get_queue_attributes(QueueUrl=url, AttributeNames=["ApproximateNumberOfMessages"])["Attributes"]
        finally:
            swept = testkit.localstack_sweep(lab.network)
    assert testkit.docker_leftovers(lab.id) == []
    assert sorted(first["orders"]) == ["o-1", "o-2"] and 0 < first["remaining_ms"] <= 3000
    assert from_event == {"orders": ["o-3"]}
    assert failed["errorType"] == "ValueError" and failed["errorMessage"] == "hỏng"
    assert "Task timed out after 3" in timed_out["errorMessage"]
    assert after_timeout["orders"] == []
    assert attributes["ApproximateNumberOfMessages"] == "0"
    assert "START RequestId" in logs and "REPORT RequestId" in logs
    assert swept == [f"sqs:{queue}"]


def test_localstack_devops_no_docker_socket():
    import yaml

    data = yaml.safe_load((testkit.ROOT / "setup" / "docker-compose.yml").read_text(encoding="utf-8"))
    devops = data["services"]["localstack-devops"]
    services = devops["environment"]["SERVICES"].split(",")
    assert {"sqs", "dynamodb", "events", "apigateway", "secretsmanager"} <= set(services)
    assert "lambda" not in services and "ecs" not in services
    assert not [v for v in devops.get("volumes", []) if "docker.sock" in str(v) or "/var/run" in str(v)]
    assert not [k for k in devops["environment"] if k.startswith(("LAMBDA_", "DOCKER_"))]
    assert "privileged" not in devops and "network_mode" not in devops
    for name, service in data["services"].items():
        assert not [v for v in service.get("volumes", []) if "docker.sock" in str(v)], name


def test_require_localstack_devops_skips_when_service_missing(monkeypatch):
    monkeypatch.setattr(testkit, "service_up", lambda name, timeout=0.5: True)
    health = {"services": {s: "available" for s in ("s3", "iam", "sts", "dynamodb")} | {"sqs": "disabled"}}
    monkeypatch.setattr(testkit, "_localstack_health", lambda endpoint: health)
    monkeypatch.delenv("LOCALSTACK_DEVOPS_PORT", raising=False)
    monkeypatch.delenv("LOCALSTACK_PORT", raising=False)
    assert testkit.Exercise.require_localstack_devops() == "http://127.0.0.1:14566"
    with pytest.raises(pytest.skip.Exception, match="chưa bật sqs, events") as info:
        testkit.Exercise.require_localstack_devops("sqs", "events")
    assert testkit.LOCALSTACK_DEVOPS_RECREATE in str(info.value) and "rm -s -f localstack-devops" in str(info.value)


def test_localstack_sweep_serverless_resources():
    if not testkit.service_up("localstack-devops"):
        pytest.skip(f"Cần localstack-devops: {testkit.LOCALSTACK_DEVOPS_START}")
    testkit.Exercise.require_localstack_devops("sqs", "events", "apigateway")
    prefix = f"devops-ex-{os.urandom(4).hex()}"
    keep = f"devops-ex-{os.urandom(4).hex()}"
    sqs, events = testkit.localstack_client("sqs"), testkit.localstack_client("events")
    apigateway = testkit.localstack_client("apigateway")
    keep_url = sqs.create_queue(QueueName=f"{keep}-q")["QueueUrl"]
    try:
        url = sqs.create_queue(QueueName=f"{prefix}-orders")["QueueUrl"]
        sqs.create_queue(QueueName=f"{prefix}-orders.fifo", Attributes={"FifoQueue": "true"})
        arn = sqs.get_queue_attributes(QueueUrl=url, AttributeNames=["QueueArn"])["Attributes"]["QueueArn"]
        events.create_event_bus(Name=f"{prefix}-bus")
        events.put_rule(Name="placed", EventBusName=f"{prefix}-bus", EventPattern='{"source": ["olist.shop"]}')
        events.put_targets(Rule="placed", EventBusName=f"{prefix}-bus", Targets=[{"Id": "q", "Arn": arn}])
        events.put_rule(Name=f"{prefix}-nightly", ScheduleExpression="rate(1 day)")
        events.put_targets(Rule=f"{prefix}-nightly", Targets=[{"Id": "q", "Arn": arn}])
        apigateway.create_rest_api(name=f"{prefix}-api")
        removed = testkit.localstack_sweep(prefix)
        assert sorted(removed) == sorted([
            f"sqs:{prefix}-orders", f"sqs:{prefix}-orders.fifo", f"events-rule:{prefix}-bus/placed", f"events-bus:{prefix}-bus",
            f"events-rule:default/{prefix}-nightly", f"apigateway:{prefix}-api"])
        assert not [u for u in sqs.list_queues().get("QueueUrls", []) if prefix in u]
        assert not [b for b in events.list_event_buses()["EventBuses"] if b["Name"].startswith(prefix)]
        assert not [r for r in events.list_rules()["Rules"] if r["Name"].startswith(prefix)]
        assert not [a for a in apigateway.get_rest_apis()["items"] if a["name"].startswith(prefix)]
        assert keep_url in sqs.list_queues(QueueNamePrefix=keep).get("QueueUrls", [])
    finally:
        sqs.delete_queue(QueueUrl=keep_url)
        testkit.localstack_sweep(prefix)


def test_lambda_lab_enter_twice_refused(monkeypatch, tmp_path):
    fn = testkit.LambdaLab(testkit.DockerLab(), write_handler(tmp_path, "def handler(e, c):\n    return {}\n"), "app.handler")
    monkeypatch.setattr(fn, "_start", lambda: None)
    monkeypatch.setattr(testkit, "_docker", lambda *a, **k: subprocess.CompletedProcess(a, 0, "", ""))
    with fn:
        with pytest.raises(RuntimeError, match="một lần"):
            fn.__enter__()
    with pytest.raises(RuntimeError, match="một lần"):
        with fn:
            pass


@pytest.mark.parametrize("config,expected", [
    ([{"Subnet": "fd00:1::/64", "Gateway": "fd00:1::1"}, {"Subnet": "172.30.0.0/16", "Gateway": "172.30.0.1"}],
     ("172.30.0.1", "172.30.0.0/16")),
    ([{"Subnet": "172.31.0.0/16", "Gateway": ""}, {"Subnet": "172.30.0.0/16", "Gateway": "172.30.0.1"}],
     ("172.30.0.1", "172.30.0.0/16")),
    ([{"Subnet": "172.31.0.0/16"}], None),
    ([{"Subnet": "fd00:1::/64", "Gateway": "fd00:1::1"}], None),
    ([{"Subnet": "bad", "Gateway": "x"}, None], None),
    (None, None),
])
def test_lambda_ipv4_gateway(config, expected):
    assert testkit._ipv4_gateway(config) == expected


def test_lambda_lab_gateway_parses_ipam_json(monkeypatch, tmp_path):
    config = [{"Subnet": "fd00:1::/64", "Gateway": "fd00:1::1"}, {"Subnet": "172.30.0.0/16", "Gateway": "172.30.0.1"}]
    calls = []

    def fake(*args, **kwargs):
        calls.append(args)
        return subprocess.CompletedProcess(args, 0, json.dumps(config), "")

    monkeypatch.setattr(testkit, "_docker", fake)
    fn = testkit.LambdaLab(testkit.DockerLab(), tmp_path, "app.handler")
    assert fn._gateway() == ("172.30.0.1", "172.30.0.0/16")
    assert calls[0][-1] == fn.network and "{{json .IPAM.Config}}" in calls[0]
    config = [{"Subnet": "fd00:1::/64", "Gateway": "fd00:1::1"}]
    with pytest.raises(pytest.fail.Exception, match="IPv4"):
        fn._gateway()


@pytest.mark.parametrize("value,expected", [(None, range(47100, 47200)), ("50000-50009", range(50000, 50010)), ("6000-6000", range(6000, 6001))])
def test_lambda_forward_ports(monkeypatch, value, expected):
    if value is None:
        monkeypatch.delenv("DEVOPS_LAMBDA_FORWARD_PORTS", raising=False)
    else:
        monkeypatch.setenv("DEVOPS_LAMBDA_FORWARD_PORTS", value)
    assert testkit.lambda_forward_ports() == expected


@pytest.mark.parametrize("value", ["80-90", "50010-50000", "abc", "50000", "60000-70000"])
def test_lambda_forward_ports_invalid(monkeypatch, value):
    monkeypatch.setenv("DEVOPS_LAMBDA_FORWARD_PORTS", value)
    with pytest.raises(ValueError):
        testkit.lambda_forward_ports()


def test_lambda_forward_binds_inside_range():
    taken = socket.socket()
    taken.bind(("127.0.0.1", 0))
    taken.listen(1)
    port = taken.getsockname()[1]
    with pytest.raises(OSError, match="DEVOPS_LAMBDA_FORWARD_PORTS"):
        testkit._Forward("127.0.0.1", "127.0.0.0/8", ("127.0.0.1", 9), ports=range(port, port + 1))
    taken.close()
    forward = testkit._Forward("127.0.0.1", "127.0.0.0/8", ("127.0.0.1", 9), ports=range(port, port + 1))
    try:
        assert forward.port == port
    finally:
        forward.close()


def test_lambda_forward_caps_connections():
    import threading

    server = socket_server()
    accepted = []

    def hold():
        while True:
            try:
                accepted.append(server.accept()[0])
            except OSError:
                return

    threading.Thread(target=hold, daemon=True).start()
    forward = testkit._Forward("127.0.0.1", "127.0.0.0/8", ("127.0.0.1", server.getsockname()[1]), ports=range(0, 1), limit=2)
    clients = []
    try:
        for _ in range(3):
            clients.append(socket.create_connection(("127.0.0.1", forward.port), timeout=2))
        clients[2].settimeout(2)
        try:
            assert clients[2].recv(10) == b""
        except ConnectionResetError:
            pass
        deadline = time.monotonic() + 5
        while len(forward.sockets) < 4 and time.monotonic() < deadline:
            time.sleep(0.05)
        assert len(forward.sockets) == 4 and len(accepted) == 2
        clients[0].close()
        accepted[0].close()
        deadline = time.monotonic() + 5
        while len(forward.sockets) > 2 and time.monotonic() < deadline:
            time.sleep(0.05)
        clients.append(socket.create_connection(("127.0.0.1", forward.port), timeout=2))
        deadline = time.monotonic() + 5
        while len(accepted) < 3 and time.monotonic() < deadline:
            time.sleep(0.05)
        assert len(accepted) == 3
    finally:
        for sock in clients + accepted:
            sock.close()
        forward.close()
        server.close()


LAMBDA_NET_HANDLER = '''import socket


def handler(event, context):
    result = {}
    for name, host, port in event["targets"]:
        try:
            socket.create_connection((host, port), timeout=3).close()
            result[name] = "ok"
        except OSError as error:
            result[name] = type(error).__name__
    return result
'''


def test_lambda_lab_isolated_network(tmp_path):
    require_lambda_image()
    peer_image = require_real_docker()
    handler = write_handler(tmp_path / "h", LAMBDA_NET_HANDLER)
    with testkit.DockerLab() as lab:
        lab.start("peer", peer_image, "python", "-u", "-m", "http.server", "8000")
        targets = {"targets": [["peer", "peer", 8000], ["internet", "1.1.1.1", 443]]}
        with testkit.LambdaLab(lab, handler, "app.handler") as fn:
            network = fn.network
            internal = testkit._docker("network", "inspect", "-f", "{{.Internal}}", network).stdout.strip()
            isolated = fn.invoke(targets)
        assert testkit._docker("network", "inspect", network).returncode != 0
        lab.wait_log("peer", "Serving HTTP", timeout=30)
        with testkit.LambdaLab(lab, handler, "app.handler", alias="shared", isolated=False) as shared:
            assert shared.network == lab.network
            reached = shared.invoke({"targets": [["peer", "peer", 8000]]})
    assert testkit.docker_leftovers(lab.id) == []
    assert internal == "true" and network == f"{lab.network}-lambda-net"
    assert isolated["peer"] != "ok" and isolated["internet"] != "ok"
    assert reached == {"peer": "ok"}


def test_lambda_firewall_docs_are_port_scoped():
    text = (testkit.ROOT / "setup" / "DEVOPS-TOOLS.md").read_text(encoding="utf-8")
    section = text[text.index("## Lambda local: LambdaLab"):text.index("## Dịch vụ phụ trợ: Vault dev")]
    first, last = testkit.LAMBDA_FORWARD_PORTS.split("-")
    rules = [line for line in section.splitlines() if line.startswith("sudo ")]
    assert f"sudo ufw allow proto tcp from 172.16.0.0/12 to any port {first}:{last}" in rules
    assert f"sudo ufw delete allow proto tcp from 172.16.0.0/12 to any port {first}:{last}" in rules
    assert all(f"{first}" in rule and "tcp" in rule for rule in rules)
    assert "DEVOPS_LAMBDA_FORWARD_PORTS" in section and "Xoá luật" in section and "bỏ qua các bài này" in section
    assert "SSRF" in text and "SSRF" in (testkit.ROOT / "CONTENT_SPEC.md").read_text(encoding="utf-8")


def test_localstack_sweep_paginates_event_buses(monkeypatch):
    import boto3

    deleted = []
    pages = {None: {"EventBuses": [{"Name": "default"}], "NextToken": "t1"},
             "t1": {"EventBuses": [{"Name": "devops-ex-abc12345-bus"}, {"Name": "other-bus"}]}}

    class Fake:
        def __init__(self, service):
            self.service = service

        def get_paginator(self, name):
            return self

        def paginate(self, **kwargs):
            return []

        def list_buckets(self, **kwargs):
            return {"Buckets": []}

        def list_event_buses(self, **kwargs):
            return pages[kwargs.get("NextToken")]

        def delete_event_bus(self, Name):
            deleted.append(Name)

    monkeypatch.setattr(boto3, "client", lambda service, **kwargs: Fake(service))
    assert testkit.localstack_sweep("devops-ex-abc12345") == ["events-bus:devops-ex-abc12345-bus"]
    assert deleted == ["devops-ex-abc12345-bus"]


LINKERD_RESOURCES = "".join(f"{r}.policy.linkerd.io\n" for r in (
    "authorizationpolicies", "egressnetworks", "httplocalratelimitpolicies", "httproutes", "meshtlsauthentications",
    "networkauthentications", "serverauthorizations", "servers"))
def pem_cert(days: float, name: str = "root.linkerd.cluster.local") -> str:
    import datetime

    from cryptography import x509
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import ec
    from cryptography.x509.oid import NameOID

    key = ec.generate_private_key(ec.SECP256R1())
    subject = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, name)])
    now = datetime.datetime.now(datetime.timezone.utc)
    cert = (x509.CertificateBuilder().subject_name(subject).issuer_name(subject).public_key(key.public_key())
            .serial_number(x509.random_serial_number()).not_valid_before(now - datetime.timedelta(days=400))
            .not_valid_after(now + datetime.timedelta(days=days)).sign(key, hashes.SHA256()))
    return cert.public_bytes(serialization.Encoding.PEM).decode()


LINKERD_TRUST_ROOT = pem_cert(3650)
LINKERD_OK = {
    "crd servers.policy.linkerd.io": (0, "customresourcedefinition.apiextensions.k8s.io/servers.policy.linkerd.io\n"),
    "configmap linkerd-config": (0, "clusterDomain: cluster.local\ncniEnabled: true\ndisableHeartBeat: true\n"),
    "daemonset linkerd-cni": (0, "3 3"),
    "configmap linkerd-identity-trust-roots": (0, LINKERD_TRUST_ROOT),
    "mutatingwebhookconfiguration linkerd-proxy-injector-webhook-config": (0, "LS0tLS1CRUdJTiBDRVJUSUZJQ0FURS0tLS0t"),
    "deployment linkerd-identity": (0, "1"),
    "deployment linkerd-destination": (0, "1"),
    "deployment linkerd-proxy-injector": (0, "1"),
    "configmap devops-linkerd-issuer-public": (0, pem_cert(3650, "identity.linkerd.cluster.local")),
}


class LinkerdFake(KubeFake):
    """KubeFake cộng Linkerd: CRD policy.linkerd.io, các kiểm của `linkerd_problem`, và endpoint admin của proxy qua
    `get --raw` (trả `raw[đường dẫn]`)."""

    def __init__(self, monkeypatch, *, answers=None, objects=None, raw=None):
        self.answers = dict(LINKERD_OK if answers is None else answers)
        self.objects = objects or {}
        self.raw = raw or {}
        super().__init__(monkeypatch)

    def run_sandboxed(self, cmd, *, writable, cwd, env, timeout=30, input=None, readonly=()):
        joined = " ".join(map(str, cmd))
        answer = None
        if "api-resources --api-group=policy.linkerd.io" in joined:
            answer = (0, LINKERD_RESOURCES)
        elif "get --raw /api/" in joined:
            path = cmd[cmd.index("--raw") + 1]
            answer = (0, self.raw[path]) if path in self.raw else (1, "")
        else:
            answer = next((v for k, v in {**self.answers, **self.objects}.items() if k in joined), None)
        if answer is None:
            return super().run_sandboxed(cmd, writable=writable, cwd=cwd, env=env, timeout=timeout, input=input, readonly=readonly)
        cmd = [str(part) for part in cmd]
        self.sandbox_calls.append({"cmd": cmd, "env": dict(env), "writable": list(writable), "readonly": list(readonly),
                                   "cwd": cwd, "input": input})
        return subprocess.CompletedProcess(cmd, answer[0], answer[1], "" if answer[0] == 0 else "NotFound")


def namespace_item(fake) -> dict:
    return next(i for i in bootstrap_items(fake) if i["kind"] == "Namespace")


def test_kube_lab_mesh_annotation(monkeypatch):
    fake = LinkerdFake(monkeypatch)
    with testkit.KubeLab(mesh=True) as lab:
        assert lab.mesh is True
    assert namespace_item(fake)["metadata"]["annotations"] == {"linkerd.io/inject": "enabled"}
    probes = [json.loads(c["input"]) for c in fake.calls_with("--dry-run=server")]
    [probe] = [p for p in probes if p["kind"] == "MeshTLSAuthentication"]
    assert probe["metadata"]["name"] == f"{lab.namespace}-probe-mesh" and probe["spec"] == {"identities": ["*"]}
    plain = LinkerdFake(monkeypatch)
    with testkit.KubeLab():
        pass
    assert "annotations" not in namespace_item(plain)["metadata"]


def test_kube_lab_mesh_skips_without_linkerd(monkeypatch):
    fake = KubeFake(monkeypatch)
    with pytest.raises(pytest.skip.Exception) as info:
        with testkit.KubeLab(mesh=True):
            pass
    assert_skip(info, "chưa có Linkerd", "apply --server-side -k setup/kind/linkerd", "certs.sh")
    assert not fake.calls_with("apply", "-f", "-")
    with testkit.KubeLab() as lab:
        pass
    assert not any(json.loads(c["input"])["kind"] == "MeshTLSAuthentication" for c in fake.calls_with("--dry-run=server"))
    assert any(i["metadata"]["name"] == f"{lab.namespace}-mesh" for i in bootstrap_items(fake))


def test_kube_lab_role_writes_linkerd_policy_in_lab_only(monkeypatch):
    fake = LinkerdFake(monkeypatch)
    with testkit.KubeLab():
        pass
    role = next(i for i in bootstrap_items(fake) if i["kind"] == "Role")
    linkerd = [r for r in role["rules"] if any("linkerd" in g for g in r["apiGroups"])]
    assert linkerd == [{"apiGroups": ["policy.linkerd.io"],
                        "resources": ["servers", "authorizationpolicies", "httproutes", "meshtlsauthentications"],
                        "verbs": testkit._KUBE_RW}]
    cluster_roles = [i for i in bootstrap_items(fake) if i["kind"] == "ClusterRole"]
    assert not any("linkerd" in json.dumps(c["rules"]) for c in cluster_roles)
    assert "policy.linkerd.io" not in testkit._KUBE_HOOK_KINDS
    assert "linkerd" in testkit.KUBE_SHARED_NAMESPACES


MESH_NS = "devops-ex-abc12345"


def mesh_identity(sa: str, ns: str = MESH_NS) -> str:
    return f"{sa}.{ns}.serviceaccount.identity.linkerd.cluster.local"


def mesh_doc(kind: str, spec: dict, version: str = "v1alpha1") -> dict:
    return {"apiVersion": f"policy.linkerd.io/{version}", "kind": kind, "metadata": {"name": "x"}, "spec": spec}


FOREIGN_MESH = {
    "authz-target-namespace-other": mesh_doc("AuthorizationPolicy", {
        "targetRef": {"kind": "Namespace", "name": "devops-ex-other"},
        "requiredAuthenticationRefs": [{"kind": "ServiceAccount", "name": "api"}]}),
    "authz-target-ns-field": mesh_doc("AuthorizationPolicy", {"targetRef": {"group": "policy.linkerd.io", "kind": "Server",
                                                                            "name": "web", "namespace": "linkerd"}}),
    "authz-auth-ref-other": mesh_doc("AuthorizationPolicy", {
        "targetRef": {"group": "policy.linkerd.io", "kind": "Server", "name": "web"},
        "requiredAuthenticationRefs": [{"group": "policy.linkerd.io", "kind": "MeshTLSAuthentication", "name": "a",
                                        "namespace": "devops-ex-other"}]}),
    "authz-sa-ref-other": mesh_doc("AuthorizationPolicy", {
        "targetRef": {"group": "policy.linkerd.io", "kind": "Server", "name": "web"},
        "requiredAuthenticationRefs": [{"kind": "ServiceAccount", "name": "api", "namespace": "kube-system"}]}),
    "mtls-star": mesh_doc("MeshTLSAuthentication", {"identities": ["*"]}),
    "mtls-other-ns": mesh_doc("MeshTLSAuthentication", {"identities": [mesh_identity("api", "devops-ex-other")]}),
    "mtls-control-plane": mesh_doc("MeshTLSAuthentication", {"identities": [mesh_identity("linkerd-destination", "linkerd")]}),
    "mtls-suffix-trick": mesh_doc("MeshTLSAuthentication", {"identities": [f"a.b.{MESH_NS}.serviceaccount.identity.linkerd.cluster.local"]}),
    "mtls-star-suffix": mesh_doc("MeshTLSAuthentication", {"identities": ["*.cluster.local"]}),
    "mtls-ref-other-sa": mesh_doc("MeshTLSAuthentication", {"identityRefs": [{"kind": "ServiceAccount", "name": "api",
                                                                             "namespace": "devops-ex-other"}]}),
    "mtls-ref-other-namespace": mesh_doc("MeshTLSAuthentication", {"identityRefs": [{"kind": "Namespace", "name": "linkerd"}]}),
    "mtls-ref-star": mesh_doc("MeshTLSAuthentication", {"identityRefs": [{"kind": "ServiceAccount", "name": "*"}]}),
    "route-parent-other": mesh_doc("HTTPRoute", {"parentRefs": [{"group": "policy.linkerd.io", "kind": "Server", "name": "web",
                                                                 "namespace": "devops-ex-other"}]}, "v1beta3"),
    "route-backend-other": mesh_doc("HTTPRoute", {"parentRefs": [{"group": "core", "kind": "Service", "name": "web", "port": 80}],
                                                  "rules": [{"backendRefs": [{"name": "web", "port": 80,
                                                                              "namespace": "devops-ex-other"}]}]}, "v1beta3"),
}


@pytest.mark.parametrize("case", sorted(FOREIGN_MESH))
def test_linkerd_policy_foreign_namespace_refused(case):
    problems = testkit.kube_manifest_problems([FOREIGN_MESH[case]], lab_id="abc12345", namespace=MESH_NS)
    assert problems and all(p.startswith(f"{FOREIGN_MESH[case]['kind']} x:") for p in problems), problems


def test_linkerd_policy_inside_lab_allowed():
    docs = [
        mesh_doc("Server", {"podSelector": {"matchLabels": {"app": "web"}}, "port": "http", "proxyProtocol": "HTTP/1"}, "v1beta3"),
        mesh_doc("MeshTLSAuthentication", {"identities": [mesh_identity("api"), f"*.{MESH_NS}.serviceaccount.identity.linkerd.cluster.local"]}),
        mesh_doc("MeshTLSAuthentication", {"identityRefs": [{"kind": "ServiceAccount", "name": "api"},
                                                            {"kind": "ServiceAccount", "name": "worker", "namespace": MESH_NS},
                                                            {"kind": "Namespace", "name": MESH_NS}]}),
        mesh_doc("AuthorizationPolicy", {"targetRef": {"group": "policy.linkerd.io", "kind": "Server", "name": "web"},
                                         "requiredAuthenticationRefs": [{"group": "policy.linkerd.io", "kind": "MeshTLSAuthentication",
                                                                         "name": "api-only"}]}),
        mesh_doc("AuthorizationPolicy", {"targetRef": {"kind": "Namespace", "name": MESH_NS},
                                         "requiredAuthenticationRefs": [{"kind": "ServiceAccount", "name": "api",
                                                                         "namespace": MESH_NS}]}),
        {**mesh_doc("HTTPRoute", {"parentRefs": [{"group": "core", "kind": "Service", "name": "web", "port": 80}],
                                  "rules": [{"timeouts": {"request": "2s"}, "backendRefs": [{"name": "web", "port": 80}]}]}, "v1beta3"),
         "metadata": {"name": "web", "annotations": {"retry.linkerd.io/http": "5xx"}}},
    ]
    assert testkit.kube_manifest_problems(docs, lab_id="abc12345", namespace=MESH_NS) == []


def test_linkerd_policy_vap_in_bootstrap(monkeypatch):
    fake = LinkerdFake(monkeypatch)
    with testkit.KubeLab() as lab:
        pass
    policy = next(i for i in bootstrap_items(fake) if i["kind"] == "ValidatingAdmissionPolicy"
                  and i["metadata"]["name"] == f"{lab.namespace}-mesh")
    spec = policy["spec"]
    assert spec["failurePolicy"] == "Fail"
    assert spec["matchConstraints"]["resourceRules"] == [{
        "apiGroups": ["policy.linkerd.io"], "apiVersions": ["*"],
        "resources": ["authorizationpolicies", "meshtlsauthentications", "httproutes"], "operations": ["CREATE", "UPDATE"]}]
    assert f"'system:serviceaccounts:{lab.namespace}' in request.userInfo.groups" in spec["matchConditions"][0]["expression"]
    text = json.dumps(spec["validations"])
    for needle in ("object.spec.targetRef", "requiredAuthenticationRefs.all", "identityRefs.all", "parentRefs.all",
                   "backendRefs.all", f"{lab.namespace}\\\\\\\\.serviceaccount\\\\\\\\.identity\\\\\\\\.linkerd\\\\\\\\.cluster\\\\\\\\.local$",
                   "lowerAscii() != 'namespace'", "r.name != '*'"):
        assert needle in text, needle
    binding = next(i for i in bootstrap_items(fake) if i["kind"] == "ValidatingAdmissionPolicyBinding"
                   and i["metadata"]["name"] == f"{lab.namespace}-mesh")
    assert binding["spec"]["validationActions"] == ["Deny"]


@pytest.mark.parametrize("identity,ok", [
    (mesh_identity("api"), True), (f"*.{MESH_NS}.serviceaccount.identity.linkerd.cluster.local", True),
    ("*", False), (mesh_identity("api", "devops-ex-other"), False), (f"a.b.{MESH_NS}.serviceaccount.identity.linkerd.cluster.local", False),
    (f"api.{MESH_NS}.serviceaccount.identity.linkerd.example.org", False), (None, False), ("", False),
])
def test_kube_mesh_identity_ok(identity, ok):
    assert testkit.kube_mesh_identity_ok(identity, MESH_NS) is ok


def linkerd_fake(monkeypatch, answers):
    fake = KubeFake(monkeypatch)
    calls = []

    def run(cmd, **kwargs):
        joined = " ".join(map(str, cmd))
        calls.append(joined)
        for key, (code, out) in answers.items():
            if key in joined:
                return subprocess.CompletedProcess(cmd, code, out, "" if code == 0 else "NotFound")
        return fake.run_sandboxed(cmd, **kwargs)

    monkeypatch.setattr(testkit, "run_sandboxed", run)
    return calls


def test_require_linkerd_ok_never_reads_secrets(monkeypatch):
    calls = linkerd_fake(monkeypatch, LINKERD_OK)
    testkit.Exercise.require_linkerd()
    assert len([c for c in calls if c.startswith("kubectl")]) == len(LINKERD_OK) + 1
    assert not any(" secret" in c or "secrets" in c for c in calls), calls


@pytest.mark.parametrize("broken,answer,needle", [
    ("configmap linkerd-identity-trust-roots", (0, pem_cert(-1)), "trust anchor"),
    ("configmap linkerd-identity-trust-roots", (0, pem_cert(3)), "sắp hết hạn"),
    ("configmap devops-linkerd-issuer-public", (0, pem_cert(-2, "identity.linkerd.cluster.local")), "issuer"),
    ("configmap devops-linkerd-issuer-public", (0, "-----BEGIN CERTIFICATE-----\nrác\n-----END CERTIFICATE-----\n"),
     "không đọc được"),
])
def test_require_linkerd_checks_certificate_expiry(monkeypatch, broken, answer, needle):
    answers = dict(LINKERD_OK)
    answers[broken] = answer
    linkerd_fake(monkeypatch, answers)
    with pytest.raises(pytest.skip.Exception) as info:
        testkit.Exercise.require_linkerd()
    assert_skip(info, needle, "certs.sh")


def test_require_linkerd_without_issuer_public_configmap_still_ok(monkeypatch):
    answers = dict(LINKERD_OK)
    answers["configmap devops-linkerd-issuer-public"] = (0, "")
    linkerd_fake(monkeypatch, answers)
    testkit.Exercise.require_linkerd()


@pytest.mark.parametrize("broken,answer,needle", [
    ("crd servers.policy.linkerd.io", (1, ""), "CRD servers.policy.linkerd.io"),
    ("configmap linkerd-config", (0, "cniEnabled: false\n"), "cniEnabled"),
    ("configmap linkerd-config", (1, ""), "cniEnabled"),
    ("daemonset linkerd-cni", (0, "2 3"), "linkerd-cni"),
    ("daemonset linkerd-cni", (0, "0 0"), "linkerd-cni"),
    ("configmap linkerd-identity-trust-roots", (1, ""), "linkerd-identity-trust-roots"),
    ("mutatingwebhookconfiguration linkerd-proxy-injector-webhook-config",
     (0, base64.b64encode(b"devops-linkerd-certs-sh").decode()), "caBundle"),
    ("mutatingwebhookconfiguration linkerd-proxy-injector-webhook-config", (0, ""), "caBundle"),
    ("deployment linkerd-identity", (0, "0"), "linkerd/linkerd-identity"),
    ("deployment linkerd-destination", (0, ""), "linkerd/linkerd-destination"),
    ("deployment linkerd-proxy-injector", (1, ""), "linkerd/linkerd-proxy-injector"),
])
def test_require_linkerd_messages(monkeypatch, broken, answer, needle):
    answers = dict(LINKERD_OK)
    answers[broken] = answer
    linkerd_fake(monkeypatch, answers)
    with pytest.raises(pytest.skip.Exception) as info:
        testkit.Exercise.require_linkerd()
    assert_skip(info, needle, "kubectl --kubeconfig ~/.kube/devops-lab.yaml apply --server-side -k setup/kind/linkerd",
                "bash setup/kind/linkerd/certs.sh", "image-archive", "SHA256SUMS", "Gateway API CRD")


def test_require_linkerd_needs_cluster_first(monkeypatch):
    KubeFake(monkeypatch, clusters="\n")
    with pytest.raises(pytest.skip.Exception) as info:
        testkit.Exercise.require_linkerd()
    assert_skip(info, "Chưa có cluster kind devops-lab")


WEB_METRICS = """# HELP response_total Total count of HTTP responses.
# TYPE response_total counter
control_identity_cert_expiration_timestamp_seconds 1794439715.0
response_total{direction="inbound",target_addr="10.244.2.6:80",target_ip="10.244.2.6",target_port="80",tls="true",client_id="api.NS.serviceaccount.identity.linkerd.cluster.local",srv_kind="server",srv_name="web-http",status_code="200",classification="success",grpc_status="",error=""} 5
response_total{direction="inbound",target_addr="10.244.2.6:80",target_ip="10.244.2.6",target_port="80",tls="true",client_id="api.NS.serviceaccount.identity.linkerd.cluster.local",srv_kind="server",srv_name="web-http",status_code="503",classification="failure",grpc_status="",error=""} 2
response_total{direction="inbound",target_addr="0.0.0.0:4191",target_ip="0.0.0.0",target_port="4191",tls="no_identity",no_tls_reason="no_tls_from_remote",status_code="200",classification="success",grpc_status="",error=""} 40
request_total{direction="inbound",target_addr="10.244.2.6:80",target_ip="10.244.2.6",target_port="80",tls="no_identity",no_tls_reason="no_tls_from_remote",srv_kind="default"} 1
request_total{direction="inbound",target_addr="0.0.0.0:4191",target_ip="0.0.0.0",target_port="4191",tls="no_identity",no_tls_reason="no_tls_from_remote"} 40
inbound_http_authz_deny_total{target_port="80",srv_group="policy.linkerd.io",srv_kind="server",srv_name="web-http",srv_port="80",tls="true",client_id="intruder.NS.serviceaccount.identity.linkerd.cluster.local"} 3
"""
API_METRICS = """control_identity_cert_expiration_timestamp_seconds 1794439715.0
response_total{direction="outbound",authority="web.NS.svc.cluster.local",target_port="80",tls="true",server_id="web.NS.serviceaccount.identity.linkerd.cluster.local",status_code="200",classification="success",grpc_status="",error=""} 5
outbound_http_route_request_statuses_total{parent_kind="Service",parent_name="web",route_name="web-retry",hostname="",http_status="200",error=""} 6
outbound_http_route_request_statuses_total{parent_kind="Service",parent_name="web",route_name="web-retry",hostname="",http_status="503",error=""} 1
outbound_http_route_request_statuses_total{parent_kind="Service",parent_name="web",route_name="web-retry",hostname="",http_status="",error="TIMEOUT"} 2
outbound_http_route_retry_requests_total{parent_kind="Service",route_name="web-retry",hostname=""} 4
"""


def mesh_pod(name: str, sa: str, *, proxy=True, phase="Running", image=testkit.KUBE_LINKERD_PROXY_IMAGE,
             version=testkit.KUBE_LINKERD_VERSION) -> dict:
    sidecars = [{"name": "linkerd-network-validator", "image": testkit.KUBE_LINKERD_PROXY_IMAGE}] + (
        [{"name": "linkerd-proxy", "image": image, "restartPolicy": "Always"}] if proxy else [])
    annotations = {"linkerd.io/proxy-version": version} if version else {}
    return {"metadata": {"name": name, "annotations": annotations},
            "spec": {"serviceAccountName": sa, "initContainers": sidecars, "containers": [{"name": "app", "image": "nginx"}]},
            "status": {"phase": phase}}


def mesh_lab_fake(monkeypatch, pods, metrics, ns_holder, identities=None):
    fake = LinkerdFake(monkeypatch)
    original = fake.run_sandboxed

    def run(cmd, **kwargs):
        cmd = [str(c) for c in cmd]
        ns = ns_holder.get("ns", "")
        joined = " ".join(cmd)
        if "/pods/" in joined:
            fake.sandbox_calls.append({"cmd": cmd, "env": dict(kwargs["env"]), "input": None})
        if "get deployment web -o json" in joined:
            return subprocess.CompletedProcess(cmd, 0, json.dumps({"spec": {"selector": {"matchLabels": {"app": "web"}}}}), "")
        if "get pods -l app=web -o json" in joined or "get pods web-0 -o json" in joined:
            body = {"kind": "List", "items": pods} if "-l" in cmd else pods[0]
            return subprocess.CompletedProcess(cmd, 0, json.dumps(body), "")
        if "--raw" in cmd and "/pods/" in cmd[cmd.index("--raw") + 1]:
            path = cmd[cmd.index("--raw") + 1]
            pod = path.split("/pods/")[1].split(":")[0]
            if path.endswith("/env.json"):
                sa = next(p["spec"].get("serviceAccountName") for p in pods if p["metadata"]["name"] == pod)
                local = (identities or {}).get(pod, mesh_identity(sa, ns)).replace("NS", ns)
                return subprocess.CompletedProcess(cmd, 0, json.dumps({"LINKERD2_PROXY_IDENTITY_LOCAL_NAME": local}), "")
            return subprocess.CompletedProcess(cmd, 0, metrics.get(pod, "").replace("NS", ns), "")
        return original(cmd, **kwargs)

    monkeypatch.setattr(testkit, "run_sandboxed", run)
    return fake


def test_mesh_status_reads_identity_and_counts(monkeypatch):
    holder = {}
    pods = [mesh_pod("web-1", "web"), mesh_pod("web-2", "web"), mesh_pod("web-3", "web", phase="Pending")]
    fake = mesh_lab_fake(monkeypatch, pods, {"web-1": WEB_METRICS, "web-2": WEB_METRICS + API_METRICS}, holder)
    with testkit.KubeLab(mesh=True) as lab:
        holder["ns"] = lab.namespace
        status = lab.mesh_status("web")
        assert status["workload"] == "deployment/web" and status["pods"] == ["web-1", "web-2"]
        assert status["injected"] and status["mtls"]
        assert status["identity"] == mesh_identity("web", lab.namespace)
        assert (status["success"], status["failure"], status["denied"], status["plaintext"]) == (10, 4, 6, 2)
        assert status["clients"] == [mesh_identity("api", lab.namespace)]
        assert (status["outbound_success"], status["outbound_failure"], status["retries"]) == (6, 3, 4)
        assert status["servers"] == [mesh_identity("web", lab.namespace)]
        raws = [c for c in fake.sandbox_calls if "--raw" in c["cmd"] and "/readyz" not in c["cmd"]]
        assert raws and all(c["env"]["KUBECONFIG"] == str(lab.admin_kubeconfig) for c in raws)
        assert {c["cmd"][c["cmd"].index("--raw") + 1] for c in raws} == {
            f"/api/v1/namespaces/{lab.namespace}/pods/{p}:4191/proxy/{e}" for p in ("web-1", "web-2") for e in ("metrics", "env.json")}


def test_mesh_status_unmeshed_pod_reports_not_injected(monkeypatch):
    holder = {}
    pods = [mesh_pod("web-0", "web", proxy=False)]
    mesh_lab_fake(monkeypatch, pods, {}, holder)
    with testkit.KubeLab(mesh=True) as lab:
        holder["ns"] = lab.namespace
        status = lab.mesh_status("pod/web-0")
        assert status["pods"] == ["web-0"] and not status["injected"] and not status["mtls"] and status["identity"] is None


def test_mesh_status_without_certificate_has_no_identity(monkeypatch):
    holder = {}
    pods = [mesh_pod("web-1", "web")]
    mesh_lab_fake(monkeypatch, pods, {"web-1": WEB_METRICS.replace("1794439715.0", "0")}, holder)
    with testkit.KubeLab(mesh=True) as lab:
        holder["ns"] = lab.namespace
        status = lab.mesh_status("deployment/web")
        assert status["injected"] and not status["mtls"] and status["identity"] is None


@pytest.mark.parametrize("change", [
    {"image": "evil/fake-proxy:1"}, {"image": "cr.l5d.io/linkerd/proxy:edge-26.11.1"}, {"version": None},
    {"version": "edge-26.11.1"},
])
def test_mesh_status_refuses_spoofed_proxy_container(monkeypatch, change):
    holder = {}
    pods = [mesh_pod("web-1", "web", **change)]
    fake = mesh_lab_fake(monkeypatch, pods, {"web-1": WEB_METRICS}, holder)
    with testkit.KubeLab(mesh=True) as lab:
        holder["ns"] = lab.namespace
        status = lab.mesh_status("deployment/web")
        assert not status["injected"] and not status["mtls"] and status["identity"] is None
        assert status["success"] == 0 and status["clients"] == []
        assert not [c for c in fake.sandbox_calls if "--raw" in c["cmd"] and "/readyz" not in c["cmd"]]


@pytest.mark.parametrize("local", ["api.NS.serviceaccount.identity.linkerd.cluster.local",
                                   "web.devops-ex-other.serviceaccount.identity.linkerd.cluster.local", "", "web"])
def test_mesh_status_identity_must_match_pod_service_account(monkeypatch, local):
    holder = {}
    pods = [mesh_pod("web-1", "web")]
    mesh_lab_fake(monkeypatch, pods, {"web-1": WEB_METRICS}, holder, identities={"web-1": local})
    with testkit.KubeLab(mesh=True) as lab:
        holder["ns"] = lab.namespace
        status = lab.mesh_status("deployment/web")
        assert status["injected"] and not status["mtls"] and status["identity"] is None


def test_mesh_status_default_service_account_identity(monkeypatch):
    holder = {}
    pod = mesh_pod("web-1", "")
    mesh_lab_fake(monkeypatch, [pod], {"web-1": WEB_METRICS}, holder,
                  identities={"web-1": "default.NS.serviceaccount.identity.linkerd.cluster.local"})
    del pod["spec"]["serviceAccountName"]
    with testkit.KubeLab(mesh=True) as lab:
        holder["ns"] = lab.namespace
        assert lab.mesh_status("deployment/web")["identity"] == mesh_identity("default", lab.namespace)


def test_linkerd_metrics_ignore_non_finite_values():
    text = ('response_total{direction="inbound",target_port="80",tls="true",client_id="a",classification="success"} NaN\n'
            'response_total{direction="inbound",target_port="80",tls="true",client_id="b",classification="failure"} +Inf\n'
            'inbound_http_authz_deny_total{target_port="80"} -Inf\n'
            'control_identity_cert_expiration_timestamp_seconds NaN\n'
            'response_total{direction="inbound",target_port="80",tls="true",client_id="c",classification="success"} 2\n')
    counts = testkit._linkerd_metrics(text)
    assert (counts["success"], counts["failure"], counts["denied"], counts["cert"]) == (2, 0, 0, False)
    assert counts["clients"] == {"c"}


def test_close_releases_hook_finalizer_on_linkerd_kinds(monkeypatch):
    fake = ArgoFake(monkeypatch)
    original = fake.run_sandboxed
    listed = []

    def run_sandboxed(cmd, **kwargs):
        joined = " ".join(map(str, cmd))
        if "api-resources --api-group=policy.linkerd.io" in joined:
            return subprocess.CompletedProcess(cmd, 0, LINKERD_RESOURCES, "")
        if "jobs.batch" in joined and "json" in cmd:
            listed.append(list(map(str, cmd)))
        return original(cmd, **kwargs)

    monkeypatch.setattr(testkit, "run_sandboxed", run_sandboxed)
    with testkit.KubeLab():
        pass
    [cmd] = listed
    kinds = cmd[cmd.index("get") + 1].split(",")
    assert {f"{r}.policy.linkerd.io" for r in testkit.KUBE_LINKERD_RESOURCES} <= set(kinds)
    assert "jobs.batch" in kinds


def test_close_hook_kinds_without_linkerd_have_no_linkerd_group(monkeypatch):
    fake = ArgoFake(monkeypatch)
    original = fake.run_sandboxed
    listed = []

    def run_sandboxed(cmd, **kwargs):
        if "jobs.batch" in " ".join(map(str, cmd)) and "json" in cmd:
            listed.append(list(map(str, cmd)))
        return original(cmd, **kwargs)

    monkeypatch.setattr(testkit, "run_sandboxed", run_sandboxed)
    with testkit.KubeLab():
        pass
    [cmd] = listed
    assert "linkerd" not in cmd[cmd.index("get") + 1]


@pytest.mark.parametrize("workload", ["", "Web", "service/web", "deployment/", "web; rm -rf /", "../web", "-n", None,
                                      "deployment/web/x"])
def test_mesh_status_validates_workload(monkeypatch, workload):
    LinkerdFake(monkeypatch)
    with testkit.KubeLab(mesh=True) as lab:
        with pytest.raises(ValueError):
            lab.mesh_status(workload)


def test_linkerd_setup_pinned_and_documented():
    import hashlib

    folder = testkit.KUBE_LINKERD_DIR
    sums = dict(reversed(line.split()) for line in (folder / "SHA256SUMS").read_text(encoding="utf-8").splitlines())
    assert set(sums) == {p.name for p in folder.iterdir() if p.is_file() and p.name != "SHA256SUMS"}
    for name, digest in sums.items():
        assert hashlib.sha256((folder / name).read_bytes()).hexdigest() == digest, name
    text = "\n".join((folder / name).read_text(encoding="utf-8") for name in sums)
    for name in sums:
        if name.endswith(".yaml"):
            body = (folder / name).read_text(encoding="utf-8")
            assert "-----BEGIN" not in body and not re.search(r"^\s*tls\.key:", body, re.M), name
    images = set(re.findall(r"image: (\S+)", text))
    assert images == set(testkit.KUBE_LINKERD_IMAGES)
    pulls = re.findall(r"imagePullPolicy: (\S+)", text)
    assert pulls and set(pulls) == {"Never"}
    rendered = (folder / "20-linkerd-control-plane-edge-26.10.1.yaml").read_text(encoding="utf-8")
    for needle in ("cniEnabled: true", "disableHeartBeat: true", "externalCA: true", "scheme: kubernetes.io/tls",
                   "linkerdVersion: edge-26.10.1", "enableShutdownEndpoint: false"):
        assert needle in rendered, needle
    assert "kind: Secret" not in rendered and "kind: CronJob" not in rendered
    assert rendered.count(f"caBundle: {base64.b64encode(testkit.KUBE_LINKERD_CA_PLACEHOLDER.encode()).decode()}") == 3
    script = (folder / "certs.sh").read_text(encoding="utf-8")
    for needle in ("mktemp -d", "trap 'rm -rf", "umask 077", "rm -f root.key", "openssl genpkey -algorithm EC",
                   "linkerd-identity-trust-roots", "linkerd-identity-issuer", "--server-side", "caBundle"):
        assert needle in script, needle
    assert script.index("rm -f root.key") < script.index("create configmap linkerd-identity-trust-roots")
    doc = (testkit.ROOT / "setup" / "DEVOPS-TOOLS.md").read_text(encoding="utf-8")
    for needle in (*testkit.KUBE_LINKERD_IMAGES.values(), "setup/kind/linkerd", "bash setup/kind/linkerd/certs.sh",
                   "edge-26.10.1", "66d634f5318c8016f0b5face246a688964b6e2c86d6c3be34be68ab9fcd2a8cc"):
        assert needle in doc, needle


@pytest.mark.skipif(not shutil.which("kubectl"), reason="Cần kubectl để render kustomization")
def test_linkerd_rendered_manifests_fail_closed(tmp_path):
    import yaml

    env = {"PATH": os.environ["PATH"], "HOME": str(tmp_path), "KUBECONFIG": str(tmp_path / "none"), "KUBERC": "off"}
    result = subprocess.run(["kubectl", "kustomize", str(testkit.KUBE_LINKERD_DIR)], capture_output=True, text=True, env=env,
                            timeout=120)
    assert result.returncode == 0, result.stderr
    docs = [d for d in yaml.safe_load_all(result.stdout) if d]
    namespaces = {d["metadata"].get("namespace") for d in docs} - {None}
    assert namespaces == {"linkerd", "linkerd-cni"}
    for doc in docs:
        if doc["kind"] in ("Deployment", "DaemonSet"):
            spec = doc["spec"]["template"]["spec"]
            for container in spec.get("initContainers", []) + spec["containers"]:
                assert container.get("imagePullPolicy") == "Never", (doc["metadata"]["name"], container["name"])
                assert "NET_ADMIN" not in json.dumps(container), container["name"]
    assert not [d for d in docs if d["kind"] in ("Secret", "CronJob")]
    labelled = [d["metadata"]["name"] for d in docs if "devops-ex" in (d["metadata"].get("labels") or {})]
    assert labelled == []
    ns = {d["metadata"]["name"]: d["metadata"]["labels"] for d in docs if d["kind"] == "Namespace"}
    assert ns["linkerd"]["pod-security.kubernetes.io/enforce"] == "restricted"
    assert ns["linkerd"]["config.linkerd.io/admission-webhooks"] == "disabled"
    injector = next(d for d in docs if d["kind"] == "MutatingWebhookConfiguration")
    exprs = injector["webhooks"][0]["namespaceSelector"]["matchExpressions"]
    assert {"key": "config.linkerd.io/admission-webhooks", "operator": "NotIn", "values": ["disabled"]} in exprs


MESH_APP = """apiVersion: v1
kind: ServiceAccount
metadata: {name: SA}
---
apiVersion: apps/v1
kind: Deployment
metadata: {name: SA}
spec:
  selector: {matchLabels: {app: SA}}
  template:
    metadata: {labels: {app: SA}}
    spec:
      serviceAccountName: SA
      containers:
      - name: SA
        image: nginx:1.30.6-alpine
        imagePullPolicy: Never
        ports: [{containerPort: 80, name: http}]
"""
MESH_POLICY = """apiVersion: v1
kind: Service
metadata: {name: web}
spec:
  selector: {app: web}
  ports: [{port: 80, targetPort: 80, name: http}]
---
apiVersion: policy.linkerd.io/v1beta3
kind: Server
metadata: {name: web-http}
spec:
  podSelector: {matchLabels: {app: web}}
  port: http
  proxyProtocol: HTTP/1
---
apiVersion: policy.linkerd.io/v1alpha1
kind: MeshTLSAuthentication
metadata: {name: api-only}
spec:
  identityRefs:
  - {kind: ServiceAccount, name: api}
---
apiVersion: policy.linkerd.io/v1alpha1
kind: AuthorizationPolicy
metadata: {name: web-from-api}
spec:
  targetRef: {group: policy.linkerd.io, kind: Server, name: web-http}
  requiredAuthenticationRefs:
  - {group: policy.linkerd.io, kind: MeshTLSAuthentication, name: api-only}
"""


def curl_code(lab, deployment: str, url: str) -> str:
    result = lab.kubectl("exec", f"deploy/{deployment}", "-c", deployment, "--", "curl", "-s", "-m", "5", "-o", "/dev/null",
                         "-w", "%{http_code}", url, check=False)
    return result.stdout.strip()


@KUBE_REQUIRED
def test_kube_lab_mesh_mtls_and_authorization_policy_real(tmp_path):
    testkit.Exercise.require_cluster()
    testkit.Exercise.require_linkerd()
    testkit.Exercise.require_kind_images(testkit.KUBE_IMAGES["nginx"])
    (tmp_path / "app.yaml").write_text("---\n".join(MESH_APP.replace("SA", sa) for sa in ("web", "api", "intruder")), encoding="utf-8")
    (tmp_path / "policy.yaml").write_text(MESH_POLICY, encoding="utf-8")
    with testkit.KubeLab(mesh=True) as lab:
        lab.apply_learner(tmp_path / "app.yaml")
        lab.kubectl("rollout", "status", "deployment/web", "deployment/api", "deployment/intruder", "--timeout=120s", timeout=150)
        lab.apply_learner(tmp_path / "policy.yaml")
        deadline = time.monotonic() + 60
        while time.monotonic() < deadline and curl_code(lab, "intruder", "http://web/") != "403":
            time.sleep(1)
        assert [curl_code(lab, "api", "http://web/") for _ in range(3)] == ["200"] * 3
        assert curl_code(lab, "intruder", "http://web/") == "403"
        web = lab.mesh_status("deployment/web")
        assert web["injected"] and web["mtls"], web
        assert web["identity"] == f"web.{lab.namespace}.serviceaccount.identity.linkerd.cluster.local"
        assert f"api.{lab.namespace}.serviceaccount.identity.linkerd.cluster.local" in web["clients"]
        assert web["success"] >= 3 and web["denied"] >= 1 and web["failure"] == 0, web
        api = lab.mesh_status("api")
        assert api["identity"] == f"api.{lab.namespace}.serviceaccount.identity.linkerd.cluster.local"
        assert web["identity"] in api["servers"] and api["outbound_success"] >= 3, api
    assert testkit.kube_leftovers(lab.id) == []


@KUBE_REQUIRED
def test_linkerd_policy_vap_refuses_foreign_namespace_real():
    testkit.Exercise.require_cluster()
    testkit.Exercise.require_linkerd()
    with testkit.KubeLab() as lab:
        def named(doc, name):
            return {**doc, "metadata": {"name": name}}

        good = [named(mesh_doc("MeshTLSAuthentication", {"identities": [mesh_identity("api", lab.namespace)]}), "by-name"),
                named(mesh_doc("MeshTLSAuthentication", {"identityRefs": [{"kind": "ServiceAccount", "name": "api"}]}), "good"),
                named(mesh_doc("AuthorizationPolicy", {"targetRef": {"kind": "Namespace", "name": lab.namespace},
                                                       "requiredAuthenticationRefs": [{"group": "policy.linkerd.io",
                                                                                       "kind": "MeshTLSAuthentication",
                                                                                       "name": "good"}]}), "good"),
                named(mesh_doc("HTTPRoute", {"parentRefs": [{"group": "core", "kind": "Service", "name": "web", "port": 80}],
                                             "rules": [{"backendRefs": [{"name": "web", "port": 80}]}]}, "v1beta3"), "good")]
        for doc in good:
            result = lab.kubectl("apply", "-f", "-", input=json.dumps(doc), check=False)
            assert result.returncode == 0, (doc["kind"], result.stderr)
        for case, doc in sorted(FOREIGN_MESH.items()):
            if case == "authz-target-ns-field":
                continue
            text = json.dumps(doc).replace(MESH_NS, lab.namespace)
            result = lab.kubectl("apply", "-f", "-", input=text.replace('"name": "x"', f'"name": "{case}"', 1), check=False)
            assert result.returncode != 0 and f"{lab.namespace}-mesh" in result.stderr, (case, result.stderr)
        for resource in ("networkauthentications", "httplocalratelimitpolicies", "serverauthorizations", "egressnetworks"):
            assert lab.kubectl("auth", "can-i", "create", f"{resource}.policy.linkerd.io", check=False).stdout.strip() == "no"
        assert lab.kubectl("auth", "can-i", "create", "serviceprofiles.linkerd.io", check=False).stdout.strip() == "no"
        assert lab.kubectl("auth", "can-i", "create", "servers.policy.linkerd.io", "-n", "linkerd",
                           check=False).stdout.strip() == "no"


def fault_info(name: str, *, labels=None, running=True, tmpfs=None, cid=None) -> dict:
    return {"Name": f"/{name}", "Id": cid or f"id-{name}", "State": {"Running": running},
            "Config": {"Labels": {"devops-ex": "1", **(labels or {})}}, "HostConfig": {"Tmpfs": tmpfs or {}}}


class FakeFaultDocker:
    """`_docker` giả cho FaultInjector: `ps` trả mọi tên (kể cả container lạ), `inspect` đọc từ `infos`, lệnh khác được ghi."""

    def __init__(self, infos: list[dict]):
        self.infos = {i["Name"].lstrip("/"): i for i in infos}
        self.calls: list[tuple[str, ...]] = []

    def __call__(self, *args, timeout=60):
        self.calls.append(args)
        if args[0] == "ps":
            return subprocess.CompletedProcess(args, 0, "\n".join(self.infos), "")
        if args[0] == "inspect":
            found = [self.infos[n] for n in args[1:] if n in self.infos]
            return subprocess.CompletedProcess(args, 0 if found else 1, json.dumps(found), "" if found else "No such object")
        if args[0] in ("kill", "stop"):
            self.infos[args[-1]]["State"]["Running"] = False
        if args[0] == "start":
            self.infos[args[-1]]["State"]["Running"] = True
        return subprocess.CompletedProcess(args, 0, "", "")

    def mutations(self) -> list[tuple[str, ...]]:
        return [c for c in self.calls if c[0] not in ("ps", "inspect")]


def fault_lab(monkeypatch, *, foreign=True):
    lab = testkit.DockerLab()
    lab._entered = True
    prefix = lab.network
    compose = {"devops-ex.lab": lab.id, "com.docker.compose.project": prefix}
    infos = [
        fault_info(f"{prefix}-api-1", labels={**compose, "com.docker.compose.service": "api"}),
        fault_info(f"{prefix}-worker-1", labels={**compose, "com.docker.compose.service": "worker"}),
        fault_info(f"{prefix}-redis-1", labels={**compose, "com.docker.compose.service": "redis"}, tmpfs={"/data": "size=16m"}),
        fault_info(f"{prefix}-postgres-1", labels={**compose, "com.docker.compose.service": "postgres"},
                   tmpfs={"/var/lib/postgresql/data": ""}),
        fault_info(f"{prefix}-prometheus-1", labels={**compose, "com.docker.compose.service": "prometheus"}, tmpfs={"/prometheus": "size=8m"}),
    ]
    if foreign:
        infos += [
            fault_info(f"{prefix}-decoy", tmpfs={"/data": "size=1m"}),
            fault_info(f"{prefix}-other-lab", labels={"devops-ex.lab": "ffffffff"}),
            fault_info(f"devops-ex-ffffffff-redis-1", labels={"devops-ex.lab": "ffffffff", "com.docker.compose.service": "redis"}),
            {**fault_info(f"{prefix}-unlabelled"), "Config": {"Labels": {"devops-ex.lab": lab.id}}},
            fault_info("de-learning-redis", labels={"com.docker.compose.service": "redis"}),
        ]
    fake = FakeFaultDocker(infos)
    monkeypatch.setattr(testkit, "_docker", fake)
    return lab, fake


def test_fault_injector_rejects_bad_arguments(monkeypatch):
    lab, _ = fault_lab(monkeypatch)
    with pytest.raises(TypeError):
        testkit.FaultInjector(object(), seed=1)
    for seed in ("1", True, 1.5):
        with pytest.raises(TypeError):
            testkit.FaultInjector(lab, seed=seed)
    with pytest.raises(ValueError, match="không nhận"):
        testkit.FaultInjector(lab, seed=1, faults=["rm-rf"])
    with pytest.raises(ValueError, match="không hỗ trợ bad-config"):
        testkit.FaultInjector(lab, seed=1, faults=["bad-config"])
    with pytest.raises(ValueError, match="không hỗ trợ net-delay"):
        testkit.FaultInjector(testkit.KubeLab(), seed=1, faults=["net-delay"])
    for delay in (0, 6000, True):
        with pytest.raises(ValueError):
            testkit.FaultInjector(lab, seed=1, delay_ms=delay)
    with pytest.raises(RuntimeError, match="with DockerLab"):
        testkit.FaultInjector(testkit.DockerLab(), seed=1).plan()


def test_fault_injector_seed_deterministic(monkeypatch):
    lab, fake = fault_lab(monkeypatch)
    plans = {seed: testkit.FaultInjector(lab, seed=seed).plan() for seed in range(200)}
    assert all(testkit.FaultInjector(lab, seed=seed).plan() == plan for seed, plan in plans.items())
    assert {code for code, _ in plans.values()} == set(testkit.FAULT_DOCKER_CODES)
    assert {service for _, service in plans.values()} == {"api", "worker", "redis", "postgres"}
    assert {s for c, s in plans.values() if c == "disk-full"} == {"redis"}
    assert {s for c, s in plans.values() if c == "redis-stop"} == {"redis"}
    assert fake.mutations() == [], "plan() không được thay đổi gì"
    only = {testkit.FaultInjector(lab, seed=seed, faults=["kill"], services=["api", "worker"]).plan() for seed in range(50)}
    assert only == {("kill", "api"), ("kill", "worker")}
    shuffled, _ = fault_lab(monkeypatch)
    fake_infos = list(testkit._docker.infos.items())
    testkit._docker.infos = dict(reversed(fake_infos))
    assert {seed: testkit.FaultInjector(shuffled, seed=seed).plan() for seed in range(200)} == plans, \
        "Thứ tự docker ps trả về không được đổi lựa chọn"


def test_fault_injector_only_touches_lab_resources(monkeypatch):
    lab, fake = fault_lab(monkeypatch)
    found = testkit.FaultInjector(lab, seed=1).candidates()
    assert {service for _, service in found} == {"api", "worker", "redis", "postgres"}
    with pytest.raises(pytest.fail.Exception, match="không có tài nguyên"):
        testkit.FaultInjector(lab, seed=1, services=["decoy", "other-lab", "unlabelled", "prometheus"]).plan()
    for name in (f"{lab.network}-decoy", f"{lab.network}-other-lab", "de-learning-redis", f"{lab.network}-unlabelled"):
        with pytest.raises(RuntimeError, match="từ chối"):
            testkit.FaultInjector(lab, seed=1)._inspect(name)
    for code in ("kill", "redis-stop", "disk-full"):
        injector = testkit.FaultInjector(lab, seed=3, faults=[code])
        assert injector.inject() == code
        assert injector.revert() == []
    own = {f"{lab.network}-api-1", f"{lab.network}-worker-1", f"{lab.network}-redis-1", f"{lab.network}-postgres-1"}
    touched = [c for c in fake.mutations()]
    assert touched and all(any(arg in own for arg in call) for call in touched), touched
    listed = [c for c in fake.calls if c[0] == "inspect" and len(c) > 2]
    assert listed and all(n.startswith(f"{lab.network}-") for c in listed for n in c[1:]), listed
    assert not [c for c in touched if f"{lab.network}-prometheus-1" in c]


class FakeKube:
    def __init__(self, lab, objects):
        self.lab = lab
        self.objects = objects
        self.calls: list[tuple[str, ...]] = []

    def __call__(self, *args, check=True, input=None, timeout=None):
        self.calls.append(args)
        if args[0] == "get" and "-o" in args and args[args.index("-o") + 1] == "json":
            return subprocess.CompletedProcess(args, 0, json.dumps({"items": self.objects}), "")
        if args[0] == "get" and "jsonpath={.spec.replicas}" in args:
            workload = next(o for o in self.objects if f"{o['kind'].lower()}/{o['metadata']['name']}" == args[1])
            return subprocess.CompletedProcess(args, 0, str(workload["spec"]["replicas"]), "")
        if args[0] == "scale":
            workload = next(o for o in self.objects if f"{o['kind'].lower()}/{o['metadata']['name']}" == args[1])
            workload["spec"]["replicas"] = int(args[2].split("=")[1])
        if args[:2] == ("patch", "configmap"):
            config = next(o for o in self.objects if o["kind"] == "ConfigMap" and o["metadata"]["name"] == args[2])
            config["data"].update(json.loads(args[-1])["data"])
        return subprocess.CompletedProcess(args, 0, "", "")


def kube_objects() -> list[dict]:
    def workload(kind, name, replicas=1, *, env_from=None, volumes=(), mounts=()):
        container = {"name": "main", "image": "x", "volumeMounts": list(mounts)}
        if env_from:
            container["envFrom"] = [{"configMapRef": {"name": env_from}}]
        return {"kind": kind, "metadata": {"name": name}, "spec": {"replicas": replicas, "selector": {"matchLabels": {"app": name}},
                "template": {"metadata": {"labels": {"app": name}}, "spec": {"containers": [container], "volumes": list(volumes)}}}}

    def pod(name, app, phase="Running"):
        return {"kind": "Pod", "metadata": {"name": name, "labels": {"app": app}}, "status": {"phase": phase}}

    return [
        workload("Deployment", "api", 2, env_from="api-config",
                 volumes=[{"name": "scratch", "emptyDir": {"sizeLimit": "16Mi"}}], mounts=[{"name": "scratch", "mountPath": "/scratch"}]),
        workload("Deployment", "redis"),
        workload("StatefulSet", "postgres", volumes=[{"name": "big", "emptyDir": {"sizeLimit": "4Gi"}}],
                 mounts=[{"name": "big", "mountPath": "/big"}]),
        {"kind": "ConfigMap", "metadata": {"name": "api-config"}, "data": {"DATABASE_URL": "postgresql://postgres/olist"}},
        {"kind": "ConfigMap", "metadata": {"name": "unused"}, "data": {"A": "b"}},
        pod("api-7d9-b", "api"), pod("api-7d9-a", "api"), pod("redis-55-x", "redis"), pod("postgres-0", "postgres", "Pending"),
    ]


def test_fault_injector_kube_stays_in_lab_namespace(monkeypatch):
    lab = testkit.KubeLab()
    fake = FakeKube(lab, kube_objects())
    monkeypatch.setattr(lab, "kubectl", fake)
    lab._admin = None
    plans = {testkit.FaultInjector(lab, seed=s).plan() for s in range(200)}
    assert plans == {("kill", "deployment/api"), ("kill", "deployment/redis"), ("disk-full", "deployment/api"),
                     ("redis-stop", "deployment/redis"), ("bad-config", "configmap/api-config")}
    for code in testkit.FAULT_KUBE_CODES:
        with testkit.FaultInjector(lab, seed=7, faults=[code]) as injector:
            assert injector.inject() == code
    config = next(o for o in fake.objects if o["metadata"]["name"] == "api-config")
    assert config["data"] == {"DATABASE_URL": "postgresql://postgres/olist"}
    assert next(o for o in fake.objects if o["metadata"]["name"] == "redis")["spec"]["replicas"] == 1
    calls = [" ".join(c) for c in fake.calls]
    assert "delete pod api-7d9-a --grace-period=0 --force --wait=false" in calls
    assert "scale deployment/redis --replicas=0" in calls and "scale deployment/redis --replicas=1" in calls
    assert any(c.startswith("exec api-7d9-a -c main -- dd if=/dev/zero of=/scratch/") for c in calls)
    assert any(c.startswith("exec api-7d9-a -c main -- rm -f /scratch/") for c in calls)
    assert sum(c.startswith("patch deployment/api --type merge") for c in calls) == 2
    patched = [json.loads(c[-1]) for c in fake.calls if c[:2] == ("patch", "configmap")]
    assert patched[0]["data"]["DATABASE_URL"].endswith(testkit.FAULT_CONFIG_SUFFIX)
    for call in fake.calls:
        flat = " ".join(call)
        assert not re.search(r"\bnodes?\b|--namespace|\s-n\s|--all-namespaces|\s-A\b|--kubeconfig|--as", f" {flat} "), flat


def docker_ps(*filters: str) -> list[str]:
    args = ["ps", "-a", "--format", "{{.Names}}"]
    for f in filters:
        args += ["--filter", f]
    return testkit._docker(*args).stdout.split()


FAULT_COMPOSE = f"""
services:
  api:
    image: {BASE}
    command: ["python", "-m", "http.server", "8000"]
  redis:
    image: {testkit.KUBE_IMAGES["redis"]}
    tmpfs: ["/data:size=8m"]
"""


def qdiscs(name: str) -> str:
    result = subprocess.run(["docker", "run", "--rm", "--network", f"container:{name}", "--cap-drop", "ALL", "--cap-add", "NET_ADMIN",
                             "--security-opt", "no-new-privileges", *testkit.docker_cpu_args(), "--entrypoint", "tc",
                             testkit.FAULT_NETEM_IMAGE, "qdisc", "show"], capture_output=True, text=True, timeout=60)
    assert result.returncode == 0, result.stderr
    return result.stdout


def started_at(name: str) -> tuple[bool, str]:
    info = inspect_container(name)
    return info["State"]["Running"], info["State"]["StartedAt"]


def fill_exists(name: str) -> bool:
    return testkit._docker("exec", name, "test", "-e", f"/data/{testkit.FAULT_FILL_FILE}").returncode == 0


def fault_real_images():
    require_real_docker(BASE)
    require_real_docker(testkit.KUBE_IMAGES["redis"])
    require_real_docker(testkit.FAULT_NETEM_IMAGE)


def test_fault_injector_real_only_touches_lab_resources(monkeypatch, tmp_path):
    fault_real_images()
    monkeypatch.setenv("DEVOPS_CPUSET", build_cpuset())
    recorded: list[list[str]] = []
    active: list[bool] = []
    real_run = subprocess.run

    def recording(cmd, *args, **kwargs):
        if active and isinstance(cmd, list) and cmd[:1] == ["docker"]:
            recorded.append(list(cmd))
        return real_run(cmd, *args, **kwargs)

    lab, other = testkit.DockerLab(), testkit.DockerLab()
    decoy = None
    with lab, other:
        lab.compose(write_compose(tmp_path / "a", FAULT_COMPOSE))
        other.compose(write_compose(tmp_path / "b", FAULT_COMPOSE))
        decoy = f"{lab.network}-decoy"
        made = testkit._docker("run", "-d", "--name", decoy, "--label", "devops-ex=1", "--security-opt", "no-new-privileges",
                               *testkit.docker_cpu_args(), "--tmpfs", "/data:size=4m", testkit.KUBE_IMAGES["redis"])
        assert made.returncode == 0, made.stderr
        try:
            bystanders = [decoy] + [other.project.container(s) for s in ("api", "redis")]
            before = {name: started_at(name) for name in bystanders}
            own = {lab.project.container(s): inspect_container(lab.project.container(s))["Id"] for s in ("api", "redis")}
            monkeypatch.setattr(testkit.subprocess, "run", recording)
            for code in testkit.FAULT_DOCKER_CODES:
                injector = testkit.FaultInjector(lab, seed=11, faults=[code])
                active.append(True)
                try:
                    assert injector.inject() == code
                finally:
                    active.clear()
                assert injector.resource in ("api", "redis")
                for name in bystanders:
                    assert started_at(name) == before[name], f"{code} chạm {name}"
                    assert "netem" not in qdiscs(name), f"{code} thêm netem vào {name}"
                assert not fill_exists(decoy) and not fill_exists(other.project.container("redis"))
                active.append(True)
                try:
                    assert injector.revert() == []
                finally:
                    active.clear()
            monkeypatch.setattr(testkit.subprocess, "run", real_run)
            names = set(own) | set(own.values())
            for argv in recorded:
                verb = argv[1]
                if verb in ("kill", "stop", "start", "exec"):
                    target = next(a for a in argv[2:] if not a.startswith("-") and a not in ("0", "5"))
                    assert target in names, argv
                if verb == "run":
                    assert argv[argv.index("--network") + 1].removeprefix("container:") in names, argv
                    assert argv[argv.index("--cap-add") + 1] == "NET_ADMIN" and argv[argv.index("--cap-drop") + 1] == "ALL"
                    assert "no-new-privileges" in argv and "--read-only" in argv and "--rm" in argv
                    assert argv[argv.index("--name") + 1].startswith(f"{lab.network}-fault-netem-")
            assert {argv[1] for argv in recorded} >= {"kill", "stop", "start", "exec", "run"}
            for name in own:
                assert not inspect_container(name)["HostConfig"].get("CapAdd"), "Container của bài không được thêm capability"
        finally:
            monkeypatch.setattr(testkit.subprocess, "run", real_run)
            testkit._docker("rm", "-f", "-v", decoy)
    assert testkit.docker_leftovers(lab.id) == [] and testkit.docker_leftovers(other.id) == []


def test_fault_injector_reverts_on_close(monkeypatch, tmp_path):
    import warnings

    fault_real_images()
    monkeypatch.setenv("DEVOPS_CPUSET", build_cpuset())
    lab = testkit.DockerLab()
    with lab:
        project = lab.compose(write_compose(tmp_path, FAULT_COMPOSE))
        api, redis = project.container("api"), project.container("redis")
        for code, service in (("kill", "api"), ("redis-stop", "redis"), ("net-delay", "api"), ("disk-full", "redis")):
            injector = testkit.FaultInjector(lab, seed=5, faults=[code], services=[service])
            name = api if service == "api" else redis
            assert injector.inject() == code and injector.resource == service
            if code in ("kill", "redis-stop"):
                assert not started_at(name)[0]
            elif code == "net-delay":
                assert f"delay {testkit.FAULT_DELAY_MS}ms" in qdiscs(name)
            else:
                assert fill_exists(name)
                full = testkit._docker("exec", name, "sh", "-c", "echo x > /data/probe")
                assert full.returncode != 0 and "space" in full.stderr.lower()
            with warnings.catch_warnings():
                warnings.simplefilter("error")
                injector.close()
            assert started_at(name)[0], f"{code}: container chưa chạy lại"
            assert "netem" not in qdiscs(name) and not fill_exists(name)
            with pytest.raises(RuntimeError, match="một lỗi"):
                injector.inject()
        recovered = testkit.FaultInjector(lab, seed=5, faults=["kill"], services=["api"])
        recovered.inject()
        assert project.run("up", "-d", "--force-recreate", "--no-deps", "api").returncode == 0
        delayed = testkit.FaultInjector(lab, seed=5, faults=["net-delay"], services=["redis"])
        delayed.inject()
        assert project.run("restart", "redis").returncode == 0
        with warnings.catch_warnings():
            warnings.simplefilter("error")
            assert recovered.revert() == [] and delayed.revert() == []
        assert started_at(project.container("api"))[0]
    assert testkit.docker_leftovers(lab.id) == []
    project_volumes = testkit._docker("volume", "ls", "-q", "--filter", f"label=com.docker.compose.project=devops-ex-{lab.id}")
    assert project_volumes.stdout.split() == []


@KUBE_REQUIRED
def test_fault_injector_kube_real():
    testkit.Exercise.require_cluster()
    testkit.Exercise.require_kind_images(testkit.KUBE_IMAGES["redis"])
    image = testkit.KUBE_IMAGES["redis"]

    def deployment(name, command, **extra):
        container = {"name": "main", "image": image, "imagePullPolicy": "Never", "command": command, **extra.pop("container", {})}
        return {"apiVersion": "apps/v1", "kind": "Deployment", "metadata": {"name": name},
                "spec": {"replicas": 1, "selector": {"matchLabels": {"app": name}},
                         "template": {"metadata": {"labels": {"app": name}},
                                      "spec": {"terminationGracePeriodSeconds": 0, "containers": [container], **extra}}}}

    docs = [
        {"apiVersion": "v1", "kind": "ConfigMap", "metadata": {"name": "web-config"}, "data": {"MODE": "ok"}},
        deployment("web", ["sh", "-c", "sleep 3600"], container={"envFrom": [{"configMapRef": {"name": "web-config"}}],
                                                                 "volumeMounts": [{"name": "scratch", "mountPath": "/scratch"}]},
                   volumes=[{"name": "scratch", "emptyDir": {"medium": "Memory", "sizeLimit": "8Mi"}}]),
        deployment("redis", ["redis-server"]),
    ]
    with testkit.KubeLab() as lab:
        lab.kubectl("apply", "-f", "-", input=json.dumps({"apiVersion": "v1", "kind": "List", "items": docs}))
        lab.kubectl("rollout", "status", "deployment/web", "deployment/redis", "--timeout=120s", timeout=150)

        def pods(app):
            out = lab.kubectl("get", "pods", "-l", f"app={app}", "-o", "json").stdout
            return [p["metadata"]["name"] for p in json.loads(out)["items"] if not p["metadata"].get("deletionTimestamp")]

        before = pods("web")
        with testkit.FaultInjector(lab, seed=2, faults=["kill"], services=["web"]) as injector:
            assert injector.inject() == "kill"
        lab.kubectl("rollout", "status", "deployment/web", "--timeout=120s", timeout=150)
        deadline = time.monotonic() + 60
        while set(pods("web")) & set(before) and time.monotonic() < deadline:
            time.sleep(1)
        assert not set(pods("web")) & set(before), "Pod bị kill phải được thay"
        with testkit.FaultInjector(lab, seed=2, faults=["redis-stop"]) as injector:
            injector.inject()
            assert lab.kubectl("get", "deployment/redis", "-o", "jsonpath={.spec.replicas}").stdout == "0"
        assert lab.kubectl("get", "deployment/redis", "-o", "jsonpath={.spec.replicas}").stdout == "1"
        lab.kubectl("rollout", "status", "deployment/web", "--timeout=120s", timeout=150)
        pod = pods("web")[0]
        with testkit.FaultInjector(lab, seed=2, faults=["disk-full"]) as injector:
            injector.inject()
            assert lab.kubectl("exec", pod, "--", "test", "-e", f"/scratch/{testkit.FAULT_FILL_FILE}", check=False).returncode == 0
        assert lab.kubectl("exec", pod, "--", "test", "-e", f"/scratch/{testkit.FAULT_FILL_FILE}", check=False).returncode != 0
        with testkit.FaultInjector(lab, seed=2, faults=["bad-config"]) as injector:
            assert injector.inject() == "bad-config" and injector.resource == "configmap/web-config"
            data = json.loads(lab.kubectl("get", "configmap", "web-config", "-o", "json").stdout)["data"]
            assert data == {"MODE": f"ok{testkit.FAULT_CONFIG_SUFFIX}"}
            lab.kubectl("rollout", "status", "deployment/web", "--timeout=120s", timeout=150)
            new = pods("web")[0]
            assert lab.kubectl("exec", new, "--", "printenv", "MODE").stdout.strip() == f"ok{testkit.FAULT_CONFIG_SUFFIX}"
        assert json.loads(lab.kubectl("get", "configmap", "web-config", "-o", "json").stdout)["data"] == {"MODE": "ok"}
        nodes_before = admin_kubectl("get", "nodes", "-o", "json")
        assert all(not n["spec"].get("unschedulable") and not n["spec"].get("taints", [])
                   or n["metadata"]["name"].endswith("control-plane") for n in json.loads(nodes_before.stdout)["items"])


def test_k6_run_argv_and_summary(monkeypatch, tmp_path):
    fake = FakeDocker()
    marker = testkit.K6_SUMMARY_MARKER

    def run(cmd, **kwargs):
        fake(cmd, **kwargs)
        if cmd[:2] == ["docker", "run"]:
            harness = next(a.split(":")[0] for a in cmd if a.endswith(":/harness:ro"))
            text = Path(harness, "run.js").read_text(encoding="utf-8")
            assert 'export * from "/scripts/load.js";' in text and "handleSummary" in text
            return subprocess.CompletedProcess(cmd, 99, f"log\n{marker}" + json.dumps({"metrics": {"x": {"values": {"rate": 1}}}}) + "\n", "")
        return subprocess.CompletedProcess(cmd, 0, "", "")

    monkeypatch.setattr(testkit.subprocess, "run", run)
    monkeypatch.setattr(testkit.Exercise, "require_image", staticmethod(lambda *a, **k: None))
    monkeypatch.setenv("DEVOPS_CPUSET", "2-3")
    script = tmp_path / "load.js"
    script.write_text("export default function () {}\n", encoding="utf-8")
    with testkit.DockerLab() as lab:
        result, summary = testkit.k6_run(lab, script, env={"TARGET": "http://api:8000", "STEPS": "10,20"})
        assert result.returncode == 99 and summary == {"metrics": {"x": {"values": {"rate": 1}}}}
        with pytest.raises(ValueError):
            testkit.k6_run(lab, script, env={"BAD KEY": "x"})
        (tmp_path / "evil.js").symlink_to(script)
        with pytest.raises(pytest.fail.Exception, match="tệp .js thường"):
            testkit.k6_run(lab, tmp_path / "evil.js")
    argv = next(c for c in fake.calls if c[:2] == ["docker", "run"])
    assert "--rm" in argv and argv[argv.index("--network") + 1] == lab.network
    assert f"{tmp_path.resolve()}:/scripts:ro" in argv and argv[argv.index("--user") + 1] == f"{os.getuid()}:{os.getgid()}"
    assert argv[argv.index("--memory") + 1] == testkit.K6_MEMORY and argv[argv.index("--cpuset-cpus") + 1] == "2-3"
    tail = argv[argv.index(testkit.K6_IMAGE):]
    assert tail == [testkit.K6_IMAGE, "run", "--quiet", "--no-color", "-e", "TARGET=http://api:8000", "-e", "STEPS=10,20",
                    "/harness/run.js"]
    import tempfile

    assert not list(Path(tempfile.gettempdir()).glob(f"{lab.network}-k6-*")), "Thư mục harness phải được xoá"


def test_k6_image_matches_mlops_pin():
    mlops = (testkit.ROOT / "mlopskit.py").read_text(encoding="utf-8")
    tag = re.search(r'K6_IMAGE = "([^"]+)"', mlops).group(1)
    assert testkit.K6_IMAGE.startswith(f"{tag}@sha256:") and re.fullmatch(r".+@sha256:[0-9a-f]{64}", testkit.K6_IMAGE)


def test_k6_run_real(monkeypatch, tmp_path):
    require_real_docker(BASE)
    require_real_docker(testkit.K6_IMAGE)
    monkeypatch.setenv("DEVOPS_CPUSET", build_cpuset())
    work = tmp_path / "k6"
    work.mkdir(mode=0o700)
    (work / "load.js").write_text(
        'import http from "k6/http";\nimport { check } from "k6";\n'
        'export const options = { scenarios: { probe: { executor: "constant-arrival-rate", rate: 10, timeUnit: "1s", '
        'duration: "2s", preAllocatedVUs: 5 } }, thresholds: { "http_req_failed{scenario:probe}": ["rate<0.01"] } };\n'
        'export default function () { check(http.get(`${__ENV.TARGET}/`), { ok: (r) => r.status === 200 }); }\n',
        encoding="utf-8")
    lab = testkit.DockerLab()
    with lab:
        lab.start("api", BASE, "python", "-u", "-m", "http.server", "8000")
        lab.wait_log("api", "Serving HTTP")
        result, summary = testkit.k6_run(lab, work / "load.js", env={"TARGET": "http://api:8000"}, timeout=120)
        assert result.returncode == 0, result.stderr[-2000:]
        assert summary["metrics"]["http_reqs"]["values"]["count"] >= 15
        assert summary["metrics"]["http_req_failed{scenario:probe}"]["values"]["rate"] == 0
        failed, summary = testkit.k6_run(lab, work / "load.js", env={"TARGET": "http://api:8000/khong-co"}, timeout=120)
        assert failed.returncode == 99, failed.stderr[-2000:]
        assert summary["metrics"]["http_req_failed{scenario:probe}"]["thresholds"]["rate<0.01"]["ok"] is False
    assert testkit.docker_leftovers(lab.id) == []


def test_fault_injector_fails_loudly_when_docker_ps_fails(monkeypatch):
    lab, fake = fault_lab(monkeypatch, foreign=False)
    calls = []

    def broken(*args, timeout=60):
        calls.append(args)
        if args[0] == "ps" and len(calls) <= 2:
            return subprocess.CompletedProcess(args, 1, "", "Error response from daemon: busy")
        return fake(*args, timeout=timeout)

    monkeypatch.setattr(testkit, "_docker", broken)
    monkeypatch.setattr(testkit.time, "sleep", lambda s: None)
    assert testkit.FaultInjector(lab, seed=1).plan()[1] in {"api", "worker", "redis", "postgres"}, "Lỗi tạm thời của docker ps được thử lại"
    calls.clear()

    def dead(*args, timeout=60):
        calls.append(args)
        return subprocess.CompletedProcess(args, 1, "", "Cannot connect to the Docker daemon")

    monkeypatch.setattr(testkit, "_docker", dead)
    with pytest.raises(pytest.fail.Exception, match="không đọc được container của lab: Cannot connect"):
        testkit.FaultInjector(lab, seed=1).plan()
    assert len(calls) == 3

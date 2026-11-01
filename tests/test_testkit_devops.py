"""Test cho helper DevOps của testkit: phiên bản công cụ, docker, cpuset, cluster kind."""

import json
import os
import pwd
import re
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


CREDENTIAL_DIRS = (".docker", ".kube", ".aws", ".ssh", ".config/gcloud", ".azure", ".config/gh", ".terraform.d")
CREDENTIAL_FILES = (".git-credentials", ".netrc")


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
    removed = [c[3] for c in fake.calls if c[1:3] == ["rm", "-f"]]
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
    assert set(env) == {"PATH", "HOME", "LANG", "LC_ALL", "DOCKER_HOST", "DEPLOY_TOKEN"}
    assert env["DOCKER_HOST"] == "unix:///run/user/1000/docker.sock"
    assert env["DEPLOY_TOKEN"] == "sieu-bi-mat"
    home = Path(env["HOME"])
    assert home != Path.home() and home.name == "home"
    assert flag(process.args, "-s") == "DEPLOY_TOKEN", "Giá trị secret đi qua env của act, không nằm trên argv"
    assert "sieu-bi-mat" not in " ".join(process.args)
    assert ".actrc" not in process.repo_files and "app.py" in process.repo_files


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
      - run: |
          echo "token=[$(printf '%s' "$TOK" | rev)]"
          env | rev
          echo "workspace=$(ls | tr '\\n' ' ')"
          echo "da-kiem-env"
        env:
          TOK: ${{ secrets.GITHUB_TOKEN }}
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
    assert "da-kiem-env" in output and "token=[]" in output
    assert "app.py" in output
    for value in [*leaks.values(), "home-ro-ri-555", "xdg-ro-ri-666", "proj-ro-ri-777", "dotenv-ro-ri-888", "secrets-ro-ri-999"]:
        assert value not in output and value[::-1] not in output, value


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
    assert testkit._act_skipped_locally(condition)


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
    assert not testkit._act_skipped_locally(condition)


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

"""Test cho helper DevOps của testkit: phiên bản công cụ, docker, cpuset, cluster kind."""

import os
import pwd
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
        "ARG GREETING\nRUN cat /sys/fs/cgroup/cpuset.cpus.effective > /build-cpuset && cat /sys/fs/cgroup/memory.max > /build-mem "
        "&& echo \"$GREETING\" > /greeting\nLABEL org.opencontainers.image.title=olist",
    )
    with testkit.DockerLab() as lab:
        tag = lab.build(context, "api", build_args={"GREETING": "xin-chao"})
        assert tag == f"devops-ex-{lab.id}/api:test"
        labels = lab.image_inspect(tag)["Config"]["Labels"]
        assert labels["devops-ex"] == "1" and labels["devops-ex.lab"] == lab.id
        assert labels["org.opencontainers.image.title"] == "olist"
        history = lab.history(tag)
        assert isinstance(history, list) and any("GREETING" in step.get("CreatedBy", "") for step in history)
        out = lab.run_once("check", tag, "sh", "-c", "cat /build-cpuset /build-mem /greeting; grep NoNewPrivs /proc/self/status")
        lines = out.stdout.split("\n")
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
        ("    cap_add: [SYS_ADMIN]\n", "SYS_ADMIN"),
        ("    devices: ['/dev/kmsg:/dev/kmsg']\n", "devices"),
        ("    security_opt: ['seccomp=unconfined']\n", "unconfined"),
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
        ("networks:\n  default:\n    name: de-learning_default\n    external: true\n", "external"),
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


def test_compose_problems_unit(tmp_path):
    root = tmp_path / "proj"
    config = {
        "services": {
            "ok": {"image": "x", "volumes": [{"type": "bind", "source": str(root / "conf"), "target": "/c"},
                                              {"type": "volume", "source": "data", "target": "/d"}],
                   "cap_add": ["NET_BIND_SERVICE"], "network_mode": "service:other", "volumes_from": ["other"]},
            "bad": {"image": "x", "ipc": "host", "network_mode": "container:portainer", "volumes_from": ["container:portainer"],
                    "cgroup_parent": "/system.slice"},
        },
        "networks": {"default": {"name": "x_default"}},
        "volumes": {"data": {"name": "x_data"}},
    }
    problems = testkit._compose_problems(config, root)
    joined = "\n".join(problems)
    assert all("ok" not in p.split(":")[0] for p in problems), joined
    for text in ("ipc: host", "container:portainer", "cgroup_parent"):
        assert text in joined


def test_docker_lab_compose_refuses_outside_with(tmp_path):
    with pytest.raises(RuntimeError):
        testkit.DockerLab().compose(tmp_path / "compose.yaml")

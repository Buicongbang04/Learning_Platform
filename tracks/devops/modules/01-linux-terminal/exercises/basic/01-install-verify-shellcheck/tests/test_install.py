import hashlib
import platform
import re
import shutil
import subprocess
from pathlib import Path

import pytest

from testkit import Exercise, parse_version, use_solution

ex = Exercise(__file__)
MIN_VERSION = "0.9.0"
OFFICIAL_SHA256 = {
    "shellcheck-v0.11.0.linux.x86_64.tar.xz": "8c3be12b05d5c177a04c29e3c78ce89ac86f1595681cab149b65b97c4e227198",
    "shellcheck-v0.11.0.linux.aarch64.tar.xz": "12b331c1d2db6b9eb13cfca64306b1b157a86eb69db83023e261eaa7e7c14588",
    "shellcheck-v0.11.0.linux.armv6hf.tar.xz": "8afc50b302d5feeac9381ea114d563f0150d061520042b254d6eb715797c8223",
    "shellcheck-v0.11.0.linux.riscv64.tar.xz": "693c987777e7b524dd311d9b8c704885a39c889c9804bb1ef1fd29b48567b0b3",
    "shellcheck-v0.11.0.darwin.x86_64.tar.xz": "3c89db4edcab7cf1c27bff178882e0f6f27f7afdf54e859fa041fca10febe4c6",
    "shellcheck-v0.11.0.darwin.aarch64.tar.xz": "56affdd8de5527894dca6dc3d7e0a99a873b0f004d7aabc30ae407d3f48b0a79",
}
URL = re.compile(
    r"^https://github\.com/koalaman/shellcheck/releases/download/v(?P<version>\d+\.\d+\.\d+)/"
    r"(?P<file>shellcheck-v(?P=version)\.(?P<platform>(?:linux|darwin)\.[a-z0-9_]+)\.tar\.xz)$"
)
SHA_LINE = re.compile(r"^(?P<hash>[0-9a-f]{64}) [ *](?P<name>\S+)$")
PIPE_TO_SHELL = re.compile(r"\b(?:curl|wget)\b.*\|\s*(?:sudo\b(?:\s+-\S+)*\s+)?(?:ba|z|da)?sh\b")
ARCH = {"x86_64": "x86_64", "amd64": "x86_64", "aarch64": "aarch64", "arm64": "aarch64", "riscv64": "riscv64"}


@pytest.fixture(scope="module", autouse=True)
def installed():
    ex.require_tool("shellcheck", MIN_VERSION)


@pytest.fixture(scope="module")
def log() -> str:
    return ex.read("install-log.md")


def field(log: str, name: str) -> str:
    match = re.search(rf"^- {re.escape(name)}:[ \t]*(.*)$", log, re.M)
    assert match, f"install-log.md thiếu dòng '- {name}: ...'"
    value = match.group(1).strip().strip("`").strip()
    assert value and "TODO" not in value, f"Điền giá trị cho '- {name}:'"
    return value


def section(log: str, title: str) -> str:
    match = re.search(rf"^## {re.escape(title)}[ \t]*$(.*?)(?=^## |\Z)", log, re.M | re.S)
    assert match, f"install-log.md thiếu phần '## {title}'"
    return match.group(1)


def this_platform() -> str:
    machine = platform.machine().lower()
    arch = "armv6hf" if machine.startswith("armv") else ARCH.get(machine, machine)
    return f"{platform.system().lower()}.{arch}"


def installed_version() -> str:
    out = subprocess.run(["shellcheck", "--version"], capture_output=True, text=True, timeout=10).stdout
    match = re.search(r"^version:\s*(\S+)", out, re.M)
    assert match, out
    return match.group(1)


def sha256_entries() -> dict[str, str]:
    entries = {}
    for line in ex.read("shellcheck.sha256").splitlines():
        if not line.strip():
            continue
        match = SHA_LINE.match(line.strip())
        assert match, f"Dòng không đúng định dạng sha256sum ('<64 ký tự hex>  <tên tệp>'): {line!r}"
        entries[match.group("name")] = match.group("hash")
    return entries


def logged_url(log: str) -> re.Match:
    url = field(log, "URL tải")
    match = URL.match(url)
    assert match, (
        "URL tải phải là tarball .tar.xz của release chính thức: "
        "https://github.com/koalaman/shellcheck/releases/download/vX.Y.Z/shellcheck-vX.Y.Z.<os>.<arch>.tar.xz"
    )
    return match


def test_no_todo_left(log):
    assert "TODO" not in log
    assert "TODO" not in ex.read("shellcheck.sha256")


def test_version_matches_installed_binary(log):
    version = field(log, "Phiên bản").lstrip("v")
    have = parse_version(version)
    assert have and have >= parse_version(MIN_VERSION), f"Cần shellcheck >= {MIN_VERSION}, log ghi {version!r}"
    if not use_solution():
        assert version == installed_version(), "Phiên bản ghi trong log khác bản `shellcheck --version` đang chạy"


def test_installed_in_user_space(log):
    logged = Path(field(log, "Đường dẫn cài").replace("$HOME", str(Path.home())).replace("~", str(Path.home()), 1))
    assert logged.name == "shellcheck"
    assert logged.parent.as_posix().endswith(".local/bin"), "Cài vào ~/.local/bin, không cần sudo"
    if not use_solution():
        found = Path(shutil.which("shellcheck"))
        assert logged.resolve() == found.resolve(), f"`which shellcheck` đang trả {found}, không phải {logged}"
        assert found.resolve().is_relative_to(Path.home().resolve()), "Bản đang chạy không nằm trong thư mục home"


def test_url_is_official_release_for_this_platform(log):
    match = logged_url(log)
    assert match.group("version") == field(log, "Phiên bản").lstrip("v")
    assert match.group("platform") == field(log, "Nền tảng"), "Nền tảng ghi trong log khác tên tệp trong URL"
    if not use_solution():
        assert match.group("platform") == this_platform(), f"Máy này là {this_platform()}, tải nhầm bản"


def test_tarball_checksum_is_official(log):
    tarball = logged_url(log).group("file")
    entries = sha256_entries()
    assert tarball in entries, f"shellcheck.sha256 thiếu dòng cho {tarball}"
    if tarball in OFFICIAL_SHA256:
        assert entries[tarball] == OFFICIAL_SHA256[tarball], "Hash tarball khác hash đã ghim của release chính thức"


def test_binary_checksum_matches_installed(log):
    entries = sha256_entries()
    assert "shellcheck" in entries, "shellcheck.sha256 thiếu dòng '<hash>  shellcheck' của binary đã cài"
    if use_solution():
        match = logged_url(log)
        if match.group("version") != installed_version() or match.group("platform") != this_platform():
            pytest.skip(f"Lời giải mẫu ghi cho {match.group('file')}, máy này cài bản khác")
    binary = Path(shutil.which("shellcheck")).resolve()
    assert entries["shellcheck"] == hashlib.sha256(binary.read_bytes()).hexdigest(), (
        f"Hash binary trong shellcheck.sha256 khác {binary}: bạn đã cài một tệp khác tệp đã kiểm"
    )


def test_checksum_was_verified_before_install(log):
    commands = section(log, "Lệnh đã chạy")
    tarball = logged_url(log).group("file")
    commands = commands.replace("\\\n", " ")
    verify = re.search(r"sha256sum\s+(?:--\S+\s+)*-c|shasum\s+-a\s*256\s+(?:--\S+\s+)*-c", commands)
    install = re.search(r"(?:^|&&|;)\s*(?:install|cp|mv)\s.*shellcheck", commands, re.M)
    assert verify, "Phần 'Lệnh đã chạy' phải có bước kiểm `sha256sum -c` (hoặc `shasum -a 256 -c`)"
    assert install, "Phần 'Lệnh đã chạy' phải có bước chép binary vào ~/.local/bin"
    assert verify.start() < install.start(), "Kiểm checksum phải đứng trước bước cài"
    assert re.search(rf"^{re.escape(tarball)}: OK$", section(log, "Kết quả kiểm checksum"), re.M), (
        f"Dán output của bước kiểm checksum, phải có dòng '{tarball}: OK'"
    )


def test_version_output_pasted(log):
    output = section(log, "Kết quả xác nhận")
    version = field(log, "Phiên bản").lstrip("v")
    assert "ShellCheck - shell script analysis tool" in output
    assert re.search(rf"^version: {re.escape(version)}$", output, re.M)


def test_no_pipe_to_shell_and_no_sudo(log):
    joined = log.replace("\\\n", " ")
    bad = [line for line in joined.splitlines() if PIPE_TO_SHELL.search(line)]
    assert not bad, f"Không cài bằng cách pipe script tải về vào shell: {bad}"
    sudo = [line for line in section(log, "Lệnh đã chạy").splitlines() if re.search(r"(^|[\s;&|(])sudo\b", line)]
    assert not sudo, f"Cài vào ~/.local/bin không cần sudo: {sudo}"


def test_uninstall_documented(log):
    steps = section(log, "Cách gỡ")
    assert re.search(r"\brm\b.*shellcheck", steps), "Ghi lệnh gỡ: xoá binary đã cài"

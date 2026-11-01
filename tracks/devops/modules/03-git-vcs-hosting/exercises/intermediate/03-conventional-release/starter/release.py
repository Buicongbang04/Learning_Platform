"""Tính phiên bản kế tiếp và changelog từ Conventional Commits. Chạy trong gốc repo: python release.py"""

from __future__ import annotations

import subprocess
import sys
from dataclasses import dataclass

SECTIONS = [("breaking", "BREAKING CHANGES"), ("feat", "Features"), ("fix", "Bug Fixes"), ("perf", "Performance")]


@dataclass
class Commit:
    sha: str
    type: str
    scope: str | None
    description: str
    breaking: bool


def git(*args: str) -> str:
    return subprocess.run(["git", *args], capture_output=True, text=True, check=True).stdout


def parse(sha: str, message: str) -> Commit | None:
    # TODO 1: header "<type>[(<scope>)][!]: <description>", type không phân biệt hoa thường;
    #         footer "BREAKING CHANGE: " hoặc "BREAKING-CHANGE: " ở đầu một dòng sau header (chữ hoa);
    #         sai định dạng -> None
    raise NotImplementedError


def latest_version() -> tuple[str, tuple[int, int, int]]:
    # TODO 2: tag dạng vX.Y.Z (không hậu tố) reachable từ HEAD, lấy bản cao nhất theo semver; không có -> v0.0.0
    raise NotImplementedError


def commits_since(tag: str | None) -> list[Commit]:
    # TODO 3: commit trong <tag>..HEAD (hoặc mọi commit nếu chưa có tag), bỏ merge commit, thứ tự git log;
    #         đọc message đầy đủ an toàn (phân tách bằng NUL)
    raise NotImplementedError


def next_version(current: tuple[int, int, int], commits: list[Commit]) -> tuple[int, int, int] | None:
    # TODO 4: breaking -> major (major 0 thì minor), feat -> minor, fix/perf -> patch, còn lại -> None
    raise NotImplementedError


def render(version: tuple[int, int, int], commits: list[Commit]) -> str:
    # TODO 5: "## vX.Y.Z", các mục theo SECTIONS, mỗi dòng "- [scope: ]description (sha7)"
    raise NotImplementedError


def main() -> int:
    # TODO 6: không phải repo git -> stderr, exit 1, không traceback; không có gì để release -> in "no release"
    raise NotImplementedError


if __name__ == "__main__":
    sys.exit(main())

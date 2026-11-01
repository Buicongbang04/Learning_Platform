"""Tính phiên bản kế tiếp và changelog từ Conventional Commits. Chạy trong gốc repo: python release.py"""

from __future__ import annotations

import re
import subprocess
import sys
from dataclasses import dataclass

SECTIONS = [("breaking", "BREAKING CHANGES"), ("feat", "Features"), ("fix", "Bug Fixes"), ("perf", "Performance")]
HEADER = re.compile(r"^(?P<type>[A-Za-z]+)(?:\((?P<scope>[^()\r\n]+)\))?(?P<bang>!)?: (?P<description>\S.*)$")
FOOTER = re.compile(r"^BREAKING[ -]CHANGE: (?P<text>\S.*)$", re.M)
SEMVER_TAG = re.compile(r"^v(\d+)\.(\d+)\.(\d+)$")


@dataclass
class Commit:
    sha: str
    type: str
    scope: str | None
    description: str
    breaking: bool


class GitError(Exception):
    pass


def git(*args: str) -> str:
    result = subprocess.run(["git", *args], capture_output=True, text=True)
    if result.returncode != 0:
        raise GitError(result.stderr.strip() or f"git {' '.join(args)} lỗi {result.returncode}")
    return result.stdout


def parse(sha: str, message: str) -> Commit | None:
    header, _, body = message.strip("\n").partition("\n")
    match = HEADER.match(header.strip())
    if not match:
        return None
    footer = FOOTER.search(body)
    description = footer.group("text").strip() if footer else match.group("description").strip()
    return Commit(
        sha=sha,
        type=match.group("type").lower(),
        scope=match.group("scope"),
        description=description,
        breaking=bool(match.group("bang") or footer),
    )


def latest_version() -> tuple[str | None, tuple[int, int, int]]:
    versions = []
    for tag in git("tag", "--merged", "HEAD").split():
        match = SEMVER_TAG.match(tag)
        if match:
            versions.append((tuple(int(part) for part in match.groups()), tag))
    if not versions:
        return None, (0, 0, 0)
    version, tag = max(versions)
    return tag, version


def commits_since(tag: str | None) -> list[Commit]:
    revision = f"{tag}..HEAD" if tag else "HEAD"
    raw = git("log", "--no-merges", "--format=%H%x00%B%x00", revision)
    fields = raw.split("\x00")
    commits = []
    for sha, message in zip(fields[0::2], fields[1::2]):
        commit = parse(sha.strip()[:7], message)
        if commit:
            commits.append(commit)
        else:
            print(f"skipped {sha.strip()[:7]} {message.strip().splitlines()[0] if message.strip() else ''}", file=sys.stderr)
    return commits


def next_version(current: tuple[int, int, int], commits: list[Commit]) -> tuple[int, int, int] | None:
    major, minor, patch = current
    if any(c.breaking for c in commits):
        return (major, minor + 1, 0) if major == 0 else (major + 1, 0, 0)
    if any(c.type == "feat" for c in commits):
        return (major, minor + 1, 0)
    if any(c.type in ("fix", "perf") for c in commits):
        return (major, minor, patch + 1)
    return None


def section_of(commit: Commit) -> str | None:
    if commit.breaking:
        return "breaking"
    return commit.type if commit.type in ("feat", "fix", "perf") else None


def render(version: tuple[int, int, int], commits: list[Commit]) -> str:
    blocks = ["## v{}.{}.{}".format(*version)]
    for key, title in SECTIONS:
        entries = [
            f"- {c.scope + ': ' if c.scope else ''}{c.description} ({c.sha})" for c in commits if section_of(c) == key
        ]
        if entries:
            blocks.append(f"### {title}\n" + "\n".join(entries))
    return "\n\n".join(blocks) + "\n"


def main() -> int:
    try:
        git("rev-parse", "--verify", "--quiet", "HEAD")
        tag, current = latest_version()
        commits = commits_since(tag)
    except GitError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    except OSError as exc:
        print(f"error: không chạy được git: {exc}", file=sys.stderr)
        return 1
    version = next_version(current, commits)
    if version is None:
        print("no release")
        return 0
    sys.stdout.write(render(version, commits))
    return 0


if __name__ == "__main__":
    sys.exit(main())

import shutil
import sys
from pathlib import Path

import pytest

from testkit import Exercise, GitRepo, git_env, run_sandboxed

ex = Exercise(__file__)
pytestmark = pytest.mark.skipif(shutil.which("git") is None, reason="Cần git")


@pytest.fixture(autouse=True)
def git_version():
    ex.require_tool("git", min_version="2.30")



class Repo:
    def __init__(self, tmp_path: Path):
        self.tmp = tmp_path
        self.home = tmp_path / "home"
        self.home.mkdir()
        self.path = tmp_path / "olist-shop"
        self.path.mkdir()
        self.counter = 0
        self.repo = GitRepo(self.path, self.home, writable=[tmp_path])
        self.git("init", "-q")

    def git(self, *args: str, check: bool = True) -> str:
        return self.repo.out("-c", "tag.gpgsign=false", *args, check=check)

    def commit(self, message: str, name: str = "CHANGES.txt") -> str:
        self.counter += 1
        (self.path / name).write_text(f"{self.counter}\n")
        self.git("add", name)
        self.git("commit", "-q", "-m", message)
        return self.git("rev-parse", "HEAD")[:7]

    def tag(self, name: str, ref: str = "HEAD") -> None:
        self.git("tag", name, ref)

    def release(self, cwd: Path | None = None):
        self.repo.taint()
        return run_sandboxed(
            [sys.executable, ex.path("release.py")], writable=[self.tmp], cwd=cwd or self.path, env=git_env(self.home), timeout=30
        )


def notes(version: str, sections: list[tuple[str, list[str]]]) -> str:
    blocks = [f"## {version}"] + [f"### {title}\n" + "\n".join(entries) for title, entries in sections if entries]
    return "\n\n".join(blocks) + "\n"


def assert_output(result, expected: str) -> None:
    assert result.returncode == 0, result.stderr
    assert "Traceback" not in result.stderr, result.stderr
    assert result.stdout.rstrip() == expected.rstrip(), f"\n--- nhận ---\n{result.stdout}\n--- cần ---\n{expected}"


@pytest.fixture
def repo(tmp_path):
    repo = Repo(tmp_path)
    repo.commit("feat: initial shop")
    return repo


def test_minor_bump_with_features_and_fixes(repo):
    repo.tag("v1.4.2")
    fix = repo.commit("fix(shipping): round fee to 2 decimals")
    repo.commit("docs: explain refunds")
    feat = repo.commit("feat(payments): add Pix")
    repo.commit("chore(deps): bump httpx")
    expected = notes("v1.5.0", [("Features", [f"- payments: add Pix ({feat})"]), ("Bug Fixes", [f"- shipping: round fee to 2 decimals ({fix})"])])
    assert_output(repo.release(), expected)


def test_patch_bump_fix_and_perf(repo):
    repo.tag("v1.4.2")
    fix = repo.commit("fix: handle empty cart")
    perf = repo.commit("perf(orders): index customer_id lookups")
    expected = notes("v1.4.3", [("Bug Fixes", [f"- handle empty cart ({fix})"]), ("Performance", [f"- orders: index customer_id lookups ({perf})"])])
    assert_output(repo.release(), expected)


def test_breaking_with_bang(repo):
    repo.tag("v1.4.2")
    feat = repo.commit("feat(payments): add boleto")
    breaking = repo.commit("feat(api)!: drop /v1/orders endpoint")
    expected = notes("v2.0.0", [("BREAKING CHANGES", [f"- api: drop /v1/orders endpoint ({breaking})"]), ("Features", [f"- payments: add boleto ({feat})"])])
    assert_output(repo.release(), expected)


def test_breaking_with_footer(repo):
    repo.tag("v1.4.2")
    breaking = repo.commit("refactor(db): rename status column\n\nMigration 0042 renames the column.\n\nBREAKING CHANGE: orders.status is now orders.state")
    hyphen = repo.commit("chore: drop python 3.10\n\nBREAKING-CHANGE: python 3.11 is required")
    expected = notes(
        "v2.0.0",
        [("BREAKING CHANGES", [f"- python 3.11 is required ({hyphen})", f"- db: orders.status is now orders.state ({breaking})"])],
    )
    assert_output(repo.release(), expected)


def test_major_zero_breaking_bumps_minor(repo):
    repo.tag("v0.9.1")
    breaking = repo.commit("feat!: new checkout flow")
    expected = notes("v0.10.0", [("BREAKING CHANGES", [f"- new checkout flow ({breaking})"])])
    assert_output(repo.release(), expected)


def test_no_release(repo):
    repo.tag("v1.4.2")
    repo.commit("docs: readme")
    repo.commit("ci: cache uv")
    repo.commit("chore: tidy")
    result = repo.release()
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "no release"


def test_no_tag_starts_from_zero(tmp_path):
    repo = Repo(tmp_path)
    first = repo.commit("feat: initial shop")
    second = repo.commit("feat(orders): list orders")
    expected = notes("v0.1.0", [("Features", [f"- orders: list orders ({second})", f"- initial shop ({first})"])])
    assert_output(repo.release(), expected)


def test_picks_highest_plain_semver_tag_reachable_from_head(repo):
    repo.tag("v1.9.0")
    repo.commit("fix: one")
    repo.tag("v1.10.0")
    repo.git("switch", "-q", "-c", "experiment")
    repo.commit("feat: experiment")
    repo.tag("v3.0.0")
    repo.git("switch", "-q", "main")
    repo.tag("release-2026-07")
    fix = repo.commit("fix(cart): keep coupon after login")
    repo.tag("v2.0.0-rc.1")
    expected = notes("v1.10.1", [("Bug Fixes", [f"- cart: keep coupon after login ({fix})"])])
    assert_output(repo.release(), expected)


def test_rc_tag_is_what_describe_would_pick(repo):
    """Chứng minh ca trên phân biệt được: `git describe --abbrev=0` trả tag rc, sắp xếp chữ trả v1.9.0."""
    repo.tag("v1.9.0")
    repo.commit("fix: one")
    repo.tag("v1.10.0")
    repo.commit("fix: two")
    repo.tag("v2.0.0-rc.1")
    assert repo.git("describe", "--tags", "--abbrev=0") == "v2.0.0-rc.1"
    assert sorted(["v1.9.0", "v1.10.0"])[-1] == "v1.9.0"


def test_parsing_rules(repo):
    repo.tag("v1.0.0")
    upper = repo.commit("Feat: Add search")
    repo.commit("feat : bad spacing")
    repo.commit("fixup! feat: add search")
    repo.commit("WIP")
    repo.commit("docs: note\n\nThis is not a BREAKING CHANGE: it is mid-line.")
    repo.commit("docs: lower\n\nbreaking change: lowercase does not count")
    scoped = repo.commit("FIX(order-api): accept ISO dates")
    expected = notes("v1.1.0", [("Features", [f"- Add search ({upper})"]), ("Bug Fixes", [f"- order-api: accept ISO dates ({scoped})"])])
    assert_output(repo.release(), expected)


def test_merge_commits_ignored(repo):
    repo.tag("v1.0.0")
    repo.git("switch", "-q", "-c", "feature/x")
    feat = repo.commit("feat(x): new thing")
    repo.git("switch", "-q", "main")
    repo.commit("docs: unrelated", "docs.txt")
    repo.git("merge", "-q", "--no-ff", "-m", "fix: merge pull request #7", "feature/x")
    expected = notes("v1.1.0", [("Features", [f"- x: new thing ({feat})"])])
    assert_output(repo.release(), expected)


def test_not_a_repository(tmp_path):
    repo = Repo(tmp_path)
    outside = tmp_path / "not-a-repo"
    outside.mkdir()
    result = repo.release(cwd=outside)
    assert result.returncode == 1, result.stdout + result.stderr
    assert result.stderr.strip()
    assert "Traceback" not in result.stderr
    assert result.stdout == ""

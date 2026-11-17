import re
import subprocess
from pathlib import Path

import httpx
import pytest

from testkit import REGISTRY_MANIFEST_TYPES, SAFE_GIT_CONFIG, DockerLab, Exercise, GitRepo, git_env, run_sandboxed

ex = Exercise(__file__)
FIXTURES = Path(__file__).parent / "fixtures"
SCRIPT = "ci/image-tags.sh"
PROMOTE = "ci/promote.sh"
DOCKER_TAG = re.compile(r"^[A-Za-z0-9_][A-Za-z0-9_.-]{0,127}$")


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
        self.repo = GitRepo(self.path, self.home, writable=[tmp_path])
        self.counter = 0
        self.git("init", "-q")

    def git(self, *args: str) -> str:
        return self.repo.out("-c", "tag.gpgsign=false", *args)

    def commit(self, date: str | None = None) -> str:
        self.counter += 1
        (self.path / "VERSION.txt").write_text(f"{self.counter}\n", encoding="utf-8")
        self.git("add", "VERSION.txt")
        if date:
            result = subprocess.run(["git", *SAFE_GIT_CONFIG, "commit", "-q", "-m", f"thay đổi {self.counter}"], cwd=self.path,
                                    env=git_env(self.home, date=date), capture_output=True, text=True, timeout=30)
            assert result.returncode == 0, result.stderr
        else:
            self.git("commit", "-q", "-m", f"thay đổi {self.counter}")
        return self.git("rev-parse", "HEAD")

    def tags(self, ref: str | None):
        self.repo.taint()
        env = git_env(self.home)
        if ref is not None:
            env["GITHUB_REF"] = ref
        return run_sandboxed(["bash", str(ex.path(SCRIPT))], writable=[self.tmp], cwd=self.path, env=env, timeout=30)


@pytest.fixture
def repo(tmp_path):
    return Repo(tmp_path)


def lines(result) -> list[str]:
    assert result.returncode == 0, f"Script thoát mã {result.returncode}: {result.stderr.strip()}"
    found = result.stdout.split()
    for tag in found:
        assert DOCKER_TAG.match(tag), f"{tag!r} không phải tag Docker hợp lệ"
        assert tag != "latest", "Không bao giờ in latest"
    return found


def refused(result, code: int) -> None:
    assert result.returncode == code, f"Cần thoát mã {code}, nhận {result.returncode} (stdout {result.stdout!r})"
    assert result.stdout.strip() == "", f"Khi từ chối, stdout phải rỗng để CI không dùng nhầm tag: {result.stdout!r}"
    assert result.stderr.strip(), "Khi từ chối, phải in lý do ra stderr"


def test_main_uses_commit_time_in_utc(repo):
    sha = repo.commit(date="2026-05-01T17:30:00+07:00")
    assert lines(repo.tags("refs/heads/main")) == [f"sha-{sha[:12]}", f"main-20260501103000-{sha[:12]}"]


def test_feature_branch_is_slugged(repo):
    sha = repo.commit()
    assert lines(repo.tags("refs/heads/Feature/Pix_Payments")) == [f"sha-{sha[:12]}", f"br-feature-pix-payments-{sha[:12]}"]


def test_long_branch_is_truncated(repo):
    sha = repo.commit()
    branch = "fix/" + "checkout-" * 5 + "timeout--when--cart--is--empty"
    slug = "fix-checkout-checkout-checkout-checkout"
    assert lines(repo.tags(f"refs/heads/{branch}")) == [f"sha-{sha[:12]}", f"br-{slug}-{sha[:12]}"]


def test_release_tag(repo):
    repo.commit()
    sha = repo.commit()
    repo.git("tag", "v1.4.2")
    assert lines(repo.tags("refs/tags/v1.4.2")) == [f"sha-{sha[:12]}", "1.4.2"]


def test_prerelease_tag(repo):
    sha = repo.commit()
    repo.git("tag", "-a", "-m", "rc", "v2.0.0-rc.1")
    assert lines(repo.tags("refs/tags/v2.0.0-rc.1")) == [f"sha-{sha[:12]}", "2.0.0-rc.1"]


def test_pull_request(repo):
    sha = repo.commit()
    assert lines(repo.tags("refs/pull/42/merge")) == [f"sha-{sha[:12]}", f"pr-42-{sha[:12]}"]


def test_tag_not_at_head_is_refused(repo):
    repo.commit()
    repo.git("tag", "v1.4.2")
    repo.commit()
    refused(repo.tags("refs/tags/v1.4.2"), 4)


@pytest.mark.parametrize("tag", ["v1.4", "1.4.2", "v1.4.2.1", "v01.4.2"])
def test_invalid_version_is_refused(repo, tag):
    repo.commit()
    repo.git("tag", tag)
    refused(repo.tags(f"refs/tags/{tag}"), 4)


def test_dirty_tracked_file_is_refused(repo):
    repo.commit()
    (repo.path / "VERSION.txt").write_text("sửa tay\n", encoding="utf-8")
    refused(repo.tags("refs/heads/main"), 3)


def test_untracked_file_is_refused(repo):
    repo.commit()
    (repo.path / "debug.log").write_text("x\n", encoding="utf-8")
    refused(repo.tags("refs/heads/main"), 3)


@pytest.mark.parametrize("ref", [None, "", "refs/remotes/origin/main", "main"])
def test_unknown_ref_is_refused(repo, ref):
    repo.commit()
    refused(repo.tags(ref), 2)


def registry_digest(client: httpx.Client, address: str, repo: str, tag: str) -> str | None:
    response = client.head(f"http://{address}/v2/{repo}/manifests/{tag}", headers={"Accept": ", ".join(REGISTRY_MANIFEST_TYPES)})
    return response.headers.get("docker-content-digest") if response.status_code == 200 else None


def promote(tmp_path: Path, address: str, repo: str, source: str, target: str):
    ex.require_tool("curl")
    return run_sandboxed(["bash", str(ex.path(PROMOTE)), address, repo, source, target], writable=[tmp_path], cwd=tmp_path,
                         env={}, timeout=60)


@pytest.fixture
def registry(tmp_path):
    ex.require_registry()
    ex.require_image("python:3.12.16-alpine3.24")
    with DockerLab() as lab, httpx.Client(trust_env=False, timeout=10) as client:
        yield lab, client


def push_tiny(lab: DockerLab, tag: str, variant: str = "a") -> tuple[str, str]:
    image = lab.build(FIXTURES / "tiny", f"tiny-{variant}", build_args={"VARIANT": variant})
    ref = lab.push(image, "olist-api", tag=tag)
    address, rest = ref.split("/", 1)
    return address, rest.rsplit(":", 1)[0]


def test_promotion_is_a_registry_side_retag(repo, registry, tmp_path):
    lab, client = registry
    repo.commit()
    main_tags = lines(repo.tags("refs/heads/main"))
    repo.git("tag", "v1.5.0")
    release = lines(repo.tags("refs/tags/v1.5.0"))
    assert main_tags[0] == release[0], "Cùng một commit phải có cùng tag sha-..."
    address, name = push_tiny(lab, release[0])
    built = registry_digest(client, address, name, release[0])
    assert registry_digest(client, address, name, release[1]) is None
    result = promote(tmp_path, address, name, release[0], release[1])
    assert result.returncode == 0, f"promote.sh thoát mã {result.returncode}: {result.stderr.strip()}"
    assert registry_digest(client, address, name, release[1]) == built, "Tag phát hành phải trỏ đúng digest đã build"
    assert result.stdout.split()[-1:] == [built], f"promote.sh phải in digest ở dòng cuối, nhận {result.stdout!r}"
    again = promote(tmp_path, address, name, release[0], release[1])
    assert again.returncode == 0 and again.stdout.split()[-1:] == [built], "Gắn lại cùng digest phải thành công (idempotent)"


def test_promotion_refuses_to_move_a_release_tag(registry, tmp_path):
    lab, client = registry
    address, name = push_tiny(lab, "sha-0123456789ab", "a")
    push_tiny(lab, "1.5.0", "b")
    before = registry_digest(client, address, name, "1.5.0")
    assert before and before != registry_digest(client, address, name, "sha-0123456789ab")
    result = promote(tmp_path, address, name, "sha-0123456789ab", "1.5.0")
    refused(result, 5)
    assert registry_digest(client, address, name, "1.5.0") == before, "Tag phát hành đã bị dời"


def test_promotion_of_missing_source_is_refused(registry, tmp_path):
    lab, _ = registry
    address, name = push_tiny(lab, "sha-0123456789ab")
    refused(promote(tmp_path, address, name, "sha-ffffffffffff", "1.5.0"), 4)


def test_scripts_pass_shellcheck(tmp_path):
    ex.require_tool("shellcheck")
    scripts = [str(ex.path(SCRIPT)), str(ex.path(PROMOTE))]
    result = run_sandboxed(["shellcheck", *scripts], writable=[tmp_path], cwd=tmp_path, env={}, timeout=60)
    assert result.returncode == 0, f"shellcheck báo lỗi:\n{result.stdout}{result.stderr}"

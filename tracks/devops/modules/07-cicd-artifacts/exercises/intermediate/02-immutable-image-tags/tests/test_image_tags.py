import re
import subprocess
from pathlib import Path

import httpx
import pytest

from testkit import REGISTRY_MANIFEST_TYPES, SAFE_GIT_CONFIG, DockerLab, Exercise, GitRepo, git_env, run_sandboxed

ex = Exercise(__file__)
FIXTURES = Path(__file__).parent / "fixtures"
SCRIPT = "ci/image-tags.sh"
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


def registry_digest(client: httpx.Client, ref: str) -> str:
    address, rest = ref.split("/", 1)
    repo, tag = rest.rsplit(":", 1)
    response = client.head(f"http://{address}/v2/{repo}/manifests/{tag}", headers={"Accept": ", ".join(REGISTRY_MANIFEST_TYPES)})
    assert response.status_code == 200, f"Registry không có {ref} (HTTP {response.status_code})"
    return response.headers.get("docker-content-digest", "")


def test_promotion_is_a_retag_with_same_digest(repo):
    repo.commit()
    main_tags = lines(repo.tags("refs/heads/main"))
    repo.git("tag", "v1.5.0")
    release_tags = lines(repo.tags("refs/tags/v1.5.0"))
    assert main_tags[0] == release_tags[0], "Cùng một commit phải có cùng tag sha-..."
    ex.require_registry()
    ex.require_image("python:3.12.16-alpine3.24")
    with DockerLab() as lab:
        image = lab.build(FIXTURES / "tiny", "olist-api")
        with httpx.Client(trust_env=False, timeout=10) as client:
            digests = {tag: registry_digest(client, lab.push(image, "olist-api", tag=tag)) for tag in [*main_tags, *release_tags]}
    assert len(set(digests.values())) == 1 and re.fullmatch(r"sha256:[0-9a-f]{64}", next(iter(digests.values()))), digests

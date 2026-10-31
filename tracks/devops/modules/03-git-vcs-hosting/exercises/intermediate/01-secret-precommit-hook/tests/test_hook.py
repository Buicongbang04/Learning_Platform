import os
import shutil
import subprocess
from pathlib import Path

import pytest

from testkit import Exercise, run_sandboxed

ex = Exercise(__file__)
NAIVE = Path(__file__).parent / "fixtures" / "naive-pre-commit"
pytestmark = pytest.mark.skipif(shutil.which("bash") is None or shutil.which("git") is None, reason="Cần bash và git")

AWS_KEY = "AKIA2OLISTSHOP7Q3XYZ"
STS_KEY = "ASIAQ4OLIST5SESSION1"
FIXTURE_KEY = "AKIAQ7FAKEFIXTURE001"


def pem(kind: str) -> str:
    label = f"{kind} PRIVATE KEY" if kind else "PRIVATE KEY"
    return f"-----BEGIN {label}-----\nMIIEowIBAAKCAQEAolist0nly4test\n-----END {label}-----\n"


def git_env(home: Path) -> dict[str, str]:
    return {
        "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
        "HOME": str(home),
        "GIT_CONFIG_GLOBAL": "/dev/null",
        "GIT_CONFIG_SYSTEM": "/dev/null",
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_AUTHOR_NAME": "Olist Dev",
        "GIT_AUTHOR_EMAIL": "dev@olist-shop.example",
        "GIT_COMMITTER_NAME": "Olist Dev",
        "GIT_COMMITTER_EMAIL": "dev@olist-shop.example",
        "GIT_AUTHOR_DATE": "2026-05-01T10:00:00+00:00",
        "GIT_COMMITTER_DATE": "2026-05-01T10:00:00+00:00",
        "GIT_TERMINAL_PROMPT": "0",
        "LANG": "C.UTF-8",
        "LC_ALL": "C.UTF-8",
    }


class Repo:
    def __init__(self, tmp_path: Path, hook: Path, initial: bool = True):
        self.tmp = tmp_path
        self.home = tmp_path / "home"
        self.home.mkdir(parents=True)
        self.path = tmp_path / "olist-shop"
        self.path.mkdir()
        self.git("init", "-q")
        if initial:
            self.write("README.md", "# Olist Shop\n")
            self.git("add", "README.md")
            self.git("commit", "-q", "-m", "chore: init")
        target = self.path / ".git" / "hooks" / "pre-commit"
        shutil.copyfile(hook, target)
        target.chmod(0o755)

    def git(self, *args: str, check: bool = True) -> str:
        result = subprocess.run(
            ["git", "-c", "init.defaultBranch=main", "-c", "commit.gpgsign=false", *args],
            cwd=self.path, env=git_env(self.home), capture_output=True, text=True, check=check,
        )
        return result.stdout.strip()

    def write(self, name: str, content: str) -> None:
        target = self.path / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content)

    def stage(self, files: dict[str, str]) -> None:
        for name, content in files.items():
            self.write(name, content)
            self.git("add", "--", name)

    def head(self) -> str:
        return self.git("rev-parse", "--verify", "--quiet", "HEAD", check=False)

    def commit(self):
        return run_sandboxed(
            ["git", "-c", "commit.gpgsign=false", "commit", "-q", "-m", "feat: change"],
            writable=[self.tmp], cwd=self.path, env=git_env(self.home), timeout=30,
        )


def assert_blocked(repo: Repo, result, findings: list[str]) -> None:
    assert result.returncode != 0, f"Hook phải chặn commit này\n{result.stderr}"
    lines = result.stderr.splitlines()
    for finding in findings:
        assert finding in lines, f"stderr thiếu dòng '{finding}'. stderr:\n{result.stderr}"


def assert_allowed(repo: Repo, before: str, result) -> None:
    assert result.returncode == 0, f"Hook chặn nhầm (false positive):\n{result.stderr}"
    assert repo.head() != before


BLOCK = {
    "aws-key": ({"config/settings.py": f'AWS_ACCESS_KEY_ID = "{AWS_KEY}"\n'}, "aws-access-key-id", "config/settings.py"),
    "sts-key": ({"deploy/env.sh": f"export AWS_ACCESS_KEY_ID={STS_KEY}\n"}, "aws-access-key-id", "deploy/env.sh"),
    "rsa-key": ({"deploy/keys/id_rsa": pem("RSA")}, "private-key", "deploy/keys/id_rsa"),
    "openssh-key": ({"ops/ssh/deploy_key": pem("OPENSSH")}, "private-key", "ops/ssh/deploy_key"),
    "pkcs8-key": ({"certs/server.key": pem("")}, "private-key", "certs/server.key"),
    "ec-key-in-yaml": (
        {"k8s/tls.yaml": "stringData:\n  tls.key: |\n" + "".join(f"    {line}\n" for line in pem("EC").splitlines())},
        "private-key",
        "k8s/tls.yaml",
    ),
    "postgresql-url": (
        {"services/api/settings.py": 'DATABASE_URL = "postgresql://olist:S3cr3t!@db.internal:5432/olist"\n'},
        "postgres-password-url",
        "services/api/settings.py",
    ),
    "postgres-url": (
        {"docker-compose.override.yml": "environment:\n  DATABASE_URL: postgres://admin:hunter2@localhost/olist\n"},
        "postgres-password-url",
        "docker-compose.override.yml",
    ),
    "dotenv": ({".env": "DEBUG=1\n"}, "dotenv-file", ".env"),
    "dotenv-nested": ({"services/api/.env.production": "LOG_LEVEL=info\n"}, "dotenv-file", "services/api/.env.production"),
    "space-in-name": ({"infra/old notes.txt": f"key {AWS_KEY}\n"}, "aws-access-key-id", "infra/old notes.txt"),
}


@pytest.mark.parametrize("case", list(BLOCK))
def test_blocks_secret(tmp_path, case):
    files, rule, path = BLOCK[case]
    repo = Repo(tmp_path, ex.path("pre-commit"))
    before = repo.head()
    repo.stage({"api/orders.py": "def list_orders():\n    return []\n", **files})
    result = repo.commit()
    assert_blocked(repo, result, [f"secret: {rule}: {path}"])
    assert repo.head() == before, "HEAD không được đổi khi bị chặn"
    assert path in repo.git("diff", "--cached", "--name-only"), "Hook không được unstage tệp của người dùng"


ALLOW = {
    "clean-code": {"api/orders.py": "def total(items):\n    return sum(i.price for i in items)\n"},
    "aws-doc-example": {"docs/aws.md": "Ví dụ trong tài liệu AWS: AKIAIOSFODNN7EXAMPLE\n"},
    "akia-in-prose": {"docs/iam.md": "Key bắt đầu bằng AKIA là long-term, ASIA là tạm thời. AKIA1234 quá ngắn.\n"},
    "public-key-and-cert": {
        "certs/ca.pem": "-----BEGIN CERTIFICATE-----\nMIIB\n-----END CERTIFICATE-----\n-----BEGIN PUBLIC KEY-----\nMIIB\n-----END PUBLIC KEY-----\n"
    },
    "key-name-in-docs": {"docs/runbook.md": "Tìm dòng BEGIN RSA PRIVATE KEY trong log rồi báo security.\n"},
    "postgres-no-password": {"services/api/settings.py": 'DATABASE_URL = "postgresql://olist@db:5432/olist"\n'},
    "postgres-env-placeholders": {
        "deploy/compose.yml": "url: postgresql://${PGUSER}:${PGPASSWORD}@db/olist\nalt: postgres://$DB_USER:$DB_PASS@db/olist\n"
    },
    "postgres-angle-placeholder": {"docs/db.md": "postgresql://olist:<password>@db.internal:5432/olist\n"},
    "dotenv-example": {".env.example": "DATABASE_URL=postgresql://olist:<password>@db/olist\n", ".env.sample": "A=1\n", ".env.template": "B=2\n"},
    "env-like-names": {"docs/env.md": "Biến môi trường\n", "config/environment.py": "ENV = 'dev'\n"},
    "pragma": {"tests/test_iam.py": f'KEY = "{AWS_KEY}"  # pragma: allowlist secret\n'},
    "allowlist-file": {".secrets-allowlist": f"# fixture dùng trong test\n{FIXTURE_KEY}\n", "tests/fixtures/creds.txt": f"{FIXTURE_KEY}\n"},
}


@pytest.mark.parametrize("case", list(ALLOW))
def test_allows_non_secret(tmp_path, case):
    repo = Repo(tmp_path, ex.path("pre-commit"))
    before = repo.head()
    repo.stage(ALLOW[case])
    assert_allowed(repo, before, repo.commit())


def test_reports_every_finding(tmp_path):
    repo = Repo(tmp_path, ex.path("pre-commit"))
    repo.stage({"a.py": f'KEY = "{AWS_KEY}"\n', ".env": "X=1\n", "b/id_ed25519": pem("OPENSSH")})
    assert_blocked(repo, repo.commit(), ["secret: aws-access-key-id: a.py", "secret: dotenv-file: .env", "secret: private-key: b/id_ed25519"])


def test_scans_staged_version_not_worktree(tmp_path):
    repo = Repo(tmp_path, ex.path("pre-commit"))
    before = repo.head()
    repo.stage({"config/settings.py": f'KEY = "{AWS_KEY}"\n'})
    repo.write("config/settings.py", "KEY = os.environ['AWS_ACCESS_KEY_ID']\n")
    result = repo.commit()
    assert_blocked(repo, result, ["secret: aws-access-key-id: config/settings.py"])
    assert repo.head() == before


def test_ignores_unstaged_secret(tmp_path):
    repo = Repo(tmp_path, ex.path("pre-commit"))
    before = repo.head()
    repo.stage({"config/settings.py": "KEY = os.environ['AWS_ACCESS_KEY_ID']\n"})
    repo.write("config/settings.py", f'KEY = "{AWS_KEY}"\n')
    assert_allowed(repo, before, repo.commit())


def test_allows_deleting_committed_dotenv(tmp_path):
    repo = Repo(tmp_path, ex.path("pre-commit"))
    repo.write(".env", "DEBUG=1\n")
    repo.git("add", ".env")
    repo.git("commit", "-q", "--no-verify", "-m", "chore: oops")
    before = repo.head()
    repo.git("rm", "-q", "--cached", ".env")
    assert_allowed(repo, before, repo.commit())


def test_blocks_on_initial_commit(tmp_path):
    repo = Repo(tmp_path, ex.path("pre-commit"), initial=False)
    repo.stage({"deploy/keys/id_rsa": pem("RSA")})
    result = repo.commit()
    assert_blocked(repo, result, ["secret: private-key: deploy/keys/id_rsa"])
    assert repo.head() == ""


def test_naive_hook_is_caught(tmp_path):
    """Hook đọc working tree thay vì bản staged: chặn nhầm thứ không commit và bỏ lọt thứ được commit."""
    repo = Repo(tmp_path, NAIVE)
    repo.stage({"config/settings.py": "KEY = os.environ['AWS_ACCESS_KEY_ID']\n"})
    repo.write("config/settings.py", f'KEY = "{AWS_KEY}"\n')
    assert repo.commit().returncode != 0
    other = Repo(tmp_path / "second", NAIVE)
    other.stage({"config/settings.py": f'KEY = "{AWS_KEY}"\n'})
    other.write("config/settings.py", "KEY = os.environ['AWS_ACCESS_KEY_ID']\n")
    assert other.commit().returncode == 0


def test_shellcheck_clean():
    ex.require_tool("shellcheck", min_version="0.9.0")
    result = subprocess.run(["shellcheck", "-S", "style", "-s", "bash", str(ex.path("pre-commit"))], capture_output=True, text=True)
    assert result.returncode == 0, result.stdout

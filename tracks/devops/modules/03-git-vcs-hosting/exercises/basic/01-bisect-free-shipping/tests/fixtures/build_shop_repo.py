"""Dựng repo Olist Shop có một commit gây lỗi miễn phí ship, lịch sử thẳng, tất định.

    uv run python build_shop_repo.py /tmp/olist-bisect        # bố cục A
    uv run python build_shop_repo.py /tmp/olist-bisect-b B    # bố cục B

Không đọc cấu hình Git của bạn: HOME, GIT_CONFIG_GLOBAL, GIT_CONFIG_SYSTEM đều bị thay.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path


@dataclass(frozen=True)
class Layout:
    total: int
    bad: int
    syntax: range
    missing_rates: range


LAYOUTS = {
    "A": Layout(total=48, bad=31, syntax=range(24, 26), missing_rates=range(28, 30)),
    "B": Layout(total=37, bad=9, syntax=range(5, 7), missing_rates=range(20, 22)),
}

MESSAGES = [
    "feat(shipping): add rate for {state}",
    "chore: bump version to {version}",
    "docs: explain shipping rules in README",
    "fix(shipping): correct {state} rate",
    "test: cover default shipping rate",
    "refactor: rename internal helpers",
    "perf(shipping): cache rates table",
    "ci: run tests on python 3.12",
]
STATES = ["SP", "RJ", "MG", "RS", "PR", "BA", "SC", "PE", "CE", "GO"]
BASE_DATE = datetime(2026, 3, 2, 9, 0, tzinfo=timezone.utc)
SAFE_CONFIG = ["-c", "core.hooksPath=/dev/null", "-c", "core.fsmonitor=false"]

SHIPPING = """import json
from pathlib import Path

RATES = json.loads((Path(__file__).parent / "rates.json").read_text())
FREE_SHIPPING_MIN = 200


def shipping_fee(subtotal, state){colon}
    if subtotal {op} FREE_SHIPPING_MIN:
        return 0
    return RATES.get(state, RATES["default"])
"""


def git_env(home: Path, when: datetime | None = None) -> dict[str, str]:
    stamp = (when or BASE_DATE).isoformat()
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
        "GIT_AUTHOR_DATE": stamp,
        "GIT_COMMITTER_DATE": stamp,
        "GIT_TERMINAL_PROMPT": "0",
        "LANG": "C.UTF-8",
        "LC_ALL": "C.UTF-8",
    }


def git(repo: Path, home: Path, *args: str, when: datetime | None = None) -> str:
    result = subprocess.run(
        ["git", *SAFE_CONFIG, "-c", "init.defaultBranch=main", "-c", "commit.gpgsign=false", "-c", "tag.gpgsign=false", *args],
        cwd=repo, env=git_env(home, when), capture_output=True, text=True, check=True,
    )
    return result.stdout.strip()


def write_state(repo: Path, index: int, layout: Layout) -> str:
    package = repo / "olist_shop"
    package.mkdir(exist_ok=True)
    version = f"1.{index // 10}.{index % 10}"
    (package / "__init__.py").write_text(f'VERSION = "{version}"\n')
    shipping = SHIPPING.format(colon="" if index in layout.syntax else ":", op=">" if index >= layout.bad else ">=")
    (package / "shipping.py").write_text(shipping)
    rates = {"default": 35, **{state: 15 + (i * 3 + index) % 11 for i, state in enumerate(STATES)}}
    rates_file = package / "rates.json"
    if index in layout.missing_rates:
        rates_file.unlink(missing_ok=True)
    else:
        rates_file.write_text(json.dumps(rates, indent=2) + "\n")
    (repo / "README.md").write_text(f"# Olist Shop pricing\n\nVersion {version}. Free shipping from 200 BRL.\n")
    return version


def message(index: int, layout: Layout, version: str) -> str:
    if index == 0:
        return "feat(shipping): free shipping for orders from 200 BRL"
    if index == layout.bad:
        return "refactor(shipping): tidy free-shipping check"
    if index == layout.syntax.start:
        return "wip: split fee calculation"
    if index == layout.syntax.stop:
        return "fix: finish fee calculation split"
    if index == layout.missing_rates.start:
        return "chore: move rates table to data dir"
    if index == layout.missing_rates.stop:
        return "revert: keep rates table next to code"
    return MESSAGES[index % len(MESSAGES)].format(state=STATES[index % len(STATES)], version=version)


def build(repo: Path, layout_name: str = "A", home: Path | None = None) -> dict:
    """Trả {"shas": [sha theo thứ tự commit], "layout": Layout}. Commit 0 có tag v1.0.0."""
    layout = LAYOUTS[layout_name]
    home = home or Path(tempfile.mkdtemp(prefix="git-home-"))
    repo.mkdir(parents=True, exist_ok=True)
    git(repo, home, "init", "-q")
    shas = []
    for index in range(layout.total):
        version = write_state(repo, index, layout)
        when = BASE_DATE + timedelta(hours=index)
        git(repo, home, "add", "-A")
        git(repo, home, "commit", "-q", "-m", message(index, layout, version), when=when)
        shas.append(git(repo, home, "rev-parse", "HEAD"))
        if index == 0:
            git(repo, home, "tag", "v1.0.0", when=when)
    return {"shas": shas, "layout": layout}


if __name__ == "__main__":
    target = Path(sys.argv[1]).resolve()
    if target.exists():
        sys.exit(f"{target} đã tồn tại, chọn thư mục khác")
    info = build(target, sys.argv[2] if len(sys.argv) > 2 else "A")
    print(f"Đã dựng {len(info['shas'])} commit trong {target}. good = v1.0.0, bad = main")

"""M17: onboard model thứ hai (tip) qua template Copier của nền tảng, ký và quét model trước deploy, báo cáo chi phí theo model.

Đề ở capstone/milestones/m17-platform-onboarding.md. Pickle độc hại trong test đã vô hại hoá (nạp vào chỉ ghi một tệp đánh dấu
trong `tmp_path`); test không bao giờ nạp tệp model.
"""

import json
import os
import re
import shutil
import struct
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
import yaml
from etakit import PROJECT, ec_keypair, marker_pickle, need, require_file, stealth_pickle

import mlopskit
import testkit

VALID = {"project_name": "Tip Amount", "team": "pricing", "owner": "lan.nguyen@example.com", "cost_center": "CC-2041"}
TAGS = {"owner": VALID["owner"], "team": "pricing", "cost_center": "CC-2041"}
MAX_COMMANDS = 5
MAE_RATIO = 0.8
MIN_TEST_ROWS = 10_000
CHAINING = re.compile(r"&&|\|\||;|\|")


def template_dir() -> Path:
    path = PROJECT / "platform" / "template"
    if not path.is_dir():
        pytest.fail(f"Chưa có thư mục {path.relative_to(PROJECT.parents[3])}", pytrace=False)
    return path


def sandbox_env(**extra: str) -> dict[str, str]:
    path = f"{Path(sys.executable).parent}{os.pathsep}{os.environ.get('PATH', '/usr/bin:/bin')}"
    return {"PATH": path, "PYTHONDONTWRITEBYTECODE": "1", "NO_COLOR": "1", **extra}


def sandboxed(cmd: list, tmp_path: Path, cwd: Path, timeout: float = 180, **env: str):
    return testkit.run_sandboxed([str(c) for c in cmd], writable=[tmp_path], cwd=cwd, env=sandbox_env(**env), timeout=timeout)


def render(tmp_path: Path, answers: dict, name: str = "out"):
    template = tmp_path / "template"
    if not template.exists():
        shutil.copytree(template_dir(), template)
    dst = tmp_path / name
    args = [sys.executable, "-m", "copier", "copy", "--defaults", "--quiet"]
    for key, value in answers.items():
        args += ["--data", f"{key}={value}"]
    return sandboxed([*args, template, dst], tmp_path, tmp_path), dst


def project_tests(tmp_path: Path, dst: Path):
    return sandboxed([sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider"], tmp_path, dst)


def passed_count(stdout: str) -> int:
    found = re.findall(r"(\d+) passed", stdout)
    return int(found[-1]) if found else 0


def sniff(data: bytes) -> str:
    if len(data) >= 8:
        (size,) = struct.unpack("<Q", data[:8])
        if 0 < size and 8 + size <= len(data):
            try:
                if isinstance(json.loads(data[8:8 + size].decode("utf-8")), dict):
                    return "safetensors"
            except (UnicodeDecodeError, ValueError):
                pass
    try:
        json.loads(data.decode("utf-8"))
        return "json"
    except (UnicodeDecodeError, ValueError):
        return "other"


def test_m17_template_contract(project, tmp_path):
    found = sorted(template_dir().glob("copier.y*ml"))
    assert len(found) == 1, "template có đúng một tệp copier.yml (hoặc copier.yaml)"
    unsafe = {"_tasks", "_migrations", "_jinja_extensions"} & set(yaml.safe_load(found[0].read_text(encoding="utf-8")))
    assert not unsafe, "template phải chạy được không cần --trust"
    result, dst = render(tmp_path, VALID)
    assert result.returncode == 0, result.stderr[-2000:]
    meta = yaml.safe_load((dst / "mlproject.yaml").read_text(encoding="utf-8"))
    assert (meta.get("name"), meta.get("registry_name"), meta.get("model_format")) == ("tip-amount", "pricing-tip-amount", "safetensors")
    assert meta.get("tags") == TAGS, "mlproject.yaml mang đúng ba tag bắt buộc từ câu trả lời"
    answers = yaml.safe_load((dst / ".copier-answers.yml").read_text(encoding="utf-8"))
    assert answers.get("_src_path") and all(answers.get(k) == VALID[k] for k in ("team", "owner", "cost_center"))
    own = project_tests(tmp_path, dst)
    assert own.returncode == 0 and passed_count(own.stdout) >= 2, (own.stdout + own.stderr)[-3000:]
    caught = []
    for tag in TAGS:
        broken = {**meta, "tags": {k: v for k, v in TAGS.items() if k != tag}}
        (dst / "mlproject.yaml").write_text(yaml.safe_dump(broken), encoding="utf-8")
        caught.append(project_tests(tmp_path, dst).returncode != 0)
    assert all(caught), f"test của dự án sinh ra bắt được {sum(caught)}/3 ca mất tag bắt buộc"


BAD_ANSWERS = {
    "owner-not-email": {"owner": "lan"},
    "cost-center-format": {"cost_center": "2041"},
    "team-unknown": {"team": "marketing"},
    "slug-underscore": {"project_slug": "tip_amount"},
    "owner-missing": {"owner": None},
    "cost-center-missing": {"cost_center": None},
}


def test_m17_template_rejects_bad_answers(project, tmp_path):
    accepted = []
    for case, change in BAD_ANSWERS.items():
        answers = {k: v for k, v in {**VALID, **change}.items() if v is not None}
        result, dst = render(tmp_path, answers, name=case)
        if result.returncode == 0 or (dst / "mlproject.yaml").exists():
            accepted.append(case)
    assert not accepted, f"{len(accepted)}/{len(BAD_ANSWERS)} câu trả lời sai hoặc thiếu vẫn sinh dự án"


def onboarding_commands() -> list[str]:
    text = require_file("docs", "onboarding.md").read_text(encoding="utf-8")
    match = re.search(r"^## Onboarding\s*$(.*?)^```bash\n(.*?)^```", text, flags=re.S | re.M)
    assert match, "docs/onboarding.md cần mục `## Onboarding` có một khối ```bash"
    return [line.strip() for line in match.group(2).splitlines() if line.strip() and not line.strip().startswith("#")]


def test_m17_onboarding_in_five_commands(project, tmp_path):
    commands = onboarding_commands()
    shaped = (1 <= len(commands) <= MAX_COMMANDS and "eta.platform gate" in commands[-1]
              and not any(CHAINING.search(c) or c.endswith("\\") for c in commands))
    assert shaped, f"khối onboarding cần tối đa {MAX_COMMANDS} lệnh, mỗi dòng một lệnh không nối, lệnh cuối là cổng deploy"
    gate = need("platform.gate", "deploy_gate")
    trips = mlopskit.real_month("nyc-tlc", "2019-03")
    shutil.copytree(template_dir(), tmp_path / "platform")
    private, public = ec_keypair(tmp_path / "keys", "release")
    work = tmp_path / "work"
    work.mkdir()
    env = {"PLATFORM": str(tmp_path / "platform"), "TRIPS": str(trips), "SIGNING_KEY": str(private), "PUBLIC_KEY": str(public),
           "PYTHONPATH": str(PROJECT / "src")}
    for i, command in enumerate(commands[:-1], 1):
        done = sandboxed(["bash", "-euo", "pipefail", "-c", command], tmp_path, work, timeout=300, **env)
        assert done.returncode == 0, f"lệnh {i} lỗi:\n{(done.stdout + done.stderr)[-3000:]}"
    root = work / "tip-amount"
    model_dir, signature = root / "build" / "model", root / "build" / "model.sig"
    assert model_dir.is_dir() and signature.is_file(), "sau các lệnh trước cổng phải có tip-amount/build/model/ và model.sig"
    files = sorted(p for p in model_dir.rglob("*") if p.is_file() or p.is_symlink())
    kinds = {p.name: sniff(p.read_bytes()) for p in files if not p.is_symlink()}
    assert "safetensors" in kinds.values() and set(kinds.values()) <= {"safetensors", "json"} and len(kinds) == len(files), (
        "model xuất ra chỉ gồm safetensors và JSON (xét theo nội dung tệp)"
    )
    card = json.loads((model_dir / "metadata.json").read_text(encoding="utf-8"))
    assert card.get("tags") == TAGS and card.get("registry_name") == "pricing-tip-amount"
    metrics = json.loads((root / "build" / "metrics.json").read_text(encoding="utf-8"))
    good = metrics["n_test"] >= MIN_TEST_ROWS and metrics["mae"] <= MAE_RATIO * metrics["baseline_mae"]
    assert good, "metrics.json: MAE trên tập test thời gian phải thấp hơn rõ so với baseline trung vị (xem đề)"
    from model_signing import verifying

    verifying.Config().use_elliptic_key_verifier(public_key=public).verify(model_dir, signature)
    decision = gate.deploy_gate(model_dir, signature, public, mlopskit.modelscan_run)
    assert decision == {"allowed": True, "reasons": []}, f"model vừa onboard bị cổng chặn: {decision['reasons']}"
    assert oct(private.stat().st_mode & 0o777) == "0o600"


def sample_model(folder: Path, tags: dict) -> Path:
    from safetensors.numpy import save_file

    folder.mkdir(parents=True)
    rng = np.random.default_rng(0)
    save_file({"coef": rng.normal(size=7), "intercept": np.array([0.4])}, str(folder / "model.safetensors"), metadata={"format": "linear"})
    (folder / "config.json").write_text(json.dumps({"features": [f"f{i}" for i in range(7)], "target": "tip_amount"}), encoding="utf-8")
    (folder / "metadata.json").write_text(json.dumps({"name": "tip-amount", "registry_name": "pricing-tip-amount", "tags": tags}),
                                          encoding="utf-8")
    return folder


def flip_byte(folder: Path) -> None:
    path = folder / "model.safetensors"
    data = bytearray(path.read_bytes())
    data[-1] ^= 0x01
    path.write_bytes(bytes(data))


def set_tags(folder: Path, tags: dict) -> None:
    card = json.loads((folder / "metadata.json").read_text(encoding="utf-8"))
    (folder / "metadata.json").write_text(json.dumps({**card, "tags": tags}), encoding="utf-8")


def without(key: str) -> dict:
    return {k: v for k, v in TAGS.items() if k != key}


def test_m17_gate_blocks_unsigned_tampered_or_malicious(project, tmp_path):
    signing = need("platform.signing", "sign", "verify")
    gate = need("platform.gate", "deploy_gate")
    keys = tmp_path / "keys"
    private, public = ec_keypair(keys, "release")
    intruder, _ = ec_keypair(keys, "intruder")
    marker = tmp_path / "marker" / "pwned.txt"
    marker.parent.mkdir()
    cases = {
        "clean": (None, None, private, []),
        "unsigned": (None, None, None, ["signature"]),
        "byte-flipped-after-signing": (None, flip_byte, private, ["signature"]),
        "signed-by-other-key": (None, None, intruder, ["signature"]),
        "tag-removed-after-signing": (None, lambda d: set_tags(d, without("cost_center")), private, ["signature", "tag:cost_center"]),
        "signed-without-tag": (lambda d: set_tags(d, without("cost_center")), None, private, ["tag:cost_center"]),
        "signed-bad-owner": (lambda d: set_tags(d, {**TAGS, "owner": "lan"}), None, private, ["tag:owner"]),
        "signed-malicious-pickle": (lambda d: (d / "preprocess.pkl").write_bytes(marker_pickle(marker)), None, private,
                                    ["format:preprocess.pkl", "scan"]),
        "signed-stealth-pickle": (lambda d: (d / "extra.bin").write_bytes(stealth_pickle(marker)), None, private, ["format:extra.bin"]),
        "pickle-added-after-signing": (None, lambda d: (d / "preprocess.pkl").write_bytes(marker_pickle(marker)), private,
                                       ["format:preprocess.pkl", "scan", "signature"]),
    }
    calls, wrong = [], []

    def scan(path):
        calls.append(Path(path))
        return mlopskit.modelscan_run(path)

    for name, (before, after, key, expected) in cases.items():
        folder = sample_model(tmp_path / name / "model", TAGS)
        signature = tmp_path / name / "model.sig"
        if before:
            before(folder)
        if key is not None:
            signing.sign(folder, key, signature)
        if after:
            after(folder)
        start = len(calls)
        decision = gate.deploy_gate(folder, signature, public, scan)
        once = calls[start:] == [folder]
        if not (once and decision == {"allowed": not expected, "reasons": expected}):
            wrong.append(name)
    assert not marker.exists(), "một tệp model đã bị nạp: cổng không bao giờ được unpickle"
    assert not wrong, f"cổng deploy quyết định sai {len(wrong)}/{len(cases)} ca: {wrong}"
    inside = tmp_path / "clean" / "model" / "model.sig"
    with pytest.raises(ValueError):
        signing.sign(tmp_path / "clean" / "model", private, inside)
    assert not inside.exists(), "chữ ký đặt trong thư mục model phải bị từ chối"


RESOURCES = {"cpu_hours": "cpu_hour", "gpu_hours": "gpu_hour", "mem_gb_hours": "mem_gb_hour"}


def recompute(usage: pd.DataFrame, config: dict) -> dict:
    df = usage.copy()
    df["cost"] = sum(df[col] * config["prices"][price] for col, price in RESOURCES.items())
    df["team"] = df["namespace"].astype(str).str.strip().map(config["namespaces"])
    df["model"] = df["model"].fillna("").astype(str).str.strip().replace("", "unlabelled")
    direct = df[df["team"].notna()].groupby(["team", "model"])["cost"].sum()
    idle = sum(max(0.0, config["capacity"][col] - df[col].sum()) * config["prices"][price] for col, price in RESOURCES.items())
    share = idle * direct / direct.sum()
    models = {key: {"direct": direct[key], "idle_share": share[key], "total": direct[key] + share[key],
                    "cost_center": config["cost_centers"][key[0]]} for key in direct.index}
    unallocated = float(df.loc[df["team"].isna(), "cost"].sum())
    capacity = sum(config["capacity"][col] * config["prices"][price] for col, price in RESOURCES.items())
    return {"models": models, "unallocated": unallocated, "idle": idle, "capacity_cost": capacity,
            "total": float(direct.sum()) + idle + unallocated}


def matches(report: dict, expected: dict, tol: float = 0.011) -> bool:
    rows = report.get("models") or []
    got = {(r["team"], r["model"]): r for r in rows}
    if len(got) != len(rows) or set(got) != set(expected["models"]):
        return False
    for key, want in expected["models"].items():
        row = got[key]
        if row.get("cost_center") != want["cost_center"]:
            return False
        if any(abs(float(row[k]) - want[k]) > tol for k in ("direct", "idle_share", "total")):
            return False
    return all(abs(float(report.get(k, float("nan"))) - expected[k]) <= tol for k in ("unallocated", "idle", "capacity_cost", "total"))


def read_usage(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, dtype={"model": str, "namespace": str}, keep_default_na=False)


def test_m17_cost_report_recomputes(project, tmp_path):
    usage_path = require_file("platform", "usage.csv")
    config = yaml.safe_load(require_file("platform", "cost.yaml").read_text(encoding="utf-8"))
    report = yaml.safe_load(require_file("reports", "cost.yaml").read_text(encoding="utf-8"))
    markdown = require_file("reports", "cost.md").read_text(encoding="utf-8")
    expected = recompute(read_usage(usage_path), config)
    assert isinstance(report, dict) and matches(report, expected), "reports/cost.yaml lệch với tính lại từ platform/usage.csv"
    assert abs(expected["total"] - expected["capacity_cost"]) < 0.05
    rows = [line for line in markdown.splitlines() if line.startswith("|")]
    missing = [key for key, want in expected["models"].items()
               if not any(key[1] in line and f"{want['total']:.2f}" in line for line in rows)]
    assert not missing, f"reports/cost.md thiếu dòng bảng cho {len(missing)} model (tên model và tổng 2 chữ số)"
    cost = need("platform.cost", "load_usage", "cost_report")
    usage = read_usage(usage_path)
    extra = pd.DataFrame([
        {"date": "2019-11-30", "namespace": "ml-research", "model": "", "workload": "notebook", "cpu_hours": 5.0, "gpu_hours": 0.0, "mem_gb_hours": 9.0},
        {"date": "2019-11-30", "namespace": " pricing", "model": "  ", "workload": "notebook", "cpu_hours": 2.0, "gpu_hours": 0.0, "mem_gb_hours": 4.0},
        {"date": "2019-11-30", "namespace": "eta-train", "model": "eta", "workload": "train", "cpu_hours": 1.0, "gpu_hours": 400.0, "mem_gb_hours": 2.0},
    ])
    changed = pd.concat([usage, extra], ignore_index=True)
    changed.to_csv(tmp_path / "usage.csv", index=False)
    got = cost.cost_report(cost.load_usage(tmp_path / "usage.csv"), config)
    assert matches(got, recompute(changed, config)), (
        "cost_report sai khi có namespace lạ, nhãn model rỗng hoặc dùng vượt năng lực một loại tài nguyên"
    )

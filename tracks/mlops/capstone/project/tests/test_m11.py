"""M11 (tuỳ chọn): một phần service lên cloud free tier bằng Terraform, tag dự án, lệnh dọn có `--dry-run`, budget.

Đề ở capstone/milestones/m11-cloud-optional.md. Không test nào cần tài khoản, khoá hay mạng cloud; test chạm cloud thật chỉ
chạy khi `ETA_CLOUD_LIVE=1`.
"""

import json
import os
import re
import shutil
import subprocess
import sys

import pytest
from etakit import PROJECT

from testkit import run_sandboxed

TAG_KEY, TAG_VALUE = "project", "eta-mlops"
SUBRESOURCES = {
    "aws_s3_bucket_public_access_block", "aws_s3_bucket_versioning", "aws_s3_bucket_server_side_encryption_configuration",
    "aws_s3_bucket_lifecycle_configuration", "aws_s3_bucket_ownership_controls", "aws_s3_bucket_policy",
    "aws_iam_role_policy", "aws_iam_role_policy_attachment", "aws_lambda_function_url", "aws_lambda_permission",
    "google_project_service", "google_storage_bucket_iam_member", "google_cloud_run_v2_service_iam_member",
    "google_cloud_run_service_iam_member", "google_project_iam_member",
}
SKIP_REASON = "M11 tuỳ chọn: chưa có thư mục cloud/ (bỏ qua không mất điểm phần lõi; xem milestones/m11-cloud-optional.md)"
FAKE_CLIS = ("aws", "gcloud", "az")


def cloud_dir():
    folder = PROJECT / "cloud"
    if not folder.is_dir():
        pytest.skip(SKIP_REASON)
    return folder


def _string_end(text: str, i: int) -> int:
    j = i + 1
    while j < len(text):
        if text[j] == "\\":
            j += 2
        elif text[j] == '"':
            return j + 1
        elif text.startswith(("${", "%{"), j):
            j = _template_end(text, j + 2)
        else:
            j += 1
    raise ValueError("chuỗi HCL không đóng")


def _template_end(text: str, j: int) -> int:
    depth = 1
    while j < len(text):
        if text[j] == '"':
            j = _string_end(text, j)
            continue
        if text[j] == "{":
            depth += 1
        elif text[j] == "}":
            depth -= 1
            if depth == 0:
                return j + 1
        j += 1
    raise ValueError("biểu thức ${...} không đóng")


def strip_hcl(text: str) -> str:
    out, i = [], 0
    while i < len(text):
        heredoc = re.match(r"<<-?([A-Za-z_]\w*)[ \t]*\n", text[i:])
        if text[i] == '"':
            j = _string_end(text, i)
            out.append(text[i:j])
            i = j
        elif heredoc:
            end = re.compile(rf"^[ \t]*{heredoc.group(1)}[ \t]*$", re.M).search(text, i + heredoc.end())
            out.append('""')
            i = len(text) if end is None else end.end()
        elif text[i] == "#" or text.startswith("//", i):
            j = text.find("\n", i)
            i = len(text) if j < 0 else j
        elif text.startswith("/*", i):
            j = text.find("*/", i + 2)
            i = len(text) if j < 0 else j + 2
        else:
            out.append(text[i])
            i += 1
    return "".join(out)


BLOCK = re.compile(r'(?m)^[ \t]*(resource|data|provider|locals|variable|output|module|terraform)((?:[ \t]+"[^"]*")*)[ \t]*\{')


def hcl_blocks(text: str) -> list[tuple[str, list[str], str]]:
    """Các block cấp ngoài cùng của một tệp `.tf`: (loại, nhãn, thân)."""
    text = strip_hcl(text)
    blocks, pos = [], 0
    while True:
        match = BLOCK.search(text, pos)
        if match is None:
            return blocks
        depth, j = 1, match.end()
        while depth and j < len(text):
            if text[j] == '"':
                j = _string_end(text, j)
                continue
            depth += {"{": 1, "}": -1}.get(text[j], 0)
            j += 1
        blocks.append((match.group(1), re.findall(r'"([^"]*)"', match.group(2)), text[match.end():j - 1]))
        pos = j


def terraform_blocks(folder):
    files = sorted(folder.glob("*.tf"))
    assert files, "cloud/ cần IaC Terraform (hoặc OpenTofu): ít nhất một tệp *.tf"
    return [block for path in files for block in hcl_blocks(path.read_text(encoding="utf-8"))]


TAGGED = re.compile(r"\b(tags|labels)\s*=\s*(merge\(\s*)?local\.tags\b")


def test_m11_iac_resources_tagged(project):
    folder = cloud_dir()
    blocks = terraform_blocks(folder)
    resources = [(labels[0], labels[1], body) for kind, labels, body in blocks if kind == "resource" and len(labels) == 2]
    assert resources, "chưa có block resource nào trong cloud/*.tf"
    locals_text = "\n".join(body for kind, _, body in blocks if kind == "locals")
    assert re.search(r"\btags\s*=", locals_text) and re.search(rf'\b{TAG_KEY}\s*=\s*"{TAG_VALUE}"', locals_text), \
        f'cần locals {{ tags = {{ {TAG_KEY} = "{TAG_VALUE}", ... }} }}'
    default = any(kind == "provider" and re.search(r"\bdefault_(tags|labels)\b[^}]*local\.tags", body, re.S)
                  for kind, _, body in blocks)
    untagged = [f"{kind}.{name}" for kind, name, body in resources
                if kind not in SUBRESOURCES and not default and not TAGGED.search(body)]
    assert not untagged, f"tài nguyên thiếu tags = local.tags (hoặc merge(local.tags, ...)): {untagged}"
    for path in sorted(folder.glob("*.tf")):
        text = strip_hcl(path.read_text(encoding="utf-8"))
        assert not re.search(r'\b(access_key|secret_key)\s*=\s*"', text), f"{path.name}: không ghi khoá truy cập vào IaC"
    ignore = folder / ".gitignore"
    assert ignore.is_file(), "cloud/.gitignore phải chặn state và thư mục provider"
    patterns = ignore.read_text(encoding="utf-8")
    assert "*.tfstate" in patterns and ".terraform" in patterns, "cloud/.gitignore cần *.tfstate và .terraform"


INVENTORY = [
    {"id": "arn:aws:s3:::eta-mlops-models-7f3a", "type": "aws_s3_bucket", "name": "eta-mlops-models-7f3a",
     "tags": {"project": "eta-mlops", "milestone": "m11"}},
    {"id": "arn:aws:lambda:us-east-1:111122223333:function:eta-mlops-health", "type": "aws_lambda_function",
     "name": "eta-mlops-health", "tags": {"project": "eta-mlops"}},
    {"id": "arn:aws:logs:us-east-1:111122223333:log-group:/aws/lambda/eta-mlops-health", "type": "aws_cloudwatch_log_group",
     "name": "/aws/lambda/eta-mlops-health", "tags": {"project": "eta-mlops"}},
    {"id": "arn:aws:iam::111122223333:role/eta-mlops/eta-mlops-health-role", "type": "aws_iam_role",
     "name": "eta-mlops-health-role", "tags": {"project": "eta-mlops"}},
    {"id": "arn:aws:budgets::111122223333:budget/eta-mlops-monthly", "type": "aws_budgets_budget",
     "name": "eta-mlops-monthly", "tags": {"project": "eta-mlops"}},
    {"id": "arn:aws:s3:::eta-mlops-scratch-manual", "type": "aws_s3_bucket", "name": "eta-mlops-scratch-manual", "tags": {}},
    {"id": "arn:aws:s3:::eta-mlops-staging-models", "type": "aws_s3_bucket", "name": "eta-mlops-staging-models",
     "tags": {"project": "eta-mlops-staging"}},
    {"id": "arn:aws:lambda:us-east-1:111122223333:function:billing-export", "type": "aws_lambda_function",
     "name": "billing-export", "tags": {"Project": "eta-mlops"}},
    {"id": "arn:aws:s3:::family-photos-2019", "type": "aws_s3_bucket", "name": "family-photos-2019",
     "tags": {"owner": "me"}},
    {"id": "arn:aws:iam::111122223333:role/legacy-ci", "type": "aws_iam_role", "name": "legacy-ci"},
]
SELECTED = [r for r in INVENTORY if (r.get("tags") or {}).get(TAG_KEY) == TAG_VALUE]
KEPT = [r for r in INVENTORY if r not in SELECTED]


@pytest.fixture
def teardown_env(tmp_path):
    script = cloud_dir() / "teardown.sh"
    assert script.is_file(), "cần cloud/teardown.sh"
    inventory = tmp_path / "inventory.json"
    inventory.write_text(json.dumps({"resources": INVENTORY}, indent=2), encoding="utf-8")
    fake = tmp_path / "bin"
    fake.mkdir()
    log = tmp_path / "cli.log"
    for name in FAKE_CLIS:
        cli = fake / name
        cli.write_text(f'#!/bin/sh\necho "{name} $*" >> "{log}"\n', encoding="utf-8")
        cli.chmod(0o755)
    py = os.path.dirname(sys.executable)

    def run(*args: str):
        result = run_sandboxed(["bash", str(script), *args, "--inventory", str(inventory)], writable=[tmp_path],
                               cwd=tmp_path, env={"PATH": f"{fake}:{py}:/usr/local/bin:/usr/bin:/bin"}, timeout=60)
        calls = log.read_text(encoding="utf-8") if log.is_file() else ""
        log.unlink(missing_ok=True)
        return result, calls

    return run


def test_m11_teardown_dry_run_inventory(project, teardown_env):
    result, calls = teardown_env("--dry-run")
    assert result.returncode == 0, f"teardown.sh --dry-run phải exit 0:\n{result.stdout}\n{result.stderr}"
    assert not calls, f"--dry-run không được gọi CLI cloud nào, đã gọi:\n{calls}"
    lines = [line for line in result.stdout.splitlines() if line.startswith("WOULD DELETE")]
    for resource in SELECTED:
        hits = [line for line in lines if resource["id"] in line]
        assert len(hits) == 1, f"{resource['id']} (tag {TAG_KEY}={TAG_VALUE}) phải có đúng một dòng WOULD DELETE, có {len(hits)}"
    for resource in KEPT:
        assert not any(resource["id"] in line for line in lines), \
            f"{resource['id']} không có tag {TAG_KEY}={TAG_VALUE} đúng từng ký tự, không được nằm trong danh sách xoá"
    assert len(lines) == len(SELECTED), f"đúng {len(SELECTED)} dòng WOULD DELETE, có {len(lines)}:\n{result.stdout}"


def test_m11_teardown_deletes_only_tagged(project, teardown_env):
    refused, calls = teardown_env()
    assert refused.returncode != 0, "không có --dry-run và không có --yes thì teardown.sh phải từ chối (exit khác 0)"
    assert not calls, f"bị từ chối thì không được gọi CLI cloud nào, đã gọi:\n{calls}"
    result, calls = teardown_env("--yes")
    assert result.returncode == 0, f"teardown.sh --yes trên inventory giả phải exit 0:\n{result.stdout}\n{result.stderr}"
    for resource in SELECTED:
        assert resource["name"] in calls, f"không thấy lệnh xoá {resource['type']} {resource['name']}:\n{calls}"
    for resource in KEPT:
        assert resource["name"] not in calls, f"teardown.sh đã đụng tới {resource['name']} (không có tag dự án):\n{calls}"


def test_m11_budget_doc(project):
    path = cloud_dir() / "budget.md"
    assert path.is_file(), "cần cloud/budget.md"
    text = path.read_text(encoding="utf-8")
    assert re.search(r"\d+(?:[.,]\d+)?\s*USD", text), "budget.md cần ngưỡng tiền ghi bằng số kèm USD"
    assert "teardown.sh --dry-run" in text, "budget.md cần lệnh xem trước việc dọn: teardown.sh --dry-run"
    assert re.search(r"(?i)alarm|cảnh báo", text), "budget.md cần nói alarm/cảnh báo gửi tới đâu"
    assert "TODO" not in text and len(text.split()) >= 150, "budget.md cần ít nhất 150 từ, không còn TODO"


def test_m11_cloud_live(project):
    if os.environ.get("ETA_CLOUD_LIVE") != "1":
        pytest.skip("Test cloud thật tắt mặc định: đặt ETA_CLOUD_LIVE=1 (cần CLI cloud đã đăng nhập) để chạy teardown --dry-run thật")
    folder = cloud_dir()
    if not any(shutil.which(name) for name in FAKE_CLIS):
        pytest.fail("ETA_CLOUD_LIVE=1 nhưng không có aws, gcloud hay az trong PATH", pytrace=False)
    result = subprocess.run(["bash", str(folder / "teardown.sh"), "--dry-run"], cwd=folder, capture_output=True, text=True,
                            timeout=300)
    assert result.returncode == 0, f"teardown.sh --dry-run trên tài khoản thật lỗi:\n{result.stdout}\n{result.stderr}"
    print(result.stdout)

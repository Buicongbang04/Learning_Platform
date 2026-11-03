import re

ORDER = [
    "sagemaker-endpoint", "vertex-endpoint", "azureml-endpoint",
    "sagemaker-endpoint-config", "sagemaker-model", "vertex-model",
    "sagemaker-notebook", "nat-gateway",
    "s3-bucket", "gcs-bucket", "azure-resource-group",
]
SAFE_NAME = re.compile(r"[a-z0-9][a-z0-9_-]{0,62}")

COMMANDS = {
    "sagemaker-endpoint": ["aws sagemaker delete-endpoint --endpoint-name {n} --region {r}"],
    "sagemaker-endpoint-config": ["aws sagemaker delete-endpoint-config --endpoint-config-name {n} --region {r}"],
    "sagemaker-model": ["aws sagemaker delete-model --model-name {n} --region {r}"],
    "sagemaker-notebook": [
        "aws sagemaker stop-notebook-instance --notebook-instance-name {n} --region {r}",
        "aws sagemaker delete-notebook-instance --notebook-instance-name {n} --region {r}",
    ],
    "nat-gateway": ["aws ec2 delete-nat-gateway --nat-gateway-id {n} --region {r}"],
    "s3-bucket": ["aws s3 rb s3://{n} --force"],
    "vertex-endpoint": ["gcloud ai endpoints delete {n} --region={r} --quiet"],
    "vertex-model": ["gcloud ai models delete {n} --region={r} --quiet"],
    "gcs-bucket": ["gcloud storage rm --recursive gs://{n}"],
    "azureml-endpoint": ["az ml online-endpoint delete --name {n} --resource-group {g} --yes"],
    "azure-resource-group": ["az group delete --name {n} --yes --no-wait"],
}


def _mine(inventory: list[dict], lab: str) -> list[dict]:
    return [item for item in inventory if item.get("tags", {}).get("lab") == lab]


def plan_teardown(inventory: list[dict], lab: str) -> list[dict]:
    mine = _mine(inventory, lab)
    for item in mine:
        if item["type"] not in COMMANDS:
            raise ValueError(f"loại tài nguyên chưa hỗ trợ: {item['type']}")
        if not SAFE_NAME.fullmatch(item["name"]):
            raise ValueError(f"tên không an toàn: {item['name']!r}")
        if item["type"] == "azureml-endpoint" and not item.get("resource_group"):
            raise ValueError(f"thiếu resource_group cho {item['name']}")
    steps = []
    for item in sorted(mine, key=lambda i: ORDER.index(i["type"])):
        for template in COMMANDS[item["type"]]:
            command = template.format(n=item["name"], r=item.get("region", ""), g=item.get("resource_group", ""))
            steps.append({"resource": item["name"], "type": item["type"], "command": command})
    return steps


def render_script(steps: list[dict]) -> str:
    lines = [
        "#!/usr/bin/env bash",
        "FAILED=0",
        "run() {",
        '  if [ "${DRY_RUN:-1}" = "0" ]; then',
        '    "$@" || { echo "FAILED: $*" >&2; FAILED=1; }',
        "  else",
        '    echo "DRY-RUN: $*"',
        "  fi",
        "}",
    ]
    lines += [f"run {step['command']}" for step in steps]
    lines.append('exit "$FAILED"')
    return "\n".join(lines) + "\n"


def leftover_warnings(inventory: list[dict], lab: str) -> list[dict]:
    warnings = []
    for item in inventory:
        if item.get("tags", {}).get("lab") != lab and item["name"].startswith(lab):
            warnings.append({"resource": item["name"], "why": "tên giống lab nhưng không có tag lab đúng, kế hoạch không động tới, tự kiểm"})
    return warnings

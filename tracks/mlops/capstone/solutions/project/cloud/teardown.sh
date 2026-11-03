#!/usr/bin/env bash
# Dọn mọi tài nguyên AWS mang tag project=eta-mlops (đúng từng ký tự). Lưới an toàn sau `terraform destroy`.
#
#   bash teardown.sh --dry-run                 # chỉ liệt kê, không gọi lệnh xoá nào
#   bash teardown.sh --yes                     # xoá thật
#   bash teardown.sh --dry-run --inventory f   # dùng inventory JSON có sẵn thay vì hỏi AWS
#
# Inventory: {"resources": [{"id": ARN, "type": "aws_s3_bucket", "name": "...", "tags": {"project": "eta-mlops"}}]}
set -euo pipefail

TAG_KEY=project
TAG_VALUE=eta-mlops
ROLE_PATH=/eta-mlops/
DRY_RUN=0
YES=0
INVENTORY=""

usage() {
    echo "usage: teardown.sh (--dry-run | --yes) [--inventory FILE]" >&2
    exit 2
}

while [ $# -gt 0 ]; do
    case "$1" in
        --dry-run) DRY_RUN=1 ;;
        --yes) YES=1 ;;
        --inventory) [ $# -ge 2 ] || usage; INVENTORY="$2"; shift ;;
        -h|--help) usage ;;
        *) echo "tham số lạ: $1" >&2; usage ;;
    esac
    shift
done

if [ "$DRY_RUN" -eq 0 ] && [ "$YES" -eq 0 ]; then
    echo "Từ chối xoá: thêm --dry-run để xem trước, hoặc --yes để xoá thật." >&2
    exit 2
fi

WORK=$(mktemp -d)
trap 'rm -rf "$WORK"' EXIT

collect_inventory() {
    command -v aws >/dev/null || { echo "không có aws CLI trong PATH" >&2; exit 2; }
    aws resourcegroupstaggingapi get-resources --tag-filters "Key=$TAG_KEY,Values=$TAG_VALUE" --output json > "$WORK/tagged.json"
    : > "$WORK/roles.jsonl"
    for role in $(aws iam list-roles --path-prefix "$ROLE_PATH" --query 'Roles[].RoleName' --output text); do
        arn=$(aws iam get-role --role-name "$role" --query 'Role.Arn' --output text)
        tags=$(aws iam list-role-tags --role-name "$role" --query 'Tags' --output json)
        printf '{"ResourceARN": "%s", "Tags": %s}\n' "$arn" "$tags" >> "$WORK/roles.jsonl"
    done
    python3 - "$WORK/tagged.json" "$WORK/roles.jsonl" > "$WORK/inventory.json" <<'PY'
import json, sys

TYPES = {"s3": "aws_s3_bucket", "lambda": "aws_lambda_function", "logs": "aws_cloudwatch_log_group",
         "iam": "aws_iam_role", "budgets": "aws_budgets_budget"}
mappings = json.load(open(sys.argv[1])).get("ResourceTagMappingList", [])
mappings += [json.loads(line) for line in open(sys.argv[2]) if line.strip()]
seen, resources = set(), []
for item in mappings:
    arn = item["ResourceARN"]
    if arn in seen:
        continue
    seen.add(arn)
    service, rest = arn.split(":")[2], arn.split(":", 5)[5]
    if service == "s3":
        name = rest
    elif service == "logs":
        name = rest.removeprefix("log-group:").removesuffix(":*")
    else:
        name = rest.rsplit(":", 1)[-1].rsplit("/", 1)[-1]
    resources.append({"id": arn, "type": TYPES.get(service, f"aws_{service}"), "name": name,
                      "tags": {t["Key"]: t["Value"] for t in item.get("Tags", [])}})
json.dump({"resources": resources}, sys.stdout, indent=2)
PY
    INVENTORY="$WORK/inventory.json"
}

[ -n "$INVENTORY" ] || collect_inventory

python3 - "$INVENTORY" "$TAG_KEY" "$TAG_VALUE" > "$WORK/plan.tsv" <<'PY'
import json, sys

ORDER = ["aws_lambda_function", "aws_cloudwatch_log_group", "aws_s3_bucket", "aws_iam_role", "aws_budgets_budget"]
inventory, key, value = json.load(open(sys.argv[1])), sys.argv[2], sys.argv[3]
chosen = [r for r in inventory.get("resources", []) if (r.get("tags") or {}).get(key) == value]
chosen.sort(key=lambda r: ORDER.index(r["type"]) if r["type"] in ORDER else len(ORDER))
for r in chosen:
    print("\t".join([r["type"], r["id"], r.get("name") or r["id"]]))
PY

delete_one() {
    local type="$1" id="$2" name="$3"
    case "$type" in
        aws_lambda_function) aws lambda delete-function --function-name "$name" ;;
        aws_cloudwatch_log_group) aws logs delete-log-group --log-group-name "$name" ;;
        aws_s3_bucket) aws s3 rb "s3://$name" --force ;;
        aws_iam_role)
            for policy in $(aws iam list-role-policies --role-name "$name" --query 'PolicyNames' --output text); do
                aws iam delete-role-policy --role-name "$name" --policy-name "$policy"
            done
            for policy in $(aws iam list-attached-role-policies --role-name "$name" --query 'AttachedPolicies[].PolicyArn' --output text); do
                aws iam detach-role-policy --role-name "$name" --policy-arn "$policy"
            done
            aws iam delete-role --role-name "$name"
            ;;
        aws_budgets_budget) aws budgets delete-budget --account-id "$(echo "$id" | cut -d: -f5)" --budget-name "$name" ;;
        *) echo "không biết cách xoá $type ($id): xoá tay trên console" >&2; return 1 ;;
    esac
}

unknown=$(awk -F'\t' '$1 !~ /^aws_(lambda_function|cloudwatch_log_group|s3_bucket|iam_role|budgets_budget)$/' "$WORK/plan.tsv")
count=$(wc -l < "$WORK/plan.tsv")

if [ "$DRY_RUN" -eq 1 ]; then
    while IFS=$'\t' read -r type id name; do
        echo "WOULD DELETE $type $id"
    done < "$WORK/plan.tsv"
    [ -z "$unknown" ] || echo "Cảnh báo, loại chưa có lệnh xoá (phải xoá tay): $unknown" >&2
    echo "Tổng: $count tài nguyên mang tag $TAG_KEY=$TAG_VALUE (dry-run, không xoá gì)" >&2
    exit 0
fi

if [ -n "$unknown" ]; then
    echo "Dừng trước khi xoá: có loại tài nguyên chưa biết cách xoá:" >&2
    echo "$unknown" >&2
    exit 3
fi

while IFS=$'\t' read -r type id name; do
    echo "DELETE $type $id"
    delete_one "$type" "$id" "$name" < /dev/null
done < "$WORK/plan.tsv"
echo "Đã xoá $count tài nguyên. Kiểm lại: bash teardown.sh --dry-run phải in 0 dòng WOULD DELETE." >&2

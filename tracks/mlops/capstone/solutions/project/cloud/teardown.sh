#!/usr/bin/env bash
# Dọn mọi tài nguyên AWS mang tag project=eta-mlops (đúng từng ký tự); lưới an toàn sau terraform destroy.
set -uo pipefail

TAG_KEY=project
TAG_VALUE=eta-mlops
ROLE_PATH=/eta-mlops/
REGION="${ETA_AWS_REGION:-us-east-1}"
DRY_RUN=0
YES=0
INVENTORY=""

usage() {
    echo "usage: teardown.sh (--dry-run | --yes) [--inventory FILE] [--region REGION]" >&2
    exit 2
}

while [ $# -gt 0 ]; do
    case "$1" in
        --dry-run) DRY_RUN=1 ;;
        --yes) YES=1 ;;
        --inventory) [ $# -ge 2 ] || usage; INVENTORY="$2"; shift ;;
        --region) [ $# -ge 2 ] || usage; REGION="$2"; shift ;;
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
    python3 - "$REGION" "$TAG_KEY" "$TAG_VALUE" "$ROLE_PATH" > "$WORK/inventory.json" <<'PY' || exit 2
import json, subprocess, sys

region, key, value, role_path = sys.argv[1:5]
TYPES = {"s3": "aws_s3_bucket", "lambda": "aws_lambda_function", "logs": "aws_cloudwatch_log_group",
         "iam": "aws_iam_role", "budgets": "aws_budgets_budget"}


def aws(*args):
    done = subprocess.run(["aws", *args, "--output", "json"], capture_output=True, text=True)
    if done.returncode != 0:
        sys.exit(f"aws {' '.join(args)} lỗi:\n{done.stderr}")
    return json.loads(done.stdout or "{}")


mappings = aws("resourcegroupstaggingapi", "get-resources", "--region", region,
               "--tag-filters", f"Key={key},Values={value}").get("ResourceTagMappingList", [])
for role in aws("iam", "list-roles", "--path-prefix", role_path).get("Roles", []):
    tags = aws("iam", "list-role-tags", "--role-name", role["RoleName"]).get("Tags", [])
    mappings.append({"ResourceARN": role["Arn"], "Tags": tags})
account = aws("sts", "get-caller-identity")["Account"]
for budget in aws("budgets", "describe-budgets", "--account-id", account).get("Budgets", []):
    arn = f"arn:aws:budgets::{account}:budget/{budget['BudgetName']}"
    tags = aws("budgets", "list-tags-for-resource", "--resource-arn", arn).get("ResourceTags", [])
    mappings.append({"ResourceARN": arn, "Tags": tags})

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

INVENTORY_ARG="$INVENTORY"
[ -n "$INVENTORY" ] || collect_inventory

python3 - "$INVENTORY" "$TAG_KEY" "$TAG_VALUE" > "$WORK/plan.tsv" <<'PY' || exit 2
import json, sys

ORDER = ["aws_lambda_function", "aws_cloudwatch_log_group", "aws_s3_bucket", "aws_iam_role", "aws_budgets_budget"]
inventory, key, value = json.load(open(sys.argv[1])), sys.argv[2], sys.argv[3]
chosen = [r for r in inventory.get("resources", []) if (r.get("tags") or {}).get(key) == value]
chosen.sort(key=lambda r: ORDER.index(r["type"]) if r["type"] in ORDER else len(ORDER))
for r in chosen:
    print("\t".join([r["type"], r["id"], r.get("name") or r["id"]]))
PY

delete_role() {
    local name="$1" rc=0 policies policy
    policies=$(aws iam list-role-policies --role-name "$name" --query 'PolicyNames' --output text) || rc=1
    for policy in $policies; do
        [ "$policy" = "None" ] && continue
        aws iam delete-role-policy --role-name "$name" --policy-name "$policy" || rc=1
    done
    policies=$(aws iam list-attached-role-policies --role-name "$name" --query 'AttachedPolicies[].PolicyArn' --output text) || rc=1
    for policy in $policies; do
        [ "$policy" = "None" ] && continue
        aws iam detach-role-policy --role-name "$name" --policy-arn "$policy" || rc=1
    done
    aws iam delete-role --role-name "$name" || rc=1
    return "$rc"
}

delete_one() {
    local type="$1" id="$2" name="$3" region
    region=$(echo "$id" | cut -d: -f4)
    region="${region:-$REGION}"
    case "$type" in
        aws_lambda_function) aws lambda delete-function --region "$region" --function-name "$name" ;;
        aws_cloudwatch_log_group) aws logs delete-log-group --region "$region" --log-group-name "$name" ;;
        aws_s3_bucket) aws s3 rb "s3://$name" --force ;;
        aws_iam_role) delete_role "$name" ;;
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
    if [ -n "$INVENTORY_ARG" ]; then
        where="trong inventory $INVENTORY_ARG"
    else
        where="ở vùng $REGION, cộng IAM role dưới $ROLE_PATH và budget toàn cục"
    fi
    echo "Tổng: $count tài nguyên mang tag $TAG_KEY=$TAG_VALUE $where (dry-run, không xoá gì)" >&2
    exit 0
fi

if [ -n "$unknown" ]; then
    echo "Dừng trước khi xoá: có loại tài nguyên chưa biết cách xoá:" >&2
    echo "$unknown" >&2
    exit 3
fi

failed=()
while IFS=$'\t' read -r type id name; do
    echo "DELETE $type $id"
    delete_one "$type" "$id" "$name" < /dev/null || failed+=("$type $id")
done < "$WORK/plan.tsv"

if [ "${#failed[@]}" -gt 0 ]; then
    for item in "${failed[@]}"; do
        echo "FAILED: $item" >&2
    done
    echo "Xoá lỗi ${#failed[@]}/$count tài nguyên, phần còn lại vẫn được xoá. Sửa lỗi rồi chạy lại --dry-run." >&2
    exit 1
fi
echo "Đã xoá $count tài nguyên. Kiểm lại: bash teardown.sh --dry-run phải in 0 dòng WOULD DELETE." >&2

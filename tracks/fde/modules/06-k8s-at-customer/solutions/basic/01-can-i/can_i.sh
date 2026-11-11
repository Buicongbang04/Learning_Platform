#!/bin/sh
set -u
checks=$1
err=$(mktemp)
trap 'rm -f "$err"' EXIT

fail() {
    echo "can_i.sh: $1" >&2
    sed 's/^/  /' "$err" >&2
    exit 2
}

json_string() {
    printf '"%s"' "$(printf '%s' "$1" | sed 's/\\/\\\\/g; s/"/\\"/g')"
}

[ -r "$checks" ] || { echo "can_i.sh: không đọc được $checks" >&2; exit 2; }

user=$(kubectl auth whoami -o jsonpath='{.status.userInfo.username}' 2>"$err") || fail "không hỏi được API server (kubectl auth whoami)"
[ -n "$user" ] || fail "kubectl auth whoami không trả username"
namespace=$(kubectl config view --minify -o jsonpath='{..namespace}' 2>"$err") || fail "không đọc được context của kubeconfig"
[ -n "$namespace" ] || namespace=default

results=""
missing=""
while read -r kind rest; do
    case $kind in
        ''|'#'*) continue ;;
        need|info) ;;
        *) echo "can_i.sh: dòng không hợp lệ trong $checks: $kind $rest" >&2; exit 2 ;;
    esac
    args=$(printf '%s\n' "$rest" | tr -s ' \t' '  ' | sed 's/^ //; s/ $//')
    answer=$(kubectl auth can-i $args 2>"$err")
    case $answer in
        yes) allowed=true ;;
        no) allowed=false ;;
        *) fail "không hỏi được quyền '$args'" ;;
    esac
    results="$results${results:+,}$(json_string "$args"):$allowed"
    if [ "$kind" = need ] && [ "$allowed" = false ]; then
        missing="$missing${missing:+,}$(json_string "$args")"
    fi
done < "$checks"

if [ -z "$missing" ]; then can_install=true; else can_install=false; fi
printf '{"user":%s,"namespace":%s,"checks":{%s},"missing":[%s],"can_install":%s}\n' \
    "$(json_string "$user")" "$(json_string "$namespace")" "$results" "$missing" "$can_install"

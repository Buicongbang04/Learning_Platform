#!/usr/bin/env bash
# Xoá cluster kind `mlops` (mọi namespace, model, workflow bên trong mất theo). Không gỡ kind/kubectl.
set -euo pipefail
KIND="$(command -v kind || echo "$HOME/.local/bin/kind")"
[[ -x "$KIND" ]] || { echo "Không thấy kind, không có gì để xoá"; exit 0; }
"$KIND" delete cluster --name mlops

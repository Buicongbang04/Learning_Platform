#!/usr/bin/env bash
# Xoá cluster kind `mlops` (mọi namespace, model, workflow bên trong mất theo). Không gỡ kind/kubectl.
set -euo pipefail
KIND="$HOME/.local/bin/kind"
[[ -x "$KIND" ]] || KIND="$(command -v kind || true)"
[[ -x "$KIND" ]] || { echo "Không thấy kind, không có gì để xoá"; exit 0; }
"$KIND" delete cluster --name mlops

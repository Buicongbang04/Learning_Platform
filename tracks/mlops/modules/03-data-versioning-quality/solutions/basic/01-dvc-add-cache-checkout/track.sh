#!/usr/bin/env bash
set -euo pipefail
FILE="$1"

dvc add "$FILE"
git add "$FILE.dvc" "$(dirname "$FILE")/.gitignore"
git commit -q -m "track $FILE"

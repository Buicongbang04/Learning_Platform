#!/usr/bin/env bash
set -euo pipefail
REV="$1"
FILE="$2"

git checkout "$REV" -- "$FILE.dvc"
dvc checkout "$FILE"

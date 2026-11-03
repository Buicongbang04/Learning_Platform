#!/usr/bin/env bash
set -euo pipefail
URL="$1"
ENDPOINT="$2"
FILE="$3"

dvc remote add -d storage "$URL"
dvc remote modify storage endpointurl "$ENDPOINT"
dvc push "$FILE"

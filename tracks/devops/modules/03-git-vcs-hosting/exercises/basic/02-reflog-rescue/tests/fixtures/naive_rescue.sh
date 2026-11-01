#!/usr/bin/env bash
set -euo pipefail
git branch -f rescue/main 'main@{1}'
git branch -f "$1" '@{-1}'
echo "rescue/main $(git rev-parse rescue/main)"
echo "$1 $(git rev-parse "$1")"

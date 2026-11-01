#!/usr/bin/env bash
set -euo pipefail
git fetch origin
GIT_SEQUENCE_EDITOR=true git rebase -i --autosquash origin/main
git push --force-with-lease origin HEAD

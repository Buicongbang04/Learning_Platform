#!/usr/bin/env bash
set -euo pipefail

usage() {
  echo "Usage: $0 <pid> [timeout_giây]" >&2
  exit 2
}

# TODO 1: kiểm tham số: pid là số nguyên > 1, timeout (mặc định 10) là số nguyên >= 0; sai thì usage
# TODO 2: tiến trình không tồn tại -> exit 1; không có quyền gửi signal -> exit 4
# TODO 3: gửi SIGTERM, chờ tối đa timeout giây (zombie tính là đã dừng) -> "stopped <pid> SIGTERM", exit 0
# TODO 4: quá timeout thì SIGKILL, chờ tiến trình biến mất -> "killed <pid> SIGKILL", exit 3

usage

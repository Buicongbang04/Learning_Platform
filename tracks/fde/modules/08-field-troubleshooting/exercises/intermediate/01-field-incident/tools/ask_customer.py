"""Nhờ IT bệnh viện gõ một lệnh trên máy của họ (qua cảnh đang chạy) và đọc lại output họ dán vào chat.

    uv run python tracks/fde/modules/08-field-troubleshooting/exercises/intermediate/01-field-incident/tools/ask_customer.py "df -h"

Khách chỉ gõ lệnh chỉ đọc theo danh sách trong README của bài, che secret trước khi gửi, và mọi lệnh được ghi vào
`.fde-lab/08-field-incident/ask-log.jsonl`.
"""

import json
import socket
import sys
from pathlib import Path

SOCKET = Path(__file__).resolve().parents[8] / ".fde-lab" / "08-field-incident" / "ask.sock"


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print('cách dùng: ask_customer.py "<một lệnh>"', file=sys.stderr)
        return 2
    if not SOCKET.exists():
        print("Chưa có cảnh nào đang chạy: dựng cảnh trước (README của bài, mục Đề bài).", file=sys.stderr)
        return 2
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as conn:
        conn.settimeout(120)
        conn.connect(str(SOCKET))
        conn.sendall(json.dumps({"command": argv[1]}).encode() + b"\n")
        raw = b""
        while not raw.endswith(b"\n"):
            chunk = conn.recv(65536)
            if not chunk:
                break
            raw += chunk
    reply = json.loads(raw)
    if not reply["allowed"]:
        print(f"IT bệnh viện: không gõ lệnh này được ({reply['output']})")
        return 1
    print(reply["output"], end="" if reply["output"].endswith("\n") else "\n")
    print(f"--- lệnh thứ {reply['count']}/{reply['limit']} khách gõ giúp cho seed này (ghi trong ask-log.jsonl)",
          file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))

"""Gửi báo cáo đồng bộ (JSON) tới dịch vụ audit nội bộ của khách (bản đồng nghiệp viết hôm triển khai thử)."""

import logging
import os
import subprocess
import sys


def main(argv: list[str]) -> int:
    report = argv[1]
    url = os.environ["AUDIT_URL"]
    token = os.environ.get("AUDIT_TOKEN") or open(os.environ["AUDIT_TOKEN_FILE"]).read().strip()
    logging.basicConfig(filename="push_report.log", level=logging.DEBUG)
    logging.debug("gửi %s tới %s, token=%s", report, url, token)
    subprocess.run(["curl", "-sS", "--fail-with-body", "-X", "POST", "-H", f"Authorization: Bearer {token}",
                    "-H", "Content-Type: application/json", "--data-binary", f"@{report}", url], check=True)
    logging.info("đã gửi")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))

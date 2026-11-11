"""Phân loại output `curl -v` / `openssl s_client` / `getent` khách dán vào ticket thành một loại lỗi kết nối."""

import re
import sys

RULES = [
    ("proxy-auth", r"\b407\b|Proxy Authentication Required|Proxy-Authenticate:"),
    ("tls-hostname", r"Hostname mismatch|does not match target host ?name|no alternative certificate subject name"
                     r"|certificate is not valid for"),
    ("tls-ca", r"unable to get local issuer certificate|self[- ]signed certificate|unable to verify the first "
               r"certificate|certificate verify failed|certificate has expired|SSL certificate problem"
               r"|Verification error"),
    ("dns", r"Could not resolve (host|proxy)|Name or service not known|Temporary failure in name resolution"
            r"|nodename nor servname|No address associated with hostname|getaddrinfo"),
    ("route", r"No route to host|Network is unreachable|Network unreachable|errno=113\b|errno=101\b"),
    ("refused", r"Connection refused|errno=111\b"),
    ("timeout", r"timed out|errno=110\b"),
]


def body(text: str) -> tuple[str, list[str]]:
    lines = text.splitlines()
    command = lines[0][2:] if lines and lines[0].startswith("$ ") else ""
    rest = lines[1:] if command else lines
    return command, [line for line in rest if line.strip()]


def classify(text: str) -> str:
    command, lines = body(text)
    joined = "\n".join(lines)
    for name, pattern in RULES:
        if re.search(pattern, joined, re.IGNORECASE):
            return name
    if command.split()[:1] == ["getent"]:
        return "ok" if lines else "dns"
    return "ok"


def main(argv: list[str]) -> int:
    with open(argv[1], encoding="utf-8", errors="replace") as handle:
        print(classify(handle.read()))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))

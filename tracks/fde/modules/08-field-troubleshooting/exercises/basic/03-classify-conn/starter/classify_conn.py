"""Phân loại output `curl -v` / `openssl s_client` / `getent` khách dán vào ticket thành một loại lỗi kết nối."""

import sys


def classify(text: str) -> str:
    raise NotImplementedError


def main(argv: list[str]) -> int:
    with open(argv[1], encoding="utf-8", errors="replace") as handle:
        print(classify(handle.read()))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))

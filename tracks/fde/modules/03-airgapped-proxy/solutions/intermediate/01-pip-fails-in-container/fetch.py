import hashlib
import json
import sys

import requests


def main() -> int:
    if len(sys.argv) != 2:
        print("Cách dùng: fetch.py <url>", file=sys.stderr)
        return 2
    response = requests.get(sys.argv[1], timeout=60)
    response.raise_for_status()
    print(json.dumps({
        "url": sys.argv[1],
        "status": response.status_code,
        "bytes": len(response.content),
        "sha256": hashlib.sha256(response.content).hexdigest(),
        "requests": requests.__version__,
    }))
    return 0


if __name__ == "__main__":
    sys.exit(main())

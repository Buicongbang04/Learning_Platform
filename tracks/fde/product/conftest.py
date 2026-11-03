import sys
from pathlib import Path

PRODUCT = Path(__file__).resolve().parent
for path in (PRODUCT / "src", PRODUCT, PRODUCT / "tests"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

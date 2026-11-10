import json
import sys
from pathlib import Path


def diagnose(text: str, need_mb: int) -> str:
    """text: toàn bộ output (stdout + stderr) của `nvidia-smi`; trả một mã chẩn đoán trong bảng của README."""
    raise NotImplementedError("TODO: chẩn đoán theo bảng trong README")


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("Cách dùng: python diagnose_gpu.py <output nvidia-smi> <need_mb>", file=sys.stderr)
        return 2
    text = Path(argv[0]).read_text(encoding="utf-8", errors="replace")
    print(json.dumps({"diagnosis": diagnose(text, int(argv[1]))}))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

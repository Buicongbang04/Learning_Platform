import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

GENESIS = "0" * 64
ACTIONS = {"set_alias", "delete_alias"}


def _digest(record: dict) -> str:
    body = {k: v for k, v in record.items() if k != "hash"}
    text = json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


class AuditLog:
    def __init__(self, path) -> None:
        self.path = Path(path)

    def entries(self) -> list[dict]:
        if not self.path.exists():
            return []
        lines = self.path.read_text(encoding="utf-8").splitlines()
        return [json.loads(line) for line in lines if line.strip()]

    def head(self) -> str:
        entries = self.entries()
        return entries[-1]["hash"] if entries else GENESIS

    def append(self, actor, action, model, alias, from_version, to_version, reason, at=None) -> dict:
        if not str(actor).strip() or not str(reason).strip():
            raise ValueError("actor và reason không được rỗng")
        if action not in ACTIONS:
            raise ValueError(f"action phải thuộc {sorted(ACTIONS)}")
        entries = self.entries()
        record = {
            "seq": len(entries),
            "at": at or datetime.now(timezone.utc).isoformat(),
            "actor": actor,
            "action": action,
            "model": model,
            "alias": alias,
            "from_version": from_version,
            "to_version": to_version,
            "reason": reason,
            "prev_hash": entries[-1]["hash"] if entries else GENESIS,
        }
        record["hash"] = _digest(record)
        with self.path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(record, ensure_ascii=False) + "\n")
        return record

    def verify(self, anchor=None):
        lines = self.path.read_text(encoding="utf-8").splitlines() if self.path.exists() else []
        lines = [line for line in lines if line.strip()]
        prev = GENESIS
        for index, line in enumerate(lines):
            try:
                record = json.loads(line)
            except ValueError:
                return index
            if not isinstance(record, dict):
                return index
            if record.get("seq") != index or record.get("prev_hash") != prev or record.get("hash") != _digest(record):
                return index
            prev = record["hash"]
        if anchor is not None and prev != anchor:
            return len(lines)
        return None

    def who_promoted(self, model, version) -> list[dict]:
        return [
            r for r in self.entries()
            if r["action"] == "set_alias" and r["alias"] == "champion" and r["model"] == model and r["to_version"] == version
        ]

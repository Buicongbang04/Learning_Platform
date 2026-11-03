from pathlib import Path


class AuditLog:
    def __init__(self, path) -> None:
        self.path = Path(path)

    def append(self, actor, action, model, alias, from_version, to_version, reason, at=None) -> dict:
        """Ghi thêm một dòng JSON vào cuối tệp và trả bản ghi (đã có seq, prev_hash, hash)."""
        # TODO: kiểm actor/reason, đọc dòng cuối để lấy prev_hash, tính hash, mở tệp chế độ "a"
        raise NotImplementedError

    def entries(self) -> list[dict]:
        """Đọc lại toàn bộ log theo thứ tự ghi."""
        # TODO
        raise NotImplementedError

    def head(self) -> str:
        """hash của dòng cuối; "0" * 64 khi log rỗng."""
        # TODO
        raise NotImplementedError

    def verify(self, anchor=None):
        """None nếu nguyên vẹn, ngược lại chỉ số bản ghi đầu tiên không khớp; lệch anchor thì len(entries)."""
        # TODO
        raise NotImplementedError

    def who_promoted(self, model, version) -> list[dict]:
        """Các bản ghi set_alias trên alias champion của model có to_version == version."""
        # TODO
        raise NotImplementedError

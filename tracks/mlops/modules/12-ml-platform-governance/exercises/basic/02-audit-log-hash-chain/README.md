---
title: Audit log append-only cho thao tác registry với hash chain
level: basic
services: []
files:
  - path: starter/auditlog.py
    note: Lớp AuditLog, các phương thức TODO
  - path: tests/test_auditlog.py
    note: Không sửa
run:
  - uv run pytest tracks/mlops/modules/12-ml-platform-governance/exercises/basic/02-audit-log-hash-chain -q
---

## Mục tiêu

Kiểm toán hỏi "ai đã đưa version 3 lên production, lúc nào, vì lý do gì" và muốn chắc câu trả lời chưa bị sửa. Bạn viết một audit log chỉ ghi thêm, mỗi dòng nối với dòng trước bằng hash (hash chain), để sửa hoặc xoá một dòng bất kỳ bị phát hiện, và truy vấn được "ai đã promote".

## Đề bài

Không cần MLflow hay stack. Log là một tệp JSON Lines (mỗi dòng một JSON). Trong `starter/auditlog.py`, lớp `AuditLog(path)`:

1. `append(actor, action, model, alias, from_version, to_version, reason, at=None) -> dict`: ghi thêm một dòng và trả về bản ghi. `action` là `set_alias` hoặc `delete_alias`; `from_version` và `to_version` là `int` hoặc `None` (đổi alias từ không có gì sang v1 thì `from_version = None`). `at` là chuỗi ISO 8601; không truyền thì dùng giờ UTC hiện tại.
2. Mỗi bản ghi có thêm `seq` (0, 1, 2...), `prev_hash` và `hash`. `prev_hash` của bản ghi đầu là `"0" * 64`. `hash` là SHA-256 (hex) của JSON chuẩn tắc của mọi trường **trừ** `hash` (`sort_keys=True`, `separators=(",", ":")`, `ensure_ascii=False`), nên đổi bất kỳ trường nào cũng đổi hash.
3. `entries() -> list[dict]` đọc lại toàn bộ log. `head() -> str` là `hash` của dòng cuối (`"0" * 64` khi log rỗng).
4. `verify(anchor=None) -> int | None`: `None` khi log nguyên vẹn, ngược lại là **chỉ số bản ghi đầu tiên không khớp** (hash sai, `prev_hash` không nối, hoặc `seq` sai). Nếu truyền `anchor` (hash đầu log đã lưu ở nơi khác) mà `head()` khác `anchor` thì trả `len(entries())`, tức log bị cắt bớt hay bị nối lại.
5. `who_promoted(model, version) -> list[dict]`: các bản ghi `set_alias` trên alias `champion` của `model` có `to_version == version`, theo thứ tự thời gian; mỗi phần tử có ít nhất `actor`, `at`, `reason`, `from_version`.

Luật mà test ép:

- `append` từ chối `actor` hoặc `reason` rỗng (chỉ khoảng trắng cũng là rỗng) bằng `ValueError`; log không bị ghi gì khi từ chối.
- `append` chỉ **thêm** vào cuối tệp; các byte đã có không bao giờ bị ghi lại.
- Mỗi bản ghi là một dòng kết thúc bằng `\n`, và chỉ `\n` mới ngăn cách bản ghi: `reason` có thể chứa ký tự như U+2028 (line separator), mà `ensure_ascii=False` ghi nguyên vào tệp; log như vậy vẫn nguyên vẹn với `entries()` và `verify()`. (`str.splitlines()` tách cả ở U+2028, U+2029, `\x85`.)
- Hai đối tượng `AuditLog` cùng một đường dẫn nối tiếp nhau đúng chuỗi (mỗi lần `append` đọc lại dòng cuối từ tệp, không chỉ nhớ trong bộ nhớ).
- Sửa một chữ trong `reason`, xoá một dòng giữa, đổi chỗ hai dòng, hay sửa cả hash của dòng sau cho khớp lại đều bị `verify` báo; chỉ số trả về là bản ghi đầu tiên bị ảnh hưởng.
- Một dòng không còn là JSON object hợp lệ (bị cắt dở, sửa hỏng, hay là `42`) cũng là bản ghi không khớp: `verify` trả chỉ số của dòng đó (đếm như `entries()`, bỏ dòng trống), **không** ném lỗi. Công cụ kiểm tra mà sập đúng lúc log bị phá thì không báo được gì.

## Tiêu chí đạt

- Test pass.
- Giải thích được vì sao hash chain **không** phát hiện việc cắt các dòng cuối nếu không có `anchor`, và anchor nên lưu ở đâu để kẻ sửa log không sửa luôn được.
- Giải thích được vì sao SHA-256 không khoá chỉ chống sửa **một phần**: ai ghi được tệp có thể viết lại cả chuỗi và tính lại mọi hash, `verify()` vẫn trả `None`; chỉ `anchor` lưu ngoài tầm tay họ (hoặc chữ ký/HMAC có khoá) mới bắt được.
- Giải thích được vì sao `who_promoted("taxi-eta", 3)` không đủ khi cần biết ai đang giữ alias hiện tại.

## Gợi ý

### Gợi ý 1

Tách một hàm `_digest(record)` dùng chung cho `append` và `verify`: bỏ khoá `hash`, `json.dumps` với đúng tham số trong đề, mã hoá UTF-8 rồi `hashlib.sha256`. Hai nơi tính khác nhau là nguồn lỗi chính.

### Gợi ý 2

Để đọc dòng cuối mà không đọc cả tệp khi log lớn, có thể đọc ngược; với bài này đọc cả tệp là đủ. Chạy `verify` trên log rỗng phải trả `None`.

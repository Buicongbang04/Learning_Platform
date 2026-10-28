---
title: ABAC policy engine theo tag catalog, có tag propagation và audit
level: advanced
services: []
files:
  - path: starter/abac.py
    note: Tự thiết kế phần thân, giữ nguyên tên lớp, hàm và hằng số
  - path: tests/test_abac.py
    note: Không sửa
run:
  - uv run pytest tracks/data-engineer/modules/10-security-governance/exercises/advanced/02-abac-policy-engine -q
---

## Mục tiêu

Xây một policy engine kiểu tag-based ABAC (giống Snowflake tag-based masking, Unity Catalog ABAC, Apache
Ranger): quyết định allow / mask / deny theo thuộc tính người dùng, tag của cột trong catalog và mục đích
truy vấn; tự lan truyền tag qua column lineage; ghi audit log có lý do.

## Đề bài

Trong `starter/abac.py` đã có `CATALOG` (bảng → cột → tập tag), `TABLE_META` (bảng → `region`),
`PURPOSES` và dataclass `Decision(effect, rule, reason)`.

### 1. `PolicyEngine(catalog, table_meta)`

`evaluate(user, table, column, purpose) -> Decision`. `user` là dict có `id`, `clearance`
(`low|medium|high`), `pii_access` (bool), `region`. Luật áp theo thứ tự, **luật đầu tiên khớp thắng**:

| # | `rule` | Điều kiện | Kết quả |
| --- | --- | --- | --- |
| 1 | `unknown_resource` | Bảng hoặc cột không có trong catalog | `deny` |
| 2 | `invalid_purpose` | `purpose` không thuộc `PURPOSES` | `deny` |
| 3 | `restricted` | Cột có tag `restricted` | `allow` nếu `clearance == "high"` **và** `purpose == "fraud"`, ngược lại `deny` |
| 4 | `pii` | Cột có tag `pii` | `allow` nếu `pii_access` **và** `purpose ∈ {support, fraud}` **và** `user.region` bằng `region` của bảng; ngược lại `mask`. Bảng không có `region` trong `TABLE_META` thì luôn `mask` (fail closed) |
| 5 | `pseudonymized` | Cột có tag `pseudonymized` và `purpose == "marketing"` | `mask` |
| 6 | `quasi_identifier` | Cột có tag `quasi_identifier` và `purpose == "marketing"` | `mask` |
| 7 | `default` | Còn lại | `allow` |

`reason` là câu giải thích ngắn, không rỗng. Mỗi lần `evaluate` thêm một dict vào `engine.audit` với các
khoá `user`, `table`, `column`, `purpose`, `effect`, `rule`, `at` (ISO 8601). `user` trong audit là
`user["id"]`, không phải cả dict.

`authorize_query(user, table, columns, purpose) -> dict[column, Decision]`: đánh giá **mọi** cột (để audit
đủ), nếu có cột `deny` thì raise `PermissionError` nêu tên các cột đó; ngược lại trả dict.

### 2. `propagate_tags(catalog, column_lineage) -> dict`

`column_lineage = {bảng_đích: {cột_đích: {"sources": [(bảng, cột), ...], "transform": ...}}}`. Trả catalog
**mới** gồm bảng cũ và bảng đích (không sửa `catalog` đầu vào). Tag của cột đích tính từ hợp tag các cột nguồn:

| `transform` | Tag cột đích |
| --- | --- |
| `identity` | giữ nguyên hợp tag nguồn |
| `hmac` | bỏ `restricted` và mọi tag bắt đầu bằng `pii`, thêm `pseudonymized` |
| `generalize` | bỏ `restricted` và mọi tag bắt đầu bằng `pii` |
| `aggregate` | rỗng |

Bảng đích có thể là nguồn của bảng đích khác, thứ tự trong dict không đảm bảo: phải xử lý theo thứ tự
phụ thuộc. Transform lạ hoặc cột nguồn không tồn tại → `ValueError`.

## Tiêu chí đạt

- Tests trong `tests/` pass.
- Policy được biểu diễn như **dữ liệu** hoặc danh sách luật rõ ràng, dễ thêm luật mới, không phải một
  khối `if` lồng nhau khó đọc.
- Có giải thích trong docstring: vì sao fail closed, vì sao audit cả quyết định allow.

## Gợi ý

### Gợi ý 1

Mỗi luật là một hàm `(ctx) -> Decision | None`; engine duyệt list luật, trả quyết định đầu tiên khác
`None`. `ctx` gom `user`, `tags`, `purpose`, `table_region`.

### Gợi ý 2

Với `propagate_tags`: lặp nhiều vòng, mỗi vòng xử lý các bảng đích mà mọi bảng nguồn đã có trong catalog
kết quả; vòng nào không tiến thêm được mà vẫn còn bảng chưa xử lý thì báo `ValueError`. `copy.deepcopy`
để không sửa đầu vào.

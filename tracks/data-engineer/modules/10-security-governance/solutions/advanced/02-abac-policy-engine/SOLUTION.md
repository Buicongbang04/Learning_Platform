# Hướng dẫn: ABAC policy engine theo tag catalog

Không có đáp án duy nhất. Dưới đây là hướng làm, quyết định thiết kế và rubric.

## Hướng làm

### Policy là danh sách luật

```python
Rule = Callable[[dict], Decision | None]

def rule_restricted(ctx):
    if "restricted" in ctx["tags"]:
        ok = ctx["user"].get("clearance") == "high" and ctx["purpose"] == "fraud"
        return Decision("allow" if ok else "deny", "restricted",
                        "Cột restricted chỉ mở cho clearance high với purpose fraud")
    return None

RULES = [rule_restricted, rule_pii, rule_pseudonymized, rule_quasi_identifier]
```

`evaluate` kiểm tra hai luật "cổng" trước (`unknown_resource`, `invalid_purpose`), dựng `ctx`
(`user`, `tags`, `purpose`, `table_region = table_meta.get(table, {}).get("region")`), duyệt `RULES`, luật
đầu tiên trả khác `None` thắng, không có thì `Decision("allow", "default", ...)`. Cuối cùng **luôn** ghi audit.

Thêm luật mới (vd. giờ hành chính, thiết bị được quản lý) = thêm một hàm vào list, không sửa luật cũ.
Có thể đi xa hơn: luật dạng dữ liệu (YAML/JSON) hoặc Rego cho Open Policy Agent.

### Tag propagation

1. `out = copy.deepcopy(catalog)`, `pending = dict(column_lineage)`.
2. Lặp: mỗi vòng chọn các bảng đích mà mọi bảng nguồn đã có trong `out`; với mỗi cột, hợp tag các cột nguồn
   (cột nguồn thiếu → `ValueError`), áp hàm transform từ bảng `TRANSFORMS` (transform lạ → `ValueError`).
3. Vòng không tiến thêm mà `pending` còn → vòng lặp phụ thuộc hoặc bảng nguồn không tồn tại → `ValueError`.

```python
def _strip_pii(tags):
    return {t for t in tags if t != "restricted" and not t.startswith("pii")}

TRANSFORMS = {
    "identity": set,
    "hmac": lambda t: _strip_pii(t) | {"pseudonymized"},
    "generalize": _strip_pii,
    "aggregate": lambda t: set(),
}
```

## Quyết định thiết kế cần cân nhắc

| Vấn đề | Lựa chọn trong bài | Lý do / đánh đổi |
| --- | --- | --- |
| Không tìm thấy tài nguyên | `deny` | Fail closed: thiếu metadata không được thành lỗ hổng |
| Bảng dẫn xuất chưa có `region` | `mask` PII | Không chứng minh được data residency thì không mở plaintext |
| Nhiều luật cùng khớp | Luật đầu tiên thắng, thứ tự từ nghiêm ngặt tới lỏng | Dễ đoán; cách khác là "deny overrides" (gom mọi luật, deny thắng) |
| Một cột bị deny trong query | Từ chối cả query | Tránh kết quả "thiếu cột" lặng lẽ; vẫn audit mọi cột |
| Audit cả `allow` | Có | Điều tra sự cố cần biết ai **đã** đọc PII, không chỉ ai bị chặn |
| `hmac` bỏ tag `pii` | Có, thêm `pseudonymized` | Theo GDPR dữ liệu pseudonymized vẫn là dữ liệu cá nhân: giữ tag riêng để luật marketing vẫn mask |
| `generalize` | Bỏ PII nhưng giữ `quasi_identifier` của nguồn | Zip 3 số vẫn góp phần re-identify khi kết hợp |
| `identity` từ nhiều nguồn | Hợp tag | Cột ghép email + cpf mang mức nhạy cảm cao nhất (`restricted`) |

Mở rộng: column-level lineage lấy tự động từ `sqlglot.lineage` hoặc OpenLineage `columnLineage` facet;
sinh masking policy thật cho Snowflake/Unity Catalog từ engine; cache quyết định theo (user, tag-set, purpose).

## Rubric (10 điểm)

| Tiêu chí | Điểm |
| --- | --- |
| Tests pass | 3 |
| Luật được tổ chức dễ mở rộng (list hàm hoặc dữ liệu), không phải `if` lồng nhau | 2 |
| Fail closed nhất quán (resource lạ, purpose lạ, thiếu region, thiếu thuộc tính user) | 1.5 |
| Tag propagation đúng thứ tự phụ thuộc, phát hiện vòng, không sửa đầu vào | 1.5 |
| Audit đầy đủ, không chứa dữ liệu nhạy cảm, `reason` hữu ích cho người đọc | 1 |
| Giải thích quyết định thiết kế trong docstring (first-match vs deny-overrides, vì sao audit allow) | 1 |

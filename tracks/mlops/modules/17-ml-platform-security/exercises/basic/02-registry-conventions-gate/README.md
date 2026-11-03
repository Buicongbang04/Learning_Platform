---
title: Cổng đăng ký model - quy ước tên, tag bắt buộc, model card, quyền theo đội
level: basic
services: []
files:
  - path: starter/registry_gate.py
    note: 6 TODO
  - path: tests/test_registry_gate.py
    note: Không sửa
run:
  - uv run pytest tracks/mlops/modules/17-ml-platform-security/exercises/basic/02-registry-conventions-gate -q
---

## Mục tiêu

Khi năm đội cùng dùng một registry, quy ước chỉ có giá trị nếu có cổng kiểm. Bạn viết cổng self-service: đội nào cũng tự đăng ký model
được, miễn là tên đúng quy ước, đủ tag để biết ai chịu trách nhiệm và ai trả tiền, có model card, và chỉ đăng ký trong không gian tên của
đội mình. Cổng thứ hai là audit: tìm các version đã lọt vào registry bằng đường vòng (gọi thẳng MLflow).

## Đề bài

Một yêu cầu đăng ký là dict:

```python
{"name": "pricing-tip-amount",
 "tags": {"owner": "lan.nguyen@example.com", "team": "pricing", "cost_center": "CC-2041"},
 "model_card": "# ...\n\n## Intended use\n...",
 "requested_by": {"user": "lan", "team": "pricing"}}
```

`check_request(request)` trả **danh sách mã vi phạm đã sắp xếp** (`sorted`), rỗng khi hợp lệ, và không sửa `request`. Mã và luật:

| Mã | Khi nào |
| --- | --- |
| `name` | tên không khớp `<team>-<phần còn lại>` với `<team>` thuộc `TEAMS`, phần còn lại là các cụm `[a-z0-9]+` nối bằng `-`; hoặc dài quá 64 ký tự |
| `tag-missing:<khoá>` | thiếu `owner`, `team` hay `cost_center`, hoặc giá trị rỗng sau khi bỏ khoảng trắng hai đầu |
| `tag-invalid:<khoá>` | `owner` không phải email (`^[^@\s]+@[^@\s]+\.[a-z]{2,}$`), `team` không thuộc `TEAMS`, `cost_center` không khớp `^CC-[0-9]{4}$` (so sau khi bỏ khoảng trắng hai đầu) |
| `team-mismatch` | tên hợp lệ, tag `team` hợp lệ nhưng khác tiền tố của tên |
| `permission` | có `requested_by`, tên hợp lệ, và đội người gửi khác tiền tố của tên và khác `platform` |
| `model-card-missing` | không có model card, hoặc chỉ có khoảng trắng |
| `model-card-section:<Tên>` | model card thiếu heading cấp 2 (`## Tên`) cho một phần trong `CARD_SECTIONS`; so không phân biệt hoa thường, bỏ khoảng trắng cuối |

`requested_by` vắng hoặc `None` thì không kiểm quyền (dùng cho audit).

`register_if_allowed(client, request, source)`: có vi phạm thì trả `(None, vi_phạm)` và **không ghi gì** vào registry. Hợp lệ thì tạo
registered model (nếu chưa có) với ba tag bắt buộc, tạo model version từ `source` với ba tag đó và `description` là model card, trả
`(số version dạng chuỗi, [])`, ví dụ `("1", [])`.

`audit_registry(client)` duyệt **mọi model version** trên registry, kiểm như `check_request` (tag của version, `description` làm model
card, không kiểm quyền), trả dict `{"<tên>/<version>": [mã vi phạm]}` chỉ gồm version vi phạm.

Test dùng registry MLflow SQLite trong thư mục tạm (`mlopskit.mlflow_local`), không cần stack. Bảng ca của test so **đúng** danh sách
mã.

## Tiêu chí đạt

- `uv run pytest tracks/mlops/modules/17-ml-platform-security/exercises/basic/02-registry-conventions-gate -q` pass.
- Bạn giải thích được vì sao cần cả cổng lúc đăng ký và audit định kỳ, và vì sao `team-mismatch` không phải lỗi cú pháp mà là lỗi
  quyền sở hữu.
- Bạn nêu được cách ép quyền thật trên registry (không chỉ trong code cổng): quyền theo registered model của MLflow, hoặc catalog
  có phân quyền như Unity Catalog (module README mục 2).

## Gợi ý

### Gợi ý 1

Tách nhỏ: một hàm lấy đội từ tên (trả `None` khi tên sai), một hàm kiểm model card. `check_request` chỉ gom kết quả rồi `sorted`.

### Gợi ý 2

`client.search_model_versions()` không có bộ lọc trả mọi version; mỗi version có `.name`, `.version`, `.tags`, `.description`.

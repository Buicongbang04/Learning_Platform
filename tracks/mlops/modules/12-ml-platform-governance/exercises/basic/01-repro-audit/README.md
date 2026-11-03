---
title: Audit tái lập một model trong registry - thiếu commit, data, lockfile hay seed
level: basic
services: []
files:
  - path: starter/audit.py
    note: 3 hàm TODO
  - path: tests/test_audit.py
    note: Không sửa
run:
  - uv run pytest tracks/mlops/modules/12-ml-platform-governance/exercises/basic/01-repro-audit -q
---

## Mục tiêu

Từ một model đang nằm trong registry, truy ngược được run đã tạo ra nó và biết run đó có đủ bốn thứ để dựng lại hay không: commit code, phiên bản dữ liệu, hash lockfile và seed. Bạn viết hàm audit trả về đúng những gì **thiếu hoặc không đáng tin**, thay vì chỉ trả "ok".

## Đề bài

Bài chạy trên MLflow cục bộ (SQLite trong thư mục tạm, không cần stack). Trong `starter/audit.py`:

1. `audit_run(tracking_uri, run_id) -> list[str]`: danh sách các mục không đạt, theo thứ tự `commit`, `data_version`, `lockfile_hash`, `seed`; rỗng nghĩa là run đủ điều kiện tái lập. Luật mà test ép:
   - `commit` đạt khi tag `git_commit` là đúng 40 ký tự hex thường **và** tag `git_dirty` bằng `"false"`. Thiếu tag, commit rút gọn, hay cây thư mục bẩn đều là không đạt.
   - `data_version` đạt khi tag `data_version` có giá trị không rỗng và không thuộc `unknown`, `none`, `latest`, `n/a` (không phân biệt hoa thường): các giá trị đó trỏ vào thứ đổi được theo thời gian.
   - `lockfile_hash` đạt khi tag `lockfile_sha256` là đúng 64 ký tự hex thường.
   - `seed` đạt khi param `seed` là một số nguyên (chuỗi như `"42"` hoặc `"-1"` đều được đọc là số nguyên; `"None"` hay `"random"` thì không).
2. `run_of_version(tracking_uri, model_name, version) -> str`: `run_id` của run tạo ra version đó. Version không tồn tại hoặc không có run nguồn thì `LookupError` nêu tên model và version.
3. `audit_model(tracking_uri, model_name, version) -> dict`: `{"run_id": ..., "missing": [...], "reproducible": bool}`; `reproducible` là `True` khi `missing` rỗng.

## Tiêu chí đạt

- Bảng ca trong test (run đủ, từng mục thiếu riêng lẻ, nhiều mục cùng thiếu, giá trị "có mặt nhưng vô nghĩa") đều khớp.
- Audit không ghi gì vào run hay registry (chỉ đọc).
- `audit_model` đi đúng từ version tới run, không đoán theo "run mới nhất".
- `run_of_version` báo `LookupError` rõ ràng thay vì lỗi MLflow thô.

## Gợi ý

### Gợi ý 1

`client.get_model_version(name, version).run_id` cho run nguồn; `client.get_run(run_id).data.tags` và `.params` cho phần còn lại. Dùng `re.fullmatch` cho hex để `"abc123 "` có khoảng trắng thừa không lọt qua.

### Gợi ý 2

Viết mỗi mục thành một hàm kiểm nhỏ trả `bool`, rồi gom bằng một vòng lặp theo thứ tự cố định. Hàm audit nên không có nhánh đặc biệt cho từng ca của test.

---
title: Dựng lineage graph từ danh sách câu SQL
level: intermediate
services: []
files:
  - path: starter/lineage.py
    note: 5 TODO
  - path: tests/test_lineage.py
    note: Không sửa
  - path: tests/fixtures/pipeline.sql
    note: Pipeline mẫu raw -> staging -> mart -> reporting
run:
  - uv run pytest tracks/data-engineer/modules/10-security-governance/exercises/intermediate/02-lineage-from-sql -q
---

## Mục tiêu

Hiểu table-level lineage được sinh ra thế nào bằng cách tự parse SQL: tìm bảng đích và bảng nguồn, dựng
graph, rồi dùng nó cho impact analysis (downstream), root cause (upstream) và thứ tự chạy (topological sort).

## Đề bài

Hoàn thiện `starter/lineage.py` (không dùng thư viện parse SQL, chỉ `re`):

1. `parse_statement(sql)` trả `(target, sources)` với `sources` là `set[str]`, hoặc `None` nếu câu không
   ghi vào bảng nào (vd. `SELECT` thuần). Hỗ trợ:
   - `CREATE [OR REPLACE] [TEMP|TEMPORARY] TABLE|VIEW [IF NOT EXISTS] <tên> AS ...`
   - `INSERT INTO <tên> [(cột, ...)] ...`
   - Không phân biệt hoa thường. Tên chuẩn hoá về chữ thường, bỏ dấu `"`: `"raw"."customers"` → `raw.customers`.
   - Nguồn là tên đứng sau `FROM` hoặc `JOIN` (mọi kiểu join). **Bỏ qua**: tên CTE khai báo trong `WITH`,
     subquery `(`, hàm bảng như `read_parquet('...')`, nội dung comment `--` và `/* */`, chuỗi `'...'`,
     và `FROM` bên trong `EXTRACT(... FROM ...)`. Không tính bảng đích là nguồn của chính nó.
2. `build_graph(statements)` nhận list câu SQL, trả `dict[target, set[sources]]` (gộp nếu một bảng được ghi
   bởi nhiều câu). Câu trả `None` bị bỏ qua.
3. `upstream(graph, table)`: tập **mọi** bảng tổ tiên (đệ quy), không gồm chính nó.
4. `downstream(graph, table)`: tập mọi bảng hậu duệ (đệ quy), không gồm chính nó.
5. `run_order(graph)`: list các **target** theo thứ tự chạy được (nguồn trước đích). Khi nhiều target cùng
   sẵn sàng, chọn tên nhỏ nhất theo thứ tự chữ cái (để kết quả ổn định). Có vòng lặp thì `ValueError`.

Hàm `split_statements(script)` (tách theo `;`) đã có sẵn để test đọc `tests/fixtures/pipeline.sql`.

## Tiêu chí đạt

- Graph của `pipeline.sql` đúng 6 target với nguồn đúng, không lẫn CTE, hàm, comment.
- `upstream`/`downstream` đệ quy đúng.
- `run_order` đúng thứ tự và phát hiện được vòng lặp.
- Test pass.

## Gợi ý

### Gợi ý 1

Làm sạch trước rồi mới tìm: xoá comment (`re.sub(r"--[^\n]*", "", sql)`, `re.sub(r"/\*.*?\*/", "", sql, flags=re.S)`),
thay chuỗi `'...'` bằng `''`, xoá `EXTRACT\s*\([^()]*\)`. Sau đó `re.findall(r"\b(?:FROM|JOIN)\s+([\w.\"]+)\b(?!\s*\()", sql, re.I)`.

### Gợi ý 2

Tên CTE: `re.findall(r"(?:\bWITH|,)\s*(?:RECURSIVE\s+)?([\w\"]+)\s+AS\s*\(", sql, re.I)`.
Topological sort: thuật toán Kahn, dùng `heapq` cho tập target sẵn sàng; nguồn không phải target (bảng raw)
coi như đã có sẵn.

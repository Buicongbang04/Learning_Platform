# Quy ước nội dung

App học tập đọc thẳng các tệp trong `tracks/`. Viết đúng quy ước dưới đây thì nội dung tự hiện
trong app, không phải sửa code. Thêm một mảng mới (Data Science, MLOps…) cũng chỉ là thêm một
thư mục theo đúng cấu trúc này.

## Cấu trúc thư mục

```
tracks/
└── <track-id>/                      # vd. data-engineer, data-science, mlops
    ├── track.json                   # khai báo track: tên, icon, thứ tự module, capstone
    ├── README.md                    # tổng quan lộ trình + sơ đồ mermaid
    ├── modules/
    │   └── <NN-module-id>/          # vd. 03-nosql (id phải trùng track.json)
    │       ├── README.md            # lý thuyết; mỗi heading `## ` là một phần đánh dấu "đã đọc"
    │       ├── interview.md         # câu hỏi phỏng vấn; mỗi heading `## ` là một câu hỏi
    │       ├── exercises/
    │       │   ├── basic/<NN-slug>/
    │       │   ├── intermediate/<NN-slug>/
    │       │   └── advanced/<NN-slug>/
    │       └── solutions/           # cùng cây với exercises/
    │           ├── basic/<NN-slug>/
    │           ├── intermediate/<NN-slug>/
    │           └── advanced/<NN-slug>/
    └── capstone/
        ├── README.md
        └── milestones/<mNN-slug>.md
```

## `track.json`

```json
{
  "id": "data-science",
  "name": "Data Science",
  "icon": "flask-conical",
  "status": "active",
  "order": 3,
  "description": "Một câu mô tả track.",
  "modules": [
    { "id": "01-statistics", "title": "Thống kê", "summary": "…", "topics": ["Xác suất", "Kiểm định"] }
  ],
  "capstone": {
    "title": "Tên dự án",
    "readme": "capstone/README.md",
    "milestones": [
      { "id": "m01", "title": "…", "after": "01-statistics", "doc": "capstone/milestones/m01-….md" }
    ]
  }
}
```

- `icon`: tên icon [lucide](https://lucide.dev/icons) (kebab-case).
- `status`: `active` hoặc `soon`. Track `soon` chỉ cần `id`, `name`, `icon`, `status`, `order`. App hiện nó là "Sắp có".
- `capstone` là tuỳ chọn.

## Lý thuyết: `modules/<id>/README.md`

- Dòng đầu là `# Tên module`, sau đó một đoạn mở đầu ngắn.
- **Mỗi `## ` là một phần**, có ô "đã đọc" riêng trong app. Đánh số: `## 1. Khi nào cần NoSQL`.
  Nên có 5–8 phần. Heading con dùng `###`.
- Viết tiếng Việt, giữ thuật ngữ tiếng Anh (partition, idempotent, Slowly Changing Dimension…).
- Có sơ đồ bằng khối ` ```mermaid ` (ít nhất 2 sơ đồ mỗi module), bảng so sánh, code mẫu chạy được.
- Phần cuối là `## N. Tài liệu tham khảo`, liệt kê link gốc (docs chính thức, sách, bài viết uy tín).
- Ví dụ dùng dữ liệu Olist (orders, customers, sellers, products, order_items, payments, reviews)
  khi hợp lý, để nối với capstone.

## Câu hỏi phỏng vấn: `modules/<id>/interview.md`

```markdown
# Câu hỏi phỏng vấn: NoSQL

## Giải thích CAP theorem. Cassandra và MongoDB chọn gì?

Câu trả lời mẫu, vài đoạn, có thể kèm bảng hoặc code.

## Câu hỏi tiếp theo…
```

Ít nhất 12 câu, từ cơ bản tới câu hỏi thiết kế hệ thống.

## Bài tập: `exercises/<level>/<NN-slug>/`

```
02-cassandra-query-model/
├── README.md            # đề bài, có frontmatter
├── starter/             # code khung có TODO, người học sửa ở đây
│   ├── schema.cql
│   └── load.py
└── tests/
    ├── test_queries.py
    └── fixtures/        # dữ liệu nhỏ cho test (tuỳ chọn)
```

### Frontmatter của `README.md`

```markdown
---
title: Thiết kế bảng Cassandra theo truy vấn đơn hàng
level: intermediate
services: [cassandra]
files:
  - path: starter/schema.cql
    note: 3 TODO
  - path: starter/load.py
    note: 2 TODO
  - path: tests/test_queries.py
    note: Không sửa
run:
  - docker compose -f setup/docker-compose.yml up -d cassandra
  - uv run pytest tracks/data-engineer/modules/03-nosql/exercises/intermediate/02-cassandra-query-model -q
---

## Mục tiêu

Một hai câu: làm xong bài này bạn biết gì.

## Đề bài

Mô tả việc cần làm, đủ để tự làm không cần hỏi thêm.

## Tiêu chí đạt

- Mỗi dòng một tiêu chí kiểm được.

## Gợi ý

### Gợi ý 1

Gợi ý nhẹ.

### Gợi ý 2

Gợi ý sát hơn.
```

- `level`: `basic`, `intermediate` hoặc `advanced`.
- `services`: dịch vụ Docker cần chạy (tên trùng `setup/docker-compose.yml`), để trống nếu không cần.
- `run`: các lệnh chạy từ thư mục gốc repo. App hiện mỗi lệnh kèm nút chép.
- Không viết đề bài ngoài các heading `## Mục tiêu`, `## Đề bài`, `## Tiêu chí đạt`, `## Gợi ý`.

### Starter và test

- Starter chạy được nhưng chưa đúng: hàm có `# TODO` và `raise NotImplementedError`, hoặc SQL có
  `-- TODO`. Chạy test trên starter phải **fail** (hoặc skip nếu thiếu dịch vụ), không lỗi cú pháp.
- Test dùng `testkit.Exercise` (xem `testkit.py` ở gốc repo):

  ```python
  from testkit import Exercise

  ex = Exercise(__file__)

  def test_revenue_by_state():
      transform = ex.module("transform.py")     # starter/transform.py hoặc lời giải
      assert transform.revenue_by_state(...) == ...
  ```

- Ưu tiên test chạy được không cần Docker (DuckDB, SQLite, pandas, mongomock, fakeredis,
  PySpark local). Bài cần dịch vụ thật thì gọi `ex.require_service("postgres")` để tự skip khi chưa bật.
- Dữ liệu test nhỏ, đặt trong `tests/fixtures/` hoặc tạo trong test. Không phụ thuộc bộ Olist thật.

### Lời giải: `solutions/<level>/<NN-slug>/`

- **Basic và Intermediate**: `SOLUTION.md` giải thích cách làm và vì sao, cộng các tệp lời giải
  **trùng tên với tệp trong `starter/`**. `SOLUTION=1 uv run pytest <thư mục bài> -q` phải pass.
- **Advanced**: chỉ `SOLUTION.md` gồm hướng làm, các quyết định thiết kế cần cân nhắc và rubric
  chấm điểm. Bài Advanced không có một đáp án duy nhất.

## Capstone: `capstone/milestones/<mNN-slug>.md`

Mỗi milestone gồm: `# Tiêu đề`, `## Mục tiêu`, `## Việc cần làm` (danh sách), `## Kết quả nộp`,
`## Tiêu chí đạt` (checklist). Code của capstone nằm ở `capstone/project/`.

## Dịch vụ Docker dùng chung

Định nghĩa ở `setup/docker-compose.yml`. Thông số kết nối (khớp `testkit.py`):

| Dịch vụ | Cổng | Đăng nhập |
| --- | --- | --- |
| postgres | 5432 | user `de`, mật khẩu `de`, database `de` |
| mongo | 27017 | không |
| redis | 6379 | không |
| cassandra | 9042 | không |
| neo4j | 7687 (bolt), 7474 (web) | `neo4j` / `password123` |
| minio | 9000 (S3 API), 9001 (console) | `minioadmin` / `minioadmin` |
| kafka | 9094 (từ máy host) | không |
| airflow | 8080 | `airflow` / `airflow` |
| metabase | 3000 | tạo lúc mở lần đầu |

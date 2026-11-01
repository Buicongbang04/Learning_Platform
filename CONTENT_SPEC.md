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
- Công thức toán viết bằng LaTeX trong `$$...$$`: đặt giữa câu là công thức trong dòng, tách thành
  đoạn riêng là công thức khối. Không dùng `$...$` một dấu (app tắt để `$0.10` vẫn là tiền). Áp dụng
  cho mọi tệp markdown (lý thuyết, interview, đề bài, `SOLUTION.md`). Đừng viết công thức trong khối code.
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

### Bài tập notebook (`.ipynb`)

Dùng khi bài là phân tích / modeling, như cách Data Scientist làm việc thật. Bài thuần logic vẫn dùng `.py`.

- Starter là `starter/<tên>.ipynb`; test gọi `ex.notebook("<tên>.ipynb")` và dùng kết quả như một module.
- **Cell chấm điểm chỉ định nghĩa hàm hoặc hằng**, thân hàm `# TODO` + `raise NotImplementedError`.
  Không gọi tính toán ở top-level, để starter vẫn nạp được và test FAIL chứ không ERROR. Ngoại lệ:
  `import` và cấu hình môi trường không thể lỗi (biến môi trường, bộ lọc cảnh báo, mức log).
- **Cell gắn tag `explore`** (đọc dữ liệu thật, vẽ biểu đồ, gọi hàm để xem) bị bỏ qua khi chấm. Dòng đầu
  cell nên là `# explore: ...` để người dùng VS Code thấy được. Tìm gốc repo trong notebook bằng
  `ROOT = next(p for p in [Path.cwd(), *Path.cwd().parents] if (p / "pyproject.toml").exists())`.
- Khi chấm: dòng magic/shell thành `pass`, cell `%%...` bị bỏ, `display` là `print`; lỗi báo theo
  `tên.ipynb[cell N]`.
- Commit notebook **không có output**. Lời giải Basic/Intermediate là notebook trùng tên trong `solutions/`,
  phải chạy được toàn bộ (kể cả cell `explore`) khi đã tải dữ liệu:
  `uv run jupyter nbconvert --to notebook --execute --stdout <notebook> > /dev/null`.

#### Bài chỉ có trắc nghiệm

Bài đọc hiểu / chọn phương án, không có code để chạy (vd. track Data Analyst, module đọc biểu đồ).

- Có `README.md` (frontmatter `files: []`, `run: []`), `exercises/<level>/<slug>/quiz.yaml` và
  `solutions/<level>/<slug>/quiz-answers.yaml` kèm `SOLUTION.md` giải thích từng đáp án.
- Không có `starter/` và `tests/`. App nhận ra bài này khi `files` không có tệp nào bắt đầu bằng `starter/` hoặc `tests/`,
  và hiện card giới thiệu (có nút "Đánh dấu hoàn thành") cùng card trắc nghiệm thay cho trình soạn code.

#### Bài Excel

Bài làm trong workbook (`.xlsx`, `.xlsm`, `.ods`) thay cho code Python.

- Workbook nằm trong `starter/` và được liệt kê trong `files:` như mọi tệp starter (vd. `starter/sales.xlsx`). Workbook commit vào repo chỉ chứa trích mẫu từ bộ dữ liệu cho phép phân phối lại; ghi nguồn trong sheet `README` của workbook và trong đề.
- App không mở tệp nhị phân (`.xlsx`, `.xlsm`, `.xls`, `.ods`, `.docx`, `.pdf`, ảnh) như text: server trả mục `{ path, binary: true }` không có `content`, Workspace hiện dòng "Tệp nhị phân — mở bằng LibreOffice/Excel" kèm đường dẫn để chép và nút "Mở bằng ứng dụng mặc định" (`xdg-open`, chỉ nhận tệp trong `starter/` của bài).
- Bài có `tests/` (đọc giá trị đã tính trong workbook) là bài `code` bình thường: người học điền, lưu, bấm "Chạy test".
- Bài `.xlsx` không có `tests/` và không có tệp text nào trong `starter/` thì đề bài và `quiz.yaml` là phần chấm chính.

#### Quiz trên bài không phải notebook

Bài `code` (có `starter/` hoặc `tests/`, kể cả bài Excel) có `exercises/<level>/<slug>/quiz.yaml` thì app hiện thẻ trắc nghiệm ngay dưới Workspace (định dạng và quy tắc như ở "Notebook dữ liệu thật" bên dưới, kèm `solutions/.../quiz-answers.yaml`). Không có `quiz.yaml` thì không hiện gì.

- Tiêu chí chọn kiểu thẻ (`quizVariantOf` trong `app/src/code/exerciseKind.ts`): **main** ("Trắc nghiệm", không nhãn "Tuỳ chọn") khi `files` có `starter/` mà mọi tệp starter đều là tệp nhị phân và không có `tests/`; mọi trường hợp khác là **optional** ("Báo cáo bài học", nhãn "Tuỳ chọn").
- Bài chỉ có trắc nghiệm (`files: []`) và bài notebook giữ nguyên cách hiện cũ.

### Dữ liệu thật

- Notebook thực hành dùng bộ dữ liệu thật. Thêm bộ mới vào registry `DATASETS` trong
  `data/download_dataset.py` (ghi nguồn, giấy phép) và bảng trong `data/README.md`.
- Test lấy thư mục bộ dữ liệu bằng `ex.dataset("<tên>")` (trả `data/raw/<tên>/`, tự skip nếu chưa tải).
  Test trên dữ liệu thật kiểm so với con số đã biết; mọi test còn lại dùng dữ liệu nhỏ sinh trong test.
- Không commit mẫu trích từ bộ có giấy phép chưa rõ.

### Notebook dữ liệu thật của track Data Engineer

Các bài notebook dữ liệu thật của track DE (module 00, capstone Bước 0 và các bài tương tự ở module khác) làm việc trên dữ liệu thật, không chỉ chấm hàm. Quy ước thêm
(phần chung xem ở trên):

- Cell đầu đưa gốc repo vào `sys.path` rồi gọi `ensure("<tên>")` từ `data/download_dataset.py`
  (tải atomic, không tải lại khi đã có `data/raw/<tên>/`).
- Cell đọc dữ liệu thật, vẽ, in là cell `explore`; chỉ cell định nghĩa hàm/hằng có tên cố định mới được chấm.
- Mỗi bài có 4 sản phẩm: dữ liệu sạch, insight có số, biểu đồ, và **trắc nghiệm bài học** (thay cho báo cáo `report.md`,
  không còn `starter/report.md`; README chỉ nhắc "làm phần trắc nghiệm trong app sau khi chạy notebook").
- Trắc nghiệm gồm `exercises/<level>/<slug>/quiz.yaml` (câu hỏi) và `solutions/<level>/<slug>/quiz-answers.yaml`
  (đáp án, app chỉ đọc sau khi nộp). Bài không có `quiz.yaml` thì không hiện card trắc nghiệm.

  ```yaml
  # quiz.yaml
  questions:
    - id: peak-day            # duy nhất trong bài
      kind: data              # data (số liệu từ bộ dữ liệu) | knowledge (kiến thức, khái niệm)
      type: single            # single (đúng một đáp án) | multi (>= 1 đáp án)
      prompt: "Ngày nào trong tháng 7/1995 có nhiều request nhất?"
      options:                # >= 2 lựa chọn
        - { id: a, text: "1/7" }
        - { id: b, text: "13/7" }
  # quiz-answers.yaml
  peak-day: [b]
  ```

  Ban đầu mỗi bài 5-8 câu, chia đôi kiến thức / dữ liệu khi có thể. Câu `data` phải có đáp án cố định trên
  dữ liệu đã ghim; bài dùng dữ liệu không tái lập (vd. stream người học tự ghi) chỉ có câu `knowledge`.
  `tests/test_quiz_files.py` kiểm định dạng (id duy nhất, mỗi câu có đáp án thuộc lựa chọn, `single` đúng một đáp án).
  Thêm hoặc sửa câu: sửa `quiz.yaml` và `quiz-answers.yaml` cùng lúc, rồi chạy `UV_NO_SYNC=1 uv run pytest tests/test_quiz_files.py -q`.
  Quy tắc độ dài: với câu `single` có >= 3 lựa chọn, số câu mà đáp án đúng là lựa chọn dài nhất hẳn (theo ký tự)
  không được vượt `max(1, n // 3)` (n = số câu `single` có >= 3 lựa chọn trong bài), để người học không đoán được bằng độ dài; viết lại lựa chọn cho độ dài gần nhau.
  Giữ nguyên `id` câu và lựa chọn khi sửa: app lưu kết quả theo hash nội dung `quiz.yaml`, nên đổi chữ trong câu hỏi
  làm kết quả đã lưu của bài đó mất hiệu lực (người học làm lại), và đổi `id` làm lệch với `quiz-answers.yaml`.
- Test trên dữ liệu thật tự skip khi chưa tải (hoặc thiếu mạng); test còn lại chạy trên dữ liệu nhỏ sinh trong test.

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
| metabase | 3000 | `admin@example.com` / `DeLearning-Admin1` (tạo bằng `setup/bi/init_bi.py`) |
| superset | 8088 | `admin` / `admin` |
| localstack | 4566 (giả lập AWS: s3, iam, sts) | access key `test` / `test` |
| mailpit (profile `devops`) | 11025 (SMTP), 18025 (web và API), chỉ mở trên `127.0.0.1` | không |

`mailpit` chỉ bật khi gọi kèm `--profile devops`, nên `docker compose up -d` của các track khác không dựng nó.

## Track DevOps

Quy ước riêng của `tracks/devops/`, bổ sung cho phần chung ở trên. Validator `tests/test_devops_track.py` kiểm phần
lớn các quy tắc này. Chi tiết API xem docstring trong `testkit.py`, không chép lại ở đây.

### Test chạy gì, bằng helper nào

| Test cần | Dùng | Đảm bảo |
| --- | --- | --- |
| Chạy script hay chương trình của người học trên máy host | `testkit.run_sandboxed(cmd, writable=[tmp_path], cwd=tmp_path, env={...})` (cần stdin/stdout dạng bytes hay `Popen` thì `sandbox_command`) | bwrap: `/` chỉ đọc, `/tmp` và `/run` là tmpfs rỗng, `~/.docker` bị che, chỉ các thư mục trong `writable` ghi được, `HOME` là `cwd`, env dựng lại từ đầu (`PATH`, `HOME`, `LANG`/`LC_ALL` cộng những gì test truyền). Mạng **không** tách. Không dùng được bwrap thì skip, **không bao giờ** chạy trần |
| Container do test dựng | `with DockerLab() as lab:` (fixture: dựng container bên trong `with`, rồi `yield lab`) | `--rm`, nhãn `devops-ex=1`, tên `devops-ex-<uuid8>-<alias>`, giới hạn RAM và số tiến trình, cpuset theo `docker_cpu_args()`, cổng chỉ trên `127.0.0.1` ở cổng trống, mount `:ro`, network riêng; lỗi hay Ctrl-C ở bất kỳ bước nào cũng dọn hết |
| Gọi `docker` thẳng (`subprocess.run(["docker", ...])`, `_docker(`) trong test của module | Cấm | Validator báo lỗi |

- Tệp fixture trong repo nhìn thấy được (chỉ đọc) trong sandbox; tệp test tạo ra đặt trong `tmp_path` để script ghi được.
- Ngoại lệ phải có lý do ghi trong `README.md` của bài, ví dụ module 01 Basic 03 (graceful-stop) phải gửi signal tới
  PID thật nên không dùng được `--unshare-pid` của bwrap; bài đó vẫn chạy script với `start_new_session=True` và env
  dựng từ đầu.

### Gating

- `ex.require_tool(name, min_version)`: thiếu công cụ, phiên bản cũ hơn mức tối thiểu, hay (với `docker`) daemon tắt
  hoặc user không có quyền socket thì skip.
- `ex.require_image(image)`, `ex.require_service(name)`, `ex.require_cluster(name="devops-lab")`: skip khi chưa có
  image, service compose hay cluster kind.
- Thông báo skip chỉ chỗ sửa: `setup/DEVOPS-TOOLS.md`, lệnh `docker pull` hay `docker compose ... up -d`. Skip không
  tính là đạt; `SOLUTION=1` phải pass không skip khi đã cài đủ công cụ.

### Ghim CPU

- Một biến duy nhất `DEVOPS_CPUSET`: dải core (`2-7`, `12-35`) hoặc rỗng/chưa đặt nghĩa là không ghim. Không bao giờ
  dùng giá trị chữ như `none`: compose truyền nguyên giá trị cho Docker và Docker từ chối tạo container.
- Compose (`cpuset: "${DEVOPS_CPUSET:-}"`) đọc biến từ shell hoặc `.env` cạnh tệp compose. `testkit.docker_cpu_args()`
  đọc từ môi trường của pytest (cộng `setup/.env`); rỗng thì chỉ tự ghim `12-35` khi máy có từ 36 core.
- Lệnh nặng trong hướng dẫn chạy với `nice -n 15 taskset -c "$DEVOPS_CPUSET"`; không ghim thì chỉ `nice -n 15`.

### Phần `## 0. Cài đặt` của module

- Có khi module dùng công cụ lần đầu; luôn là phần `## ` đầu tiên và không tính vào 5–8 phần.
- Bảng phiên bản đã kiểm và mức tối thiểu cho bài tập; lệnh tải qua HTTPS; kiểm checksum **trước** khi giải nén hay
  cài; cài vào `~/.local/bin` (không `sudo` nếu được); lệnh xác nhận kèm output thật; cách gỡ.
- Khối cài nối các bước bằng `&&` để checksum sai thì dừng, không cài. Không bao giờ `curl ... | sudo bash`.

### Bài sự cố cố ý

- `README.md` chỉ tả triệu chứng; nguyên nhân chỉ nằm trong `solutions/`.
- Test chứng minh hành vi đúng sau khi sửa, và có một ca hồi quy chứng minh starter tái hiện đúng triệu chứng.

### Capstone

- Test trong `capstone/project/tests` chấm `capstone/project/`; `SOLUTION=1` chấm `capstone/solutions/project/`.
- `-k mNN` chọn một milestone; tên test bắt đầu bằng `test_mNN_`.
- Tên tệp milestone cố định theo trường `doc` trong `track.json`.

### Dự kiến cho Phase 2

Các helper sau **chưa có**; phải thêm vào `testkit.py` (kèm test) trước khi bài nào dùng:

- `KubeLab`: namespace riêng trên cluster `devops-lab`, dọn khi xong.
- `act_run`: chạy workflow GitHub Actions bằng `act` với container của `DockerLab`.
- `DockerLab.build` và `DockerLab.compose`: build image và dựng compose với cùng bảo đảm như `start`.
- `kind_node_exec`: chạy lệnh trong node kind.
- Helper git cho testkit: repo tạm có commit, branch, remote giả.

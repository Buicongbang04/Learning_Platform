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

## Track MLOps

Quy ước riêng của `tracks/mlops/`, bổ sung cho phần chung ở trên. Validator `tests/test_mlops_track.py` kiểm phần
lớn các quy tắc này. Track đứng độc lập, không lấy track DevOps làm điều kiện. Chi tiết API xem docstring và mã
trong `mlopskit.py`.

### Helper `mlopskit`

`mlopskit.py` ở gốc repo, dựng trên `testkit` (không sửa `testkit.py`), có test riêng ở `tests/test_mlopskit.py`.
Test của bài tập và capstone gọi Docker **chỉ** qua helper này hoặc `testkit.DockerLab`; gọi `docker` trần
(`subprocess.run(["docker", ...])`, `_docker(`) trong `tracks/mlops/**/tests/*.py` bị validator báo lỗi.

| Test cần | Dùng | Đảm bảo |
| --- | --- | --- |
| Biết cổng của dịch vụ trong stack | `mlopskit.stack_port("mlflow")` (`postgres`, `minio`, `mlflow`) | Đọc biến `MLOPS_*_PORT` từ môi trường hoặc `setup/.env`, mặc định dải 2xxxx |
| Cần MLflow server, MinIO hoặc Postgres của stack | `mlopskit.require_stack("mlflow", "minio")` | Skip với đúng lệnh `docker compose -f setup/mlops/compose.yaml up -d --wait` khi cổng chưa mở |
| Cần MLflow nhưng không cần server | `mlopskit.mlflow_local(tmp_path)` | Tracking URI SQLite trong `tmp_path`, experiment riêng; **không** đòi stack |
| Build image từ Dockerfile của người học | `with mlopskit.built_image(context) as tag:` | Tên `mlops-ex-<uuid8>:test`, nhãn `mlops-ex=1`, timeout, xoá image trong `finally` kể cả khi lỗi |
| Dựng stack Compose tạm của người học | `with mlopskit.compose_project(file, env) as project:` | Project tên `mlops-ex-<uuid8>`, `up --wait`, `project.port/logs/exec`, `down -v --rmi local` trong `finally` |
| Kiểm tra không còn rác | `mlopskit.leftovers(needle)` | Liệt kê container, network, image có nhãn `mlops-ex=1` hoặc tiền tố `mlops-ex-`; `needle` (tuỳ chọn) lọc theo chuỗi con trong tên |
| Xem image đã build | `mlopskit.image_inspect(tag, fmt)`, `image_size_bytes(tag)`, `image_has_healthcheck(tag)` | `docker image inspect --format` theo Go template; kích thước theo byte; có `Healthcheck` hay không |
| Timeout build | `mlopskit.build_timeout()` | Giây, đọc `MLOPS_BUILD_TIMEOUT` lúc gọi; mặc định 1800 |

- Script của người học chạy qua `testkit.run_sandboxed`, như track DevOps.
  Ngoại lệ: test cloud thật tuỳ chọn (`ETA_CLOUD_LIVE=1`, capstone M11) chạy `teardown.sh --dry-run` của người học ngoài `run_sandboxed`, vì cần mạng và thông tin đăng nhập cloud; chỉ `--dry-run`, mặc định skip.
- Helper riêng của một module hay capstone nằm cạnh bài, tên `<topic>kit.py` (`cikit.py` ở module 08, `segkit.py` ở module 11, `k8skit.py` ở module 13, `k8sprodkit.py` ở module 14, `distkit.py` ở module 15, `tlcstream.py` ở module 16, `seckit.py` ở module 17, `etakit.py` ở `capstone/project/tests/`), được import qua `sys.path.insert` trong `conftest.py` của module/capstone. Chỉ dùng cho thứ riêng một module/capstone; thứ dùng chung nhiều module thuộc `mlopskit.py`. Helper này **không** gọi `docker`, `kubectl`, `kind` trần: mọi lệnh đi qua `mlopskit`.
  Helper Giai đoạn 4:

  | Helper | Việc riêng |
  | --- | --- |
  | `k8sprodkit.py` (module 14) | Image lab `ml-lab:dev`; `applied()` apply một manifest có cả tài nguyên cluster-scoped (allowlist ResourceFlavor, ClusterQueue, Cohort, PriorityClass, WorkloadPriorityClass) lẫn namespaced (LocalQueue, Job; không được tự ghi `metadata.namespace`) cùng một run id; đọc Workload Kueue; `node_port_service` + `node_url` + `k6` chạy `mlopskit.k6_run(..., network="kind")` |
  | `distkit.py` (module 15) | `torchrun` có timeout cứng; mỗi lần chạy gắn biến `MLOPS_EX_DIST_RUN=<uuid8>`, `finally` diệt mọi tiến trình mang đúng marker đó (worker torchrun ở session riêng, giết process group không đủ; gửi tín hiệu qua `pidfd` sau khi đọc lại environ); chạy trong network namespace riêng (ghi chú dưới); `pickle_by_value` cho Ray |
  | `tlcstream.py` (module 16) | Lát chuyến TLC 2019-03 thật (qua `mlopskit.real_month`) để phát lại thành stream, xáo trộn có giới hạn theo `seed` |
  | `seckit.py` (module 17) | Cặp khoá EC sinh tại chỗ (khoá riêng tạo với quyền 0600), model safetensors mẫu, pickle độc hại đã vô hại hoá. Luật của module: payload pickle chỉ ghi tệp đánh dấu trong `tmp_path`; test không bao giờ unpickle trừ đúng một ca minh hoạ; quét model chỉ qua `mlopskit.modelscan_run` |
- Timeout build của `built_image` và `compose_project` mặc định 1800 giây, chỉnh bằng biến môi trường `MLOPS_BUILD_TIMEOUT` (giây, đọc lúc gọi). Quá hạn thì test fail kèm gợi ý build trước (cache) rồi chạy lại hoặc tăng biến này.
- Mọi tài nguyên do `mlopskit` tạo có nhãn `mlops-ex=1` và tiền tố `mlops-ex-`; lỗi hay Ctrl-C giữa chừng vẫn dọn hết.
- Helper mới được thêm vào `mlopskit.py` kèm test ở task dùng chúng, không trước (kind và GPU: Giai đoạn 3, bảng bên dưới).

Helper Giai đoạn 2 (test riêng ở `tests/test_mlopskit.py`):

| Test cần | Dùng | Đảm bảo |
| --- | --- | --- |
| Prometheus, Alertmanager, Grafana, Redis của stack | `mlopskit.require_stack("prometheus")`, `("redis")` | Skip kèm lệnh có `--profile monitoring` (Prometheus, Alertmanager, Grafana) hay `--profile feast` (Redis) |
| Chạy Feast | `mlopskit.feast_run(repo, "apply")`, `mlopskit.feast_python(repo, script)` | **Feast chỉ chạy trong container** `mlops-feast:0.67.0` (vì `feast[redis]` kéo `pandas` xuống 2.3.3, không vào môi trường mặc định); `repo` mount `/repo` rw, user không root, `--rm`, nhãn `mlops-ex=1`; `feast_python` in JSON ra stdout |
| Kiểm cấu hình, rule Prometheus | `mlopskit.promtool("check", "rules", "r.yml", cwd=dir)` | `promtool` trong `prom/prometheus:v3.5.0`, `cwd` mount chỉ đọc tại `/work` |
| Kiểm cấu hình, route Alertmanager | `mlopskit.amtool("check-config", "am.yml", cwd=dir)`, `amtool("config", "routes", "test", "--config.file=am.yml", "severity=critical", cwd=dir)` | `amtool` trong `prom/alertmanager:v0.34.1`, `cwd` mount chỉ đọc tại `/work` |
| Chạy Evidently | `mlopskit.evidently_python(dir, script)` | `python -c script` trong `mlops-evidently:0.7.23`, `dir` mount `/work` (rw), script in JSON ra stdout |
| Tải thử | `mlopskit.k6_run(script, {"TARGET": url})` | `grafana/k6:1.8.1`, mạng `host`; `.stdout` là JSON của `--summary-export` |
| Chạy workflow CI | `mlopskit.act_run(workdir)` | `act` với runner `mlops-act-runner:1` tự build, `--pull=false --bind`; `act_run` chỉ đảm bảo không kéo image, **workflow không được dùng `uses:` action từ xa** (chỉ bước `run:`, nếu không act cần mạng và GitHub); skip khi thiếu `act`; trong `finally` chỉ dọn container của chính lần chạy (nhãn `mlops-ex-run=<uuid8>`), không đụng container khác; tuỳ chọn container thêm (vd. `--user uid:gid`) truyền qua tham số `container_options=`, **không** truyền `--container-options` trong `args` (act chỉ giữ giá trị cuối, `act_run` báo lỗi) |
| Dữ liệu NYC TLC thật | `mlopskit.real_month("nyc-tlc", "2019-03")` (hoặc `"nyc-tlc-2020"`), `mlopskit.zone_lookup()` cho `taxi_zone_lookup.csv` | Skip khi chưa tải; `pytest.fail` khi sha256 lệch bảng `REAL_SHA256` (tệp nguồn bị TLC sửa hoặc tải hỏng). Không đọc thẳng `data/raw/...` |
| Chạy `dvc`/`git` trong sandbox | `mlopskit.dvc_sh(repo, cmd, args, ok=True, env=None)` | DVC/git cấu hình riêng trong `repo`, `repo` ghi được |

Profile Compose `monitoring` (prometheus 29090, alertmanager 29093, grafana 23000) và `feast` (redis 26390) bật bằng `docker compose -f setup/mlops/compose.yaml --profile monitoring --profile feast up -d --wait`.

Helper Giai đoạn 3 (test riêng ở `tests/test_mlopskit.py`). Cluster kind duy nhất `mlops` (context `kind-mlops`) dựng bằng
`bash setup/mlops/kind/up.sh` (kind v0.33.0, Kubernetes v1.35.8, cert-manager v1.20.4, KServe v0.21.0 chế độ RawDeployment,
Argo Workflows v4.1.5 + MinIO làm kho artifact; phiên bản, ngày phát hành, checksum ở `setup/mlops/kind/versions.env`,
chi tiết ở `setup/mlops/kind/README.md`). Test **không** tạo/xoá cluster và không gọi `kubectl`/`kind` trần.

| Test cần | Dùng | Đảm bảo |
| --- | --- | --- |
| Cluster kind | `mlopskit.require_kind()` | Skip khi thiếu `kind`/`kubectl`, chưa có cluster `mlops` hoặc API không phản hồi; message có `bash setup/mlops/kind/up.sh` và trỏ module 13 mục 0 |
| Gọi kubectl | `mlopskit.kubectl(*args, namespace=None, input=None, timeout=120)` | Luôn `--context kind-mlops`, không dùng context hiện hành của máy; dùng bản ghim trong `~/.local/bin` trước PATH; trả `CompletedProcess` |
| Namespace tạm | `with mlopskit.k8s_namespace() as ns:` | Tên `mlops-ex-<uuid8>`, nhãn `mlops-ex=1` và `mlops-ex-run=<uuid8>`; SA `default` được gắn ClusterRole `mlops-argo-executor` (chạy Workflow Argo); `delete --wait=false` đúng namespace này trong `finally` |
| Nạp image tự build | `mlopskit.kind_load(tag)` | `docker save --platform` + `kind load image-archive` (tránh lỗi image đa nền tảng), tar tạm ở `~/.cache/mlops-kind/load` rồi xoá; image ở lại trong node |
| Apply manifest | `mlopskit.apply_manifest(path_or_text, ns, check=True)` | `Path` là tệp/thư mục, `str` là nội dung YAML; `check` fail kèm stderr |
| Chờ trạng thái | `mlopskit.wait_for(kind, name, condition, ns, timeout, fail_on=())` | Chờ tài nguyên xuất hiện (`--for=create`) rồi đạt `condition` (tên condition như `Ready`, `Available`, hoặc biểu thức đủ `jsonpath={.status.phase}=Succeeded`), cùng một `timeout`; `fail_on=("Failed", "Error")` fail ngay khi `.status.phase` rơi vào các giá trị đó (Workflow Argo, Pod); fail kèm `describe`, pod, log, events (thu best-effort, không che lý do chính) |
| Gọi service trong cluster | `with mlopskit.port_forward(ns, "svc/x", 8080) as port:` | Cổng local tự do trên 127.0.0.1; sẵn sàng khi kubectl in `Forwarding from` (không gửi request thử vào service, nên không lệch số đếm canary); output kubectl ghi tệp tạm, không PIPE; dừng tiến trình khi ra. Service chưa có pod Ready thì request đầu có thể lỗi: test tự chờ `Ready`/`Available` trước |
| Kiểm rác | `mlopskit.leftovers(needle)` | Liệt kê thêm namespace `mlops-ex-*` còn Active hoặc kẹt Terminating quá 2 phút; phần cluster là best-effort (timeout ngắn, không cluster thì bỏ qua, không bao giờ fail) |
| GPU | `mlopskit.require_cuda()`, `mlopskit.gpu_python(script, cwd, timeout=300)` | Skip `"Không có CUDA"` khi `nvidia-smi -L` không thấy GPU; `gpu_python` chạy `uv run --no-sync --project setup/gpu python -I -c script` (test không tự sync/tải gói; `-I` không import module trong `cwd`), skip kèm `uv sync --project setup/gpu` khi env chưa có, thiếu onnxruntime-gpu hoặc còn onnxruntime CPU đè lên; script in JSON ra stdout |

Kiểm GPU bằng `session.get_providers()[0] == "CUDAExecutionProvider"` sau `onnxruntime.preload_dlls()`, không bằng
`get_available_providers()` (liệt kê cả khi thư viện CUDA không nạp được, ORT âm thầm chạy CPU).

Helper Giai đoạn 4 (test riêng ở `tests/test_mlopskit.py`). Add-on senior của cluster (metrics-server v0.9.0, KEDA
v2.21.0, Kueue v0.20.2) cài bằng `bash setup/mlops/kind/up.sh --senior`; Kafka bằng profile Compose `streaming`. Chi tiết
và số đo ở `setup/mlops/kind/README.md`, `setup/mlops/README.md`.

| Test cần | Dùng | Đảm bảo |
| --- | --- | --- |
| KEDA, Kueue, metrics-server | `mlopskit.require_senior_addons()` | Như `require_kind`, thêm skip khi thiếu CRD `scaledobjects.keda.sh` hoặc `clusterqueues.kueue.x-k8s.io`; message có `bash setup/mlops/kind/up.sh --senior`. Rồi chờ webhook Kueue nhận `create --dry-run=server` (≤120 giây; webhook Job của Kueue là `failurePolicy: Fail`, sau khi node khởi động lại tạo Job bị từ chối tới khi controller lên), quá hạn thì fail |
| Tài nguyên cluster-scoped (ClusterQueue, ResourceFlavor, Cohort, PriorityClass, WorkloadPriorityClass, ClusterTriggerAuthentication...) | `with mlopskit.cluster_scoped(manifest) as names:` | Mọi `__RUN__` trong manifest thay bằng run id `<uuid8>`; tên mỗi tài nguyên phải chứa run id (không thì fail); ép nhãn `mlops-ex=1`, `mlops-ex-run=<uuid8>`; trả `["clusterqueue/cq-<uuid8>", ...]`; xoá đúng các đối tượng này trong `finally`, kể cả khi apply lỗi giữa chừng. Kind mà cluster chưa phục vụ (add-on chưa cài) thì skip kèm `up.sh --senior`. Tài nguyên namespaced bị từ chối (dùng `apply_manifest` trong `k8s_namespace`; LocalQueue tham chiếu ClusterQueue bằng tên trả về) |
| GPU giả để thực hành lập lịch | `with mlopskit.fake_extended_resource("gpu", 2) as res:` | Patch `status.capacity` của node: `mlops.example/gpu-<uuid8>` = 2, chờ `allocatable` thấy rồi mới trả tên resource; gỡ khỏi `capacity` và `allocatable` trong `finally`. Không test nào sửa node theo cách khác |
| Kafka | `mlopskit.require_kafka()` → `"127.0.0.1:<cổng>"`; `with mlopskit.kafka_topic(partitions=1) as topic:` | Skip kèm lệnh có `--profile streaming`; topic `mlops-ex-<uuid8>` tạo bằng admin client (broker tắt tự tạo topic), xoá trong `finally`. Client là `kafka-python-ng` của môi trường mặc định |
| Ray cục bộ | `with mlopskit.ray_local(num_cpus=2) as storage:` | `ray.init` không dashboard, **chỉ loopback** (`_node_ip_address=127.0.0.1` + `RAY_ENABLE_WINDOWS_OR_OSX_CLUSTER=0`; mặc định trên Linux GCS, raylet, object manager nghe mọi địa chỉ với IP LAN; node không ở 127.0.0.1 thì fail), thư mục tạm `/tmp/mlops-ex-ray-<uuid8>`; tắt tích hợp `uv run` của Ray (`RAY_ENABLE_UV_RUN_RUNTIME_ENV=0`, nếu không trial Tune treo `PENDING` khi chạy qua `uv run pytest`); hai biến nằm trong hằng `mlopskit.RAY_ENV` (đặt khi vào, khôi phục khi ra), subprocess dùng Ray truyền `env={**os.environ, **mlopskit.RAY_ENV}`; `storage` dùng cho `tune.RunConfig(storage_path=str(storage))` (không ghi `~/ray_results`); `finally`: `ray.shutdown()`, diệt mọi tiến trình còn mang đường dẫn tạm (worker mồ côi), xoá thư mục. Không lồng hai `ray_local` |
| Quét model | `mlopskit.modelscan_run(path)` | `modelscan` 0.8.8 trong image `mlops-modelscan:0.8.8` (build tại chỗ từ `setup/mlops/modelscan/Dockerfile`: base ghim digest, `pip install --require-hashes` từ `requirements.txt` sinh bằng `uv pip compile --generate-hashes --exclude-newer 2026-10-21`; sửa `requirements.txt` cũng build lại), `--network none`, chỉ đúng `path` (tệp hoặc thư mục) mount chỉ đọc tại `/scan/<tên>`, không mount thư mục cha; `--pull never` (thiếu image thì fail kèm lệnh build), `--cap-drop ALL`, `no-new-privileges`, rootfs read-only; thư mục báo cáo 0700, `report.json` là symlink thì fail; `.returncode` là mã thoát modelscan (0 sạch, 1 có vấn đề, 2 lỗi, 3 không có gì để quét, 4 không hỗ trợ), `.stdout` là báo cáo JSON |
| Kiểm rác | `mlopskit.leftovers(needle)` | Liệt kê thêm: đối tượng cluster-scoped có nhãn `mlops-ex-run` (PriorityClass, ClusterRole/Binding, các kind Kueue/KEDA; đang xoá vì finalizer, vd. ClusterQueue chờ workload, thì chỉ tính khi kẹt quá 2 phút), extended resource `mlops.example/*` trên node (`node/<tên>:<resource>`), topic `kafka-topic/mlops-ex-*`, thư mục `/tmp/mlops-ex-ray-*`; best-effort, không bao giờ fail |

Ruling Triton (đo 2026-11-04): image nhỏ nhất chạy được là `nvcr.io/nvidia/tritonserver:26.09-py3` (tạo 2026-09-24),
**9,04 GB nén** cho amd64 (46 layer); `26.09-pyt-python-py3` 7,49 GB nén; `26.09-py3-min` (6,47 GB) chỉ là base để build,
không có server. NGC không có image CPU-only. Giải nén trên đĩa gấp ~2 lần, `kind load` cần thêm bản tar và bản trong
containerd của node: vượt xa ngưỡng 6 GB đĩa / 5 phút. Vì vậy bài Triton của module 14 có test gate `MLOPS_TRITON=1`
(mặc định skip, message nêu lý do và kích thước), không kéo sẵn image; bài load test bắt buộc chạy trên KServe custom
predictor. Test Triton **chưa chạy thật lần nào** (viết theo tài liệu NGC; uid 1000 của image chưa kiểm); README module,
README bài và thông điệp gate đều ghi điều này. Bật `MLOPS_TRITON=1` lần đầu có thể cần sửa.

Ghi chú kỹ thuật Giai đoạn 4 (đo 2026-11-04):

- **Kueue chỉ quản lý `batch/v1` Job.** `up.sh --senior` bỏ 8 webhook Pod/Deployment/StatefulSet/LeaderWorkerSet của
  manifest gốc (`failurePolicy: Fail` ở mọi namespace: Kueue chưa lên thì KServe, Argo, module 13 không tạo được pod) và
  để `integrations.frameworks` chỉ `batch/job`. Bài Kueue dùng Job có nhãn `kueue.x-k8s.io/queue-name`. Webhook Job vẫn
  `failurePolicy: Fail`: sau khi node khởi động lại, tạo Job bị từ chối (`failed calling webhook "mjob.kb.io"`) tới khi
  controller lên; `require_senior_addons()` chờ việc này.
- **Load test nhiều replica không qua `port_forward`** (port-forward dính một pod): dùng Service `NodePort` cổng tự cấp
  và `k6` trong mạng Docker `kind`, chờ ~5 giây sau khi endpoint Ready cho kube-proxy. Chấm thông lượng ≥ 1,5×, trung vị
  latency ≤ 0,7×, p95 ≤ 0,9× so với 1 replica; lần 3 replica trông lệch (keep-alive dồn vào một pod) thì đo lại một lần,
  giữ lần thông lượng cao hơn. Không ép `noConnectionReuse` (bỏ keep-alive làm p95 tăng, lời giải đúng fail oan):
  quy tắc này cho bài module 14, nơi người học tự viết script tải. **Ngoại lệ capstone M14:** test tự viết script
  k6, đo sức một pod C và chạy tải chấm với **cùng** chính sách `noConnectionReuse` (`K6_NO_CONNECTION_REUSE=true`,
  mỗi request một kết nối) để kube-proxy chia đều tải giữa các replica; ngưỡng p95 suy từ C đo cùng điều kiện nên
  chi phí bỏ keep-alive đã nằm trong C.
- Manifest người học ở module 14: tài nguyên cluster-scoped viết `__RUN__`, GPU giả `__GPU__`, namespace trong URL
  `__NAMESPACE__`; test thay. Job/Pod mẫu dùng `busybox:1.37` `IfNotPresent`, non-root, seccomp `RuntimeDefault`,
  drop ALL, rootfs chỉ đọc.
- **torchrun:** `--rdzv-backend=c10d --rdzv-endpoint=127.0.0.1:0 --local-addr=127.0.0.1`, không `--standalone` (treo khi
  hostname phân giải ra IP LAN không định tuyến). gloo nghe 127.0.0.1 (`GLOO_SOCKET_IFNAME=lo`), nhưng TCPStore của
  chính torchrun (rendezvous c10d và store của agent) **nghe mọi interface**, không xác thực, torch 2.14.1 không có cờ ép
  về loopback (kiểm bằng `ss -tlnp`). Vì vậy `distkit` chạy torchrun trong network namespace riêng không cần root
  (`unshare --user --map-root-user --net`, bật `lo`); máy chặn user namespace (AppArmor Ubuntu 24.04) thì chạy không cô
  lập và `distkit.isolated()` trả False. Test `tests/test_distkit.py` của module kiểm không còn socket LISTEN nào của
  job trên máy.
- **FSDP2** (`fully_shard`, torch 2.14.1 CPU) chạy được trên gloo.
- **Feast SQLite online store không so `event_timestamp`**: ghi đè theo thứ tự ghi (Redis store có so, trừ `skip_dedup`).
  Bài push của module 16 dùng SQLite trong repo tạm, `feast_*` với `network="none"` (không trạng thái dùng chung giữa
  các lần chạy song song), và biến điều này thành yêu cầu "không đè bằng giá trị cũ". Freshness đo từ event time tới lúc
  đọc được online. Kafka dùng `kafka_topic()` một partition để thứ tự đọc xác định.
- **modelscan 0.8.8** chọn scanner theo đuôi tệp, không theo nội dung: pickle đổi tên `.safetensors` → mã 3, `.bin`/`.pt`
  bị bỏ qua; safetensors/JSON → mã 3 (bình thường, "không có gì để quét"); payload `pathlib` không bị báo; joblib chứa
  mảng numpy cho lỗi parse. Cổng deploy phải dùng allowlist theo nội dung và fail closed; quét sạch không chứng minh an
  toàn. Assertion phụ thuộc hành vi modelscan ghi rõ "hành vi đo trên modelscan 0.8.8".
- **`cyclonedx-py requirements`** chạy offline; khi lỗi thoát 1 và để lại tệp output **0 byte** (kiểm nội dung, không
  chỉ kiểm tệp tồn tại).
- Copier trong `run_sandboxed`: `sys.executable -m copier copy --defaults --quiet --data k=v`, không `--trust`; validator
  dùng `regex_search` (Jinja không có test `match`).
- Bài sự cố có thể dùng fixture golden (`expected.json`) sinh bằng script trong `solutions/` khi để tham chiếu trong test
  sẽ lộ cách sửa.

### Stack và cổng

Định nghĩa ở `setup/mlops/compose.yaml`, bật bằng `docker compose -f setup/mlops/compose.yaml up -d --wait`. Đã đổi cổng trong `setup/.env` thì thêm `--env-file setup/.env` trước `-f` (Compose chỉ tự đọc `.env` cạnh tệp compose). Cổng ở dải 2xxxx vì
máy đã dùng 5432, 9000, 8000; mọi cổng remap được qua `setup/.env`.

| Dịch vụ | Cổng host mặc định | Biến `.env` | Ghi chú |
| --- | --- | --- | --- |
| postgres | 25433 | `MLOPS_PG_PORT` | Backend store của MLflow |
| minio | 29000 (S3 API), 29001 (console) | `MLOPS_MINIO_PORT` | Artifact store, remote của DVC |
| mlflow | 25000 | `MLOPS_MLFLOW_PORT` | Tracking server và registry |
| kafka (profile `streaming`) | 29092 | `MLOPS_KAFKA_PORT` | `apache/kafka:4.3.1` KRaft 1 node; container khác trong mạng `mlops_default` dùng `kafka:9092` |

**Client tải model từ host:** MLflow 3.17 server luôn quảng bá multipart download qua presigned URL trỏ `minio:9000` (không phân giải được từ host; không có cờ server tắt). Mọi client chạy trên host đọc model/artifact từ stack (`mlflow.pyfunc.load_model("models:/...")`, `download_artifacts`) phải đặt `MLFLOW_ENABLE_PROXY_MULTIPART_DOWNLOAD=false` (ví dụ `monkeypatch.setenv` trong fixture) để tải qua proxy `--serve-artifacts`; nếu không sẽ treo.

Test cần stack mà chưa bật phải `skip` kèm lệnh bật (`require_stack`); test dùng được MLflow file store thì không
được đòi stack. Skip không tính là đạt; `SOLUTION=1` phải pass không skip khi stack và công cụ đã có.

### Model nhẹ, mỗi bài ≤5 phút

- Mỗi bài chạy trên laptop ≤5 phút CPU, không kể lần đầu tải dữ liệu. Dữ liệu thật dùng **mẫu xác định theo
  `seed`** (ví dụ 200 000 dòng của một tháng), không đọc cả 84 triệu chuyến; chỉ đọc các cột cần.
- Dataset: `nyc-tlc` (2019), `nyc-tlc-2020` (2020, có cú sốc COVID), `oxford-pets` và `oxford-pets-trimaps` (module 11).
  Không commit mẫu trích từ dữ liệu; fixture test sinh trong test.
- Bài distributed, GPU, K8s dùng model nhỏ (nhiều tiến trình CPU, kind nhiều node). Bài chỉ "chờ model chạy" mà
  không dạy việc vận hành thì cắt bớt.

### Môi trường Python

- Dependency mà test cần (mlflow, dvc, pandera, prefect…) nằm trong **môi trường mặc định** của
  `pyproject.toml` để nút "Run tests" (`uv run pytest`) chạy được; ghim phiên bản phát hành ≥2 tuần trước ngày thêm.
- Xung đột với pin hiện có (`numpy`, `pyarrow`, `grpcio`, `pandas`): (1) chọn phiên bản tương thích; (2) nếu không
  được, chạy công cụ đó **trong container** của stack `setup/mlops` và test gọi qua CLI/HTTP; (3) không bao giờ hạ
  pin làm hỏng track khác. Kết quả kiểm mỗi công cụ ghi ở đây khi thêm: `dvc[s3]` resolve cùng pin
  hiện tại; `feast[redis]` kéo pandas xuống 2.3.3 nên module 06 phải chạy Feast trong container hoặc tìm bản tương thích. `evidently==0.7.23` (bản mới nhất, kiểm 2026-11-03) **không import được với pandas 3.1** (`infer_dtype_from_object` đã bị bỏ) và đòi `plotly<6`, nên Evidently chạy trong image `mlops-evidently:0.7.23` (pandas 2.3.3) qua `mlopskit.evidently_python`, giống Feast trong `mlops-feast`. Không shim/monkeypatch pandas trong bài.
- Giai đoạn 4 (kiểm 2026-11-04 bằng `uv add` dưới pin hiện tại, rồi import và chạy thử thật): `ray[train,tune]==2.59.0`,
  `river==0.26.1`, `copier==9.19.1`, `model-signing==1.1.1`, `cyclonedx-bom==7.5.0` resolve cùng pin hiện có, **không hạ
  bản gói nào**, nên nằm trong group `mlops-senior` của `pyproject.toml`, group này có trong `[tool.uv] default-groups`
  (`uv sync`/`uv run` mặc định cài). Mọi gói mới kể cả gián tiếp (sigstore 4.5.1, securesystemslib 1.6.0, tuf 7.0.1,
  chardet 7.7.0...) phát hành ≤ 2026-10-21. `model-signing` 1.1.1 import `OpenSSL` nhưng không khai báo (sigstore 4.x
  đã bỏ pyOpenSSL), nên group ghim thêm `pyopenssl==26.4.0`. Ký/verify bằng khoá EC sinh trong test chạy offline
  (`use_elliptic_key_signer`/`use_elliptic_key_verifier`), không cần Sigstore. SBOM dùng `cyclonedx-py environment`
  (CycloneDX 1.6). `modelscan==0.8.8` đòi `rich<15` và `tomlkit<0.14` (env đang có rich 15.0.0, tomlkit 0.15.2) nên
  **không** vào môi trường mặc định: chạy trong image `mlops-modelscan:0.8.8` qua `mlopskit.modelscan_run`. Client Kafka
  dùng `kafka-python-ng` 2.2.3 đã có (DE module 07); đã kiểm với broker 4.3.1 (tạo/xoá topic, produce, consume theo
  group), không thêm `confluent-kafka`. Ray chạy qua `uv run` cần `RAY_ENABLE_UV_RUN_RUNTIME_ENV=0` (test dùng
  `mlopskit.ray_local`; script của người học chạy trực tiếp bằng `uv run` cũng phải đặt biến này, ghi trong README module). Mọi
  chỗ chạy Ray (test, subprocess, script người học) dùng đủ `mlopskit.RAY_ENV`, trong đó `RAY_ENABLE_WINDOWS_OR_OSX_CLUSTER=0`
  ép Ray chỉ nghe 127.0.0.1 (gRPC của GCS/raylet không nên lộ ra mạng LAN khi học).
- Ngày phát hành của bản ghim chạy trong container, và của dependency thêm ở Giai đoạn 4 (kiểm 2026-11-03, Giai đoạn 4
  kiểm 2026-11-04, qua PyPI JSON `upload_time`, GitHub Releases `published_at`, Docker Hub; mọi bản ≥2 tuần trước ngày thêm):

  | Bản ghim | Phát hành | Nguồn |
  | --- | --- | --- |
  | `feast==0.67.0` (image `mlops-feast`) | 2026-10-13 | PyPI |
  | `evidently==0.7.23` (image `mlops-evidently`) | 2026-09-11 | PyPI |
  | `prom/alertmanager:v0.34.1` | 2026-09-17 | GitHub `prometheus/alertmanager` |
  | `grafana/k6:1.8.1` | 2026-08-12 | GitHub `grafana/k6` |
  | `prom/prometheus:v3.5.0` | 2025-07-14 | GitHub `prometheus/prometheus` |
  | `grafana/grafana:12.1.0` | 2025-07-23 | GitHub `grafana/grafana` |
  | `redis:7.4.5` | 2025-07-06 | GitHub `redis/redis` |
  | `modelscan==0.8.8` (image `mlops-modelscan`, cùng `rich==14.3.4`, `tomlkit==0.13.3`) | 2026-02-18 | PyPI |
  | `apache/kafka:4.3.1` (ghim digest) | 2026-06-23 | Docker Hub `apache/kafka` |
  | `ray==2.59.0` | 2026-10-02 | PyPI |
  | `river==0.26.1` | 2026-08-21 | PyPI |
  | `copier==9.19.1` | 2026-10-13 | PyPI |
  | `model-signing==1.1.1` | 2025-10-10 | PyPI |
  | `cyclonedx-bom==7.5.0` | 2026-09-29 | PyPI |
  | `pyopenssl==26.4.0` | 2026-08-01 | PyPI |
- **GPU:** môi trường chính giữ torch CPU và `onnxruntime` CPU. Đường GPU (onnxruntime-gpu, torch CUDA) nằm trong
  project `setup/gpu`; test GPU chạy qua project đó và skip khi không có CUDA. Mọi bài GPU có đường CPU; PC mạnh chỉ
  để đo thêm, test không bao giờ cần. `setup/gpu` dùng `onnxruntime-gpu==1.29.0` bản **CUDA 12** (feed `onnxruntime-cuda-12`
  của ONNX Runtime), không phải 1.31.x như CPU của env gốc: PyPI `onnxruntime-gpu` từ 1.28 build cho CUDA 13 (cần driver
  >= 580; laptop driver 550 báo `CUDA driver version is insufficient` rồi rơi về CPU), và 1.29.0 là bản CUDA 12 mới nhất
  trên feed. Bản này cần libcudart 12.8+ nên `setup/gpu` override `nvidia-cuda-runtime-cu12==12.9.79` (torch cu126 vẫn chạy).
  Chi tiết và cách kiểm ở `setup/gpu/README.md`.

### Bài sự cố cố ý

Bắt buộc từ module 07 trở đi, ≥1 bài mỗi module; module 01–04 đã có sẵn. `README.md` chỉ tả triệu chứng; nguyên nhân chỉ nằm trong `solutions/`. Test
chứng minh hành vi đúng sau khi sửa, và có một ca hồi quy chứng minh starter tái hiện đúng triệu chứng. Ví dụ:
training-serving skew do tiền xử lý lệch, model sai version sau deploy, alert không bắn do rule sai, drift giả do
pipeline đổi đơn vị, OOM GPU do batch size.

### Bài quyết định

Dùng ở module 10 và capstone (M10, M13); M18 là bài dẫn sự cố với tập hành động riêng (xem mục Capstone). Đề cho tình huống drift kèm số liệu; người học nộp tệp YAML:

```yaml
decision: keep   # retrain | rollback | keep
reasons:
  - "PSI của trip_distance 0.31 nhưng MAE trên nhãn đã về không đổi so với tháng trước"
  - "Drift do thay đổi mùa vụ, không làm hỏng dự đoán"
```

Test chỉ kiểm `decision` (giá trị hợp lệ và khớp đáp án); `reasons` chấm bằng rubric trong `SOLUTION.md`. Có bài mà
đáp án đúng là **giữ nguyên model**; không dạy "thấy drift thì retrain" như phản xạ.

Ngoại lệ ở capstone (M10 trở đi), nơi người học tự phát lại trên dữ liệu thật: **không có đáp án cố định**. Test tính lại
`summary.parquet` bằng code của người học; `evidence` trong YAML phải khớp summary đó trong sai số cho phép (M10: 1%),
`as_of` phải là lúc nhãn đã công bố, và `decision` phải qua các luật nhất quán ghi trong đề (M10: MAE không xấu đi thì
`keep`; MAE xấu đi hơn 50% thì không `keep`). Phần còn lại chấm bằng rubric trong `SOLUTION.md`.

### Phần `## 0. Cài đặt` của module

Giống quy ước track DevOps: có khi module dùng công cụ lần đầu, luôn là phần `## ` đầu tiên, không tính vào 5–8 phần;
bảng phiên bản đã kiểm, kiểm checksum trước khi cài, cài vào `~/.local/bin` hoặc qua `uv`, lệnh xác nhận, cách gỡ.
Không bao giờ `curl ... | sudo bash` (validator kiểm trong `tracks/mlops/**/*.md`).

### Capstone

- Test trong `capstone/project/tests` chấm `capstone/project/`; `SOLUTION=1` chấm `capstone/solutions/project/`.
- `-k mNN` chọn một milestone; tên test bắt đầu bằng `test_mNN_`.
- Tên tệp milestone cố định theo trường `doc` trong `track.json`; 18 milestone `m01`…`m18`, mỗi milestone có `after` là
  module mà nó mở ra sau (m12 và m13 cùng sau module 13).
- M14: tải chấm suy từ sức một pod C đo ngay trong test (bậc thang k6 trên 1 replica, `ceil(2,2 × C)` kẹp trong
  [150, 400] req/s), cả hai cùng `noConnectionReuse` (xem ghi chú kỹ thuật Giai đoạn 4). Thứ tự ưu tiên serving >
  training (`value`, `preemptionPolicy: Never` của training) kiểm trên manifest và trên pod thật; preemption thật chỉ
  thực hành ở module 14 (`basic/02-priority-preemption`). Helper K8s của test (`quantity`, `get_json`, `condition`,
  `workloads`, `node_url`, `k6_summary`, …) nằm trong `etakit.py`.
- M15: model Ray so với model train một tiến trình (`eta.train.train`, cùng tham số, cùng dữ liệu, cùng tập valid) qua
  cổng M04 (`mae` ≤ +3%, `mae_airport` ≤ +5%) và phải thắng rõ baseline trung vị theo cặp zone trên cùng dữ liệu
  (`mae` < 0,8 × baseline); không so với con số cố định của M04 vì mẫu dữ liệu khác.
- M16: freshness đo trên **trục thời gian mô phỏng** (`SimClock`), ngưỡng 2 × (cửa sổ + lateness + xử lý × speedup);
  serving đọc snapshot online do job push ghi (image serving không có Feast).
- M17: lệnh onboarding trong doc được test chạy trong bwrap, trừ lệnh cổng cuối (cần Docker) chạy ngoài với cùng env; test
  gọi hàm cổng với `mlopskit.modelscan_run` thay vào.
- M18: bài **dẫn sự cố**, không phải "Bài quyết định" retrain | rollback | keep ở trên. Tập hành động riêng
  (`rollback | restart | scale-out | wait | disable-feature | failover`); dữ liệu sự cố dựng từ ngày thật bằng
  `etakit.incident_data` (`mlopskit.real_month`, `mlopskit.zone_lookup`). Test kiểm các trường có đáp án của tệp sự cố
  (hành động, thay đổi gây ra, nguyên nhân, mốc thời gian, vai trò) và chỉ kiểm cấu trúc tối thiểu của `reasons` (≥2 câu, mỗi câu
  ≥6 từ, có số); nội dung lập luận chấm bằng rubric trong `SOLUTION.md`.

## Track FDE

Quy ước riêng của `tracks/fde/` (Forward Deployed Engineer), bổ sung cho phần chung ở trên. Validator
`tests/test_fde_track.py` kiểm phần lớn các quy tắc này. Track đứng độc lập, không lấy track DevOps hay MLOps làm điều
kiện. Chi tiết API xem docstring và mã trong `fdekit.py`; lab VM, hồ sơ khách và golden image xem `setup/fde/README.md`.

### Helper `fdekit`

`fdekit.py` ở gốc repo, dựng trên `testkit` (không sửa `testkit.py`), có test riêng ở `tests/test_fdekit.py`.
"Máy khách" là VM QEMU/KVM thật dựng từ cloud image chính thức (overlay qcow2 trên golden image của hồ sơ khách,
seed cloud-init, SSH bằng key sinh riêng mỗi lần chạy), không phải container giả lập.

| Test cần | Dùng | Đảm bảo |
| --- | --- | --- |
| Có KVM và QEMU | `fdekit.require_kvm()` | Skip khi `/dev/kvm` không đọc/ghi được hoặc thiếu `qemu-system-x86_64`/`qemu-img` |
| Golden image của một hồ sơ | `fdekit.require_golden("bank")` | Skip kèm đúng lệnh `uv run python -m fdekit prepare bank`; trả đường dẫn golden |
| Dựng golden (một lần, ngoài bài) | `fdekit.prepare(profile, force=False)` hoặc `python -m fdekit prepare <hồ sơ> [--force]` | Boot cloud image có mạng, chạy `setup/fde/cloud-init/<hồ sơ>.sh`, xoá sudo tạm và key, ghi qcow2 độc lập; pull image proxy/registry phía host mà hồ sơ cần |
| Cloud image đã ghim | `fdekit.fetch_image("rocky-8")` (khoá trong `fdekit.IMAGES`) | Tải một lần vào `data/raw/fde-images/`, kiểm sha256, tệp sai thì tải lại |
| Một VM theo hồ sơ | `with fdekit.vm("lab-open", memory_mb=..., forwards=(18080,)) as m:` | Overlay riêng (golden không bao giờ bị ghi), chờ SSH; `restrict`/`sudo` mặc định theo hồ sơ; skip khi thiếu KVM, golden, OpenSSH hay RAM trống < RAM của VM + 512 MB; luôn dọn khi ra |
| Thao tác trên VM | `m.ssh(cmd, user="fde", timeout=60, check=False)`, `m.put(local, remote)`, `m.get(remote, local)`, `m.port(18080)`, `m.ssh_command()`, `m.snapshot(path)` | `ssh` trả `CompletedProcess` (phần không tin cậy trong `cmd` phải `shlex.quote`); `port` trả cổng `127.0.0.1` phía host của cổng đã khai trong `forwards` (chưa khai thì `KeyError`); `ssh_command` trả argv để dùng với `Popen`; `snapshot` tắt sạch VM rồi ghi qcow2 độc lập |
| Trọn một "khách hàng" | `with fdekit.customer_site("hospital", memory_mb=..., forwards=(...)) as s:` | `Site` gồm `s.vm`, `s.profile`, `s.proxy_ca` (PEM CA của mitmproxy, sinh mới mỗi lần, **không** được trust sẵn trong VM), `s.registry` (`10.0.2.101:5000`, nhìn từ VM), `s.registry_host` (`127.0.0.1:<cổng>`, nhìn từ host để đẩy image). Proxy/registry chạy bằng `testkit.DockerLab`, tên `fde-ex-<run_id>-proxy`/`-registry` |
| "Sự thật" để chấm báo cáo survey | `fdekit.PROFILES["bank"].facts` | 13 khoá: `os_id`, `os_version`, `kernel_major`, `glibc`, `cpus`, `mem_mb`, `disk_free_gb_max`, `gpu`, `proxy_url`, `sudo`, `selinux`, `runtime`, `egress`; `cpus`/`mem_mb` là cấu hình `customer_site()` boot mặc định (2 CPU, 2048 MB) |
| Model GGUF đã ghim | `fdekit.fetch_model("llm-small")` (khoá trong `fdekit.MODELS`: `llm-small`, `llm-medium`, `embed-small`) | Tải một lần vào `data/raw/fde-models/`, kiểm sha256 trước khi đặt tên chính thức |
| Repo capstone của người học | `fdekit.capstone_dir()` | `SOLUTION=1` ⇒ `tracks/fde/capstone/solutions/project/`; ngược lại đọc `FDE_CAPSTONE_DIR`, chưa đặt hay không phải thư mục thì skip |
| Kiểm tra không còn rác | `fdekit.leftovers(run_id)`, `fdekit.clean(run_id)`, `fdekit.clean_capstone_tmp()`; CLI `python -m fdekit leftovers`, `python -m fdekit clean <run_id>`, `python -m fdekit clean-tmp` | `leftovers` chỉ **báo cáo**: không có run id (`leftovers()`, CLI `leftovers`) thì liệt kê mọi tiến trình QEMU, thư mục `.fde-lab/fde-ex-*`, container và network `fde-ex-*` còn sót, cùng thư mục tạm capstone `/var/tmp/fde-capstone-<pid>-*` mà pid đã chết, không xoá gì. Chỉ `clean <run_id>` xoá, và chỉ xoá của **đúng** một run id (`fde-ex-<run_id>*`); `clean-tmp` chỉ xoá `/var/tmp/fde-capstone-*` thuộc user hiện tại mà pid trong tên đã chết. Không có lệnh xoá hàng loạt |

- Mọi tài nguyên lab mang tên chứa run id riêng (`fde-ex-<uuid8>`); dọn theo run id, **không bao giờ** theo nhãn hay tiền
  tố chung (nhiều phiên chạy song song trên cùng máy). QEMU và container của một run chết theo tiến trình pytest kể cả
  khi bị `SIGKILL` (app cắt test sau 300 s): một tiến trình canh giữ pipe "lifeline" và dọn khi thấy EOF.
- Test của bài tập, capstone và sản phẩm (`tracks/fde/**/tests/*.py`) **không** gọi `docker` hay `qemu-system-*` trần:
  Docker qua `testkit.DockerLab` (hoặc helper của `fdekit`), VM qua `fdekit.vm`/`customer_site`. Validator báo lỗi
  `subprocess.run(["docker", ...])`, `_docker(` và mọi chuỗi `"qemu-system...`. Lệnh `docker` chạy **trong VM** qua
  `m.ssh("docker ...")` thì được, đó là công cụ thật của khách.
- Script người học chạy trên host qua `testkit.run_sandboxed` như track DevOps; chạy trên máy khách qua SSH của `fdekit`.
- Helper chưa có (gate PC GPU qua `FDE_PC_SSH`, k3s của khách, Keycloak, file share…) được thêm vào `fdekit.py` kèm test ở
  task dùng chúng, không trước.

### Hồ sơ khách

Mỗi hồ sơ là `setup/fde/profiles/<hồ sơ>.yaml`, nạp vào `fdekit.PROFILES`. Bài chọn hồ sơ theo "tật" cần dạy:

| Hồ sơ | OS | sudo | Egress | Runtime | Dịch vụ phía host | Tật chính |
| --- | --- | --- | --- | --- | --- | --- |
| `lab-open` | Ubuntu 22.04, 20 GB | có | `open` | Docker + `docker compose` | — | Không tật: máy đối chứng |
| `hospital` | Ubuntu 20.04, 8 GB | có | `proxy` (TLS inspection) | Docker, không plugin compose | mitmproxy | Proxy chỉ đặt trong `/etc/environment`, CA chưa trust, đĩa nhỏ |
| `bank` | Rocky Linux 8.10, 20 GB | **không** | `none` | Podman rootless | — | Air-gapped hoàn toàn, SELinux enforcing |
| `lawfirm-staging` | Ubuntu 22.04, 30 GB | có | `none` | Docker, không plugin compose | registry nội bộ HTTP | Air-gapped, registry chưa khai `insecure-registries` |

Egress `none`/`proxy` ⇒ VM không route ra internet, không DNS, không tới loopback host qua `10.0.2.2`; chỉ còn SSH, các
cổng `forwards` và `guestfwd` tới proxy (`10.0.2.100:3128`) hoặc registry (`10.0.2.101:5000`). Golden không mang theo
mạng hay sudo lúc dựng: lúc chạy bài, `vm(profile)`/`customer_site()` áp lại theo hồ sơ.

Thêm hồ sơ mới: thêm YAML + `setup/fde/cloud-init/<hồ sơ>.sh`, đo `facts` trên golden, cập nhật bảng trong
`setup/fde/README.md` và ở đây; `test_facts_match_vm` trong `tests/test_fdekit.py` phải pass.

### Ngân sách VM và thời gian

- Tối đa **2 VM cùng lúc** mỗi bài (capstone tối đa 3). VM phụ (proxy, registry, Keycloak, file share) ≤2048 MB; VM chạy
  quillo ≤5120 MB; tổng RAM VM trong một bài ≤8192 MB.
- Mỗi bài ≤**300 s** kể cả boot VM (nút "Run tests" của app cắt pytest sau 300 s; không sửa timeout này). Golden image
  chuẩn bị trước bằng `fdekit prepare` và việc tải image/model/dữ liệu lần đầu không tính. Ngưỡng thời gian trong test
  chừa gấp đôi số đo. Bài vẫn vượt 300 s thì README bài ghi rõ chạy bằng terminal; frontmatter `run` vẫn phải đúng lệnh.
- Việc nặng (dựng golden, build bundle, `SOLUTION=1` cả module) chạy với `nice -n 15`.

### Chỗ hỏng thật từ hồ sơ khách

- Mọi bài cài đặt/triển khai trên VM có **ít nhất một chỗ hỏng do hồ sơ khách gây ra** (proxy, CA nội bộ, egress bị
  chặn, đĩa nhỏ, không sudo, SELinux, thiếu plugin compose…), **không** phải lỗi cố tình cài vào code hay starter.
  Bài chạy suôn sẻ trên `lab-open` thì phải có ca trên hồ sơ "khó" làm nó hỏng.
- `README.md` của bài chỉ tả bối cảnh và triệu chứng (như khách báo lại: "cài dừng giữa chừng", output lỗi khách gửi);
  nguyên nhân chỉ nằm trong `solutions/`. Tên hàm, tệp, biến trong starter không được lộ nguyên nhân.
- Test kiểm **kết quả cuối trên VM** bằng công cụ thật (dịch vụ trả lời qua cổng forward, installer chạy lại idempotent,
  báo cáo survey khớp `Profile.facts`), không mô phỏng bằng Python và không chỉ grep chuỗi. Mọi quy tắc test chấm phải
  được nói trong README bài hoặc milestone.

### Module và trường `section`

- 21 module chính `00-introduction` … `20-fde-interview` và 3 module Cloud lab `c1-aws-byoc`, `c2-gcp-azure`,
  `c3-cloud-gpu-inference`. Module Cloud lab khai `"section": "cloud-lab"` trong `track.json`; app gom chúng vào nhóm
  "Cloud lab (có phí)", đánh số `C1`…`C3`, không tính vào tiến độ chính và không vào "học tiếp". Id bắt đầu bằng `c` khi
  và chỉ khi module là Cloud lab; module chính bỏ trống `section`.
- Bài Cloud lab ghi chi phí ước tính, dựng budget alarm trước tiên, có bước `destroy` bắt buộc kèm script kiểm không còn
  tài nguyên tính phí; test tự skip khi không có credential. Không bài nào của track chính phụ thuộc Cloud lab.
- Mỗi module 4–9 bài (≥3 Basic, trừ module 00; ≥2 Advanced); module DSA `15-dsa-core`, `16-dsa-advanced` được tới 30 bài.
  Basic và Intermediate có `SOLUTION.md` cộng lời giải trùng tên mọi tệp `starter/`; Advanced có `SOLUTION.md` (hướng làm
  + rubric).
- Không lặp track cũ: Docker, Linux, K8s, Terraform, RAG cơ bản tối đa **một** `## ` ôn nhanh mỗi module, có link về
  module gốc (DevOps 01/06/08/10, AE 13/20, MLOps 02). `interview.md` ≥12 câu, có câu tình huống hiện trường ("khách nói
  X, bạn làm gì").

### Sản phẩm `quillo`

"Sản phẩm công ty" ở `tracks/fde/product/` (MIT, hư cấu): FastAPI + htmx, worker nạp tài liệu, Postgres + pgvector, LLM
và embedding qua **llama.cpp server** với model GGUF ghim trong `fdekit.MODELS`. Hai bản `1.0.0` và `1.1.0` (migration
`0002_v1_1_tags.sql`) dựng từ cùng cây mã. `release.py build --version X.Y.Z` tạo bundle offline `quillo-X.Y.Z.tar`
(image `docker save`, model, compose, `REQUIREMENTS.yaml`, `manifest.json` sha256); `release.py verify` từ chối tar cắt
cụt, tệp sai sha, thiếu, thừa hay đường dẫn lạ. `REQUIREMENTS.yaml` là chuẩn cho bài survey/preflight. API publish cổng
`QUILLO_PORT` (mặc định 18080) trên `QUILLO_BIND` (mặc định `127.0.0.1`); hai biến này đặt trong `.env` cạnh
`compose.yaml` của bản cài quillo (installer ghi), không phải `setup/.env` của repo học. Sản phẩm là công cụ của bài, không phải chủ
đề dạy; test riêng ở `tracks/fde/product/tests/`.

### Bài tài liệu (dùng từ Phase 3)

Module trụ 2 (11–14), System Design (17–18) và các milestone tài liệu: người học nộp tệp Markdown có **frontmatter YAML
bắt buộc** (vd. scope must/should/won't, ước lượng có `min`/`max`, rủi ro, tiêu chí nghiệm thu, con số ROI).

- Phần có cấu trúc chấm **xác định** bằng test: đủ trường, kiểu đúng, số liệu nhất quán (ROI tính lại đúng từ input).
- Phần lập luận chấm bằng **LLM-judge local qua `llmkit`** theo rubric công khai trong README bài; test judge tự skip khi
  không có model local và có ngưỡng chừa biên. Rubric đầy đủ và bài mẫu nằm trong `solutions/`.
- Stakeholder simulator: persona và yêu cầu ẩn chỉ nằm trong `solutions/`; tài liệu yêu cầu chấm theo số yêu cầu ẩn
  hỏi ra được.

### Phần `## 0. Cài đặt` của module

Giống quy ước track DevOps/MLOps: có khi module dùng công cụ lần đầu (module 00: QEMU/KVM, quyền `/dev/kvm`, golden
image), luôn là phần `## ` đầu tiên, không tính vào 5–8 phần; bảng phiên bản đã kiểm, checksum trước khi cài, lệnh xác
nhận, cách gỡ. Không bao giờ `... | sudo bash` hay `... | sudo sh` (validator kiểm trong `tracks/fde/**/*.md`).

### Capstone

- Capstone "Trợ lý hợp đồng cho công ty luật" (dữ liệu CUAD, CC BY 4.0, ghi công trong `capstone/README.md`; không commit
  dữ liệu) làm trong **repo Git riêng của người học**, ngoài repo học. Repo học chỉ chứa đề (`capstone/README.md`,
  `capstone/milestones/`), bộ chấm (`capstone/tests/`) và lời giải tham chiếu (`capstone/solutions/project/`, không phải
  repo git lồng).
- Bộ chấm lấy repo qua `fdekit.capstone_dir()`: `FDE_CAPSTONE_DIR` trong `setup/.env` hoặc môi trường, chưa đặt thì skip;
  `SOLUTION=1` chấm lời giải tham chiếu. Repo riêng phải tự chứa: không import `testkit`/`fdekit`, không trỏ đường dẫn
  vào repo học, không commit secret/khoá lab/`.env`/dữ liệu (test M00 kiểm).
- `uv run pytest tracks/fde/capstone -k mNN` chọn một milestone; tên test bắt đầu bằng `test_mNN_`.
- 17 milestone `m00`…`m16`; tên tệp cố định theo trường `doc` trong `track.json`. Milestone chỉ gắn (`after`) vào module
  chính, **không** gắn vào module Cloud lab. `m00`…`m14` sau module cùng số, `m15` sau `18-system-design-fde`, `m16` sau
  `20-fde-interview`.
- Capstone dùng tối đa 3 VM cùng lúc, cùng ngân sách RAM và 300 s mỗi test như bài tập.
- Bộ chấm ở `capstone/tests/` (helper chung `capstonekit.py`, fixture `capstone` trong `conftest.py`). Lệnh `make` của
  repo người học chạy trên host qua `testkit.run_sandboxed` (repo chỉ đọc, chỉ thư mục tạm ghi được), tới máy khách qua
  biến `SSH=<lệnh ssh của fdekit>`; bundle lớn đặt ở `/var/tmp` (`fdekit.capstone_tmp()`, tên mang pid để `clean-tmp`
  dọn khi pytest bị SIGKILL), không ở tmpfs `/tmp`. Mỗi bước có giới hạn riêng và mỗi test có ngân sách chung 270 s
  (`capstonekit.Budget`) để installer treo làm test FAIL kèm thông báo trước mốc 300 s; đề milestone ghi các giới hạn.
- Repo tham chiếu `capstone/solutions/project/` là một repo đứng riêng, có thể có test riêng: `capstone/conftest.py` bỏ
  qua nó khi chạy `uv run pytest tracks/fde/capstone` (gọi thẳng đường dẫn thì vẫn chạy), và quy tắc "test không gọi
  `docker`/`qemu-system` trần" của validator không quét nó (test của repo người học không dùng `testkit`/`fdekit`).

### Biến `setup/.env`

| Biến | Dùng cho |
| --- | --- |
| `FDE_CAPSTONE_DIR` | Đường dẫn repo capstone của người học; chưa đặt thì test capstone skip |
| `FDE_PC_SSH` | (Phase 2) SSH tới PC có GPU cho bài GPU tuỳ chọn; chưa đặt thì bài đó skip |

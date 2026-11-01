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
| Chạy script hay chương trình của người học trên máy host | `testkit.run_sandboxed(cmd, writable=[tmp_path], cwd=tmp_path, env={...})` (thư mục cần đọc mà không được ghi, kể cả khi nằm dưới `/tmp`: `readonly=[...]`, mount `--ro-bind` sau tmpfs) (cần stdin/stdout dạng bytes hay `Popen` thì `sandbox_command`) | bwrap: `/` chỉ đọc, `/tmp` và `/run` là tmpfs rỗng (riêng tệp đích của `/etc/resolv.conf` khi nằm dưới `/run`, như stub của systemd-resolved, được bind lại chỉ đọc để DNS chạy; không bind thư mục hay socket nào khác), thông tin đăng nhập của mọi home thật bị che khi tồn tại (`~/.docker`, `~/.kube`, `~/.aws`, `~/.ssh`, `~/.config/gcloud`, `~/.azure`, `~/.config/gh`, `~/.terraform.d` phủ tmpfs; `~/.git-credentials`, `~/.netrc` thay bằng `/dev/null`; symlink được resolve và che ở đích, đích dưới `/tmp` đã bị che sẵn), chỉ các thư mục trong `writable` ghi được (`readonly` nhìn thấy nhưng không ghi được), `HOME` là `cwd`, env dựng lại từ đầu (`PATH`, `HOME`, `LANG`/`LC_ALL` cộng những gì test truyền). Mạng **không** tách. Không dùng được bwrap thì skip, **không bao giờ** chạy trần |
| Repo git tạm (dựng lịch sử, rồi chạy script người học trong repo) | `GitRepo(path, home, writable=[tmp_path])`, `git_env(home)`, `SAFE_GIT_CONFIG`; gọi `repo.taint()` ngay khi code người học đã chạy trong repo | Env dựng từ đầu (`HOME` tạm, `GIT_CONFIG_GLOBAL`/`GIT_CONFIG_SYSTEM=/dev/null`, tác giả và ngày cố định, `GIT_CEILING_DIRECTORIES`); trước `taint()` git chạy trực tiếp kèm `SAFE_GIT_CONFIG` (tắt hook, fsmonitor, ký commit), sau `taint()` mọi lệnh git của test chạy qua `run_sandboxed` vì cấu hình repo có thể đã bị sửa |
| Container do test dựng | `with DockerLab() as lab:` (fixture: dựng container bên trong `with`, rồi `yield lab`) | Nhãn `devops-ex=1`, tên `devops-ex-<uuid8>-<alias>`, `--security-opt no-new-privileges`, giới hạn RAM và số tiến trình (`run_once` cũng nhận `memory`/`pids_limit`), cpuset theo `docker_cpu_args()`, cổng chỉ trên `127.0.0.1` ở cổng trống, mount `:ro`, network riêng. Container nền không dùng `--rm` để `wait_log`/`wait_http` báo lỗi kèm 40 dòng `docker logs` cuối; `close()` luôn xoá mọi container đã tạo, lỗi hay Ctrl-C ở bất kỳ bước nào cũng dọn hết. `run_once` dùng `--rm`. `lab.stop(alias, timeout)` chạy `docker stop -t` và trả số giây đã chờ, `lab.state(alias)` trả `State` (`ExitCode`, `OOMKilled`, `Health`) để bài vòng đời tiến trình chấm bằng hành vi |
| Build image từ tệp của người học | `tag = lab.build(context, "api", build_args={...})` trả `devops-ex-<id>/<alias>:test`; `lab.image_inspect(tag)`, `lab.history(tag)` | `docker buildx build --builder <context hiện tại> --load --pull=false`; mọi image base trong dòng FROM (bỏ tên stage, `scratch`, ARG không resolve được) phải có sẵn, thiếu thì skip kèm `docker pull <image>` nên build không bao giờ tự kéo image, nhãn `devops-ex=1` và `devops-ex.lab=<id>`, bước RUN bị ghim CPU theo `docker_cpu_args()` và giới hạn RAM (mặc định `1g`). Không `--network`, `--ssh`, `--secret`, `--allow`: Dockerfile không lấy được mạng host, SSH agent hay bí mật. Env của lệnh build dựng từ đầu (không mang `BUILDX_BUILDER`, biến cloud). `close()` chạy `rmi -f` mọi tag đã build, rồi xoá image còn nhãn `devops-ex.lab=<id>`; không bao giờ xoá image base. Build cache của BuildKit dùng chung và không bị dọn (dọn tay bằng `docker builder prune`). Test giới hạn build truyền nonce vào bước RUN để bước đó luôn chạy lại, không lấy từ cache. **Đã kiểm 2026-11-01** (buildx v0.38.1, BuildKit v0.34.0, driver `docker`): RUN `cat /sys/fs/cgroup/cpuset.cpus.effective; nproc; cat memory.max` in `0-35 36 max` khi không cờ, `12-13 2 268435456` với `--cpuset-cpus 12-13 --memory 256m`; `--cpu-quota` bị bỏ qua. Vì driver `docker` tôn trọng cpuset và memory nên **không** dùng builder `docker-container` riêng; builder khác driver `docker` thì skip. Bài cần mạng lúc build (pip, apt) bắt lỗi của `build` và chỉ skip khi `testkit.build_failed_on_network(str(error))` (lỗi mạng nằm trong output của đúng bước lỗi và sau nó không còn dấu hiệu tải thành công); retry đã hồi phục rồi lỗi thật thì vẫn fail |
| Dựng project compose của người học | `project = lab.compose(file, env={...})`; `project.port(service, cổng)`, `project.exec`, `project.logs`, `project.ps()`, `project.container(service)` | Thư mục chứa tệp compose được **chép** vào thư mục tạm của lab, compose chạy từ bản chép (`-p devops-ex-<id>`) với tệp của người học cộng tệp override sinh ra. Cấu hình (output của `docker compose config`) xét theo **allowlist**: service chỉ được image, build (context/dockerfile/args/target trong thư mục), command, entrypoint, environment, env_file (trong thư mục), ports, expose, depends_on, healthcheck, volumes, working_dir, user, labels, restart, stop_signal, stop_grace_period, tmpfs, read_only, init, networks, cap_drop, profiles, hostname, deploy (chỉ `resources.limits` cpus/memory/pids và replicas), logging (json-file/local), ulimits (nofile), cộng các khoá testkit ghi đè (cpuset, mem_limit, pids_limit, memswap_limit, container_name, pull_policy); cấp trên cùng chỉ services, volumes, networks, name, `x-*`. Khoá khác (privileged, cap_add, security_opt, devices, device_cgroup_rules, gpus, runtime, network_mode, pid, ipc, uts, userns_mode, cgroup, sysctls, configs, secrets...) bị **từ chối** kèm lý do; bind mount ngoài thư mục (kèm gợi ý riêng cho docker.sock) cũng vậy. Volume/network cấp trên cùng: `name:` phải bắt đầu bằng `devops-ex-<id>`, không external, driver mặc định, không driver_opts. Override: cpuset, `mem_limit`/`pids_limit` (và `deploy.resources.limits` cùng giá trị), nhãn `devops-ex=1` cho service, volume và network, `security_opt: !override [no-new-privileges:true]`, `ports: !override` về `127.0.0.1:<cổng trống>`, mọi bind mount **chỉ đọc** (cần ghi thì dùng named volume hay tmpfs), bỏ `container_name` và `restart`. Service có `build:` được build bằng `lab.build` (không tạo tag cố định của người học); image khác phải có sẵn (`--pull never`, thiếu thì skip kèm `docker pull`). Env dựng từ đầu cộng `env`. `up -d --wait`; lỗi thì fail kèm 40 dòng log cuối. `close()` chạy `down -v --remove-orphans`. Cần compose ≥ 2.24.4 (`!reset`/`!override`), cũ hơn thì skip. Mỗi lab một project |
| Chạy workflow GitHub Actions của người học | `result = testkit.act_run(project_dir, event="push", job=None, env={...}, secrets={...}, timeout=600)`; `testkit.act_job_results(result)` trả `{job_id: True/False}`; `testkit.act_outputs(result)` trả `{job_id: {key: value}}` từ các dòng `devops-ex-output <key>=<value>` mà bước `run:` in ra (workspace của job là bản chép, tệp job ghi ra không về tới test) | act chạy trên host (cần socket Docker nên không vào bwrap) trên **bản chép tạm** của thư mục thành repo git mới (bỏ `.git`, `.actrc`). Trong bản chép, `name:` cấp trên cùng của mọi workflow đổi thành `devops-ex-<id>-<tên cũ hoặc tên tệp>`: act đặt tên container và volume là `act-<name>-<job>-<sha256>` không phụ thuộc lần chạy, nên không đổi tên thì act tái dùng rồi xoá container, volume trùng tên của người học hay của lần chạy khác. Env dựng từ đầu: `HOME` tạm (không đọc `~/.actrc`, `~/.config/act`), không mang `GITHUB_TOKEN`, `ACTIONS_*`, `AWS_*`, `DOCKER_*` (chỉ `DOCKER_HOST` lấy từ context hiện tại); `.env`, `.secrets`, `.vars`, `.input` của repo không được đọc; chỉ chạy workflow ngay trong `.github/workflows/` (`-W <bản chép>/.github/workflows/ --no-recurse`). Job chạy trong image ghim `ACT_IMAGE` (`devops-track/act-runner:1.0-<hash8>`, `<hash8>` là 8 ký tự đầu SHA-256 của `Dockerfile` nối `requirements-ci.txt` do `act_runner_tag()` tính nên đổi đầu vào là đổi tag: build một lần từ `setup/act-runner/Dockerfile` trên `node:24.22.2-trixie-slim@sha256:...`, thêm `ca-certificates`, `git`, uv 0.10.8 kiểm SHA-256, CPython 3.12.13 ở `/opt/uv/python`, cache wheel của Olist Shop ở `/opt/uv/cache`, `UV_OFFLINE=1`; image không có nhãn `devops-ex=1`, không thuộc lab nào nên không bị dọn; thiếu thì skip kèm đúng lệnh build `ACT_IMAGE_BUILD`; `--pull=false`), network riêng `devops-ex-<id>`, `docker_cpu_args()`, `--memory 1g --pids-limit 512 --security-opt no-new-privileges`, nhãn `devops-ex=1` và `devops-ex.act=<id>`, không có socket Docker (`--container-daemon-socket -`), `--container-options-policy restrict`, không cache server, tối đa 2 job song song. Kiểm trước khi chạy mọi tệp `*.yml`/`*.yaml` dưới `.github/workflows/` kể cả thư mục con (tệp trong thư mục con bị từ chối): chỉ `runs-on: ubuntu-latest`, bước `run:`, action trong `ACT_ALLOWED_ACTIONS` (hiện chỉ `actions/checkout`: act chép thẳng repo vào job, không clone từ remote **khi không đặt `ref`/`repository`**; vì vậy checkout chỉ được có input trong `ACT_CHECKOUT_INPUTS` (`persist-credentials`, `fetch-depth`, `path`...), `ref`, `repository`, `token` và input khác bị từ chối kèm lý do, và mọi `actions/checkout@<ref>` cũng được thay bằng action rỗng qua `--local-repository` để không bao giờ tải mã của action), và action `owner/repo[/đường-dẫn]@ref` khác **chỉ** ở bước có `if:` (bỏ `${{ }}` và khoảng trắng) đúng bằng `!env.ACT` hoặc là chuỗi `&&` ở cấp trên cùng có một vế đúng bằng `!env.ACT` và mọi vế có ngoặc khác đúng bằng một hàm trạng thái trong `ACT_STATUS_FUNCTIONS` (`always()`, `success()`, `failure()`, `cancelled()`, `!cancelled()`), để bước lưu báo cáo viết được `if: ${{ !cancelled() && !env.ACT }}` (có `||`, nháy kép, `!=`, `$`, `{}` hay ngoặc khác thì không công nhận; chuỗi trong nháy đơn không tính); act bỏ qua bước đó, testkit thay action bằng action composite rỗng cục bộ qua `--local-repository` nên không tải gì, đoạn `.`/`..` trong đường dẫn bị từ chối và thư mục thay thế phải nằm trong thư mục tạm; `uses: docker://...` và action cục bộ `./...` luôn bị từ chối, kể cả có `if:`; `uses:` chứa khoảng trắng hay xuống dòng bị từ chối; workflow đặt biến `ACT` (không phân biệt hoa thường) ở `env:` cấp workflow, job hay bước, hoặc dùng biểu thức cho `env:`, bị từ chối vì sẽ vô hiệu `!env.ACT`; `env`/`secrets` của `act_run` cũng không nhận tên `ACT`; `services:`, `container:`, workflow gọi workflow thì fail kèm lý do. Action khác khi thêm vào danh sách (chỉ action JavaScript) tải một lần về `${XDG_CACHE_HOME:-~/.cache}/devops-track/act` rồi dùng offline (`--action-offline-mode`); thiếu action mà mất mạng thì skip. Bước cài đặt của workflow lỗi vì mạng: test dùng `testkit.act_failed_on_network(result, step_names)`, chỉ xét output của đúng bước có tên trong `step_names` đã fail (giữa `⭐ Run` và `❌ Failure` của cùng job), có lỗi mạng và sau đó không còn dấu hiệu tải thành công thì True để skip; lỗi khác thì fail. Secret đi qua env của tiến trình act (argv chỉ có tên), act che thành `***`, testkit che thêm trong output trả về; secret ngắn hơn 4 ký tự (`ACT_SECRET_MIN_LENGTH`) bị từ chối. Quá `timeout` thì SIGKILL cả nhóm tiến trình và fail kèm output cuối. Mọi đường thoát (xong, lỗi, timeout, Ctrl-C) xoá container vừa có nhãn `devops-ex.act=<id>` vừa có tên bắt đầu bằng `act-devops-ex-<id>`, volume và network tên bắt đầu bằng `act-devops-ex-<id>`, và network `devops-ex-<id>` có nhãn của lần chạy; volume dùng chung `act-toolcache` (act 0.2.94 không cho đổi tên) không bao giờ bị xoá. Các lần chạy song song an toàn nhờ tên riêng. Skip khi thiếu `act` (từ `ACT_MIN_VERSION`), git hay image runner. **Mẫu chấm module 07 và capstone m04**: workflow chạy lint, test và tính tag dưới act rồi in `devops-ex-output tag=...`; bước build, push, deploy thật gắn `if: ${{ !env.ACT }}` và chỉ được kiểm tĩnh (cấu trúc YAML, cộng `actionlint` nếu đã cài); harness đọc `act_outputs` rồi tự build, push (`lab.build`, `lab.push`) và deploy bằng `DockerLab`. Không dùng volume `act-toolcache` để cache: thứ dùng chung giữa các lần chạy nằm trong image runner. **Đã kiểm 2026-11-01** (act 0.2.94): module 07 với `SOLUTION=1` pass khi network của job là `--internal` (không ra Internet); trong job `cpuset.cpus.effective` đúng `DEVOPS_CPUSET`, `memory.max` 1073741824, `pids.max` 512, `NoNewPrivs: 1`, không có `/var/run/docker.sock` |
| Push image lên registry local | `address = ex.require_registry()`; trong `with DockerLab() as lab:` dùng `ref = lab.push(tag, "api")` | Service compose `registry` (profile `devops`, `127.0.0.1:${DEVOPS_REGISTRY_PORT:-15000}`, `REGISTRY_STORAGE_DELETE_ENABLED=true`); `require_registry` skip khi chưa chạy hoặc cổng là server khác. `push` chỉ nhận image do chính lab build (`lab.build`), gắn tag `<registry>/devops-ex-<id>/<name>:<tag>` (tiền tố riêng của lab), `close()` xoá manifest trên registry và tag local. Không push dưới tên khác tiền tố của lab |
| Chạy cấu hình OpenTofu của người học (module 08, capstone m05) | `with TofuLab(ex.path("infra")) as lab:` rồi `lab.init()`, `lab.plan("-detailed-exitcode")`, `lab.apply()`, `lab.output("bucket")`, `lab.state("list")`, `lab.run("validate")`; tên tài nguyên lấy từ `var.prefix` (`lab.prefix`, `devops-ex-<id>`) | Skip khi thiếu `tofu` (từ `TOFU_MIN_VERSION`), bwrap hay `localstack-devops` (`ex.require_localstack_devops()`: service profile `devops`, `127.0.0.1:${LOCALSTACK_DEVOPS_PORT:-14566}`, cổng trùng `localstack` của DE hay server khác thì skip). Cấu hình được chép vào thư mục tạm; mọi lệnh `tofu` chạy qua `run_sandboxed` với env `tofu_env(home, prefix=...)` dựng từ đầu: `HOME` tạm, `AWS_ACCESS_KEY_ID`/`AWS_SECRET_ACCESS_KEY` = `test`, `AWS_REGION=us-east-1`, `AWS_CONFIG_FILE`/`AWS_SHARED_CREDENTIALS_FILE=/dev/null`, `AWS_EC2_METADATA_DISABLED=true`, `TF_IN_AUTOMATION=1`, `TF_INPUT=0`, `TF_VAR_prefix`, `TF_CLI_CONFIG_FILE` sinh trong thư mục tạm (`~/.terraformrc`, `TF_CLI_CONFIG_FILE` và biến `AWS_*` của người học không được đọc). **Không bao giờ ra AWS thật**: `AWS_ENDPOINT_URL=http://127.0.0.1:<cổng>` (provider AWS và backend `s3` đều đọc, địa chỉ IP nên S3 tự dùng path-style) nên provider quên `endpoints` vẫn gọi LocalStack; `HTTPS_PROXY`/`HTTP_PROXY` trỏ một cổng loopback đã bind mà không listen, `NO_PROXY` chỉ có loopback, nên request tới host khác (kể cả endpoint AWS thật ghi trong `endpoints {}`) bị từ chối trước khi tra DNS. **Provider offline**: CLI config chỉ có `provider_installation { filesystem_mirror }` trỏ `tofu_plugin_dir()` (`${XDG_CACHE_HOME:-~/.cache}/devops-track/tofu-plugins`, OpenTofu tạo symlink, không chép; mọi lệnh `tofu` do cấu hình người học điều khiển chỉ thấy mirror qua `readonly=`, kể cả khi mirror dưới `/tmp`); mirror thiếu bản trong `TOFU_PROVIDERS` thì `tofu_fetch_providers()` tải một lần bằng cấu hình **của testkit** (`version = "= 6.12.0"`, không bao giờ dùng HCL của người học nên `~> 6.0` không kéo bản mới) qua `run_sandboxed` với `TF_PLUGIN_CACHE_DIR` cùng thư mục; không tải được vì mạng thì skip. Sau `init`, `.terraform.lock.hcl` phải khoá đúng `hashicorp/aws` 6.12.0, khác (hay ràng buộc loại trừ 6.12.0) thì fail kèm lý do LocalStack 4.4.0. Cấu hình có đối số `no_proxy`, `http_proxy`, `https_proxy`, `custom_ca_bundle` (provider hay backend, ở bất kỳ vị trí nào kể cả block một dòng, bỏ qua chú thích `#`, `//`, `/* */`; kể cả `.tf.json` và module con) bị từ chối trước khi chạy lệnh nào (`tofu_config_problems`). `close()` luôn chạy `destroy -auto-approve -lock=false` (lỗi, Ctrl-C); destroy lỗi thì luôn có `UserWarning`, test đang đạt thì fail, test đã lỗi thì giữ lỗi gốc. Rồi `localstack_sweep(lab.prefix)` xoá bằng boto3 trên **chỉ** `localstack-devops` (cổng trùng DE thì từ chối) bucket S3 (kể cả version), bảng DynamoDB, IAM role (gỡ policy, instance profile), IAM policy, tham số SSM, secret của Secrets Manager (xoá ngay) và alias KMS (kèm lên lịch xoá khoá) có tên đúng tiền tố `devops-ex-<8 hex>` hoặc bắt đầu bằng `<tiền tố>-`/`<tiền tố>/` (`lab.swept` liệt kê), rồi xoá thư mục tạm. `endpoint=` của `TofuLab` chỉ dành cho test của testkit (server giả), khi đó không sweep |
| Gọi `docker`, `kind`, `act`, `kubectl`, `helm`, `tofu` thẳng trong test dưới `modules/` hay `capstone/`: lệnh (list, tuple, chuỗi, f-string, `shutil.which(...)`, hay biến gán từ chúng) truyền cho `subprocess.*`, `os.system`/`os.popen`/`os.exec*`, `asyncio.create_subprocess_*`, `Popen` hay hàm cục bộ tên chứa `run`/`exec`, kể cả qua đường dẫn tuyệt đối, wrapper (`nice`, `taskset`, `timeout`, `env`, `sudo`, `stdbuf`, `ionice`, `chrt`), `VAR=x` hay `bash -lc "..."`; hoặc dùng `_docker` | Cấm | Validator (`check_tool_calls`) báo lỗi. Không bắt tuple/list dữ liệu (`parametrize`, vòng `for`, cặp phiên bản), `require_tool(...)`, `require_image(...)`, `shutil.which(...)` đứng riêng, chữ trong chuỗi hay chú thích, dict binary giả. `run_sandboxed`/`sandbox_command` không bị xét: lệnh trong đó chạy trong bwrap, vd. `run_sandboxed(["tofu", "plan"], ...)` |

- Tệp fixture trong repo nhìn thấy được (chỉ đọc) trong sandbox; tệp test tạo ra đặt trong `tmp_path` để script ghi được.
- Ngoại lệ phải có lý do ghi trong `README.md` của bài, ví dụ module 01 Basic 03 (graceful-stop) phải gửi signal tới
  PID thật nên không dùng được `--unshare-pid` của bwrap; bài đó vẫn chạy script với `start_new_session=True` và env
  dựng từ đầu.

### trivy

- DB lỗ hổng dùng chung ở `${XDG_CACHE_HOME:-~/.cache}/devops-track/trivy`. Test chạy với `--cache-dir` đó cộng `--skip-db-update
  --offline-scan --skip-version-check --disable-telemetry --cache-backend memory`; chưa có DB thì thử
  `trivy image --download-db-only` vào đúng thư mục, không tải được thì skip.
- Cấu hình hay ngoại lệ của người học chạy với `trivy sbom` qua `run_sandboxed`; quét image (cần socket Docker) chạy trivy trực
  tiếp với env dựng từ đầu (chỉ `PATH`, `HOME`, biến tìm daemon Docker; không mang `TRIVY_*`), `--config` rỗng và thư mục làm việc tạm, không đọc cấu hình của người học.
- Không bao giờ đếm CVE hay đòi CVE cụ thể có thể biến mất: chấm quyết định chính sách (đọc cấu hình), số gói (SBOM không cần
  DB), hoặc quan hệ; mỗi phép kiểm dựa trên một CVE có lần quét đối chứng không cấu hình, DB không còn CVE đó thì bỏ qua hay skip.

### OpenTofu và LocalStack

- `tofu` bản đã kiểm `TOFU_VERSION` (1.13.2), tối thiểu `TOFU_MIN_VERSION` (1.10, S3 native locking). Provider AWS ghim
  `TOFU_AWS_PROVIDER` (`hashicorp/aws` 6.12.0): **đã kiểm 2026-11-01** với LocalStack 4.4.0, 6.12.0 apply, plan lại không
  đổi và destroy được S3 (kèm versioning), DynamoDB, IAM role, KMS, SSM SecureString; 6.13.0 trở lên kẹt ở chờ bảng DynamoDB
  (`waiting for update ... couldn't find resource`), 6.36 lỗi CreateBucket, 6.71 gọi S3 Control để đọc tag bucket mà
  LocalStack 4.4.0 không có. Đổi bản provider thì kiểm lại bằng test thật trong `tests/test_testkit_devops.py`.
- Cấu hình mẫu và starter khai báo `required_providers` với `version = "6.12.0"` và nhận `variable "prefix"`; mọi tên
  tài nguyên (bucket, bảng, role, alias) bắt đầu bằng `var.prefix` để sweep dọn được và các lần chạy song song không trùng.
- Khối provider trong bài viết như với AWS thật (`provider "aws" { region = "us-east-1" }`), không cần `endpoints`,
  `access_key` hay `s3_use_path_style`: env của `TofuLab` lo phần đó. Hướng dẫn chạy tay trong README dùng cùng các biến
  (`AWS_ENDPOINT_URL=http://127.0.0.1:14566`, `AWS_ACCESS_KEY_ID=test`, `AWS_SECRET_ACCESS_KEY=test`,
  `AWS_REGION=us-east-1`, `AWS_EC2_METADATA_DISABLED=true`). Khi muốn cấu hình tự đứng được không cần env, đặt thêm
  `skip_credentials_validation = true`, `skip_requesting_account_id = true`, `skip_metadata_api_check = true` (và
  `s3_use_path_style = true` khi endpoint là tên miền) trong provider.
- Backend `s3` trên LocalStack chạy được với `use_lockfile = true` (LocalStack 4.4.0 tôn trọng `If-None-Match`, lần chạy
  thứ hai nhận `PreconditionFailed` và báo "Error acquiring the state lock") và với `dynamodb_table`; bucket và bảng của
  backend do test tạo trước bằng boto3 với tên theo `lab.prefix`.
- LocalStack bật S3, IAM, STS, DynamoDB, KMS, SSM, Secrets Manager. Không có trong bản community hay chưa bật: EC2/VPC thật,
  Route 53, S3 Control, Organizations; bài cần các service đó dùng `tofu plan` hay provider mock của `tofu test` thay vì apply.

### Gating

- `ex.require_tool(name, min_version)`: thiếu công cụ, phiên bản cũ hơn mức tối thiểu (so sau khi đệm số 0: `1.27`
  bằng `1.27.0`), không đọc được phiên bản (thông báo riêng, chỉ lệnh để tự kiểm), hay (với `docker`) daemon tắt hoặc
  user không có quyền socket thì skip.
- `ex.require_image(image)`, `ex.require_service(name)`, `ex.require_registry()`, `ex.require_cluster(name="devops-lab")`: skip khi chưa có
  image, service compose, registry local hay cluster kind.
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
- `kind_node_exec`: chạy lệnh trong node kind.

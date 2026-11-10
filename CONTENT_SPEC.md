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
  Ngoại lệ: bài Advanced có test kiểm cấu trúc tự động (khung DESIGN.md, plan JSON...) **được** kèm tệp lời giải mẫu trùng tên
  với tệp trong `starter/` (ví dụ `DESIGN.md`, `aws/*.tf`, `COST.md`) bên cạnh `SOLUTION.md`, để `SOLUTION=1` chạy được thay vì
  skip; mẫu đó chỉ là một lời giải qua test, rubric trong `SOLUTION.md` vẫn là thứ chấm nội dung.

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
| Chạy script hay chương trình của người học trên máy host | `testkit.run_sandboxed(cmd, writable=[tmp_path], cwd=tmp_path, env={...})` (thư mục cần đọc mà không được ghi, kể cả khi nằm dưới `/tmp`: `readonly=[...]`, mount `--ro-bind` sau tmpfs) (cần stdin/stdout dạng bytes hay `Popen` thì `sandbox_command`) | bwrap: `/` chỉ đọc, `/tmp` và `/run` là tmpfs rỗng (riêng tệp đích của `/etc/resolv.conf` khi nằm dưới `/run`, như stub của systemd-resolved, được bind lại chỉ đọc để DNS chạy; không bind thư mục hay socket nào khác), thông tin đăng nhập của mọi home thật bị che khi tồn tại (`~/.docker`, `~/.kube`, `~/.aws`, `~/.ssh`, `~/.config/gcloud`, `~/.azure`, `~/.config/gh`, `~/.terraform.d`, `~/.cache/devops-track/kube` phủ tmpfs; `~/.git-credentials`, `~/.netrc` thay bằng `/dev/null`; symlink được resolve và che ở đích, đích dưới `/tmp` đã bị che sẵn), chỉ các thư mục trong `writable` ghi được (`readonly` nhìn thấy nhưng không ghi được), `HOME` là `cwd`, env dựng lại từ đầu (`PATH`, `HOME`, `LANG`/`LC_ALL`, `PYTHONNOUSERSITE=1` cộng những gì test truyền). Mạng **không** tách. Không dùng được bwrap thì skip, **không bao giờ** chạy trần |
| Repo git tạm (dựng lịch sử, rồi chạy script người học trong repo) | `GitRepo(path, home, writable=[tmp_path])`, `git_env(home)`, `SAFE_GIT_CONFIG`; gọi `repo.taint()` ngay khi code người học đã chạy trong repo | Env dựng từ đầu (`HOME` tạm, `GIT_CONFIG_GLOBAL`/`GIT_CONFIG_SYSTEM=/dev/null`, tác giả và ngày cố định, `GIT_CEILING_DIRECTORIES`); trước `taint()` git chạy trực tiếp kèm `SAFE_GIT_CONFIG` (tắt hook, fsmonitor, ký commit), sau `taint()` mọi lệnh git của test chạy qua `run_sandboxed` vì cấu hình repo có thể đã bị sửa |
| Container do test dựng | `with DockerLab() as lab:` (fixture: dựng container bên trong `with`, rồi `yield lab`) | Nhãn `devops-ex=1`, tên `devops-ex-<uuid8>-<alias>`, `--security-opt no-new-privileges`, giới hạn RAM và số tiến trình (`run_once` cũng nhận `memory`/`pids_limit`), cpuset theo `docker_cpu_args()`, cổng chỉ trên `127.0.0.1` ở cổng trống, mount `:ro`, network riêng. Container nền không dùng `--rm` để `wait_log`/`wait_http` báo lỗi kèm 40 dòng `docker logs` cuối; `close()` luôn xoá mọi container đã tạo bằng `docker rm -f -v` rồi `docker volume rm` volume ẩn danh (tên 64 ký tự hex, sinh từ `VOLUME` của image như `postgres`, `redis`) đã gắn vào chúng, lỗi hay Ctrl-C ở bất kỳ bước nào cũng dọn hết; không đụng volume có tên. `run_once` dùng `--rm`. `lab.stop(alias, timeout)` chạy `docker stop -t` và trả số giây đã chờ, `lab.state(alias)` trả `State` (`ExitCode`, `OOMKilled`, `Health`) để bài vòng đời tiến trình chấm bằng hành vi |
| Build image từ tệp của người học | `tag = lab.build(context, "api", build_args={...})` trả `devops-ex-<id>/<alias>:test`; `lab.image_inspect(tag)`, `lab.history(tag)` | `docker buildx build --builder <context hiện tại> --load --pull=false`; mọi image base trong dòng FROM (bỏ tên stage, `scratch`, ARG không resolve được) phải có sẵn, thiếu thì skip kèm `docker pull <image>` nên build không bao giờ tự kéo image, nhãn `devops-ex=1` và `devops-ex.lab=<id>`, bước RUN bị ghim CPU theo `docker_cpu_args()` và giới hạn RAM (mặc định `1g`). Không `--network`, `--ssh`, `--secret`, `--allow`: Dockerfile không lấy được mạng host, SSH agent hay bí mật. Env của lệnh build dựng từ đầu (không mang `BUILDX_BUILDER`, biến cloud). `close()` chạy `rmi -f` mọi tag đã build, rồi xoá image còn nhãn `devops-ex.lab=<id>`; không bao giờ xoá image base. Build cache của BuildKit dùng chung và không bị dọn (dọn tay bằng `docker builder prune`). Test giới hạn build truyền nonce vào bước RUN để bước đó luôn chạy lại, không lấy từ cache. **Đã kiểm 2026-11-01** (buildx v0.38.1, BuildKit v0.34.0, driver `docker`): RUN `cat /sys/fs/cgroup/cpuset.cpus.effective; nproc; cat memory.max` in `0-35 36 max` khi không cờ, `12-13 2 268435456` với `--cpuset-cpus 12-13 --memory 256m`; `--cpu-quota` bị bỏ qua. Vì driver `docker` tôn trọng cpuset và memory nên **không** dùng builder `docker-container` riêng; builder khác driver `docker` thì skip. Bài cần mạng lúc build (pip, apt) bắt lỗi của `build` và chỉ skip khi `testkit.build_failed_on_network(str(error))` (lỗi mạng nằm trong output của đúng bước lỗi và sau nó không còn dấu hiệu tải thành công); retry đã hồi phục rồi lỗi thật thì vẫn fail |
| Dựng project compose của người học | `project = lab.compose(file, env={...})`; `project.port(service, cổng)`, `project.exec`, `project.logs`, `project.ps()`, `project.container(service)` | Thư mục chứa tệp compose được **chép** vào thư mục tạm của lab, compose chạy từ bản chép (`-p devops-ex-<id>`) với tệp của người học cộng tệp override sinh ra. Cấu hình (output của `docker compose config`) xét theo **allowlist**: service chỉ được image, build (context/dockerfile/args/target trong thư mục), command, entrypoint, environment, env_file (trong thư mục), ports, expose, depends_on, healthcheck, volumes, working_dir, user, labels, restart, stop_signal, stop_grace_period, tmpfs, read_only, init, networks, cap_drop, profiles, hostname, deploy (chỉ `resources.limits` cpus/memory/pids và replicas), logging (json-file/local), ulimits (nofile), cộng các khoá testkit ghi đè (cpuset, mem_limit, pids_limit, memswap_limit, container_name, pull_policy); cấp trên cùng chỉ services, volumes, networks, name, `x-*`. Khoá khác (privileged, cap_add, security_opt, devices, device_cgroup_rules, gpus, runtime, network_mode, pid, ipc, uts, userns_mode, cgroup, sysctls, configs, secrets...) bị **từ chối** kèm lý do; bind mount ngoài thư mục (kèm gợi ý riêng cho docker.sock) cũng vậy. Volume/network cấp trên cùng: `name:` phải bắt đầu bằng `devops-ex-<id>`, không external, driver mặc định, không driver_opts. Override: cpuset, `mem_limit`/`pids_limit` (và `deploy.resources.limits` cùng giá trị), nhãn `devops-ex=1` cho service, volume và network, `security_opt: !override [no-new-privileges:true]`, `ports: !override` về `127.0.0.1:<cổng trống>`, mọi bind mount **chỉ đọc** (cần ghi thì dùng named volume hay tmpfs), bỏ `container_name` và `restart`. Service có `build:` được build bằng `lab.build` (không tạo tag cố định của người học); image khác phải có sẵn (`--pull never`, thiếu thì skip kèm `docker pull`). Env dựng từ đầu cộng `env`. `up -d --wait`; lỗi thì fail kèm 40 dòng log cuối. `close()` chạy `down -v --remove-orphans`. Cần compose ≥ 2.24.4 (`!reset`/`!override`), cũ hơn thì skip. Mỗi lab một project |
| Chạy workflow GitHub Actions của người học | `result = testkit.act_run(project_dir, event="push", job=None, env={...}, secrets={...}, timeout=600, github_token=None)`; `testkit.act_job_results(result)` trả `{job_id: True/False}`; `testkit.act_outputs(result)` trả `{job_id: {key: value}}` từ các dòng `devops-ex-output <key>=<value>` mà bước `run:` in ra (workspace của job là bản chép, tệp job ghi ra không về tới test) | act chạy trên host (cần socket Docker nên không vào bwrap) trên **bản chép tạm** của thư mục thành repo git mới (bỏ `.git`, `.actrc`). Trong bản chép, `name:` cấp trên cùng của mọi workflow đổi thành `devops-ex-<id>-<tên cũ hoặc tên tệp>`: act đặt tên container và volume là `act-<name>-<job>-<sha256>` không phụ thuộc lần chạy, nên không đổi tên thì act tái dùng rồi xoá container, volume trùng tên của người học hay của lần chạy khác. Env dựng từ đầu: `HOME` tạm (không đọc `~/.actrc`, `~/.config/act`), không mang `GITHUB_TOKEN`, `GH_*`, `ACTIONS_*`, `AWS_*`, `DOCKER_*`, `DBUS_*`, `XDG_*` (chỉ `DOCKER_HOST` lấy từ context hiện tại); act luôn nhận secret `GITHUB_TOKEN` giả tường minh (`ACT_DUMMY_GITHUB_TOKEN`, hay `github_token=` của người gọi) nên không bao giờ tới được đăng nhập `gh` của máy (act 0.2.94 chạy `gh auth token` khi thiếu secret này), và `PATH` của act bắt đầu bằng một `gh` giả, bị gọi thì `act_run` fail; `.env`, `.secrets`, `.vars`, `.input` của repo không được đọc; chỉ chạy workflow ngay trong `.github/workflows/` (`-W <bản chép>/.github/workflows/ --no-recurse`). Job chạy trong image ghim `ACT_IMAGE` (`devops-track/act-runner:1.0-<hash8>`, `<hash8>` là 8 ký tự đầu SHA-256 của `Dockerfile` nối `requirements-ci.txt` do `act_runner_tag()` tính nên đổi đầu vào là đổi tag: build một lần từ `setup/act-runner/Dockerfile` trên `node:24.22.2-trixie-slim@sha256:...`, thêm `ca-certificates`, `git`, uv 0.10.8 kiểm SHA-256, CPython 3.12.13 ở `/opt/uv/python`, cache wheel của Olist Shop ở `/opt/uv/cache`, `UV_OFFLINE=1`; image không có nhãn `devops-ex=1`, không thuộc lab nào nên không bị dọn; thiếu thì skip kèm đúng lệnh build `ACT_IMAGE_BUILD`; `--pull=false`), network riêng `devops-ex-<id>`, `docker_cpu_args()`, `--memory 1g --pids-limit 512 --security-opt no-new-privileges`, nhãn `devops-ex=1` và `devops-ex.act=<id>`, không có socket Docker (`--container-daemon-socket -`), `--container-options-policy restrict`, không cache server, tối đa 2 job song song. Kiểm trước khi chạy mọi tệp `*.yml`/`*.yaml` dưới `.github/workflows/` kể cả thư mục con (tệp trong thư mục con bị từ chối): chỉ `runs-on: ubuntu-latest`, bước `run:`, action trong `ACT_ALLOWED_ACTIONS` (hiện chỉ `actions/checkout`: act chép thẳng repo vào job, không clone từ remote **khi không đặt `ref`/`repository`**; vì vậy checkout chỉ được có input trong `ACT_CHECKOUT_INPUTS` (`persist-credentials`, `fetch-depth`, `path`...), `ref`, `repository`, `token` và input khác bị từ chối kèm lý do, và mọi `actions/checkout@<ref>` cũng được thay bằng action rỗng qua `--local-repository` để không bao giờ tải mã của action), và action `owner/repo[/đường-dẫn]@ref` khác **chỉ** ở bước có `if:` (bỏ `${{ }}` và khoảng trắng) đúng bằng `!env.ACT` hoặc là chuỗi `&&` ở cấp trên cùng có một vế đúng bằng `!env.ACT` và mọi vế có ngoặc khác đúng bằng một hàm trạng thái trong `ACT_STATUS_FUNCTIONS` (`always()`, `success()`, `failure()`, `cancelled()`, `!cancelled()`), để bước lưu báo cáo viết được `if: ${{ !cancelled() && !env.ACT }}` (có `||`, nháy kép, `!=`, `$`, `{}` hay ngoặc khác thì không công nhận; chuỗi trong nháy đơn không tính); act bỏ qua bước đó, testkit thay action bằng action composite rỗng cục bộ qua `--local-repository` nên không tải gì, đoạn `.`/`..` trong đường dẫn bị từ chối và thư mục thay thế phải nằm trong thư mục tạm; `uses: docker://...` và action cục bộ `./...` luôn bị từ chối, kể cả có `if:`; `uses:` chứa khoảng trắng hay xuống dòng bị từ chối; workflow đặt biến `ACT` (không phân biệt hoa thường) ở `env:` cấp workflow, job hay bước, hoặc dùng biểu thức cho `env:`, bị từ chối vì sẽ vô hiệu `!env.ACT`; `env`/`secrets` của `act_run` cũng không nhận tên `ACT`; `services:`, `container:`, workflow gọi workflow thì fail kèm lý do. Action khác khi thêm vào danh sách (chỉ action JavaScript) tải một lần về `${XDG_CACHE_HOME:-~/.cache}/devops-track/act` rồi dùng offline (`--action-offline-mode`); thiếu action mà mất mạng thì skip. Bước cài đặt của workflow lỗi vì mạng: test dùng `testkit.act_failed_on_network(result, step_names)`, chỉ xét output của đúng bước có tên trong `step_names` đã fail (giữa `⭐ Run` và `❌ Failure` của cùng job), có lỗi mạng và sau đó không còn dấu hiệu tải thành công thì True để skip; lỗi khác thì fail. Secret đi qua env của tiến trình act (argv chỉ có tên), act che thành `***`, testkit che thêm trong output trả về; secret ngắn hơn 4 ký tự (`ACT_SECRET_MIN_LENGTH`) bị từ chối. Quá `timeout` thì SIGKILL cả nhóm tiến trình và fail kèm output cuối. Mọi đường thoát (xong, lỗi, timeout, Ctrl-C) xoá container vừa có nhãn `devops-ex.act=<id>` vừa có tên bắt đầu bằng `act-devops-ex-<id>`, volume và network tên bắt đầu bằng `act-devops-ex-<id>`, và network `devops-ex-<id>` có nhãn của lần chạy; volume dùng chung `act-toolcache` (act 0.2.94 không cho đổi tên) không bao giờ bị xoá. Các lần chạy song song an toàn nhờ tên riêng. Skip khi thiếu `act` (từ `ACT_MIN_VERSION`), git hay image runner. **Mẫu chấm module 07 và capstone m04**: workflow chạy lint, test và tính tag dưới act rồi in `devops-ex-output tag=...`; bước build, push, deploy thật gắn `if: ${{ !env.ACT }}` (test nhận ra bước đó bằng `testkit.act_skipped_locally(step.get("if"))`, cùng luật công nhận `if:` như trên) và chỉ được kiểm tĩnh (cấu trúc YAML, cộng `actionlint` nếu đã cài); harness đọc `act_outputs` rồi tự build, push (`lab.build`, `lab.push`) và deploy bằng `DockerLab`. Không dùng volume `act-toolcache` để cache: thứ dùng chung giữa các lần chạy nằm trong image runner. **Đã kiểm 2026-11-01** (act 0.2.94): module 07 với `SOLUTION=1` pass khi network của job là `--internal` (không ra Internet); trong job `cpuset.cpus.effective` đúng `DEVOPS_CPUSET`, `memory.max` 1073741824, `pids.max` 512, `NoNewPrivs: 1`, không có `/var/run/docker.sock` |
| Push image lên registry local | `address = ex.require_registry()`; trong `with DockerLab() as lab:` dùng `ref = lab.push(tag, "api")` | Service compose `registry` (profile `devops`, `127.0.0.1:${DEVOPS_REGISTRY_PORT:-15000}`, `REGISTRY_STORAGE_DELETE_ENABLED=true`); `require_registry` skip khi chưa chạy hoặc cổng là server khác. `push` chỉ nhận image do chính lab build (`lab.build`), gắn tag `<registry>/devops-ex-<id>/<name>:<tag>` (tiền tố riêng của lab), `close()` xoá manifest trên registry và tag local. Không push dưới tên khác tiền tố của lab |
| Chạy cấu hình OpenTofu của người học (module 08, capstone m05) | `with TofuLab(ex.path("infra")) as lab:` rồi `lab.init()`, `lab.plan("-detailed-exitcode")`, `lab.apply()`, `lab.output("bucket")`, `lab.state("list")`, `lab.run("validate")`, `lab.plan_json()` (`plan -out` vào tệp tạm rồi `show -json`, trả dict có `resource_changes`); tên tài nguyên lấy từ `var.prefix` (`lab.prefix`, `devops-ex-<id>`); tạo trước hay kiểm tài nguyên bằng `testkit.localstack_client("s3")` (boto3 chỉ trỏ `localstack-devops`, cổng trùng DE thì RuntimeError, không đọc `AWS_*` hay `~/.aws` của người học), đặt tên theo `lab.prefix` để sweep dọn được | Skip khi thiếu `tofu` (từ `TOFU_MIN_VERSION`), bwrap hay `localstack-devops` (`ex.require_localstack_devops()`: service profile `devops`, `127.0.0.1:${LOCALSTACK_DEVOPS_PORT:-14566}`, cổng trùng `localstack` của DE hay server khác thì skip). Cấu hình được chép vào thư mục tạm; mọi lệnh `tofu` chạy qua `run_sandboxed` với env `tofu_env(home, prefix=...)` dựng từ đầu: `HOME` tạm, `AWS_ACCESS_KEY_ID`/`AWS_SECRET_ACCESS_KEY` = `test`, `AWS_REGION=us-east-1`, `AWS_CONFIG_FILE`/`AWS_SHARED_CREDENTIALS_FILE=/dev/null`, `AWS_EC2_METADATA_DISABLED=true`, `TF_IN_AUTOMATION=1`, `TF_INPUT=0`, `TF_VAR_prefix`, `TF_CLI_CONFIG_FILE` sinh trong thư mục tạm (`~/.terraformrc`, `TF_CLI_CONFIG_FILE` và biến `AWS_*` của người học không được đọc). **Không bao giờ ra AWS thật**: `AWS_ENDPOINT_URL=http://127.0.0.1:<cổng>` (provider AWS và backend `s3` đều đọc, địa chỉ IP nên S3 tự dùng path-style) nên provider quên `endpoints` vẫn gọi LocalStack; `HTTPS_PROXY`/`HTTP_PROXY` trỏ một cổng loopback đã bind mà không listen, `NO_PROXY` chỉ có loopback, nên request tới host khác (kể cả endpoint AWS thật ghi trong `endpoints {}`) bị từ chối trước khi tra DNS. **Provider offline**: CLI config chỉ có `provider_installation { filesystem_mirror }` trỏ `tofu_plugin_dir()` (`${XDG_CACHE_HOME:-~/.cache}/devops-track/tofu-plugins`, OpenTofu tạo symlink, không chép; mọi lệnh `tofu` do cấu hình người học điều khiển chỉ thấy mirror qua `readonly=`, kể cả khi mirror dưới `/tmp`); mirror thiếu bản trong `TOFU_PROVIDERS` thì `tofu_fetch_providers()` tải một lần bằng cấu hình **của testkit** (`version = "= 6.12.0"`, không bao giờ dùng HCL của người học nên `~> 6.0` không kéo bản mới) qua `run_sandboxed` với `TF_PLUGIN_CACHE_DIR` cùng thư mục; không tải được vì mạng thì skip. Sau `init`, `.terraform.lock.hcl` phải khoá đúng `hashicorp/aws` 6.12.0, khác (hay ràng buộc loại trừ 6.12.0) thì fail kèm lý do LocalStack 4.4.0. Cấu hình có đối số `no_proxy`, `http_proxy`, `https_proxy`, `custom_ca_bundle` (quét văn bản thô của `*.tf`, `*.tofu`, tệp test `*.tftest.hcl`/`*.tofutest.hcl` và bản `.json` của chúng, kể cả module con: tên cấm theo sau bởi `=` hay `:` ở bất kỳ đâu, **kể cả trong chú thích hay chuỗi**, đều bị từ chối để mẹo `/*` trong chuỗi hay heredoc không lách được; chỉ nhắc tên mà không có `=`/`:` thì được; riêng các tệp `.json` còn cấm mọi escape `\uXXXX` ở khoá hay giá trị, phải parse được bằng `json` (lồng quá sâu cũng bị từ chối), và mọi khoá đã giải mã ở mọi độ sâu được so không phân biệt hoa thường với tên cấm) bị từ chối trước khi chạy lệnh nào (`tofu_config_problems`). `close()` luôn chạy `destroy -auto-approve -lock=false` (lỗi, Ctrl-C); destroy lỗi thì luôn có `UserWarning`, test đang đạt thì fail, test đã lỗi thì giữ lỗi gốc. Rồi `localstack_sweep(lab.prefix)` xoá bằng boto3 trên **chỉ** `localstack-devops` (cổng trùng DE thì từ chối) bucket S3 (kể cả version), bảng DynamoDB, IAM role (gỡ policy, instance profile), IAM policy, tham số SSM, secret của Secrets Manager (xoá ngay) và alias KMS (kèm lên lịch xoá khoá) có tên đúng tiền tố `devops-ex-<8 hex>` hoặc bắt đầu bằng `<tiền tố>-`/`<tiền tố>/` (`lab.swept` liệt kê), rồi xoá thư mục tạm. `endpoint=` của `TofuLab` chỉ dành cho test của testkit (server giả), khi đó không sweep |
| Chạy playbook, role, inventory Ansible của người học (module 09, capstone m05) | `with AnsibleLab(["worker-1", "worker-2"]) as lab:` rồi `project = lab.stage(ex.target)`, `run = lab.playbook("site.yml", "--diff", inventory=["inventory"], cwd=project)` trả `AnsibleRun` (`returncode`, `output`, `recap` theo host, `changed`, `tasks(name, host=, changed=, handler=)`, `connections`, `pinned_overrides` đọc từ callback của lab, không parse văn bản); `lab.run("ansible-inventory", ..., env={...})`, `lab.run("ansible-vault", ...)` (`env` chỉ thêm biến cho chương trình của bài như script inventory động, không đặt được `ANSIBLE_*`, `HOME`, `PATH`); kiểm target bằng `lab.read(host, path)`, `lab.stat(host, path)`, `lab.exec(host, ...)`; `AnsibleLab()` không host thì không dựng container | Skip khi thiếu `ansible-playbook` (từ `ANSIBLE_MIN_VERSION`, bản đã kiểm `ANSIBLE_VERSION` 2.21.5), bwrap hay Docker. Target là container do `DockerLab` dựng từ image build bằng `lab.build(setup/ansible-target)` (`python:3.12.16-slim-trixie` cộng openssh-server, sudo, `systemd` chỉ để có `systemd-analyze`, `packaging` cho module `pip`, wheel của worker Olist Shop ở `/srv/wheels`; lỗi mạng lúc build lần đầu thì skip theo `build_failed_on_network`): sshd chạy bằng root làm PID 1, **không** có systemd chạy thật (systemd trong container cần quyền mà `DockerLab` cấm), `no-new-privileges`, RAM 512m, cổng 22 chỉ trên `127.0.0.1` ở cổng trống; sshd giữ được với capability mặc định (`SYS_CHROOT`, `SETUID`, `SETGID`), `sudo` của root vẫn chạy dưới `no-new-privileges`. Lab dùng hai thư mục tạm: thư mục **điều khiển** (`lab.control`: khoá ed25519, `ssh_config`, `known_hosts`, `allowed`, script ProxyCommand, callback, `ansible.cfg`, `lab-conn.yml`, `lab.ini`, `ANSIBLE_HOME`, và thư mục rỗng cho roles, collections và **mọi** đường dẫn plugin của ansible-core 2.21.5: action, become, cache, cliconf, connection, filter, httpapi, inventory, lookup, netconf, strategy, terminal, test, vars, doc_fragment, `library`, `module_utils`; callback trỏ thư mục chứa callback của lab; `collections_scan_sys_path = False`) mà sandbox chỉ thấy qua `readonly=` (ghi vào đó trong sandbox trả `EROFS`), thư mục **bài** (`lab.root`: bài đã chép, tệp test ghi) cũng chỉ đọc trong sandbox, và thư mục **ghi được** (`lab.work`, thư mục tạm riêng, không nằm trong hay cạnh bài đã chép) chỉ có `home` (`HOME`, local tmp), `cp` (control path) và `events` (tệp sự kiện). Plugin cạnh playbook hay trong role (`*_plugins/`, `library/`, `module_utils/`) không tắt được bằng cấu hình và, đã kiểm với 2.21.5, che được cả `ansible.builtin.ssh` (module plugin cùng tên nằm sẵn trong `sys.modules`), nên `stage()` từ chối chúng và không ai tạo được chúng trong bài lúc chạy (bài chỉ đọc). Code của bài trong sandbox vẫn ghi được một role có `vars_plugins/`, `filter_plugins/` vào `HOME`, và Ansible nạp plugin cạnh mọi role nó tải; vì vậy `stage()` từ chối mọi tham chiếu role, playbook, task hay tệp biến có thể trỏ ra ngoài bài (xem phép quét bên dưới), và `HOME` nằm ở `lab.work` nên `../home` từ bài không tới đâu cả. Code nào của bài vẫn chạy được trên máy điều khiển thì chạy trong sandbox. Tên module, action hay plugin không ghi FQCN chỉ bị thay khi có đường dẫn plugin ghi được, mà giờ không còn. Trước mỗi lệnh `ansible-*`, lab ghi lại mọi tệp điều khiển từ bản trong bộ nhớ (tệp tạm rồi `os.replace`) và xoá tệp, thư mục lạ trong đó. Khoá host của mỗi container được ghim vào `known_hosts`; ssh chạy với `-F` tệp riêng (`StrictHostKeyChecking yes`, `IdentityAgent none`, `GlobalKnownHostsFile /dev/null`, `BatchMode yes`, `ProxyCommand` (python gốc bằng đường dẫn tuyệt đối cố định, chạy `-I`: không user site, không biến `PYTHON*`, không thêm thư mục script vào `sys.path`; đường dẫn trong nháy kép) chỉ mở kết nối tới `127.0.0.1:<cổng của lab>` liệt kê trong `allowed`). `lab.ini` chỉ liệt kê tên máy, truyền **sau** inventory của bài. **Biến kết nối bị ghim** (`ANSIBLE_PINNED_VARS`) bằng extra vars `-e @<control>/lab-conn.yml`, luôn là đối số cuối, nên thắng `set_fact`, inventory (kể cả script động), `vars:` và từ khoá `connection:`: `ansible_connection: ansible.builtin.ssh` (FQCN để không đi qua `ansible.legacy`, nơi plugin của người dùng thắng); `ansible_host` và `ansible_ssh_host` = `{{ devops_ex_lab_addr[inventory_hostname] | default('0.0.0.0') }}`, `ansible_port` và `ansible_ssh_port` = `{{ devops_ex_lab_port[inventory_hostname] | default(1) }}` (ghim cả tên cũ vì plugin ssh lấy tên khai báo sau cùng; máy ngoài lab, kể cả `localhost` ngầm định, thành `0.0.0.0:1` và bị ProxyCommand chặn); `ansible_user`, `ansible_ssh_user: root` (lab chỉ đăng nhập bằng root; `become`, `become_user` vẫn chạy; đặt hai biến này ở chỗ khác bị bỏ qua mà không báo, vì đó là thực hành bình thường ở production); `ansible_ssh_args` của lab; `ansible_ssh_common_args`, `ansible_ssh_extra_args`, `ansible_scp_extra_args`, `ansible_sftp_extra_args`, `ansible_ssh_pkcs11_provider` rỗng; `ansible_ssh_executable: ssh`, `ansible_sftp_executable: sftp`, `ansible_scp_executable: scp`, `ansible_ssh_transfer_method: smart`; `ansible_host_key_checking`, `ansible_ssh_host_key_checking` true; `ansible_ssh_private_key_file`, `ansible_private_key_file` là khoá của lab, `ansible_private_key`, `ansible_ssh_private_key` null; `ansible_control_path: "%(directory)s/%%C"`, `ansible_control_path_dir` là thư mục `cp` của lab (không dùng lại được master của host khác); `ansible_pipelining`, `ansible_ssh_pipelining` true (không bài nào cần đổi). `ansible_python_interpreter`, `ansible_become_*` không bị ghim. Mọi lệnh `ansible-*` chạy qua `run_sandboxed` với env dựng từ đầu (`ANSIBLE_CONFIG` trỏ tệp của lab nên `ansible.cfg` của bài, `~/.ansible.cfg`, `/etc/ansible` không được đọc; `HOME` tạm; `PYTHONNOUSERSITE=1`; không mang `ANSIBLE_*`, `SSH_AUTH_SOCK`; sandbox che `~/.ssh`). Phân vai: **ranh giới** cho code của bài chạy trên máy điều khiển (script inventory, lookup, task lỡ chạy local) là sandbox bwrap; **thứ giữ kết nối trong lab** là biến kết nối ghim cộng tệp điều khiển chỉ đọc cộng khoá host ghim cộng ProxyCommand; **phát hiện** (không phải ranh giới, vì tệp sự kiện phải ghi được nên code của bài trong sandbox có thể ghi thêm vào đó): `playbook()` đánh dấu lần chạy lỗi (`guard_problems`) khi callback thấy task trên host ngoài lab, task không đi bằng `ansible.builtin.ssh` tới `127.0.0.1:<cổng của máy thực thi>` (task có `delegate_to` đọc `_ansible_delegated_vars`, cái duy nhất ansible-core 2.21 đưa cho callback; task khác resolve tên kết nối qua VariableManager của play, tên khai báo sau thắng như plugin ssh), kết nối bị ProxyCommand chặn (sự kiện `connect`), hay chỗ bài cố đặt biến bị ghim (khoá `ansible_facts` của `set_fact`/`include_vars`, `vars` của task, block, role, play, biến host và nhóm của inventory, `connection:` khác ssh). Phép quét tĩnh `ansible_problems` khi `stage()` (chép thư mục bài, bỏ `README.md`, `SOLUTION.md`) phần lớn là tín hiệu dạy học, riêng phần tham chiếu ra ngoài bài là lớp chặn chính cho plugin cạnh role (cộng `HOME` không với tới bằng đường dẫn tương đối): quét văn bản thô, kể cả chú thích và chuỗi: `connection`, `ansible_connection`, `ansible_host`, `ansible_port`, `ansible_ssh_*`, `*host_key_checking`, `ssh_args`, `delegate_to`, `local_action`, `add_host`... theo sau bởi `:` hay `=`; lookup `pipe`/`lines`; escape `\xNN`, `\uNNNN`, `\UNNNNNNNN`; `localhost`, 127.0.0.0/8 cả dạng rút gọn (`127.1`, `127.0.0.01`), `0.0.0.0`, `0x7f...`, `2130706433`, `::1`, `::ffff:127...`, `[::]` ở mọi tệp ngoài `templates/` và `files/`; thư mục `*_plugins`, `collections`, `library`, `module_utils`; `..` dạng thành phần đường dẫn ở mọi tệp; `roles_path`; tham chiếu `roles`, `dependencies`, `include_role`/`import_role` (`name`, `tasks_from`, `vars_from`, `defaults_from`, `handlers_from`), `include_tasks`, `import_tasks`, `import_playbook`, `vars_files`, `include_vars` (`file`, `dir`) có `..`, đường dẫn tuyệt đối, `~`, `$`, `\`, alias hay anchor YAML, tag (`!vault`, `!unsafe`) hay template (`{{`, `{%`), xét cả trên văn bản thô (phần còn lại của dòng) lẫn trên YAML đã giải mã (escape, nối dòng, alias đều đã được giải); tham chiếu code trỏ vào thư mục dữ liệu (`group_vars`, `host_vars`, `vars`, `defaults`, `files`, `templates`); tệp mã hoá cả tệp bằng vault nằm ngoài các thư mục dữ liệu đó (phép quét không đọc được nội dung đã mã hoá). `src` của `template`/`copy` không bị xét vì chỉ đọc tệp, không nạp code; tên khoá dựng bằng Jinja2 hay script inventory lách được nó. Test của testkit cho từng đường vòng (khoá `set_fact` dựng bằng template, kể cả `ansible_ssh_host`/`ansible_ssh_port` trỏ sang cổng của host khác trong lab; khoá escape; script inventory đặt `local`; `hosts: "{{ 'local' ~ 'host' }}"`; script inventory ghi đè `lab-conn.yml`, callback, script proxy, `known_hosts`, `allowed`, `ssh_config`, `ansible.cfg`; script inventory ghi `$HOME/.ansible/plugins/connection/ssh.py`, `<bài>/connection_plugins/ssh.py`, `<bài>/action_plugins/copy.py` ở lần chạy đầu; script inventory ghi vào `HOME` một role có `vars_plugins/`, `filter_plugins/` rồi bài trỏ tới nó bằng `../`, template hay đường dẫn tuyệt đối: `stage()` từ chối trước khi chạy, bài chỉ dùng role trong bài thì không plugin nào trong `HOME` được nạp, `../home` không tới được role, còn đối chứng bỏ qua phép quét bằng đường dẫn tuyệt đối thì có nạp, trong sandbox; script inventory cài `usercustomize.py` và `.pth` vào user site trong `HOME`: không chạy trong ProxyCommand hay ansible-playbook): task của host trong lab vẫn chạy qua ssh trên đúng container, kết nối ra ngoài lab bị chặn, mọi lần ghi tệp điều khiển trả `EROFS` và lần chạy thứ hai vẫn dùng ssh tới lab với callback gốc, lần chạy bị đánh dấu lỗi khi có đường vòng. `close()` (lỗi hay Ctrl-C) xoá container, image, network qua `DockerLab.close` và thư mục tạm |
| Chạy manifest, chart, script kubectl/helm của người học trên Kubernetes (module 10, 11, capstone m06) | `with KubeLab(allow=(...), pod_security="baseline") as lab:` rồi `lab.apply_learner(ex.path("k8s"))` (tệp, thư mục hay thư mục Kustomize), `lab.helm_install("api", ex.path("chart"), "--set", ...)`, `lab.kubectl("get", "deploy", "api", "-o", "json")`, `lab.helm("list")`, `lab.run(["bash", "deploy.sh"], cwd=..., readonly=[ex.target])` (script tự gọi kubectl); việc của admin chỉ qua helper từ spec đã kiểm: `lab.admin_local_pv({"name": "data", "capacity": "1Gi", "node": "devops-lab-worker"})` (PV `local` dưới `/srv/devops-lab-pv/<id>/<name>` trong worker, `claimRef` giữ cho PVC của lab), `lab.node_action({"action": "drain", "node": "devops-lab-worker2"})` (cordon, uncordon, drain có eviction, taint, untaint; chỉ worker, `close()` hoàn tác rồi chờ Deployment trong `kube-system`, `local-path-storage`, `devops-gateway`, `argocd`, `devops-git` available lại; trạng thái node không đếm theo lab nên lần `node_action` đầu giữ khoá flock `~/.cache/devops-track/kube-nodes.lock` tới khi `close()` xong, hai lab dùng `node_action` không bao giờ chạy chồng nhau, kể cả ở hai tiến trình; mỗi thao tác ghi vào `kube-nodes.state.json` cạnh khoá trước khi chạy và xoá khi đã hoàn tác (tệp chỉ được đọc, ghi, xoá khi đang giữ khoá), nên lab bị SIGKILL thì `require_cluster` của bài sau (khoá rảnh) hay lần `node_action` sau giữ khoá, so tệp với trạng thái thật của node, hoàn tác phần còn trên cluster rồi chạy tiếp; chỉ skip kèm lệnh `kubectl uncordon`/`kubectl taint ... -` khi chính việc hoàn tác lỗi; drain nhận `timeout` 10 tới 120 giây; tệp test dùng `node_action` phải có `pytestmark = pytest.mark.kube_nodes` ở cấp module, validator kiểm); `lab.namespace` (`devops-ex-<id>`), `lab.label` (`devops-ex=<id>`); `testkit.kube_leftovers(lab.id)`; lệnh cố định của testkit trong node: `kind_node_exec("devops-lab-control-plane", "etcdctl", ...)`, `kind_node_cp(node, "/đường/dẫn", tmp_path / "x")` | Skip khi thiếu kind, kubectl, bwrap, khi Docker tắt, chưa có cluster `devops-lab`, node đang dừng hay `/readyz` không trả `ok` trong 5 giây (bốn thông báo khác nhau). Kubeconfig admin lấy bằng `kind get kubeconfig` mỗi lần (không bao giờ đọc `KUBECONFIG`, `~/.kube`), chỉ dùng cho lệnh cố định của testkit, không mount vào sandbox của người học. Namespace `devops-ex-<id>` nhãn `devops-ex=<id>`, Pod Security `enforce=baseline` (hoặc `restricted`), `warn`/`audit=restricted`. Ranh giới: người học (kể cả `lab.kubectl`) dùng token của ServiceAccount `devops-ex-learner` gắn một Role riêng trong namespace của lab (workload, Service, ConfigMap, Secret, PVC, NetworkPolicy, Ingress, HTTPRoute, HPA, PDB, Role/RoleBinding, ResourceQuota, LimitRange, Application của ArgoCD...; không AppProject; không `impersonate`, không `serviceaccounts/token`, không escalate/bind; `allow` có CustomResourceDefinition thì thêm quyền ghi mọi resource của nhóm API riêng `lab.api_group` (`<namespace>.olist.test`) trong namespace của lab, CRD phải thuộc nhóm đó và không có conversion webhook (API server gọi URL đó từ mạng của control plane), `names.categories`, `names.shortNames` (dùng chung cho mọi lab), kiểm cả tĩnh lẫn trong policy của lab), `view` cộng quyền đọc object cluster-scoped, ghi chỉ các kind trong `allow` (`KUBE_ALLOWABLE`: ClusterRole, ClusterRoleBinding, IngressClass, PriorityClass, CustomResourceDefinition; không có StorageClass hay PersistentVolume: PV của bài trỏ được nfs tới máy host hay giữ sẵn PVC của lab khác). ValidatingAdmissionPolicy chính của lab (`devops-ex-<id>`) áp cho MỌI ServiceAccount trong namespace của lab (nhóm `system:serviceaccounts:<ns>`, nên token mount trong pod của ServiceAccount khác cũng bị bắt): object cluster-scoped tạo, sửa, xoá phải có nhãn `devops-ex=<id>`, PV không hostPath/local, PriorityClass không `globalDefault`, ClusterRoleBinding không cấp cho nhóm hay user `system:*`. Policy RBAC của lab (`devops-ex-<id>-rbac`, cũng cho mọi ServiceAccount của namespace, áp cả Role/RoleBinding trong namespace): không nhãn `rbac.authorization.k8s.io/aggregate-to-*` (gộp quyền vào `view`, `edit`, `admin` dùng chung của mọi lab), không aggregationRule, binding không cấp cho `system:*` hay ServiceAccount của namespace khác (subject ServiceAccount của RoleBinding bỏ trống namespace là namespace của chính binding, được nhận). Policy PV của lab (`devops-ex-<id>-pv`) từ chối PV hostPath với mọi user không phải thành phần hệ thống (kể cả admin) và PV local ngoài `/srv/devops-lab-pv/` hay không do admin tạo. Policy route của lab (`devops-ex-<id>-routes`, cho mọi ServiceAccount của namespace): Ingress `ingressClassName: devops-traefik`, không `defaultBackend`, HTTPRoute chỉ gắn `devops-gateway/public`, mọi host là `lab.hostname` hay tên con. Policy ArgoCD của lab (`devops-ex-<id>-argocd`, cho mọi ServiceAccount của namespace): Application có `spec.project` là `devops-ex-<id>`, destination là namespace của lab trên `https://kubernetes.default.svc`, repoURL là `lab.repo_url`, không `sourceHydrator`, không `operation.sync.source`/`sources`/`manifests` (ArgoCD không đối chiếu chúng với project), không tạo hay sửa `status`. Tổng cộng năm ValidatingAdmissionPolicy mỗi lab (`devops-ex-<id>`, `-rbac`, `-pv`, `-routes`, `-argocd`), lab chỉ trao kubeconfig khi tất cả đã chặn lần tạo thử (policy ArgoCD chỉ thử khi cluster có CRD của ArgoCD). Pod Security baseline của namespace. StorageClass bị từ chối (tham số `pathPattern` của local-path trỏ ra ngoài thư mục dữ liệu, tới socket containerd). Kubeconfig của lab (một context, namespace của lab) nằm trong thư mục chỉ đọc; `HOME`, cache/config/data của helm trong thư mục ghi được; `KUBERC=off`; `kubectl`/`helm` từ chối `--kubeconfig`, `--context`, `--cluster`, `--user`, `--group`, `--serviceaccount`, `--server`/`-s`, `--token`, `--as*`, cờ chứng chỉ, với helm mọi `--kube*`; riêng `--user`, `--group`, `--serviceaccount` được nhận khi argv bắt đầu bằng `create rolebinding` hay `create clusterrolebinding` (subject của binding; đặt trước lệnh con là cờ toàn cục, bị từ chối). `lab.can_i(verb, resource, serviceaccount=... | user=..., groups=..., subresource=..., all_namespaces=...)` hỏi `kubectl auth can-i --as` bằng kubeconfig admin, chỉ đọc, vì token của lab không có `impersonate`. `apply_learner`/`helm_install` kiểm tĩnh bằng `kube_manifest_problems` (namespace khác, AppProject, ApplicationSet, Application có project, destination hay repoURL ngoài lab, `operation.sync.source`/`sources`/`manifests` hay `status`, cluster-scoped thiếu nhãn hay ngoài `allow`, Namespace, Node, webhook, admission policy, binding vào cluster-admin hay `system:*`, verb escalate/bind/impersonate, privileged, hostPath, hostNetwork/PID/IPC, hostPort, capability ngoài baseline, PV hostPath/local, Service externalIPs; không nhận symlink, alias YAML) rồi apply đúng JSON đã kiểm. Ranh giới là RBAC, policy và Pod Security trong cluster; kiểm tĩnh là tín hiệu sớm. `close()` xoá Application của lab (gỡ finalizer khi ArgoCD không xử lý kịp), gỡ finalizer `argocd.argoproj.io/hook-finalizer` khỏi hook còn dở (ArgoCD chỉ gỡ khi hook kết thúc; Application bị xoá lúc hook kẹt thì namespace kẹt Terminating), namespace, object cluster-scoped có nhãn của lab, AppProject của lab và repo git của lab, không xoá gì khác. `kind_node_exec`/`kind_node_cp` chỉ nhận container `devops-lab-control-plane`, `devops-lab-worker`, `devops-lab-worker<số>` có nhãn kind của `devops-lab`, argv không qua shell; lệnh chạy bằng root trong node privileged nên validator bắt node, lệnh, đường dẫn trong node, `input`, `to_node` phải là hằng viết sẵn và hai hàm chỉ được gọi trực tiếp. `kind_node_exec`/`kind_node_cp` không bao giờ mang nội dung do người học viết vào node và không bao giờ apply tệp của người học bằng quyền admin; việc admin trên đầu vào của người học chỉ đi qua `admin_local_pv`, `node_action` và apply của `KubeLab` |
| Mã hoá, giải mã bằng SOPS + age (module 12, capstone) | `key, public = testkit.age_keypair(tmp_path / "keys", outside=[project])`; `run_sandboxed(["sops", "decrypt", "s.enc.yaml"], writable=[work, home], readonly=[key.parent], cwd=work, env=testkit.sops_env(home, key, outside=[project]))` | `age-keygen -o` chạy trong sandbox, chỉ thư mục khoá ghi được; khoá riêng quyền 0600, không bao giờ in ra; thư mục khoá nằm trong repo hay trong `outside` (project, repo git của bài) thì `ValueError`, kể cả khi trỏ vào đó qua symlink hay `..`. `sops_env` đặt `HOME`, `XDG_CONFIG_HOME`, `GNUPGHOME` tạm và `SOPS_AGE_KEY_FILE` của lab; không mang `SOPS_*`, `AGE_*`, `GNUPGHOME` của máy, không đọc `~/.config/sops` (sandbox còn che `~/.config/sops`, `~/.gnupg`, `~/.vault-token`). Khoá dưới `/tmp` phải truyền `readonly=[key.parent]`. Bản đã kiểm `SOPS_VERSION` (3.13.3) / `AGE_VERSION` (1.3.2), tối thiểu `SOPS_MIN_VERSION` (3.9) / `AGE_MIN_VERSION` (1.2) |
| Vault dev (module 12, capstone) | `ex.require_vault_devops()`; `run_sandboxed(["vault", "kv", "get", "secret/app"], ..., env=testkit.vault_env(token, tmp_path / "vault-home"))` với `testkit.VAULT_DEV_TOKEN` hay token con do test tạo | Service compose `vault-devops` (profile `devops`, `VAULT_IMAGE` = `hashicorp/vault:2.2.1` ghim digest, dev mode chỉ trong RAM, `127.0.0.1:${DEVOPS_VAULT_PORT:-18200}`, cpuset). Token root dev là chuỗi cố định cho lab (`DEVOPS_VAULT_TOKEN`, mặc định `devops-lab-root`, không bí mật). `vault_env` chỉ trả `VAULT_ADDR` của lab, token truyền vào và `HOME` là thư mục tạm bắt buộc (ngoài repo; `vault login` ghi `.vault-token` ở đó chứ không vào project của người học), không mang `VAULT_*` của máy. `require_vault_devops` skip khi service chưa chạy hay cổng là server khác (`/v1/sys/health` không trả Vault đã unseal). Tắt: `docker compose -f setup/docker-compose.yml --profile devops rm -s -f -v vault-devops` (image có `VOLUME`, cần `-v`) |
| GitOps bằng ArgoCD (module 12, capstone m07) | `ex.require_argocd()`; trong `with KubeLab() as lab:`: `lab.argocd_project()` (trả `devops-ex-<id>`), `lab.gitops_repo(ex.path("gitops"))` (trả `lab.repo_url`, gọi lại với nội dung mới là thêm commit), `lab.apply_learner(...)` cho manifest `Application` (`spec.project` = project của lab, `repoURL` = `lab.repo_url`, plugin `sops-kustomize` khi repo có `*.enc.yaml`), `lab.argocd_wait("web", health="Healthy", sync="Synced", timeout=180)`, `lab.sops_age_recipient` (cũng là `lab.age_public_key`) cho `sops encrypt --age` hay `.sops.yaml`; `lab.gitops_revision` là SHA của commit cuối | ArgoCD v3.5.6 bản core do admin cài một lần từ `setup/kind/argocd/` (Application chỉ trong namespace `devops-ex-*`, sync bằng impersonation ServiceAccount `devops-ex-learner` của lab nên RBAC, policy, Pod Security của lab vẫn áp dụng; AppProject `default` khoá trống). `argocd_project` tạo AppProject `devops-ex-<id>` trong `argocd` bằng quyền admin: `sourceRepos` chỉ repo của lab, `destinations` chỉ namespace của lab trên `https://kubernetes.default.svc`, `sourceNamespaces` chỉ namespace của lab, không `clusterResourceWhitelist`, `destinationServiceAccounts` là `devops-ex-learner`. Token của lab ghi `applications.argoproj.io` trong namespace của lab, không ghi `appprojects`. `gitops_repo` chép tệp thường (bỏ `.git`, từ chối symlink, tệp có `AGE-SECRET-KEY-`, quá `KUBE_GITOPS_MAX_FILES` 2000 tệp hay `KUBE_GITOPS_MAX_BYTES` 20 MiB mỗi lần, đếm theo byte đọc được lúc chép; bundle cả lịch sử của lab quá `KUBE_GITOPS_MAX_REPO_BYTES` 40 MiB) vào repo git mới (`GitRepo`, `SAFE_GIT_CONFIG`) rồi bằng quyền admin đưa bundle vào git server chỉ đọc (`git daemon` trong `devops-git`, NetworkPolicy chỉ cho repo-server), refresh mọi Application của lab. `argocd_wait` đọc bằng token của lab, chờ cả commit cuối của `gitops_repo` và không còn thao tác sync đang chạy; lỗi thì in health, sync, revision, thông điệp, không in object. Khoá riêng age chỉ ở Secret `argocd/devops-sops-age`, chỉ mount vào sidecar CMP; testkit chỉ đọc ConfigMap `argocd/devops-sops-age-public`. `close()` xoá Application, gỡ `hook-finalizer` khỏi hook còn dở, xoá AppProject và repo của lab; lab bị giết trước `close()` thì lab mở sau xoá repo, bundle, AppProject không còn namespace. Repo-server chỉ ra được DNS, git server, redis (NetworkPolicy egress), HTTP(S) qua proxy chết, sidecar tắt git; CMP từ chối sớm tệp SOPS có khoá kms, hc_vault, pgp... (kiểm theo tên, lọt được, ranh giới thật là egress). Application không có subresource `status`: token của lab dùng `kubectl apply`, `patch`, `annotate` được, còn `kubectl replace` hay `apply --force` bị policy từ chối vì gửi lại object thiếu `status`; test và bài của module 12, capstone m07 dùng apply hay patch. Manifest `Application` của bài ghi placeholder `LAB_PROJECT`, `LAB_REPO_URL`, `LAB_NAMESPACE`; test thay bằng `lab.argocd_project()`, `lab.repo_url`, `lab.namespace` trước `apply_learner`. `argocd --core` (CLI v3.5.6) không đọc Application ngoài namespace `argocd` (`namespace ... is not permitted`), nên bài đọc trạng thái bằng `kubectl`; bài Vault dùng `vault` CLI tối thiểu 1.15 (bản đã kiểm 2.2.1) |
| Gọi `docker`, `kind`, `act`, `kubectl`, `helm`, `tofu`, `sops`, `age`, `age-keygen`, `vault`, `argocd` thẳng trong test dưới `modules/` hay `capstone/`: lệnh (list, tuple, chuỗi, f-string, `shutil.which(...)`, hay biến gán từ chúng) truyền cho `subprocess.*`, `os.system`/`os.popen`/`os.exec*`, `asyncio.create_subprocess_*`, `Popen` hay hàm cục bộ tên chứa `run`/`exec`, kể cả qua đường dẫn tuyệt đối, wrapper (`nice`, `taskset`, `timeout`, `env`, `sudo`, `stdbuf`, `ionice`, `chrt`), `VAR=x` hay `bash -lc "..."`; hoặc dùng `_docker` | Cấm | Validator (`check_tool_calls`) báo lỗi. Không bắt tuple/list dữ liệu (`parametrize`, vòng `for`, cặp phiên bản), `require_tool(...)`, `require_image(...)`, `shutil.which(...)` đứng riêng, chữ trong chuỗi hay chú thích, dict binary giả. `run_sandboxed`/`sandbox_command`/`kind_node_exec`/`kind_node_cp` và phương thức của lab (`lab.kubectl`) không bị xét: lệnh trong đó chạy trong bwrap hay chỉ trong node kind, vd. `run_sandboxed(["tofu", "plan"], ...)`, `run_sandboxed(["sops", "decrypt", ...], env=sops_env(...))` |

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

### Ansible

- `ansible-core` bản đã kiểm `ANSIBLE_VERSION` (2.21.5), tối thiểu `ANSIBLE_MIN_VERSION` (2.21), cài trong venv riêng
  `${XDG_CACHE_HOME:-~/.cache}/devops-track/ansible` bằng `uv pip install --require-hashes -r setup/ansible/requirements.txt`
  (hash SHA-256 của mọi wheel, kiểm trước khi cài) rồi symlink lệnh vào `~/.local/bin`. Không thêm vào `pyproject.toml` gốc
  để lock của các track khác không đổi.
- Bài chỉ dùng module `ansible.builtin.*`, không cần collection từ Galaxy (chấm offline).
- Target không chạy systemd: unit systemd là tệp được deploy rồi kiểm bằng `systemd-analyze verify` ngay trong target; task
  quản service (`ansible.builtin.systemd_service`) gắn `when: ansible_facts.service_mgr == "systemd"` (trong lab
  `service_mgr` là `sshd`), handler vẫn được notify và ghi nhận bởi callback. README module ghi rõ giới hạn này.
- Molecule chỉ dạy khái niệm (driver docker cần socket Docker mà sandbox che). Test của bài đóng vai trò kịch bản
  converge + idempotence của molecule: chạy hai lần, lần hai `changed=0` đọc từ `AnsibleRun.changed`.

### Gating

- `ex.require_tool(name, min_version)`: thiếu công cụ, phiên bản cũ hơn mức tối thiểu (so sau khi đệm số 0: `1.27`
  bằng `1.27.0`), không đọc được phiên bản (thông báo riêng, chỉ lệnh để tự kiểm), hay (với `docker`) daemon tắt hoặc
  user không có quyền socket thì skip.
- `ex.require_image(image)`, `ex.require_service(name)`, `ex.require_registry()`, `ex.require_vault_devops()`, `ex.require_cluster(name="devops-lab")`,
  `ex.require_kind_images(*images)`, `ex.require_gateway()`, `ex.require_metrics()`, `ex.require_argocd()`: skip khi chưa có image, service compose, registry local, cluster kind,
  image trong worker của cluster, Gateway, metrics-server hay ArgoCD dùng chung (`require_cluster` có bốn thông báo riêng: Docker tắt, chưa có cluster, node đang dừng kèm lệnh
  `docker start`, `/readyz` không trả `ok` trong 5 giây).
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

### Kubernetes

- Cluster `devops-lab` cấu hình ở `setup/kind/devops-lab.yaml` (`KIND_NODE_IMAGE` = `kindest/node:v1.34.0` ghim digest, mặc
  định của kind 0.30.0; 1 control plane + 2 worker; API server và cổng ingress `18180`/`18543` chỉ trên `127.0.0.1`). Người
  học tạo, ghim CPU, tắt, bật, xoá theo `setup/DEVOPS-TOOLS.md`; test không bao giờ tạo hay xoá cluster.
- kind tối thiểu `KIND_MIN_VERSION` (0.30, bản đã kiểm 0.30.0); kubectl bản đã kiểm `KUBECTL_VERSION` (1.34.13), tối
  thiểu `KUBECTL_MIN_VERSION` (1.33): `require_cluster`, `require_gateway`, `require_metrics` skip khi kind hay kubectl cũ
  hơn. helm `HELM_VERSION` (3.22.1), tối thiểu `HELM_MIN_VERSION` (3.18). Phần `## 0. Cài đặt` của module 10, 11 dùng đúng các bản này.
- CNI là kindnet mặc định; kindnet của kind 0.30.0 thực thi NetworkPolicy (đã kiểm), bài NetworkPolicy không cần Calico.
- Node kind là container Docker privileged (mount `/lib/modules` chỉ đọc, volume cho `/var`, không có socket Docker): pod
  privileged thấy ổ đĩa của máy host. Vì vậy privileged, hostPath, hostNetwork/PID/IPC là chuyện an toàn của máy host; bài
  không bao giờ cần chúng, README hướng dẫn thực hành tay trong namespace có Pod Security `baseline`.
- PersistentVolume tĩnh dạng hostPath (bài CKA quen thuộc) bị từ chối; bài PV tĩnh dùng `lab.admin_local_pv(spec)` (testkit
  tạo PV `local` trong thư mục riêng của worker, không mount từ máy host: thư mục bind từ host cho pod root tạo được tệp
  setuid trên máy host), PV động dùng StorageClass `standard` có sẵn.
- Lab bị giết giữa bài thao tác node để lại cordon, taint: `require_cluster` lần sau giữ khoá node, hoàn tác rồi chạy tiếp.
  Khoá đang bị giữ thì `require_cluster` không chờ: một tiến trình khác gọi `require_cluster` cùng lúc vẫn chạy tiếp trong khi
  việc hoàn tác của tiến trình kia chưa xong, nên worker có thể còn cordon vài giây (bài cần lịch pod trên worker đó nên chờ
  pod `Ready` thay vì giả định worker đã sạch).
- Việc của admin trong CKA: cordon, drain, taint qua `lab.node_action(spec)` (chỉ worker); etcd snapshot là một lời gọi
  `kind_node_exec("devops-lab-control-plane", ...)` với argv hằng. **Đã kiểm 2026-11-02** (etcd 3.6.4, crictl 1.33.0): node không có
  etcdctl, image `registry.k8s.io/etcd:3.6.4-0` có `etcdctl` nhưng không có `etcdutl` hay shell; argv là `crictl exec -q --name ^etcd$
  --state running etcdctl --endpoints=https://127.0.0.1:2379 --cacert=/etc/kubernetes/pki/etcd/ca.crt
  --cert=/etc/kubernetes/pki/etcd/server.crt --key=/etc/kubernetes/pki/etcd/server.key snapshot save
  /var/lib/etcd/devops-ex-snapshot.db` (`crictl exec` nhận bộ lọc `--name` thay cho ID container; `/var/lib/etcd` là mount ghi được
  duy nhất chung giữa container etcd và node), rồi `kind_node_cp` về máy và `rm -f` trong `finally`. etcdctl 3.6 bỏ `snapshot
  status`, nên test kiểm tệp trên máy (magic bbolt `0xED0CDAED` ở offset 16, khoá `/registry/...` của object vừa tạo). Restore
  etcd và nâng cấp bằng kubeadm là lab tay trong README, chấm bằng rubric, testkit không làm.
- Image cho pod của bài (`KUBE_IMAGES`: `devops-track/olist-shop:1.0` build từ `setup/kind/olist-shop.Dockerfile`,
  `postgres:16.15-alpine`, `redis:7.4.12-alpine`, `nginx:1.30.6-alpine`) phải nạp sẵn vào hai worker; test gọi
  `ex.require_kind_images(...)` trước khi apply để skip kèm lệnh `kind load` thay vì để pod kéo image từ Internet hay kẹt
  `ImagePullBackOff`. Manifest của bài dùng đúng tag này (không `latest`). CustomResourceDefinition trong `allow` chỉ cho tạo CRD; custom resource của nó cần
  quyền thêm, thêm vào `KubeLab` (kèm test) khi bài cần.
- Ingress và Gateway API: admin cài một lần từ `setup/kind/gateway/` (CRD Gateway API standard v1.6.3, Traefik v3.7.17 ghim digest ở
  bước pull, IngressClass và GatewayClass `devops-traefik`, Gateway `devops-gateway/public` chỉ nhận HTTPRoute từ namespace có nhãn
  `devops-ex`); test không cài, `ex.require_gateway()` skip kèm lệnh. Token của lab ghi được `httproutes`, `ingresses` (không
  Gateway, GatewayClass, ReferenceGrant); policy `devops-ex-<id>-routes` của lab và `kube_manifest_problems` buộc Ingress dùng
  `ingressClassName: devops-traefik`, không `defaultBackend`, HTTPRoute chỉ gắn `devops-gateway/public`, mọi host là
  `lab.hostname` (`<namespace>.olist.test`) hay tên con. Test gọi Service `traefik.devops-gateway.svc.cluster.local` từ một pod
  kèm header `Host`, không dùng cổng của máy.
- metrics-server (HPA, `kubectl top`): admin cài một lần từ `setup/kind/metrics-server/` (`components.yaml` của release v0.9.1 chép
  nguyên cộng `kustomization.yaml` thêm `--kubelet-insecure-tls`, vì kubelet của kind dùng chứng chỉ tự ký không có IP SAN, và
  `imagePullPolicy: Never`; image kéo theo digest rồi nạp bằng `kind load image-archive`), `kubectl apply -k`; test không cài,
  `ex.require_metrics()` skip kèm lệnh. **Đã kiểm 2026-11-02**: số liệu đầu tiên sau khoảng 30 giây; HPA của module 11 scale lên trong
  khoảng 30 giây khi có tải, về 1 replica khoảng 70 giây sau khi hết tải (stabilization 30 giây); test chờ tới 300 giây.
- ArgoCD và git server (GitOps, SOPS): admin cài một lần từ `setup/kind/argocd/` (`core-install.yaml` của v3.5.6 chép nguyên,
  kustomization đặt `application.namespaces: devops-ex-*`, impersonation khi sync, applicationset-controller 0 replica, request
  nhỏ, `imagePullPolicy: Never`; sidecar CMP `sops-kustomize` chạy `sops --decrypt` cho `*.enc.yaml` rồi `kustomize build` không
  exec plugin, khoá age từ Secret `argocd/devops-sops-age` do admin tạo; git server `git daemon` chỉ đọc trong `devops-git`; ba
  image kéo theo digest rồi nạp bằng `kind load image-archive`); test không cài, `ex.require_argocd()` skip kèm lệnh. Chọn sidecar
  CMP thay ksops vì ksops cần bật exec plugin của kustomize cho repo-server (repo của bất kỳ lab nào chạy được chương trình cạnh
  khoá age); chọn `git daemon` thay `git http-backend` sau nginx vì dùng lại image ArgoCD, không cần web server, không ai push qua
  mạng. **Đã kiểm 2026-11-10**: cài xong khoảng 21 giây; RAM lúc nghỉ khoảng 145 MiB, sau hai bài GitOps song song khoảng 190 MiB;
  sync đầu tiên khoảng 2 giây, sync lại sau commit mới khoảng 2 giây; Application khác project, khác namespace, khác cluster hay
  trỏ repo của lab khác bị policy của lab chặn, và (khi admin tạo hộ để bỏ qua policy) bị AppProject từ chối; object ngoài
  namespace hay cluster-scoped trong repo không được sync; Secret SOPS được giải mã khi sync, giá trị không có trong status hay
  log của ArgoCD. Manifest đã render (kể cả Secret) nằm trong cache redis của `argocd`; repo của git server ở `emptyDir`, mất khi
  pod git khởi động lại. **Đã kiểm 2026-11-11** (sau review): NetworkPolicy egress chỉ cho repo-server ra DNS, git server, redis
  (kết nối ra ngoài bị chặn), remote base `https://` của kustomize (cả built-in lẫn CMP) lỗi trong khoảng 1 giây nhờ proxy chết
  thay vì chờ hết 30 giây render; `operation.sync.source` trỏ repo của lab khác và `status` giả bị policy của lab từ chối (ArgoCD
  tự nó không chặn `operation.sync.source`).

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
| Chạy workflow CI | `mlopskit.act_run(workdir)` | `act` với runner `mlops-act-runner:1` tự build, `--pull=false --bind`; `act_run` chỉ đảm bảo không kéo image, **workflow không được dùng `uses:` action từ xa** (chỉ bước `run:`, nếu không act cần mạng và GitHub); skip khi thiếu `act` hay act cũ hơn `ACT_MIN_VERSION` (0.2.80; tài liệu cài 0.2.94, cùng bản với track DevOps); act chạy với `HOME` tạm, không mang `GITHUB_*`, `GH_*`, `ACTIONS_*`, `DOCKER_*`, `DBUS_*`, `XDG_*` của máy (`DOCKER_HOST` lấy từ docker context), luôn nhận secret `GITHUB_TOKEN` giả và có `gh` giả đầu `PATH`, bị gọi thì fail (act 0.2.94 chạy `gh auth token` khi thiếu secret này, token thật của máy sẽ lọt vào job); trong `finally` chỉ dọn container của chính lần chạy (nhãn `mlops-ex-run=<uuid8>`), không đụng container khác; tuỳ chọn container thêm (vd. `--user uid:gid`) truyền qua tham số `container_options=`, **không** truyền `--container-options` trong `args` (act chỉ giữ giá trị cuối, `act_run` báo lỗi) |
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

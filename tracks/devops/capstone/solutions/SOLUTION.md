# Lời giải tham chiếu: capstone Olist Shop platform

Bản tham chiếu cho phần chấm được bằng test, cùng cây thư mục với `capstone/project/`:

```bash
SOLUTION=1 uv run pytest tracks/devops/capstone/project/tests -q -rs
```

Đây là **một** cách làm qua được hợp đồng trong đề, không phải cách duy nhất. Đọc sau khi đã tự làm; so phần quyết
định dưới đây với lựa chọn của bạn quan trọng hơn so từng dòng code.

## M01: `project/ops/`

### healthcheck.sh

- **Chỉ hỏi `/readyz`.** Liveness (`/healthz`) trả lời "process còn sống không"; readiness trả lời "có nhận traffic
  được không", gồm cả DB và Redis. Script vận hành và bước kiểm sau deploy cần câu thứ hai.
- **Exit 0/1/2 thay vì kiểu Nagios 0–3** như bài healthcheck của module 02. Người gọi ở đây là `bootstrap.sh`, CI và
  bước verify sau deploy: chúng chỉ cần "được/không được", còn chi tiết nằm trong dòng `FAIL ...`. Exit 2 dành riêng
  cho lỗi gọi sai, để người gọi phân biệt "service hỏng" với "mình gọi sai".
- **Một dòng, dạng cố định.** `FAIL readyz=503 failing=redis` grep được, đưa thẳng vào alert hay chat được. Giữ `OK`
  và `FAIL` ở đầu dòng để đọc lướt.
- **Không tin body khi mã HTTP mâu thuẫn.** 200 kèm `"db":"error"` hay 503 mà cả hai `ok` là dấu hiệu proxy hoặc app
  hỏng theo cách khác; báo `unexpected response` thay vì đoán.
- **`-w` nằm trong healthcheck, không nằm trong bootstrap.** Vòng chờ có hạn chót là logic dùng lại được (bootstrap, CI,
  deploy script). `SECONDS` của Bash đủ chính xác cho hạn chót tính bằng giây và không cần gọi `date`.
- **`curl -s` không kèm `-f`.** `-f` biến 503 thành exit 22 và bỏ body, trong khi ta cần đọc body 503 để biết thành
  phần nào lỗi. Bản lỗi trong `tests/fixtures/defective/ops/healthcheck.sh` cho thấy chiều ngược lại: thiếu cả `-f` lẫn
  kiểm mã HTTP thì 503 thành "OK".

### bootstrap.sh

- **Kiểm điều kiện trước, thay đổi sau.** Thiếu `docker compose` mà đã tạo `.env` thì lần sau người dùng nhận một tệp
  họ không biết từ đâu ra. Lỗi điều kiện là exit 2, lỗi lúc chạy là exit 1.
- **Không ghi đè `.env`, không `source` nó.** `.env` là cấu hình của người vận hành; ghi đè là xoá quyết định của họ.
  `source` biến một tệp cấu hình thành script chạy với quyền của bạn. Lọc đúng một khoá bằng `grep` là đủ.
- **Một lệnh `up --detach --build`, không `down` trước.** `compose up` vốn idempotent: chỉ tạo lại container có cấu hình
  đổi. `down -v` "cho sạch" là cách nhanh nhất mất dữ liệu Postgres. `--build` tốn vài giây khi cache còn, đổi lại image
  luôn khớp code.
- **Không dùng `up --wait` để thay healthcheck.** `--wait` chỉ chờ container ở trạng thái running/healthy theo Docker;
  service `api` trong compose không khai healthcheck, và "container healthy" khác "API trả lời `/readyz` 200 qua cổng host". Kiểm từ phía người dùng.
- **Tìm sample-app bằng cách đi lên thư mục cha.** Cùng một script chạy được ở `capstone/project/ops`,
  `capstone/solutions/project/ops` và trong repo portfolio tách riêng (sample-app nằm ở gốc). `OLIST_SHOP_APP_DIR` để ghi
  đè khi cần.
- **Không đụng `DEVOPS_CPUSET`.** Compose tự đọc biến này; script tự đặt giá trị (nhất là giá trị cứng như `12-35`) sẽ
  làm hỏng máy có ít core hơn.

### backup.sh

- **Thư mục theo timestamp thay vì tệp theo ngày.** Một bản là một thư mục (`olist.dump` + `SHA256SUMS`), sau này thêm
  `globals.sql` hay manifest mà không đổi quy ước tên. Timestamp UTC dạng `YYYYMMDDTHHMMSSZ` sắp xếp theo tên là sắp
  xếp theo thời gian.
- **Dựng trong `.inprogress-*` rồi `mv -T`.** Đổi tên trong cùng filesystem là nguyên tử: hoặc có bản đầy đủ, hoặc
  không có gì. Người khác (hay retention) không bao giờ thấy bản dở. Thư mục tạm còn sót sau `kill -9` được dọn ở lần
  chạy sau, khi đã có khoá, nên không xoá nhầm thư mục của một lần chạy đang làm.
- **`trap` cho `EXIT`, `INT`, `TERM`.** `trap 'exit 143' TERM` biến tín hiệu thành một lần thoát bình thường với mã
  rõ ràng, rồi `cleanup` chạy qua trap `EXIT`. Không dựa vào việc shell có tự chạy trap `EXIT` khi chết vì tín hiệu
  hay không: Bash có, nhưng không phải shell nào cũng vậy, và người sau có thể đổi shebang.
- **`flock -n` trên fd, exit 75 (`EX_TEMPFAIL`).** Khoá gắn với file descriptor nên tự nhả khi tiến trình chết, không cần
  dọn tệp PID. Exit 75 báo cho cron hay systemd "thử lại sau", khác với lỗi thật.
- **Idempotent theo timestamp và checksum.** Cùng `BACKUP_TIMESTAMP` mà bản cũ còn nguyên thì `skip`, không dump lại.
  Chỉ chống trùng khi bên gọi ghim `BACKUP_TIMESTAMP`: mặc định `date -u +%Y%m%dT%H%M%SZ` cho mỗi lần retry
  (systemd `Restart=on-failure`, CI chạy lại) một timestamp mới, tức một bản thứ hai. Job định kỳ muốn retry không tạo
  bản trùng thì ghim theo khung giờ của lịch, ví dụ job mỗi giờ:
  `BACKUP_TIMESTAMP="$(date -u +%Y%m%dT%H0000Z)" backup.sh`. Retry trong cùng giờ gặp bản đã có và `skip`.
- **Retention theo tên, chỉ trên thư mục đúng dạng.** Bản lỗi trong `tests/fixtures/defective/ops/backup.sh` dùng
  `ls | sort | tail | xargs rm -rf` và xoá luôn ghi chú hay bản backup tay. Đánh đổi của bản tham chiếu: retention đếm
  theo tên, không kiểm checksum của bản cũ, nên một bản mới bị hỏng vẫn chiếm một suất. Hệ thống thật nên kiểm khôi
  phục định kỳ (M09) thay vì tin checksum.
- **Mật khẩu chỉ qua `PGPASSWORD`/`.pgpass`.** Tham số dòng lệnh hiện trong `ps` của mọi user trên máy.

## M02: `project/nginx/`

### gen-cert.sh

- **EC P-256, 365 ngày, SAN đủ ba tên.** Key nhỏ, bắt tay nhanh, độ an toàn tương đương RSA 3072; 365 ngày nằm dưới giới hạn
  398 ngày; thiếu SAN thì curl, Python và trình duyệt đều từ chối dù CN đúng.
- **Idempotent theo "còn dùng được"**, không theo "tệp có tồn tại": cert còn trên 30 ngày và key khớp thì giữ nguyên,
  để chạy script trong bootstrap hay CI không đổi cert (và không làm hỏng chỗ đã tin cert cũ).
- **Ghi vào thư mục tạm rồi `mv`, `umask 077`.** Key không bao giờ tồn tại dù một khoảnh khắc với quyền đọc rộng. Hai
  lệnh `mv` không nguyên tử với nhau; chấp nhận được vì Nginx chỉ đọc cert lúc khởi động hoặc reload.

### olist-shop.conf

- **`map $http_x_request_id` để giữ id client gửi, sinh `$request_id` khi thiếu.** Giữ id cho phép client (app mobile,
  service khác) lần request của họ qua hệ thống. Rủi ro: client gửi id giả hay rất dài vào log. Ở edge công khai thật,
  cân nhắc chỉ tin id từ mạng nội bộ hoặc giới hạn độ dài; ghi lựa chọn đó trong README.
- **Không `add_header X-Request-ID`.** API đã trả lại header này; thêm ở Nginx sinh hai header cùng tên, client nhận
  giá trị nào tuỳ thư viện.
- **`log_format` riêng có `rid=`.** Access log mặc định không có request id, nên không nối được log Nginx với log API.
- **`limit_req` 5r/s, `burst=10 nodelay`, `limit_req_status 429`, chỉ ở `/jobs/`.** Mỗi job quét toàn bảng; một người
  bấm vài lần liền vẫn qua (burst), script spam bị chặn ngay (nodelay không xếp hàng làm chậm request). Khoá theo
  `$binary_remote_addr`: sau load balancer hay CDN phải dùng `real_ip` trước, nếu không mọi người dùng chung một IP.
- **`proxy_set_header` ở cấp `server`.** Các `location` không tự khai `proxy_set_header` thì kế thừa trọn bộ. Thêm một
  `proxy_set_header` trong một `location` là mất toàn bộ phần kế thừa, lỗi kinh điển (module 05 mục 2).
- **`return 301` ở server cổng 80, dùng `$host`.** 301 được trình duyệt cache lâu; 308 giữ method và body cho `POST`.
  Với API chủ yếu được gọi qua HTTPS ngay từ đầu, 301 đủ; nếu có client cũ `POST` qua HTTP thì 308 an toàn hơn.
- **Không HSTS** ở lab local: xem lý do trong đề M02.

## M03: `project/container/`

### Dockerfile

- **Ba stage: `deps`, `runtime`, rồi `worker` và `api` cùng `FROM runtime`.** Dependency cài một lần vào `/opt/venv` ở
  `deps`, `runtime` chép venv và code, hai target chỉ khác `CMD`, `HEALTHCHECK` và cổng. Hai image chung mọi layer trừ phần
  metadata: registry lưu một lần, node kéo một lần, trivy quét một bộ gói. Cái giá: worker mang theo FastAPI và uvicorn mà nó
  không dùng (vài MB). Tách requirements theo tiến trình chỉ đáng khi bộ dependency khác nhau thật sự.
- **`api` là stage cuối.** `docker build` không `--target` ra image API, đúng với người quen Dockerfile một stage.
- **`ARG APP_VERSION`, `GIT_COMMIT` đặt sau mọi `COPY`.** ARG chỉ làm đổi cache từ chỗ nó được dùng trở xuống; đặt ở đầu
  stage thì mỗi commit build lại cả layer venv. `ENV` và `LABEL` không tạo layer nên đổi version không đổi layer nào.
- **`USER 10001:10001` dạng số.** Tên user chỉ có nghĩa trong `/etc/passwd` của image; kubelet kiểm `runAsNonRoot` bằng số.
  UID ngoài dải user thường của máy host (1000) để tệp do container ghi lên volume không trùng chủ với người thật.
- **`Dockerfile.dockerignore` dạng allowlist (`**` rồi `!requirements.txt`, `!olist_shop/`).** Danh sách loại trừ luôn sót
  thứ ai đó thêm vào repo sau này (`.env`, dump, cert); allowlist thì thứ mới mặc định ở ngoài. Dù vậy Dockerfile vẫn chỉ
  `COPY` đúng thứ cần: ignore là lớp thứ hai, không phải lớp duy nhất. Bản lỗi trong
  `tests/fixtures/defective/container/Dockerfile` dùng `COPY . .` và mang `.env` có token vào image.
- **HEALTHCHECK bằng Python, `--start-interval=2s`.** Image slim không có curl, và thêm curl chỉ để healthcheck là thêm gói
  phải quét. `--start-interval` (Docker 25+) cho kiểm dày trong lúc khởi động mà không phải kiểm 2 giây một lần suốt đời
  container, nên `compose up --wait` xong nhanh. Worker kiểm cổng metrics `9101`: server metrics chạy ở thread riêng,
  nên cổng trả lời chỉ chứng minh tiến trình còn sống, không chứng minh vòng lặp chính còn lấy được job; M08 bổ sung
  bằng alert theo độ dài hàng đợi.
- **Giữ `python:3.12.16-slim-trixie` thay vì distroless hay alpine.** `psycopg[binary]` có wheel cho glibc; alpine (musl)
  cần wheel musllinux hay build từ nguồn. Distroless bỏ shell và pip, ít gói hơn nhiều, nhưng không còn `python -m venv`
  cùng phiên bản và khó debug lúc sự cố. Ghi lựa chọn và số đo vào README; module 06 Intermediate 02 cho cách đếm gói.

### compose.yaml

- **`image: ${OLIST_API_IMAGE:?...}`, không `build:`.** Compose production chạy đúng thứ pipeline đã build và quét. Có
  `build:` thì một lần `up --build` trên máy chủ là chạy code chưa qua CI; thiếu biến mà có giá trị mặc định thì chạy nhầm
  bản cũ không ai biết.
- **Anchor `x-app` cho phần chung của `api` và `worker`.** Hardening viết một lần; thêm tiến trình thứ ba không quên
  `read_only` hay `cap_drop`.
- **`read_only` cộng `tmpfs: /tmp`, `cap_drop: [ALL]`.** App không cần ghi gì ngoài `/tmp` và không cần capability nào
  (cổng 8000 > 1024). Postgres và Redis giữ mặc định: entrypoint của chúng cần `chown`, `setuid` lúc khởi động.
- **Postgres, Redis không mở cổng.** Ở production local, chỉ API nói chuyện với chúng qua mạng của project. Cần vào DB
  thì `docker compose exec postgres psql`, không mở cổng "tạm" rồi quên.
- **Mật khẩu qua `${POSTGRES_PASSWORD:?}`.** Compose không có secret thật khi không dùng Swarm (`secrets:` của compose
  thường chỉ là bind mount tệp). Biến bắt buộc ít nhất bảo đảm không có mật khẩu mặc định nào lọt lên production. M07 thay
  bằng SOPS.
- **`stop_grace_period: 20s` cho worker.** Worker chỉ kiểm cờ dừng sau mỗi `BLPOP` (5 giây) và có thể đang giữa một job
  tính lại doanh thu; 10 giây mặc định của Docker là sát, 20 giây cho job đang chạy kịp xong.
- **Redis `--appendonly yes` trên volume.** Hàng đợi job nằm trong Redis; restart mà mất hàng đợi là mất job đã nhận
  `202`. Nếu job tính lại được thì đây là lựa chọn, không phải bắt buộc.

### trivy.yaml

- Cùng chính sách với module 06: chặn `HIGH`/`CRITICAL` đã có bản vá, bỏ qua lỗ hổng chưa có bản vá, ngoại lệ qua tệp có
  hạn. Thêm scanner `secret`: quét bí mật trong image rẻ và không cần DB.
- **`.trivyignore.yaml` rỗng.** Lúc viết bản tham chiếu, cả hai image không có lỗ hổng chặn nào. Khi gate đỏ, thứ tự xử lý:
  nâng patch của image nền (rebuild, không đổi code), nâng gói Python, rồi mới đến ngoại lệ có `purls`, lý do và
  `expired_at` trong vòng 30 ngày.

## M04: `project/.github/workflows/ci.yml`, `project/ci/smoke-test.sh`

### ci.yml

- **`cancel-in-progress: ${{ github.event_name == 'pull_request' }}`.** Module 07 dạy `cancel-in-progress: true` cho
  workflow chỉ build. Khi cùng workflow có deploy, commit thứ hai lên `main` sẽ huỷ lần chạy đang deploy, để staging với
  compose dở dang. Deploy job có `concurrency` riêng (`deploy-staging`, không cancel): lần deploy sau chờ lần trước xong;
  GitHub chỉ giữ một lần đang chờ (lần mới nhất), lần chờ cũ hơn bị bỏ.
- **Build với `load: true`, quét, rồi mới `docker push`.** `build-push-action` với `push: true` đẩy ngay sau build, trước
  khi gate kịp nói gì; image bị chặn vẫn nằm trên registry và ai đó vẫn kéo được. Tách build và push làm gate thật sự chặn.
- **Push trong một bước `run:` đọc `RepoDigests`.** Output của job là `<repo>@sha256:...`, không phải tag; deploy nhận digest
  nên lần chạy lại hay người khác push đè tag (nếu registry cho) không đổi thứ staging chạy.
- **Pull request chạy build và quét nhưng không push.** Lỗi Dockerfile và lỗ hổng lộ ra trước khi merge, registry chỉ có image
  của code đã review.
- **`environment: staging`.** Trên GitHub, environment gắn secret riêng (`STAGING_POSTGRES_PASSWORD`), quy tắc bảo vệ (người
  duyệt, nhánh được deploy) và lịch sử deploy. Production là một environment khác, có reviewer bắt buộc.
- **Smoke test là một bước của pipeline, không phải việc sau.** `compose up --wait` chỉ nói container healthy theo
  HEALTHCHECK; smoke test hỏi từ phía người dùng rằng đúng version vừa build đang trả lời và sẵn sàng. Pipeline xanh nghĩa
  là staging đã chạy bản này.
- **Giới hạn cố ý.** Không có bước rollback tự động: smoke test đỏ thì job đỏ và staging giữ bản lỗi cho người xem. Rollback
  là chạy lại job deploy với digest của lần xanh trước (GitHub: "Re-run" lần chạy cũ), ghi trong README.

### smoke-test.sh

- **Một vòng lặp có hạn chót cho cả hai điều kiện.** Container vừa `up` thì `/healthz` thường trả lời trước `/readyz`;
  kiểm version trước để báo đúng lý do khi staging còn chạy bản cũ (deploy không đổi image) thay vì báo "chưa sẵn sàng".
- **`--max-time 3` cho mỗi lần gọi.** Không có nó, một cổng nhận kết nối mà không trả lời giữ script tới hết timeout mặc định
  của curl, vượt xa `SMOKE_TIMEOUT`.
- **Dòng `FAIL` nêu lý do cuối cùng thấy được** (`version=... expected=...`, `readyz=503`): người đọc log CI biết ngay deploy
  sai bản hay hạ tầng chưa lên.

## Rubric cho phần tự đánh giá

| Mục | Đạt | Chưa đạt |
| --- | --- | --- |
| Vòng thật M01 | bootstrap in `ready`, healthcheck đổi sang `failing=redis` khi dừng Redis và trở lại `OK`, `pg_restore --list` đọc được bản backup | Chỉ chạy test với binary giả |
| README "Vận hành" | Ba lệnh, exit code, lệnh khôi phục có cảnh báo ghi đè | Chỉ liệt kê tên script |
| Vòng thật M02 | curl qua `--cacert` (không `-k`), thấy 429 khi spam `/jobs/`, tìm được cùng một request id trong log Nginx và log API | Tắt kiểm cert hoặc không lần được request id |
| README "Edge" | Có lý do cho rate/burst, 429, chính sách request id, lựa chọn Nginx | Chỉ chép cấu hình |
| Vòng thật M03 | Build hai target, chạy compose production, gate trivy chạy bằng `trivy.yaml`, có bảng số đo image cũ và mới | Chỉ chạy test |
| README "Container" | Lý do chọn image nền, ý nghĩa từng khoá hardening, quy trình khi gate đỏ đã làm thật một lần | Liệt kê khoá không giải thích |
| Vòng thật M04 | Chạy workflow bằng act, đọc log từng job, rollback staging bằng digest cũ và đo thời gian | Chỉ chạy test |
| README "Pipeline" | Sơ đồ job, lý do quét trước push và deploy theo digest, quy trình rollback có số đo, kế hoạch promote | Chỉ mô tả các bước YAML |

# M01: Script vận hành: bootstrap, healthcheck, backup

## Mục tiêu

Olist Shop đang chạy được bằng `docker compose up` trên máy dev, nhưng chưa ai vận hành được nó: không có lệnh
dựng chuẩn, không có cách hỏi "service có khoẻ không" mà máy đọc được, và không có backup. Milestone này cho bạn ba
script nhỏ trong `capstone/project/ops/`, đủ tốt để một người khác trong team (hoặc cron, systemd, CI) gọi mà không cần
hỏi bạn:

- `bootstrap.sh` dựng stack Olist Shop và chỉ báo xong khi API thật sự sẵn sàng.
- `healthcheck.sh` hỏi `/readyz` và trả exit code cùng một dòng kết quả nói rõ thành phần nào hỏng.
- `backup.sh` sao lưu Postgres vào thư mục theo timestamp, có checksum, giữ N bản mới nhất, chạy lại an toàn.

Đây là bài tích hợp sau [module 02 Scripting](../../modules/02-scripting/README.md). Bạn dùng lại những gì module đó
dạy (strict mode, quoting, `getopts`, exit code là hợp đồng, `trap`, ghi tạm rồi `mv`, `flock`, test script bằng
binary giả) nhưng tự ghép chúng thành công cụ cho một service cụ thể. Các milestone sau dựa vào kết quả này:
M02 đặt Nginx trước stack mà `bootstrap.sh` dựng, M03 trở đi dùng `healthcheck.sh` làm bước kiểm sau deploy, và game
day M09 cần bản backup khôi phục được.

## Việc cần làm

Mọi script viết bằng Bash, bắt đầu bằng `#!/usr/bin/env bash` và `set -euo pipefail`, qua `shellcheck -S style` không
cảnh báo. Test chạy script **trong sandbox bubblewrap**: chỉ thư mục tạm của test ghi được, môi trường dựng lại từ đầu
(chỉ có `PATH`, `HOME` và các biến test đặt), không thấy socket Docker. Vì vậy script chỉ được lấy cấu hình từ tham số
và biến môi trường mô tả dưới đây. `pg_dump` và `docker` trong test là binary giả đứng đầu `PATH`, ghi lại tham số và
biến môi trường mà script truyền cho chúng; API là một server HTTP giả trên `127.0.0.1`.

Mọi quy tắc dưới đây đều được chấm. Không có quy tắc chấm nào nằm ngoài tệp này.

### 1. `ops/healthcheck.sh`

```text
healthcheck.sh [-u BASE_URL] [-t TIMEOUT] [-w WAIT]
```

| Tham số / biến | Ý nghĩa | Mặc định |
| --- | --- | --- |
| `-u BASE_URL` | Gốc URL của API, bỏ `/` ở cuối nếu có | `$OLIST_SHOP_API_URL`, nếu trống thì `http://127.0.0.1:${OLIST_SHOP_API_PORT:-28000}` |
| `-t TIMEOUT` | Giới hạn thời gian mỗi lần gọi, số nguyên ≥ 1 (giây) | `3` |
| `-w WAIT` | Tổng thời gian chờ tối đa, số nguyên ≥ 0 (giây); `0` là hỏi một lần | `0` |

Thứ tự ưu tiên URL: `-u` > `OLIST_SHOP_API_URL` > `OLIST_SHOP_API_PORT` > `28000`.

Script gọi `GET <BASE_URL>/readyz` (được gọi thêm `/healthz`, không gọi đường dẫn nào khác) và in **đúng một dòng** ra
stdout:

| Tình huống | stdout | Exit |
| --- | --- | --- |
| HTTP 200, body JSON `{"db":"ok","redis":"ok"}` | `OK db=ok redis=ok` | 0 |
| HTTP 503, body JSON có `db` và `redis` đều thuộc `ok`/`error`, ít nhất một `error` | `FAIL readyz=503 failing=<danh sách>`, danh sách là các thành phần `error` theo thứ tự `db`, `redis`, nối bằng dấu phẩy: `failing=redis`, `failing=db`, `failing=db,redis` | 1 |
| Không kết nối được hoặc quá `-t` giây | dòng **bắt đầu bằng** `FAIL api unreachable` (được thêm chi tiết phía sau, ví dụ mã lỗi curl) | 1 |
| Mọi trường hợp khác: mã HTTP khác 200/503, body không phải JSON object, thiếu khoá, giá trị ngoài `ok`/`error`, 200 mà có `error`, 503 mà cả hai `ok` | `FAIL readyz=<mã HTTP> unexpected response` | 1 |
| Sai tham số: cờ lạ, thiếu giá trị, `-t` không phải số ≥ 1, `-w` không phải số ≥ 0, thừa tham số | stdout rỗng, stderr bắt đầu bằng `Usage:` | 2 |

Với `-w WAIT > 0`: nếu chưa `OK` thì chờ khoảng 1 giây rồi hỏi lại, tới khi `OK` hoặc hết `WAIT` giây; stdout chỉ có
dòng kết quả của lần hỏi cuối. Không có `-w` thì chỉ hỏi `/readyz` đúng một lần. Tổng thời gian chạy không vượt quá
khoảng `WAIT + TIMEOUT` giây (test cho phép dư vài giây).

Test cần `curl` ≥ 7.68 và `jq` ≥ 1.6 trên máy (skip nếu thiếu), nên bạn dùng được cả hai.

### 2. `ops/bootstrap.sh`

```text
bootstrap.sh [-t WAIT]
```

`WAIT` là số giây tối đa chờ API sẵn sàng, số nguyên ≥ 1, mặc định `120`. Sai tham số: exit 2, stderr bắt đầu bằng
`Usage:`, không gọi `docker compose up`.

| Biến | Ý nghĩa | Mặc định |
| --- | --- | --- |
| `OLIST_SHOP_APP_DIR` | Thư mục sample-app (chứa `compose.yaml`) | Tìm từ thư mục chứa script đi lên các thư mục cha; ở mỗi cấp xét `<cấp>/sample-app/compose.yaml` rồi `<cấp>/tracks/devops/sample-app/compose.yaml`, lấy chỗ đầu tiên có |
| `OLIST_SHOP_PROJECT` | Tên project compose | `olist-shop` |
| `OLIST_SHOP_API_URL` | Gốc URL để chờ readiness | `http://127.0.0.1:<cổng>` |
| `OLIST_SHOP_API_PORT` | Cổng API trên host | giá trị `OLIST_SHOP_API_PORT=` trong `<app>/.env`, nếu không có thì `28000` |

Các bước, theo đúng thứ tự:

1. **Kiểm điều kiện trước khi thay đổi bất cứ thứ gì.** `compose.yaml` phải tồn tại và `docker compose version` phải
   chạy được. Thiếu một trong hai: exit 2, stderr nói rõ thiếu gì (với compose, thông báo phải có chữ `compose`),
   không tạo `.env`, không gọi `up`.
2. **`.env`.** Chưa có `<app>/.env` thì chép nguyên `<app>/.env.example` sang. Đã có thì **không** đụng tới (người vận
   hành có thể đã đổi cổng hay `LOG_LEVEL`).
3. **Tính URL chờ.** Đọc cổng theo bảng trên. Đọc `.env` bằng cách lọc dòng `OLIST_SHOP_API_PORT=`, không `source` tệp
   (tệp `.env` không phải script và có thể chứa thứ bạn không muốn chạy).
4. **Dựng stack.** Gọi **đúng một** lệnh `docker compose --project-name <project> --file <app>/compose.yaml up --detach`
   (được thêm cờ khác như `--build`; dạng ngắn `-p`, `-f`, `-d` cũng được; `--file` tương đối thì tính từ thư mục hiện
   tại lúc gọi). `up` lỗi: exit 1, giữ nguyên thông báo lỗi của docker trên stderr, không chờ readiness.
5. **Chờ readiness** tối đa `WAIT` giây (gọi `healthcheck.sh -w` nằm cùng thư mục là cách gọn nhất; test chép cả thư
   mục `ops/` nên bạn gọi được). Sẵn sàng: dòng **cuối** của stdout là `ready <BASE_URL>`, ví dụ
   `ready http://127.0.0.1:28000`, exit 0. Hết giờ: exit 1, stdout hoặc stderr có tên thành phần đang lỗi (ví dụ dòng
   `FAIL readyz=503 failing=redis` của healthcheck), không in dòng `ready`.

Thêm hai ràng buộc:

- **Không lệnh phá huỷ.** bootstrap không bao giờ gọi `docker` với tham số `down`, `rm`, `kill`, `stop`, `prune`,
  `volume` hay `system`. Chạy lại bootstrap phải an toàn với dữ liệu đang có.
- **Không tự ghim CPU.** Không đặt hay sửa `DEVOPS_CPUSET`: compose của sample-app tự đọc biến đó từ môi trường bạn đã
  `export` (rỗng hoặc chưa đặt nghĩa là không ghim).

Chạy bootstrap hai lần liên tiếp phải cùng thành công, mỗi lần gọi `up` một lần và giữ nguyên `.env`.

### 3. `ops/backup.sh`

```text
backup.sh [-k KEEP] [-d DEST]
```

| Tham số / biến | Ý nghĩa | Mặc định |
| --- | --- | --- |
| `-k KEEP` | Số bản giữ lại, số nguyên ≥ 1 | `$OLIST_BACKUP_KEEP`, nếu trống thì `5` |
| `-d DEST` | Thư mục chứa các bản backup, bỏ `/` ở cuối; rỗng là lỗi tham số | `$OLIST_BACKUP_DIR`, nếu trống thì `backups` (tương đối với thư mục hiện tại) |
| `BACKUP_TIMESTAMP` | Tên bản backup, dạng `YYYYMMDDTHHMMSSZ` | giờ UTC hiện tại, `date -u +%Y%m%dT%H%M%SZ` |
| `PGHOST`, `PGPORT`, `PGUSER`, `PGDATABASE` | Kết nối Postgres; biến đã có trong môi trường thắng | `127.0.0.1`, `$OLIST_SHOP_PG_PORT` hoặc `25432`, `olist`, `olist` |
| `PGPASSWORD` | Mật khẩu, chỉ truyền qua môi trường (hoặc `~/.pgpass`) | không đặt mặc định |

Quy tắc:

- **Sai tham số** (cờ lạ, thiếu giá trị, `-k` không phải số ≥ 1, `-d ""`, thừa tham số): exit 2, stderr bắt đầu bằng
  `Usage:`, không gọi `pg_dump`. `BACKUP_TIMESTAMP` sai dạng: exit 2, có thông báo trên stderr, không gọi `pg_dump`.
- **Dump.** Gọi `pg_dump` định dạng custom (`--format=custom` hoặc `-Fc`), ghi bằng `--file`/`-f` hay chuyển hướng
  stdout đều được. Mật khẩu không bao giờ nằm trong tham số dòng lệnh hay trong output của script.
- **Kết quả.** `DEST/<TS>/` chứa đúng hai tệp: `olist.dump` (không rỗng) và `SHA256SUMS` có đúng một dòng
  `<sha256 của olist.dump>  olist.dump` (định dạng của `sha256sum`, kiểm lại được bằng `sha256sum -c SHA256SUMS` trong
  thư mục đó). Quyền: thư mục `700`, tệp `600`. stdout đúng một dòng `created DEST/<TS>`, với `DEST` đúng như bạn nhận
  (đã bỏ `/` cuối): mặc định là `created backups/<TS>`.
- **Nguyên tử.** Dựng bản backup trong một thư mục tạm `DEST/.inprogress-<gì cũng được>` rồi đổi tên thành `DEST/<TS>`.
  Khi bắt đầu (sau khi có khoá), xoá mọi `DEST/.inprogress-*` còn sót từ lần chạy bị ngắt. Sau mỗi lần chạy, trong
  `DEST` không còn thư mục nào tên bắt đầu bằng `.` (tệp khoá thì được).
- **Lỗi không để lại gì.** `pg_dump` thoát khác 0 hoặc tạo tệp rỗng: exit 1, stdout rỗng, stderr nói lý do, không tạo
  và không xoá mục nào (không áp retention). Bị `SIGTERM` giữa chừng: exit khác 0, stdout rỗng, không còn `DEST/<TS>`
  dở dang hay thư mục tạm; chạy lại sau đó tạo bản bình thường.
- **Idempotent.** `DEST/<TS>` đã có và checksum khớp: stdout `skip DEST/<TS>`, exit 0, không gọi `pg_dump`, không đụng
  tệp. Đã có nhưng hỏng (dump bị sửa hoặc mất `SHA256SUMS`): tạo lại, stdout `created DEST/<TS>`.
- **Retention.** Sau mỗi lần thành công (`created` hoặc `skip`), trong các thư mục con tên đúng dạng
  `YYYYMMDDTHHMMSSZ`, giữ `KEEP` thư mục có tên lớn nhất và xoá hẳn phần còn lại. Không đụng mọi thứ khác trong `DEST`
  (tệp ghi chú, thư mục backup tay như `manual-before-upgrade/`, tệp khoá).
- **Khoá.** Dùng `flock` trên một tệp trong `DEST` (ví dụ `DEST/.lock`). Đang có lần chạy khác giữ khoá: thoát ngay với
  exit 75 và thông báo trên stderr, không chờ, không tạo gì. Tiến trình giữ khoá chết thì khoá phải tự nhả.

### 4. Chạy thử với stack thật

Test không cần Docker, nhưng bạn nên chạy một vòng thật để thấy ba script ghép với nhau. Từ gốc repo, với
`DEVOPS_CPUSET` đã đặt theo [Ghim CPU](../../README.md#ghim-cpu-trên-máy-dùng-chung) (để trống nếu không ghim):

```bash
bash tracks/devops/capstone/project/ops/bootstrap.sh -t 180
```

Nạp dữ liệu theo [README sample-app](../../sample-app/README.md#chạy-bằng-docker-compose), rồi kiểm, sao lưu và đọc thử
bản sao lưu (`pg_restore --list` chỉ đọc mục lục, không ghi vào database nào):

```bash
ops=tracks/devops/capstone/project/ops
backups=tracks/devops/capstone/project/backups
bash "$ops/healthcheck.sh" && PGPASSWORD=olist bash "$ops/backup.sh" -d "$backups"
latest="$(find "$backups" -mindepth 1 -maxdepth 1 -type d -regex '.*/[0-9]*T[0-9]*Z' | sort | tail -n 1)" && [ -n "$latest" ] && pg_restore --list "$latest/olist.dump" | head
```

Thấy healthcheck báo lỗi thật bằng cách dừng Redis **của project Olist Shop** rồi bật lại:

```bash
docker compose -p olist-shop -f tracks/devops/sample-app/compose.yaml stop redis && bash tracks/devops/capstone/project/ops/healthcheck.sh; docker compose -p olist-shop -f tracks/devops/sample-app/compose.yaml start redis
```

Máy chưa có `pg_dump` 16 thì cài `postgresql-client-16`, hoặc tạm bỏ qua bước backup thật: test của milestone dùng
`pg_dump` giả. Xong thì `docker compose -p olist-shop -f tracks/devops/sample-app/compose.yaml down` (thêm `-v` nếu muốn
xoá luôn dữ liệu).

### 5. Chạy test

```bash
uv run pytest tracks/devops/capstone/project/tests -q -rs -k m01
```

Trên máy dùng chung, thêm `nice -n 15 ${DEVOPS_CPUSET:+taskset -c "$DEVOPS_CPUSET"}` trước `uv run`. Test cần
`bwrap` (bubblewrap) để chạy sandbox, xem [module 02, mục Cài đặt](../../modules/02-scripting/README.md#0-cài-đặt).

Có một test tích hợp tuỳ chọn chạy `healthcheck.sh` và `backup.sh` với Postgres, Redis và API thật. Test tự dựng
container riêng (tên `devops-ex-...`, dọn khi xong), không đụng project compose `olist-shop` của bạn, và chỉ chạy khi
bạn bật:

```bash
cd tracks/devops/sample-app && docker compose build api && cd ../../.. && DEVOPS_CAPSTONE_INTEGRATION=1 uv run pytest tracks/devops/capstone/project/tests -q -rs -k integration
```

Test đó cần image `olist-shop:dev`, `postgres:16`, `redis:7` và `pg_dump`, `pg_restore` ≥ 16 trên máy; thiếu thứ gì thì
skip kèm lý do. `bootstrap.sh` không có test tích hợp vì sandbox cố ý che socket Docker.

## Kết quả nộp

- `capstone/project/ops/healthcheck.sh`
- `capstone/project/ops/bootstrap.sh`
- `capstone/project/ops/backup.sh`
- Một mục ngắn "Vận hành" trong `capstone/project/README.md` (hoặc README portfolio của bạn): ba lệnh, exit code của
  từng lệnh, và cách khôi phục từ một bản backup (`pg_restore --clean --if-exists -d ...`), kèm cảnh báo lệnh đó ghi
  đè dữ liệu.

## Tiêu chí đạt

- [ ] `uv run pytest tracks/devops/capstone/project/tests -q -rs -k m01` pass, không skip (trừ test tích hợp tuỳ chọn).
- [ ] Ba script qua `shellcheck -S style` không cảnh báo.
- [ ] healthcheck: đúng một dòng stdout và exit code theo bảng ở mục 1, có giới hạn thời gian mỗi lần gọi, `-w` chờ
      rồi chỉ in kết quả cuối.
- [ ] bootstrap: kiểm điều kiện trước khi thay đổi gì, không ghi đè `.env`, một lệnh `up` mỗi lần chạy, chờ tới khi
      sẵn sàng rồi in `ready <URL>`, không lệnh phá huỷ, không tự đặt `DEVOPS_CPUSET`.
- [ ] backup: thư mục timestamp có checksum và quyền `700`/`600`, nguyên tử, lỗi hay bị ngắt không để lại gì, chạy lại
      cùng timestamp thì `skip`, retention chỉ xoá thư mục backup cũ, khoá với exit 75.
- [ ] (Tự đánh giá) Đã chạy vòng thật ở mục 4: bootstrap tới `ready`, healthcheck báo `failing=redis` khi dừng Redis,
      `pg_restore --list` đọc được bản backup.
- [ ] (Tự đánh giá) README có mục "Vận hành" như phần Kết quả nộp.

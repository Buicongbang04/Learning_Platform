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
  Đây là thứ giúp một job bị retry (systemd `Restart=on-failure`, CI chạy lại) không tạo bản trùng.
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

## Rubric cho phần tự đánh giá

| Mục | Đạt | Chưa đạt |
| --- | --- | --- |
| Vòng thật M01 | bootstrap in `ready`, healthcheck đổi sang `failing=redis` khi dừng Redis và trở lại `OK`, `pg_restore --list` đọc được bản backup | Chỉ chạy test với binary giả |
| README "Vận hành" | Ba lệnh, exit code, lệnh khôi phục có cảnh báo ghi đè | Chỉ liệt kê tên script |
| Vòng thật M02 | curl qua `--cacert` (không `-k`), thấy 429 khi spam `/jobs/`, tìm được cùng một request id trong log Nginx và log API | Tắt kiểm cert hoặc không lần được request id |
| README "Edge" | Có lý do cho rate/burst, 429, chính sách request id, lựa chọn Nginx | Chỉ chép cấu hình |

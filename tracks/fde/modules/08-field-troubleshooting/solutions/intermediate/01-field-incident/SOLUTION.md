# Lời giải: sự cố ở bệnh viện

## Bố cục lời giải và cách chấm

- `scenarios.py`: các sự cố (nguyên nhân thật, cách test dựng lại, ticket, tập `cause` chấp nhận, mẫu bằng chứng trực
  tiếp). Test của bài nạp tệp này để dựng cảnh, nên tên sự cố và nguyên nhân không nằm trong `exercises/`.
- `incidents/<sự cố>.yaml`: báo cáo tham chiếu cho **từng** sự cố. Với `SOLUTION=1`, test chạy mọi sự cố, mỗi sự cố với
  một seed ngẫu nhiên và báo cáo tham chiếu của đúng sự cố đó (không cần bước 1 tương tác). Người học thì đi hai bước
  với `FDE_08_INCIDENT_SEED`, sự cố do seed quyết định.
- `incident.yaml`: bản sao của `incidents/disk-night-export.yaml` (validator cần lời giải trùng tên tệp starter).

## Sự cố `disk-night-export` (hồ sơ `hospital`: đĩa 8 GB)

Job export đêm của HIS ghi bản dump vào `/var/backups/his/` trên **cùng** ổ `/` 8 GB với Docker và volume Postgres. Ổ
đầy: Postgres không mở rộng được tệp dữ liệu khi worker ghi chunk của tài liệu mới (`ERROR: could not extend file …: No
space left on device`), worker xếp lỗi database này vào "sự cố hạ tầng", để nguyên tệp và thử lại mãi. Đọc không cần ghi
nên hỏi tài liệu cũ vẫn được, `/healthz` vẫn 200: đúng ticket.

Đường chẩn đoán ngắn nhất: ticket nói "đọc được, ghi mới không được" → mở `system/df.txt` trước log (`100% /`) → log
`db` và `worker` xác nhận cơ chế (`No space left on device`, `DiskFull`, `để nguyên tệp và thử lại sau`) → **một** lệnh
nhờ khách để biết ai chiếm chỗ: `sudo du -xh -d 2 /var` (thấy `/var/backups/his` vài GB, không phải `/var/lib/docker`).
Tập chấp nhận: `disk-full`.

Cách sửa nằm ở IT bệnh viện (chuyển/xoá bản export theo chính sách lưu trữ của họ, đưa job sang ổ khác); không xoá gì
trong `/var/lib/docker`, không `docker system prune` trên máy production. Worker tự nạp lại khi có chỗ.

## Sự cố `proxy-docker-config` (hồ sơ `hospital`: proxy công ty)

IT bệnh viện muốn `docker pull` đi qua proxy nên khai `proxies` trong `~/.docker/config.json` của user vận hành, rồi
`docker compose up -d --force-recreate` trong đợt bảo trì. Docker CLI và compose bơm `HTTP_PROXY`/`HTTPS_PROXY`/
`NO_PROXY` vào **mọi container tạo mới**; `noProxy` chỉ có `localhost,127.0.0.1`. httpx trong `api` tôn trọng các biến
đó nên lời gọi `http://llm:8080`, `http://embed:8080` đi vòng qua proxy, proxy không phân giải được `llm`/`embed` và trả
`502`. Healthcheck của `llm`/`embed` gọi `127.0.0.1` ngay trong container nên vẫn `healthy`: đúng ticket. Worker không
lên vì `api` không bao giờ healthy (compose báo `dependency failed to start`).

Đường chẩn đoán: `quillo/healthz.txt` (`"llm":false`, `"embed":false`) mâu thuẫn với `compose-ps.txt` (llm, embed
healthy) → `api.log` có `502 Bad Gateway' for url 'http://embed:8080…`: một dịch vụ llama.cpp không bao giờ trả 502,
vậy có thứ đứng giữa → ticket nói máy ở sau proxy công ty (hồ sơ bệnh viện) → bundle không thu biến môi trường của
container (đúng: không được thu), nên nhờ khách **một** lệnh: `docker inspect --format '{{json .Config.Env}}'
quillo-api-1` (output đã che secret) thấy `HTTP_PROXY=http://10.0.2.100:3128`. Thay thế được: `cat
~/.docker/config.json`. Tập chấp nhận: `proxy-misrouting` (đúng nhất theo định nghĩa) hoặc `config-error` (cấu hình
Docker client sai), kèm bằng chứng trực tiếp về biến proxy.

Cách sửa: proxy cho `dockerd` (systemd drop-in) nếu mục đích là pull image; nếu thật sự cần proxy trong container thì
`noProxy` phải có tên dịch vụ nội bộ (`llm,embed,db,api`) và dải mạng compose; tạo lại container rồi kiểm `/healthz`.

## Vì sao test chấm như vậy

- **Dựng lại cảnh, đừng tin bundle cũ:** với seed, test dựng lại đúng sự cố trên VM mới, lấy bundle mới bằng chính
  `quillo-support.sh` và chạy lại lệnh khách. Đoạn trích phải là phần ổn định của dòng; đó cũng là cách viết ticket tốt.
- **Bằng chứng trực tiếp:** `direct` trong `scenarios.py` là cặp (nguồn, mẫu): đĩa đầy chấp nhận `100% /` từ
  `system/df.txt`, `No space left on device`/`DiskFull`/`could not extend file` từ log `db`/`worker`/`api`, và những dấu
  vết đó (thêm `/var/backups/his`) từ output lệnh khách; proxy chỉ chấp nhận biến proxy **của container hay Docker
  client** (`HTTP_PROXY=http…`, `"httpProxy"`, viết đúng hoa thường) từ output lệnh khách. Biến proxy hệ thống
  (`/etc/environment`, chữ thường) có ở bệnh viện dù có sự cố hay không, nên không tính; bundle cũng không còn thu tệp đó.
  Đoạn trích từ output một lệnh mà chính câu lệnh chứa đoạn trích (`ls '/No space left on device'`) không tính.
  Một báo cáo chỉ có `502` và `/healthz 503` đúng triệu chứng mà chưa chỉ ra nguyên nhân.
- **Lệnh đã thật sự hỏi:** ở chế độ người học, test đọc `.fde-lab/08-field-incident/ask-log.jsonl` (mỗi dòng có seed,
  chỉ ghi nối): số lệnh khách đã gõ cho seed đó ≤ 4 và `customer_commands` ⊆ các lệnh đó. `ask_customer` từ chối lệnh
  thứ 5. Với `SOLUTION=1` (ruling R2) không có nhật ký nên bước này bỏ qua, test chạy không cần người.
- **Khách che secret** bằng cách thay đúng hai giá trị bí mật của bản cài (token quản trị, mật khẩu database) trước khi
  dán; công cụ không dùng bộ lọc theo dạng chung (đó là việc của bài basic 01).
- **Giới hạn lệnh và danh sách lệnh** mô phỏng sự kiên nhẫn và chính sách của IT bệnh viện: chỉ đọc, một lệnh mỗi lần,
  không mở tệp secret, output được che trước khi dán.

Biến thể sai đã thử (mỗi biến thể 2 lần, đều trượt): báo cáo của sự cố này nộp cho sự cố kia; báo cáo đúng `cause` nhưng
chỉ có bằng chứng triệu chứng; đoạn trích chứa giờ của lần điều tra; bằng chứng "trực tiếp" do lệnh khách lặp lại đối số
(`ls /HTTP_PROXY=…`, `ls '/No space left on device'`); biến proxy hệ thống (`cat /etc/environment`) thay cho biến của
container. Ở chế độ người học: nhật ký có 5 lệnh cho seed, hoặc `customer_commands` có lệnh chưa hỏi, đều trượt.

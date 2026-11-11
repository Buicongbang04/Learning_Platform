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
vậy có thứ đứng giữa → `system/environment.txt` cho biết máy có proxy công ty → bundle không thu biến môi trường của
container (đúng: không được thu), nên nhờ khách **một** lệnh: `docker inspect --format '{{json .Config.Env}}'
quillo-api-1` (output đã che secret) thấy `HTTP_PROXY=http://10.0.2.100:3128`. Thay thế được: `cat
~/.docker/config.json`. Tập chấp nhận: `proxy-misrouting` (đúng nhất theo định nghĩa) hoặc `config-error` (cấu hình
Docker client sai), kèm bằng chứng trực tiếp về biến proxy.

Cách sửa: proxy cho `dockerd` (systemd drop-in) nếu mục đích là pull image; nếu thật sự cần proxy trong container thì
`noProxy` phải có tên dịch vụ nội bộ (`llm,embed,db,api`) và dải mạng compose; tạo lại container rồi kiểm `/healthz`.

## Vì sao test chấm như vậy

- **Dựng lại cảnh, đừng tin bundle cũ:** với seed, test dựng lại đúng sự cố trên VM mới, lấy bundle mới bằng chính
  `quillo-support.sh` và chạy lại lệnh khách. Đoạn trích phải là phần ổn định của dòng; đó cũng là cách viết ticket tốt.
- **Bằng chứng trực tiếp:** mẫu `direct` trong `scenarios.py` (vd. `No space left on device`, `100% /`,
  `/var/backups/his`; `HTTP_PROXY`, `10.0.2.100:3128`). Một báo cáo chỉ có `502` và `/healthz 503` đúng triệu chứng mà
  chưa chỉ ra nguyên nhân.
- **Giới hạn lệnh và danh sách lệnh** mô phỏng sự kiên nhẫn và chính sách của IT bệnh viện: chỉ đọc, một lệnh mỗi lần,
  không mở tệp secret, output được che trước khi dán.

Biến thể sai đã thử (mỗi biến thể 2 lần, đều trượt): báo cáo của sự cố này nộp cho sự cố kia; báo cáo đúng `cause` nhưng
chỉ có bằng chứng triệu chứng; đoạn trích chứa giờ của lần điều tra.

# Lời giải: inventory động từ CMDB

Lời giải là `inventory/cmdb.py`, `inventory/constructed.yml` và `rollout.yml`.

## Các quyết định

- **Fail to, không fail im.** Thiếu `OLIST_CMDB_FILE` hay JSON hỏng thì thoát mã 2 kèm thông báo. Inventory rỗng nguy hiểm hơn lỗi:
  playbook "thành công" trên 0 máy, pipeline xanh mà không deploy gì.
- **Một lần gọi `--list` có `_meta`.** Có `_meta.hostvars` thì Ansible không gọi `--host` cho từng máy; `--host` trả `{}` cho đúng
  giao thức.
- **Chuẩn hoá ở một chỗ.** `slug()` cho tên nhóm, `.lower()` cho giá trị; dữ liệu CMDB bẩn (`PROD`, `Payment-API`, `Active`) không
  sinh ra nhóm trùng nghĩa khác tên.
- **Lọc theo `status`.** Máy decommissioned vẫn còn trong CMDB vài tuần (chờ thu hồi); deploy vào đó là lỗi hay rò cấu hình.
- **Logic nhóm thứ cấp ở `constructed`.** Nhóm `canary`, `big` và biến `olist_worker_concurrency` suy ra từ biến của máy, nên script
  chỉ lo dịch dữ liệu nguồn. `strict: true` biến lỗi biểu thức thành lỗi thật. Tên `cmdb.py` đứng trước `constructed.yml` theo thứ tự
  chữ cái, nên khi `constructed` chạy biến đã có.
- **Pattern thay vì danh sách tên.** `role_worker:&env_prod:&canary` và `role_worker:&env_prod:!canary`: thêm máy vào CMDB là
  tự vào đúng đợt. Play 2 dùng `serial: "50%"` (xem Advanced 01).

## Đọc thêm

- Ở cloud thật dùng inventory plugin (`amazon.aws.aws_ec2`, `google.cloud.gcp_compute`) cùng `keyed_groups` thay vì script; script
  hợp với nguồn nội bộ không có plugin. Plugin hỗ trợ cache (`cache: true`, `cache_timeout`) để không gọi API mỗi lần.
- Pattern mọi máy prod ở `hcm-1a` trừ database: `env_prod:&az_hcm_1a:!role_postgres`.
- `--limit` cũng nhận pattern và giao với `hosts:` của play; `--limit @retry_file` chạy lại đúng máy lỗi.

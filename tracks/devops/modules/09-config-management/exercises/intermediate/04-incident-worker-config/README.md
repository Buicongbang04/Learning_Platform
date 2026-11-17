---
title: Sự cố - cấu hình worker đổi mà như không đổi
level: intermediate
services: []
files:
  - path: starter/site.yml
    note: Play đang dùng trên staging
  - path: starter/inventory/hosts.yml
    note: Hai worker và một máy batch
  - path: starter/inventory/group_vars/workers.yml
    note: Thay đổi gần nhất của ops
  - path: starter/roles/olist_worker_config/tasks/main.yml
    note: Task của role
  - path: starter/roles/olist_worker_config/defaults/main.yml
    note: Biến mặc định
  - path: starter/roles/olist_worker_config/vars/main.yml
    note: Biến của role
  - path: starter/roles/olist_worker_config/handlers/main.yml
    note: Handler
  - path: tests/fixtures/incident/site.yml
    note: Bản lúc sự cố (cả thư mục incident), test dùng để tái hiện triệu chứng
  - path: tests/test_incident_worker_config.py
    note: Không sửa
run:
  - docker pull python:3.12.16-slim-trixie
  - uv run pytest tracks/devops/modules/09-config-management/exercises/intermediate/04-incident-worker-config -q -rs
---

## Mục tiêu

Chẩn đoán như người on-call một role "chạy xanh" mà không làm đúng việc: đọc recap, so giá trị biến Ansible thấy với giá trị trên
máy, tìm task nói dối về thay đổi, sửa tận gốc và giữ được một ca hồi quy.

## Đề bài

Role `olist_worker_config` (trong `starter/`) cấu hình worker trên staging: `worker-1`, `worker-2` (nhóm `workers`) và `worker-3`
(nhóm `batch`, chạy job đêm, không có biến riêng trong inventory). Ba báo cáo trong tuần:

1. Ops đặt `olist_worker_log_level: DEBUG` trong `inventory/group_vars/workers.yml` để điều tra job chậm. Deploy xanh, nhưng
   `/etc/olist-shop/worker.env` trên `worker-1` vẫn `LOG_LEVEL=INFO`. `ansible-inventory -i inventory --host worker-1` lại in
   `"olist_worker_log_level": "DEBUG"`.
2. Dashboard theo dõi thay đổi đỏ cả tuần: mọi lần deploy, kể cả khi không ai đổi gì, recap báo `changed=1` trên **mọi** máy, luôn ở
   cùng một task.
3. Hôm qua chuyển worker sang Redis mới (`redis-b`) bằng cách sửa `olist_worker_redis_url` trong `group_vars/workers.yml`. Env file trên
   hai worker đã có URL mới, nhưng recap không báo thay đổi nào ở task env file và worker vẫn nói chuyện với Redis cũ tới khi có người
   restart tay.

Sửa `starter/` cho hết cả ba triệu chứng mà không đổi thiết kế: inventory vẫn là nơi ops đặt giá trị cho từng nhóm, role vẫn có giá
trị mặc định cho máy không đặt gì. Viết postmortem ngắn (không chấm tự động): nguyên nhân gốc từng triệu chứng, vì sao recap và
`ansible-inventory` không báo động, cách phát hiện sớm lần sau.

| Kết quả cần có | Test kiểm |
| --- | --- |
| Giá trị của inventory có hiệu lực | `worker-1`, `worker-2`: `LOG_LEVEL=DEBUG`; `worker-3`: env file đúng `REDIS_URL=redis://redis.internal:6379/0` và `LOG_LEVEL=INFO` (mặc định của role) |
| Thư mục dữ liệu | `/var/lib/olist-shop` `0750 olist:olist` trên cả ba máy |
| Không báo đổi giả | Chạy lại không đổi gì: `changed=0` trên mọi máy |
| Đổi thật thì restart | Đổi URL Redis trong `group_vars/workers.yml` rồi chạy: env file có URL mới, `worker-1` và `worker-2` mỗi máy đúng `changed=1`, handler `Restart olist-worker` chạy trên đúng hai máy đó, `worker-3` `changed=0` |
| Check mode | `--check --diff` sau đó `changed=0` |

**Cách test chấm.** Hai `AnsibleLab` riêng, mỗi lab ba container. Lab đầu chạy `starter/` (hay lời giải với `SOLUTION=1`): converge,
chạy lại, sửa URL Redis trong bản chép của `group_vars/workers.yml`, chạy, rồi `--check --diff`. Lab thứ hai chạy y hệt với
`tests/fixtures/incident/` (bản lúc sự cố) và đòi nó tái hiện đúng ba triệu chứng, để chứng minh test bắt được lỗi. Khoảng 1 phút.

## Tiêu chí đạt

- Mọi test pass, kể cả ca tái hiện sự cố.
- Postmortem chỉ ra nguyên nhân gốc của từng triệu chứng và một biện pháp phát hiện tự động cho mỗi cái.
- Nói được vì sao triệu chứng 2 và triệu chứng 3 là cùng một loại lỗi: recap không phản ánh đúng thay đổi thật.

## Gợi ý

### Gợi ý 1

Với triệu chứng 1, `ansible-inventory` chỉ thấy biến của inventory. Xem giá trị Ansible **thật sự dùng** khi chạy role bằng một task
`ansible.builtin.debug: var=olist_worker_log_level` tạm thời, rồi đối chiếu với bảng precedence ở mục 4 của module.

### Gợi ý 2

Chạy starter hai lần liền, đọc task nào báo `changed` ở lần hai. Với triệu chứng 3, so nội dung tệp trước và sau với dòng recap của
task ghi tệp đó: Ansible quyết định "changed" dựa trên gì, và có gì trong task ghi đè quyết định đó không.

---
title: Role idempotent cài và cấu hình worker Olist Shop
level: intermediate
services: []
files:
  - path: starter/site.yml
    note: Play gọi role, không sửa
  - path: starter/inventory/hosts.yml
    note: Hai worker, không sửa
  - path: starter/inventory/group_vars/workers.yml
    note: URL database và Redis của staging
  - path: starter/roles/olist_worker/tasks/main.yml
    note: Viết các task
  - path: starter/roles/olist_worker/handlers/main.yml
    note: Viết handler
  - path: starter/roles/olist_worker/defaults/main.yml
    note: Biến mặc định của role
  - path: starter/roles/olist_worker/meta/main.yml
    note: Metadata của role
  - path: starter/roles/olist_worker/templates/worker.env.j2
    note: Env file của worker
  - path: starter/roles/olist_worker/templates/olist-worker.service.j2
    note: Unit của module 01, chuyển thành template
  - path: tests/test_worker_role.py
    note: Không sửa
run:
  - docker pull python:3.12.16-slim-trixie
  - uv run pytest tracks/devops/modules/09-config-management/exercises/intermediate/01-olist-worker-role -q -rs
---

## Mục tiêu

Đóng gói việc cài một service thành role có giao diện rõ (biến trong `defaults`), chạy bao nhiêu lần cũng ra cùng một trạng thái,
chỉ restart service khi cấu hình thật sự đổi, tự sửa drift, và chạy được một phần bằng tag. Đây là kịch bản converge rồi kiểm
idempotence của molecule, chấm bằng test.

## Đề bài

Module 01 bạn đã viết `olist-worker.service` bằng tay. Giờ có 2 worker staging (sắp thành 40 máy production), nên việc cài phải là
code. Viết role `roles/olist_worker` cài worker Olist Shop trên Debian. Test chép package `olist_shop` của sample-app vào
`artifacts/olist_shop/` cạnh `site.yml` trước khi chạy (vai trò của artifact build ở module 07). Máy target có sẵn
`/usr/local/bin/python3` (3.12) và một kho wheel nội bộ ở `/srv/wheels` (không có Internet, như mạng production đóng).

| Mục | Yêu cầu test kiểm |
| --- | --- |
| Layout | `defaults/main.yml`, `tasks/main.yml`, `handlers/main.yml`, `meta/main.yml`, `templates/worker.env.j2`, `templates/olist-worker.service.j2` |
| User | User hệ thống `olist` (UID dưới 1000), group `olist`, shell `/usr/sbin/nologin` |
| Thư mục | `/opt/olist-shop` `0755 root:root`; `/etc/olist-shop` `0750 root:olist` |
| Code | `/opt/olist-shop/app/olist_shop/` chép từ biến `olist_worker_src` (mặc định `{{ playbook_dir }}/artifacts/olist_shop/`), tệp `0644 root:root` |
| Dependency | Virtualenv `/opt/olist-shop/.venv` tạo bằng `/usr/local/bin/python3 -m venv`, cài `sqlalchemy==2.1.6`, `psycopg[binary]==3.3.6`, `redis==8.1.0`, `prometheus-client==0.26.0` **chỉ** từ `/srv/wheels` |
| Env file | `/etc/olist-shop/worker.env` `0640 root:olist`, đúng bốn biến `DATABASE_URL`, `REDIS_URL`, `LOG_LEVEL`, `PYTHONPATH=/opt/olist-shop/app` (dòng chú thích được phép); giá trị lấy từ `olist_worker_database_url`, `olist_worker_redis_url` (inventory đặt), `olist_worker_log_level` (mặc định `INFO`) |
| Unit | `/etc/systemd/system/olist-worker.service` `0644 root:root`; `[Service]` có `User=olist`, `Group=olist`, `EnvironmentFile=/etc/olist-shop/worker.env`, `WorkingDirectory=/opt/olist-shop/app`, `ExecStart=/opt/olist-shop/.venv/bin/python -m olist_shop.worker`, `Restart=on-failure`, `MemoryMax=512M` (biến `olist_worker_memory_max`), `NoNewPrivileges=yes`, `ProtectSystem=strict`; `[Install]` có `WantedBy=multi-user.target`; `systemd-analyze verify` trong target không lỗi, không cảnh báo |
| Chạy được | User `olist` nạp env file rồi `import olist_shop.worker` bằng python của venv thành công, `Settings().log_level` là `INFO` |
| Handler | Handler tên đúng `Restart olist-worker`, được notify khi code, venv, env file hay unit đổi |
| Service | Task bật và khởi động `olist-worker` (`ansible.builtin.systemd_service`), chỉ chạy khi `ansible_facts.service_mgr == "systemd"`; handler cũng vậy |
| Tag | Task ghi env file và unit gắn tag `config`; chỉ chúng mang tag này |

Vì sao service không thật sự chạy trong lab: target là container không có systemd làm PID 1 (systemd trong container cần quyền mà lab
cấm). Role vẫn viết như cho VM thật; trên lab `service_mgr` là `sshd` nên hai task quản service bị bỏ qua, còn unit được kiểm bằng
`systemd-analyze verify` ngay trên target. Test vẫn thấy handler được notify (nó hiện là `skipped` trong kết quả).

**Cách test chấm.** `AnsibleLab` dựng `worker-1`, `worker-2`. Chuỗi: converge hai lần (lần hai phải `changed=0`, không handler);
`--check --diff` (phải `changed=0`); `-e olist_worker_log_level=DEBUG` (đúng một task đổi trên mỗi máy, handler chạy);
`--tags config -e olist_worker_log_level=WARNING` (chỉ task có tag `config`, không có `copy` hay `pip`); chạy lại mặc định rồi test sửa
tay unit trên `worker-1` và chạy lần nữa (chỉ `worker-1` đổi và chỉ nó restart). Khoảng 1,5 phút.

## Tiêu chí đạt

- Mọi test pass, không skip.
- Giải thích được vì sao biến người dùng cần ghi đè nằm ở `defaults` chứ không ở `vars` của role.
- Nói được `--check` của từng module trong role có trung thực không, và vì sao một module báo `changed` trong check mode dù máy đã đúng.
- So sánh được bài này với một kịch bản molecule: converge, idempotence, verify; test của bài làm phần nào.

## Gợi ý

### Gợi ý 1

`ansible.builtin.copy` với `src` kết thúc bằng `/` chép **nội dung** thư mục; `directory_mode` đặt quyền thư mục con.
`ansible.builtin.pip` nhận `name` là danh sách, `virtualenv`, `virtualenv_command`. Đừng dùng `extra_args` để chỉ kho wheel:
check mode của module `pip` luôn báo `changed` khi có `extra_args` hay `requirements`. Biến môi trường `PIP_NO_INDEX` và
`PIP_FIND_LINKS` (khoá `environment:` của task) làm được việc tương tự.

### Gợi ý 2

Tên trong `notify:` phải trùng `name:` của handler (hoặc `listen:`). Handler của role được gọi bằng tên ngắn, không cần tiền tố
role. Tag đặt ở cấp task (`tags: [config]`). `{{ ansible_managed }}` trong dòng chú thích đầu template nhắc người sửa tay rằng tệp
do Ansible quản.

# Lời giải: role idempotent cho worker Olist Shop

Lời giải là `roles/olist_worker/` (cộng `site.yml`, `inventory/` giữ như starter).

## Các quyết định

- **Giao diện ở `defaults`.** Mọi giá trị người dùng role có thể muốn đổi (URL, log level, giới hạn RAM, đường dẫn nguồn, danh sách
  gói) nằm ở `defaults/main.yml`, tầng thấp nhất của precedence, nên inventory hay `-e` ghi đè được. Role không có `vars/main.yml`.
- **Thứ tự task theo phụ thuộc.** Group trước user; thư mục cấu hình thuộc group `olist` nên tạo sau group; venv trước unit vì
  `ExecStart` trỏ vào python của venv (`systemd-analyze verify` kiểm đường dẫn này có thực thi được).
- **Code là artifact, không `git clone` trên máy đích.** `copy` thư mục đã build (module 07) nên mọi máy chạy đúng một bản, máy đích
  không cần quyền đọc repo. Ở production thay bằng `unarchive` một tarball có checksum từ kho artifact.
- **Wheel nội bộ qua biến môi trường của pip.** `PIP_NO_INDEX=1`, `PIP_FIND_LINKS=/srv/wheels` thay vì `extra_args`: module `pip`
  coi mọi `extra_args` (và `requirements:`) là "không biết", nên `--check` luôn báo `changed`. Với `name:` là danh sách ghim phiên
  bản, check mode so được với `pip freeze` và trung thực.
- **Một handler, nhiều nguồn notify.** Code, venv, env file, unit đều notify `Restart olist-worker`; handler chạy một lần ở cuối
  play dù được notify bốn lần. `daemon_reload: true` để unit mới có hiệu lực.
- **Quản service có điều kiện.** `when: ansible_facts.service_mgr == "systemd"` giữ role đúng trên VM thật và chạy được trong lab
  container. Đây là điều kiện về **môi trường**, không phải cờ riêng cho lab: role không có biến kiểu `olist_worker_in_lab`.
- **Tag `config` cho thay đổi nhỏ, thường xuyên.** Đổi log level không cần chép lại code hay kiểm venv. Không gắn tag cho task tạo
  user và thư mục là có chủ đích: chạy `--tags config` trên máy mới sẽ fail vì thiếu group `olist`, đúng là tín hiệu nên chạy đủ.
- **`ansible_managed` ở đầu template.** Người mở tệp trên máy biết sửa tay sẽ bị ghi đè (và test drift chứng minh điều đó).

## Molecule

Molecule là khung test cho role: `create` (dựng máy test), `converge` (chạy role), `idempotence` (chạy lại, fail nếu có task
`changed`), `verify` (assert trạng thái bằng Ansible hay testinfra), `destroy`. Test của bài làm đúng các bước đó: `AnsibleLab` là
`create`/`destroy`, hai lần `playbook` là `converge` và `idempotence`, các `assert` trên `lab.read`/`lab.stat`/`systemd-analyze` là
`verify`. Bài không chạy molecule thật vì driver docker cần socket Docker, mà sandbox của test che socket đó. Ở repo thật, đặt
`molecule/default/` trong role và chạy `molecule test` trong CI có Docker.

## Đọc thêm

- Muốn service thật sự chạy trong lab cần container có systemd làm PID 1 (image kiểu `geerlingguy/docker-debian12-ansible`,
  `--privileged` hoặc `--cgroupns=host` cùng cgroup ghi được). Đó là quyền mà lab cấm, và cũng là lý do molecule cho role systemd
  thường chạy trong VM (driver Vagrant, EC2) hay container đặc quyền trên runner riêng.
- Kiểm role bằng `ansible-lint` profile `production` trước khi review.

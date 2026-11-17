# Lời giải: sự cố cấu hình worker đổi mà như không đổi

Lời giải nằm trong `roles/olist_worker_config/` (`defaults/main.yml`, `vars/main.yml`, `tasks/main.yml`); các tệp khác giữ như starter.

## Nguyên nhân gốc

1. **`olist_worker_log_level` nằm trong `vars/main.yml` của role.** Role vars đứng ở tầng 15 của precedence, cao hơn
   `inventory/group_vars/*` (tầng 6), nên giá trị `DEBUG` của ops bị nuốt mà không có cảnh báo. `ansible-inventory` chỉ in biến của
   inventory nên vẫn thấy `DEBUG`: công cụ đúng, người đọc sai tầng. Sửa: chuyển giá trị mặc định sang `defaults/main.yml` (tầng 2);
   `vars/main.yml` chỉ còn hằng số nội bộ (đường dẫn tệp).
2. **Task `ansible.builtin.shell: chown -R olist:olist /var/lib/olist-shop`.** Shell không biết trạng thái nên luôn báo `changed`.
   Recap đỏ mọi lần làm người ta quen bỏ qua "changed", và đó là lý do triệu chứng 3 không ai thấy. Sửa: `owner`, `group` ngay trong
   task `ansible.builtin.file` tạo thư mục.
3. **`changed_when: false` trên task ghi env file.** Ai đó thêm vào để "tắt" màu vàng trên dashboard. Template vẫn ghi tệp mới, nhưng
   kết quả bị ép thành không đổi, nên `notify` không bao giờ kích hoạt handler: worker chạy với cấu hình cũ tới khi restart tay. Sửa:
   bỏ dòng đó. Chỉ dùng `changed_when: false` cho task chỉ đọc.

## Postmortem mẫu (rút gọn)

- **Ảnh hưởng**: 3 ngày không có log DEBUG khi điều tra job chậm; 14 giờ worker dùng Redis cũ sau migration, job xếp hàng ở Redis
  mới không ai xử lý.
- **Vì sao không phát hiện**: deploy luôn xanh; recap luôn `changed=1` nên "changed" không còn là tín hiệu; không có bước kiểm cấu
  hình trên máy sau deploy.
- **Hành động**: CI chạy converge hai lần và đòi lần hai `changed=0` (bắt triệu chứng 2); `ansible-lint` với rule `no-changed-when`
  và review mọi `changed_when: false` trên task ghi tệp (triệu chứng 3); quy ước role chỉ dùng `defaults` cho giá trị người dùng đổi
  được, lint tuỳ biến cảnh báo khi một biến xuất hiện cả trong `vars/` của role và inventory (triệu chứng 1); bước verify sau deploy
  đọc `worker.env` và so với giá trị mong đợi.

## Đọc thêm

- `ansible-playbook ... -e` "sửa" được triệu chứng 1 vì extra vars thắng role vars, nhưng đó là che lỗi: cấu hình thật của môi
  trường lại không nằm trong Git.
- Cách xem biến thực tế ở tầng play: task tạm `ansible.builtin.debug: var=olist_worker_log_level` trong role, hay
  `ansible-playbook --start-at-task` cùng `-v`.

# Lời giải: viết lại playbook toàn shell bằng module

Lời giải là `harden.yml`.

## Các quyết định

- **`file` cho thư mục và symlink.** Hai task `state: directory` (quyền khác nhau) và một task `state: link`. Module so trạng thái
  hiện tại nên chạy lại không đổi gì; `ln -sfn` luôn ghi lại link và luôn báo `changed`.
- **`lineinfile` có `regexp`.** Dòng `TZ=` được sửa tại chỗ, `LOG_LEVEL=` được thêm đúng một lần. `echo >>` thêm một dòng mỗi lần chạy.
  Khi tệp có nhiều dòng cần quản, chuyển sang `template` cho cả tệp: một nguồn sự thật, không trộn sửa tay với Ansible.
- **Lệnh chỉ đọc: `changed_when: false`.** `python3 --version` và `grep -c` không đổi gì trên máy; không có dòng này recap báo
  `changed` mỗi lần và che mất thay đổi thật.
- **`failed_when: errors.rc > 1`.** `grep` trả 0 khi có dòng khớp, 1 khi không có (log sạch, không phải lỗi), 2 khi lỗi (tệp không
  có). `ignore_errors: true` sai vì nuốt cả lỗi thật của `worker-3`.
- **`command`, không `shell`.** Không cần pipe hay chuyển hướng nên không cần shell: tránh injection và hành vi phụ thuộc shell.
- **Dừng bằng `assert` có `fail_msg`.** Người trực đọc được ngay lý do (`7 dòng ERROR`), thay vì một mã thoát.

## Đọc thêm

- `ansible-lint` bắt các mẫu này: `command-instead-of-module`, `no-changed-when`, `risky-shell-pipe`.
- Khi buộc phải dùng `command` để tạo gì đó: `creates:`/`removes:` cho Ansible biết khi nào bỏ qua; trong check mode task có
  `creates` vẫn được đánh giá đúng.

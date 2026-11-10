# Lời giải: Ansible trên máy đang chạy hay image bất biến

Tài liệu mẫu: `DECISION.md`. Không có một đáp án duy nhất; rubric dưới chấm lập luận.

## Rubric (10 điểm)

| Tiêu chí | Đạt | Điểm |
| --- | --- | --- |
| Gắn với số liệu của đề | Mỗi quyết định dẫn ít nhất một số liệu (9 phút boot, 40 phút hàng đợi, 2 TB, rule đổi hằng ngày, ba máy lệch bản) | 2 |
| Worker | Chọn image (hay kết hợp có lý do), nêu cái giá: build mỗi lần deploy, vá khẩn chậm hơn, cần pipeline image | 1 |
| Postgres | Giữ Ansible (dữ liệu không thay máy được), nêu cách giảm drift (job `--check` định kỳ) và thứ tự thay đổi (replica trước) | 1 |
| Nginx edge | Nhận ra hai nhịp thay đổi khác nhau (OS theo tháng, rule theo ngày) và tách phần thuộc image với phần đẩy bằng Ansible, hoặc lập luận được vì sao không tách | 1 |
| Tái dùng role | Role Ansible hiện có thành provisioner của Packer, không viết lại cấu hình hai lần | 1 |
| Rollback và drift | Luồng có canary, health check, đường rollback cụ thể cho cả hai kiểu (image cũ; playbook bản cũ và giới hạn của nó) | 1 |
| Tuân thủ | Trả lời câu hỏi audit: quét trên image, SBOM hay nhãn image, CIS áp bằng cùng role cho máy mutable | 1 |
| Secret | Không secret trong image hay user-data; nguồn lúc chạy (Secrets Manager, Vault) và quyền đọc (role IAM của instance) | 1 |
| Lộ trình | Chuyển từng bước, có đường lui, có chỉ số đo sau chuyển đổi | 1 |

## Điểm hay bị trừ

- "Immutable cho mọi thứ" kể cả Postgres mà không nói dữ liệu đi đâu và mất bao lâu để thay một primary 2 TB.
- Coi Ansible và image là loại trừ nhau. Thực tế phổ biến nhất là Ansible **trong** pipeline build image, cộng Ansible cho phần còn lại.
- Bỏ qua vá CVE khẩn: image cần build, quét, rollout; cần quy trình (playbook vá khẩn có thời hạn, hay pipeline đủ nhanh).
- Nướng secret vào image cho boot nhanh, hay đặt mật khẩu vào user-data (đọc được từ metadata endpoint).
- Không đề cập máy "sống lâu": image bất biến chỉ có lợi khi máy thật sự được thay định kỳ.

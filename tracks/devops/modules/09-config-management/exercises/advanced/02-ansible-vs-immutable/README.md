---
title: Chọn Ansible trên máy đang chạy hay image bất biến cho từng workload của Olist Shop
level: advanced
services: []
files:
  - path: starter/DECISION.md
    note: Khung tài liệu quyết định
  - path: tests/test_decision.py
    note: Kiểm cấu trúc, không sửa
  - path: tests/fixtures/DECISION.good.md
    note: Ví dụ đạt (tình huống khác)
run:
  - uv run pytest tracks/devops/modules/09-config-management/exercises/advanced/02-ansible-vs-immutable -q -rs
---

## Mục tiêu

Ra một quyết định kiến trúc có lý lẽ, không theo phong trào: với từng workload, cấu hình máy đang chạy (mutable, Ansible) hay thay máy
bằng image dựng sẵn (immutable), hay kết hợp; kèm luồng build, cách xử lý drift, vá lỗi, secret, rủi ro và lộ trình.

## Đề bài

Olist Shop giữa năm 2027:

- **Worker**: 12 VM lúc thường, tới 60 trong đợt 11.11 nhờ autoscaling group; stateless; deploy khoảng 10 lần mỗi tuần. Jenkins đẩy
  playbook tới 40 worker mất 25 phút; máy mới do autoscaling tạo chạy `ansible-pull` qua cloud-init, 9 phút mới nhận job, nên đợt
  11.11 năm ngoái hàng đợi dồn 40 phút. Tháng trước ba worker bị `pip install` bản vá tay lúc trực đêm và lệch bản hai tuần.
- **Postgres**: một primary, hai replica trên VM, 2 TB dữ liệu, vá OS hằng tháng, không dựng lại nhanh được.
- **Nginx edge**: 4 VM giữ TLS (chứng chỉ 60 ngày) và rule rate limit đổi gần như mỗi ngày.
- **Bastion**: 1 VM.
- **Tuân thủ**: audit hằng quý đòi chứng minh mọi máy theo CIS level 1 và biết gói nào đang chạy ở đâu.
- **Team**: 4 người platform, quen Ansible, chưa dùng Packer.

Điền `starter/DECISION.md` (giữ đúng 7 tiêu đề `## 1.` tới `## 7.`).

| Phần | Test kiểm |
| --- | --- |
| Toàn tài liệu | Không còn `TODO`; không câu nào đưa secret (mật khẩu, token, khoá riêng) vào image mà không phủ định |
| 1. Bối cảnh | Ít nhất 300 ký tự văn xuôi |
| 2. Tiêu chí | Bảng ít nhất 6 tiêu chí đủ 3 cột; phần này nói tới drift, rollback và thời gian boot |
| 3. Quyết định | Bảng có dòng cho worker, postgres, nginx, bastion; cột Chọn là `Ansible`, `Image` hoặc `Kết hợp` |
| 4. Luồng | Khối mermaid có build, image, ansible, rollback; phần này nhắc công cụ build image (Packer, image builder hay docker build) |
| 5. Drift | Ít nhất 4 gạch đầu dòng; nói tới `--check`, CIS, patch hay vá |
| 6. Secret | Ít nhất 3 gạch đầu dòng; nói tới vault, Secrets Manager hay Parameter Store, và cloud-init hay user-data |
| 7. Rủi ro | Ít nhất 4 gạch đầu dòng |

Test chỉ kiểm cấu trúc và từ khoá; chất lượng lập luận chấm bằng rubric trong `SOLUTION.md` (tự chấm hoặc nhờ người review).

**Cách test chấm.** Đọc `starter/DECISION.md` và chạy cùng bộ kiểm trên ba fixture (khung, bản yếu, bản đạt) để chứng minh bộ kiểm
bắt được lỗi. Không cần Docker.

## Tiêu chí đạt

- Test pass.
- Rubric trong `SOLUTION.md` đạt từ 7/10: mỗi quyết định có lý do gắn với số liệu của đề, nêu rõ cái giá phải trả.
- Bảo vệ được quyết định trước câu hỏi "vậy sao không đưa luôn Postgres lên image?" và "vá CVE khẩn trong 1 giờ thì làm sao?".

## Gợi ý

### Gợi ý 1

Hai câu hỏi tách workload: máy có giữ dữ liệu không thay được không, và máy có được tạo, huỷ tự động không. Role Ansible bạn viết ở
Intermediate 01 không bỏ đi khi chuyển sang image: Packer chạy nó làm provisioner lúc build.

### Gợi ý 2

Đọc `tests/fixtures/DECISION.good.md` để thấy độ chi tiết mong đợi (tình huống của nó khác của bạn). Phần secret: cái gì ở trong
image thì ai đọc được image cũng đọc được; user-data đọc được từ metadata của máy.

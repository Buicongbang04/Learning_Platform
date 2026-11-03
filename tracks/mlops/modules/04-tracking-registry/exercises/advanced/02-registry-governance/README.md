---
title: Thiết kế registry dùng chung cho nhiều đội ML
level: advanced
services: []
files:
  - path: starter/DESIGN.md
    note: Khung thiết kế, điền mọi TODO
  - path: tests/fixtures/DESIGN.bad.md
    note: Ví dụ thiết kế yếu, test dùng để kiểm bộ kiểm tra
  - path: tests/test_design.py
    note: Không sửa
run:
  - uv run pytest tracks/mlops/modules/04-tracking-registry/exercises/advanced/02-registry-governance -q
---

## Mục tiêu

Thiết kế cách một công ty dùng chung một hệ tracking và registry mà không biến nó thành bãi rác hay điểm sự cố chung: đặt
tên, quyền, vận hành, và lúc nào nên bỏ tự host.

## Đề bài

Công ty taxi có 4 đội ML (ETA, giá cước, phát hiện gian lận, gợi ý điểm đón) với 30 người và khoảng 12 model production.
Hiện mỗi đội tự chạy MLflow riêng với file store trên máy một người, nên không ai biết model nào đang chạy ở đâu, hai lần
có người đổi model nhầm của đội khác, và một ổ đĩa hỏng làm mất 3 tháng run của đội giá cước. Kiểm toán nội bộ sắp yêu cầu
biết "ai duyệt model này lên production, dựa trên số liệu nào".

Ràng buộc: ngân sách hạ tầng nhỏ (một cụm Postgres, một object storage), chưa có nền tảng đám mây quản lý; đội giá cước có
dữ liệu nhạy cảm, các đội khác không được đọc artifact của họ; đội vận hành chỉ có 2 người.

Viết `starter/DESIGN.md`, giữ các heading `## 1.` tới `## 6.`, không còn chữ `TODO`:

| Phần | Yêu cầu kiểm tự động |
| --- | --- |
| 1. Bối cảnh và giả định | Ít nhất 300 ký tự (không tính bảng và khối code) |
| 2. Kiến trúc | Khối ` ```mermaid ` có ít nhất 6 cạnh (`-->`, `->>` hoặc `---`) |
| 3. Quy ước đặt tên và metadata | Bảng ít nhất 6 dòng đủ 3 cột (`Đối tượng`, `Quy ước`, `Lý do`) |
| 4. Vai trò và quyền | Bảng ít nhất 5 vai trò đủ 4 cột (`Vai trò`, `Được làm`, `Không được làm`, `Cơ chế thực thi`); vai trò Data Scientist hoặc ML Engineer không được có `champion`, `promote` hay `production` trong cột `Được làm` |
| 5. Vận hành | Ít nhất 4 gạch đầu dòng, có nhắc `backup` và `retention` |
| 6. Rủi ro và việc còn mở | Ít nhất 3 gạch đầu dòng |

Test chỉ kiểm khung và quy tắc về quyền promote ở trên; một test khác đưa một thiết kế yếu vào cùng bộ kiểm tra và đòi nó
bị bắt. Nội dung chấm bằng rubric trong `solutions/advanced/02-registry-governance/SOLUTION.md`; đọc rubric **sau** khi viết
xong.

## Tiêu chí đạt

- `uv run pytest tracks/mlops/modules/04-tracking-registry/exercises/advanced/02-registry-governance -q` pass.
- Tự chấm đạt ít nhất 70/100 điểm rubric.
- Mỗi quyết định ở phần 3 và 4 truy được về một yêu cầu trong đề (kiểm toán, cô lập đội giá cước, đội vận hành 2 người...).
- Nêu điều kiện cụ thể để chuyển sang dịch vụ quản lý hoặc SaaS, không chỉ "khi lớn hơn".

## Gợi ý

### Gợi ý 1

Phân biệt ba lớp kiểm soát: cái MLflow OSS làm được (đặt tên, tag, alias), cái cần proxy hoặc IdP đứng trước, và cái chỉ làm
được bằng quy trình. Điền cột "Cơ chế thực thi" trung thực: "quy ước" khác "bị chặn".

### Gợi ý 2

Với mỗi tài nguyên dùng chung (Postgres, MinIO, server), hỏi: nếu nó chết lúc 9 giờ sáng thứ Hai thì đội nào dừng việc, và
phục hồi mất bao lâu. Đó là phần 5.

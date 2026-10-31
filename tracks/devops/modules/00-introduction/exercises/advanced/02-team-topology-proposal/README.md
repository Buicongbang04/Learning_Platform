---
title: Đề xuất mô hình DevOps, SRE và Platform cho công ty đang lớn
level: advanced
services: []
files:
  - path: starter/PROPOSAL.md
    note: Khung đề xuất, điền mọi TODO
  - path: tests/test_proposal.py
    note: Không sửa; chỉ kiểm khung, chất lượng chấm theo rubric
run:
  - uv run pytest tracks/devops/modules/00-introduction/exercises/advanced/02-team-topology-proposal -q
---

## Mục tiêu

Thiết kế cách tổ chức con người quanh việc vận hành, câu hỏi thiết kế hay gặp nhất ở phỏng vấn DevOps/SRE senior:
ai sở hữu service, ai trực on-call, platform team làm gì và không làm gì, SRE đứng ở đâu, và đi từ hiện trạng tới
mô hình mới thế nào mà không làm sập hệ thống giữa chừng.

## Đề bài

Công ty bán lẻ online vận hành một hệ thống giống Olist Shop nhưng lớn hơn. 18 tháng qua đội kỹ thuật tăng từ 15
lên **60 kỹ sư** (con số này đã gồm mọi người hiện có, ngân sách năm nay không tuyển thêm):

- 8 team sản phẩm (catalog, search, checkout, payment, đơn hàng, giao vận, khuyến mãi, app mobile), 5–7 người mỗi team.
- 1 "DevOps team" 4 người: nhận mọi ticket deploy, tạo hạ tầng, sửa pipeline, trực on-call cho **toàn bộ** hệ thống.
  Hai người đã xin nghỉ vì quá tải. Hàng đợi ticket trung bình 6 ngày.
- Mỗi team tự viết pipeline và Dockerfile; có 5 cách deploy khác nhau. Lỗ hổng image cơ sở phải vá ở 23 repo.
- Checkout và payment chiếm 80% doanh thu; một giờ sập checkout mất khoảng 1 tỉ đồng. Các service khác chấp nhận
  chậm vài phút.
- CEO đọc một bài viết và muốn "lập team SRE 10 người như Google".

Điền `starter/PROPOSAL.md`:

1. **Hiện trạng và vấn đề**: ít nhất 3 vấn đề, mỗi vấn đề nêu hậu quả kinh doanh.
2. **Mô hình đề xuất**: bảng các team (tên, loại theo Team Topologies: `stream-aligned`, `platform`, `enabling`,
   `complicated-subsystem`; số người; sở hữu gì; on-call thế nào). Tổng số người không vượt 60, mỗi team 2–12 người.
3. **Ranh giới trách nhiệm**: ít nhất 6 việc vận hành (deploy, on-call, SLO, hạ tầng, bảo mật image, postmortem,
   capacity…), ghi rõ vai trò của team sản phẩm, platform và SRE cho từng việc.
4. **Lộ trình chuyển đổi**: ít nhất 3 bước có thứ tự, nói rõ điều kiện để sang bước sau.
5. **Rủi ro và cách đo thành công**: ít nhất 3 dòng, mỗi dòng có dấu hiệu hoặc metric và cách xử lý.

## Tiêu chí đạt

- `uv run pytest tracks/devops/modules/00-introduction/exercises/advanced/02-team-topology-proposal -q` pass: không
  còn TODO, đủ các phần, bảng team hợp lệ. Chất lượng chấm theo rubric trong
  `solutions/advanced/02-team-topology-proposal/SOLUTION.md`.
- Đạt ít nhất 70/100 điểm rubric khi tự chấm.
- Trả lời được câu CEO sẽ hỏi: "Vì sao không lập team SRE 10 người?" bằng một đoạn ngắn có số liệu từ đề.

## Gợi ý

### Gợi ý 1

Bắt đầu từ cognitive load: team sản phẩm 6 người không thể tự giỏi Kubernetes, OpenTofu, bảo mật image và on-call
cùng lúc. Platform team tồn tại để giảm tải đó bằng sản phẩm tự phục vụ, không phải bằng nhận ticket. SRE đắt, nên
đặt ở nơi một giờ sập đắt nhất.

### Gợi ý 2

Chuyển đổi theo từng team, không "big bang". Một cách hay dùng: chọn một team sản phẩm làm thí điểm golden path,
chuyển on-call service đó cho chính team (kèm runbook và alert đã dọn), đo lại, rồi nhân rộng. Không bỏ on-call cũ
trước khi on-call mới đã chạy thật ít nhất vài tuần.

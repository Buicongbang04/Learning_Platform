---
title: Thiết kế governance cho ba đội ML có mức rủi ro khác nhau
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
  - uv run pytest tracks/mlops/modules/12-ml-platform-governance/exercises/advanced/01-governance-three-teams -q
---

## Mục tiêu

Một quy trình governance duy nhất cho mọi đội thì quá nặng với đội nghiên cứu hoặc quá lỏng với đội tín dụng. Bạn thiết kế governance **theo tầng rủi ro**: ai được duyệt, kiểm soát nào bắt buộc ở tầng nào, audit giữ bao lâu, và cái giá của nó.

## Đề bài

Công ty fintech có 25 người ML dùng chung một registry và một cụm Kubernetes, do hai kỹ sư nền tảng vận hành:

- **`credit-risk`** (6 người): model chấm điểm tín dụng, quyết định cho vay tự động. Chịu thanh tra của ngân hàng trung ương: phải tái lập và giải thích được bất kỳ quyết định nào trong **5 năm gần nhất**; sai là tổn thất tiền và rủi ro pháp lý.
- **`recsys`** (12 người): gợi ý sản phẩm trên trang chủ. Ảnh hưởng doanh thu, không bị quản lý trực tiếp; sai thì mất tiền nhưng sửa được trong ngày.
- **`research`** (7 người): thử nghiệm trên notebook, model chưa phục vụ khách hàng.

Hiện mỗi đội tự đặt luật; tuần trước một thành viên `recsys` tự đổi alias `champion` của model đội khác trong lúc debug, và kiểm toán nội bộ hỏi "ai duyệt model credit-risk-v14 và dựa trên số liệu nào" nhưng không ai trả lời được.

Viết `starter/DESIGN.md`, giữ các heading `## 1.` tới `## 6.`, không còn chữ `TODO`:

| Phần | Yêu cầu kiểm tự động |
| --- | --- |
| 1. Phân tầng rủi ro | Ít nhất 300 ký tự văn xuôi (không tính bảng) và bảng đủ 4 cột (`Đội`, `Tầng`, `Lý do`, `Hậu quả khi sai`) có đúng 3 dòng cho `credit-risk`, `recsys`, `research`; `Tầng` là `cao`, `trung bình` hoặc `thấp`; `credit-risk` là `cao`, `research` là `thấp` |
| 2. Ma trận kiểm soát | Bảng có cột `Kiểm soát`, `Cao`, `Trung bình`, `Thấp`; ít nhất 6 dòng, không ô trống; ít nhất 4 dòng có nội dung ở `Cao` khác `Thấp`; có dòng về duyệt mà ô `Cao` nói rõ hai người (`hai người` hoặc `2 người`) |
| 3. Tách quyền | Ít nhất 4 gạch đầu dòng; có nêu người train không được tự duyệt model của mình (cụm `tự duyệt`) |
| 4. Audit và lưu giữ | Nhắc `audit log`, `hash` và `retention`, kèm con số lưu giữ có đơn vị (`năm`, `tháng` hoặc `ngày`); số năm cho tầng cao không dưới 5 |
| 5. Luồng duyệt | Khối ` ```mermaid ` có ít nhất 6 cạnh (`-->`) và có chữ `rollback` |
| 6. Chi phí và rủi ro | Ít nhất 4 gạch đầu dòng, nhắc `ngân sách` hoặc `budget` |

Test chỉ kiểm khung và các luật trên; một test khác đưa một thiết kế yếu vào cùng bộ kiểm tra và đòi nó bị bắt. Nội dung chấm bằng rubric trong `solutions/advanced/01-governance-three-teams/SOLUTION.md`; đọc rubric **sau** khi viết xong.

## Tiêu chí đạt

- `uv run pytest tracks/mlops/modules/12-ml-platform-governance/exercises/advanced/01-governance-three-teams -q` pass.
- Tự chấm đạt ít nhất 70/100 điểm rubric.
- Mỗi kiểm soát bắt buộc truy được về một yêu cầu trong đề (thanh tra 5 năm, sự cố đổi alias nhầm, hai kỹ sư nền tảng).
- Phần nào là "bị chặn bằng cơ chế" khác "quy ước" được nói rõ; và nêu cái giá của kiểm soát (thời gian chờ duyệt, người phải trực).

## Gợi ý

### Gợi ý 1

Bắt đầu từ hậu quả khi sai, không từ công cụ: đội nào mà một model sai làm mất tiền, vi phạm luật, hay chỉ mất thời gian? Kiểm soát chỉ đáng giá khi rẻ hơn hậu quả; đặt gánh nặng ở `research` bằng gánh nặng ở `credit-risk` là sai thiết kế dù an toàn.

### Gợi ý 2

Với mỗi kiểm soát hỏi "ai thực thi và nếu người đó bỏ qua thì sao": quy ước trong wiki khác với quyền registry khác với một bước CI không thể bỏ qua. Audit log chỉ đáng tin khi người được audit không ghi được vào nó (bài hash chain).

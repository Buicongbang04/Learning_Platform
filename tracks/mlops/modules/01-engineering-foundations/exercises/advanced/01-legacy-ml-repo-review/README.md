---
title: Review và lên kế hoạch cứu một repo ML cũ
level: advanced
services: []
files:
  - path: starter/legacy-repo.md
    note: Cây thư mục, số liệu git và trích đoạn của repo cần review
  - path: starter/review.md
    note: Điền 4 mục
  - path: tests/test_review.py
    note: Kiểm cấu trúc, không chấm nội dung
run:
  - uv run pytest tracks/mlops/modules/01-engineering-foundations/exercises/advanced/01-legacy-ml-repo-review -q
---

## Mục tiêu

Đọc một repo ML bạn thừa kế và đưa ra bản review có thứ tự ưu tiên cùng kế hoạch refactor mà mỗi bước kiểm được, thay vì "viết lại từ đầu".

## Đề bài

Bạn vừa nhận `eta-service-v0` (mô tả đầy đủ trong `starter/legacy-repo.md`): đang phục vụ một API, người viết đã nghỉ, không ai nhớ vì sao mọi thứ như hiện tại.
Trưởng nhóm cho bạn một tuần. Điền `starter/review.md`:

1. **Phát hiện**: ít nhất 8 mục, mỗi mục bắt đầu bằng mức độ `[P0]` (xử lý ngay), `[P1]` hoặc `[P2]`, nêu tệp cụ thể, triệu chứng và hậu quả.
2. **Kế hoạch refactor**: ít nhất 5 bước đánh số, mỗi bước kết thúc bằng `Kiểm:` mô tả cách biết bước đó đúng.
3. **Thứ tự và lý do**: vì sao theo thứ tự đó, bước nào chặn bước nào, việc nào làm trong ngày hôm nay.
4. **Không làm (và vì sao)**: ít nhất 2 việc bạn cố ý không làm lúc này.

Test chỉ kiểm cấu trúc: đúng bốn heading `## ` như template theo thứ tự, không còn `TODO`; mỗi phát hiện dài ít nhất 60 ký tự; phần thứ tự và lý do dài ít nhất 300 ký tự; phần không làm có ít nhất 2 gạch đầu dòng; dòng nói về mật khẩu trong `config.py` (chứa một trong các chữ `password`, `mật khẩu`, `secret`, `DB_URL`, `lộ`) mang mức `[P0]`; mỗi phát hiện là một dòng bắt đầu bằng `-` hoặc `*` rồi tới `[P0]`, `[P1]` hoặc `[P2]`, có ít nhất 8 dòng như vậy và phần phát hiện nhắc tới ít nhất 6 vị trí trong repo (tệp hoặc thư mục); kế hoạch có ít nhất 5 dòng bắt đầu bằng `1.`, `2.`... và mỗi dòng chứa `Kiểm:`. Chất lượng nội dung chấm theo rubric trong `SOLUTION.md`.

## Tiêu chí đạt

- Phát hiện cụ thể theo tệp, có mức độ, có ít nhất một `[P0]`, bí mật trong `config.py` được xếp `[P0]`.
- Kế hoạch có thứ tự bảo vệ được người học: an toàn và khả năng quay lui trước, refactor sau, có test trước khi sửa.
- Mỗi bước có cách kiểm chạy được.
- Phần "không làm" có lý do thực tế.

## Gợi ý

### Gợi ý 1

Hỏi: nếu hôm nay server chết, bạn dựng lại model đang chạy được không? Nếu mật khẩu này lộ, ai đăng nhập được gì? Hai câu hỏi đó thường ra P0.

### Gợi ý 2

Trước khi sửa code cũ, bạn cần một cách chứng minh hành vi không đổi. Cái gì đóng vai đó khi repo không có test?

### Gợi ý 3

Đừng bắt đầu từ cái dễ thấy nhất (cấu trúc thư mục) mà từ cái đắt nhất nếu sai (bí mật, khả năng quay lui model).

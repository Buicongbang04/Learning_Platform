---
title: Trắc nghiệm phỏng vấn SRE và DevOps
level: advanced
services: []
files: []
run: []
---

## Mục tiêu

Luyện cách trả lời các câu phỏng vấn SRE/DevOps hay gặp: chọn SLI, tính burn rate, chính sách error budget, vai trò khi có sự cố,
postmortem không đổ lỗi, chaos, capacity, FinOps, bảo mật pipeline, toil và câu hỏi hành vi.

## Đề bài

Bài này không có code. Làm 12 câu trắc nghiệm trong app (card **Trắc nghiệm** bên dưới): 10 câu chọn một đáp án, 2 câu chọn mọi đáp án
đúng. Đọc toàn bộ lý thuyết và `interview.md` của module trước khi làm.

Với mỗi câu, trả lời như trước người phỏng vấn:

1. **Đo cái gì?** Thứ khách cảm nhận hay thứ máy móc báo?
2. **Con số nào?** Viết phép tính ra (burn rate, budget, Little) trước khi chọn.
3. **Ai quyết, dựa trên gì?** Quy tắc đã thống nhất trước hay cảm tính lúc sự cố?
4. **Hệ thống hay con người?** Câu trả lời tốt sửa hệ thống để lỗi người không thành sự cố.

Sau khi nộp, đọc `SOLUTION.md`: mỗi câu có lời giải thích và cách mở rộng câu trả lời khi người phỏng vấn hỏi tiếp.

## Tiêu chí đạt

- Đúng ít nhất 10/12 câu.
- Với mỗi câu, nói thành lời được câu trả lời trong 2 phút như đang phỏng vấn, kèm một ví dụ từ các bài của module.
- Nhấn **Đánh dấu hoàn thành** sau khi đã đọc lời giải.

## Gợi ý

### Gợi ý 1

Burn rate là tỉ lệ lỗi chia phần được phép lỗi. Phần budget tiêu bằng burn rate nhân thời gian chia độ dài cửa sổ SLO.

### Gợi ý 2

Định luật Little: số việc đang xử lý bằng tốc độ đến nhân thời gian ở lại. Nhớ đổi mili giây sang giây.

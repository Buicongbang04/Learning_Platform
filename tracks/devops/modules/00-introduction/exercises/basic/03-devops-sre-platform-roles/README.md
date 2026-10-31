---
title: CALMS, SRE và Platform Engineering qua tình huống tổ chức
level: basic
services: []
files: []
run: []
---

## Mục tiêu

Phân biệt được DevOps (văn hoá và cách làm), SRE (một cách hiện thực DevOps bằng kỹ thuật phần mềm, SLO và error
budget) và Platform Engineering (sản phẩm nội bộ cho developer tự phục vụ) qua những tình huống tổ chức hay gặp, và
nhận ra các anti-pattern phổ biến như "DevOps team" làm silo mới hay biến metric thành chỉ tiêu.

## Đề bài

Bài này không có code. Làm 10 câu trắc nghiệm trong app (card **Trắc nghiệm** bên dưới):

- 9 câu chọn một đáp án về CALMS, error budget, golden path, postmortem blameless, batch size, toil và định nghĩa
  failed change của DORA.
- 1 câu chọn nhiều đáp án: dấu hiệu một tổ chức chỉ "làm DevOps" trên danh nghĩa.

Mỗi câu đặt bạn vào vai người được hỏi ý kiến trong một cuộc họp. Hãy chọn phương án mà bạn sẵn sàng bảo vệ trước
CTO, không phải phương án nghe an toàn nhất.

## Tiêu chí đạt

- Trả lời đúng ít nhất 8/10 câu.
- Với mỗi câu, nói được trụ cột CALMS hoặc nguyên tắc SRE/Platform Engineering mà câu đó kiểm.
- Nhấn **Đánh dấu hoàn thành** sau khi đã đọc lời giải.

## Gợi ý

### Gợi ý 1

Nếu một phương án thêm một bước duyệt, thêm một người, hoặc thêm một nhóm trung gian giữa dev và production, hãy
nghi ngờ nó. DevOps giảm số lần chuyền tay; SRE và Platform Engineering là cách làm việc đó ở quy mô lớn.

### Gợi ý 2

Phân biệt "đo để học" và "đo để thưởng phạt". Phần 3 của lý thuyết có danh sách cách DORA metrics bị bóp méo khi
thành KPI. Với toil, đi lần lượt qua năm tính chất trong đề: việc nào thiếu một tính chất thì không phải toil.

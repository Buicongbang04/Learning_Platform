---
title: Chọn công cụ versioning và kiểm dữ liệu theo tình huống
level: basic
services: []
files: []
run: []
---

## Mục tiêu

Chọn đúng công cụ (DVC, lakeFS, Delta Lake, Pandera, Great Expectations) từ ràng buộc thật của đội, thay vì dùng DVC
hay Pandera cho mọi thứ.

## Đề bài

Bài này không có code. Làm 8 câu trắc nghiệm trong app (card **Trắc nghiệm** bên dưới): 7 câu chọn một đáp án, câu cuối chọn mọi
đáp án đúng. Các câu đi qua: Git giữ gì khi có DVC, `dvc.lock`, khi nào cần lakeFS hay Delta thay vì DVC, Pandera so với Great
Expectations, ai sở hữu data contract, và cách đọc một lần `dvc repro` bỏ qua stage.

Trước khi chọn, với mỗi tình huống tự hỏi:

1. Dữ liệu là vài tệp trong một dự án ML hay một data lake dùng chung nhiều đội ghi?
2. Ai đổi dữ liệu và có cần giao dịch (atomic commit) hay chỉ cần tái lập một lần train?
3. Kiểm tra chạy ở đâu: trong code Python của pipeline hay như một bước kiểm chất lượng độc lập có báo cáo?

## Tiêu chí đạt

- Trả lời đúng ít nhất 6/8 câu.
- Với mỗi câu sai, nói lại được ràng buộc quyết định và điều kiện để phương án bạn chọn trở thành đúng.
- Nhấn **Đánh dấu hoàn thành** sau khi đã đọc lời giải.

## Gợi ý

### Gợi ý 1

DVC giải bài toán "mỗi commit Git trỏ tới đúng một phiên bản dữ liệu của dự án này". Nếu bài toán là "nhiều job cùng ghi vào
một data lake và cần rollback cả lake", công cụ phải sống ở tầng lưu trữ.

### Gợi ý 2

Phân biệt *hợp đồng* (schema, ngữ nghĩa, SLA, người sở hữu) với *công cụ thực thi hợp đồng* (Pandera, GE, test dbt).

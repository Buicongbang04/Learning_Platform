---
title: Chọn công cụ MLOps theo tình huống
level: basic
services: []
files: []
run: []
---

## Mục tiêu

Chọn công cụ và mức đầu tư theo ràng buộc thật (đội mấy người, đã có gì, tải bao nhiêu), thay vì chọn "stack chuẩn".

## Đề bài

Bài không có code. Làm 8 câu trắc nghiệm trong app (card **Trắc nghiệm**): 7 câu chọn một đáp án, 1 câu chọn mọi đáp án
đúng. Các tình huống đi qua tracking, data versioning, orchestrator khi đã có Airflow, serving mức nhỏ, monitoring,
training-serving skew, CI cho ML và cám dỗ over-engineering.

Trước mỗi câu tự hỏi: vấn đề cụ thể đang đau là gì, công cụ nào giải đúng vấn đề đó, và cái giá vận hành của nó là gì?

## Tiêu chí đạt

- Đúng ít nhất 6/8 câu.
- Với mỗi câu sai, nói lại được ràng buộc quyết định và điều kiện để phương án bạn chọn trở thành đúng.
- Nhấn **Đánh dấu hoàn thành** sau khi đọc lời giải.

## Gợi ý

### Gợi ý 1

Phương án đúng thường là cái nhỏ nhất giải được vấn đề đang có và có đường nâng cấp, không phải cái nhiều tính năng nhất.

### Gợi ý 2

Phân biệt công cụ theo vấn đề nó giải: versioning dữ liệu (DVC), orchestration (Airflow, Prefect), tracking (MLflow),
skew giữa training và serving (feature store), quan sát service (Prometheus, Grafana).

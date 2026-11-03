---
title: Model card sinh tự động và linter cho model card
level: basic
services: []
files:
  - path: starter/modelcard.py
    note: 3 hàm TODO
  - path: tests/test_modelcard.py
    note: Không sửa
run:
  - uv run pytest tracks/mlops/modules/04-tracking-registry/exercises/basic/03-model-card -q
---

## Mục tiêu

Model card chỉ có ích khi nó được sinh ra từ dữ liệu của run (không ai chép tay) và bị kiểm trong CI (không ai quên điền).
Bạn viết cả hai nửa: bộ sinh và linter, và hiểu vì sao phần "Hạn chế" là phần không được để trống.

## Đề bài

Trong `starter/modelcard.py`:

1. `worst_slices(slices, overall_mae, k=3, min_n=100)`: k slice tệ nhất so với MAE tổng, dạng `(tên, tỉ lệ)`, tỉ lệ
   giảm dần, bỏ slice có `n < min_n`.
2. `build_model_card(info) -> str`: Markdown với dòng đầu `# Model card: <name> v<version>` rồi đúng năm phần theo
   `REQUIRED_HEADINGS`. Phần Hiệu năng có đúng một bảng, bảng slice, với cột `Slice | n | MAE (giây) | So với MAE tổng`, slice tệ nhất
   đứng đầu, tỉ lệ viết dạng `1.65x`. Bảng liệt kê mọi slice (kể cả slice nhỏ, nhưng sắp xếp theo cùng thứ tự).
   `limitations` rỗng thì `ValueError`.
3. `card_problems(text) -> list[str]`: linter cho CI, trả mọi lỗi tìm thấy (không dừng ở lỗi đầu tiên): thiếu heading,
   còn `TODO`, phần Hạn chế không có gạch đầu dòng, phần Hiệu năng không có bảng, phần Lineage thiếu git commit 40 ký tự
   hex. Test tìm từ khoá trong thông điệp lỗi: lỗi thiếu heading chứa tên heading thiếu (ví dụ `Lineage`); lỗi còn `TODO`
   chứa chữ `TODO`; lỗi Hạn chế chứa cụm `gạch đầu dòng`; lỗi Hiệu năng chứa chữ `bảng`; lỗi Lineage chứa `git_commit`.

## Tiêu chí đạt

- Card sinh ra đi qua chính linter của bạn (`card_problems(...) == []`).
- Từng loại lỗi trong linter được phát hiện độc lập; card gần rỗng báo từ 5 lỗi trở lên cùng lúc.
- Thứ tự slice trong bảng là thứ tự "tệ nhất trước", không phải thứ tự trong dict đầu vào.

## Gợi ý

### Gợi ý 1

Cắt một phần của Markdown bằng regex `^## Tên\s*$(.*?)(?=^## |\Z)` với cờ `re.M | re.S`. Dùng lại hàm này cho cả bốn
phép kiểm trong linter.

### Gợi ý 2

Bảng Markdown hợp lệ có dòng tiêu đề `| a | b |` ngay sau là dòng phân cách `| --- | --- |`. Kiểm hai dòng liên tiếp đó,
đừng chỉ kiểm có ký tự `|`.

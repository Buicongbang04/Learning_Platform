---
title: Phân vai RACI cho đội ML năm vai trò
level: advanced
services: []
files:
  - path: starter/raci.yaml
    note: Điền ma trận và ba đoạn lý do
  - path: tests/test_raci.py
    note: Không sửa; kiểm nguyên tắc cơ học
run:
  - uv run pytest tracks/mlops/modules/00-introduction/exercises/advanced/02-raci-ml-team -q
---

## Mục tiêu

Phân công ai làm, ai chịu trách nhiệm cuối cho từng hoạt động vòng đời ML trong một đội thật, đặc biệt ở ranh giới giữa
DS, MLOps, DE và backend nơi sự cố hay rơi vào khoảng trống.

## Đề bài

Đội gồm `ds`, `mlops`, `de`, `backend`, `pm`. Điền `starter/raci.yaml` cho 10 hoạt động theo thang R/A/AR/C/I/-.

Ràng buộc test kiểm: mỗi hoạt động đúng **một** A và ít nhất một R; `ds`, `mlops`, `de`, `backend` mỗi vai trò là A của ít
nhất một hoạt động và không vai trò nào là A của quá nửa; người A của `promotion-gate` không được là người R của `train-model`;
`de` là A của `data-contract-change` và `ds` không được để `-`; `model-quality-oncall` có cả `ds` và `mlops`.

Sau đó viết ba đoạn lý do (`decisions`, mỗi đoạn tối thiểu 80 ký tự) cho `promotion-gate`, `model-quality-oncall` và
`retrain-vs-rollback-decision`: vì sao phân công vậy và đánh đổi nào bạn chấp nhận. Rubric trong `SOLUTION.md`.

## Tiêu chí đạt

- Test xanh.
- Mỗi lý do nêu rõ cái giá của lựa chọn.
- Tự chấm rubric đạt từ 8/12.

## Gợi ý

### Gợi ý 1

Hai câu hỏi cho mỗi dòng: nếu việc này hỏng lúc 3 giờ sáng thì ai bị gọi, và ai có quyền quyết định cuối?

### Gợi ý 2

Quyền duyệt tách khỏi quyền làm. Quyết định có hệ quả tiền bạc thuộc người sở hữu sản phẩm, còn người kỹ thuật cung cấp số liệu.

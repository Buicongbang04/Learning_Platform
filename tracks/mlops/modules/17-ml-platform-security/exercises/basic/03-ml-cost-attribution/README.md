---
title: FinOps cho ML - cost attribution theo đội và model, idle, showback, chargeback
level: basic
services: []
files:
  - path: starter/cost.py
    note: 6 hàm TODO
  - path: quiz.yaml
    note: 5 câu FinOps và build vs buy
  - path: tests/test_cost.py
    note: Không sửa
run:
  - uv run pytest tracks/mlops/modules/17-ml-platform-security/exercises/basic/03-ml-cost-attribution -q
---

## Mục tiêu

Biến log sử dụng của cụm dùng chung thành báo cáo "đội nào, model nào tốn bao nhiêu", gồm cả phần mà không ai muốn nhận: năng lực
đã cấp nhưng nhàn rỗi và tài nguyên không gắn nhãn. Đây là nền của showback (cho đội thấy) và chargeback (trừ vào ngân sách đội).
Sau đó làm phần trắc nghiệm về FinOps và build vs buy.

## Đề bài

Log sử dụng là CSV, mỗi dòng là một workload trong một ngày:

| Cột | Ý nghĩa |
| --- | --- |
| `date` | ngày, `YYYY-MM-DD` |
| `namespace` | namespace Kubernetes của workload |
| `model` | nhãn `model` của pod; có thể rỗng (không gắn nhãn) |
| `workload` | `train`, `serve` hoặc `notebook` |
| `cpu_hours`, `gpu_hours`, `mem_gb_hours` | lượng tài nguyên **đã xin** (request) trong ngày |

Cấu hình là dict:

```python
{"prices": {"cpu_hour": 0.031, "gpu_hour": 0.90, "mem_gb_hour": 0.004},
 "capacity": {"cpu_hours": ..., "gpu_hours": ..., "mem_gb_hours": ...},
 "namespaces": {"eta-prod": "eta", "eta-train": "eta", "pricing": "pricing", ...},
 "cost_centers": {"eta": "CC-1001", "pricing": "CC-2041", ...}}
```

`capacity` là năng lực đã cấp (đã trả tiền) trong cả kỳ. Điền 6 hàm trong `starter/cost.py`:

- `load_usage(path)`: list dict cùng khoá với CSV; ba cột tài nguyên là `float`; `model` rỗng (sau khi bỏ khoảng trắng) thành `None`.
- `row_cost(row, prices)`: `cpu_hours x cpu_hour + gpu_hours x gpu_hour + mem_gb_hours x mem_gb_hour`.
- `cost_by_model(rows, config)`: dict `{(team, model): chi phí}`. Đội lấy từ `namespaces`; namespace không có trong bảng thuộc đội
  `"unallocated"`; model `None` thành `"unlabelled"`.
- `idle_cost(rows, config)`: với **từng loại tài nguyên**, `max(0, capacity - tổng đã dùng) x giá`, rồi cộng lại. Một loại dùng vượt
  năng lực không được bù cho loại khác.
- `showback(rows, config)`: dict `{team: {"direct", "idle_share", "total"}}` cho mọi đội có chi phí (kể cả `"unallocated"`). Chi phí
  idle chia cho các đội **đã biết** theo tỉ lệ chi phí trực tiếp; `"unallocated"` có `idle_share = 0`. `total = direct + idle_share`.
  Khi không dùng vượt năng lực, tổng `total` của mọi đội bằng đúng chi phí năng lực đã cấp (test kiểm).
- `chargeback(rows, config)`: list `{"cost_center", "team", "amount"}`, một dòng mỗi đội trong showback, `amount = round(total, 2)`,
  `cost_center` lấy từ `cost_centers`, riêng `"unallocated"` là `"UNALLOCATED"`; sắp theo `cost_center`.

Test sinh 30 ngày log cho 5 đội và một namespace không gắn đội, rồi tính lại mọi con số bằng pandas.

Phần trắc nghiệm `quiz.yaml`: 5 câu, đáp án ở `solutions/.../quiz-answers.yaml`.

## Tiêu chí đạt

- `uv run pytest tracks/mlops/modules/17-ml-platform-security/exercises/basic/03-ml-cost-attribution -q` pass.
- Trả lời đúng ít nhất 4/5 câu trắc nghiệm.
- Bạn giải thích được vì sao báo cáo phải có dòng `UNALLOCATED` thay vì chia đều hay bỏ đi, và vì sao chi phí tính theo request chứ không
  theo mức dùng thực tế.

## Gợi ý

### Gợi ý 1

`csv.DictReader` đọc mọi cột thành chuỗi. `collections.defaultdict(float)` gọn cho các phép cộng dồn theo khoá.

### Gợi ý 2

`showback` dựng trên `cost_by_model` (cộng theo đội) và `idle_cost`. Mẫu số chia idle chỉ gồm chi phí trực tiếp của các đội đã biết.

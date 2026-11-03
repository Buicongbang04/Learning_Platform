---
title: Chính sách continuous training - khi nào retrain, khi nào không
level: advanced
services: []
files:
  - path: starter/POLICY.md
    note: Chính sách, điền mọi TODO
  - path: starter/decisions.yaml
    note: Quyết định cho 7 tình huống
  - path: tests/fixtures/scenarios.yaml
    note: Chính sách hiện hành và 7 tình huống, đọc trước
  - path: tests/test_policy.py
    note: Không sửa
run:
  - uv run pytest tracks/mlops/modules/05-training-pipelines/exercises/advanced/01-ct-trigger-policy -q
---

## Mục tiêu

Viết chính sách continuous training cho dịch vụ ETA và áp nó vào các tình huống mà phản xạ "có trigger thì retrain" cho kết quả
sai. Phần quyết định kiểm bằng máy; phần chính sách chấm bằng rubric.

## Đề bài

Dịch vụ ETA có ba loại trigger: lịch (tuần/tháng), dữ liệu mới (hash đổi), cảnh báo (drift hoặc hiệu năng). `tests/fixtures/scenarios.yaml`
chứa chính sách hiện hành (SLO, tỉ lệ nhãn tối thiểu, tuổi tối đa của model, ngưỡng chất lượng dữ liệu, cooldown) và 7 tình
huống C1 đến C7 kèm số liệu. Mỗi tình huống chọn một trong ba hành động:

- `retrain`: chạy pipeline train (rồi qua cổng promotion);
- `skip`: bỏ lượt này, ghi lý do;
- `investigate`: dừng trigger, người kiểm tra nguồn dữ liệu hoặc pipeline trước.

Việc cần làm:

1. `starter/decisions.yaml`: mỗi mục có `decision` và `reasons` (danh sách, mỗi lý do từ 10 ký tự trở lên, nêu số liệu). Test kiểm
   `decision` đúng theo chính sách và kiểm lý do nhắc đúng từ khoá của yếu tố quyết định (ví dụ `MAE`, `PSI`, `SLO`, `null`,
   `tuổi`, `nhãn`, `cooldown`; mỗi tình huống một từ, nằm sẵn trong đề).
2. `starter/POLICY.md`: chính sách bạn đề xuất, giữ các heading `## 1.` tới `## 5.`, không còn `TODO`:

| Phần | Yêu cầu kiểm tự động |
| --- | --- |
| 1. Nguyên tắc | Có mặt (nội dung chấm bằng rubric) |
| 2. Luồng quyết định | Khối ` ```mermaid ` có ít nhất 4 cạnh (`-->`, `->>` hoặc `---`) |
| 3. Các loại trigger | Bảng ít nhất 4 dòng đủ 3 cột (`Trigger`, `Chạy train khi`, `Bỏ qua khi`) |
| 4. Guardrail | Ít nhất 3 gạch đầu dòng, có nhắc `cooldown` và `nhãn` |
| 5. Quan sát và hậu kiểm | Ít nhất 3 gạch đầu dòng |

Test chỉ kiểm quyết định, từ khoá và khung cấu trúc; một test khác chứng minh bộ kiểm tra bắt được kiểu trả lời "trigger nào cũng
retrain". Nội dung chấm bằng rubric trong `solutions/advanced/01-ct-trigger-policy/SOLUTION.md`; đọc rubric **sau** khi viết xong.

## Tiêu chí đạt

- `uv run pytest tracks/mlops/modules/05-training-pipelines/exercises/advanced/01-ct-trigger-policy -q` pass.
- Tự chấm đạt ít nhất 70/100 điểm rubric.
- Với mỗi tình huống `skip` hoặc `investigate`, nêu được điều gì sẽ đổi quyết định thành `retrain` (điều kiện cụ thể).

## Gợi ý

### Gợi ý 1

Với mỗi tình huống, hỏi theo thứ tự: dữ liệu có đáng tin không (nếu không, đừng train trên nó), hiệu năng **thật** (trên nhãn đã
về) có xấu đi không, đã đủ nhãn mới chưa, và lần retrain gần nhất có giải quyết được vấn đề không.

### Gợi ý 2

Một alert chỉ cho bạn biết "có gì đó khác", không cho biết "model sai". Retrain trả lời câu hỏi thứ hai bằng cách thay model,
không phải bằng cách tìm hiểu; hãy viết ra những lần thay model không thể sửa được vấn đề.

---
title: Viết chính sách promotion cho ETA và áp dụng vào 8 tình huống
level: advanced
services: []
files:
  - path: starter/POLICY.md
    note: Chính sách, điền mọi TODO
  - path: starter/decisions.yaml
    note: Quyết định cho 8 tình huống
  - path: tests/fixtures/scenarios.yaml
    note: Số đo của champion và 8 challenger, đọc trước
  - path: tests/test_policy.py
    note: Không sửa
run:
  - uv run pytest tracks/mlops/modules/04-tracking-registry/exercises/advanced/01-promotion-policy-eta -q
---

## Mục tiêu

Viết chính sách promotion cho một dịch vụ thật (ETA taxi NYC) và áp nó vào các ca khó mà người ta hay quyết định theo cảm
tính. Phần quyết định kiểm bằng máy; phần chính sách chấm bằng rubric.

## Đề bài

Dịch vụ ETA đang chạy champion (version 5). Đội nhận được 8 challenger (`tests/fixtures/scenarios.yaml`: số đo trên cùng tập
đánh giá, kèm câu chuyện và lineage). Chính sách hiện hành (cũng nằm ở đầu tệp đó):

- MAE tổng của challenger cải thiện ít nhất 1% so với champion;
- mọi slice của champion có cỡ mẫu (cả hai bên) từ 200 trở lên không được xấu đi quá 5%; slice nhỏ hơn bị bỏ qua; slice
  champion có mà challenger không báo cáo thì không kiểm được và tính là trượt;
- latency p95 không quá 1.2 lần champion;
- lineage: `git_dirty` phải là `false`, có `data_version` và `git_commit`.

Việc cần làm:

1. `starter/decisions.yaml`: mỗi tình huống có `decision` (`promote` hoặc `reject`) và `reasons` (danh sách lý do, mỗi lý do ít
   nhất 10 ký tự, nêu đúng thứ làm quyết định đổi chiều: tên slice, `latency`, `MAE`, `git_dirty`…). Test kiểm quyết định
   theo chính sách và kiểm lý do có nhắc từ khoá của từng ca trượt.
2. `starter/POLICY.md`: chính sách bạn đề xuất cho đội (có thể giữ nguyên ngưỡng hiện hành, nhưng phải biện minh), giữ
   các heading `## 1.` tới `## 5.`, không còn `TODO`:

| Phần | Yêu cầu kiểm tự động |
| --- | --- |
| 1. Phạm vi và nguyên tắc | Có mặt (nội dung chấm bằng rubric) |
| 2. Quy trình | Một khối ` ```mermaid ` có ít nhất 4 cạnh (`-->`, `->>` hoặc `---`) |
| 3. Slice bảo vệ | Bảng ít nhất 4 slice đủ 3 cột (`Slice`, `Vì sao quan trọng`, `Dung sai`) |
| 4. Ngoại lệ và người duyệt | Ít nhất 3 gạch đầu dòng |
| 5. Rollback và hậu kiểm | Ít nhất 3 gạch đầu dòng |

Nội dung chấm bằng rubric trong `solutions/advanced/01-promotion-policy-eta/SOLUTION.md`; đọc rubric **sau** khi viết xong.

## Tiêu chí đạt

- `uv run pytest tracks/mlops/modules/04-tracking-registry/exercises/advanced/01-promotion-policy-eta -q` pass.
- Tự chấm đạt ít nhất 70/100 điểm rubric.
- Với ca có quyết định gây tranh cãi (S3, S8), giải thích trong `POLICY.md` hoặc `reasons` vì sao chính sách làm vậy và đánh
  đổi của nó.

## Gợi ý

### Gợi ý 1

Duyệt từng ca theo đúng thứ tự bốn điều kiện, ghi lại điều kiện nào trượt rồi mới quyết. Ca nào trượt hai điều kiện thì liệt
kê cả hai trong `reasons`.

### Gợi ý 2

Hỏi cho mỗi slice trong phần 3: nếu slice này xấu đi 20% thì ai gọi điện, và nó chiếm bao nhiêu phần trăm chuyến hoặc phần
trăm doanh thu. Đó là lý do để bảo vệ nó, hoặc để không bảo vệ.

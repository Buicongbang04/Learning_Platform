---
title: Thiết kế nền tảng feature cho 3 model taxi
level: advanced
services: []
files:
  - path: starter/DESIGN.md
    note: Khung thiết kế, điền mọi TODO
  - path: tests/fixtures/DESIGN.bad.md
    note: Ví dụ thiết kế yếu, test dùng để kiểm bộ kiểm tra
  - path: tests/test_design.py
    note: Không sửa
run:
  - uv run pytest tracks/mlops/modules/06-feature-stores/exercises/advanced/01-feature-platform-design -q
---

## Mục tiêu

Thiết kế cách một công ty đưa feature dùng chung vào sản xuất mà không có skew âm thầm và không tự làm mình kiệt sức vận hành.

## Đề bài

Công ty taxi có ba model: ETA (online, dưới 100 ms, cần tốc độ trung bình theo zone), giá cước động (online, cần số yêu cầu đang
chờ theo zone, tươi trong 5 phút) và phát hiện gian lận (chạy theo lô mỗi đêm, cần lịch sử 30 ngày của tài xế). Ba nhóm đang tự tính
lại cùng một số feature và lệch nhau; ETA từng lệch giữa train và serve hai tuần không ai biết. Đội nền tảng 2 người; hạ tầng
có Postgres, object storage, Redis; dữ liệu về kho theo lô mỗi giờ, chưa có streaming.

Viết `starter/DESIGN.md`, giữ các heading `## 1.` tới `## 6.`, không còn `TODO`:

| Phần | Yêu cầu kiểm tự động |
| --- | --- |
| 1. Bối cảnh và giả định | Ít nhất 300 ký tự (không tính bảng và khối code) |
| 2. Kiến trúc | Khối ` ```mermaid ` có ít nhất 6 cạnh (`-->`, `->>` hoặc `---`) |
| 3. Danh mục feature | Bảng ít nhất 6 feature đủ 3 cột (`Feature`, `Nguồn và cách tính`, `Cần online?`); cột 3 bắt đầu bằng `có` hoặc `không`, và có ít nhất một dòng mỗi loại |
| 4. Chống training-serving skew | Ít nhất 4 gạch đầu dòng, có nhắc `point-in-time` và `parity` |
| 5. Vận hành | Ít nhất 4 gạch đầu dòng, có nhắc `materialize`, `TTL` và `backfill` |
| 6. Rủi ro và việc còn mở | Ít nhất 3 gạch đầu dòng |

Test chỉ kiểm khung ở trên; một test khác đưa một thiết kế yếu vào cùng bộ kiểm tra và đòi nó bị bắt. Nội dung chấm bằng rubric
trong `solutions/advanced/01-feature-platform-design/SOLUTION.md`; đọc rubric **sau** khi viết xong.

## Tiêu chí đạt

- `uv run pytest tracks/mlops/modules/06-feature-stores/exercises/advanced/01-feature-platform-design -q` pass.
- Tự chấm đạt ít nhất 70/100 điểm rubric.
- Mỗi quyết định truy được về một yêu cầu trong đề (độ tươi 5 phút, đội 2 người, lô theo giờ).
- Nêu điều kiện cụ thể để chuyển sang dịch vụ quản lý hoặc streaming, không chỉ "khi lớn hơn".

## Gợi ý

### Gợi ý 1

Với từng feature hỏi: ai cần, độ tươi bao nhiêu, tính ở đâu, và nếu nó sai thì model nào hỏng. Feature chỉ cần cho job theo
lô không nên chiếm chỗ trong online store.

### Gợi ý 2

Hãy nghĩ tới "feature 5 phút" trước: nó có tương thích với lô theo giờ không? Thiết kế trung thực nói rõ chỗ nó chưa giải được.

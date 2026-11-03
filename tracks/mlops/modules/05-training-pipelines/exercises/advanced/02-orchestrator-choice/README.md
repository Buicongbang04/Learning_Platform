---
title: Chọn orchestrator cho pipeline training của một nhóm có ràng buộc thật
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
  - uv run pytest tracks/mlops/modules/05-training-pipelines/exercises/advanced/02-orchestrator-choice -q
---

## Mục tiêu

Chọn công cụ orchestration bằng ràng buộc và điều bạn chấp nhận mất, không bằng sở thích; và viết ra điều kiện cụ thể để đổi lại
quyết định.

## Đề bài

Nhóm của bạn có 4 Data Scientist và 2 Data Engineer. Hôm nay: 6 model train hằng tuần, batch scoring hằng ngày, chạy trên một máy
ảo bằng Docker Compose; Kubernetes dự kiến sau khoảng 12 tháng. Nhóm DE đã vận hành Airflow cho ELT (xem module DE
`05-batch-pipelines`). Yêu cầu: retry cho bước đọc dữ liệu, tham số hoá theo tháng, backfill có kiểm soát, chạy thử trên laptop
không cần cụm, không thêm người trực, đội DS không muốn học một DSL riêng.

Viết `starter/DESIGN.md`, giữ các heading `## 1.` tới `## 5.`, không còn chữ `TODO`:

| Phần | Yêu cầu kiểm tự động |
| --- | --- |
| 1. Bối cảnh và ràng buộc | Ít nhất 300 ký tự (không tính bảng và khối code) |
| 2. Kiến trúc | Khối ` ```mermaid ` có ít nhất 5 cạnh (`-->`, `->>` hoặc `---`) |
| 3. So sánh công cụ | Bảng đủ 4 cột (`Công cụ`, `Hợp khi`, `Chi phí vận hành`, `Quyết định`), có dòng cho Prefect, Airflow, Kubeflow, ZenML, Metaflow; cột Quyết định mỗi dòng chứa `chọn`, `loại` hoặc `theo dõi`; **đúng một** dòng `chọn` |
| 4. Quy ước vận hành | Ít nhất 4 gạch đầu dòng, có nhắc `retry`, `backfill`, `idempotent` |
| 5. Rủi ro và điều kiện đổi công cụ | Ít nhất 3 gạch đầu dòng, ít nhất một điều kiện có con số đo được |

Test chỉ kiểm khung ở trên; một test khác đưa một thiết kế yếu vào cùng bộ kiểm tra và đòi nó bị bắt. Nội dung chấm bằng rubric trong
`solutions/advanced/02-orchestrator-choice/SOLUTION.md`; đọc rubric **sau** khi viết xong.

## Tiêu chí đạt

- `uv run pytest tracks/mlops/modules/05-training-pipelines/exercises/advanced/02-orchestrator-choice -q` pass.
- Tự chấm đạt ít nhất 70/100 điểm rubric.
- Mỗi dòng ở phần 3 truy được về một ràng buộc trong đề; công cụ bị loại có lý do cụ thể, không chỉ "nặng".

## Gợi ý

### Gợi ý 1

Bắt đầu từ ba câu hỏi: ai vận hành nó lúc 3 giờ sáng, chạy ở đâu (laptop, VM, Kubernetes, đám mây của ai), và đơn vị công việc
là DAG theo lịch hay "hàm Python có tham số". Mỗi công cụ trả lời ba câu này khác nhau.

### Gợi ý 2

Điều kiện đổi công cụ tốt có dạng "khi X vượt Y" với X đo được (số pipeline, số job cần GPU, giờ sửa hạ tầng mỗi tuần), không
phải "khi lớn hơn". Đó là phần phỏng vấn viên chú ý nhất.

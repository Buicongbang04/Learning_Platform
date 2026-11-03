# Lời giải: chọn orchestrator

Bài Advanced không có đáp án duy nhất. `DESIGN.md` cạnh tệp này là một bản mẫu đã chạy qua test; chấm theo chất lượng lập luận.

## Các quyết định cốt lõi

- **Chọn Prefect 3** vì ràng buộc: Python thuần (không DSL), tham số hoá và backfill tự nhiên (flow là hàm có tham số), chạy được
  trên laptop không cụm, vận hành nhẹ cho nhóm không có người trực riêng. Điều chấp nhận mất: thêm một hệ thống nữa bên cạnh
  Airflow đã có, và hệ sinh thái operator nhỏ hơn.
- **Airflow ở trạng thái "theo dõi", không bị loại.** Nó đã có người vận hành; nếu số pipeline ML lớn hoặc DE muốn gom lịch thì
  chuyển sang là hợp lý. Mô hình DAG hướng lịch làm tham số hoá theo tháng và chạy ad-hoc kém tự nhiên hơn, nhưng làm được.
  Chi tiết ôn Airflow xem DE `05-batch-pipelines`.
- **Kubeflow Pipelines bị loại hôm nay**, không phải mãi mãi: nó đáng giá khi đã có Kubernetes, nhiều job GPU, component container
  hoá; trước đó chi phí vận hành cụm lớn hơn giá trị. Điều kiện quay lại nêu bằng số.
- **ZenML và Metaflow:** ZenML là lớp trừu tượng stack bao ngoài orchestrator, hợp khi muốn đổi backend mà không viết lại pipeline;
  Metaflow hợp khi đã ở AWS (Batch, Step Functions). Chọn "theo dõi" hoặc "loại" đều được nếu lý do bám ràng buộc.

## Điều kiện kiểm tự động chứ không phải thẩm mỹ

Bộ kiểm tra bắt: thiếu công cụ nào đó trong bảng, hai công cụ cùng "chọn", quy ước vận hành không nhắc `idempotent` (backfill an
toàn phụ thuộc vào nó), và điều kiện đổi công cụ không có con số.

## Rubric (100 điểm)

| Tiêu chí | Điểm | Đạt đủ điểm khi |
| --- | --- | --- |
| Quyết định bám ràng buộc | 25 | Mỗi dòng bảng truy được về một ràng buộc trong đề; nêu rõ điều chấp nhận mất |
| So sánh công bằng | 15 | Không mô tả công cụ khác bằng lỗi thời; nêu đúng điểm mạnh thật của Airflow, Kubeflow |
| Quy ước vận hành cho backfill và retry | 20 | Tham số hoá theo tháng logic, idempotent, retry chỉ cho lỗi tạm thời, kiểm soát ghi đè |
| Điều kiện đổi công cụ đo được | 20 | Có ngưỡng số, có người sở hữu việc đo |
| Rủi ro vận hành | 10 | Nêu điểm sự cố mới (server orchestrator), backup, chế độ chạy khi server hỏng |
| Rõ ràng, sơ đồ đúng | 10 | Sơ đồ khớp văn bản, phần ngắn |

Dưới 70: thường vì chọn công cụ vì "phổ biến" hoặc "mạnh nhất" mà không nói ràng buộc nào quyết định.

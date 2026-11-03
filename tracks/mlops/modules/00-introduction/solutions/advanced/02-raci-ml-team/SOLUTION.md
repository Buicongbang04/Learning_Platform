# Lời giải mẫu: RACI cho đội ML 5 vai trò

Không có ma trận duy nhất đúng. Test chỉ kiểm các nguyên tắc cơ học: đúng một A mỗi hoạt động, có người R, không ai
gánh quá nửa số A, ai làm train thì không tự duyệt promote, bên sở hữu dữ liệu là A của thay đổi schema. Phần quan trọng
là ba đoạn lý do trong `decisions`, chấm bằng rubric.

## Bản mẫu

```yaml
activities:
  define-problem-label: {ds: A, mlops: C, de: C, backend: C, pm: R}
  ingest-data: {ds: C, mlops: I, de: AR, backend: I, pm: "-"}
  data-contract-change: {ds: C, mlops: I, de: AR, backend: I, pm: "-"}
  train-model: {ds: AR, mlops: C, de: I, backend: "-", pm: "-"}
  promotion-gate: {ds: R, mlops: A, de: "-", backend: C, pm: I}
  build-serving-ci: {ds: C, mlops: R, de: "-", backend: A, pm: "-"}
  deploy-rollback: {ds: I, mlops: AR, de: "-", backend: R, pm: I}
  monitoring-alerts: {ds: R, mlops: A, de: C, backend: C, pm: I}
  model-quality-oncall: {ds: R, mlops: A, de: C, backend: C, pm: I}
  retrain-vs-rollback-decision: {ds: R, mlops: R, de: C, backend: I, pm: A}
decisions:
  promotion-gate: >
    DS đề xuất tiêu chí và chạy so sánh (R) vì hiểu slice nào quan trọng, nhưng MLOps là A để người train không tự duyệt
    model của mình. Đánh đổi: thêm một bước chuyển giao và có thể chậm một ngày; chấp nhận vì cổng chỉ có giá trị khi
    người giữ cổng độc lập với người viết model.
  model-quality-oncall: >
    Page đầu tiên về MLOps (A) vì họ xử lý được lỗi service và quay lui, DS (R) được gọi khi chỉ số model xấu mà service
    khoẻ. Đánh đổi: DS phải có lịch hỗ trợ ngoài giờ cho loại cảnh báo này; đổi lại tránh MLOps phải tự phán đoán chất lượng
    model lúc 3 giờ sáng.
  retrain-vs-rollback-decision: >
    Quyết định ảnh hưởng tiền và trải nghiệm khách nên PM là A, MLOps và DS cùng R để đưa số liệu (MAE theo slice, thời gian
    quay lui). Đánh đổi: chậm hơn khi PM vắng; giảm bằng quy tắc mặc định (quay lui nếu MAE tăng quá ngưỡng) PM duyệt trước.
```

## Rubric (tổng 12 điểm, đạt từ 8)

| Tiêu chí | Điểm | Đạt khi |
| --- | --- | --- |
| Tách làm và duyệt | 3 | `promotion-gate` có người A độc lập với người train, lý do nói rõ rủi ro nếu gộp |
| Có người trả lời lúc sự cố | 3 | `model-quality-oncall` chỉ rõ ai bị page trước, ai được gọi tiếp, và DS có vai trò thật |
| Quyết định kinh doanh có chủ | 3 | `retrain-vs-rollback-decision` có A chịu trách nhiệm về hệ quả, kèm cách giảm độ chậm (quy tắc mặc định) |
| Nói được đánh đổi | 3 | Mỗi lý do nêu cái giá phải trả, không chỉ "vì họ phù hợp" |

Lỗi hay gặp: đặt MLOps là A của mọi thứ (nút cổ chai và mất quyền sở hữu của DS); để DS tự promote model mình train;
quên `data-contract-change`: DE đổi schema mà DS không được báo là nguồn sự cố phổ biến.

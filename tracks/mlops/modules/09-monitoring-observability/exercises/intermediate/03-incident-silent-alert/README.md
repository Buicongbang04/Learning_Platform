---
title: Sự cố - service lỗi thật mà alert không bao giờ kêu
level: intermediate
services: []
files:
  - path: starter/rules.yml
    note: Rule alert đang chạy ở production, tìm và sửa lỗi
  - path: tests/fixtures/eta_app.py
    note: Bản mô phỏng service ETA đang chạy, test dùng đầu ra /metrics thật của nó
  - path: tests/test_incident.py
    note: Không sửa
run:
  - uv run pytest tracks/mlops/modules/09-monitoring-observability/exercises/intermediate/03-incident-silent-alert -q
---

## Mục tiêu

Chẩn đoán một alert im lặng trong khi người dùng đang gặp lỗi thật, từ triệu chứng, và sửa tối thiểu sao cho alert bắn đúng lúc
mà không đổi ý định ban đầu của nó. Bài này không có lỗi cú pháp để `promtool check rules` bắt hộ.

## Đề bài

Thứ Năm, 14:02, service `eta-service` bắt đầu trả lỗi. Triệu chứng ghi nhận:

- Log của service đầy các dòng `500` và `503`; khoảng 30% yêu cầu tới `/predict` thất bại. Khách hàng gọi điện báo app không báo
  được giờ xe tới.
- Trang `Status > Targets` của Prometheus cho thấy target `eta-service` ở trạng thái `UP`. Truy vấn tay
  `rate(http_requests_total[5m])` vẫn trả số liệu, đồ thị request rate vẽ bình thường.
- Alert `ETAHighErrorRate` ở trạng thái `inactive` suốt 40 phút. Không có lúc nào nó `pending`. Alertmanager không nhận được gì.
- `promtool check rules` báo `SUCCESS`. Không ai đổi `rules.yml` từ lúc nó được viết, và rule này từng được duyệt theo
  đúng ngưỡng 5% trong 5 phút.

`starter/rules.yml` là rule đang chạy. Sửa nó sao cho alert bắn với đầu ra `/metrics` thật của service. Đừng đoán: dùng
`tests/fixtures/eta_app.py` để xem service xuất gì (test dựng đúng app đó, gửi yêu cầu thật rồi đưa các chuỗi thời gian nó
xuất cho `promtool test rules`). Chỉ sửa `starter/rules.yml`; không đổi service hay test.

Luật mà test kiểm:

- Giữ nguyên tên alert `ETAHighErrorRate`, `for`, `labels`, `annotations`, ngưỡng 0.05, cửa sổ `[5m]`, và các điều kiện
  `job="eta-service"`, `route="/predict"` trong biểu thức. Chỉ đúng một rule trong file.
- Với service lỗi 30% (mã 500 và 503): chưa bắn ở phút 2, bắn ở phút 15 và 30.
- Service khỏe, lỗi 1%, hoặc không có traffic (mọi bộ đếm đứng yên): không bắn.
- Test có thêm một ca hồi quy chứng minh bản rule gốc (`tests/fixtures/rules.original.yml`) im lặng trước đầu ra thật.

## Tiêu chí đạt

- `uv run pytest tracks/mlops/modules/09-monitoring-observability/exercises/intermediate/03-incident-silent-alert -q` pass.
- Bạn viết được một câu mô tả nguyên nhân gốc và một việc để lần sau loại sự cố cùng loại trước khi nó xảy ra.
- Bạn nêu được vì sao `inactive` kéo dài không chứng minh được rằng mọi thứ ổn.

## Gợi ý

### Gợi ý 1

Chia biểu thức làm hai nửa và chạy từng nửa bằng tay (hoặc trong `promtool test rules` với `promql_expr_test`) trên đầu ra
thật của service. Nửa nào cho kết quả khác điều bạn mong đợi?

### Gợi ý 2

Trước khi sửa, hãy in đầu ra `/metrics` của `eta_app.py` sau vài yêu cầu lỗi và đọc từng dòng của `http_requests_total` bằng mắt,
rồi đối chiếu với từng điều kiện trong rule.

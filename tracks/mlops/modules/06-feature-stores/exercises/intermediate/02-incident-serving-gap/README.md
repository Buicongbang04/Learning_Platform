---
title: Sự cố - model tốt offline nhưng tệ khi phục vụ
level: intermediate
services: []
files:
  - path: starter/service.py
    note: Dịch vụ dự đoán giá cước, tìm và sửa lỗi
  - path: starter/API.md
    note: Hợp đồng API với app khách hàng, không đổi
  - path: tests/test_incident.py
    note: Không sửa
  - path: tests/fixtures/service_v1.py
    note: Bản gốc của service để test chứng minh triệu chứng
run:
  - uv run pytest tracks/mlops/modules/06-feature-stores/exercises/intermediate/02-incident-serving-gap -q
---

## Mục tiêu

Chẩn đoán một sự cố mà không có exception, không có alert: model tốt trên số đo offline nhưng dự đoán sai khi phục vụ. Tìm
nguyên nhân bằng cách đối chiếu hai đường tính, sửa tối thiểu, và có test chứng minh.

## Đề bài

Đội giá cước vừa đưa model dự đoán giá cước taxi lên production. Triệu chứng sau hai ngày:

- Trên tập kiểm thử offline, MAE là 1.49 USD. Bản thân model đã được xem xét kỹ, huấn luyện lại cũng cho kết quả tương tự.
- Đội phát lại cùng 4000 chuyến của tập kiểm thử qua API: MAE là 10.76 USD. Dự đoán trung bình 23.6 USD, trong khi
  dự đoán offline cho cùng các chuyến là 13.0 USD.
- Chuyến dài lệch nhiều hơn chuyến ngắn: có chuyến offline dự đoán 32.7 USD, qua API ra 72.7 USD.
- Độ trễ, tỉ lệ lỗi HTTP, log đều bình thường. Không có exception. Khách bắt đầu phàn nàn giá hiển thị cao bất thường.
- Rollback sang bản dịch vụ trước đó cho kết quả y hệt.

`starter/service.py` có `build_features(df)` (đường offline, dùng khi huấn luyện) và `FareService` (đường online). Hợp đồng của
API với app nằm trong `starter/API.md` và đã phát hành, không đổi được.

Sửa `starter/service.py` để dự đoán qua API **trùng** dự đoán offline cho cùng chuyến. Ràng buộc test ép:

- Chỉ sửa trong `service.py`; **không đổi đầu ra của `build_features`** (test kiểm trên một bảng mẫu) và không đổi hợp đồng
  API: `FareService.predict(request: dict) -> float`, `request` theo `API.md`.
- Với 4000 chuyến thật tháng 3/2019 (`mlopskit.real_month`), mô hình học trên 20 000 chuyến khác, dự đoán online lệch dự đoán
  offline tối đa `1e-6`, MAE online bằng MAE offline (sai khác tương đối dưới 0.1%), độ lệch trung bình trên chuyến dài dưới
  0.01 USD.
- `zone_id` thiếu hoặc `None` được coi như `0`; thiếu `distance_km` thì `ValueError`.
- `predict` vẫn trả `float`.

Test cũng có một ca chạy bản gốc của service (`tests/fixtures/service_v1.py`) và khẳng định triệu chứng tái hiện: MAE online
gấp hơn hai lần MAE offline. Ca này phải luôn pass, kể cả sau khi bạn sửa.

## Tiêu chí đạt

- `uv run pytest tracks/mlops/modules/06-feature-stores/exercises/intermediate/02-incident-serving-gap -q` pass.
- Viết được tóm tắt sự cố ba dòng: triệu chứng, nguyên nhân, vì sao không có alert nào bắn.
- Đề xuất được một kiểm tra tự động mà nếu có từ trước thì sự cố này bị chặn ở CI.

## Gợi ý

### Gợi ý 1

Đừng bắt đầu từ model. Lấy cùng một chuyến, tính feature theo đường offline và theo đường online, rồi so từng cột (bài
`03-skew-report` làm đúng việc này). Cột nào lệch trước thì nguyên nhân nằm quanh đó.

### Gợi ý 2

Đọc `API.md` và `featurize` song song, từng trường một, và hỏi: giá trị đi vào model có cùng ý nghĩa với giá trị lúc huấn luyện
không? Khi sửa, cân nhắc cách làm để hai đường không thể lệch lần nữa thay vì chỉ sửa một dòng.

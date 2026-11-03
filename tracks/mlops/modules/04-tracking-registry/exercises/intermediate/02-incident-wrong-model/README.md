---
title: Sự cố - dự đoán ETA nhảy vọt sau deploy mà không ai đổi model
level: intermediate
services: []
files:
  - path: starter/service.py
    note: Service nạp model, tìm và sửa lỗi
  - path: tests/test_incident.py
    note: Không sửa
run:
  - uv run pytest tracks/mlops/modules/04-tracking-registry/exercises/intermediate/02-incident-wrong-model -q
---

## Mục tiêu

Chẩn đoán một sự cố "model sai sau deploy" từ triệu chứng và log, rồi sửa tối thiểu sao cho hành vi đúng và có test chứng minh.

## Đề bài

Thứ Ba, 14:05, service `taxi-eta` được restart trong một đợt deploy thường lệ (không đổi mã nguồn, không ai đổi cấu hình).
Triệu chứng ghi nhận:

- Ngay sau restart, mọi dự đoán ETA trả về khoảng 999 giây, trong khi trước đó là 620 giây cho cùng chuyến. Khách bắt đầu báo
  "app báo xe tới sau 16 phút ở mọi nơi".
- Log lúc khởi động: `loaded taxi-eta v3`. Response có trường `model_version: 3`.
- Trong MLflow UI, `taxi-eta` có 3 version. Version 3 do một thành viên đăng ký lúc 11:30 để thử nghiệm, nhánh feature đang
  dở, chưa qua review. Quy ước của đội: **model được duyệt cho production là version đang giữ alias `champion`**; hiện alias
  đó đang ở version 2.
- Rollback sang bản service cũ không giúp: bản cũ cũng cho 999 sau khi restart.
- Không có alert nào kêu: service trả HTTP 200 và độ trễ bình thường.

Sửa `starter/service.py` để service luôn phục vụ đúng model được duyệt. Hợp đồng giao diện mà test dùng:

- `ModelService(tracking_uri, model_name)`: nạp model lúc khởi tạo; thuộc tính `version` (int).
- `predict(rows) -> {"model_version": int, "predictions": [float, ...]}`.
- `refresh() -> bool`: nạp lại nếu model được duyệt đã đổi (trả `True`), không thì trả `False`.
- Chưa có model nào được duyệt thì khởi tạo `ModelService` phải `LookupError`. `refresh()` không xác định được model
  được duyệt cũng `LookupError`, và service giữ nguyên model đang chạy, vẫn dự đoán được.

Tìm nguyên nhân bằng cách đọc log, so với registry, và đọc mã; chỉ sửa trong `service.py`, không đổi registry hay test.

## Tiêu chí đạt

- Với 3 version và alias `champion` ở version 2, service phục vụ version 2 (620 giây), kể cả sau restart và sau khi có thêm
  một version mới được đăng ký.
- Khi alias `champion` được dời về version 1 (rollback), `refresh()` đổi sang version 1 và trả `True`; gọi lại trả `False`.
- Registry có version nhưng không ai mang alias `champion`: khởi tạo `LookupError`.
- `refresh()` thất bại không làm service mất model đang chạy.

## Gợi ý

### Gợi ý 1

Bắt đầu từ câu "service chọn version nào, bằng cách nào" thay vì từ model: so con số trong log với trạng thái registry, rồi
tìm trong mã đúng dòng quyết định điều đó. Hỏi tiếp: điều gì khiến cùng một mã cho kết quả khác nhau ở hai thời điểm?

### Gợi ý 2

Sau khi sửa, tự thử hai tình huống mà hệ thống thật hay gặp: có người đăng ký thêm version trong lúc service đang chạy, và
có người dời trạng thái duyệt về version cũ. Cả hai phải cho hành vi bạn mô tả được bằng một câu.

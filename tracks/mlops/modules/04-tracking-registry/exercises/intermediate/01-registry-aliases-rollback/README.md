---
title: Registry thật - đăng ký version, alias champion và rollback có chứng minh
level: intermediate
services: []
files:
  - path: starter/registry.py
    note: 4 hàm TODO
  - path: tests/test_registry.py
    note: Không sửa
  - path: quiz.yaml
    note: Trắc nghiệm chọn công cụ và registry
run:
  - docker compose -f setup/mlops/compose.yaml up -d --wait
  - uv run pytest tracks/mlops/modules/04-tracking-registry/exercises/intermediate/01-registry-aliases-rollback -q
---

## Mục tiêu

Làm việc với Model Registry của MLflow server thật (Postgres + MinIO): đăng ký nhiều version, đặt alias `champion`, rollback
bằng cách đổi alias, và chứng minh client nạp đúng version sau mỗi thao tác bằng dự đoán của chính model đó.

## Đề bài

Cần stack `setup/mlops` đang chạy (test tự skip và nói lệnh bật nếu chưa). Test dùng tên model và experiment có hậu tố
ngẫu nhiên và dọn khi xong (model xoá hẳn, experiment xoá mềm). Test tự đặt `MLFLOW_ENABLE_PROXY_MULTIPART_DOWNLOAD=false` cho tiến trình pytest; khi
bạn tự chạy code ngoài pytest với server này, đặt biến đó (và `MLFLOW_TRACKING_URI`) trong shell, không thì tải artifact có
thể treo vì URL presigned trỏ tới tên miền nội bộ của MinIO.

Mọi hàm nhận `client = MlflowClient(<uri server>)`. Trong `starter/registry.py`:

1. `register_version(client, model_name, model_uri, model_id, run_id, tags=None) -> int`: đăng ký version mới
   (`model_uri` và `model_id` là của model đã `log_model` bằng MLflow 3). Tạo registered model nếu chưa có, gọi lần hai
   với cùng tên không được lỗi. Version gắn `run_id`, `model_id`, `tags`; chỉ trả về (số version, kiểu `int`) khi status
   là `READY`.
2. `promote(client, model_name, version, alias="champion") -> int | None`: đặt alias cho version, trả version đang giữ alias
   trước đó (`None` nếu chưa có). Khi có version cũ, ghi lên **version mới** tag `previous_<alias>` = số version cũ dạng
   chuỗi; không có version cũ thì không ghi tag nào.
3. `rollback(client, model_name, alias="champion") -> int`: đưa alias về version trong tag `previous_<alias>` của version
   đang giữ alias, gắn tag `rolled_back = "true"` lên version bị gỡ, trả version mới của alias. Alias chưa tồn tại hoặc
   version hiện tại không có tag đường lui thì `LookupError`. Rollback hai lần liên tiếp phải `LookupError` ở lần hai.
4. `load_by_alias(client, model_name, alias="champion") -> (model, version)`: model là `pyfunc`. Version trả về phải đúng là
   version đã nạp, kể cả khi alias bị đổi ngay sau đó (test đổi alias sau khi nạp và kiểm model đã nạp vẫn cho dự đoán
   cũ).

Sau khi test pass, làm phần trắc nghiệm trong app.

## Tiêu chí đạt

- Ba version của một model cho ba dự đoán khác nhau; sau `promote` v2 thì `load_by_alias` trả version 2 và dự đoán của v2,
  sau `rollback` thì trả version 1 và dự đoán của v1.
- Promote lần đầu không ghi tag `previous_*`; promote lần hai ghi đúng tag.
- Các ngoại lệ `LookupError` đúng như mô tả ở trên.
- Test dọn sau khi chạy: model xoá hẳn khỏi registry, experiment chuyển sang trạng thái deleted (MLflow xoá mềm).

## Gợi ý

### Gợi ý 1

`client.create_registered_model` lỗi nếu tên đã có; bắt `MlflowException` và kiểm nội dung lỗi. Với model log bằng MLflow 3,
`create_model_version` cần truyền cả `model_id=`. Sau khi tạo, version có thể ở trạng thái `PENDING_REGISTRATION`: hỏi lại
`get_model_version` tới khi `READY`.

### Gợi ý 2

`client.get_model_version_by_alias` ném `MlflowException` khi alias chưa tồn tại. Tag của version đọc qua
`client.get_model_version(name, version).tags`. Để nạp đúng một version, dùng URI `models:/<tên>/<số version>`.

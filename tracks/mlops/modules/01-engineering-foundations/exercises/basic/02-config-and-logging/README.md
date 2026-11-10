---
title: Config tách khỏi code và logging JSON
level: basic
services: []
files:
  - path: starter/settings.py
    note: 1 TODO lớn
  - path: starter/jsonlog.py
    note: 2 TODO
  - path: starter/config.example.yaml
    note: Mẫu cấu hình, có sẵn
  - path: tests/test_config_logging.py
    note: Không sửa
run:
  - uv run pytest tracks/mlops/modules/01-engineering-foundations/exercises/basic/02-config-and-logging -q
---

## Mục tiêu

Viết lớp cấu hình có thứ tự ưu tiên rõ ràng (mặc định, YAML, biến môi trường) và logger ghi mỗi dòng là một JSON, che bí mật.

## Đề bài

**Cấu hình (`settings.py`).** Hoàn thành `load_settings(yaml_path, env)`:

- Ưu tiên tăng dần: giá trị mặc định của `Settings` < tệp YAML < biến môi trường `ETA_<TÊN_IN_HOA>` (vd. `ETA_SEED`, `ETA_DATA_PATH`).
- `env=None` nghĩa là đọc `os.environ`; test có thể truyền một dict.
- Khoá lạ trong YAML là lỗi (`ValueError` nêu tên khoá): `sed: 3` thay vì `seed: 3` phải bị bắt, không được bỏ qua âm thầm.
- Số không parse được là `ValueError` nêu tên trường. Thiếu `data_path` ở mọi nguồn là `ValueError`.
- Đường dẫn tương đối trong YAML tính từ **thư mục chứa tệp YAML**; đường dẫn từ env và giá trị mặc định tính từ thư mục đang chạy. Mọi đường dẫn trả về là tuyệt đối.

**Logging (`jsonlog.py`).** Hoàn thành `JsonFormatter` và `configure_logging`:

- Mỗi bản ghi là một dòng JSON có `ts` (ISO 8601 UTC), `level`, `logger`, `msg`, cộng mọi trường truyền qua `extra=`.
- Trường có tên chứa `password`, `token`, `secret` hoặc `key` (không phân biệt hoa thường) bị thay bằng `"***"`.
- `logger.exception(...)` thêm khoá `exc` chứa traceback.
- `configure_logging` gọi nhiều lần không nhân đôi handler và không đẩy log lên root logger.

## Tiêu chí đạt

- Thứ tự ưu tiên mặc định < YAML < env đúng với từng trường.
- Đường dẫn tương đối trong YAML không phụ thuộc thư mục đang chạy.
- Khoá lạ, số sai, thiếu `data_path` đều có lỗi rõ ràng nêu tên trường.
- `config.example.yaml` nạp được và cho `data_path` là `yellow_tripdata_2019-01.parquet`.
- Mỗi dòng log là JSON hợp lệ có đủ khoá (`logger` là tên logger bạn cấu hình, `ts` có hậu tố `+00:00`); bí mật không lọt vào đầu ra; traceback được giữ.
- Cấu hình logger hai lần vẫn ra đúng một dòng cho mỗi bản ghi.

## Gợi ý

### Gợi ý 1

Dựng `dict` giá trị từng lớp rồi cập nhật theo thứ tự ưu tiên, cuối cùng mới tạo `Settings(**values)`. Tên khoá hợp lệ lấy từ `dataclasses.fields`.

### Gợi ý 2

Trường chuẩn của `LogRecord` có thể lấy từ `vars(logging.LogRecord("", 0, "", 0, "", (), None))`; mọi thuộc tính khác trong `vars(record)` là `extra`.

### Gợi ý 3

Với đường dẫn từ YAML dùng `yaml_path.resolve().parent / giá_trị`; đừng dùng `Path.cwd()`. Với `configure_logging`, xoá handler cũ của chính logger đó trước khi thêm handler mới.

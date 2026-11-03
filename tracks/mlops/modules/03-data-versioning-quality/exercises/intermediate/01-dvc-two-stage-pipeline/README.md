---
title: Pipeline DVC hai stage prepare → split và hành vi dvc repro
level: intermediate
services: []
files:
  - path: starter/dvc.yaml
    note: 2 stage cần khai báo
  - path: starter/params.yaml
    note: Có sẵn
  - path: starter/prepare.py
    note: Có sẵn, không sửa
  - path: starter/split.py
    note: Có sẵn, không sửa
  - path: tests/test_pipeline.py
    note: Không sửa
run:
  - uv run pytest tracks/mlops/modules/03-data-versioning-quality/exercises/intermediate/01-dvc-two-stage-pipeline -q
---

## Mục tiêu

Khai báo pipeline trong `dvc.yaml` sao cho `dvc repro` chạy đúng stage cần chạy: đổi dữ liệu đầu vào thì chạy lại cả chuỗi, đổi
một tham số của `split` thì chỉ chạy lại `split`, không đổi gì thì bỏ qua tất cả.

## Đề bài

Hai script đã viết sẵn. Việc của bạn là điền `starter/dvc.yaml` với đúng hai stage:

| Stage | `cmd` | Đầu vào | Đầu ra |
| --- | --- | --- | --- |
| `prepare` | `python prepare.py` | script, `data/raw/trips.csv`, tham số `prepare.min_distance` | `data/clean.csv` |
| `split` | `python split.py` | script, `data/clean.csv`, tham số `split.seed` và `split.test_size` | `data/train.csv`, `data/test.csv` |

Nguyên tắc khai báo: mọi tệp mà stage đọc phải nằm trong `deps`, mọi khoá tham số stage dùng phải nằm trong `params`. Tên stage phải đúng `prepare` và `split`; dữ liệu thô `data/raw/trips.csv` do test tạo (không thuộc stage nào). `params.yaml` đã có
sẵn các khoá trên. Test dựng repo Git + DVC tạm, chép các tệp starter vào, rồi chạy `dvc repro` nhiều lần trong sandbox.

## Tiêu chí đạt

- `dvc repro` lần đầu chạy cả hai stage và sinh `dvc.lock`, `data/train.csv`, `data/test.csv`.
- Chạy lại ngay không đổi gì: cả hai stage đều bị bỏ qua.
- Thêm một dòng vào `data/raw/trips.csv`: cả `prepare` và `split` chạy lại.
- Đổi `split.test_size` trong `params.yaml`: chỉ `split` chạy lại, `prepare` bị bỏ qua.
- Đổi `prepare.min_distance`: cả hai chạy lại (vì đầu ra của `prepare` đổi).
- `dvc.yaml` khai báo `data/clean.csv` là `outs` của `prepare` và là `deps` của `split` (đó là cách DVC dựng đồ thị).

## Gợi ý

### Gợi ý 1

Dùng `dvc stage add -n prepare -d ... -o ... -p ... python prepare.py` để sinh khối YAML đúng, hoặc viết tay theo mẫu trong
phần lý thuyết. Tham số theo dạng `-p prepare.min_distance`: chỉ khoá đó được theo dõi, không phải cả `params.yaml`.

### Gợi ý 2

Nếu đổi `test_size` mà `prepare` cũng chạy lại, bạn đã khai báo cả `params.yaml` như một `deps` thay vì dùng mục `params:`.

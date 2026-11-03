---
title: Sự cố, dvc repro không chạy lại sau khi sửa script lọc dữ liệu
level: intermediate
services: []
files:
  - path: starter/dvc.yaml
    note: Tệp cần sửa
  - path: starter/params.yaml
    note: Không sửa
  - path: starter/prepare.py
    note: Không sửa
  - path: tests/test_incident.py
    note: Không sửa
run:
  - uv run pytest tracks/mlops/modules/03-data-versioning-quality/exercises/intermediate/03-incident-repro-not-rerun -q
---

## Mục tiêu

Chẩn đoán vì sao DVC báo "didn't change, skipping" trong khi bạn vừa sửa code, rồi sửa khai báo pipeline để không bao giờ dùng lại
dữ liệu cũ một cách im lặng.

## Đề bài

Triệu chứng từ đồng đội: "Mình sửa `prepare.py` để lọc thêm chuyến ngắn hơn 0,1 dặm, chạy `dvc repro`, DVC in
`Stage 'prepare' didn't change, skipping`, và `data/clean.csv` vẫn còn nguyên các chuyến đó. Model train xong vẫn học từ dữ liệu cũ.
Đổi tham số lọc trong `params.yaml` cũng không thấy gì xảy ra."

Việc của bạn: tìm nguyên nhân bằng cách tự tái hiện trong một repo tạm (`dvc init`, `dvc repro`, sửa, `dvc repro`, `dvc status`,
`dvc dag`), rồi sửa **chỉ** `starter/dvc.yaml`. Không sửa `prepare.py` và `params.yaml`; chỉ ghi nguyên nhân vào commit message
hoặc ghi chú của bạn, test không đọc.

Test dùng sandbox để chạy `dvc repro` trong repo tạm.

## Tiêu chí đạt

- Lần chạy đầu tạo `data/clean.csv`; chạy lại không đổi gì thì bỏ qua stage.
- Sửa nội dung `prepare.py` (đổi điều kiện lọc) rồi `dvc repro`: stage chạy lại và `data/clean.csv` đổi theo.
- Đổi tham số lọc trong `params.yaml` rồi `dvc repro`: stage chạy lại.
- Đổi một tham số **không** thuộc stage này (khoá khác trong `params.yaml`): stage vẫn bị bỏ qua.

## Gợi ý

### Gợi ý 1

Tái hiện trước khi đoán: chạy `dvc repro`, sửa script, chạy `dvc status` và `dvc repro` lần nữa, rồi so sánh với kết quả bạn mong đợi.

### Gợi ý 2

Mở `dvc.lock` và `dvc dag` sau lần chạy đầu và đối chiếu với những gì script thực sự đọc khi chạy.

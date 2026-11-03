---
title: Image thân thiện cache và build context sạch
level: basic
services: []
files:
  - path: starter/Dockerfile
    note: Bản đang chậm và phình to, sửa lại
  - path: starter/.dockerignore
    note: TODO
  - path: tests/test_cache.py
    note: Không sửa
run:
  - docker pull python:3.12.11-slim
  - uv run pytest tracks/mlops/modules/02-containers-for-ml/exercises/basic/02-cache-friendly-image -q
---

## Mục tiêu

Sắp xếp layer để sửa code không kéo theo cài lại dependency nặng, và giữ dữ liệu cùng rác sinh ra khi dev ra khỏi image.

## Đề bài

`starter/Dockerfile` của đồng nghiệp chạy được nhưng: mỗi lần sửa một dòng `app/serve.py` là cài lại cả numpy, scipy, scikit-learn; image chứa cả thư mục `notebooks/` (150 MB CSV trong build context của test) lẫn `__pycache__`.

Context của test giống bài trước (`requirements.txt`, `app/`, `model.joblib`) cộng `notebooks/trips-2019-01.csv` và `app/__pycache__/`. Sửa `Dockerfile` và `.dockerignore` sao cho:

- trong stage cài đặt, `COPY requirements.txt` đứng **trước** `RUN pip install`, và không có `COPY` nào chép cả thư mục (`.`) hay `app` trước bước cài;
- multi-stage: ít nhất hai `FROM`, stage cuối dùng `COPY --from=<stage>` để lấy dependency đã cài;
- mọi `FROM` ghim tag đầy đủ (vd. `3.12.11-slim`), biến thể `slim`, không `latest`;
- `pip install` kèm `--no-cache-dir`;
- `.dockerignore` loại `notebooks/` và `__pycache__` khỏi context, để `/srv` trong image không có chúng;
- image nhỏ hơn **600 MB** và service vẫn trả lời `/healthz`; model nằm ở `/models/model.joblib`, `WORKDIR` là `/srv`.

## Tiêu chí đạt

- `uv run pytest tracks/mlops/modules/02-containers-for-ml/exercises/basic/02-cache-friendly-image -q` pass.
- Giải thích được vì sao thứ tự `COPY`/`RUN` quyết định layer nào được cache, và `.dockerignore` ảnh hưởng cả cache lẫn bảo mật (bí mật không lọt vào layer).

## Gợi ý

### Gợi ý 1

Docker cache theo từng lệnh và nội dung đầu vào của lệnh đó. Thứ ít đổi nhất (dependency) đặt trước, thứ hay đổi nhất (code) đặt sau.

### Gợi ý 2

`COPY . .` làm mọi tệp trong context thành đầu vào của layer. Chỉ chép đúng tệp mỗi bước cần, và dùng `.dockerignore` cho phần không bao giờ cần.

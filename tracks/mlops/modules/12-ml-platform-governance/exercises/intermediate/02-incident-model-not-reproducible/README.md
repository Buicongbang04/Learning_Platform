---
title: Sự cố - model production không tái lập được dù đã log đủ mọi thứ
level: intermediate
services: []
files:
  - path: starter/pipeline.py
    note: Train, ghi run lên MLflow và dựng lại; tìm và sửa lỗi
  - path: starter/trainer.py
    note: Script train chạy trong tiến trình con, không sửa
  - path: tests/test_incident.py
    note: Không sửa
  - path: tests/fixtures/libs
    note: Thư viện giả lập dùng trong test, không sửa
run:
  - uv run pytest tracks/mlops/modules/12-ml-platform-governance/exercises/intermediate/02-incident-model-not-reproducible -q
---

## Mục tiêu

Chẩn đoán một sự cố "không dựng lại được model" từ triệu chứng, tìm thứ **chưa được ghi** dù mọi tag trông đầy đủ, rồi sửa tối thiểu sao cho dựng lại cho ra đúng dự đoán cũ và có test chứng minh.

## Đề bài

Model ETA đang chạy production có dự đoán trên một tập giữ lại cố định. Quý sau cần vá một lỗi nhỏ, nên người trực chạy lại **đúng run đã sinh ra nó**. Triệu chứng:

- Dự đoán của bản dựng lại lệch với bản production, rõ ở chữ số thứ hai sau dấu phẩy; metric của run dựng lại không trùng metric của run gốc.
- Run gốc có đủ: `git_commit` đầy đủ 40 ký tự và `git_dirty = false`, `data_version`, `lockfile_sha256`, param `seed` và `alpha`. Công cụ audit của bài 01 báo run đủ điều kiện tái lập.
- Dựng lại hai lần liên tiếp thì hai kết quả giống hệt nhau, nên không phải ngẫu nhiên giữa các lần chạy.
- Không ai đổi mã, không ai đổi dữ liệu, không ai đổi tham số.

Sửa `starter/pipeline.py` để `replay` cho ra đúng dự đoán đã sinh ra lúc train, kể cả khi `index` lúc dựng lại không giống `index` lúc train. Hợp đồng giao diện mà test dùng:

- `train_and_log(tracking_uri, experiment_id, workdir, index, seed=7, alpha=1.0) -> run_id`: train, ghi run `FINISHED` lên MLflow (artifact `preds.json` là dự đoán gốc). Lỗi giữa chừng thì run phải là `FAILED`.
- `replay(tracking_uri, run_id, workdir, index) -> list[float]`: dựng lại từ **những gì run ghi** và trả dự đoán trên tập giữ lại. Không sửa run gốc (tag, param, metric, artifact giữ nguyên).
- `index` là tham số do test cấp cho tiến trình con (mỗi test dựng một `index` riêng); chỉ sửa `pipeline.py`, không sửa `trainer.py`, test hay fixture.
- Không dựng lại được từ những gì đã ghi thì `LookupError` có tên thứ bị thiếu, không im lặng dùng thứ khác.

## Tiêu chí đạt

- `replay` khớp dự đoán gốc trong sai số 1e-9, kể cả khi `index` lúc dựng lại khác `index` lúc train (test thử nhiều dạng khác nhau).
- `replay` hai lần cho cùng kết quả; không sửa run gốc.
- Dựng lại không được thì `LookupError` nêu rõ, không trả kết quả khác.
- Bạn nói được trong một câu vì sao bốn thứ trong tag chưa đủ, và thêm vào run thứ gì để công cụ audit lần sau bắt được lỗi kiểu này.

## Gợi ý

### Gợi ý 1

So hai lần chạy (lúc train và lúc dựng lại) theo thứ tự: đầu vào nào của `trainer.py` đã có trong run, và đầu vào nào **không** nằm trong run mà vẫn quyết định kết quả. Một tiến trình con chỉ làm đúng một việc với những gì nó được cấp.

### Gợi ý 2

Điều gì khiến cùng một lệnh cho kết quả khác nhau ở hai thời điểm? Tìm trong `pipeline.py` dòng quyết định nó, và hỏi dòng đó được tính vào lúc nào ở `train_and_log` so với ở `replay`.

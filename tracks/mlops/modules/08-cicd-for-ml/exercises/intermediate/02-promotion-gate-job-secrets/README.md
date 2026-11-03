---
title: Cổng promotion thành job CI - exit khác 0 chặn deploy, secrets không lộ vào log
level: intermediate
services: []
files:
  - path: starter/gate.py
    note: Hàm decide TODO
  - path: starter/ct.yml
    note: Workflow train, gate, deploy chưa nối
  - path: tests/test_gate_job.py
    note: Không sửa
run:
  - uv run pytest tracks/mlops/modules/08-cicd-for-ml/exercises/intermediate/02-promotion-gate-job-secrets -q
---

## Mục tiêu

Biến cổng promotion (module 04) thành một job của pipeline: challenger tệ hơn thì job **thoát khác 0** và mọi job phụ thuộc
vào nó không chạy. Đồng thời dùng secret để "đẩy lên registry" mà không để lộ nó vào log, kể cả dưới dạng đã biến đổi.

## Đề bài

Repo `etalite` có `train.py` (huấn luyện mẫu trên 4 000 chuyến thật của tháng 3/2019, ghi `models/model.json` và
`models/metrics.json` với `mae`). Bạn sửa hai tệp trong `starter/`.

**`gate.py`**: hàm `decide(challenger, champion, min_improvement) -> (đạt: bool, lý do: str)`; `main()` đã có sẵn, đọc
`models/metrics.json` và (nếu có) `champion/metrics.json`, in `GATE PASSED: ...` hoặc `GATE FAILED: ...` rồi thoát 0/1.

- `challenger` không có `mae` hữu hạn (thiếu, NaN, vô cực, không phải số): không đạt.
- `champion` là `None` (model đầu tiên): đạt.
- Ngược lại đạt khi `mae` của challenger `<=` `mae` champion `*` `(1 - min_improvement)`; đúng bằng ngưỡng thì đạt (cộng sai số
  `1e-12`). `mae` champion không hữu hạn: không đạt.
- `lý do` không rỗng; khi từ chối có cả hai con số.

**`ct.yml`**: ba job nối nhau, chỉ có bước `run:`.

1. `train` chạy `python train.py`.
2. `gate` `needs: train`, chạy `python gate.py --min-improvement 0.01`.
3. `deploy` `needs: gate`. Secret `REGISTRY_TOKEN` truyền qua `env:` của bước cần nó. Không có secret (chuỗi rỗng) thì bước
   in lỗi và thoát 1. Có thì sao chép `models/model.json` vào `registry/model.json` và in một dòng bắt đầu bằng `DEPLOYED`.
   Log của workflow **không được chứa** giá trị secret, bản base64 của nó, hay 10 ký tự đầu của nó.

Test chạy `act` với `-s REGISTRY_TOKEN=...` và đặt `champion/metrics.json` theo hệ số 1,5 (champion tệ hơn, challenger thắng)
hoặc 0,5 (champion tốt hơn nhiều) so với MAE challenger thật.

## Tiêu chí đạt

- `decide` đúng ở 11 ca (ngưỡng, đúng bằng ngưỡng, không champion, NaN, thiếu, vô cực).
- Challenger tốt hơn: `act` thoát 0, log có `GATE PASSED` và `DEPLOYED`, `registry/model.json` giống `models/model.json`.
- Challenger tệ hơn: `act` thoát khác 0, log có `GATE FAILED`, không có `DEPLOYED`, không dòng nào của job `deploy`, không có thư mục `registry/`.
- Model đầu tiên (không có `champion/metrics.json`) qua cổng và được deploy.
- Thiếu secret: pipeline đỏ và không có `registry/model.json`.
- Log không chứa secret ở ba dạng nêu trên.
- `deploy` `needs: gate`, `gate` `needs: train`.

## Gợi ý

### Gợi ý 1

Cổng đỏ chặn deploy nhờ hai thứ cùng lúc: `gate.py` thoát khác 0 (bước fail, job fail) và `deploy` khai `needs: gate`. Thiếu một
trong hai thì deploy vẫn chạy. Phép so sánh giữa số thực nên có sai số làm tròn: ngưỡng `200 * (1 - 0.01)` không đúng bằng `198` trong số thực.

### Gợi ý 2

Runner che giá trị secret **nguyên văn** khi nó xuất hiện trong log (thấy `***`), nhưng không che bản cắt, đảo hay mã hoá.
Cách an toàn nhất là không đưa giá trị vào bất kỳ lệnh in nào, rồi tự đọc log chạy được để kiểm.

---
title: Sự cố - pipeline xanh nhưng model được deploy không phải model vừa train
level: intermediate
services: []
files:
  - path: starter/release.yml
    note: Workflow release, tìm và sửa lỗi
  - path: tests/test_incident.py
    note: Không sửa
run:
  - uv run pytest tracks/mlops/modules/08-cicd-for-ml/exercises/intermediate/03-incident-wrong-model-deployed -q
---

## Mục tiêu

Chẩn đoán một sự cố mà không có gì đỏ: mọi job xanh, nhưng thứ chạy ở production không phải thứ bạn vừa train. Tự tái hiện bằng
`act`, tìm nguyên nhân trong workflow, sửa tối thiểu, và để lại một kiểm tra chặn lỗi này quay lại.

## Đề bài

Đội ETA có workflow `release` (`starter/release.yml`): job `train` huấn luyện, job `deploy` đưa model lên "production" (ở bài
này là chép vào `deployed/model.json`). Triệu chứng đội ghi nhận:

- Pipeline xanh ở mọi lần chạy, không cảnh báo, không lỗi.
- Chín lần chạy đầu mọi thứ đúng. Từ lần chạy thứ 10 trở đi, thỉnh thoảng người trực thấy `deployed/model.json` mang
  `model_id` của một model cũ, khác dòng `trained model_id=...` mà job `train` in ra trong cùng lần chạy. MAE trên production
  không cải thiện dù log train báo tốt hơn.
- Rollback workflow về phiên bản cũ không giúp. Không ai đổi code hay tham số trong thời gian đó.

Hợp đồng của môi trường mà test dựng (bạn không sửa các phần này):

- `train.py` huấn luyện, in `trained model_id=<id>`, rồi ghi model vào kho artifact `store/run-<số lần chạy>/model.json`
  (số lần chạy là `github.run_number`). Kho có sẵn các model của lần chạy 8, 9, 10; mỗi lần chạy của test thêm một mục.
- Chỉ sửa `starter/release.yml`, chỉ dùng bước `run:`. Trên GitHub thật mỗi job chạy trên một máy riêng và chỉ kho artifact là
  chung, nên bước của job `deploy` **không được đọc `models/`** (thư mục làm việc của job `train`).
- Lần chạy mà job `train` không tạo model nào vào kho thì job `deploy` phải **fail** (thoát khác 0) và không ghi
  `deployed/model.json`; không được đưa model của lần chạy khác lên thay.

Tìm nguyên nhân bằng cách tự chạy `act` với các số lần chạy khác nhau (`--env GITHUB_RUN_NUMBER=11`), so `model_id` hai đầu, rồi đọc
đúng bước quyết định thứ gì được deploy.

## Tiêu chí đạt

- Với số lần chạy 11, 12 và 100 liên tiếp trên cùng một kho, `act` thoát 0 và `model_id` trong `deployed/model.json` đúng bằng
  `model_id` job `train` in ra trong lần chạy đó.
- Lần chạy không có model mới trong kho (`ETALITE_SKIP_PUBLISH=1`): `act` thoát khác 0, không có `deployed/model.json`.
- Job `deploy` vẫn `needs: train` và không tham chiếu `models/`.
- Test cũng có một ca chứng minh workflow gốc tái hiện triệu chứng (xanh nhưng sai model) trên số lần chạy 11.

## Gợi ý

### Gợi ý 1

Bắt đầu từ câu "job `deploy` chọn đầu vào của nó bằng cách nào", không phải từ model. So hai mã định danh ở hai đầu của một lần
chạy; rồi chạy lại với số lần chạy khác để xem lỗi lúc đúng lúc sai phụ thuộc vào cái gì.

### Gợi ý 2

Khi đã biết nguyên nhân, hỏi thêm một câu: nếu bước chọn đầu vào không tìm thấy thứ nó cần thì nó nên làm gì? Một sửa lỗi
vẫn "tìm gì đó khác cho chắc" chỉ chuyển lỗi sang chỗ khác.
